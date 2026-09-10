"""
Whitelisted, validated weather and domain intelligence tools.
Guaranteed safety: No arbitrary model-directed execution, no shell/SQL injection.
"""
from datetime import date, timedelta
from typing import Any
from pydantic import BaseModel, Field, ConfigDict, model_validator
from ..providers.engine import weather_engine
from ..providers.weather import earthquakes
from ..providers.imd import imd
from ..services.alerts import alerts_service
from ..services.rag import knowledge_base
from ..ml.registry import model_registry
from ..ml.features import MLFeatureBuilder, feature_registry


class ToolArguments(BaseModel):
    model_config = ConfigDict(extra="ignore")
    latitude: float = Field(25.5941, ge=-90, le=90)
    longitude: float = Field(85.1376, ge=-180, le=180)
    start: date | None = None
    end: date | None = None
    query: str | None = None
    hours: int | None = Field(default=48, ge=1, le=168)
    days: int | None = Field(default=7, ge=1, le=16)
    radius_km: float | None = Field(default=1000, ge=1, le=5000)

    @model_validator(mode="after")
    def validate_dates(self):
        if self.start and self.end:
            if self.end < self.start or (self.end - self.start).days > 365 * 30:
                raise ValueError("Invalid archive date range")
        return self


class WeatherToolRouter:
    names = {
        "get_current_weather",
        "get_hourly_forecast",
        "get_daily_forecast",
        "get_forecast",
        "get_air_quality",
        "get_marine",
        "get_earthquakes",
        "get_earthquake_data",
        "get_climate_history",
        "get_historical_weather",
        "get_climate_statistics",
        "get_active_disaster_alerts",
        "get_ndma_cap_alerts",
        "get_weather_ml_prediction",
        "get_disaster_ml_prediction",
        "get_gfs_forecast",
        "get_nwp_profile",
        "get_imd_current",
        "get_imd_current_weather",
        "get_imd_warning",
        "get_imd_nowcast",
        "get_imd_city_forecast",
        "get_imd_rainfall",
        "get_imd_cyclone",
        "get_imd_cyclone_data",
        "get_imd_marine",
        "get_imd_marine_warning",
        "get_imd_agromet",
        "retrieve_agriculture_knowledge",
        "retrieve_marine_knowledge",
        "retrieve_aviation_knowledge",
    }

    async def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name not in self.names:
            raise ValueError(f"Tool '{name}' is not allowed or whitelisted.")

        args = ToolArguments.model_validate(arguments or {})
        lat, lon = args.latitude, args.longitude

        # 1. Core Weather
        if name in ("get_current_weather", "get_forecast"):
            return await weather_engine.weather(lat, lon)

        if name == "get_hourly_forecast":
            w = await weather_engine.weather(lat, lon)
            return {
                "location": {"latitude": lat, "longitude": lon},
                "hourly": (w.get("hourly") or [])[:args.hours or 48],
                "source": w.get("source"),
                "timestamp": w.get("timestamp"),
            }

        if name == "get_daily_forecast":
            w = await weather_engine.weather(lat, lon)
            return {
                "location": {"latitude": lat, "longitude": lon},
                "daily": (w.get("daily") or [])[:args.days or 7],
                "source": w.get("source"),
                "timestamp": w.get("timestamp"),
            }

        # 2. Environmental & Marine
        if name == "get_air_quality":
            return await weather_engine.air(lat, lon)

        if name in ("get_marine", "get_imd_marine", "get_imd_marine_warning"):
            marine_data = await weather_engine.marine(lat, lon)
            return marine_data

        # 3. Earthquakes (Filtered for India / nearby relevance)
        if name in ("get_earthquakes", "get_earthquake_data"):
            all_quakes = await earthquakes()
            # Filter for events within India / South Asia bounds or radius
            events = all_quakes.get("events", [])
            india_events = [
                e for e in events
                if 5.0 <= e.get("latitude", 0) <= 38.5 and 60.0 <= e.get("longitude", 0) <= 100.0
            ]
            return {
                **all_quakes,
                "events": india_events,
                "total_regional": len(india_events),
                "scope": "India & nearby region",
            }

        # 4. Disaster & CAP Alerts
        if name in ("get_active_disaster_alerts", "get_ndma_cap_alerts"):
            from ..providers.cap import cap_provider
            w = await weather_engine.weather(lat, lon)
            rule_alerts = alerts_service.evaluate(w)
            cap_alerts = await cap_provider.refresh()
            return {
                "threshold_alerts": rule_alerts,
                "cap_alerts": cap_alerts,
                "source": "NDMA Sachet CAP & IMD Early Warning Screening",
            }

        # 5. IMD Official Products
        imd_map = {
            "get_imd_current": "current",
            "get_imd_current_weather": "current",
            "get_imd_warning": "warnings",
            "get_imd_nowcast": "nowcast",
            "get_imd_city_forecast": "forecast",
            "get_imd_rainfall": "rainfall",
            "get_imd_cyclone": "cyclone",
            "get_imd_cyclone_data": "cyclone",
            "get_imd_agromet": "agromet",
        }
        if name in imd_map:
            return await imd.fetch(imd_map[name])

        # 6. WeatherGPT Own ML Prediction & Feature Inference
        if name == "get_weather_ml_prediction":
            champ = model_registry.active_champion or model_registry.load_active_champion()
            if not champ:
                return {"status": "unavailable", "message": "ML model champion not loaded"}
            w = await weather_engine.weather(lat, lon)
            obs = w.get("current", {})
            features = MLFeatureBuilder.build_features_from_obs(obs, {}, feature_registry)
            res = model_registry.predict(features)
            return {
                "status": "live",
                "model_version": champ.version,
                "algorithm": champ.metadata.get("algorithm", "HistGradientBoosting"),
                "horizon": "next_1_hour",
                "prediction": res.get("prediction", {}) if res else {},
            }

        if name == "get_disaster_ml_prediction":
            w = await weather_engine.weather(lat, lon)
            obs = w.get("current", {})
            return alerts_service.prediction(obs)

        # 7. GFS Forecast & Atmospheric Profile
        if name in ("get_gfs_forecast", "get_nwp_profile"):
            from ..providers.gfs import gfs_provider
            return await gfs_provider.get_forecast(lat, lon)

        # 8. Historical Climate & Reanalysis
        if name in ("get_climate_history", "get_historical_weather", "get_climate_statistics"):
            if not args.start or not args.end:
                start_date = (date.today() - timedelta(days=30)).isoformat()
                end_date = (date.today() - timedelta(days=5)).isoformat()
            else:
                start_date = args.start.isoformat()
                end_date = args.end.isoformat()
            hist = await weather_engine.history(lat, lon, start_date, end_date)
            return hist

        # 9. Sector RAG Retrieval
        q = args.query or ""
        if name == "retrieve_agriculture_knowledge":
            return {"chunks": knowledge_base.retrieve(q, sector="agriculture")}
        if name == "retrieve_marine_knowledge":
            return {"chunks": knowledge_base.retrieve(q, sector="marine")}
        if name == "retrieve_aviation_knowledge":
            return {"chunks": knowledge_base.retrieve(q, sector="aviation")}

        raise ValueError(f"Unhandled tool '{name}'")


tools = WeatherToolRouter()
