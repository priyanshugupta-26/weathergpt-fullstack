"""
Query & Intent Router for WeatherGPT
Intelligently classifies user queries into semantic intents and domains.
Determines whether live data, user coordinates, or weather/domain tools are required.
Ensures WeatherGPT behaves as a general-purpose conversational AI assistant with
specialized meteorological, disaster, agro, air quality, and marine intelligence.
"""
import re
import sys
import logging
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger("weathergpt.router")


@dataclass
class IntentRouteResult:
    intent: str  # "greeting", "general", "weather_current", "weather_forecast", "air_quality", "disaster_live", "agro_advisory", "climate_history", "marine", "travel_weather", "aviation_weather"
    domain: str = "general"  # "general", "weather", "disaster", "agro", "air_quality", "climate", "marine"
    requires_live_data: bool = False
    requires_location: bool = False
    requires_weather_tool: bool = False  # True whenever requires_live_data is True
    confidence: float = 0.95
    location: str | None = None
    time_range: str | None = None  # "today", "tomorrow", "tonight", "weekend", or None
    time_period: str | None = None  # "morning", "evening", "afternoon", "after_5pm", or None
    sector: str = "general"
    route: tuple[str, str] | None = None
    is_followup: bool = False
    details: dict[str, Any] = field(default_factory=dict)


LOCATION_REQUIRED_INTENTS = {
    "weather_current",
    "weather_forecast",
    "air_quality",
    "disaster_live",
    "agro_advisory",
    "climate_history",
    "marine",
    "travel_weather",
    "aviation_weather",
}

# Greetings and casual conversational phrases
GREETING_PATTERNS = [
    r"^(hi|hello|hey|greetings|howdy|hola|namaste|नमस्ते|vanakkam|வணக்கம்|namaskara|నమస్కారం|pranam|kem\s+cho|khalas)(?:\b|\s|$)",
    r"^(good\s+(morning|afternoon|evening|night|day))(?:\b|\s|$)",
    r"^(how\s+are\s+you|how\'?s\s+it\s+going|how\s+do\s+you\s+do|what\'?s\s+up|sup)(?:\b|\s|$)",
    r"^(who\s+are\s+you|what\s+is\s+your\s+name|what\s+can\s+you\s+do|introduce\s+yourself|tell\s+me\s+about\s+yourself)(?:\b|\s|$)",
    r"^(thank\s+you|thanks|thx|धन्यवाद|शुक्रिया|bye|goodbye|see\s+you|take\s+care)(?:\b|\s|$)",
]

# Educational / General scientific / Concept questions (MUST NEVER trigger live tools)
EDUCATIONAL_CONCEPT_PATTERNS = [
    # "explain cyclones", "what is a cyclone", "how do cyclones form"
    r"^(what\s+is|what\s+are|explain|how\s+do|how\s+does|define|causes\s+of|types\s+of)\s+(a\s+|an\s+|the\s+)?(cyclone|cyclones|hurricane|hurricanes|typhoon|typhoons|tornado|tornadoes)\b",
    # "what is rainfall", "how does rainfall occur", "what causes rain"
    r"^(what\s+is|what\s+causes|how\s+does|how\s+do|explain)\s+(a\s+|an\s+|the\s+)?(rainfall|rain|precipitation|clouds?|water\s+cycle)\b",
    # "what is humidity", "why does humidity make us feel hotter", "explain why humidity makes hot weather feel worse"
    r"^(what\s+is|explain|why\s+does)\s+(a\s+|an\s+|the\s+)?(humidity|relative\s+humidity|dew\s+point|humid\s+weather)\b",
    r"(?:explain\s+)?why\s+(?:does\s+)?(humidity|humid\s+air|moisture)\s+makes?\s+(?:us|it|hot\s+weather)\s+feel\s+(?:hotter|worse|uncomfortable)",
    r"^explain\s+(?:why|how)\s+.*(humidity|hot\s+weather|clouds?|rain|rainfall|aqi|cyclones?)\b",
    # "what is aqi", "what is air quality index", "how is aqi calculated"
    r"^(what\s+is|explain|how\s+is)\s+(a\s+|an\s+|the\s+)?(aqi|air\s+quality\s+index|pm2\.?5|pm10|smog)\b",
    # "why are summers hot", "why are winters cold", "what causes seasons"
    r"^(why\s+are|what\s+causes|why\s+is)\s+(summers?|winters?|seasons?|hot\s+weather|cold\s+weather|climate\s+change|global\s+warming)\b",
    # "what is farming", "what is agriculture", "explain photosynthesis"
    r"^(what\s+is|explain|define)\s+(a\s+|an\s+|the\s+)?(farming|agriculture|crop\s+rotation|photosynthesis|organic\s+farming|irrigation\s+system)\b",
    # General weather science
    r"^(what\s+is|what\s+causes|how\s+does)\s+(the\s+)?(greenhouse\s+effect|el\s+nino|la\s+nina|coriolis\s+force|atmospheric\s+pressure|barometer\s+work|rainbows?\s+form|thunder\s+and\s+lightning)\b",
]

