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
from .intent_router import intent_router
LOCALIZED_TEMPLATES = {
    "en": {
        "unavailable": "Weather data is temporarily unavailable. Please try again shortly. I cannot verify current conditions.",
        "current": "**{name} · Current conditions**\n\nTemperature is {temp} °C (feels like {feels} °C). Humidity is {humidity}%, wind is {wind} km/h from {wind_dir}°, and precipitation is {precip} mm.",
        "tomorrow": "**{name} · Tomorrow**\n\nExpect {t_min}–{t_max} °C, with a {rain_prob}% precipitation probability and {rain_sum} mm forecast precipitation. Maximum wind: {wind_max} km/h.",
        "source": "Source: ",
    },
    "hi": {
        "unavailable": "मौसम डेटा अभी उपलब्ध नहीं है। थोड़ी देर बाद फिर कोशिश करें।",
        "current": "**{name} — वर्तमान मौसम**\n\nतापमान {temp} °C (महसूस {feels} °C)। आर्द्रता {humidity}%, हवा {wind} km/h ({wind_dir}°) और वर्षा {precip} mm।",
        "tomorrow": "**{name} — कल का पूर्वानुमान**\n\nतापमान {t_min}–{t_max} °C। बारिश की संभावना {rain_prob}%, कुल वर्षा {rain_sum} mm, अधिकतम हवा {wind_max} km/h।",
        "source": "स्रोत: ",
    },
    "te": {
        "unavailable": "వాతావరణ సమాచారం ప్రస్తుతానికి అందుబాటులో లేదు. దయచేసి కాసేపటి తర్వాత మళ్ళీ ప్రయత్నించండి.",
        "current": "**{name} — ప్రస్తుత వాతావరణం**\n\nఉష్ణోగ్రత {temp} °C (అనుభూతి {feels} °C). తేమ {humidity}%, గాలి వేగం {wind} km/h ({wind_dir}°) మరియు వర్షపాతం {precip} mm.",
        "tomorrow": "**{name} — రేపటి వాతావరణ అంచనా**\n\nఉష్ణోగ్రత {t_min}–{t_max} °C. వర్షపు సంభావ్యత {rain_prob}%, మొత్తం వర్షపాతం {rain_sum} mm, గరిష్ట గాలి {wind_max} km/h.",
        "source": "మూలం: ",
    },
    "ta": {
        "unavailable": "வானிலை தகவல் தற்போது கிடைக்கவில்லை. சிறிது நேரம் கழித்து மீண்டும் முயற்சிக்கவும்.",
        "current": "**{name} — தற்போதைய வானிலை**\n\nவெப்பநிலை {temp} °C (உணரப்படுவது {feels} °C). ஈரப்பதம் {humidity}%, காற்று {wind} km/h ({wind_dir}°) மற்றும் மழைப்பொழிவு {precip} mm.",
        "tomorrow": "**{name} — நாளைய வானிலை முன்னறிவிப்பு**\n\nவெப்பநிலை {t_min}–{t_max} °C. மழை வாய்ப்பு {rain_prob}%, மொத்த மழை {rain_sum} mm, அதிகபட்ச காற்று {wind_max} km/h.",
        "source": "மூலம்: ",
    },
    "bn": {
        "unavailable": "আবহাওয়া তথ্য বর্তমানে অনুপলব্ধ। অনুগ্রহ করে কিছুক্ষণ পর আবার চেষ্টা করুন।",
        "current": "**{name} — বর্তমান আবহাওয়া**\n\nতাপমাত্রা {temp} °C (অনুভূত {feels} °C)। আর্দ্রতা {humidity}%, বাতাস {wind} km/h ({wind_dir}°) এবং বৃষ্টিপাত {precip} mm।",
        "tomorrow": "**{name} — আগামীকালের পূর্বাভাস**\n\nতাপমাত্রা {t_min}–{t_max} °C। বৃষ্টির সম্ভাবনা {rain_prob}%, মোট বৃষ্টিপাত {rain_sum} mm, সর্বোচ্চ বাতাস {wind_max} km/h।",
        "source": "উৎস: ",
    },
    "mr": {
        "unavailable": "हवामानाची माहिती सध्या उपलब्ध नाही. कृपया थोड्या वेळाने पुन्हा प्रयत्न करा.",
        "current": "**{name} — सद्य हवामान**\n\nतापमान {temp} °C (जाणवणारे {feels} °C). आर्द्रता {humidity}%, वारा {wind} km/h ({wind_dir}°) आणि पाऊस {precip} mm.",
        "tomorrow": "**{name} — उद्याचा अंदाज**\n\nतापमान {t_min}–{t_max} °C. पावसाची शक्यता {rain_prob}%, एकूण पाऊस {rain_sum} mm, कमाल वारा {wind_max} km/h.",
        "source": "स्रोत: ",
    },
    "gu": {
        "unavailable": "હવામાન માહિતી હાલ ઉપલબ્ધ નથી. કૃપા કરીને થોડીવાર પછી ફરી પ્રયાસ કરો.",
        "current": "**{name} — વર્તમાન હવામાન**\n\nતાપમાન {temp} °C (અનુભવાતું {feels} °C). ભેજ {humidity}%, પવન {wind} km/h ({wind_dir}°) અને વરસાદ {precip} mm.",
        "tomorrow": "**{name} — આવતીકાલની આગાહી**\n\nતાપમાન {t_min}–{t_max} °C. વરસાદની શક્યતા {rain_prob}%, કુલ વરસાદ {rain_sum} mm, મહત્તમ પવન {wind_max} km/h.",
        "source": "સ્ત્રોત: ",
    },
    "kn": {
        "unavailable": "ಹವಾಮಾನ ಮಾಹಿತಿ ಪ್ರಸ್ತುತ ಲಭ್ಯವಿಲ್ಲ. ದಯವಿಟ್ಟು ಸ್ವಲ್ಪ ಸಮಯದ ನಂತರ ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.",
        "current": "**{name} — ಪ್ರಸ್ತುತ ಹವಾಮಾನ**\n\nತಾಪಮಾನ {temp} °C (ಅನಿಸುವುದು {feels} °C). ತೇವಾಂಶ {humidity}%, ಗಾಳಿ {wind} km/h ({wind_dir}°) ಮತ್ತು ಮಳೆ {precip} mm.",
        "tomorrow": "**{name} — ನಾಳೆಯ ಮುನ್ಸೂಚನೆ**\n\nತಾಪಮಾನ {t_min}–{t_max} °C. ಮಳೆಯ ಸಂಭವನೀಯತೆ {rain_prob}%, ಒಟ್ಟು ಮಳೆ {rain_sum} mm, ಗರಿಷ್ಠ ಗಾಳಿ {wind_max} km/h.",
        "source": "ಮೂಲ: ",
    },
    "ml": {
        "unavailable": "കാലാവസ്ഥാ വിവരങ്ങൾ ഇപ്പോൾ ലഭ്യമല്ല. ദയവായി അല്പം കഴിഞ്ഞ് വീണ്ടും ശ്രമിക്കുക.",
        "current": "**{name} — നിലവിലെ കാലാവസ്ഥ**\n\nതാപനില {temp} °C (തോന്നുന്നത് {feels} °C). ഈർപ്പം {humidity}%, കാറ്റ് {wind} km/h ({wind_dir}°) മഴ {precip} mm.",
        "tomorrow": "**{name} — നാളത്തെ പ്രവചനം**\n\nതാപനില {t_min}–{t_max} °C. മഴ സാധ്യത {rain_prob}%, ആകെ മഴ {rain_sum} mm, പരമാവധി കാറ്റ് {wind_max} km/h.",
        "source": "ഉറവിടം: ",
    },
    "pa": {
        "unavailable": "ਮੌਸਮ ਜਾਣਕਾਰੀ ਇਸ ਵੇਲੇ ਉਪਲਬਧ ਨਹੀਂ ਹੈ। ਕਿਰਪਾ ਕਰਕੇ ਥੋੜ੍ਹੀ ਦੇਰ ਬਾਅਦ ਦੁਬਾਰਾ ਕੋਸ਼ਿਸ਼ ਕਰੋ।",
        "current": "**{name} — ਮੌਜੂਦਾ ਮੌਸਮ**\n\nਤਾਪਮਾਨ {temp} °C (ਮਹਿਸੂਸ {feels} °C)। ਨਮੀ {humidity}%, ਹਵਾ {wind} km/h ({wind_dir}°) ਅਤੇ ਵਰਖਾ {precip} mm।",
        "tomorrow": "**{name} — ਕੱਲ੍ਹ ਦਾ ਅਨੁਮਾਨ**\n\nਤਾਪਮਾਨ {t_min}–{t_max} °C। ਮੀਂਹ ਦੀ ਸੰਭਾਵਨਾ {rain_prob}%, ਕੁੱਲ ਵਰਖਾ {rain_sum} mm, ਵੱਧ ਤੋਂ ਵੱਧ ਹਵਾ {wind_max} km/h।",
        "source": "ਸਰੋਤ: ",
    },
    "or": {
        "unavailable": "ପାଣିପାଗ ସୂଚନା ବର୍ତ୍ତମାନ ଉପଲବ୍ଧ ନାହିଁ। ଦୟାକରି କିଛି ସମୟ ପରେ ପୁନର୍ବାର ଚେଷ୍ଟା କରନ୍ତୁ।",
        "current": "**{name} — ବର୍ତ୍ତମାନର ପାଣିପାଗ**\n\nତାପମାତ୍ରା {temp} °C (ଅନୁଭୂତ {feels} °C)। ଆର୍ଦ୍ରତା {humidity}%, ପବନ {wind} km/h ({wind_dir}°) ଏବଂ ବର୍ଷା {precip} mm।",
        "tomorrow": "**{name} — ଆଗାମୀ କାଲିର ପୂର୍ବାନୁମାନ**\n\nତାପମାତ୍ରା {t_min}–{t_max} °C। ବର୍ଷା ସମ୍ଭାବନା {rain_prob}%, ମୋଟ ବର୍ଷା {rain_sum} mm, ସର୍ବାଧିକ ପବନ {wind_max} km/h।",
        "source": "ଉତ୍ସ: ",
    },
    "as": {
        "unavailable": "বতৰৰ তথ্য বৰ্তমান উপলব্ধ নহয়। অনুগ্ৰহ কৰি কিছু সময়ৰ পিছত পুনৰ চেষ্টা কৰক।",
        "current": "**{name} — বৰ্তমানৰ বতৰ**\n\nউষ্ণতা {temp} °C (অনুভৱ {feels} °C)। আৰ্দ্ৰতা {humidity}%, বতাহ {wind} km/h ({wind_dir}°) আৰু বৰষুণ {precip} mm।",
        "tomorrow": "**{name} — কাইলৈৰ পূৰ্বাভাস**\n\nউষ্ণতা {t_min}–{t_max} °C। বৰষুণৰ সম্ভাৱনা {rain_prob}%, মুঠ বৰষুণ {rain_sum} mm, সৰ্বাধিক বতাহ {wind_max} km/h।",
        "source": "উৎস: ",
    },
    "ur": {
        "unavailable": "موسم کا ڈیٹا فی الحال دستیاب نہیں ہے۔ براہ کرم تھوڑی دیر بعد دوبارہ کوشش کریں۔",
        "current": "**{name} — موجودہ موسم**\n\nدرجہ حرارت {temp} °C (محسوس {feels} °C)۔ نمی {humidity}%، ہوا {wind} km/h ({wind_dir}°) اور بارش {precip} mm۔",
        "tomorrow": "**{name} — کل کی پیش گوئی**\n\nدرجہ حرارت {t_min}–{t_max} °C۔ بارش کا امکان {rain_prob}%، کل بارش {rain_sum} mm، زیادہ سے زیادہ ہوا {wind_max} km/h۔",
        "source": "ماخذ: ",
    },
}


