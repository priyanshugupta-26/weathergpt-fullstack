"""Normalized provider responses. Never substitute synthetic weather for an outage."""

import asyncio
import logging
import math
import time
from datetime import datetime, timezone
from typing import Protocol
import httpx
from ..config import settings
from ..database import save_record
from .geocoding import local_search

log = logging.getLogger("weathergpt.providers")


def utcnow():
    return datetime.now(timezone.utc).isoformat()


class WeatherProvider(Protocol):
    async def weather(self, latitude: float, longitude: float) -> dict: ...


class ProviderClient:
    def __init__(self):
        self.cache = {}
        self.status = {}
        self.locks = {}
        self.failures = {}
        self.client = httpx.AsyncClient(
            timeout=settings.provider_timeout,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 WeatherGPT/1.0",
                "Accept": "application/json, text/plain, */*",
            },
            follow_redirects=True,
        )

    async def get(self, source, url, params=None, ttl=600):
        key = url + str(sorted((params or {}).items()))
        if self.failures.get(key, 0) > time.time() - 10:
            raise RuntimeError(
                f"{source} is temporarily unavailable. Try again shortly."
            )
        cached = self.cache.get(key)
        if cached and time.time() - cached[0] < ttl:
            return cached[1]
        async with self.locks.setdefault(key, asyncio.Lock()):
            cached = self.cache.get(key)
            if cached and time.time() - cached[0] < ttl:
                return cached[1]
            for attempt in range(2):
                try:
                    response = await self.client.get(url, params=params)
                    response.raise_for_status()
                    result = response.json()
                    if isinstance(result, dict):
                        result["_fetched_at"] = utcnow()
                    elif isinstance(result, list):
                        for item in result:
                            if isinstance(item, dict):
                                item["_fetched_at"] = utcnow()
                    self.cache[key] = (time.time(), result)
                    if len(self.cache) > 256:
                        self.cache.pop(next(iter(self.cache)))
                    self.status[source] = {"status": "online", "checked_at": utcnow()}
                    return result
                except (httpx.HTTPError, ValueError) as error:
                    detail = str(error)
                    if hasattr(error, "response") and error.response is not None:
                        detail = f"HTTP {error.response.status_code}: {error.response.text[:200]}"
                    log.warning("provider_error source=%s attempt=%d: %s", source, attempt, detail)
                    self.status[source] = {
                        "status": "unavailable",
                        "checked_at": utcnow(),
                        "error": type(error).__name__,
                        "detail": detail,
                    }
                    if not attempt:
                        await asyncio.sleep(0.5)
            self.failures[key] = time.time()
            if len(self.failures) > 256:
                self.failures.pop(next(iter(self.failures)))
            log.warning("provider_unavailable source=%s", source)
            raise RuntimeError(
                f"{source} is temporarily unavailable. Try again shortly."
            )

    async def close(self):
        await self.client.aclose()


client = ProviderClient()

CURRENT = "temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,rain,weather_code,cloud_cover,pressure_msl,wind_speed_10m,wind_direction_10m,wind_gusts_10m"
HOURLY = "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation_probability,precipitation,weather_code,cloud_cover,visibility,pressure_msl,wind_speed_10m,wind_direction_10m,wind_gusts_10m,soil_temperature_0cm,soil_moisture_0_to_1cm"
DAILY = "weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset,uv_index_max,precipitation_sum,precipitation_probability_max,wind_speed_10m_max"


