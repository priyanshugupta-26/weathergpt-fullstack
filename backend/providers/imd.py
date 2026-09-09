"""Official IMD v1 adapters. Catalog verified 2026-09-09.
https://api.imd.gov.in/public/api_reference.html
Warning colors deliberately differ between district warning and nowcast products.
"""
import asyncio
import hashlib
import math
import re
import time
from datetime import datetime, timedelta, timezone
import httpx
from ..config import settings

UTC = timezone.utc
IST = timezone(timedelta(hours=5, minutes=30))
CATALOG = {
    "current": "current_wx", "forecast": "cityforecastloc",
    "stations": "cityforecast_mapping", "aws": "aws_data",
    "aws_mapping": "aws_data_mapping", "nowcast": "districtnowcast",
    "warnings": "districtwarning", "subdivision_warnings": "subdivisionwarning",
    "rainfall": "districtrainfall", "state_rainfall": "staterainfall",
    "rainfall_forecast": "subdivision_rainfall_forecast",
    "district_rainfall_forecast": "state_district_rainfall_forecast",
    "qpf": "basinqpf", "cyclone": "cyclone_track", "cyclone_wind": "cyclone_wind",
    "cyclone_cone": "cyclone_cou", "marine": "seabulletin",
    "coastal": "coastalbulletin", "port": "portwarning", "sunmoon": "sunmoon",
}
# Listed in the public catalog but endpoint contracts are not published there.
RESTRICTED = {"radar", "lightning", "agromet", "fishermen"}
WARNING_NAMES = {2: "Heavy rain", 3: "Heavy snow", 4: "Thunderstorm and lightning",
                 5: "Hailstorm", 6: "Dust storm", 7: "Dust raising winds", 8: "Strong wind",
                 9: "Heat wave", 10: "Hot day", 11: "Warm night", 12: "Cold wave",
                 13: "Cold day", 14: "Frost", 15: "Fog", 16: "Very heavy rain",
                 17: "Extremely heavy rain"}
DISTRICT_COLORS = {1: ("red", "SEVERE"), 2: ("orange", "WARNING"),
                   3: ("yellow", "WATCH"), 4: ("green", "INFO")}
NOWCAST_COLORS = {1: ("green", "INFO"), 2: ("yellow", "WATCH"),
                  3: ("orange", "WARNING"), 4: ("red", "SEVERE")}


def stamp():
    return datetime.now(UTC).isoformat()


def value(row, *names):
    clean = {re.sub(r"[^a-z0-9]", "", str(k).lower()): v for k, v in row.items()}
    for key in names:
        v = clean.get(re.sub(r"[^a-z0-9]", "", key.lower()))
        if v is not None and str(v).strip() not in ("", "NA", "N/A", "NIL", "--", "-", "null"):
            return v
    return None


def numeric(v):
    try:
        n = float(str(v).strip().rstrip("%"))
        return n if math.isfinite(n) and n not in (-999, -9999, 9999) else None
    except (TypeError, ValueError):
        return None


def timestamp(day, hour=None, zone=UTC):
    if not day:
        return None
    raw = str(day).strip()
    if hour is not None:
        h = str(hour).strip()
        if h.isdigit() and len(h) <= 4:
            h = h.zfill(4)
            h = h[:2] + ":" + h[2:]
        raw += " " + h
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d-%m-%Y %H:%M",
                "%d.%m.%y/%H%M", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=zone).astimezone(UTC).isoformat()
        except ValueError:
            pass
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt.replace(tzinfo=dt.tzinfo or zone).astimezone(UTC).isoformat()
    except ValueError:
        return None


def freshness(ts):
    if not ts:
        return None
    return max(0, int((datetime.now(UTC) - datetime.fromisoformat(ts)).total_seconds()))


def records(payload):
    if isinstance(payload, list):
        if not all(isinstance(x, dict) for x in payload):
            raise ValueError("Invalid IMD record list")
        return payload
    if not isinstance(payload, dict):
        raise ValueError("Invalid IMD response")
    if payload.get("status") is False:
        raise ValueError("IMD reports unsuccessful response")
    if "data" in payload:
        data = payload["data"]
        if data is None:
            return []
        return records(data)
    if not payload:
        return []
    if all(isinstance(x, dict) for x in payload.values()):
        return list(payload.values())
    if any(value(payload, k) is not None for k in ("Station", "Station_Name", "District", "Date", "SUBDIV", "sunrise", "moonrise", "Basin", "Port Name", "Layer", "ID")):
        return [payload]
    raise ValueError("Unrecognized IMD response")