class WeatherQueryEngine:
    def extract(self, message, language):
        text = message.lower()
        # Detect explicit target language requests
        detected_lang = language or "en"
        from ..schemas import SUPPORTED_LANGUAGES
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
            if kw in text:
                detected_lang = code
                break
        else:
            # Script-based detection
            if re.search(r"[\u0C00-\u0C7F]", message):  # Telugu
                detected_lang = "te"
            elif re.search(r"[\u0B80-\u0BFF]", message):  # Tamil
                detected_lang = "ta"
            elif re.search(r"[\u0980-\u09FF]", message):  # Bengali/Assamese
                detected_lang = detected_lang if detected_lang in ("bn", "as", "mni") else "bn"
            elif re.search(r"[\u0A80-\u0AFF]", message):  # Gujarati
                detected_lang = "gu"
            elif re.search(r"[\u0C80-\u0CFF]", message):  # Kannada
                detected_lang = "kn"
            elif re.search(r"[\u0D00-\u0D7F]", message):  # Malayalam
                detected_lang = "ml"
            elif re.search(r"[\u0A00-\u0A7F]", message):  # Punjabi
                detected_lang = "pa"
            elif re.search(r"[\u0B00-\u0B7F]", message):  # Odia
                detected_lang = "or"
            elif re.search(r"[\u0600-\u06FF\u0750-\u077F]", message):  # Urdu/Sindhi
                detected_lang = detected_lang if detected_lang in ("ur", "sd", "ks") else "ur"
            elif re.search(r"[\u0900-\u097F]", message):  # Devanagari
                detected_lang = detected_lang if detected_lang in ("hi", "mr", "sa", "mai", "ne", "brx", "doi", "kok") else "hi"

        mappings = [
            ("cyclone", ["cyclone", "चक्रवात", "తుఫాను", "புயல்", "ঘূর্ণিঝড়"]),
            ("earthquake", ["earthquake", "भूकंप", "భూకంపం", "நிலநடுக்கம்", "ভূমিকম্প"]),
            ("comparison", ["compare", "तुलना", "పోల్చండి", "ஒப்பிடு"]),
            ("air_quality", ["air quality", "aqi", "pollution", "प्रदूषण", "గాలి నాణ్యత"]),
            ("marine", ["marine", "waves", "sea", "समुद्र", "సముద్రం"]),
            ("disaster_alert", ["warning", "alert", "lightning", "चेतावनी", "హెచ్చరిక", "எச்சரிக்கை"]),
            ("historical", ["last month", "histor", "पिछले", "గత"]),
            ("agriculture", ["crop", "irrigat", "farmer", "किसान", "सिंचाई", "వ్యవసాయం", "రైతు"]),
            ("rain", ["rain", "बारिश", "వర్షం", "மழை", "বৃষ্টি"]),
            ("wind", ["wind", "हवा", "గాలి", "காற்று"]),
            ("advisory", ["safe", "travel", "flood", "బాధ", "సురక్షిత"]),
            ("forecast", ["tomorrow", "forecast", "कल", "రేపు", "நாளை"]),
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
            "hindi", "english", "tamil", "telugu", "bengali", "marathi", "gujarati", "urdu",
            "my area", "me", "here",
        ):
            location = None
        return {
            "intent": intent,
            "location": location,
            "time": "tomorrow" if ("tomorrow" in text or "कल" in text or "రేపు" in text or "நாளை" in text) else "today",
            "weather_parameter": intent,
            "language": detected_lang if detected_lang in SUPPORTED_LANGUAGES else "en",
            "use_case": intent if intent in ["agriculture", "advisory"] else "general",
        }

    async def prepare(self, request):
        route = intent_router.classify(request.message)
        if not route.requires_weather_tool:
            return {
                "message": "Hi! How can I help you today?",
                "query": {"intent": "GENERAL", "language": request.language or "en", "requires_weather_tool": False, "location": None},
                "mode": "general",
                "weather": None,
                "tool_context": {},
            }
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
        lang = query.get("language") or "en"
        tpl = LOCALIZED_TEMPLATES.get(lang, LOCALIZED_TEMPLATES.get("en"))
        hi = lang == "hi"
        c = weather["current"]
        if weather["status"] != "live":
            message = tpl.get("unavailable", LOCALIZED_TEMPLATES["en"]["unavailable"])
        elif query["intent"] in ["cyclone", "earthquake"]:
            if lang == "hi":
                message = "चक्रवात की आधिकारिक जानकारी यहाँ उपलब्ध नहीं है। भूकंप की रिपोर्ट ग्लोब पर USGS स्रोत में देखें।"
            elif lang == "te":
                message = "తుఫాను హెచ్చరికలు ఇంకా కనెక్ట్ కాలేదు. భూకంప నివేదికల కోసం గ్లోబ్‌లోని USGS లేయర్‌ను చూడండి."
            elif lang == "ta":
                message = "புயல் எச்சரிக்கைகள் இன்னும் இணைக்கப்படவில்லை. நிலநடுக்க அறிக்கைகளுக்கு USGS அடுக்கைப் பார்க்கவும்."
            elif lang == "bn":
                message = "ঘূর্ণিঝড় সতর্কতা এখনও সংযুক্ত নয়। ভূমিকম্পের তথ্যের জন্য গ্লোবে USGS লেয়ার দেখুন।"
            elif lang == "ur":
                message = "طوفان کی سرکاری معلومات یہاں دستیاب نہیں ہیں۔ زلزلے کی رپورٹ کے لیے گلوب پر USGS لیئر دیکھیں۔"
            else:
                message = "Cyclone warnings are not connected. For earthquake reports, select the USGS earthquake layer on the globe. Missing data does not mean there is no hazard."
        elif query["intent"] == "historical":
            if lang == "hi":
                message = "पुराने मौसम के लिए Climate पृष्ठ पर तारीखें चुनें।"
            elif lang == "te":
                message = "గత వాతావరణం కోసం క్లైమేట్ పేజీలో తేదీలను ఎంచుకోండి."
            elif lang == "ta":
                message = "கடந்த கால வானிலைக்கு கிளைமேట్ பக்கத்தில் தேதிகளைத் தேர்ந்தெடுக்கவும்."
            elif lang == "bn":
                message = "পূর্ববর্তী আবহাওয়ার জন্য ক্লাইমেট পেজে তারিখ নির্বাচন করুন।"
            elif lang == "ur":
                message = "گزشتہ موسم کے لیے کلائمیٹ پیج پر تاریخیں منتخب کریں۔"
            else:
                message = "Open Climate and select a date range to inspect actual historical data. I have not calculated a comparison from this question."
        elif query["time"] == "tomorrow" and len(weather["daily"]) > 1:
            d = weather["daily"][1]
            t_str = tpl.get("tomorrow", LOCALIZED_TEMPLATES["en"]["tomorrow"])
            message = t_str.format(
                name=name,
                t_min=d.get("temperature_2m_min", "—"),
                t_max=d.get("temperature_2m_max", "—"),
                rain_prob=d.get("precipitation_probability_max", 0),
                rain_sum=d.get("precipitation_sum", 0.0),
                wind_max=d.get("wind_speed_10m_max", "—"),
            )
        else:
            c_str = tpl.get("current", LOCALIZED_TEMPLATES["en"]["current"])
            message = c_str.format(
                name=name,
                temp=c.get("temperature_2m", "—"),
                feels=c.get("apparent_temperature", c.get("temperature_2m", "—")),
                humidity=c.get("relative_humidity_2m", "—"),
                wind=c.get("wind_speed_10m", "—"),
                wind_dir=c.get("wind_direction_10m", "—"),
                precip=c.get("precipitation", 0.0),
            )
        if query["intent"] == "agriculture" and c:
            if lang == "hi":
                message += "\n\nसिंचाई से पहले मिट्टी की नमी और आने वाली बारिश जाँचें।"
            elif lang == "te":
                message += "\n\nనీటిపారుదలకు ముందు నేలలోని తేమను మరియు రాబోయే వర్షాన్ని తనిఖీ చేయండి."
            elif lang == "ta":
                message += "\n\nபாசனத்திற்கு முன் மண்ணின் ஈரப்பதம் மற்றும் வரவிருக்கும் மழையைச் சரிபார்க்கவும்."
            elif lang == "bn":
                message += "\n\nসেচের আগে মাটির আর্দ্রতা এবং আসন্ন বৃষ্টিপাত পরীক্ষা করুন।"
            elif lang == "ur":
                message += "\n\nآبپاشی سے پہلے مٹی کی نمی اور آنے والی بارش کو چیک کریں۔"
            else:
                message += "\n\nCheck measured root-zone soil moisture and upcoming rainfall before irrigating. Avoid spraying during rain or strong wind; this is general decision support."
        if query["intent"] == "advisory":
            if lang == "hi":
                message += "\n\nयात्रा से पहले स्थानीय आधिकारिक चेतावनियाँ देखें। बाढ़ का जोखिम केवल मौसम से तय नहीं किया जा सकता।"
            elif lang == "te":
                message += "\n\nప్రయాణానికి ముందు స్థానిక అధికారిక హెచ్చరికలను తనిఖీ చేయండి. వరద ప్రమాదాన్ని వాతావరణం మాత్రమే నిర్ణయించదు."
            elif lang == "ta":
                message += "\n\nபயணத்திற்கு முன் உள்ளூர் அதிகாரப்பூர்வ எச்சரிக்கைகளைச் சரிபார்க்கவும். வெள்ள அபாயத்தை வானிலை மட்டுமே தீர்மானிக்க முடியாது."
            elif lang == "bn":
                message += "\n\nযাত্রার আগে স্থানীয় সরকারী সতর্কতা পরীক্ষা করুন। বন্যার ঝুঁকি শুধুমাত্র আবহাওয়া দ্বারা নির্ধারণ করা যায় না।"
            elif lang == "ur":
                message += "\n\nسفر سے پہلے مقامی سرکاری انتباہات چیک کریں۔ سیلاب کا خطرہ صرف موسم سے طے نہیں کیا جا سکتا۔"
            else:
                message += "\n\nWeather alone cannot establish travel safety or flood risk. Check local official warnings and road conditions before departure."
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
        message += "\n\n" + tpl.get("source", "Source: ") + weather["source"] + " · " + str(weather.get("timestamp") or "time unavailable") + " · " + str(weather.get("timezone", "UTC"))
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
        from .orchestrator import weather_orchestrator
        return await weather_orchestrator.answer(request)


query_engine = WeatherQueryEngine()
