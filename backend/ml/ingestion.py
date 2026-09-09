"""WeatherGPT ML Ingestion Service.
Handles periodic live observation ingestion and incremental historical bootstrapping across India.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError

from backend.database import Session, WeatherLocation, WeatherObservation
from backend.ml.quality import DataQualityService
from backend.providers.weather import client, utcnow

log = logging.getLogger("weathergpt.ml.ingestion")

# Standard Pilot Locations across India
PILOT_LOCATIONS = [
    {"name": "Patna", "latitude": 25.5941, "longitude": 85.1376, "elevation": 53.0, "state": "Bihar"},
    {"name": "New Delhi", "latitude": 28.6139, "longitude": 77.2090, "elevation": 216.0, "state": "Delhi"},
    {"name": "Mumbai", "latitude": 19.0760, "longitude": 72.8777, "elevation": 14.0, "state": "Maharashtra"},
    {"name": "Kolkata", "latitude": 22.5726, "longitude": 88.3639, "elevation": 9.0, "state": "West Bengal"},
    {"name": "Bengaluru", "latitude": 12.9716, "longitude": 77.5946, "elevation": 920.0, "state": "Karnataka"},
    {"name": "Chennai", "latitude": 13.0827, "longitude": 80.2707, "elevation": 6.0, "state": "Tamil Nadu"},
    {"name": "Hyderabad", "latitude": 17.3850, "longitude": 78.4867, "elevation": 542.0, "state": "Telangana"},
    {"name": "Jaipur", "latitude": 26.9124, "longitude": 75.7873, "elevation": 431.0, "state": "Rajasthan"},
    {"name": "Lucknow", "latitude": 26.8467, "longitude": 80.9462, "elevation": 123.0, "state": "Uttar Pradesh"},
    {"name": "Guwahati", "latitude": 26.1445, "longitude": 91.7362, "elevation": 55.0, "state": "Assam"},
]


class WeatherIngestionService:
    """Manages observational telemetry ingestion into the SQL time-series database."""

    def __init__(self):
        self.is_running = False
        self.stats = {
            "status": "idle",
            "last_ingestion_time": None,
            "next_ingestion_time": None,
            "rows_inserted": 0,
            "duplicates_ignored": 0,
            "outliers_flagged": 0,
            "provider_failures": 0,
        }

    def ensure_locations_seeded(self):
        """Ensures all standard pilot locations exist in weather_locations table."""
        with Session.begin() as db:
            for loc in PILOT_LOCATIONS:
                existing = db.scalar(
                    select(WeatherLocation).where(
                        WeatherLocation.latitude == loc["latitude"],
                        WeatherLocation.longitude == loc["longitude"],
                    )
                )
                if not existing:
                    db.add(
                        WeatherLocation(
                            name=loc["name"],
                            latitude=loc["latitude"],
                            longitude=loc["longitude"],
                            elevation=loc["elevation"],
                            state=loc["state"],
                            country="India",
                            is_active=1,
                        )
                    )

    def get_observation_count(self) -> int:
        with Session() as db:
            return db.scalar(select(func.count()).select_from(WeatherObservation)) or 0

    async def ingest_live_location(self, lat: float, lon: float, location_id: int | None = None) -> int:
        """Fetches current real weather for a location and inserts normalized observation."""
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,dew_point_2m,apparent_temperature,precipitation,rain,weather_code,cloud_cover,surface_pressure,wind_speed_10m,wind_direction_10m,wind_gusts_10m",
            "hourly": "soil_temperature_0cm,soil_moisture_0_to_1cm,shortwave_radiation,direct_normal_irradiance,diffuse_radiation,et0_fao_evapotranspiration,vapour_pressure_deficit",
            "timezone": "auto",
            "forecast_days": 1,
        }
        try:
            try:
                data = await client.get("Open-Meteo Ingestion", "https://api.open-meteo.com/v1/forecast", params=params, ttl=60)
            except Exception:
                # Fallback to wttr.in for real-time observation
                wttr_data = await client.get("wttr.in", f"https://wttr.in/{lat:.4f},{lon:.4f}", params={"format": "j1"}, ttl=60)
                curr_w = (wttr_data.get("current_condition") or [{}])[0]
                now_dt = datetime.now(timezone.utc).isoformat()
                temp = float(curr_w.get("temp_C", 25.0) or 25.0)
                hum = float(curr_w.get("humidity", 50.0) or 50.0)
                press = float(curr_w.get("pressure", 1013.0) or 1013.0)
                ws = float(curr_w.get("windspeedKmph", 10.0) or 10.0)
                wd = float(curr_w.get("winddirDegree", 180.0) or 180.0)
                wg = float(curr_w.get("WindGustKmph", ws * 1.3) or ws * 1.3)
                pr = float(curr_w.get("precipMM", 0.0) or 0.0)
                cc = float(curr_w.get("cloudcover", 20.0) or 20.0)
                data = {
                    "current": {
                        "time": now_dt,
                        "temperature_2m": temp,
                        "relative_humidity_2m": hum,
                        "dew_point_2m": temp - ((100 - hum) / 5),
                        "apparent_temperature": float(curr_w.get("FeelsLikeC", temp) or temp),
                        "precipitation": pr,
                        "rain": pr,
                        "surface_pressure": press,
                        "wind_speed_10m": ws,
                        "wind_direction_10m": wd,
                        "wind_gusts_10m": wg,
                        "cloud_cover": cc,
                        "weather_code": 1,
                    },
                    "hourly": {},
                }

            curr = data.get("current", {})
            if not curr:
                return 0

            obs_time = curr.get("time")
            if not obs_time:
                return 0

            # Find matching hourly telemetry if available
            hourly = data.get("hourly", {})
            soil_temp = None
            soil_moist = None
            shortwave = None
            dni = None
            diffuse = None
            et0 = None
            vpd = None

            times = hourly.get("time", [])
            if obs_time in times:
                idx = times.index(obs_time)
                soil_temp = hourly.get("soil_temperature_0cm", [None])[idx]
                soil_moist = hourly.get("soil_moisture_0_to_1cm", [None])[idx]
                shortwave = hourly.get("shortwave_radiation", [None])[idx]
                dni = hourly.get("direct_normal_irradiance", [None])[idx]
                diffuse = hourly.get("diffuse_radiation", [None])[idx]
                et0 = hourly.get("et0_fao_evapotranspiration", [None])[idx]
                vpd = hourly.get("vapour_pressure_deficit", [None])[idx]

            raw_obs = {
                "latitude": lat,
                "longitude": lon,
                "timestamp": datetime.fromisoformat(obs_time).astimezone(timezone.utc).isoformat(),
                "temperature": curr.get("temperature_2m"),
                "humidity": curr.get("relative_humidity_2m"),
                "dew_point": curr.get("dew_point_2m"),
                "feels_like": curr.get("apparent_temperature"),
                "precipitation": curr.get("precipitation"),
                "rainfall": curr.get("rain"),
                "surface_pressure": curr.get("surface_pressure"),
                "wind_speed": curr.get("wind_speed_10m"),
                "wind_direction": curr.get("wind_direction_10m"),
                "wind_gust": curr.get("wind_gusts_10m"),
                "cloud_cover": curr.get("cloud_cover"),
                "weather_code": curr.get("weather_code"),
                "soil_temperature": soil_temp,
                "soil_moisture": soil_moist,
                "shortwave_radiation": shortwave,
                "direct_normal_irradiance": dni,
                "diffuse_radiation": diffuse,
                "et0_fao_evapotranspiration": et0,
                "vapour_pressure_deficit": vpd,
            }

            is_valid, quality_flag, issues = DataQualityService.validate_observation(raw_obs)
            if not is_valid:
                log.warning("Rejected invalid live observation: %s", issues)
                return 0

            with Session.begin() as db:
                obs_row = WeatherObservation(
                    location_id=location_id,
                    latitude=lat,
                    longitude=lon,
                    timestamp=raw_obs["timestamp"],
                    provider="Open-Meteo",
                    data_type="OBSERVATION",
                    quality_flag=quality_flag,
                    temperature=raw_obs["temperature"],
                    feels_like=raw_obs["feels_like"],
                    humidity=raw_obs["humidity"],
                    dew_point=raw_obs["dew_point"],
                    surface_pressure=raw_obs["surface_pressure"],
                    wind_speed=raw_obs["wind_speed"],
                    wind_direction=raw_obs["wind_direction"],
                    wind_gust=raw_obs["wind_gust"],
                    rainfall=raw_obs["rainfall"],
                    precipitation=raw_obs["precipitation"],
                    cloud_cover=raw_obs["cloud_cover"],
                    weather_code=raw_obs["weather_code"],
                    soil_temperature=raw_obs["soil_temperature"],
                    soil_moisture=raw_obs["soil_moisture"],
                    shortwave_radiation=raw_obs["shortwave_radiation"],
                    direct_normal_irradiance=raw_obs["direct_normal_irradiance"],
                    diffuse_radiation=raw_obs["diffuse_radiation"],
                    et0_fao_evapotranspiration=raw_obs["et0_fao_evapotranspiration"],
                    vapour_pressure_deficit=raw_obs["vapour_pressure_deficit"],
                )
                db.add(obs_row)
                self.stats["rows_inserted"] += 1
                if quality_flag == "SUSPICIOUS":
                    self.stats["outliers_flagged"] += 1
                return 1

        except IntegrityError:
            self.stats["duplicates_ignored"] += 1
            return 0
        except Exception as e:
            self.stats["provider_failures"] += 1
            log.warning("Live ingestion error for (%s, %s): %s", lat, lon, e)
            return 0

    async def ingest_live_pilot_network(self) -> int:
        """Ingests live observations across the pilot cities network."""
        self.ensure_locations_seeded()
        total_inserted = 0
        with Session() as db:
            locations = db.scalars(select(WeatherLocation).where(WeatherLocation.is_active == 1)).all()
            for loc in locations:
                inserted = await self.ingest_live_location(loc.latitude, loc.longitude, loc.id)
                total_inserted += inserted
                await asyncio.sleep(0.1)  # Throttle to avoid burst

        self.stats["last_ingestion_time"] = utcnow()
        self.stats["next_ingestion_time"] = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
        return total_inserted

    async def bootstrap_historical_data(self, days_back: int = 14, max_locations: int = 3) -> int:
        """Bootstraps historical hourly observation data if the local DB has insufficient history.
        
        Downloads real ERA5 / historical observation records incrementally.
        """
        self.ensure_locations_seeded()
        count = self.get_observation_count()
        if count >= 300:
            log.info("Sufficient historical observations present (%d rows). Skipping bootstrap.", count)
            return count

        log.info("Bootstrapping historical weather data (%d days) for initial training...", days_back)
        now_dt = datetime.now(timezone.utc)
        end_date = (now_dt - timedelta(days=2)).strftime("%Y-%m-%d")
        start_date = (now_dt - timedelta(days=days_back + 2)).strftime("%Y-%m-%d")

        inserted_count = 0
        with Session() as db:
            locations = db.scalars(select(WeatherLocation).where(WeatherLocation.is_active == 1)).all()[:max_locations]

        for loc in locations:
            params = {
                "latitude": loc.latitude,
                "longitude": loc.longitude,
                "start_date": start_date,
                "end_date": end_date,
                "hourly": "temperature_2m,relative_humidity_2m,dew_point_2m,apparent_temperature,precipitation,rain,surface_pressure,wind_speed_10m,wind_direction_10m,wind_gusts_10m,cloud_cover,soil_temperature_0_to_7cm,soil_moisture_0_to_7cm,shortwave_radiation,direct_normal_irradiance,diffuse_radiation,et0_fao_evapotranspiration,vapour_pressure_deficit",
                "timezone": "auto",
            }
            try:
                data = await client.get("Open-Meteo Archive Bootstrap", "https://archive-api.open-meteo.com/v1/archive", params=params, ttl=86400)
                hourly = data.get("hourly", {})
                times = hourly.get("time", [])
                if not times:
                    continue

                records_checked = len(times)
                dups_loc = 0
                outliers_loc = 0

                with Session.begin() as db:
                    for i in range(records_checked):
                        t_str = times[i]
                        iso_ts = datetime.fromisoformat(t_str).astimezone(timezone.utc).isoformat()
                        
                        # Check if row already exists
                        existing = db.scalar(
                            select(WeatherObservation.id).where(
                                WeatherObservation.latitude == loc.latitude,
                                WeatherObservation.longitude == loc.longitude,
                                WeatherObservation.provider == "Open-Meteo",
                                WeatherObservation.timestamp == iso_ts,
                                WeatherObservation.data_type == "OBSERVATION",
                            )
                        )
                        if existing:
                            dups_loc += 1
                            continue

                        raw_obs = {
                            "latitude": loc.latitude,
                            "longitude": loc.longitude,
                            "timestamp": iso_ts,
                            "temperature": hourly.get("temperature_2m", [None])[i],
                            "humidity": hourly.get("relative_humidity_2m", [None])[i],
                            "dew_point": hourly.get("dew_point_2m", [None])[i],
                            "feels_like": hourly.get("apparent_temperature", [None])[i],
                            "precipitation": hourly.get("precipitation", [None])[i],
                            "rainfall": hourly.get("rain", [None])[i],
                            "surface_pressure": hourly.get("surface_pressure", [None])[i],
                            "wind_speed": hourly.get("wind_speed_10m", [None])[i],
                            "wind_direction": hourly.get("wind_direction_10m", [None])[i],
                            "wind_gust": hourly.get("wind_gusts_10m", [None])[i],
                            "cloud_cover": hourly.get("cloud_cover", [None])[i],
                            "soil_temperature": hourly.get("soil_temperature_0_to_7cm", [None])[i],
                            "soil_moisture": hourly.get("soil_moisture_0_to_7cm", [None])[i],
                            "shortwave_radiation": hourly.get("shortwave_radiation", [None])[i],
                            "direct_normal_irradiance": hourly.get("direct_normal_irradiance", [None])[i],
                            "diffuse_radiation": hourly.get("diffuse_radiation", [None])[i],
                            "et0_fao_evapotranspiration": hourly.get("et0_fao_evapotranspiration", [None])[i],
                            "vapour_pressure_deficit": hourly.get("vapour_pressure_deficit", [None])[i],
                        }

                        is_valid, quality_flag, _ = DataQualityService.validate_observation(raw_obs)
                        if not is_valid:
                            continue

                        obs = WeatherObservation(
                            location_id=loc.id,
                            latitude=loc.latitude,
                            longitude=loc.longitude,
                            timestamp=iso_ts,
                            provider="Open-Meteo",
                            data_type="OBSERVATION",
                            quality_flag=quality_flag,
                            temperature=raw_obs["temperature"],
                            feels_like=raw_obs["feels_like"],
                            humidity=raw_obs["humidity"],
                            dew_point=raw_obs["dew_point"],
                            surface_pressure=raw_obs["surface_pressure"],
                            wind_speed=raw_obs["wind_speed"],
                            wind_direction=raw_obs["wind_direction"],
                            wind_gust=raw_obs["wind_gust"],
                            rainfall=raw_obs["rainfall"],
                            precipitation=raw_obs["precipitation"],
                            cloud_cover=raw_obs["cloud_cover"],
                            soil_temperature=raw_obs["soil_temperature"],
                            soil_moisture=raw_obs["soil_moisture"],
                            shortwave_radiation=raw_obs["shortwave_radiation"],
                            direct_normal_irradiance=raw_obs["direct_normal_irradiance"],
                            diffuse_radiation=raw_obs["diffuse_radiation"],
                            et0_fao_evapotranspiration=raw_obs["et0_fao_evapotranspiration"],
                            vapour_pressure_deficit=raw_obs["vapour_pressure_deficit"],
                        )
                        db.add(obs)
                        inserted_count += 1
                        if quality_flag == "SUSPICIOUS":
                            outliers_loc += 1

                self.stats["rows_inserted"] += inserted_count
                self.stats["duplicates_ignored"] += dups_loc
                DataQualityService.record_quality_report(
                    provider="Open-Meteo Archive",
                    records_checked=records_checked,
                    duplicates_skipped=dups_loc,
                    outliers_flagged=outliers_loc,
                    status="COMPLETED",
                )
                log.info("Bootstrapped %d observations for %s", inserted_count, loc.name)
                await asyncio.sleep(0.5)

            except Exception as err:
                log.error("Historical bootstrap failed for %s: %s", loc.name, err)

        return self.get_observation_count()


ingestion_service = WeatherIngestionService()