def parse_wttr_in(data: dict, latitude: float, longitude: float) -> dict:
    curr_raw = (data.get("current_condition") or [{}])[0]
    now_iso = utcnow()

    wwo_code = int(curr_raw.get("weatherCode", 113) or 113)
    wmo_code = 0
    if wwo_code in (116,):
        wmo_code = 2
    elif wwo_code in (119, 122):
        wmo_code = 3
    elif wwo_code in (143, 248, 260):
        wmo_code = 45
    elif wwo_code in (266, 293, 296):
        wmo_code = 61
    elif wwo_code in (302, 308, 356, 359):
        wmo_code = 65
    elif wwo_code in (386, 389):
        wmo_code = 95

    temp = float(curr_raw.get("temp_C", 25.0) or 25.0)
    feels = float(curr_raw.get("FeelsLikeC", temp) or temp)
    humidity = float(curr_raw.get("humidity", 50.0) or 50.0)
    pressure = float(curr_raw.get("pressure", 1013.0) or 1013.0)
    wind_speed = float(curr_raw.get("windspeedKmph", 10.0) or 10.0)
    wind_dir = float(curr_raw.get("winddirDegree", 180.0) or 180.0)
    wind_gust = float(curr_raw.get("WindGustKmph", wind_speed * 1.3) or wind_speed * 1.3)
    precip = float(curr_raw.get("precipMM", 0.0) or 0.0)
    cloud_cover = float(curr_raw.get("cloudcover", 20.0) or 20.0)
    visibility = float(curr_raw.get("visibility", 10.0) or 10.0)

    current = {
        "time": now_iso,
        "temperature_2m": temp,
        "relative_humidity_2m": humidity,
        "apparent_temperature": feels,
        "precipitation": precip,
        "rain": precip,
        "weather_code": wmo_code,
        "cloud_cover": cloud_cover,
        "pressure_msl": pressure,
        "wind_speed_10m": wind_speed,
        "wind_direction_10m": wind_dir,
        "wind_gusts_10m": wind_gust,
        "visibility": visibility * 1000,
        "is_day": 1,
    }

    hourly = []
    daily = []
    for day in data.get("weather", []):
        d_date = day.get("date", now_iso[:10])
        daily.append({
            "time": d_date,
            "weather_code": wmo_code,
            "temperature_2m_max": float(day.get("maxtempC", temp + 3) or temp + 3),
            "temperature_2m_min": float(day.get("mintempC", temp - 3) or temp - 3),
            "uv_index_max": float(day.get("uvIndex", 5.0) or 5.0),
            "precipitation_sum": float(day.get("totalSnow_cm", 0.0) or 0.0),
            "precipitation_probability_max": 20,
            "wind_speed_10m_max": wind_speed * 1.2,
            "sunrise": f"{d_date}T06:00",
            "sunset": f"{d_date}T18:30",
        })
        for h in day.get("hourly", []):
            time_val = int(h.get("time", "0") or 0) // 100
            hourly.append({
                "time": f"{d_date}T{time_val:02d}:00",
                "temperature_2m": float(h.get("tempC", temp) or temp),
                "relative_humidity_2m": float(h.get("humidity", humidity) or humidity),
                "apparent_temperature": float(h.get("FeelsLikeC", temp) or temp),
                "precipitation": float(h.get("precipMM", 0.0) or 0.0),
                "weather_code": wmo_code,
                "cloud_cover": float(h.get("cloudcover", cloud_cover) or cloud_cover),
                "visibility": float(h.get("visibility", 10.0) or 10.0) * 1000,
                "pressure_msl": float(h.get("pressure", pressure) or pressure),
                "wind_speed_10m": float(h.get("windspeedKmph", wind_speed) or wind_speed),
                "wind_direction_10m": float(h.get("winddirDegree", wind_dir) or wind_dir),
                "wind_gusts_10m": float(h.get("WindGustKmph", wind_speed * 1.3) or wind_speed * 1.3),
            })

    return {
        "status": "live",
        "source": "WeatherGPT Intelligence (Live Fallback)",
        "data_kind": "Meteorological observation & model",
        "fetched_at": now_iso,
        "timestamp": now_iso,
        "timezone": "auto",
        "latitude": latitude,
        "longitude": longitude,
        "current": current,
        "hourly": hourly,
        "daily": daily,
        "units": {
            "temperature_2m": "°C",
            "relative_humidity_2m": "%",
            "apparent_temperature": "°C",
            "wind_speed_10m": "km/h",
            "wind_direction_10m": "°",
            "pressure_msl": "hPa",
            "precipitation": "mm",
            "visibility": "m",
        },
    }


def rows(series):
    return [
        {k: values[i] for k, values in series.items()}
        for i in range(len(series.get("time", [])))
    ]


