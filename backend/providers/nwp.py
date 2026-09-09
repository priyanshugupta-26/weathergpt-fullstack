"""Public GFS via Open-Meteo; explicit normalized-file interface for local WRF output."""
import json
from pathlib import Path
from .weather import client, rows, HOURLY
from ..config import settings


class NWPProvider:
    name = "NWP"
    async def forecast(self, latitude, longitude):
        raise NotImplementedError


class GFSProvider(NWPProvider):
    name = "NOAA GFS via Open-Meteo"
    async def forecast(self, latitude, longitude):
        try:
            data = await client.get(self.name, "https://api.open-meteo.com/v1/gfs", {
                "latitude": latitude, "longitude": longitude,
                "hourly": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,wind_direction_10m,pressure_msl",
                "forecast_days": 3, "timezone": "UTC"}, ttl=1800)
            return {"status": "available", "source": self.name, "source_type": "nwp", "timezone": "UTC",
                    "hourly": rows(data["hourly"]), "units": data.get("hourly_units", {}), "retrieved_at": data.get("_fetched_at")}
        except (RuntimeError, KeyError, TypeError):
            return {"status": "unavailable", "source": self.name, "hourly": []}


class WRFProvider(NWPProvider):
    name = "WRF"
    async def forecast(self, latitude, longitude):
        if not settings.wrf_data_path:
            return {"status": "not_configured", "source": "WRF", "message": "Adapter ready; no local WRF run configured", "hourly": []}
        try:
            path = Path(settings.wrf_data_path)
            if path.stat().st_size > 5_000_000:
                raise ValueError("WRF export too large")
            data = json.loads(path.read_text())
            if abs(data["latitude"]-latitude) > 0.05 or abs(data["longitude"]-longitude) > 0.05:
                raise ValueError("No matching WRF grid point")
            if not data.get("run_time") or not isinstance(data.get("hourly"), list):
                raise ValueError("Missing WRF metadata")
            return {**data, "status": "available", "source": "WRF", "source_type": "nwp"}
        except (OSError, ValueError, KeyError, TypeError):
            return {"status": "unavailable", "source": "WRF", "hourly": []}
