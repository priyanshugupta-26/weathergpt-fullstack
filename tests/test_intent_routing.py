"""
Tests for WeatherGPT Intelligent Intent Routing and General AI Capability
Verifies that:
1. General questions do NOT trigger weather tools or inject weather values.
2. Weather questions DO invoke real weather tools and ground responses in real data.
3. Conversational context retains locations for weather follow-ups but cleanly resets for general questions.
4. UI payload structures (intent, structured cards) are intent-aware.
"""
import pytest
from backend.services.intent_router import intent_router


def test_intent_classification_general_queries():
    general_queries = [
        "Hi",
        "Hello",
        "How are you?",
        "What is machine learning?",
        "Explain recursion in Python.",
        "Write a Java program for factorial.",
        "Who is APJ Abdul Kalam?",
        "Give me a LinkedIn caption.",
        "What is the capital of Japan?",
        "Tell me something about Guntur.",
        "Explain why humidity makes hot weather feel worse.",
        "What should I wear?",
    ]
    for q in general_queries:
        route = intent_router.classify(q)
        assert route.intent == "GENERAL", f"Query '{q}' should be classified as GENERAL, got {route.intent}"
        assert route.requires_weather_tool is False, f"Query '{q}' should NOT require weather tools"
        assert route.location is None, f"Query '{q}' should not extract weather location"


def test_intent_classification_weather_queries():
    weather_queries = [
        ("What's the weather in Guntur?", "WEATHER_CURRENT", "Guntur"),
        ("Will it rain tomorrow in Guntur?", "WEATHER_FORECAST", "Guntur"),
        ("Temperature in Delhi today?", "WEATHER_CURRENT", "Delhi"),
        ("Is Guntur hot today?", "WEATHER_CURRENT", "Guntur"),
        ("What's the weather this weekend?", "WEATHER_FORECAST", None),
        ("Will the cyclone affect Andhra Pradesh?", "DISASTER_WEATHER", "Andhra Pradesh"),
        ("Should I carry an umbrella to college tomorrow?", "WEATHER_FORECAST", None),
        ("Can I go outside tomorrow if it rains?", "WEATHER_FORECAST", None),
    ]
    for q, expected_intent, expected_loc in weather_queries:
        route = intent_router.classify(q)
        assert route.requires_weather_tool is True, f"Query '{q}' should require weather tools"
        assert route.intent == expected_intent, f"Query '{q}' expected intent {expected_intent}, got {route.intent}"
        if expected_loc:
            assert route.location and expected_loc.lower() in route.location.lower(), f"Query '{q}' expected location {expected_loc}, got {route.location}"


def test_conversational_followup_and_reset():
    # Turn 1: Weather query
    ctx = {}
    r1 = intent_router.classify("What's the temperature in Delhi?", conversation_context=ctx)
    assert r1.requires_weather_tool is True
    assert r1.location == "Delhi"

    ctx["location_name"] = "Delhi"
    ctx["last_intent"] = r1.intent

    # Turn 2: Follow-up referring to "there"
    r2 = intent_router.classify("Is it going to rain there tomorrow?", conversation_context=ctx)
    assert r2.requires_weather_tool is True
    assert r2.location == "Delhi"
    assert r2.time_range == "tomorrow"

    # Turn 3: User switches to general question -> MUST switch to GENERAL
    r3 = intent_router.classify("Explain recursion in Python.", conversation_context=ctx)
    assert r3.intent == "GENERAL"
    assert r3.requires_weather_tool is False
    assert r3.location is None


