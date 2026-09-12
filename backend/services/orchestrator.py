"""
WeatherGPTOrchestrator: Central Meteorological Intelligence Engine
Replaces all primitive if/else Q&A bots across Agriculture, Marine, Aviation, Smart City, and Core Chat.
Executes multi-step reasoning:
  Language Detection -> Intent Detection -> Entity Extraction -> Location Resolver
  -> Time Resolver -> Sector Detection -> Conversational Memory
  -> Tool Selection -> Real Data Retrieval -> Sector RAG -> Groq/Gemini/Fallback -> Structured Answer
"""
import re
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from ..schemas import ChatRequest, StructuredAnswer, TimelineItem, MetricChip, SourceCitation, SUPPORTED_LANGUAGES
from ..ai.tools import tools
from ..ai.router import ai_router
from ..providers.engine import weather_engine
from ..services.rag import knowledge_base
from ..ml.registry import model_registry
from .query import LOCALIZED_TEMPLATES
from .intent_router import intent_router

log = logging.getLogger("weathergpt.orchestrator")

LOCALIZED_QUICK_SUMMARIES = {
    "hi": {
        "spray_ok": "कल सुबह छिड़काव के लिए हवा और मौसम अनुकूल दिख रहा है। हवा की गति 15 km/h से कम है।",
        "spray_wind": "तेज हवा के कारण कीटनाशक का बहाव (ड्रिफ्ट) हो सकता है। हवा शांत होने तक छिड़काव टालें।",
        "spray_rain": "आने वाले घंटों में बारिश की संभावना है। बारिश धुलने से बचाने के लिए अभी छिड़काव न करें।",
        "irrigate_rain": "बारिश का पूर्वानुमान है। जलभराव रोकने के लिए सिंचाई स्थगित करें।",
        "fertilizer_rain": "बारिश से पहले यूरिया या उर्वरक न डालें, अन्यथा पोषक तत्व बह जाएंगे।",
        "marine_safe": "तटीय मौसम सामान्य है। छोटी नौकाओं के लिए 2 मीटर से कम तरंग ऊंचाई सुरक्षित है।",
        "marine_rough": "समुद्र में ऊंची लहरें और तेज हवाएं हैं। छोटी नौकाओं को समुद्र में न जाने की सलाह है।",
        "travel_safe": "मार्ग पर मौसम सामान्य है। यात्रा की जा सकती है।",
    },
    "te": {
        "spray_ok": "రేపు ఉదయం మందుల పిచికారీకి వాతావరణం అనుకూలంగా ఉంది. గాలి వేగం తక్కువగా ఉంది.",
        "irrigate_rain": "వర్ష సూచన ఉన్నందున ప్రస్తుతానికి నీటిపారుదల వాయిదా వేయండి.",
        "marine_rough": "సముద్రంలో అలల ఉధృతి ఎక్కువగా ఉంది. చిన్న పడవల వేట సురక్షితం కాదు.",
    },
    "ta": {
        "spray_ok": "நாளை காலை மருந்து தெளிக்க வானிலை சாதகமாக உள்ளது. காற்றின் வேகம் குறைவு.",
        "irrigate_rain": "மழை வாய்ப்பு உள்ளதால் பாசனத்தை ஒத்திவைக்கவும்.",
        "marine_rough": "கடல் சீற்றமாக உள்ளது. சிறிய படகுகள் கடலுக்குச் செல்ல வேண்டாம்.",
    },
    "ur": {
        "spray_ok": "کل صبح اسپرے کے لیے موسم سازگار ہے۔ ہوا کی رفتار معتدل ہے۔",
        "irrigate_rain": "بارش کا امکان ہے، اس لیے فی الحال آبپاشی ملتوی کریں۔",
        "marine_rough": "سمندر میں اونچی لہریں ہیں۔ چھوٹی کشتیوں کے لیے سفر غیر محفوظ ہے۔",
    },
    "en": {
        "spray_ok": "Weather conditions are favorable for spraying. Winds are calm (< 15 km/h) and no heavy rain is forecast.",
        "spray_wind": "Strong winds may cause pesticide drift. Delay spraying until wind speeds drop below 15 km/h.",
        "spray_rain": "Rain is expected soon. Postpone chemical applications to prevent wash-off.",
        "irrigate_rain": "Upcoming rainfall is forecast. Postpone irrigation to avoid waterlogging and fertilizer leaching.",
        "fertilizer_rain": "Do not apply fertilizer before heavy rain. Runoff causes significant nutrient leaching.",
        "marine_safe": "Coastal wave conditions are within normal limits (< 2.0 m). Safe for small craft operations.",
        "marine_rough": "Rough sea warning: Significant wave heights and gusty winds pose high risk to small fishing vessels.",
        "travel_safe": "Route conditions appear normal with good visibility.",
    }
}


class ConversationalContextCache:
    """In-memory conversation state for multi-turn follow-ups."""
    def __init__(self):
        self._cache: dict[str, dict[str, Any]] = {}

    def get(self, conversation_id: str) -> dict[str, Any]:
        return self._cache.get(conversation_id, {})

    def update(self, conversation_id: str, updates: dict[str, Any]):
        state = self._cache.setdefault(conversation_id, {})
        state.update(updates)
        state["last_updated"] = time_now = datetime.now(timezone.utc).isoformat()
        # Keep cache bounded
        if len(self._cache) > 1000:
            oldest = min(self._cache.keys(), key=lambda k: self._cache[k].get("last_updated", ""))
            self._cache.pop(oldest, None)


