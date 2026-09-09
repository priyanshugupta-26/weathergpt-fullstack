import copy
import pytest
from backend.providers.weather import provider, ProviderClient
from backend.services.alerts import alerts_service
from models.adapters.adapter import ModelAdapter
from backend.database import Session, User
from sqlalchemy import select

WEATHER = {
    "status": "live",
    "source": "Test fixture (not live provider)",
    "timestamp": "2026-09-09T12:00",
    "timezone": "Asia/Kolkata",
    "latitude": 25.5941,
    "longitude": 85.1376,
    "current": {
        "temperature_2m": 31,
        "apparent_temperature": 34,
        "relative_humidity_2m": 75,
        "wind_speed_10m": 12,
        "wind_gusts_10m": 18,
        "wind_direction_10m": 90,
        "precipitation": 0,
        "weather_code": 2,
    },
    "hourly": [],
    "daily": [
        {
            "temperature_2m_min": 25,
            "temperature_2m_max": 33,
            "precipitation_probability_max": 40,
            "precipitation_sum": 2,
            "wind_speed_10m_max": 15,
        },
        {
            "temperature_2m_min": 24,
            "temperature_2m_max": 30,
            "precipitation_probability_max": 70,
            "precipitation_sum": 9,
            "wind_speed_10m_max": 20,
        },
    ],
    "units": {},
}


@pytest.fixture(autouse=True)
def mock_weather(monkeypatch):
    async def weather(*args):
        return copy.deepcopy(WEATHER)

    monkeypatch.setattr(provider, "weather", weather)


def test_health_and_home(client):
    assert client.get("/api/health").json()["database"] == "ok"
    assert client.get("/").status_code == 200


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/globe",
        "/forecast",
        "/chat",
        "/alerts",
        "/climate",
        "/agriculture",
        "/aviation",
        "/marine",
        "/dashboard",
        "/profile",
        "/settings",
        "/admin",
        "/city-monitor",
        "/model-lab",
        "/setup",
    ],
)
def test_routes(client, path):
    assert client.get(path).status_code == 200


def test_forecast_and_validation(client):
    r = client.get("/api/weather/forecast")
    assert r.status_code == 200
    assert r.json()["daily"][1]["precipitation_sum"] == 9
    for query in ["latitude=100", "longitude=999", "latitude=nan", "latitude=abc"]:
        assert client.get("/api/weather/current?" + query).status_code == 422
    assert (
        client.get("/api/weather/history?start=2026-01-02&end=2026-01-01").status_code
        == 422
    )
    assert client.get("/api/does-not-exist").status_code == 404


def test_chat_fallback(client):
    r = client.post("/api/chat", json={"message": "Will it rain tomorrow?"})
    assert r.status_code == 200
    assert "70%" in r.json()["message"]
    assert r.json()["mode"] == "deterministic"
    h = client.post("/api/chat", json={"message": "Explain today weather in Hindi"})
    assert "वर्तमान" in h.json()["message"]
    assert client.post("/api/chat", json={"message": ""}).status_code == 422


def test_alerts_and_models(client):
    assert client.get("/api/alerts").json()["alerts"] == []
    assert len(client.get("/api/models/status").json()["models"]) == 2
    r = client.post(
        "/api/predict/disaster", json={"features": {"temperature_2m": 44}}
    ).json()
    assert r["severity"] == "WARNING" and r["confidence"] is None
    r = client.post("/api/predict/weather", json={"features": {}}).json()
    assert r["mode"] == "fallback" and r["prediction"] is None
    assert (
        client.post("/api/predict/weather", json={"features": {"x": "bad"}}).status_code
        == 422
    )


def test_rule_absence_not_all_clear():
    assert alerts_service.prediction({})["risk"] == "undetermined"
    assert (
        alerts_service.evaluate(
            {"status": "unavailable", "current": {"temperature_2m": 50}}
        )
        == []
    )


