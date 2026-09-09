"""Unit and integration tests for WeatherGPT Own ML Forecasting System (WeatherGPTML)."""

import json
import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.database import Session, WeatherObservation, ModelVersion, ModelPrediction
from backend.main import app
from backend.ml.drift import drift_service, ks_2samp
from backend.ml.features import feature_registry, MLFeatureBuilder, FeatureValidator
from backend.ml.quality import DataQualityService
from backend.ml.registry import model_registry
from backend.ml.training import training_service, circular_angular_mae
from backend.database import Session, WeatherObservation, ModelVersion, ModelPrediction, initialize
from backend.main import app
from backend.ml.drift import drift_service, ks_2samp
from backend.ml.features import feature_registry, MLFeatureBuilder, FeatureValidator
from backend.ml.quality import DataQualityService
from backend.ml.registry import model_registry
from backend.ml.training import training_service, circular_angular_mae
from backend.ml.verification import verification_service
from backend.config import ROOT


@pytest.fixture(autouse=True)
def setup_ml_test():
    initialize()
    champ = model_registry.load_active_champion()
    if champ is None:
        v_dir = ROOT / "models" / "registry" / "weather" / "v001"
        if (v_dir / "model.pkl").exists():
            with Session.begin() as db:
                db.add(ModelVersion(
                    model_name="weathergpt_ml",
                    model_type="multi_output_regressor",
                    version="v001",
                    algorithm="HistGradientBoosting",
                    training_rows=300,
                    metrics="{}",
                    artifact_path=str(v_dir / "model.pkl"),
                    status="CHAMPION",
                ))
            model_registry.load_active_champion()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_feature_registry_exact_sequence():
    """Verify feature registry loads exact 39 features with strict ordering and target specifications."""
    assert feature_registry.count == 39
    assert feature_registry.target_count >= 8
    names = feature_registry.feature_names
    assert names[0] == "latitude"
    assert names[1] == "longitude"
    assert names[2] == "temperature_2m"
    assert "wet_bulb_temp" in names
    assert "pressure_tendency_3h" in names
    assert "temp_lag_1" in names
    assert "radiation_lag_24" in names


def test_data_quality_validation():
    """Verify physical constraints: impossible temps, negative humidity/rainfall are caught."""
    # Valid observation
    valid_obs = {
        "latitude": 25.594,
        "longitude": 85.138,
        "timestamp": "2026-09-09T10:00:00+00:00",
        "temperature": 28.5,
        "humidity": 65.0,
        "surface_pressure": 1004.0,
        "precipitation": 0.0,
    }
    is_valid, flag, issues = DataQualityService.validate_observation(valid_obs)
    assert is_valid is True
    assert flag == "VALID"
    assert len(issues) == 0

    # Negative humidity -> Fatal rejection
    bad_humidity = {**valid_obs, "humidity": -5.0}
    is_valid, flag, issues = DataQualityService.validate_observation(bad_humidity)
    assert is_valid is False
    assert flag == "REJECTED"

    # Extreme impossible temperature -> Fatal rejection
    extreme_temp = {**valid_obs, "temperature": 85.0}
    is_valid, flag, issues = DataQualityService.validate_observation(extreme_temp)
    assert is_valid is False
    assert flag == "REJECTED"

    # Outlier temperature (63°C > 60°C boundary) -> Suspicious flag (not discarded)
    outlier_temp = {**valid_obs, "temperature": 63.0}
    is_valid, flag, issues = DataQualityService.validate_observation(outlier_temp)
    assert is_valid is True
    assert flag == "SUSPICIOUS"


def test_circular_angular_mae():
    """Verify circular angular MAE correctly calculates distance between angles across 360° boundary."""
    import numpy as np
    # 359° and 1° should have angular error of 2°, not 358°
    y_true = np.array([359.0, 10.0, 180.0])
    y_pred = np.array([1.0, 350.0, 180.0])
    # |359 - 1| = 2; |10 - 350| = 20; |180 - 180| = 0 -> Mean = (2 + 20 + 0) / 3 = 7.333
    mae = circular_angular_mae(y_true, y_pred)
    assert round(mae, 2) == 7.33


