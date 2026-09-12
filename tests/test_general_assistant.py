import pytest
from backend.services.intent_router import intent_router
from backend.services.orchestrator import weather_orchestrator
from backend.schemas import ChatRequest
from backend.database import initialize

initialize()


def test_case_1_greeting_hi():
    res = intent_router.classify("Hi")
    assert res.intent == "greeting"
    assert res.domain == "general"
    assert res.requires_live_data is False
    assert res.requires_location is False
    assert res.requires_weather_tool is False


def test_case_2_greeting_hello():
    res = intent_router.classify("Hello")
    assert res.intent == "greeting"
    assert res.domain == "general"
    assert res.requires_live_data is False
    assert res.requires_location is False


def test_case_3_casual_how_are_you():
    res = intent_router.classify("How are you?")
    assert res.domain == "general"
    assert res.requires_live_data is False
    assert res.requires_location is False


def test_case_4_general_machine_learning():
    res = intent_router.classify("What is machine learning?")
    assert res.intent == "general"
    assert res.domain == "general"
    assert res.requires_live_data is False
    assert res.requires_location is False


def test_case_5_programming_binary_search():
    res = intent_router.classify("Write Python code for binary search.")
    assert res.intent == "general"
    assert res.domain == "general"
    assert res.requires_live_data is False
    assert res.requires_location is False


def test_case_6_biography_einstein():
    res = intent_router.classify("Who is Albert Einstein?")
    assert res.intent == "general"
    assert res.domain == "general"
    assert res.requires_live_data is False
    assert res.requires_location is False


def test_case_7_casual_joke():
    res = intent_router.classify("Tell me a joke.")
    assert res.domain == "general"
    assert res.requires_live_data is False
    assert res.requires_location is False


def test_case_8_weather_question_guntur():
    res = intent_router.classify("What's the weather in Guntur?")
    assert res.domain == "weather"
    assert res.intent == "weather_current"
    assert res.location == "Guntur"
    assert res.requires_live_data is True
    assert res.requires_location is True


def test_case_9_weather_forecast_here():
    res = intent_router.classify("Will it rain here tomorrow?")
    assert res.domain == "weather"
    assert res.intent == "weather_forecast"
    assert res.requires_live_data is True
    assert res.requires_location is True
    assert res.time_range == "tomorrow"


def test_case_10_temperature_inquiry():
    res = intent_router.classify("What is the temperature?")
    assert res.domain == "weather"
    assert res.requires_live_data is True
    assert res.requires_location is True


def test_case_11_disaster_cyclone_warning_near_me():
    res = intent_router.classify("Is there a cyclone warning near me?")
    assert res.domain == "disaster"
    assert res.intent == "disaster_live"
    assert res.requires_live_data is True
    assert res.requires_location is True


def test_case_12_agro_advisory_rice_field():
    res = intent_router.classify("Should I irrigate my rice field today?")
    assert res.domain == "agro"
    assert res.intent == "agro_advisory"
    assert res.requires_live_data is True
    assert res.requires_location is True


def test_case_13_mixed_greeting_and_weather():
    # Starts with 'Hi', but the actual intent is weather!
    res = intent_router.classify("Hi, will it rain tomorrow?")
    assert res.domain == "weather"
    assert res.intent == "weather_forecast"
    assert res.requires_live_data is True
    assert res.requires_location is True


def test_case_14_educational_vs_live_disaster():
    # Educational question about cyclones -> GENERAL
    res_edu = intent_router.classify("Explain cyclones.")
    assert res_edu.domain == "general"
    assert res_edu.requires_live_data is False
    assert res_edu.requires_location is False

    res_edu2 = intent_router.classify("What is a cyclone?")
    assert res_edu2.domain == "general"
    assert res_edu2.requires_live_data is False

    # Live warning question -> DISASTER
    res_live = intent_router.classify("Is there a cyclone near me?")
    assert res_live.domain == "disaster"
    assert res_live.requires_live_data is True