def test_auth_and_isolation(client):
    account = {
        "email": "test@example.com",
        "password": "WeatherTest!234",
        "name": "Test",
    }
    assert client.get("/api/profile").status_code == 401
    assert client.post("/api/auth/register", json=account).status_code == 201
    assert client.post("/api/auth/register", json=account).status_code == 409
    assert (
        client.post(
            "/api/auth/login", json={**account, "password": "incorrect-pass"}
        ).status_code
        == 401
    )
    response = client.post("/api/auth/login", json=account)
    assert response.status_code == 200 and "HttpOnly" in response.headers["set-cookie"]
    assert client.get("/api/profile").json()["name"] == "Test"
    assert client.get("/api/admin").status_code == 403
    assert (
        client.post(
            "/api/locations/saved",
            json={"name": "Patna", "latitude": 25.5, "longitude": 85.1},
        ).status_code
        == 201
    )
    locations = client.get("/api/locations/saved").json()["locations"]
    assert len(locations) == 1
    assert (
        client.patch(
            "/api/profile", json={"name": "Updated", "language": "hi"}
        ).status_code
        == 200
    )
    client.post("/api/chat", json={"message": "Weather today"})
    assert len(client.get("/api/chat/history").json()["messages"]) == 2
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/locations/saved").status_code == 401
    account2 = {**account, "email": "other@example.com"}
    client.post("/api/auth/register", json=account2)
    client.post("/api/auth/login", json=account2)
    assert client.get("/api/locations/saved").json()["locations"] == []
    assert client.get("/api/chat/history").json()["messages"] == []
    client.delete("/api/locations/saved/" + str(locations[0]["id"]))
    with Session.begin() as db:
        user = db.scalar(select(User).where(User.email == account2["email"]))
        user.role = "admin"
    assert client.get("/api/admin").status_code == 200


def test_origin_protection(client):
    assert (
        client.post(
            "/api/auth/logout", headers={"Origin": "https://evil.example"}
        ).status_code
        == 403
    )


def test_websocket(client):
    with client.websocket_connect("/ws/alerts") as ws:
        data = ws.receive_json()
        assert data["type"] == "alerts" and isinstance(data["alerts"], list)


@pytest.mark.asyncio
async def test_provider_retry_and_cache(monkeypatch):
    import httpx

    transport_calls = []

    def handler(request):
        transport_calls.append(request)
        return httpx.Response(
            503 if len(transport_calls) == 1 else 200, json={"value": 42}
        )

    c = ProviderClient()
    await c.client.aclose()
    c.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    assert (await c.get("test", "https://example.test"))["value"] == 42
    assert (await c.get("test", "https://example.test"))["value"] == 42
    assert len(transport_calls) == 2
    await c.close()


@pytest.mark.asyncio
async def test_provider_outage(monkeypatch):
    import httpx

    c = ProviderClient()
    await c.client.aclose()
    c.client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda r: httpx.Response(503))
    )
    with pytest.raises(RuntimeError):
        await c.get("test", "https://example.test")
    assert c.status["test"]["status"] == "unavailable"
    await c.close()


def test_model_order_and_missing_features():
    adapter = ModelAdapter("weather")

    class Model:
        def predict(self, data):
            assert data == [[2, 1]]
            return [3]

    adapter.model = Model()
    adapter.schema = {"features": ["b", "a"], "input_format": "array"}
    assert adapter.predict({"a": 1, "b": 2})["prediction"] == 3
    with pytest.raises(ValueError):
        adapter.predict({"a": 1})


def test_development_origin(client):
    assert (
        client.post(
            "/api/chat",
            json={"message": "Weather today"},
            headers={"Origin": "http://127.0.0.1:5173"},
        ).status_code
        == 200
    )


def test_offline_geocoding(client):
    result = client.get("/api/locations/search?q=Mumbai").json()["results"]
    assert result and abs(result[0]["latitude"] - 19.07) < 0.2
    coordinates = client.get("/api/locations/search?q=25.5,85.1").json()["results"][0]
    assert coordinates["latitude"] == 25.5


