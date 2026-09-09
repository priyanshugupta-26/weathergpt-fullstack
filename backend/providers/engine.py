"""Preserve separate observation/forecast provenance at component level."""
from .weather import provider as openmeteo
from .imd import imd


class MultiSourceWeatherEngine:
    async def weather(self, latitude, longitude):
        result = dict(await openmeteo.weather(latitude, longitude))
        result.update(source_type="api_forecast", observation_time=result.get("timestamp"),
                      retrieved_at=result.get("fetched_at"))
        # Geographic box only limits attempts. Station distance establishes applicability.
        if 6 <= latitude <= 38 and 68 <= longitude <= 98:
            nearby = await imd.nearby(latitude, longitude)
            result["imd_status"] = imd.status()["status"]
            if nearby:
                obs = nearby["observation"]
                result["official_forecast"] = nearby["station"]
                result["official_station_distance_km"] = nearby["distance_km"]
                if obs:
                    result["official_observation"] = obs
                    if obs.get("freshness_seconds") is not None and obs["freshness_seconds"] < 10800:
                        result["model_current"] = result["current"]
                        result["current"] = {**obs, "time": obs["timestamp"]}
                        result["current_source"] = "IMD"
                        result["forecast_source"] = result["source"]
                        result["source"] = "IMD observation · Open-Meteo forecast"
                        result["timestamp"] = obs["timestamp"]
                        result["status"] = "live"
                        result["source_type"] = "official_observation_and_api_forecast"
        return result

    async def search(self, query):
        return await openmeteo.search(query)

    async def history(self, *args):
        return await openmeteo.history(*args)

    async def marine(self, *args):
        return await openmeteo.marine(*args)

    async def air(self, *args):
        return await openmeteo.air(*args)


weather_engine = MultiSourceWeatherEngine()