def test_api_chat_general_queries_no_weather_cards(client):
    # Test "Hi"
    r = client.post("/api/chat", json={"message": "Hi"})
    assert r.status_code == 200
    data = r.json()
    assert data.get("type") == "general"
    assert data.get("intent") == "GENERAL"
    assert data.get("structured") is None, "GENERAL response should NOT contain structured weather cards"
    assert data.get("weather") is None, "GENERAL response should NOT contain weather data"
    assert "Hi" in data.get("message") or "help" in data.get("message")
    # Verify no weather terms are forced into "Hi" response
    assert "Guntur" not in data.get("message")
    assert "precipitation" not in data.get("message").lower()

    # Test "What is machine learning?" (Test G)
    r2 = client.post("/api/chat", json={"message": "What is machine learning?"})
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2.get("type") == "general"
    assert d2.get("intent") == "GENERAL"
    assert d2.get("structured") is None
    assert "machine learning" in d2.get("message").lower() or "data" in d2.get("message").lower()

    # Test "What is Python?" (Test B)
    r_py = client.post("/api/chat", json={"message": "What is Python?"})
    assert r_py.status_code == 200
    d_py = r_py.json()
    assert d_py.get("type") == "general"
    assert d_py.get("intent") == "GENERAL"
    assert d_py.get("structured") is None
    assert "python" in d_py.get("message").lower()
    assert "Guntur" not in d_py.get("message")

    # Test "Explain recursion in simple language." (Test C)
    r_rec = client.post("/api/chat", json={"message": "Explain recursion in simple language."})
    assert r_rec.status_code == 200
    d_rec = r_rec.json()
    assert d_rec.get("type") == "general"
    assert d_rec.get("intent") == "GENERAL"
    assert d_rec.get("structured") is None
    assert "recursion" in d_rec.get("message").lower()

    # Test "Write a Python program to reverse a string."
    r_rev = client.post("/api/chat", json={"message": "Write a Python program to reverse a string."})
    assert r_rev.status_code == 200
    d_rev = r_rev.json()
    assert d_rev.get("type") == "general"
    assert d_rev.get("intent") == "GENERAL"
    assert d_rev.get("structured") is None
    assert "reversed" in d_rev.get("message").lower() or "reverse" in d_rev.get("message").lower()

    # Test "What is the capital of Japan?"
    r3 = client.post("/api/chat", json={"message": "What is the capital of Japan?"})
    assert r3.status_code == 200
    d3 = r3.json()
    assert d3.get("type") == "general"
    assert d3.get("intent") == "GENERAL"
    assert "Tokyo" in d3.get("message")


def test_api_chat_weather_queries_grounded(client):
    # Test "What's the weather in Guntur?" (Test D)
    r = client.post("/api/chat", json={"message": "What's the weather in Guntur?"})
    assert r.status_code == 200
    data = r.json()
    assert data.get("type") == "weather"
    assert data.get("intent") == "WEATHER_CURRENT"
    assert data.get("structured") is not None, "Weather response MUST contain structured weather card"
    assert data.get("weather") is not None, "Weather response MUST contain weather data"
    assert "Guntur" in data["query"]["location"] or "guntur" in data["location"]["name"].lower()

    # Test "Will it rain tomorrow in Guntur?" (Test E)
    r_rain = client.post("/api/chat", json={"message": "Will it rain tomorrow in Guntur?"})
    assert r_rain.status_code == 200
    d_rain = r_rain.json()
    assert d_rain.get("type") == "weather"
    assert d_rain.get("intent") == "WEATHER_FORECAST"
    assert d_rain.get("structured") is not None
    assert d_rain.get("weather") is not None

    # Test "Should I carry an umbrella tomorrow?" (Test F)
    r_umb = client.post("/api/chat", json={"message": "Should I carry an umbrella tomorrow?"})
    assert r_umb.status_code == 200
    d_umb = r_umb.json()
    assert d_umb.get("type") == "weather"
    assert d_umb.get("intent") == "WEATHER_FORECAST"
    assert d_umb.get("structured") is not None


def test_api_chat_followup_and_mode_switching(client):
    conv_id = "test-session-intent-switch-99"

    # 1. Weather in Delhi
    r1 = client.post("/api/chat", json={"message": "What's the temperature in Delhi?", "conversation": conv_id})
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1.get("type") == "weather"
    assert d1.get("intent") == "WEATHER_CURRENT"
    assert d1.get("structured") is not None

    # 2. Elliptical follow-up: "What about tomorrow?"
    r2 = client.post("/api/chat", json={"message": "What about tomorrow?", "conversation": conv_id})
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2.get("type") == "weather"
    assert d2.get("intent") in ("WEATHER_FORECAST", "WEATHER_CURRENT")
    assert d2.get("structured") is not None

    # 3. General switch: "Explain recursion in Python."
    r3 = client.post("/api/chat", json={"message": "Explain recursion in Python.", "conversation": conv_id})
    assert r3.status_code == 200
    d3 = r3.json()
    assert d3.get("type") == "general"
    assert d3.get("intent") == "GENERAL"
    assert d3.get("structured") is None
    assert d3.get("weather") is None
    assert "recursion" in d3.get("message").lower()
    assert "Delhi" not in d3.get("message")