def test_chat_resolves_city(client):
    result = client.post(
        "/api/chat", json={"message": "Will it rain in Patna tomorrow?"}
    ).json()
    assert result["location"]["name"] == "Patna"
    assert "70%" in result["message"]


def test_multi_output_and_list_prediction():
    from models.adapters.adapter import ModelAdapter, FeatureBuilder

    adapter = ModelAdapter("weather")

    class MultiOutputModel:
        def predict(self, data):
            assert len(data[0]) == 2
            return [[28.5, 65.0]]

    adapter.model = MultiOutputModel()
    adapter.schema = {
        "features": ["temp", "humidity"],
        "outputs": ["predicted_temp", "predicted_rh"],
        "input_format": "array",
    }
    
    # Test dictionary input
    res_dict = adapter.predict({"temp": 27.0, "humidity": 60.0})
    assert res_dict["prediction"] == {"predicted_temp": 28.5, "predicted_rh": 65.0}

    # Test list input
    res_list = adapter.predict([27.0, 60.0])
    assert res_list["prediction"] == {"predicted_temp": 28.5, "predicted_rh": 65.0}

    # Test 39-feature weather feature builder
    obs = {
        "latitude": 21.1458,
        "longitude": 79.0882,
        "temperature_2m": 30.5,
        "relative_humidity_2m": 55.0,
        "wind_speed_10m": 12.0,
        "wind_direction_10m": 120.0,
        "surface_pressure": 1008.0,
        "shortwave_radiation": 450.0,
    }
    feats_39 = FeatureBuilder.build_weather_features(obs)
    assert len(feats_39) == 39
    assert "wet_bulb_temp" in feats_39
    assert "wind_u_vector" in feats_39
    assert "pressure_tendency_3h" in feats_39

    # Test 20-feature disaster feature builder
    telemetry = {
        "temp_2m": 32.0,
        "precip_1h": 15.0,
        "rain_48h": 50.0,
        "wind_speed_10m": 25.0,
        "surface_pressure": 995.0,
        "us_aqi": 80.0,
        "pm2_5": 35.0,
    }
    feats_20 = FeatureBuilder.build_disaster_features(telemetry)
    assert len(feats_20) == 20
    assert "wind_pressure_shear" in feats_20
    assert "precipitation_saturation_rate" in feats_20
    assert "thermal_particulate_index" in feats_20


def test_setup_endpoints(client):
    r = client.get("/api/setup/status")
    assert r.status_code == 200
    assert "local_setup_allowed" in r.json()
    assert "groq" in r.json()
    assert "gemini" in r.json()


def test_provider_status(client):
    r = client.get("/api/providers/status")
    assert r.status_code == 200
    data = r.json()
    assert "providers" in data
    assert "imd" in data
    assert "ai" in data


def test_city_monitor(client):
    r = client.get("/api/city-monitor")
    assert r.status_code == 200
    data = r.json()
    assert "cities" in data
    assert len(data["cities"]) > 5
    first = data["cities"][0]
    assert "name" in first
    assert "temperature" in first
    assert "flood_risk" in first
    assert "heat_risk" in first


def test_predict_auto_weather(client):
    r = client.post("/api/predict/auto/weather?latitude=28.6139&longitude=77.2090&name=New%20Delhi")
    assert r.status_code == 200
    data = r.json()
    assert "predicted_temp_next_hour" in data
    assert "thermal_delta" in data
    assert "features_39" in data
    assert len(data["features_39"]) == 39


def test_predict_auto_disaster(client):
    r = client.post("/api/predict/auto/disaster?latitude=28.6139&longitude=77.2090&name=New%20Delhi")
    assert r.status_code == 200
    data = r.json()
    assert "features_20" in data
    assert len(data["features_20"]) == 20
    assert "risk" in data or "event" in data