def normalize_observation(row, aws=False):
    ts = timestamp(value(row, "Date of Observation", "DATE"), value(row, "Time of Observation", "TIME"))
    cloud = numeric(value(row, "Nebulosity"))
    lat, lon = numeric(value(row, "Latitude", "lat")), numeric(value(row, "Longitude", "lon"))
    wind = numeric(value(row, "Wind Speed", "WIND_SPEED"))
    # AWS sample supplies wind values but no explicit units in the public reference.
    # Retain the raw value without silently treating it as km/h.
    return {
        "station_id": str(value(row, "Station Id", "Station_Code", "CALL_SIGN", "ID") or ""),
        "station_name": value(row, "Station", "Station_Name"),
        "district": value(row, "District"), "state": value(row, "State"),
        "latitude": lat if lat is not None and -90 <= lat <= 90 else None,
        "longitude": lon if lon is not None and -180 <= lon <= 180 else None,
        "timestamp": ts, "observation_time": ts, "source": "IMD", "source_type": "official",
        "data_kind": "Observation", "freshness_seconds": freshness(ts),
        "temperature_2m": numeric(value(row, "Temperature", "CURR_TEMP")),
        "apparent_temperature": numeric(value(row, "Feel Like")),
        "dew_point": numeric(value(row, "DEW_POINT_TEMP")),
        "relative_humidity_2m": numeric(value(row, "Humidity", "RH")),
        "pressure_msl": numeric(value(row, "M.S.L.P", "MSLP")),
        "wind_speed_10m": None if aws else wind, "wind_speed_raw": wind,
        "wind_speed_unit": "unspecified" if aws else "km/h",
        "wind_direction_10m": numeric(value(row, "Wind Direction")),
        "rainfall_24h": numeric(value(row, "Last 24 hrs Rainfall", "Past_24_hrs_Rainfall")),
        "cloud_cover": cloud * 12.5 if cloud is not None and 0 <= cloud <= 8 else None,
        "temperature_min": numeric(value(row, "MIN_TEMP")),
        "temperature_max": numeric(value(row, "MAX_TEMP")),
        "imd_weather_code": value(row, "Weather Code"),
        "weather_code": None,  # IMD present-weather codes are not Open-Meteo WMO forecast codes.
    }


def normalize_forecast(row):
    issued = timestamp(value(row, "Date"), zone=IST)
    days = []
    for i in range(1, 8):
        low = value(row, "Todays_Forecast_Min_temp" if i == 1 else f"Day_{i}_Min_temp")
        high = value(row, "Todays_Forecast_Max_Temp" if i == 1 else f"Day_{i}_Max_Temp")
        text = value(row, "Todays_Forecast" if i == 1 else f"Day_{i}_Forecast")
        if low is None and high is None and text is None:
            continue
        days.append({"day": i, "time": (datetime.fromisoformat(issued).astimezone(IST).date() + timedelta(days=i-1)).isoformat() if issued else None,
                     "temperature_2m_min": numeric(low), "temperature_2m_max": numeric(high),
                     "description": text, "source": "IMD", "data_kind": "Official forecast"})
    return {"station_id": str(value(row, "Station_Code") or ""),
            "station_name": value(row, "Station_Name"), "latitude": numeric(value(row, "Latitude")),
            "longitude": numeric(value(row, "Longitude")), "timestamp": issued, "daily": days,
            "sunrise": value(row, "Sunrise_time"), "sunset": value(row, "Sunset_time"),
            "moonrise": value(row, "Moonrise_time"), "moonset": value(row, "Moonset_time")}


