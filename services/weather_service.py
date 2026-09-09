import math
from datetime import datetime, timezone
import httpx

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

CITIES = [
    {"name":"New Delhi","lat":28.6139,"lon":77.2090},
    {"name":"Mumbai","lat":19.0760,"lon":72.8777},
    {"name":"Kolkata","lat":22.5726,"lon":88.3639},
    {"name":"Chennai","lat":13.0827,"lon":80.2707},
    {"name":"Bengaluru","lat":12.9716,"lon":77.5946},
    {"name":"Hyderabad","lat":17.3850,"lon":78.4867},
    {"name":"Patna","lat":25.5941,"lon":85.1376},
    {"name":"Ahmedabad","lat":23.0225,"lon":72.5714},
    {"name":"Guwahati","lat":26.1445,"lon":91.7362},
    {"name":"Srinagar","lat":34.0837,"lon":74.7973},
    {"name":"Thiruvananthapuram","lat":8.5241,"lon":76.9366},
    {"name":"Bhubaneswar","lat":20.2961,"lon":85.8245},
]

CURRENT_FIELDS = ",".join([
    "temperature_2m","relative_humidity_2m","apparent_temperature","precipitation","rain",
    "weather_code","cloud_cover","pressure_msl","surface_pressure","wind_speed_10m",
    "wind_direction_10m","wind_gusts_10m"
])
HOURLY_FIELDS = ",".join([
    "temperature_2m","relative_humidity_2m","precipitation_probability","precipitation","rain",
    "pressure_msl","cloud_cover","visibility","wind_speed_10m","wind_direction_10m","wind_gusts_10m","uv_index"
])

def _mock(lat: float, lon: float):
    phase = math.sin(math.radians(lat + lon))
    temp = round(27 + 7 * phase, 1)
    wind = round(7 + 14 * abs(math.cos(math.radians(lon))), 1)
    rain = round(max(0, 3.5 * math.sin(math.radians(lat * 3))), 1)
    return {
        "time": datetime.now(timezone.utc).isoformat(),
        "temperature_2m": temp,
        "relative_humidity_2m": int(55 + 30 * abs(phase)),
        "apparent_temperature": round(temp + 1.8, 1),
        "precipitation": rain,
        "rain": rain,
        "weather_code": 3 if rain == 0 else 61,
        "cloud_cover": int(40 + 50 * abs(phase)),
        "pressure_msl": round(1007 + 6 * math.cos(math.radians(lat)), 1),
        "surface_pressure": round(998 + 6 * math.cos(math.radians(lat)), 1),
        "wind_speed_10m": wind,
        "wind_direction_10m": int((lon * 3) % 360),
        "wind_gusts_10m": round(wind * 1.45, 1),
        "source": "demo-fallback"
    }

async def current_weather(lat: float, lon: float):
    params = {"latitude":lat,"longitude":lon,"current":CURRENT_FIELDS,"timezone":"auto"}
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(FORECAST_URL, params=params)
            r.raise_for_status()
            data = r.json()
            current = data.get("current", {})
            current["source"] = "open-meteo"
            current["latitude"] = data.get("latitude", lat)
            current["longitude"] = data.get("longitude", lon)
            current["timezone"] = data.get("timezone")
            return current
    except Exception:
        d = _mock(lat, lon); d.update({"latitude":lat,"longitude":lon,"timezone":"UTC"}); return d

async def forecast(lat: float, lon: float, hours: int = 24):
    params = {"latitude":lat,"longitude":lon,"hourly":HOURLY_FIELDS,"forecast_days":3,"timezone":"auto"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(FORECAST_URL, params=params)
            r.raise_for_status()
            data = r.json()
            hourly = data.get("hourly", {})
            keys = list(hourly.keys())
            rows = []
            for i in range(min(hours, len(hourly.get("time", [])))):
                rows.append({k: hourly[k][i] for k in keys})
            return {"source":"open-meteo","rows":rows,"timezone":data.get("timezone")}
    except Exception:
        now = datetime.now(timezone.utc)
        base = _mock(lat, lon)
        rows = []
        for i in range(hours):
            rows.append({
                "time": now.isoformat(),
                "temperature_2m": round(base["temperature_2m"] + 3*math.sin(i/4),1),
                "relative_humidity_2m": max(30,min(95,base["relative_humidity_2m"]-i%8)),
                "precipitation_probability": int(min(100,base["rain"]*18+i%15)),
                "precipitation": base["rain"],"rain":base["rain"],
                "pressure_msl":base["pressure_msl"],"cloud_cover":base["cloud_cover"],
                "visibility":10000,"wind_speed_10m":base["wind_speed_10m"],
                "wind_direction_10m":base["wind_direction_10m"],"wind_gusts_10m":base["wind_gusts_10m"],"uv_index":4.2
            })
        return {"source":"demo-fallback","rows":rows,"timezone":"UTC"}