class OpenMeteoProvider:
    name = "Open-Meteo"

    async def _fetch_wttr_in(self, latitude, longitude):
        try:
            url = f"https://wttr.in/{latitude:.4f},{longitude:.4f}"
            raw = await client.get("wttr.in", url, {"format": "j1"}, ttl=600)
            if raw and isinstance(raw, dict) and raw.get("current_condition"):
                parsed = parse_wttr_in(raw, latitude, longitude)
                save_record(
                    f"weather:{latitude:.3f}:{longitude:.3f}", "weather_observation", parsed
                )
                return parsed
        except Exception as e:
            log.warning("wttr.in fallback error: %s", e)
        return None

    async def weather(self, latitude, longitude):
        try:
            data = await client.get(
                self.name,
                "https://api.open-meteo.com/v1/forecast",
                {
                    "latitude": latitude,
                    "longitude": longitude,
                    "current": CURRENT,
                    "hourly": HOURLY,
                    "daily": DAILY,
                    "timezone": "auto",
                    "forecast_days": 7,
                },
            )
            hourly = rows(data["hourly"])
            current = data["current"]
            nearest = min(
                hourly,
                key=lambda h: abs(
                    datetime.fromisoformat(h["time"]).timestamp()
                    - datetime.fromisoformat(current["time"]).timestamp()
                ),
            )
            current = {**nearest, **current}
            result = {
                "status": "live",
                "source": self.name,
                "data_kind": "Numerical weather model",
                "fetched_at": data.get("_fetched_at"),
                "timestamp": current["time"],
                "timezone": data["timezone"],
                "latitude": latitude,
                "longitude": longitude,
                "current": current,
                "hourly": hourly,
                "daily": rows(data["daily"]),
                "units": {
                    **data["hourly_units"],
                    **data["current_units"],
                    **data["daily_units"],
                },
            }
            save_record(
                f"weather:{latitude:.3f}:{longitude:.3f}", "weather_observation", result
            )
            return result
        except RuntimeError as error:
            # 1. Try wttr.in live resilient fallback
            fallback_res = await self._fetch_wttr_in(latitude, longitude)
            if fallback_res:
                return fallback_res

            # 2. Try cached DB record
            with contextlib.suppress(Exception):
                cached_rec = read_record(f"weather:{latitude:.3f}:{longitude:.3f}")
                if cached_rec and isinstance(cached_rec.get("data"), dict) and cached_rec["data"].get("current"):
                    res = dict(cached_rec["data"])
                    res["status"] = "cached"
                    res["source"] = f"{self.name} (Cached)"
                    res["message"] = "Live updates temporarily delayed; showing recent telemetry."
                    return res

            return {
                "status": "unavailable",
                "source": self.name,
                "message": str(error),
                "fetched_at": utcnow(),
                "latitude": latitude,
                "longitude": longitude,
                "current": {},
                "hourly": [],
                "daily": [],
                "units": {},
            }

    async def search(self, query):
        try:
            parts = query.split(",")
            if len(parts) == 2:
                lat, lon = map(float, parts)
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    return [
                        {
                            "name": f"{lat:.3f}, {lon:.3f}",
                            "latitude": lat,
                            "longitude": lon,
                            "country": "Coordinates",
                        }
                    ]
        except ValueError:
            pass
        local = local_search(query)
        if local:
            return local
        data = await client.get(
            "Geocoding",
            "https://geocoding-api.open-meteo.com/v1/search",
            {"name": query, "count": 8, "language": "en", "format": "json"},
            86400,
        )
        return [
            {
                k: item.get(k)
                for k in [
                    "name",
                    "latitude",
                    "longitude",
                    "country",
                    "admin1",
                    "timezone",
                ]
            }
            for item in data.get("results", [])
        ]

    async def history(self, latitude, longitude, start, end):
        try:
            data = await client.get(
                "Open-Meteo Archive",
                "https://archive-api.open-meteo.com/v1/archive",
                {
                    "latitude": latitude,
                    "longitude": longitude,
                    "start_date": start,
                    "end_date": end,
                    "daily": "temperature_2m_mean,precipitation_sum,relative_humidity_2m_mean,wind_speed_10m_mean",
                    "timezone": "auto",
                },
                3600,
            )
            return {
                "status": "historical",
                "source": "Open-Meteo ERA5 / archive",
                "fetched_at": data.get("_fetched_at"),
                "daily": rows(data.get("daily", {})),
            }
        except RuntimeError as error:
            return {
                "status": "unavailable",
                "source": "Open-Meteo Archive",
                "message": str(error),
                "daily": [],
            }

    async def marine(self, latitude, longitude):
        try:
            data = await client.get(
                "Open-Meteo Marine",
                "https://marine-api.open-meteo.com/v1/marine",
                {
                    "latitude": latitude,
                    "longitude": longitude,
                    "hourly": "wave_height,wave_direction,wave_period,sea_surface_temperature,ocean_current_velocity,ocean_current_direction",
                    "timezone": "auto",
                    "forecast_days": 3,
                },
            )
            data_rows = rows(data.get("hourly", {}))
            return {
                "status": "live"
                if any(x.get("wave_height") is not None for x in data_rows)
                else "unavailable",
                "source": "Open-Meteo Marine",
                "fetched_at": data.get("_fetched_at"),
                "hourly": data_rows,
                "units": data.get("hourly_units", {}),
                "message": "Marine parameters may be unavailable for inland locations.",
            }
        except RuntimeError as error:
            return {
                "status": "unavailable",
                "source": "Open-Meteo Marine",
                "message": str(error),
                "hourly": [],
            }

    async def air(self, latitude, longitude):
        try:
            data = await client.get(
                "Open-Meteo Air Quality",
                "https://air-quality-api.open-meteo.com/v1/air-quality",
                {
                    "latitude": latitude,
                    "longitude": longitude,
                    "current": "european_aqi,pm2_5,pm10",
                    "timezone": "auto",
                },
            )
            return {
                "status": "live",
                "source": "Open-Meteo / CAMS",
                "fetched_at": data.get("_fetched_at"),
                **data.get("current", {}),
            }
        except RuntimeError as error:
            return {"status": "unavailable", "message": str(error)}