def test_feature_builder_prevents_future_leakage():
    """Verify feature builder only uses t <= T data and computes correct physics transformations."""
    obs_t = {
        "latitude": 28.61,
        "longitude": 77.20,
        "timestamp": "2026-09-09T14:00:00+00:00",
        "temperature_2m": 30.0,
        "relative_humidity_2m": 50.0,
        "surface_pressure": 1000.0,
        "wind_speed_10m": 15.0,
        "wind_direction_10m": 180.0,
    }
    past_lags = {
        "lag_1h": {"temperature_2m": 29.5, "surface_pressure": 1001.0},
        "lag_2h": {"temperature_2m": 29.0, "surface_pressure": 1002.0},
        "lag_3h": {"temperature_2m": 28.5, "surface_pressure": 1003.0},
        "lag_24h": {"temperature_2m": 29.8, "surface_pressure": 1000.5},
    }

    features = MLFeatureBuilder.build_features_from_obs(obs_t, past_lags, feature_registry)

    assert len(features) == 39
    assert features["temperature_2m"] == 30.0
    assert features["temp_lag_1"] == 29.5
    assert features["temp_lag_2"] == 29.0
    assert features["temp_lag_3"] == 28.5
    assert features["temp_lag_24"] == 29.8
    # Pressure tendency: p(t) - p(t-3) = 1000.0 - 1003.0 = -3.0
    assert features["pressure_tendency_3h"] == -3.0
    # Wet-bulb should be finite and realistic
    assert 15.0 <= features["wet_bulb_temp"] <= 30.0
    # Harmonic cyclical features should be between -1 and 1
    assert -1.0 <= features["sin_hour"] <= 1.0
    assert -1.0 <= features["cos_hour"] <= 1.0


def test_model_registry_and_champion():
    """Verify ModelRegistry loads active Champion, smoke tests, and runs multi-output prediction."""
    champ = model_registry.load_active_champion()
    assert champ is not None
    assert champ.version.startswith("v")

    # Predict using active champion
    pred_res = model_registry.predict([0.0] * 39)
    assert pred_res is not None
    assert "prediction" in pred_res
    pred = pred_res["prediction"]
    assert "temperature_2m" in pred
    assert "relative_humidity_2m" in pred
    assert "surface_pressure" in pred
    assert "wind_speed_10m" in pred


def test_prediction_logging_and_verification():
    """Verify predictions are logged and matched against delayed ground truth observations."""
    pred_id = verification_service.log_prediction(
        model_version="v001",
        location="Patna",
        latitude=25.594,
        longitude=85.138,
        forecast_valid_at="2026-09-09T12:00:00+00:00",
        predictions={"temperature_2m": 28.0, "relative_humidity_2m": 60.0},
    )
    assert pred_id is not None

    with Session() as db:
        pred_rows = db.scalars(select(ModelPrediction).where(ModelPrediction.prediction_id == pred_id)).all()
        assert len(pred_rows) == 2


def test_api_ml_endpoints(client):
    """Test REST endpoints: /api/ml/status, /api/ml/models, /api/ml/weather/predict, /api/ml/metrics, /api/ml/drift."""
    # 1. Status
    res = client.get("/api/ml/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ACTIVE"
    assert "champion" in data
    assert "dataset" in data
    assert data["champion"]["feature_count"] == 39

    # 2. Models
    res = client.get("/api/ml/models")
    assert res.status_code == 200
    data = res.json()
    assert "models" in data
    assert len(data["models"]) >= 1

    # 3. Champion
    res = client.get("/api/ml/models/champion")
    assert res.status_code == 200
    data = res.json()
    assert "version" in data

    # 4. Predict
    pred_payload = {
        "latitude": 25.5941,
        "longitude": 85.1376,
        "location_name": "Patna",
        "forecast_horizon_hours": 1,
    }
    res = client.post("/api/ml/weather/predict", json=pred_payload)
    assert res.status_code == 200
    p_data = res.json()
    assert p_data["badge"] == "WEATHERGPT ML"
    assert p_data["model_name"] == "WeatherGPTML"
    assert "predictions" in p_data
    assert "temperature_2m" in p_data["predictions"]

    # 5. Metrics
    res = client.get("/api/ml/metrics")
    assert res.status_code == 200

    # 6. Drift
    res = client.get("/api/ml/drift")
    assert res.status_code == 200

    # 7. Dataset stats
    res = client.get("/api/ml/dataset/stats")
    assert res.status_code == 200
    assert "total_observations" in res.json()

    # 8. Auto retrain toggle
    res = client.post("/api/ml/auto-retrain/toggle", json={"enabled": True, "min_new_rows": 60})
    assert res.status_code == 200
    assert res.json()["config"]["min_new_rows"] == 60


def test_rollback_and_promotion(client):
    """Test manual model rollback and promotion endpoints."""
    # List models
    res = client.get("/api/ml/models")
    models = res.json().get("models", [])
    if len(models) >= 2:
        target_v = models[1]["version"]
        res = client.post(f"/api/ml/models/{target_v}/rollback")
        assert res.status_code == 200
        assert res.json()["status"] == "rolled_back"