def test_case_15_educational_vs_live_rainfall():
    # Educational question about rainfall -> GENERAL
    res_rain = intent_router.classify("What is rainfall?")
    assert res_rain.domain == "general"
    assert res_rain.requires_live_data is False

    # Specific live forecast -> WEATHER
    res_live_rain = intent_router.classify("How much rainfall will Guntur get tomorrow?")
    assert res_live_rain.domain == "weather"
    assert res_live_rain.location == "Guntur"
    assert res_live_rain.requires_live_data is True


def test_keyword_traps_not_weather():
    # 'weathering in rocks' is geology, not weather
    res_geology = intent_router.classify("Explain the process of weathering in rocks")
    assert res_geology.domain == "general"
    assert res_geology.requires_live_data is False

    # 'Python random forest' is ML, not an environmental query
    res_rf = intent_router.classify("Write Python code for random forest classification")
    assert res_rf.domain == "general"
    assert res_rf.requires_live_data is False


def test_educational_concepts_general():
    assert intent_router.classify("What is humidity?").domain == "general"
    assert intent_router.classify("What is AQI?").domain == "general"
    assert intent_router.classify("Why are summers hot?").domain == "general"
    assert intent_router.classify("What is farming?").domain == "general"

    # In contrast, live requests for those parameters trigger specialized domains:
    assert intent_router.classify("Humidity in Guntur").domain == "weather"
    assert intent_router.classify("AQI in Delhi today").domain == "air_quality"
    assert intent_router.classify("What crops should I grow based on today's weather?").domain == "agro"


def test_multilingual_greeting_and_weather():
    # Hindi greeting
    assert intent_router.classify("नमस्ते").intent == "greeting"
    assert intent_router.classify("नमस्ते").domain == "general"

    # Hindi weather query
    res_hi = intent_router.classify("गुंटूर में आज बारिश होगी क्या?")
    assert res_hi.domain == "weather"
    assert res_hi.requires_live_data is True

    # Hindi general query
    assert intent_router.classify("Machine learning क्या है?").domain == "general"


@pytest.mark.asyncio
async def test_orchestrator_general_with_coordinates_does_not_use_location():
    # Crucial test: Sending GPS coordinates with 'Hi' MUST NOT set city_name or invoke weather
    req = ChatRequest(
        message="Hi",
        latitude=16.3067,
        longitude=80.4365,
        name="Guntur",
    )
    ans = await weather_orchestrator.answer(req)
    assert ans["intent"] == "greeting"
    assert ans["response_mode"] == "general"
    assert ans["city_name"] is None
    assert ans["weather"] is None
    assert ans["structured"] is None
    assert "WeatherGPT" in ans["reply"] or "Hi" in ans["reply"]


@pytest.mark.asyncio
async def test_orchestrator_multi_turn_topic_switch():
    conv_id = "test-multi-turn-session"

    # Turn 1: Weather query
    req1 = ChatRequest(
        message="What is the weather in Guntur?",
        conversation=conv_id,
        latitude=16.3067,
        longitude=80.4365,
        name="Guntur",
    )
    ans1 = await weather_orchestrator.answer(req1)
    assert ans1["response_mode"] == "weather"
    assert ans1["city_name"] == "Guntur"
    assert ans1["weather"] is not None

    # Turn 2: Follow-up regarding tomorrow
    req2 = ChatRequest(
        message="And tomorrow?",
        conversation=conv_id,
        latitude=16.3067,
        longitude=80.4365,
        name="Guntur",
    )
    ans2 = await weather_orchestrator.answer(req2)
    assert ans2["response_mode"] == "weather"
    assert ans2["city_name"] == "Guntur"

    # Turn 3: Topic switch to general programming
    req3 = ChatRequest(
        message="What is Python?",
        conversation=conv_id,
        latitude=16.3067,
        longitude=80.4365,
        name="Guntur",
    )
    ans3 = await weather_orchestrator.answer(req3)
    assert ans3["response_mode"] == "general"
    assert ans3["city_name"] is None
    assert ans3["weather"] is None
    assert "Python" in ans3["reply"]
    # Ensure Guntur is NOT injected into Python response
    assert "Guntur" not in ans3["reply"]
