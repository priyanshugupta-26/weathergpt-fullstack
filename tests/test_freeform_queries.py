"""
Test Suite: 50+ Diverse Free-Form Natural Language Queries & Follow-ups
Tests semantic variations, multilingual prompts (Hindi, Telugu, Tamil, Urdu, Bengali),
paraphrases, and conversational context retention.
"""
import copy
import pytest
from backend.providers.weather import provider

WEATHER_FIXTURE = {
    "status": "live",
    "source": "Open-Meteo Ensemble",
    "timestamp": "2026-09-10T08:00:00Z",
    "timezone": "Asia/Kolkata",
    "latitude": 25.5941,
    "longitude": 85.1376,
    "current": {
        "temperature_2m": 31.5,
        "apparent_temperature": 36.2,
        "relative_humidity_2m": 78,
        "wind_speed_10m": 12.0,
        "wind_gusts_10m": 19.5,
        "wind_direction_10m": 110,
        "precipitation": 0.0,
        "surface_pressure": 1004.2,
        "weather_code": 2,
    },
    "hourly": [
        {"time": "2026-09-10T08:00", "temperature_2m": 31.5, "precipitation": 0.0, "precipitation_probability": 10, "wind_speed_10m": 12.0},
        {"time": "2026-09-10T14:00", "temperature_2m": 33.0, "precipitation": 0.5, "precipitation_probability": 30, "wind_speed_10m": 14.0},
        {"time": "2026-09-10T17:00", "temperature_2m": 29.0, "precipitation": 6.2, "precipitation_probability": 75, "wind_speed_10m": 24.0},
    ],
    "daily": [
        {
            "time": "2026-09-10",
            "temperature_2m_min": 25.0,
            "temperature_2m_max": 33.5,
            "precipitation_probability_max": 75,
            "precipitation_sum": 6.8,
            "wind_speed_10m_max": 24.0,
        },
        {
            "time": "2026-09-11",
            "temperature_2m_min": 24.0,
            "temperature_2m_max": 31.0,
            "precipitation_probability_max": 65,
            "precipitation_sum": 12.5,
            "wind_speed_10m_max": 22.0,
        },
    ],
    "units": {},
}

DIVERSE_50_PROMPTS = [
    # 1-8: Agriculture (Spraying, Drift, Wash-off)
    ("Should I spray pesticide tomorrow morning?", "agriculture"),
    ("Will strong winds affect spraying near my farm?", "agriculture"),
    ("Kal subah khet me keetnashak chhidakna theek rahega?", "agriculture"),
    ("Can I apply fungicide if it might drizzle later?", "agriculture"),
    ("Is it too windy right now for chemical dusting?", "agriculture"),
    ("What is the wind limit for spraying wheat?", "agriculture"),
    ("Dawa chhidakne ke liye sabse achha samay kaun sa hai?", "agriculture"),
    ("Pesticide wash-off risk tomorrow afternoon?", "agriculture"),

    # 9-16: Agriculture (Irrigation, Fertilizer, Crops)
    ("I am growing rice, should I irrigate tomorrow?", "agriculture"),
    ("Rain aa rahi hai to fertilizer kab dalu?", "agriculture"),
    ("Khad dalne se pehle mausam dekhna hai", "agriculture"),
    ("Should I pump canal water into the paddy field today?", "agriculture"),
    ("Top-dressing urea timing with upcoming rain", "agriculture"),
    ("Khet me paani lagayein ya baarish ka intezar karein?", "agriculture"),
    ("Will heavy showers leach nitrogen fertilizer tonight?", "agriculture"),
    ("Cotton crop irrigation advice for this week", "agriculture"),

    # 17-24: Marine & Coastal Fishing
    ("Is the sea safe for a small fishing boat near Visakhapatnam tomorrow?", "marine"),
    ("Kal machhli pakadne jana safe hai kya?", "marine"),
    ("What wave conditions are expected on this coast?", "marine"),
    ("Can small fiberglass boats launch from Chennai port?", "marine"),
    ("Offshore swell height prediction for tomorrow morning", "marine"),
    ("Samundar me leharon ki unchai kitni rahegi kal?", "marine"),
    ("Is there any squall or rough sea warning for fishermen?", "marine"),
    ("Visakhapatnam coastal wind speed over water", "marine"),

    # 25-30: Aviation & Runway Conditions
    ("Is VFR flight feasible from Patna airport tomorrow morning?", "aviation"),
    ("What is the surface visibility and crosswind at Delhi airport?", "aviation"),
    ("Can private aircraft fly through expected convective clouds?", "aviation"),
    ("Runway wind gusts and turbulence check for Ranchi flight", "aviation"),
    ("Cloud base ceiling and low-level wind shear risk", "aviation"),
    ("VFR ya IFR flying conditions kal subah?", "aviation"),

    # 31-36: Travel & Commute
    ("Can I travel from Patna to Ranchi tomorrow morning?", "travel"),
    ("Will rain disrupt driving between Lucknow and Varanasi?", "travel"),
    ("Patna se Ranchi raste me baarish ka kya haal hai?", "travel"),
    ("Best time of day to drive without thunderstorm risk", "travel"),
    ("Road travel safety during evening squall", "travel"),
    ("Kolkata to Digha highway weather conditions", "travel"),

    # 37-42: Disasters & Meteorological Physics
    ("Why is there a thunderstorm warning?", "disaster"),
    ("What will happen if pressure keeps falling?", "disaster"),
    ("Lightning safety instructions for rural open fields", "disaster"),
    ("Bijli girne ka khatra kab tak hai?", "disaster"),
    ("Explain the barometric pressure drop trend", "general"),
    ("Flash flood warning advisory check", "disaster"),

    # 43-46: Comparisons & Temporal Analytics
    ("Compare today's wind with yesterday.", "general"),
    ("Which part of the day has lowest rain risk?", "general"),
    ("Kis samay sabse kam baarish hone ki sambhavna hai?", "general"),
    ("Morning vs evening temperature drop", "general"),

    # 47-52: Scheduled Indian Languages
    ("Explain this warning in Telugu.", "te"),
    ("ఈ హెచ్చరికను తెలుగులో వివరించండి", "te"),
    ("நாளை மழை பெய்யுமா?", "ta"),
    ("কাল কি বৃষ্টি হবে পাটনায়?", "bn"),
    ("موسم کی تازہ ترین صورتحال بتائیں", "ur"),
    ("उद्या मुंबईत पाऊस पडेल का?", "mr"),
]