# Explicit keyword traps that must NOT be confused with weather
KEYWORD_TRAP_PATTERNS = [
    r"\b(weathering\s+in\s+rocks|rock\s+weathering|biological\s+weathering|chemical\s+weathering|mechanical\s+weathering)\b",
    r"\b(random\s+forest|gradient\s+boosting|decision\s+tree|deep\s+learning|machine\s+learning|neural\s+network)\b",
]

# General programming, mathematics, science, literature, and general AI topics
GENERAL_TOPIC_PATTERNS = [
    r"\b(machine\s+learning|deep\s+learning|artificial\s+intelligence|neural\s+network|nlp|llm)\b",
    r"\b(python|javascript|typescript|java|c\+\+|golang|rust|html|css|sql|docker|git|react)\b",
    r"\b(binary\s+search|bubble\s+sort|quicksort|merge\s+sort|recursion|algorithm|data\s+structure|reverse\s+a?\s+string|factorial|fibonacci)\b",
    r"\b(write\s+(a\s+)?(python|java|c\+\+|code|program|script|function|class|essay|poem|joke|story|recipe))\b",
    r"\b(who\s+is|who\s+was|tell\s+me\s+about)\s+(albert\s+einstein|apj\s+abdul\s+kalam|newton|galileo|curie|turing|shakespeare)\b",
    r"\b(capital\s+of|currency\s+of|president\s+of|prime\s+minister\s+of)\b",
    r"\b(photosynthesis|mitochondria|gravity|theory\s+of\s+relativity|quantum|dna|rna)\b",
    r"\b(tell\s+me\s+a\s+joke|make\s+me\s+laugh|riddle)\b",
]

# Live warning / disaster triggers (distinguished from educational questions)
DISASTER_LIVE_TRIGGERS = [
    r"\b(cyclone|flood|tsunami|earthquake|landslide|storm|storm\s+surge)\s+(warning|alert|near\s+me|today|tomorrow|here|in\s+[a-z]+|risk\s+in\s+[a-z]+)\b",
    r"\b(warning|alert|danger|risk)\s+(for|of|from)\s+(cyclone|flood|tsunami|earthquake|landslide|thunderstorm|lightning)\b",
    r"\b(is\s+there\s+a\s+cyclone|any\s+cyclone\s+warning|cyclone\s+risk\s+in|is\s+it\s+safe\s+from\s+cyclone)\b",
]


