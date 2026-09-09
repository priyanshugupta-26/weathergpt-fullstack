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


def rows(series):
    return [
        {k: values[i] for k, values in series.items()}
        for i in range(len(series.get("time", [])))
    ]


class OpenMeteoProvider:
    name = "Open-Meteo"

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


async def earthquakes():
    try:
        data = await client.get(
            "USGS",
            "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson",
            ttl=300,
        )
        return {
            "status": "live",
            "source": "USGS · M2.5+ past 24 hours",
            "fetched_at": data.get("_fetched_at"),
            "events": [
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
                for f in data["features"]
            ],
        }
    except RuntimeError as error:
        return {
            "status": "unavailable",
            "source": "USGS",
            "message": str(error),
            "events": [],
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