def normalize_warnings(row, kind="warnings"):
    nowcast = kind == "nowcast"
    issue = timestamp(value(row, "Date", "date_obs"), value(row, "UTC", "toi"), zone=UTC if not nowcast else IST)
    area = str(value(row, "District", "Station", "SUBDIV") or "Unspecified area")
    output = []
    for day in ([1] if nowcast else range(1, 6)):
        original = value(row, "color" if nowcast else f"Day{day}_Color")
        colors = NOWCAST_COLORS if nowcast else DISTRICT_COLORS
        color, severity = colors.get(numeric(original), ("unknown", "UNKNOWN"))
        if str(original).lower() in ("#ff0000", "#ffa500", "#ffff00", "#7cfc00", "#008000"):
            color, severity = {"#ff0000": ("red", "SEVERE"), "#ffa500": ("orange", "WARNING"), "#ffff00": ("yellow", "WATCH"), "#7cfc00": ("green", "INFO"), "#008000": ("green", "INFO")}[str(original).lower()]
        codes = value(row, f"Day_{day}")
        names = [WARNING_NAMES[int(c)] for c in re.findall(r"\d+", str(codes or "")) if int(c) in WARNING_NAMES]
        description = value(row, "message" if nowcast else f"day{day}_warning") or ", ".join(names)
        if not description or color == "green":
            continue
        effective = (datetime.fromisoformat(issue) + timedelta(days=day-1)) if issue else None
        expiry = timestamp(value(row, "Date"), value(row, "Vupto"), zone=IST) if nowcast else (effective + timedelta(days=1)).isoformat() if effective else None
        if nowcast and expiry and issue and expiry < issue:
            expiry = (datetime.fromisoformat(expiry) + timedelta(days=1)).isoformat()
        uid = hashlib.sha256(f"{kind}:{area}:{issue}:{day}:{description}".encode()).hexdigest()[:24]
        output.append({"id": "imd:"+uid, "alert_type": next((h for h in ("Rain", "Lightning", "Thunderstorm", "Heat", "Cold", "Wind", "Fog", "Hail", "Cyclone", "Marine") if h.lower() in str(description).lower()), "Weather"),
                       "severity": severity, "color": color, "original_code": original,
                       "original_warning_codes": codes, "description": str(description),
                       "recommendation": "Follow the original IMD bulletin and local authority instructions.",
                       "location": area, "district": area if kind != "subdivision_warnings" else None,
                       "timestamp": issue, "effective": effective.isoformat() if effective else None,
                       "expires": expiry, "validity_basis": "provider time" if nowcast else "issue day + forecast day; exact end not supplied",
                       "source": "IMD", "data_source": "IMD OFFICIAL", "model_source": "Official nowcast" if nowcast else "Official warning",
                       "source_type": "official", "priority": 2 if nowcast else 1,
                       "url": "https://mausam.imd.gov.in/responsive/districtWiseWarningGIS.php",
                       "latitude": numeric(value(row, "Latitude")), "longitude": numeric(value(row, "Longitude"))})
    return output


def normalize_rainfall(row):
    return {"location": value(row, "District", "State", "SUBDIV"), "timestamp": timestamp(value(row, "Date", "date_obs")),
            "periods": {p.lower(): {"actual_mm": numeric(value(row, p+" Actual", p+" Acutual")),
                                   "normal_mm": numeric(value(row, p+" Normal")),
                                   "departure_percent": numeric(value(row, p+" Departure Per", p+" Departue Per")),
                                   "category": value(row, p+" Category"), "period": value(row, p+" Date")}
                        for p in ("Daily", "Weekly", "Monthly", "Cumulative")}}


def normalize_cyclones(payload):
    data = payload.get("data", payload) if isinstance(payload, dict) else {}
    groups = {}
    for kind in ("observed", "forecast"):
        for row in data.get(kind, []) if isinstance(data, dict) else []:
            lat, lon = numeric(value(row, "lat")), numeric(value(row, "lon"))
            ts = timestamp(value(row, "Date/Time"))
            if lat is None or lon is None or not ts or abs(lat) > 90 or abs(lon) > 180:
                continue
            name = str(value(row, "CYCLONE_NAME") or "Unnamed system")
            groups.setdefault(name, []).append({"latitude": lat, "longitude": lon,
                "timestamp": ts, "kind": kind, "wind_speed_kmh": numeric(value(row, "Mean MSW (kmph)")),
                "category": value(row, "Category"), "pressure_hpa": numeric(value(row, "Central Pressure"))})
    result = []
    for name, track in groups.items():
        track.sort(key=lambda p: p["timestamp"])
        observed = [p for p in track if p["kind"] == "observed"]
        latest = (observed or track)[-1]
        result.append({"id": "imd-cyclone:"+name, "name": name, "source": "IMD", "source_type": "official",
                       **latest, "track": track, "stale": freshness(latest["timestamp"]) > 86400})
    return result


def distance(a, b, c, d):
    r1, r2 = math.radians(a), math.radians(c)
    x = math.sin((r2-r1)/2)**2 + math.cos(r1)*math.cos(r2)*math.sin(math.radians(d-b)/2)**2
    return 6371 * 2 * math.asin(min(1, math.sqrt(x)))


