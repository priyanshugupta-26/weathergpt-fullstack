import asyncio
import httpx


async def main():
    urls = [
        (
            "geocoding",
            "https://geocoding-api.open-meteo.com/v1/search",
            {"name": "Mumbai", "count": 3},
        ),
        (
            "air",
            "https://air-quality-api.open-meteo.com/v1/air-quality",
            {"latitude": 25.5, "longitude": 85.1, "current": "european_aqi,pm2_5,pm10"},
        ),
        (
            "marine",
            "https://marine-api.open-meteo.com/v1/marine",
            {
                "latitude": 18.6,
                "longitude": 72.5,
                "hourly": "wave_height,wave_direction,wave_period,sea_surface_temperature,ocean_current_velocity,ocean_current_direction",
                "forecast_days": 3,
            },
        ),
    ]
    async with httpx.AsyncClient(timeout=20) as client:
        for name, url, params in urls:
            try:
                r = await client.get(url, params=params)
                print(name, r.status_code, r.text[:450])
            except Exception as e:
                print(name, type(e).__name__, str(e))


asyncio.run(main())
