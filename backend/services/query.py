import re
import json
from datetime import date, timedelta
from ..ai.router import ai_router
from ..ai.tools import tools
from ..providers.imd import imd
from .fusion import AlertFusionEngine, active
from ..providers.engine import weather_engine as provider
from ..config import settings
from ..ml.registry import model_registry
from ..ml.features import MLFeatureBuilder, feature_registry


class WeatherQueryEngine:
    def extract(self, message, language):
        text = message.lower()
        mappings = [
            ("cyclone", ["cyclone", "चक्रवात"]),
            ("earthquake", ["earthquake", "भूकंप"]),
            ("comparison", ["compare", "तुलना"]),
            ("air_quality", ["air quality", "aqi", "pollution"]),
            ("marine", ["marine", "waves", "sea"]),
            ("disaster_alert", ["warning", "alert", "lightning", "चेतावनी"]),
            ("historical", ["last month", "histor", "पिछले"]),
            ("agriculture", ["crop", "irrigat", "farmer", "किसान", "सिंचाई"]),
            ("rain", ["rain", "बारिश"]),
            ("wind", ["wind", "हवा"]),
            ("advisory", ["safe", "travel", "flood"]),
            ("forecast", ["tomorrow", "forecast", "कल"]),
        ]
        intent = next(
            (intent for intent, words in mappings if any(w in text for w in words)),
            "current_weather",
        )
        match = re.search(
            r"\b(?:in|near|for|to)\s+([a-zA-Z][a-zA-Z .-]*?)(?=\s+(?:tomorrow|today|this|next|on|at)|[?!,]|$)",
            message,
            re.I,
        )
        location = match.group(1).strip() if match else None
        if location and location.lower() in (
            "hindi",
            "english",
            "my area",
            "me",
            "here",
        ):
            location = None
        return {
            "intent": intent,
            "location": location,
            "time": "tomorrow" if "tomorrow" in text or "कल" in text else "today",
            "weather_parameter": intent,
            "language": "hi" if "hindi" in text or "हिंदी" in text else language,
            "use_case": intent if intent in ["agriculture", "advisory"] else "general",
        }

    async def prepare(self, request):
        query = self.extract(request.message, request.language)
        lat, lon, name = request.latitude, request.longitude, request.name
        if query["location"]:
            try:
                matches = await provider.search(query["location"])
            except RuntimeError:
                matches = []
            if not matches:
                return {
                    "message": f"I could not resolve “{query['location']}”. Select the location in search and ask again.",
                    "query": query,
                    "mode": "deterministic",
                    "weather": None,
                }
            lat, lon, name = (
                matches[0]["latitude"],
                matches[0]["longitude"],
                matches[0]["name"],
            )
        weather = await provider.weather(lat, lon)
        hi = query["language"] == "hi"
        c = weather["current"]
        if weather["status"] != "live":
            message = (
                "मौसम डेटा अभी उपलब्ध नहीं है। थोड़ी देर बाद फिर कोशिश करें।"
                if hi
                else "Weather data is temporarily unavailable. Please try again shortly. I cannot verify current conditions."
            )
        elif query["intent"] in ["cyclone", "earthquake"]:
            message = (
                "चक्रवात की आधिकारिक जानकारी यहाँ उपलब्ध नहीं है। भूकंप की रिपोर्ट ग्लोब पर USGS स्रोत में देखें।"
                if hi
                else "Cyclone warnings are not connected. For earthquake reports, select the USGS earthquake layer on the globe. Missing data does not mean there is no hazard."
            )
        elif query["intent"] == "historical":
            message = (
                "पुराने मौसम के लिए Climate पृष्ठ पर तारीखें चुनें।"
                if hi
                else "Open Climate and select a date range to inspect actual historical data. I have not calculated a comparison from this question."
            )
        elif query["time"] == "tomorrow" and len(weather["daily"]) > 1:
            d = weather["daily"][1]
            message = (
                f"**{name} — कल**\n\nतापमान {d['temperature_2m_min']}–{d['temperature_2m_max']} °C। बारिश की संभावना {d['precipitation_probability_max']}%, कुल वर्षा {d['precipitation_sum']} mm।"
                if hi
                else f"**{name} · Tomorrow**\n\nExpect {d['temperature_2m_min']}–{d['temperature_2m_max']} °C, with a {d['precipitation_probability_max']}% precipitation probability and {d['precipitation_sum']} mm forecast precipitation. Maximum wind: {d['wind_speed_10m_max']} km/h."
            )
        else:
            message = (
                f"**{name} — वर्तमान मौसम**\n\nतापमान {c.get('temperature_2m')} °C, आर्द्रता {c.get('relative_humidity_2m')}%, हवा {c.get('wind_speed_10m')} km/h और वर्षा {c.get('precipitation')} mm।"
                if hi
                else f"**{name} · Current conditions**\n\nTemperature is {c.get('temperature_2m')} °C (feels like {c.get('apparent_temperature')} °C). Humidity is {c.get('relative_humidity_2m')}%, wind is {c.get('wind_speed_10m')} km/h from {c.get('wind_direction_10m')}°, and precipitation is {c.get('precipitation')} mm."
            )
        if query["intent"] == "agriculture" and c:
            message += (
                "\n\nसिंचाई से पहले मिट्टी की नमी और आने वाली बारिश जाँचें।"
                if hi
                else "\n\nCheck measured root-zone soil moisture and upcoming rainfall before irrigating. Avoid spraying during rain or strong wind; this is general decision support."
            )
        if query["intent"] == "advisory":
            message += (
                "\n\nयात्रा से पहले स्थानीय आधिकारिक चेतावनियाँ देखें। बाढ़ का जोखिम केवल मौसम से तय नहीं किया जा सकता।"
                if hi
                else "\n\nWeather alone cannot establish travel safety or flood risk. Check local official warnings and road conditions before departure."
            )
        evidence = {"weather": {k: weather.get(k) for k in ("status", "source", "timestamp", "timezone", "current", "daily", "official_observation", "official_forecast")}}
        sources = [{"name": weather["source"], "time": weather.get("timestamp"), "url": "https://open-meteo.com/"}]

        # Retrieve WeatherGPT Own ML Model 1-hour forecast
        champ = model_registry.active_champion or model_registry.load_active_champion()
        if champ and c:
            try:
                features_dict = MLFeatureBuilder.build_features_from_obs(c, {}, feature_registry)
                ml_res = model_registry.predict(features_dict)
                if ml_res and "prediction" in ml_res:
                    pred_data = ml_res["prediction"]
                    evidence["weathergpt_own_model"] = {
                        "source": f"WeatherGPT Own Model ({champ.version})",
                        "algorithm": champ.metadata.get("algorithm", "HistGradientBoosting"),
                        "horizon": "next_1_hour",
                        "predictions": pred_data,
                    }
                    sources.append({
                        "name": f"WeatherGPT Own Model ({champ.version})",
                        "time": weather.get("timestamp"),
                        "url": "/model-lab",
                    })
                    if any(w in text for w in ("next", "hour", "forecast", "predict", "कल", "भविष्यवाणी")):
                        message += (
                            f"\n\n**WeatherGPT Own Model ({champ.version}) Next-Hour Forecast:**\n"
                            f"- Temperature: {pred_data.get('temperature_2m', '—')} °C\n"
                            f"- Humidity: {pred_data.get('relative_humidity_2m', '—')}%\n"
                            f"- Wind: {pred_data.get('wind_speed_10m', '—')} km/h ({pred_data.get('wind_direction_10m', '—')}°)\n"
                            f"- Rain: {pred_data.get('precipitation', 0.0)} mm\n"
                            f"- Barometric Pressure: {pred_data.get('surface_pressure', '—')} hPa"
                        )
            except Exception:
                pass

        arguments = {"latitude": lat, "longitude": lon}
        intent = query["intent"]
        special = {"air_quality": "get_air_quality", "earthquake": "get_earthquake_data", "cyclone": "get_imd_cyclone_data", "marine": "get_marine", "agriculture": "get_imd_agromet", "disaster_alert": "get_imd_warning"}
        if intent in special:
            data = await tools.call(special[intent], arguments)
            if intent == "disaster_alert":
                data = {**data, "items": [a for a in data.get("items", []) if active(a) and AlertFusionEngine.matches(a, {"name": name, **arguments})]}
            evidence[intent] = data
            sources.append({"name": data.get("source", special[intent]), "time": data.get("fetched_at"), "url": "https://api.imd.gov.in/public/api_reference.html" if "imd" in special[intent] else "https://earthquake.usgs.gov/" if intent == "earthquake" else "https://open-meteo.com/"})
            if intent != "agriculture":
                message = f"**{name} · {intent.replace('_', ' ')}**\n\n" + self.describe(data, hi)
            elif data.get("items"):
                message += "\n\nIMD original advisory: " + self.describe(data, hi)
        if intent == "historical":
            dates = re.findall(r"\d{4}-\d{2}-\d{2}", request.message)
            if "last month" in request.message.lower():
                end = date.today().replace(day=1)-timedelta(days=1)
                dates = [end.replace(day=1).isoformat(), end.isoformat()]
            if len(dates) >= 2:
                try:
                    data = await tools.call("get_climate_history", {**arguments, "start": dates[0], "end": dates[1]})
                    evidence["history"] = data
                    rows = data.get("daily", [])
                    temps = [r["temperature_2m_mean"] for r in rows if r.get("temperature_2m_mean") is not None]
                    rain = [r["precipitation_sum"] for r in rows if r.get("precipitation_sum") is not None]
                    message = f"**{name} · {dates[0]} to {dates[1]}**\n\n{len(rows)} daily records. Mean temperature: {round(sum(temps)/len(temps),1) if temps else 'unavailable'} °C. Rainfall total: {round(sum(rain),1) if rain else 'unavailable'} mm. Source: {data.get('source')}."
                except ValueError:
                    message = "Use two ISO dates (YYYY-MM-DD), ending at least five days ago, over at most two years."
        if intent == "comparison":
            match = re.search(r"compare\s+(.+?)\s+(?:and|with)\s+(.+?)(?:\s+weather|\s+tomorrow|[?.]|$)", request.message, re.I)
            if match:
                comparison = []
                for city in match.groups():
                    found = await provider.search(city.strip())
                    if found:
                        w = await provider.weather(found[0]["latitude"], found[0]["longitude"])
                        comparison.append({"location": found[0]["name"], "source": w["source"], "timestamp": w.get("timestamp"), "current": w["current"], "tomorrow": w["daily"][1] if len(w["daily"]) > 1 else {}})
                evidence["comparison"] = comparison
                message = "| Location | Temperature °C | Wind km/h | Source |\n|---|---|---|---|\n" + "\n".join(f"| {c['location']} | {c['tomorrow'].get('temperature_2m_max', '—') if query['time']=='tomorrow' else c['current'].get('temperature_2m', '—')} | {c['tomorrow'].get('wind_speed_10m_max', '—') if query['time']=='tomorrow' else c['current'].get('wind_speed_10m', '—')} | {c['source']} |" for c in comparison)
        message += "\n\n" + ("स्रोत: " if hi else "Source: ") + weather["source"] + " · " + str(weather.get("timestamp") or "time unavailable") + " · " + str(weather.get("timezone", "UTC"))
        query.update(latitude=lat, longitude=lon, district=None, state=None, country=None,
                     time_range=query["time"], weather_variables=[query["weather_parameter"]],
                     sector=query["use_case"], urgency="unknown")
        return {
            "message": message, "query": query, "mode": "deterministic",
            "location": {"name": name, "latitude": lat, "longitude": lon},
            "weather": weather, "source": weather["source"], "sources": sources,
            "tool_context": evidence,
        }

    @staticmethod
    def describe(data, hi=False):
        if data.get("status") not in ("live", "available", "historical"):
            return ("डेटा उपलब्ध नहीं है। " if hi else "Data unavailable. ") + str(data.get("message") or data.get("status"))
        entries = data.get("items", data.get("events", data.get("hourly", [])))
        if not entries and "european_aqi" not in data:
            return "No matching current data. Missing warnings are not an all-clear."
        if "european_aqi" in data:
            return f"European AQI: {data.get('european_aqi', '—')}; PM2.5: {data.get('pm2_5', '—')} µg/m³. Source: {data.get('source')}"
        return "\n".join("- " + str(e.get("description") or e.get("place") or e.get("name") or json.dumps(e, ensure_ascii=False)) for e in entries[:5])

    async def answer(self, request):
        result = await self.prepare(request)
        if "tool_context" not in result:
            return result
        ai = await ai_router.generate({"message": request.message, "language": result["query"]["language"], "data": result.pop("tool_context"), "fallback": result["message"]})
        result.update(message=ai.text, mode=ai.provider, ai={"provider": ai.provider, "model": ai.model, "usage": ai.usage})
        return result


query_engine = WeatherQueryEngine()