class IMDProvider:
    def __init__(self):
        self.cache, self.states = {}, {}
        self.lock = asyncio.Lock()
        self.blocked_until = 0

    async def fetch(self, product, params=None):
        base = {"source": "IMD", "source_type": "official", "product": product,
                "retrieved_at": stamp(), "fetched_at": stamp(), "items": []}
        if product in RESTRICTED:
            return {**base, "status": "not_configured", "message": "Listed by IMD; an authorized endpoint contract is required. No endpoint is guessed."}
        if product not in CATALOG:
            raise ValueError("Unknown IMD product")
        if not settings.imd_enabled:
            return {**base, "status": "disabled", "message": "IMD disabled by configuration"}
        key = (product, str(sorted((params or {}).items())))
        ttl = 86400 if product in ("stations", "aws_mapping") else max(60, settings.imd_refresh_seconds)
        cached = self.cache.get(key)
        if cached and time.monotonic() - cached[0] < ttl:
            return cached[1]
        if self.blocked_until > time.monotonic():
            state = self.states.get("access", {})
            return {**base, "status": state.get("status", "unavailable"), "message": state.get("message", "IMD temporarily unavailable")}
        async with self.lock:
            cached = self.cache.get(key)
            if cached and time.monotonic() - cached[0] < ttl:
                return cached[1]
            if self.blocked_until > time.monotonic():
                return {**base, **self.states.get("access", {})}
            started = time.monotonic()
            headers = {}
            if settings.imd_token:
                headers[settings.imd_auth_header] = (settings.imd_auth_scheme + " " + settings.imd_token).strip()
            try:
                async with httpx.AsyncClient(timeout=min(settings.provider_timeout, 8), follow_redirects=False) as session:
                    r = await session.get(settings.imd_base_url.rstrip("/") + "/api/v1/" + CATALOG[product], params=params, headers=headers)
                if r.status_code in (401, 403, 429):
                    state = {401: "authentication_required", 403: "access_denied", 429: "rate_limited"}[r.status_code]
                    message = {401: "IMD authentication required", 403: "IMD denied access; authorization or IP approval may be required", 429: "IMD rate limit reached"}[r.status_code]
                    if "whitelist" in r.text[:2000].lower():
                        state, message = "ip_whitelist_required", "IMD reports IP whitelist required"
                    self.states["access"] = {"status": state, "message": message}
                    self.blocked_until = time.monotonic() + 300
                    result = {**base, **self.states["access"]}
                else:
                    r.raise_for_status()
                    payload = r.json()
                    if product == "cyclone":
                        items = normalize_cyclones(payload)
                    elif product in ("cyclone_wind", "cyclone_cone"):
                        items = [{"geometry": payload.get("data"), "timestamp": None,
                                  "validity": "Not supplied; do not display as active without a matching current cyclone"}]
                    else:
                        rows = records(payload)
                        if product in ("current", "aws"):
                            items = [normalize_observation(x, product == "aws") for x in rows]
                        elif product == "forecast":
                            items = [normalize_forecast(x) for x in rows]
                        elif product in ("warnings", "nowcast", "subdivision_warnings"):
                            items = [a for x in rows for a in normalize_warnings(x, product)]
                        elif product in ("rainfall", "state_rainfall"):
                            items = [normalize_rainfall(x) for x in rows]
                        else:
                            items = [{"fields": {re.sub(r"[^a-z0-9]+", "_", str(k).lower()).strip("_"): v for k, v in x.items()}} for x in rows]
                    result = {**base, "status": "available", "items": items,
                              "message": "No current data" if not items else None}
            except (httpx.HTTPError, ValueError, TypeError, KeyError) as error:
                result = {**base, "status": "unavailable", "message": "IMD data could not be retrieved or validated", "error": type(error).__name__}
                self.blocked_until = time.monotonic() + 60
                self.states["access"] = {"status": result["status"], "message": result["message"]}
            result["latency_ms"] = round((time.monotonic()-started)*1000)
            self.states[product] = {k: result.get(k) for k in ("status", "message", "retrieved_at", "latency_ms", "error")}
            self.cache[key] = (time.monotonic(), result)
            if len(self.cache) > 128:
                self.cache.pop(next(iter(self.cache)))
            return result

    def status(self):
        return {"configured": bool(settings.imd_token), "enabled": settings.imd_enabled,
                "status": self.states.get("access", {}).get("status", "healthy" if any(x.get("status") == "available" for x in self.states.values()) else "not_checked"),
                "products": self.states, "catalog": list(CATALOG), "restricted_products": sorted(RESTRICTED),
                "documentation": "https://api.imd.gov.in/public/api_reference.html"}

    async def nearby(self, lat, lon):
        data = await self.fetch("forecast")
        stations = [x for x in data["items"] if x.get("latitude") is not None and x.get("longitude") is not None]
        if not stations:
            return None
        station = min(stations, key=lambda x: distance(lat, lon, x["latitude"], x["longitude"]))
        km = distance(lat, lon, station["latitude"], station["longitude"])
        if km > 50:
            return None
        current = await self.fetch("current", {"id": station["station_id"]})
        observation = next(iter(current["items"]), None)
        return {"station": station, "observation": observation, "distance_km": round(km, 1)}


class IMDRadarProvider:
    async def fetch(self):
        return await imd.fetch("radar")


class IMDLightningProvider:
    async def fetch(self):
        return await imd.fetch("lightning")


imd = IMDProvider()