class IntentRouter:
    """
    Intelligent Query Router for WeatherGPT.
    Classifies queries into structured domain intents, cleanly separating
    general conversational questions from live grounded meteorological and domain requests.
    """

    def classify(
        self,
        message: str,
        conversation_context: dict[str, Any] | None = None,
        sector_hint: str | None = None,
    ) -> IntentRouteResult:
        text = message.strip()
        lower = text.lower()
        context = conversation_context or {}

        # 1. Clean punctuation for matching
        clean_text = re.sub(r"[?!.,'\"]", "", lower).strip()

        # 2. Check for explicit keyword traps (e.g., "weathering in rocks", "Python random forest")
        for pat in KEYWORD_TRAP_PATTERNS:
            if re.search(pat, lower, re.I):
                res = IntentRouteResult(
                    intent="general",
                    domain="general",
                    requires_live_data=False,
                    requires_location=False,
                    requires_weather_tool=False,
                    confidence=0.99,
                )
                self._log(message, res)
                return res

        # 3. Check for Educational / General Science Weather Concepts (e.g. "Explain cyclones", "What is rainfall?")
        # These are informational questions, NOT live disaster or weather requests!
        for pat in EDUCATIONAL_CONCEPT_PATTERNS:
            if re.search(pat, clean_text, re.I):
                # Ensure no live location/warning query is appended
                if not any(re.search(d_pat, lower) for d_pat in DISASTER_LIVE_TRIGGERS) and not any(w in lower for w in ("in guntur", "in delhi", "in mumbai", "in chennai", "near me", "here today")):
                    res = IntentRouteResult(
                        intent="general",
                        domain="general",
                        requires_live_data=False,
                        requires_location=False,
                        requires_weather_tool=False,
                        confidence=0.98,
                    )
                    self._log(message, res)
                    return res

        # 4. Check for Mixed Queries: Greeting prefix + specialized weather/domain inquiry
        # e.g., "Hi, will it rain tomorrow?" or "Hello, what is the temperature in Guntur?"
        stripped_weather_query = self._strip_greeting_prefix(clean_text)
        if stripped_weather_query and stripped_weather_query != clean_text:
            # Re-evaluate the underlying query without greeting
            underlying_res = self._classify_weather(stripped_weather_query, stripped_weather_query.lower(), context)
            if underlying_res.requires_live_data:
                self._log(message, underlying_res)
                return underlying_res

        # 5. Check for Pure Greetings and Casual Conversation
        for pat in GREETING_PATTERNS:
            if re.search(pat, clean_text, re.I):
                # Ensure no live weather words are in the query
                if not any(w in lower for w in ("weather", "rain", "temperature", "temp", "forecast", "cyclone", "warning", "alert", "humidity", "aqi", "irrigate", "spray")):
                    res = IntentRouteResult(
                        intent="greeting",
                        domain="general",
                        requires_live_data=False,
                        requires_location=False,
                        requires_weather_tool=False,
                        confidence=0.99,
                    )
                    self._log(message, res)
                    return res

        # 6. Check for General Knowledge, Programming, Math, Writing
        for pat in GENERAL_TOPIC_PATTERNS:
            if re.search(pat, lower, re.I):
                if not any(w in lower for w in ("what's the weather", "temperature today", "rain tomorrow", "current weather")):
                    res = IntentRouteResult(
                        intent="general",
                        domain="general",
                        requires_live_data=False,
                        requires_location=False,
                        requires_weather_tool=False,
                        confidence=0.99,
                    )
                    self._log(message, res)
                    return res

        # 7. Check for Explicit Sector Hints (e.g. from specialized UI tabs)
        if sector_hint and sector_hint != "general":
            res = self._classify_weather(text, lower, context, forced_sector=sector_hint)
            self._log(message, res)
            return res

        # 8. Check for Conversational Elliptical Follow-ups (e.g. "What about tomorrow?", "And in Delhi?")
        is_followup = self._is_elliptical_followup(lower)
        last_intent = context.get("last_intent")

        if is_followup and last_intent and last_intent not in ("general", "greeting", "GENERAL"):
            res = self._handle_followup(text, lower, context)
            self._log(message, res)
            return res

        # 9. Check for Weather, Disaster, Agro, Air Quality, Marine & Travel Inquiries
        weather_res = self._classify_weather(text, lower, context)
        if weather_res.requires_live_data:
            self._log(message, weather_res)
            return weather_res

        # 10. Default: GENERAL query (No weather tools invoked, no location resolved)
        res = IntentRouteResult(
            intent="general",
            domain="general",
            requires_live_data=False,
            requires_location=False,
            requires_weather_tool=False,
            confidence=0.95,
        )
        self._log(message, res)
        return res

    def _strip_greeting_prefix(self, text: str) -> str | None:
        """Strips greetings like 'hi', 'hello', 'hey' from the beginning of a query."""
        m = re.match(r"^(hi|hello|hey|namaste|greetings)\s*[,!.-]?\s*(.*)$", text, re.I)
        if m:
            rest = m.group(2).strip()
            return rest if len(rest) > 2 else None
        return None

    def _is_elliptical_followup(self, lower: str) -> bool:
        followup_phrases = [
            r"^(what|how)\s+about\s+(tomorrow|today|tonight|evening|morning|afternoon|after\s+\d+|there|sunday|saturday|the\s+weekend)",
            r"^and\s+(tomorrow|today|there|in\s+[a-z]+|evening|morning)",
            r"^(will\s+it|is\s+it\s+going\s+to)\s+rain\s+there(\s+tomorrow)?",
            r"^what\s+about\s+after\s+\d+",
            r"^what\s+about\s+there",
            r"^what\s+about\s+[a-z]+",
        ]
        return any(re.search(pat, lower) for pat in followup_phrases)

    def _handle_followup(self, text: str, lower: str, context: dict[str, Any]) -> IntentRouteResult:
        prior_location = context.get("location_name")
        prior_sector = context.get("sector", "general")
        prior_intent = context.get("last_intent", "weather_forecast")

        time_target = None
        time_period = None

        if any(w in lower for w in ("tomorrow", "kal", "రేపు", "நாளை", "আগামীকাল")):
            time_target = "tomorrow"
        elif any(w in lower for w in ("today", "aaj", "current", "now", "इस समय")):
            time_target = "today"
        elif any(w in lower for w in ("tonight", "aaj raat")):
            time_target = "tonight"
        elif any(w in lower for w in ("weekend", "this weekend", "saturday", "sunday")):
            time_target = "weekend"

        if any(w in lower for w in ("morning", "subah", "ఉదయం", "காலை")):
            time_period = "morning"
        elif any(w in lower for w in ("evening", "shaam", "సాయంత్రం", "மாலை")):
            time_period = "evening"
        elif any(w in lower for w in ("afternoon", "dopahar", "మధ్యాహ్నం")):
            time_period = "afternoon"
        elif any(w in lower for w in ("after 5", "5 pm", "5 baje")):
            time_period = "after_5pm"

        new_loc = self._extract_location(text)
        location = new_loc or prior_location

        intent = "weather_forecast" if time_target in ("tomorrow", "weekend") or "rain" in lower else (prior_intent if prior_intent not in ("general", "greeting") else "weather_current")
        domain = "weather"
        if "cyclone" in intent or "disaster" in intent:
            domain = "disaster"
        elif "agro" in intent:
            domain = "agro"

        return IntentRouteResult(
            intent=intent,
            domain=domain,
            location=location,
            time_range=time_target or context.get("time_target", "today"),
            time_period=time_period or context.get("time_period", "all_day"),
            requires_live_data=True,
            requires_location=True,
            requires_weather_tool=True,
            sector=prior_sector,
            is_followup=True,
            confidence=0.96,
        )

    def _classify_weather(
        self,
        text: str,
        lower: str,
        context: dict[str, Any],
        forced_sector: str | None = None,
    ) -> IntentRouteResult:
        # Route detection
        route_match = re.search(r"from\s+([a-zA-Z\s]+?)\s+to\s+([a-zA-Z\s]+?)(?:\s+(?:tomorrow|today|morning|evening)|[?!.]|$)", text, re.I)
        route = None
        if route_match:
            route = (route_match.group(1).strip(), route_match.group(2).strip())
        else:
            travel_cue = any(w in lower for w in ("travel", "trip", "journey", "highway", "road", "drive", "driving", "route", "raste"))
            if travel_cue:
                route_dash = re.search(r"\b([a-zA-Z]{3,})\s+to\s+([a-zA-Z]{3,})\b", text, re.I)
                if route_dash:
                    w1 = route_dash.group(1).strip().lower()
                    w2 = route_dash.group(2).strip().lower()
                    non_places = {
                        "how", "want", "need", "go", "going", "carry", "take", "taking", "umbrella",
                        "come", "drive", "travel", "road", "highway", "trip", "safe", "listen",
                        "able", "ready", "close", "next", "prior", "due", "according", "thanks",
                        "college", "school", "office", "work", "home", "class", "outside"
                    }
                    if w1 not in non_places and w2 not in non_places:
                        route = (route_dash.group(1).strip(), route_dash.group(2).strip())

        # Sector detection
        sector = forced_sector or "general"
        agri_words = [
            "spray", "spraying", "pesticide", "insecticide", "fungicide", "irrigate", "irrigation",
            "fertilizer", "urea", "crop", "rice", "paddy", "wheat", "cotton", "farmer",
            "dalu", "khad", "kheti", "khet", "pani du", "fasal", "chhidkao", "chhidkav",
            "chhidakna", "chhidakne", "sinchai", "keetnashak", "wash-off", "dusting"
        ]
        marine_words = [
            "sea", "boat", "boats", "fishing", "fish", "waves", "machhli", "swell", "coast",
            "coastal", "tide", "offshore", "ocean", "samundar", "port", "leharon", "squall",
            "rough sea", "fishermen"
        ]
        aviation_words = [
            "flight", "plane", "aviation", "vfr", "ifr", "runway", "turbulence", "pilot",
            "aircraft", "convective", "cloud base", "wind shear", "visibility", "crosswind", "ceiling"
        ]
        travel_words = [
            "travel", "trip", "journey", "highway", "road", "drive", "driving", "raste", "disrupt driving"
        ]

        # Check for agriculture questions (e.g., "Should I irrigate my rice field today?")
        if any(w in lower for w in agri_words) or any(phrase in lower for phrase in ("irrigate my", "should i spray", "what crops should i grow")):
            sector = "agriculture"
        elif any(w in lower for w in marine_words):
            sector = "marine"
        elif any(w in lower for w in aviation_words):
            sector = "aviation"
        elif any(w in lower for w in travel_words) or route:
            sector = "travel"

        # Time extraction
        time_target = None
        time_period = None
        if any(w in lower for w in ("tomorrow", "kal", "రేపు", "நாளை", "আগামীকাল")):
            time_target = "tomorrow"
        elif any(w in lower for w in ("today", "aaj", "current", "now", "इस समय", "वर्तमान", "ఈ రోజు", "இன்று", "আজ")):
            time_target = "today"
        elif any(w in lower for w in ("tonight", "aaj raat", "ఈ రాత్రి")):
            time_target = "tonight"
        elif any(w in lower for w in ("weekend", "this weekend", "saturday", "sunday")):
            time_target = "weekend"
        elif any(w in lower for w in ("yesterday", "kal (past)", "గత")):
            time_target = "yesterday"

        if any(w in lower for w in ("morning", "subah", "ఉదయం", "காலை")):
            time_period = "morning"
        elif any(w in lower for w in ("evening", "shaam", "సాయంత్రం", "மாலை")):
            time_period = "evening"
        elif any(w in lower for w in ("afternoon", "dopahar", "మధ్యాహ్నం")):
            time_period = "afternoon"
        elif any(w in lower for w in ("after 5", "5 pm", "5 baje")):
            time_period = "after_5pm"

        # Weather keywords
        weather_words = [
            "weather", "temperature", "temp", "forecast", "climate", "hot", "cold",
            "warm", "chilly", "humid", "humidity", "heat", "garmi", "sardi", "thand", "mausam",
            "हवामान", "వాతావరణం", "வானிலை", "আবহাওয়া", "موسم", "मौसम", "तापमान", "गरमी", "सर्दी",
            "rain", "raining", "rainy", "rainfall", "drizzle", "shower", "downpour",
            "barish", "baarish", "बारिश", "वर्षा", "వర్షం", "மழை", "বৃষ্টি", "पाऊस", "paus", "بارش", "umbrella",
            "wind", "windy", "breeze", "gust", "storm", "cyclone", "चक्रवात", "తుఫాను", "புயல்", "toofan", "طوفان", "तूफान",
            "alert", "warning", "flood", "earthquake", "lightning", "thunderstorm", "bijli", "बिजली", "चेतावनी", "హెచ్చరిక", "बाढ़",
            "pressure", "barometer", "aqi", "air quality", "pollution", "squall", "hail", "frost", "fog", "mist", "snow", "sunny"
        ]

        has_weather_word = any(w in lower for w in weather_words)

        # Mixed / practical actions: e.g. "Should I carry an umbrella tomorrow?"
        is_mixed_weather_question = any(phrase in lower for phrase in [
            "carry an umbrella", "take an umbrella", "need an umbrella", "umbrella",
            "go outside tomorrow if it rains", "safe to travel", "should i spray",
            "can i spray", "should i irrigate", "can i travel", "rain here tomorrow",
            "temperature today", "what is the temperature", "what's the temperature",
            "how hot is it", "how cold is it"
        ])

        # Temperature or weather inquiry: e.g. "Is Guntur hot today?", "Weather in Guntur"
        is_temp_inquiry = bool(re.search(r"\b(is|are)\s+([a-zA-Z\s]+?)\s+(hot|cold|warm|rainy|humid|sunny)\b", lower))

        requires_tool = (
            has_weather_word
            or is_mixed_weather_question
            or is_temp_inquiry
            or (sector != "general")
            or (route is not None)
            or (forced_sector is not None)
        )

        if not requires_tool:
            return IntentRouteResult(
                intent="general",
                domain="general",
                requires_live_data=False,
                requires_location=False,
                requires_weather_tool=False,
                confidence=0.95,
            )

        # Location extraction
        location = self._extract_location(text)
        if not location and "there" in lower and context.get("location_name"):
            location = context.get("location_name")

        # Specific domain & intent categorization
        intent = "weather_current"
        domain = "weather"

        # Check for disaster queries
        is_disaster = any(w in lower for w in ("cyclone", "चक्रवात", "తుఫాను", "earthquake", "flood", "tsunami")) or any(re.search(p, lower) for p in DISASTER_LIVE_TRIGGERS)
        is_air_quality = any(w in lower for w in ("aqi", "air quality", "pollution", "pm2.5", "pm10"))

        if is_disaster:
            intent = "disaster_live"
            domain = "disaster"
        elif is_air_quality:
            intent = "air_quality"
            domain = "air_quality"
        elif sector == "agriculture":
            intent = "agro_advisory"
            domain = "agro"
        elif sector == "marine":
            intent = "marine"
            domain = "marine"
        elif sector == "aviation":
            intent = "aviation_weather"
            domain = "weather"
        elif sector == "travel" or route:
            intent = "travel_weather"
            domain = "weather"
        elif any(w in lower for w in ("warning", "alert", "चेतावनी", "హెచ్చరిక")):
            intent = "disaster_live" if any(w in lower for w in ("cyclone", "flood", "danger")) else "weather_forecast"
            domain = "disaster" if intent == "disaster_live" else "weather"
        elif any(w in lower for w in ("history", "historical", "last month", "पिछले")):
            intent = "climate_history"
            domain = "climate"
        elif any(w in lower for w in ("climate trend", "climate change", "global warming")):
            intent = "climate_history"
            domain = "climate"
        elif time_target in ("tomorrow", "weekend") or any(w in lower for w in ("forecast", "will it rain", "is it going to rain", "upcoming")):
            intent = "weather_forecast"
            domain = "weather"
        elif is_temp_inquiry or any(w in lower for w in ("temperature", "temp", "hot", "cold", "humidity", "current", "weather")):
            intent = "weather_current"
            domain = "weather"

        return IntentRouteResult(
            intent=intent,
            domain=domain,
            location=location,
            time_range=time_target or "today",
            time_period=time_period or "all_day",
            requires_live_data=True,
            requires_location=True,
            requires_weather_tool=True,
            sector=sector,
            route=route,
            confidence=0.97,
            details={
                "is_spray_question": any(w in lower for w in ("spray", "pesticide", "fungicide", "chhidkao", "chhidkav")),
                "is_irrigate_question": any(w in lower for w in ("irrigate", "irrigation", "sinchai", "pani du")),
                "is_fertilizer_question": any(w in lower for w in ("fertilizer", "urea", "khad", "dalu")),
                "is_fishing_question": any(w in lower for w in ("fishing", "fish", "boat", "machhli", "sea safe", "samundar")),
                "is_thunderstorm_question": any(w in lower for w in ("thunderstorm", "lightning", "bijli", "thunder", "why warning")),
                "is_pressure_question": any(w in lower for w in ("pressure", "barometer", "falling pressure", "dhabav")),
                "is_compare_wind": any(w in lower for w in ("compare today's wind with yesterday", "wind with yesterday", "hawa kal")),
                "is_lowest_rain": any(w in lower for w in ("lowest rain", "lowest risk", "safe part of day", "least rain")),
                "is_explain_warning": any(w in lower for w in ("explain this warning", "explain warning", "warning in")),
            }
        )

    def _extract_location(self, text: str) -> str | None:
        time_words = r"(?:tomorrow|today|tonight|yesterday|this|next|after|before|morning|evening|afternoon|weekend)"
        # Pattern 1: "in/near/at/for/around/of/affect/hit/towards <location>"
        loc_match = re.search(
            rf"\b(?:in|near|at|for|around|of|affect|hit|towards)\s+([a-zA-Z][a-zA-Z\s.-]*?)(?=\s+{time_words}\b|[?!,]|\s*$)",
            text,
            re.I,
        )
        location = loc_match.group(1).strip() if loc_match else None

        # Pattern 2: "Is <location> hot/cold/rainy today?"
        if not location:
            m_prop = re.search(r"\b(?:is|are)\s+([a-zA-Z][a-zA-Z\s.-]*?)\s+(?:hot|cold|warm|rainy|humid|sunny|windy)\b", text, re.I)
            if m_prop:
                location = m_prop.group(1).strip()

        # Pattern 3: "<location> weather" or "<location> forecast"
        if not location:
            m_city_weather = re.search(r"\b([a-zA-Z]{3,})\s+(?:weather|forecast|temperature|temp|aqi)\b", text, re.I)
            if m_city_weather and m_city_weather.group(1).lower() not in (
                "the", "today", "tomorrow", "this", "bad", "good", "local", "current", "what", "whats", "high", "low"
            ):
                location = m_city_weather.group(1).strip()

        # Pattern 4: "will/does/is/can <location> get/receive/see/expect/experience"
        if not location:
            m_verb = re.search(r"\b(?:will|does|can|is|should)\s+([a-zA-Z][a-zA-Z\s.-]*?)\s+(?:get|receive|see|experience|expect|have|face)\b", text, re.I)
            if m_verb:
                location = m_verb.group(1).strip()

        if location:
            excluded = {
                "hindi", "english", "tamil", "telugu", "urdu", "bengali", "marathi", "gujarati", "kannada", "malayalam", "odia", "punjabi", "assamese",
                "my area", "the area", "my farm", "the farm", "here", "there", "the sea", "the coast", "college", "school", "office", "home",
                "me", "us", "him", "her", "them", "it", "this", "that", "the", "what", "whats", "a", "an", "python", "machine learning", "java",
                "hot", "cold", "warm", "humid", "sunny", "rainy", "weather", "today", "tomorrow", "tonight", "yesterday", "air", "moisture", "feel", "worse",
            }
            if location.lower() in excluded:
                return None
            location = re.sub(r"\s+(to|from|and|or|with)$", "", location, flags=re.I).strip()
            return location if len(location) >= 2 else None

        return None

    def _log(self, query: str, res: IntentRouteResult):
        clean_q = query.strip().replace("\n", " ")
        req_loc_str = "true" if res.requires_location else "false"
        req_tool_str = "true" if res.requires_live_data else "false"

        # 1. Output structured [CHAT ROUTER] debug block requested by user
        resolved_city_str = f'\nresolved_city="{res.location}"' if res.location else ""
        router_block = (
            f'[CHAT ROUTER]\n'
            f'message="{clean_q}"\n'
            f'intent="{res.intent}"\n'
            f'requires_location={req_loc_str}\n'
            f'requires_tool={req_tool_str}'
            f'{resolved_city_str}'
        )
        print(router_block, flush=True)
        log.info(router_block)

        # 2. Output flow logs for test & tracking compatibility
        if res.requires_live_data:
            log.info(f'[ROUTER] Query: "{clean_q}"')
            log.info(f"[ROUTER] Intent: {res.intent}")
            if res.location:
                log.info(f"[ROUTER] Location: {res.location}")
            log.info("[ROUTER] Weather tool: CALLED")
            print(f'[ROUTER] Query: "{clean_q}"\n[ROUTER] Intent: {res.intent}' + (f'\n[ROUTER] Location: {res.location}' if res.location else '') + '\n[ROUTER] Weather tool: CALLED', flush=True)
        else:
            log.info(f'[ROUTER] Query: "{clean_q}"')
            log.info(f"[ROUTER] Intent: {res.intent}")
            log.info("[ROUTER] Weather tool: SKIPPED")
            print(f'[ROUTER] Query: "{clean_q}"\n[ROUTER] Intent: {res.intent}\n[ROUTER] Weather tool: SKIPPED', flush=True)


intent_router = IntentRouter()