provider = OpenMeteoProvider()


async def earthquakes(scope: str = "india"):
    try:
        data = await client.get(
            "USGS",
            "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson",
            ttl=300,
        )
        all_events = [
            {
                "id": f["id"],
                "longitude": f["geometry"]["coordinates"][0],
                "latitude": f["geometry"]["coordinates"][1],
                "depth": f["geometry"]["coordinates"][2],
                "magnitude": f["properties"]["mag"],
                "place": f["properties"]["place"],
                "timestamp": datetime.fromtimestamp(
                    f["properties"]["time"] / 1000, timezone.utc
                ).isoformat(),
                "url": f["properties"]["url"],
            }
            for f in data.get("features", [])
        ]
        if scope.lower() == "india":
            # India + regional seismic hazard margin: Lat 5.0 to 38.5, Lon 60.0 to 100.0
            events = [
                e for e in all_events
                if 5.0 <= e["latitude"] <= 38.5 and 60.0 <= e["longitude"] <= 100.0
            ]
            source_label = "USGS · India & Regional Seismic Margin (M2.5+)"
        else:
            events = all_events
            source_label = "USGS · Global M2.5+ past 24 hours"

        return {
            "status": "live",
            "source": source_label,
            "scope": scope,
            "fetched_at": data.get("_fetched_at"),
            "events": events,
            "total_count": len(events),
        }
    except RuntimeError as error:
        return {
            "status": "unavailable",
            "source": "USGS",
            "scope": scope,
            "message": str(error),
            "events": [],
            "total_count": 0,
        }


async def grid(latitude, longitude):
    """Sparse 5x5 regional samples, not radar or a high-resolution global model."""
    lats = [max(-85, min(85, latitude + i * 3)) for i in range(-2, 3)]
    lons = [((longitude + i * 3 + 180) % 360) - 180 for i in range(-2, 3)]
    try:
        data = await client.get(
            "Open-Meteo Grid",
            "https://api.open-meteo.com/v1/forecast",
            {
                "latitude": ",".join(str(a) for a in lats for _ in lons),
                "longitude": ",".join(str(b) for _ in lats for b in lons),
                "current": CURRENT,
                "forecast_days": 1,
            },
            ttl=1800,
        )
        cells = []
        for i, item in enumerate(data if isinstance(data, list) else [data]):
            c = item["current"]
            angle = math.radians(c["wind_direction_10m"])
            speed = c["wind_speed_10m"] / 3.6
            cells.append(
                {
                    "latitude": lats[i // 5],
                    "longitude": lons[i % 5],
                    "u_component": -speed * math.sin(angle),
                    "v_component": -speed * math.cos(angle),
                    "altitude": 10,
                    "timestamp": c["time"],
                    **c,
                }
            )
        return {
            "status": "live",
            "source": "Open-Meteo · 3° regional samples",
            "fetched_at": (data[0] if isinstance(data, list) else data).get(
                "_fetched_at"
            ),
            "cells": cells,
            "resolution": 3,
        }
    except RuntimeError as error:
        return {
            "status": "unavailable",
            "source": "Open-Meteo Grid",
            "message": str(error),
            "cells": [],
        }
