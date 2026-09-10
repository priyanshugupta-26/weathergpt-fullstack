import pytest
from datetime import datetime, timedelta, timezone
from backend.database import Session, WeatherObservation, WeatherLocation, ModelVersion, initialize

@pytest.fixture(autouse=True)
def setup_data_lab_test():
    initialize()
    with Session.begin() as db:
        loc = WeatherLocation(name="Patna", latitude=25.5941, longitude=85.1376, state="Bihar")
        db.add(loc)
        db.flush()

        base_time = datetime.now(timezone.utc)
        for i in range(10):
            t_iso = (base_time - timedelta(hours=i)).isoformat()
            db.add(
                WeatherObservation(
                    location_id=loc.id,
                    latitude=25.5941,
                    longitude=85.1376,
                    timestamp=t_iso,
                    retrieval_timestamp=t_iso,
                    provider="Open-Meteo",
                    data_type="OBSERVATION",
                    quality_flag="VALID",
                    temperature=28.0 + (i * 0.2),
                    feels_like=30.0 + (i * 0.2),
                    humidity=65.0 - (i * 0.5),
                    dew_point=20.0,
                    surface_pressure=1008.0,
                    wind_speed=8.0,
                    wind_direction=160.0,
                    rainfall=0.0,
                    precipitation=0.0,
                    cloud_cover=20.0,
                )
            )


def test_data_stats_endpoint(client):
    res = client.get("/api/data/stats")
    assert res.status_code == 200
    data = res.json()
    assert "total_observations" in data
    assert data["total_observations"] > 0
    assert "verified_observations" in data
    assert data["features_available"] == 39
    assert "latest_observation" in data
    assert "current_champion" in data
    assert "auto_learning" in data
    assert data["auto_learning"]["status"] in ("ACTIVE", "PAUSED")
    assert "pipeline_status" in data


def test_data_observations_pagination_and_filters(client):
    # Default page
    res = client.get("/api/data/observations?page=1&page_size=10")
    assert res.status_code == 200
    data = res.json()
    assert data["page"] == 1
    assert data["page_size"] == 10
    assert data["total_count"] > 0
    assert len(data["items"]) <= 10
    first = data["items"][0]
    assert "temperature" in first
    assert "humidity" in first
    assert "surface_pressure" in first
    assert "wind_speed" in first
    assert "stored" in first
    assert first["stored"] is True

    # Filter by provider
    res_om = client.get("/api/data/observations?provider=Open-Meteo&page_size=5")
    assert res_om.status_code == 200
    assert all("Open-Meteo" in item["provider"] for item in res_om.json()["items"])


def test_data_observation_feature_inspection(client):
    # Get first observation ID
    res = client.get("/api/data/observations?page=1&page_size=5")
    assert res.status_code == 200
    obs_id = res.json()["items"][0]["id"]

    res_detail = client.get(f"/api/data/observations/{obs_id}")
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert detail["observation_id"] == obs_id
    assert "used_features" in detail
    assert len(detail["used_features"]) == 39
    assert "available_unused_features" in detail
    assert len(detail["available_unused_features"]) > 0

    # Verify status tags
    assert all(f["status"] == "USED BY CURRENT MODEL" for f in detail["used_features"])
    assert all(f["status"] == "AVAILABLE BUT NOT USED" for f in detail["available_unused_features"])


def test_data_features_catalog(client):
    res = client.get("/api/data/features")
    assert res.status_code == 200
    catalog = res.json()
    assert catalog["total_features"] == 39
    assert len(catalog["features"]) == 39
    assert catalog["features"][0]["name"] == "latitude"
    assert catalog["features"][-1]["name"] == "radiation_lag_24"
    assert "targets" in catalog
    assert len(catalog["targets"]) >= 7


def test_data_growth_and_milestones(client):
    res = client.get("/api/data/growth")
    assert res.status_code == 200
    growth = res.json()
    assert "growth_series" in growth
    assert "milestones" in growth
    assert len(growth["milestones"]) > 0
    first_milestone = growth["milestones"][0]
    assert "version" in first_milestone
    assert "status" in first_milestone


def test_data_quality_report(client):
    res = client.get("/api/data/quality")
    assert res.status_code == 200
    q = res.json()
    assert "total_checked" in q
    assert q["total_checked"] > 0
    assert "missingness_by_feature" in q
    assert len(q["missingness_by_feature"]) > 5
    assert "quality_distribution" in q


def test_contributing_locations(client):
    res = client.get("/api/data/locations")
    assert res.status_code == 200
    locs = res.json()
    assert len(locs) >= 5
    first = locs[0]
    assert "name" in first
    assert "latitude" in first
    assert "longitude" in first
    assert "observation_count" in first


def test_data_export_csv(client):
    res = client.get("/api/data/export?limit=5")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/csv")
    csv_text = res.text
    assert "temperature_c" in csv_text
    assert "surface_pressure_hpa" in csv_text
    assert "wind_speed_kmh" in csv_text
    lines = [line for line in csv_text.strip().split("\n") if line]
    assert len(lines) > 1  # Header + rows


def test_ml_training_split(client):
    res = client.get("/api/ml/training-split")
    assert res.status_code == 200
    split = res.json()
    assert "train_rows" in split
    assert "validation_rows" in split
    assert "NO FUTURE DATA LEAKAGE" in split["leakage_prevention"]
    assert split["features_count"] == 39
    assert split["targets_count"] == 8


def test_ml_metrics_history(client):
    res = client.get("/api/ml/metrics/history")
    assert res.status_code == 200
    data = res.json()
    assert "history" in data
    assert len(data["history"]) > 0
    first = data["history"][0]
    assert "version" in first
    assert "status" in first


def test_ml_predictions_verification(client):
    res = client.get("/api/ml/predictions/verification?target=temperature_2m")
    assert res.status_code == 200
    data = res.json()
    assert data["target"] == "temperature_2m"
    assert "rolling_metrics" in data
    assert "items" in data
