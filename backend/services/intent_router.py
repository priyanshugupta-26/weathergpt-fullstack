"""
Query & Intent Router for WeatherGPT
Intelligently classifies user queries to determine whether weather tools are needed.
Ensures WeatherGPT behaves as a general-purpose AI assistant with weather as its specialized capability.
"""
import re
import sys
import logging
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger("weathergpt.router")


@dataclass
class IntentRouteResult:
    intent: str  # GENERAL, WEATHER_CURRENT, WEATHER_FORECAST, WEATHER_ALERT, WEATHER_HISTORICAL, CLIMATE, AGRICULTURE_WEATHER, DISASTER_WEATHER, MARINE_WEATHER, AVIATION_WEATHER, TRAVEL_WEATHER
    location: str | None = None
    time_range: str | None = None  # "today", "tomorrow", "tonight", "weekend", or None
    time_period: str | None = None  # "morning", "evening", "afternoon", "after_5pm", or None
    requires_weather_tool: bool = False
    sector: str = "general"
    route: tuple[str, str] | None = None
    is_followup: bool = False
    details: dict[str, Any] = field(default_factory=dict)


# Common greetings and social conversational phrases
GREETING_PATTERNS = [
    r"^(hi|hello|hey|greetings|howdy|hola|namaste|vanakkam|namaskara|pranam|khalas|kem\s+cho)\b",
    r"^(good\s+(morning|afternoon|evening|night|day))\b",
    r"^(how\s+are\s+you|how\'?s\s+it\s+going|how\s+do\s+you\s+do|what\'?s\s+up|sup)\b",
    r"^(who\s+are\s+you|what\s+is\s+your\s+name|what\s+can\s+you\s+do|introduce\s+yourself|tell\s+me\s+about\s+yourself)\b",
    r"^(thank\s+you|thanks|thx|bye|goodbye|see\s+you|take\s+care)\b",
]

# Patterns for general queries that must NEVER trigger weather tools
GENERAL_TOPIC_PATTERNS = [
    r"\b(machine\s+learning|deep\s+learning|artificial\s+intelligence|neural\s+network|nlp|llm)\b",
    r"\b(python|javascript|typescript|java|c\+\+|golang|rust|html|css|sql|docker|git)\b",
    r"\b(recursion|algorithm|data\s+structure|bubble\s+sort|quicksort|binary\s+search|reverse\s+a\s+string|factorial|fibonacci)\b",
    r"\b(write\s+(a\s+)?(python|java|code|program|script|function|class|essay|poem|caption|email|letter|post))\b",
    r"\b(linkedin\s+caption|resume|cover\s+letter|joke|story|recipe)\b",
    r"\b(who\s+is|who\s+was|biography\s+of|tell\s+me\s+about\s+apj|abdul\s+kalam)\b",
    r"\b(capital\s+of|currency\s+of|president\s+of|prime\s+minister\s+of)\b",
    r"\b(photosynthesis|mitochondria|gravity|theory\s+of\s+relativity|quantum|dna|rna)\b",
]

# Scientific / educational weather questions (theoretical explanation, no live weather data needed)
THEORETICAL_WEATHER_PATTERNS = [
    r"^explain\s+(why|how)\s+.*(humidity|hot\s+weather|rain|wind|cyclone|cloud|temperature|fog|frost)",
    r"^why\s+does\s+(humidity\s+make\s+hot\s+weather\s+feel\s+worse|humid\s+weather\s+feel\s+hotter|it\s+rain|wind\s+blow|hot\s+air\s+rise)",
    r"^what\s+(is|causes)\s+(the\s+greenhouse\s+effect|el\s+nino|la\s+nina|a\s+cyclone|a\s+tsunami|humidity|atmospheric\s+pressure|coriolis)",
    r"^how\s+(does|do)\s+(clouds\s+form|rain\s+form|hurricanes\s+form|cyclones\s+form|barometers\s+work)",
]

# General knowledge about locations (e.g. "Tell me something about Guntur")
GENERAL_LOCATION_PATTERNS = [
    r"^(tell\s+me\s+(something|more)?\s*(about)?|what\s+is\s+the\s+history\s+of|history\s+of|culture\s+of|places\s+to\s+visit\s+in|famous\s+for|population\s+of)\s+([a-zA-Z\s]+)$",
]