@pytest.fixture(autouse=True)
def patch_weather(monkeypatch):
    async def fake_weather(*args, **kwargs):
        return copy.deepcopy(WEATHER_FIXTURE)
    monkeypatch.setattr(provider, "weather", fake_weather)


@pytest.mark.parametrize("query,expected_sector", DIVERSE_50_PROMPTS)
def test_freeform_prompt_evaluation(client, query, expected_sector):
    """Verifies that arbitrary, non-predefined natural language queries are answered intelligently."""
    resp = client.post("/api/chat", json={"message": query})
    assert resp.status_code == 200, f"Query failed: {query}"
    data = resp.json()
    assert "message" in data and len(data["message"]) > 0
    # Verify structured answer schema exists
    assert "structured" in data
    st = data["structured"]
    assert "summary" in st and len(st["summary"]) > 0
    assert "key_points" in st and isinstance(st["key_points"], list)
    assert "actions" in st and isinstance(st["actions"], list)
    assert "sources" in st and isinstance(st["sources"], list)
    assert len(st["sources"]) > 0


def test_conversational_followup_retention(client):
    """Verifies conversational follow-ups retain location and context."""
    conv_id = "test-session-followup-1"

    # Turn 1: Specific question with location and time
    r1 = client.post("/api/chat", json={
        "message": "Will it rain tomorrow in Patna?",
        "conversation": conv_id,
    })
    assert r1.status_code == 200
    res1 = r1.json()
    assert "Patna" in res1["query"]["location"] or "patna" in res1["location"]["name"].lower()
    assert res1["query"]["time_target"] == "tomorrow"

    # Turn 2: Follow-up specifying only time period ("What about evening?")
    r2 = client.post("/api/chat", json={
        "message": "What about evening?",
        "conversation": conv_id,
    })
    assert r2.status_code == 200
    res2 = r2.json()
    # Must retain Patna and tomorrow
    assert res2["query"]["time_target"] == "tomorrow"
    assert "Patna" in res2["query"]["location"] or "patna" in res2["location"]["name"].lower()
    assert res2["query"]["time_period"] == "evening"

    # Turn 3: Marine follow-up
    conv_marine = "test-session-marine-2"
    m1 = client.post("/api/chat", json={
        "message": "Is fishing safe tomorrow near Chennai?",
        "conversation": conv_marine,
    })
    assert m1.status_code == 200
    assert m1.json()["query"]["sector"] == "marine"

    m2 = client.post("/api/chat", json={
        "message": "What about after 5 PM?",
        "conversation": conv_marine,
    })
    assert m2.status_code == 200
    assert m2.json()["query"]["sector"] == "marine"
    assert m2.json()["query"]["time_period"] == "after_5pm"