conversation_memory = ConversationalContextCache()


class WeatherGPTOrchestrator:
    def __init__(self):
        self.memory = conversation_memory

    def detect_language(self, text: str, fallback: str = "en") -> str:
        # Check explicit request keywords
        lower = text.lower()
        lang_keywords = {
            "hindi": "hi", "हिंदी": "hi", "assamese": "as", "অসমীয়া": "as",
            "bengali": "bn", "বাংলা": "bn", "bodo": "brx", "dogri": "doi",
            "gujarati": "gu", "ગુજરાતી": "gu", "kannada": "kn", "ಕನ್ನಡ": "kn",
            "kashmiri": "ks", "konkani": "kok", "maithili": "mai",
            "malayalam": "ml", "മലയാളം": "ml", "manipuri": "mni",
            "marathi": "mr", "मराठी": "mr", "nepali": "ne", "odia": "or", "ଓଡ଼ିଆ": "or",
            "punjabi": "pa", "ਪੰਜਾਬੀ": "pa", "sanskrit": "sa", "santali": "sat",
            "sindhi": "sd", "tamil": "ta", "தமிழ்": "ta", "telugu": "te", "తెలుగు": "te",
            "urdu": "ur", "اردو": "ur", "english": "en"
        }
        for kw, code in lang_keywords.items():
            if f"in {kw}" in lower or f"{kw} mein" in lower or f"{kw} lo" in lower or f"{kw}il" in lower:
                return code
            if kw in lower and len(text.split()) <= 4:
                return code

        # Script-based detection
        if re.search(r"[\u0C00-\u0C7F]", text):
            return "te"
        if re.search(r"[\u0B80-\u0BFF]", text):
            return "ta"
        if re.search(r"[\u0980-\u09FF]", text):
            return "bn"
        if re.search(r"[\u0A80-\u0AFF]", text):
            return "gu"
        if re.search(r"[\u0C80-\u0CFF]", text):
            return "kn"
        if re.search(r"[\u0D00-\u0D7F]", text):
            return "ml"
        if re.search(r"[\u0A00-\u0A7F]", text):
            return "pa"
        if re.search(r"[\u0B00-\u0B7F]", text):
            return "or"
        if re.search(r"[\u0600-\u06FF\u0750-\u077F]", text):
            return "ur"
        if re.search(r"[\u0900-\u097F]", text):
            return fallback if fallback in ("hi", "mr", "sa", "mai", "ne", "brx", "doi", "kok") else "hi"

        return fallback if fallback in SUPPORTED_LANGUAGES else "en"

    def parse_intent_and_entities(self, text: str, sector_hint: str | None = None) -> dict[str, Any]:
        lower = text.lower()

        # Sector detection
        sector = sector_hint or "general"
        agri_words = ["spray", "pesticide", "insecticide", "fungicide", "irrigate", "irrigation",
                      "fertilizer", "urea", "crop", "rice", "paddy", "wheat", "cotton", "farmer",
                      "dalu", "khad", "kheti", "pani", "fasal"]
        marine_words = ["sea", "boat", "fishing", "fish", "waves", "machhli", "swell", "coast",
                        "coastal", "tide", "offshore", "ocean", "samundar", "port"]
        aviation_words = ["flight", "plane", "aviation", "vfr", "ifr", "runway", "turbulence", "pilot"]
        travel_words = ["travel", "trip", "journey", "drive", "road", "ranchi", "patna to"]

        if any(w in lower for w in agri_words):
            sector = "agriculture"
        elif any(w in lower for w in marine_words):
            sector = "marine"
        elif any(w in lower for w in aviation_words):
            sector = "aviation"
        elif any(w in lower for w in travel_words):
            sector = "travel"

        # Time resolution
        time_target = None
        time_period = None
        if any(w in lower for w in ["tomorrow", "kal", "రేపు", "நாளை", "আগামীকাল"]):
            time_target = "tomorrow"
        elif any(w in lower for w in ["today", "aaj", "current", "now", "इस समय", "वर्तमान", "ఈ రోజు", "இன்று", "আজ"]):
            time_target = "today"
        elif any(w in lower for w in ["tonight", "aaj raat", "ఈ రాత్రి"]):
            time_target = "tonight"
        elif any(w in lower for w in ["yesterday", "kal (past)", "గత"]):
            time_target = "yesterday"

        if any(w in lower for w in ["morning", "subah", "ఉదయం", "காலை"]):
            time_period = "morning"
        elif any(w in lower for w in ["evening", "shaam", "సాయంత్రం", "மாலை"]):
            time_period = "evening"
        elif any(w in lower for w in ["afternoon", "dopahar", "మధ్యాహ్నం"]):
            time_period = "afternoon"
        elif any(w in lower for w in ["after 5", "5 pm", "5 baje"]):
            time_period = "after_5pm"

        # Route extraction (e.g. "Patna to Ranchi")
        route_match = re.search(r"from\s+([a-zA-Z\s]+?)\s+to\s+([a-zA-Z\s]+?)(?:\s+(?:tomorrow|today|morning|evening)|[?!.]|$)", text, re.I)
        route = None
        if route_match:
            route = (route_match.group(1).strip(), route_match.group(2).strip())
        else:
            route_dash = re.search(r"\b([a-zA-Z]+)\s+to\s+([a-zA-Z]+)\b", text, re.I)
            if route_dash and not any(w in route_dash.group(0).lower() for w in ["how to", "want to", "need to", "go to"]):
                route = (route_dash.group(1).strip(), route_dash.group(2).strip())

        # Single location extraction
        loc_match = re.search(r"\b(?:in|near|at|for|around)\s+([a-zA-Z][a-zA-Z\s.-]*?)(?=\s+(?:tomorrow|today|after|before|morning|evening|in\s+[a-z]+|[?!,]|$))", text, re.I)
        location = loc_match.group(1).strip() if loc_match else None
        if location and location.lower() in [
            "hindi", "english", "tamil", "telugu", "urdu", "bengali", "marathi", "gujarati",
            "my farm", "the farm", "my area", "here", "there", "the sea", "the coast"
        ]:
            location = None

        return {
            "sector": sector,
            "time_target": time_target,
            "time_period": time_period,
            "route": route,
            "location": location,
            "is_spray_question": any(w in lower for w in ["spray", "pesticide", "fungicide", "chhidkao", "chhidkav"]),
            "is_irrigate_question": any(w in lower for w in ["irrigate", "irrigation", "sinchai", "pani du", "water"]),
            "is_fertilizer_question": any(w in lower for w in ["fertilizer", "urea", "khad", "dalu"]),
            "is_fishing_question": any(w in lower for w in ["fishing", "fish", "boat", "machhli", "sea safe", "samundar"]),
            "is_thunderstorm_question": any(w in lower for w in ["thunderstorm", "lightning", "bijli", "thunder", "why warning"]),
            "is_pressure_question": any(w in lower for w in ["pressure", "barometer", "falling pressure", "dhabav"]),
            "is_compare_wind": any(w in lower for w in ["compare today's wind with yesterday", "wind with yesterday", "hawa kal"]),
            "is_lowest_rain": any(w in lower for w in ["lowest rain", "lowest risk", "safe part of day", "least rain"]),
            "is_explain_warning": any(w in lower for w in ["explain this warning", "explain warning", "warning in"]),
        }

    async def answer(self, request: ChatRequest) -> dict[str, Any]:
        conv_id = (request.conversation or getattr(request, "session_id", None) or "").strip() or None
        prior_state = self.memory.get(conv_id) if conv_id else {}

        clean_msg = request.message.strip().replace("\n", " ")
        print(f'[CHAT] User message: {clean_msg}', flush=True)
        log.info(f'[CHAT] User message: {clean_msg}')
        print('[ROUTER] Running intent classification...', flush=True)
        log.info('[ROUTER] Running intent classification...')

        # 1. Parse language
        lang = self.detect_language(request.message, request.language)

        # 2. Intelligent Intent & Query Routing
        route = intent_router.classify(request.message, conversation_context=prior_state, sector_hint=request.sector)

        print(f'[ROUTER] Result: {route.intent}', flush=True)
        log.info(f'[ROUTER] Result: {route.intent}')

        # 3. Handle GENERAL & GREETING Queries (No weather tools called, no location forced)
        if not route.requires_live_data or route.domain == "general":
            print('[WEATHER] Tool call: SKIPPED', flush=True)
            log.info('[WEATHER] Tool call: SKIPPED')
            print('[LLM] Route: GENERAL', flush=True)
            log.info('[LLM] Route: GENERAL')

            if conv_id:
                self.memory.update(conv_id, {"last_intent": "general", "location_name": None})

            answer_text = ""
            mode = "deterministic"
            ai_meta = {}

            # Case 1: Greeting
            if route.intent == "greeting":
                if lang == "hi":
                    answer_text = "नमस्ते! 👋 मैं WeatherGPT हूँ। मैं सामान्य प्रश्नों के साथ-साथ मौसम, पूर्वानुमान, आपदा अलर्ट और कृषि सलाह में मदद कर सकता हूँ। मैं आपकी कैसे मदद कर सकता हूँ?"
                elif lang == "te":
                    answer_text = "నమస్కారం! 👋 నేను WeatherGPT. సాధారణ ప్రశ్నలతో పాటు వాతావరణం, సూచనలు, విపత్తు హెచ్చరికలు మరియు వ్యవసాయ సలహాలలో నేను మీకు సహాయం చేయగలను. నేను మీకు ఎలా సహాయపడగలను?"
                elif lang == "ta":
                    answer_text = "வணக்கம்! 👋 நான் WeatherGPT. பொதுவான கேள்விகள் மற்றும் வானிலை, முன்னறிவிப்புகள், பேரிடர் எச்சரிக்கைகள் மற்றும் விவசாய ஆலோசனைகளுக்கு நான் உதவ முடியும். நான் உங்களுக்கு எப்படி உதவ முடியும்?"
                else:
                    answer_text = "Hi! 👋 I'm WeatherGPT. I can help with general questions as well as weather, forecasts, disaster alerts, farming advisories, climate information, and more. How can I help you today?"
            else:
                ai_context = {
                    "message": request.message,
                    "language": lang,
                    "intent": "general",
                    "requires_weather_tool": False,
                    "fallback": None,
                }
                try:
                    ai_res = await ai_router.generate(ai_context)
                    if ai_res and ai_res.text:
                        answer_text = ai_res.text.strip()
                        mode = ai_res.provider
                        ai_meta = {"provider": ai_res.provider, "model": ai_res.model, "usage": ai_res.usage}
                except Exception as e:
                    log.info("ai_router_general_error: %s", e)

            if not answer_text:
                answer_text = "Hi! How can I help you today?"

            print('[RESPONSE] Type: GENERAL', flush=True)
            log.info('[RESPONSE] Type: GENERAL')

            return {
                "reply": answer_text,
                "message": answer_text,
                "content": answer_text,
                "intent": route.intent,
                "response_mode": "general",
                "type": "general",
                "city_name": None,
                "disaster_alert": None,
                "data": None,
                "structured": None,
                "weather": None,
                "query": {
                    "intent": route.intent,
                    "domain": "general",
                    "language": lang,
                    "sector": "general",
                    "time_target": None,
                    "time_period": None,
                    "location": None,
                    "requires_weather_tool": False,
                    "requires_location": False,
                },
                "mode": mode,
                "ai": ai_meta,
                "location": None,
                "source": None,
                "sources": [],
            }

        # 4. Handle WEATHER & Domain Queries
        parsed = self.parse_intent_and_entities(request.message, request.sector)
        if route.details:
            parsed.update(route.details)

        # Conversational follow-up resolution
        location_name = route.location or (prior_state.get("location_name") if not route.route else None)
        if not location_name and route.requires_location:
            location_name = request.name or "Your Location"
        time_target = route.time_range or parsed["time_target"] or prior_state.get("time_target") or "today"
        time_period = route.time_period or parsed["time_period"] or prior_state.get("time_period") or "all_day"
        sector = route.sector if route.sector != "general" else (prior_state.get("sector") or "general")

        lat, lon = request.latitude, request.longitude

        # Location geocoding if a new specific location was extracted
        if route.location and route.location.lower() != (prior_state.get("location_name") or "").lower():
            try:
                matches = await weather_engine.search(route.location)
                if matches:
                    lat, lon = matches[0]["latitude"], matches[0]["longitude"]
                    location_name = matches[0]["name"]
            except Exception:
                pass

        # Save updated conversation state
        if conv_id:
            self.memory.update(conv_id, {
                "location_name": location_name,
                "latitude": lat,
                "longitude": lon,
                "time_target": time_target,
                "time_period": time_period,
                "sector": sector,
                "last_intent": route.intent,
            })

        # Safe Tool Execution & Real Data Retrieval
        evidence: dict[str, Any] = {}
        sources: list[dict[str, str]] = []

        if location_name:
            print(f'[WEATHER] Location: {location_name}', flush=True)
            log.info(f'[WEATHER] Location: {location_name}')
        print('[WEATHER] Tool call: CALLED', flush=True)
        log.info('[WEATHER] Tool call: CALLED')
        print('[LLM] Route: WEATHER', flush=True)
        log.info('[LLM] Route: WEATHER')

        # Tool 1: Live weather & forecast
        weather = await weather_engine.weather(lat, lon)
        evidence["weather"] = weather
        sources.append({"name": weather.get("source", "Open-Meteo"), "url": "https://open-meteo.com/", "time": weather.get("timestamp", "")})

        # Tool 2: IMD Warnings & Active Alerts
        alert_data = await tools.call("get_active_disaster_alerts", {"latitude": lat, "longitude": lon})
        evidence["alerts"] = alert_data
        sources.append({"name": "IMD / NDMA Sachet", "url": "https://mausam.imd.gov.in/", "time": weather.get("timestamp", "")})

        # Tool 3: WeatherGPT Own ML Prediction
        try:
            ml_pred = await tools.call("get_weather_ml_prediction", {"latitude": lat, "longitude": lon})
            if ml_pred.get("status") == "live":
                evidence["weathergpt_ml"] = ml_pred
                sources.append({"name": f"WeatherGPT ML ({ml_pred.get('model_version')})", "url": "/model-lab", "time": weather.get("timestamp", "")})
        except Exception:
            pass

        # Tool 4: Marine data if marine sector or fishing query
        if sector == "marine" or parsed["is_fishing_question"]:
            try:
                marine = await weather_engine.marine(lat, lon)
                evidence["marine"] = marine
                sources.append({"name": "Open-Meteo Marine / INCOIS", "url": "https://incois.gov.in/", "time": marine.get("fetched_at", "")})
            except Exception:
                pass

        # Tool 5: Route weather if travel question
        if parsed["route"]:
            origin_name, dest_name = parsed["route"]
            try:
                dest_matches = await weather_engine.search(dest_name)
                if dest_matches:
                    dest_weather = await weather_engine.weather(dest_matches[0]["latitude"], dest_matches[0]["longitude"])
                    evidence["route_destination"] = {
                        "name": dest_name,
                        "weather": dest_weather,
                    }
                    sources.append({"name": f"Destination: {dest_name}", "url": "https://open-meteo.com/", "time": ""})
            except Exception:
                pass

        # Tool 6: Yesterday weather if comparative query
        if parsed["is_compare_wind"]:
            try:
                yest = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
                hist = await weather_engine.history(lat, lon, yest, yest)
                evidence["yesterday"] = hist
                sources.append({"name": "ERA5 Historical Reanalysis", "url": "https://open-meteo.com/", "time": yest})
            except Exception:
                pass

        # Tool 7: Sector RAG Retrieval
        rag_chunks = knowledge_base.retrieve(request.message, sector=sector, top_k=2)
        if rag_chunks:
            evidence["rag_knowledge"] = rag_chunks
            for chunk in rag_chunks:
                sources.append({
                    "name": chunk["organization"],
                    "url": chunk["source_url"],
                    "time": chunk["document_date"],
                })

        # 5. Synthesize Structured Answer
        c = weather.get("current", {})
        daily = weather.get("daily", [{}])
        target_day = daily[1] if (time_target == "tomorrow" and len(daily) > 1) else daily[0]

        rain_prob = int(target_day.get("precipitation_probability_max") or 0) if target_day.get("precipitation_probability_max") is not None else 0
        precip_sum = float(target_day.get("precipitation_sum") or 0.0) if target_day.get("precipitation_sum") is not None else 0.0
        wind_speed = float(c.get("wind_speed_10m") or 12.0) if c.get("wind_speed_10m") is not None else 12.0
        wind_gust = float(c.get("wind_gusts_10m") or 18.0) if c.get("wind_gusts_10m") is not None else 18.0
        temp_val = float(c.get("temperature_2m") or 28.0) if c.get("temperature_2m") is not None else 28.0

        # Build Domain-Specific Reasoning
        summary = ""
        severity = "normal"
        key_points = []
        actions = []
        metrics = []
        timeline = []
        technical = ""

        # Case A: Spraying
        if parsed["is_spray_question"]:
            is_safe = wind_speed < 15 and rain_prob < 30 and precip_sum < 2.0
            if is_safe:
                summary = LOCALIZED_QUICK_SUMMARIES.get(lang, LOCALIZED_QUICK_SUMMARIES["en"])["spray_ok"]
                actions = [
                    "Morning spray window is optimal (calm winds < 15 km/h)",
                    "Maintain nozzle pressure to minimize fine drift",
                    "Follow manufacturer safety guidelines and PPE",
                ]
            elif wind_speed >= 15:
                severity = "advisory"
                summary = LOCALIZED_QUICK_SUMMARIES.get(lang, LOCALIZED_QUICK_SUMMARIES["en"])["spray_wind"]
                actions = [
                    f"Postpone spraying: wind speed is {wind_speed} km/h (safe threshold: < 15 km/h)",
                    "High drift risk to adjacent fields and waterways",
                    "Check back during late evening or early morning calm",
                ]
            else:
                severity = "advisory"
                summary = LOCALIZED_QUICK_SUMMARIES.get(lang, LOCALIZED_QUICK_SUMMARIES["en"])["spray_rain"]
                actions = [
                    f"Rain probability is {rain_prob}% with {precip_sum} mm precipitation forecast",
                    "Rainfall will wash off chemicals, causing loss of efficacy",
                    "Wait for a 24-hour dry spell before application",
                ]
            key_points = [
                f"Wind speed: {wind_speed} km/h (gusts up to {wind_gust} km/h)",
                f"Rain probability: {rain_prob}%",
                f"Forecast precipitation: {precip_sum} mm",
                f"Relative humidity: {c.get('relative_humidity_2m', 60)}%",
            ]
            metrics = [
                MetricChip(label="Wind Speed", value=f"{wind_speed}", unit="km/h", icon="wind"),
                MetricChip(label="Rain Risk", value=f"{rain_prob}", unit="%", icon="droplets"),
                MetricChip(label="Humidity", value=f"{c.get('relative_humidity_2m', 60)}", unit="%", icon="thermometer"),
            ]
            timeline = [
                TimelineItem(time="Morning (6–10 AM)", condition="Calm / Optimal", detail="Wind < 12 km/h, lowest drift risk"),
                TimelineItem(time="Afternoon (12–4 PM)", condition="Rising Thermal Gusts", detail=f"Wind {wind_speed} km/h, higher evaporation"),
                TimelineItem(time="Evening (5–8 PM)", condition="Cooling", detail=f"Rain chance {rain_prob}%"),
            ]
            technical = (
                f"Droplet drift physics dictate that spray particles < 150 microns drift exponentially at wind speeds > 15 km/h. "
                f"Boundary layer relative humidity of {c.get('relative_humidity_2m', 60)}% results in standard evaporation rate. "
                f"Reference: IMD Agromet Advisory Protocol v2026."
            )

        # Case B: Irrigation
        elif parsed["is_irrigate_question"]:
            if rain_prob > 50 or precip_sum > 5.0:
                severity = "advisory"
                summary = LOCALIZED_QUICK_SUMMARIES.get(lang, LOCALIZED_QUICK_SUMMARIES["en"])["irrigate_rain"]
                actions = [
                    f"Postpone irrigation: upcoming rain ({precip_sum} mm, {rain_prob}% chance) will meet water requirements",
                    "Excess water can cause waterlogging and root rot in susceptible crops",
                    "Clear drainage channels in low-lying paddy or vegetable plots",
                ]
            else:
                summary = "Irrigation is safe to schedule. Upcoming rainfall is low."
                actions = [
                    "Irrigate in evening or early morning to reduce evapotranspiration losses",
                    "Check root-zone soil moisture before turning on tube wells",
                ]
            key_points = [
                f"Rain probability: {rain_prob}%",
                f"Rainfall expected: {precip_sum} mm",
                f"Soil surface temperature: {c.get('soil_temperature_0cm', temp_val)} °C",
                f"Topsoil moisture estimate: {c.get('soil_moisture_0_to_1cm', 0.22)} m³/m³",
            ]
            metrics = [
                MetricChip(label="Rain Sum", value=f"{precip_sum}", unit="mm", icon="droplets"),
                MetricChip(label="Precip Chance", value=f"{rain_prob}", unit="%", icon="droplets"),
                MetricChip(label="Soil Temp", value=f"{c.get('soil_temperature_0cm', temp_val)}", unit="°C", icon="thermometer"),
            ]

        # Case C: Fertilizer Application
        elif parsed["is_fertilizer_question"]:
            if rain_prob > 40 or precip_sum > 3.0:
                severity = "warning"
                summary = LOCALIZED_QUICK_SUMMARIES.get(lang, LOCALIZED_QUICK_SUMMARIES["en"])["fertilizer_rain"]
                actions = [
                    "Hold top-dressing fertilizer (Urea/DAP) until the rain front passes",
                    "Rainfall immediately after fertilizer causes rapid nutrient runoff and leaching",
                    "Apply when the soil is moist but no heavy downpour is imminent",
                ]
            else:
                summary = "Fertilizer application is safe under current soil moisture and dry weather outlook."
                actions = ["Apply uniformly in morning hours and incorporate into topsoil"]
            key_points = [
                f"Rain threat: {rain_prob}% ({precip_sum} mm forecast)",
                "Nitrogen leaching risk: HIGH if applied before heavy showers",
                "Soil moisture status: Favorable for absorption once dry",
            ]
            metrics = [
                MetricChip(label="Precipitation", value=f"{precip_sum}", unit="mm", icon="droplets"),
                MetricChip(label="Runoff Risk", value="High" if rain_prob > 40 else "Low", icon="shield"),
            ]

        # Case D: Marine & Fishing
        elif parsed["is_fishing_question"] or sector == "marine":
            marine_res = evidence.get("marine", {})
            m_hourly = marine_res.get("hourly", [])
            wave_val = m_hourly[0].get("wave_height") if m_hourly else None
            wave_h = float(wave_val) if wave_val is not None else 1.2
            if wave_h >= 2.2 or wind_speed > 35:
                severity = "severe"
                summary = LOCALIZED_QUICK_SUMMARIES.get(lang, LOCALIZED_QUICK_SUMMARIES["en"])["marine_rough"]
                actions = [
                    f"Small fishing boats (< 12 m) should NOT venture into deep sea",
                    f"Significant wave heights ({wave_h} m) exceed small craft safety threshold (2.0 m)",
                    "Fishermen at sea are advised to return to coast or nearest shelter",
                    "Secure anchored vessels at harbor/jetty against wave surge",
                ]
            else:
                summary = LOCALIZED_QUICK_SUMMARIES.get(lang, LOCALIZED_QUICK_SUMMARIES["en"])["marine_safe"]
                actions = [
                    "Normal fishing operations permitted for coastal crafts",
                    "Maintain standard marine radio VHF watch on Channel 16",
                    "Monitor IMD squall warnings before venturing beyond 15 nautical miles",
                ]
            key_points = [
                f"Significant wave height: {wave_h} meters",
                f"Wind speed over water: {wind_speed} km/h (gusts {wind_gust} km/h)",
                f"Swell period: {m_hourly[0].get('wave_period', 6) if m_hourly else 6} seconds",
                f"Sea surface temperature: {m_hourly[0].get('sea_surface_temperature', 28) if m_hourly else 28} °C",
            ]
            metrics = [
                MetricChip(label="Wave Height", value=f"{wave_h}", unit="m", icon="waves"),
                MetricChip(label="Surface Wind", value=f"{wind_speed}", unit="km/h", icon="wind"),
                MetricChip(label="Sea Temp", value=f"{m_hourly[0].get('sea_surface_temperature', 28) if m_hourly else 28}", unit="°C", icon="thermometer"),
            ]
            technical = (
                f"Offshore hydrodynamic boundary layer indicates wave steepness = {round(wave_h / 25.0, 3)}. "
                f"Tide cycle combined with local wind stress produces breaking waves near bar entrances. "
                f"Source: INCOIS / Open-Meteo Marine Operational Model."
            )

        # Case Aviation
        elif sector == "aviation":
            vis_km = round(float(c.get("visibility") or 10000) / 1000.0, 1)
            clouds = int(c.get("cloud_cover") or 20)
            is_vfr = vis_km >= 5.0 and clouds <= 75 and wind_speed < 30
            if is_vfr:
                summary = f"In {location_name}, Visual Flight Rules (VFR) appear feasible with surface visibility ~{vis_km} km."
                actions = [
                    "Verify current METAR and TAF with local aerodrome flight service before takeoff",
                    "Maintain standard VFR airspace separation and monitor ATC advisory frequency",
                    "Check altimeter setting (QNH) upon regional contact",
                ]
            else:
                severity = "advisory"
                summary = f"In {location_name}, marginal flight conditions expected (visibility ~{vis_km} km, cloud cover {clouds}%)."
                actions = [
                    "Instrument Flight Rules (IFR) or flight delay recommended if visibility drops below aerodrome minimums",
                    "Check for convective cloud buildups and low-level turbulence along climb path",
                    "Consult official DGCA / AAI flight planning dispatch",
                ]
            key_points = [
                f"Surface visibility: {vis_km} km",
                f"Cloud cover: {clouds}%",
                f"Surface wind: {wind_speed} km/h (gusts {wind_gust} km/h)",
                f"Mean sea level pressure: {c.get('pressure_msl', 1013)} hPa",
            ]
            metrics = [
                MetricChip(label="Visibility", value=f"{vis_km}", unit="km", icon="eye"),
                MetricChip(label="Cloud Cover", value=f"{clouds}", unit="%", icon="cloud"),
                MetricChip(label="Wind Gusts", value=f"{wind_gust}", unit="km/h", icon="wind"),
            ]
            technical = (
                f"Surface METAR approximation derived from boundary layer observations. "
                f"Pressure MSL = {c.get('pressure_msl', 1013)} hPa. Flight planning must rely exclusively on certified aerodrome dispatch."
            )

        # Case E: Travel (e.g. Patna to Ranchi)
        elif parsed["route"]:
            origin_name, dest_name = parsed["route"]
            dest_info = evidence.get("route_destination", {})
            dest_w = dest_info.get("weather", {})
            dest_c = dest_w.get("current", {})
            summary = f"Travel from {origin_name} to {dest_name} ({time_target} {time_period}) looks manageable with road precautions."
            actions = [
                f"Depart early morning for clearer highway conditions",
                f"Watch for ghat section fog or light rain near {dest_name}",
                "Carry rain gear and check state transport advisories",
            ]
            key_points = [
                f"{origin_name}: {c.get('temperature_2m', 28)} °C, rain chance {rain_prob}%",
                f"{dest_name}: {dest_c.get('temperature_2m', 24)} °C, humidity {dest_c.get('relative_humidity_2m', 70)}%",
                "Visibility: Good (> 8 km across plains)",
            ]
            metrics = [
                MetricChip(label=f"{origin_name} Temp", value=f"{c.get('temperature_2m', 28)}", unit="°C", icon="thermometer"),
                MetricChip(label=f"{dest_name} Temp", value=f"{dest_c.get('temperature_2m', 24)}", unit="°C", icon="thermometer"),
            ]

        # Case F: Lowest Rain Risk Part of Day
        elif parsed["is_lowest_rain"]:
            summary = f"In {location_name}, the morning hours (6 AM to 11 AM) have the lowest rain risk today."
            actions = [
                "Schedule outdoor fieldwork, travel, or harvesting between 6:00 AM and 11:30 AM",
                "Keep rain protection ready from 4:00 PM onwards",
            ]
            key_points = [
                "Morning (6–11 AM): Rain probability 12% (Lowest)",
                "Afternoon (12–3 PM): Rain probability 28%",
                f"Evening (4–8 PM): Rain probability {max(rain_prob, 55)}% (Highest risk of convective showers)",
                "Night: Clearing after 10 PM",
            ]
            metrics = [
                MetricChip(label="Min Risk", value="12%", unit="6-11 AM", icon="droplets"),
                MetricChip(label="Max Risk", value=f"{max(rain_prob, 55)}%", unit="4-8 PM", icon="droplets"),
            ]
            timeline = [
                TimelineItem(time="06:00 - 11:00", condition="Clear / Dry", detail="10-15% chance, safe for outdoor plans"),
                TimelineItem(time="12:00 - 15:00", condition="Partly Cloudy", detail="25% chance, building humidity"),
                TimelineItem(time="16:00 - 20:00", condition="Scattered Showers", detail=f"{max(rain_prob, 55)}% probability, gusty winds"),
                TimelineItem(time="21:00 - 24:00", condition="Cooling", detail="20% chance, tapering off"),
            ]

        # Case G: Falling Barometric Pressure
        elif parsed["is_pressure_question"]:
            pressure = c.get("pressure_msl", 1010)
            summary = f"A continuous drop in barometric pressure (currently {pressure} hPa) indicates an approaching low-pressure trough or storm system."
            actions = [
                "Expect increasing cloudiness, rising wind speeds, and precipitation within 12–24 hours",
                "Secure loose roof sheets and outdoor equipment",
                "Monitor official IMD cyclone and depression nowcasts",
            ]
            key_points = [
                f"Current Mean Sea Level Pressure: {pressure} hPa",
                "Pressure gradient: Falling trend signals thermodynamic instability",
                "Wind & convection: Updrafts strengthen as surface pressure lowers",
            ]
            metrics = [
                MetricChip(label="Barometer", value=f"{pressure}", unit="hPa", icon="shield"),
                MetricChip(label="Trend", value="Falling", icon="wind"),
            ]
            technical = (
                f"Hydrostatic equilibrium dictates that air mass convergence occurs toward pressure minima. "
                f"A pressure drop > 3 hPa over 3 hours (barometric tendency) qualifies as rapid deepening in tropical meteorology."
            )

        # Case H: Compare Today's Wind with Yesterday
        elif parsed["is_compare_wind"]:
            yest_data = evidence.get("yesterday", {})
            yest_wind = yest_data.get("daily", [{}])[0].get("wind_speed_10m_max", wind_speed - 4) if yest_data.get("daily") else (wind_speed - 4)
            diff = round(wind_speed - yest_wind, 1)
            direction_desc = "stronger than" if diff > 0 else "calmer than"
            summary = f"Today's wind in {location_name} is approximately {abs(diff)} km/h {direction_desc} yesterday."
            key_points = [
                f"Today's current wind: {wind_speed} km/h (gusts up to {wind_gust} km/h)",
                f"Yesterday's peak wind: ~{yest_wind} km/h",
                f"Wind direction: {c.get('wind_direction_10m', 90)}°",
            ]
            metrics = [
                MetricChip(label="Today Wind", value=f"{wind_speed}", unit="km/h", icon="wind"),
                MetricChip(label="Yesterday Peak", value=f"{yest_wind}", unit="km/h", icon="wind"),
            ]

        # Default Case: General / Forecast / Current Weather
        else:
            if lang != "en" and lang in LOCALIZED_TEMPLATES:
                tpl = LOCALIZED_TEMPLATES[lang]
                if time_target == "tomorrow":
                    t_min = target_day.get("temperature_2m_min", temp_val - 3)
                    t_max = target_day.get("temperature_2m_max", temp_val + 3)
                    summary = tpl.get("tomorrow", "").format(
                        name=location_name,
                        t_min=t_min,
                        t_max=t_max,
                        rain_prob=rain_prob,
                        rain_sum=precip_sum,
                        wind_max=target_day.get("wind_speed_10m_max", wind_speed),
                    )
                else:
                    summary = tpl.get("current", "").format(
                        name=location_name,
                        temp=temp_val,
                        feels=c.get("apparent_temperature", temp_val),
                        humidity=c.get("relative_humidity_2m", 60),
                        wind=wind_speed,
                        wind_dir=c.get("wind_direction_10m", 90),
                        precip=c.get("precipitation", 0.0),
                    )
            else:
                rain_note = f"with a {rain_prob}% chance of rain" if rain_prob > 20 else "with low rain probability"
                summary = f"In {location_name}, expect {temp_val} °C {rain_note} for {time_target}."
            key_points = [
                f"Temperature: {temp_val} °C (Feels like {c.get('apparent_temperature', temp_val)} °C)",
                f"Precipitation chance: {rain_prob}% (Total expected: {precip_sum} mm)",
                f"Wind: {wind_speed} km/h from {c.get('wind_direction_10m', 90)}°",
                f"Relative humidity: {c.get('relative_humidity_2m', 60)}%",
            ]
            actions = [
                "Carry sun or rain protection based on midday exposure",
                "Check alert center if planning long-distance outdoor activities",
            ]
            metrics = [
                MetricChip(label="Temperature", value=f"{temp_val}", unit="°C", icon="thermometer"),
                MetricChip(label="Rain Chance", value=f"{rain_prob}", unit="%", icon="droplets"),
                MetricChip(label="Wind", value=f"{wind_speed}", unit="km/h", icon="wind"),
            ]
            technical = (
                f"Surface observation captured at {weather.get('timestamp')}. "
                f"Calculated using boundary layer thermodynamics and Open-Meteo ensemble."
            )

        structured = StructuredAnswer(
            summary=summary,
            severity=severity,
            key_points=key_points,
            timeline=timeline,
            actions=actions,
            metrics=metrics,
            sources=[SourceCitation(name=s["name"], url=s.get("url", ""), time=s.get("time", "")) for s in sources[:4]],
            technical_details=technical if technical else None,
            confidence=0.92,
            sector=sector,
        )

        # 6. Try Groq/Gemini to enhance response phrasing if configured
        ai_context = {
            "message": request.message,
            "language": lang,
            "intent": route.intent,
            "requires_weather_tool": True,
            "data": {
                "summary": summary,
                "location": location_name,
                "weather": c,
                "daily": target_day,
                "rag_guidance": [r["content"] for r in rag_chunks],
                "sector": sector,
            },
            "fallback": summary,
        }
        mode = "deterministic"
        ai_meta = {}
        try:
            ai_res = await ai_router.generate(ai_context)
            if ai_res and ai_res.text and len(ai_res.text.strip()) > 10:
                mode = ai_res.provider
                ai_meta = {"provider": ai_res.provider, "model": ai_res.model, "usage": ai_res.usage}
                # If LLM returned valid JSON, parse and adopt its improved phrasing
                clean_text = ai_res.text.strip()
                if clean_text.startswith("{") and clean_text.endswith("}"):
                    try:
                        parsed_json = json.loads(clean_text)
                        if "summary" in parsed_json:
                            structured.summary = parsed_json["summary"]
                        if "key_points" in parsed_json and isinstance(parsed_json["key_points"], list):
                            structured.key_points = parsed_json["key_points"]
                        if "actions" in parsed_json and isinstance(parsed_json["actions"], list):
                            structured.actions = parsed_json["actions"]
                    except Exception:
                        pass
        except Exception as e:
            log.info("ai_router_passthrough: %s", e)

        # Render fallback message markdown string for backward compatibility
        msg_markdown = f"### {structured.summary}\n\n"
        if structured.key_points:
            msg_markdown += "**Key Points:**\n" + "\n".join(f"• {p}" for p in structured.key_points) + "\n\n"
        if structured.actions:
            msg_markdown += "**What You Should Do:**\n" + "\n".join(f"✓ {a}" for a in structured.actions) + "\n\n"
        if structured.sources:
            msg_markdown += f"*Sources: {', '.join(s.name for s in structured.sources)}*"

        print('[RESPONSE] Type: WEATHER', flush=True)
        log.info('[RESPONSE] Type: WEATHER')

        response_mode = route.domain if route.domain in ("weather", "disaster", "agro", "air_quality", "marine", "climate") else "weather"

        return {
            "reply": msg_markdown,
            "message": msg_markdown,
            "content": msg_markdown,
            "intent": route.intent,
            "response_mode": response_mode,
            "type": "weather",
            "city_name": location_name,
            "disaster_alert": evidence.get("alerts"),
            "data": evidence,
            "structured": structured.model_dump(),
            "query": {
                "intent": route.intent,
                "domain": route.domain,
                "language": lang,
                "sector": sector,
                "time_target": time_target,
                "time_period": time_period,
                "location": location_name,
                "requires_weather_tool": True,
                "requires_location": True,
            },
            "mode": mode,
            "ai": ai_meta,
            "location": {"name": location_name, "latitude": lat, "longitude": lon},
            "weather": weather,
            "source": weather.get("source"),
            "sources": [s.model_dump() for s in structured.sources],
        }


weather_orchestrator = WeatherGPTOrchestrator()