class IntentRouter:
    """
    Intelligent query router that classifies user messages into structured intents.
    Determines whether weather tools, location resolution, or live weather APIs are needed.
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

        # Check explicit sector hints from specialized tabs (e.g. /agriculture, /marine)
        if sector_hint and sector_hint != "general":
            res = self._classify_weather(text, lower, context, forced_sector=sector_hint)
            self._log(message, res)
            return res

        # 2. Check for Greetings / Casual Conversational Queries
        for pat in GREETING_PATTERNS:
            if re.search(pat, clean_text, re.I):
                res = IntentRouteResult(
                    intent="GENERAL",
                    location=None,
                    time_range=None,
                    requires_weather_tool=False,
                    sector="general",
                )
                self._log(message, res)
                return res

        # 3. Check for Theoretical / Educational Science questions
        for pat in THEORETICAL_WEATHER_PATTERNS:
            if re.search(pat, lower, re.I):
                res = IntentRouteResult(
                    intent="GENERAL",
                    location=None,
                    time_range=None,
                    requires_weather_tool=False,
                    sector="general",
                )
                self._log(message, res)
                return res

        # 4. Check for General Knowledge about a place (e.g., "Tell me something about Guntur")
        for pat in GENERAL_LOCATION_PATTERNS:
            m = re.match(pat, clean_text, re.I)
            if m:
                # Unless it specifically contains a weather word like "weather", "rain", "temperature"
                if not any(w in lower for w in ("weather", "rain", "temperature", "temp", "forecast", "climate", "hot", "cold", "humidity", "wind")):
                    res = IntentRouteResult(
                        intent="GENERAL",
                        location=None,
                        time_range=None,
                        requires_weather_tool=False,
                        sector="general",
                    )
                    self._log(message, res)
                    return res

        # 5. Check for General Programming, Writing, Math, and Knowledge Topics
        for pat in GENERAL_TOPIC_PATTERNS:
            if re.search(pat, lower, re.I):
                # Ensure no explicit live weather query is piggybacking
                if not any(w in lower for w in ("what's the weather", "temperature today", "rain tomorrow", "current weather")):
                    res = IntentRouteResult(
                        intent="GENERAL",
                        location=None,
                        time_range=None,
                        requires_weather_tool=False,
                        sector="general",
                    )
                    self._log(message, res)
                    return res

        # 6. Check for Pure General Questions (e.g., "What should I wear?", "Should I go outside?")
        # Without weather context or location, these are general questions.
        if lower in ("what should i wear", "what should i wear today", "what can i wear", "how should i dress"):
            # Check if there is active weather conversation context
            if not context.get("location_name") or context.get("last_intent") == "GENERAL":
                res = IntentRouteResult(
                    intent="GENERAL",
                    location=None,
                    time_range=None,
                    requires_weather_tool=False,
                    sector="general",
                )
                self._log(message, res)
                return res

        # 7. Check for Conversational Elliptical Follow-ups (e.g., "What about tomorrow?", "Will it rain there tomorrow?")
        is_followup = self._is_elliptical_followup(lower)
        last_intent = context.get("last_intent")

        if is_followup and last_intent and last_intent != "GENERAL":
            res = self._handle_followup(text, lower, context)
            self._log(message, res)
            return res

        # 8. Check for Weather & Specialized Domain Inquiries
        weather_res = self._classify_weather(text, lower, context)
        if weather_res.requires_weather_tool:
            self._log(message, weather_res)
            return weather_res

        # 9. Default: GENERAL query (No weather tools invoked)
        res = IntentRouteResult(
            intent="GENERAL",
            location=None,
            time_range=None,
            requires_weather_tool=False,
            sector="general",
        )
        self._log(message, res)
        return res

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
        prior_intent = context.get("last_intent", "WEATHER_FORECAST")

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

        # Check if a new location was mentioned in the follow-up (e.g., "and in Delhi?")
        new_loc = self._extract_location(text)
        location = new_loc or prior_location

        intent = "WEATHER_FORECAST" if time_target in ("tomorrow", "weekend") or "rain" in lower else (prior_intent if prior_intent != "GENERAL" else "WEATHER_CURRENT")

        return IntentRouteResult(
            intent=intent,
            location=location,
            time_range=time_target or context.get("time_target", "today"),
            time_period=time_period or context.get("time_period", "all_day"),
            requires_weather_tool=True,
            sector=prior_sector,
            is_followup=True,
        )

    def _classify_weather(
        self,
        text: str,
        lower: str,
        context: dict[str, Any],
        forced_sector: str | None = None,
    ) -> IntentRouteResult:
        # Check routes (e.g. "Patna to Ranchi" or "travel from Patna to Ranchi")
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

        if any(w in lower for w in agri_words):
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

        # Check weather trigger keywords
        weather_words = [
            "weather", "temperature", "temp", "forecast", "climate", "hot", "cold",
            "warm", "chilly", "humid", "humidity", "heat", "garmi", "sardi", "thand", "mausam",
            "हवामान", "వాతావరణం", "வானிலை", "আবহাওয়া", "موسم",
            "rain", "raining", "rainy", "rainfall", "drizzle", "shower", "downpour",
            "barish", "baarish", "वर्षा", "వర్షం", "மழை", "বৃষ্টি", "पाऊस", "paus", "بارش", "umbrella",
            "wind", "windy", "breeze", "gust", "storm", "cyclone", "चक्रवात", "తుఫాను", "புயல்", "toofan", "طوفان",
            "alert", "warning", "flood", "earthquake", "lightning", "thunderstorm", "bijli", "बिजली", "चेतावनी", "హెచ్చరిక",
            "pressure", "barometer", "aqi", "air quality", "pollution", "squall", "hail", "frost", "fog", "mist", "snow", "sunny"
        ]

        has_weather_word = any(w in lower for w in weather_words)

        # Mixed queries: e.g. "Should I carry an umbrella to college tomorrow?" or "Can I go outside tomorrow if it rains?"
        is_mixed_weather_question = any(phrase in lower for phrase in [
            "carry an umbrella", "take an umbrella", "need an umbrella", "umbrella",
            "go outside tomorrow if it rains", "safe to travel", "should i spray",
            "can i spray", "should i irrigate", "can i travel"
        ])

        # Temperature / heat inquiry for a place: e.g. "Is Guntur hot today?"
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
                intent="GENERAL",
                location=None,
                time_range=None,
                requires_weather_tool=False,
                sector="general",
            )

        # Location extraction
        location = self._extract_location(text)
        if not location and "there" in lower and context.get("location_name"):
            location = context.get("location_name")

        # Intent classification
        intent = "WEATHER_CURRENT"
        if any(w in lower for w in ("cyclone", "चक्रवात", "తుఫాను", "earthquake", "flood")):
            intent = "DISASTER_WEATHER"
        elif any(w in lower for w in ("warning", "alert", "चेतावनी", "హెచ్చరిక")):
            intent = "WEATHER_ALERT"
        elif any(w in lower for w in ("history", "historical", "last month", "पिछले")):
            intent = "WEATHER_HISTORICAL"
        elif any(w in lower for w in ("climate trend", "climate change", "global warming")):
            intent = "CLIMATE"
        elif sector == "agriculture":
            intent = "AGRICULTURE_WEATHER"
        elif sector == "marine":
            intent = "MARINE_WEATHER"
        elif sector == "aviation":
            intent = "AVIATION_WEATHER"
        elif sector == "travel" or route:
            intent = "TRAVEL_WEATHER"
        elif time_target in ("tomorrow", "weekend") or any(w in lower for w in ("forecast", "will it rain", "is it going to rain", "upcoming")):
            intent = "WEATHER_FORECAST"
        elif is_temp_inquiry or any(w in lower for w in ("temperature", "temp", "hot", "cold", "humidity", "current", "weather")):
            intent = "WEATHER_CURRENT"

        return IntentRouteResult(
            intent=intent,
            location=location,
            time_range=time_target or "today",
            time_period=time_period or "all_day",
            requires_weather_tool=True,
            sector=sector,
            route=route,
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

        # Pattern 3: "<location> weather"
        if not location:
            m_city_weather = re.search(r"\b([a-zA-Z]{3,})\s+weather\b", text, re.I)
            if m_city_weather and m_city_weather.group(1).lower() not in (
                "the", "today", "tomorrow", "this", "bad", "good", "local", "current", "what", "whats"
            ):
                location = m_city_weather.group(1).strip()

        if location:
            # Exclude false positives (languages, pronouns, generic terms)
            excluded = {
                "hindi", "english", "tamil", "telugu", "urdu", "bengali", "marathi", "gujarati", "kannada", "malayalam", "odia", "punjabi", "assamese",
                "my area", "the area", "my farm", "the farm", "here", "there", "the sea", "the coast", "college", "school", "office", "home",
                "me", "us", "him", "her", "them", "it", "this", "that", "the", "what", "whats", "a", "an"
            }
            if location.lower() in excluded:
                return None
            # Clean trailing prepositions or spaces
            location = re.sub(r"\s+(to|from|and|or|with)$", "", location, flags=re.I).strip()
            return location if len(location) >= 2 else None

        return None

    def _log(self, query: str, res: IntentRouteResult):
        clean_q = query.strip().replace("\n", " ")
        if res.requires_weather_tool:
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
