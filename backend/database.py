import json
from datetime import datetime, timezone
from sqlalchemy import create_engine, String, Text, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from .config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {},
    pool_pre_ping=True,
)
Session = sessionmaker(engine, expire_on_commit=False)


def now():
    return datetime.now(timezone.utc).isoformat()


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(20), default="user")
    preferences: Mapped[str] = mapped_column(Text, default="{}")
    mobile: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    preferred_language: Mapped[str] = mapped_column(String(20), default="en")
    state: Mapped[str | None] = mapped_column(String(100), default="", nullable=True)
    district: Mapped[str | None] = mapped_column(String(100), default="", nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), default="", nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_active: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[str] = mapped_column(String(40), default=now)
    updated_at: Mapped[str] = mapped_column(String(40), default=now)
    last_login: Mapped[str | None] = mapped_column(String(40), nullable=True)


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    expires: Mapped[float] = mapped_column(Float, index=True)


class Location(Base):
    __tablename__ = "saved_locations"
    __table_args__ = (UniqueConstraint("user_id", "latitude", "longitude"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    district: Mapped[str] = mapped_column(String(100), default="")
    state: Mapped[str] = mapped_column(String(100), default="")
    radius_km: Mapped[float] = mapped_column(Float, default=25)
    label: Mapped[str] = mapped_column(String(20), default="Custom")


class Record(Base):
    __tablename__ = "records"
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    kind: Mapped[str] = mapped_column(String(40), index=True)
    payload: Mapped[str] = mapped_column(Text)
    created: Mapped[str] = mapped_column(String(40), default=now, index=True)


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    conversation: Mapped[str] = mapped_column(String(64), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    created: Mapped[str] = mapped_column(String(40), default=now)


# ========================================================
# WeatherGPT ML & Observational Time-Series Tables
# ========================================================

class WeatherLocation(Base):
    __tablename__ = "weather_locations"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    latitude: Mapped[float] = mapped_column(Float, index=True)
    longitude: Mapped[float] = mapped_column(Float, index=True)
    elevation: Mapped[float | None] = mapped_column(Float, nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), default="", nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), default="India", nullable=True)
    is_active: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[str] = mapped_column(String(40), default=now)


class WeatherObservation(Base):
    __tablename__ = "weather_observations"
    __table_args__ = (
        UniqueConstraint("latitude", "longitude", "provider", "timestamp", "data_type", name="uq_obs_point_time"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[int | None] = mapped_column(ForeignKey("weather_locations.id"), nullable=True, index=True)
    latitude: Mapped[float] = mapped_column(Float, index=True)
    longitude: Mapped[float] = mapped_column(Float, index=True)
    timestamp: Mapped[str] = mapped_column(String(40), index=True)
    retrieval_timestamp: Mapped[str] = mapped_column(String(40), default=now)
    provider: Mapped[str] = mapped_column(String(50), index=True)  # Open-Meteo, IMD, etc.
    data_type: Mapped[str] = mapped_column(String(30), default="OBSERVATION", index=True)  # OBSERVATION vs FORECAST
    quality_flag: Mapped[str] = mapped_column(String(30), default="VALID", index=True)  # VALID, SUSPICIOUS, REJECTED

    # Core thermodynamics (Allow nullable, NEVER default missing data to fake 0)
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    feels_like: Mapped[float | None] = mapped_column(Float, nullable=True)
    humidity: Mapped[float | None] = mapped_column(Float, nullable=True)
    dew_point: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Barometric
    pressure: Mapped[float | None] = mapped_column(Float, nullable=True)
    surface_pressure: Mapped[float | None] = mapped_column(Float, nullable=True)
    mslp: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Kinematics
    wind_speed: Mapped[float | None] = mapped_column(Float, nullable=True)
    wind_direction: Mapped[float | None] = mapped_column(Float, nullable=True)
    wind_gust: Mapped[float | None] = mapped_column(Float, nullable=True)
    u_wind: Mapped[float | None] = mapped_column(Float, nullable=True)
    v_wind: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Precipitation
    rainfall: Mapped[float | None] = mapped_column(Float, nullable=True)
    precipitation: Mapped[float | None] = mapped_column(Float, nullable=True)
    precipitation_probability: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Sky & Atmosphere
    cloud_cover: Mapped[float | None] = mapped_column(Float, nullable=True)
    visibility: Mapped[float | None] = mapped_column(Float, nullable=True)
    weather_code: Mapped[float | None] = mapped_column(Float, nullable=True)
    uv_index: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Solar & Radiation
    shortwave_radiation: Mapped[float | None] = mapped_column(Float, nullable=True)
    direct_normal_irradiance: Mapped[float | None] = mapped_column(Float, nullable=True)
    diffuse_radiation: Mapped[float | None] = mapped_column(Float, nullable=True)
    et0_fao_evapotranspiration: Mapped[float | None] = mapped_column(Float, nullable=True)
    vapour_pressure_deficit: Mapped[float | None] = mapped_column(Float, nullable=True)
    wet_bulb_temp: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Air Quality & Environment
    pm2_5: Mapped[float | None] = mapped_column(Float, nullable=True)
    pm10: Mapped[float | None] = mapped_column(Float, nullable=True)
    co: Mapped[float | None] = mapped_column(Float, nullable=True)
    no2: Mapped[float | None] = mapped_column(Float, nullable=True)
    o3: Mapped[float | None] = mapped_column(Float, nullable=True)
    so2: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Soil parameters
    soil_temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    soil_moisture: Mapped[float | None] = mapped_column(Float, nullable=True)

    raw_payload: Mapped[str | None] = mapped_column(Text, nullable=True)


class WeatherForecastRecord(Base):
    __tablename__ = "weather_forecasts"
    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[int | None] = mapped_column(ForeignKey("weather_locations.id"), nullable=True)
    latitude: Mapped[float] = mapped_column(Float, index=True)
    longitude: Mapped[float] = mapped_column(Float, index=True)
    provider: Mapped[str] = mapped_column(String(50), index=True)  # Open-Meteo, IMD, WeatherGPT ML
    generated_at: Mapped[str] = mapped_column(String(40), index=True)
    target_time: Mapped[str] = mapped_column(String(40), index=True)
    forecast_horizon_hours: Mapped[int] = mapped_column(default=1)
    payload: Mapped[str] = mapped_column(Text)  # JSON


class WeatherFeature(Base):
    __tablename__ = "weather_features"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    unit: Mapped[str] = mapped_column(String(30), default="")
    dtype: Mapped[str] = mapped_column(String(30), default="float64")
    source: Mapped[str] = mapped_column(String(100), default="computed")
    is_target: Mapped[int] = mapped_column(default=0)
    config_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class TrainingSample(Base):
    __tablename__ = "training_samples"
    id: Mapped[int] = mapped_column(primary_key=True)
    timestamp: Mapped[str] = mapped_column(String(40), index=True)
    location_id: Mapped[int | None] = mapped_column(ForeignKey("weather_locations.id"), nullable=True)
    latitude: Mapped[float] = mapped_column(Float, index=True)
    longitude: Mapped[float] = mapped_column(Float, index=True)
    features_json: Mapped[str] = mapped_column(Text)
    targets_json: Mapped[str] = mapped_column(Text)
    data_source_flag: Mapped[str] = mapped_column(String(30), default="REAL", index=True)  # REAL, DEMO, SYNTHETIC


class ModelVersion(Base):
    __tablename__ = "model_versions"
    id: Mapped[int] = mapped_column(primary_key=True)
    model_name: Mapped[str] = mapped_column(String(100), default="weathergpt_ml", index=True)
    model_type: Mapped[str] = mapped_column(String(60), default="multi_output_regressor")
    version: Mapped[str] = mapped_column(String(50), unique=True, index=True)  # e.g. v001
    algorithm: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[str] = mapped_column(String(40), default=now, index=True)
    training_start: Mapped[str | None] = mapped_column(String(40), nullable=True)
    training_end: Mapped[str | None] = mapped_column(String(40), nullable=True)
    training_rows: Mapped[int] = mapped_column(default=0)
    feature_schema_version: Mapped[str] = mapped_column(String(30), default="1.0.0")
    target_schema_version: Mapped[str] = mapped_column(String(30), default="1.0.0")
    metrics: Mapped[str] = mapped_column(Text, default="{}")  # JSON metrics
    artifact_path: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(30), default="CHALLENGER", index=True)
    # Statuses: TRAINING, CHALLENGER, CHAMPION, REJECTED, FAILED, ARCHIVED
    parent_model: Mapped[str | None] = mapped_column(String(50), nullable=True)
    promotion_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class ModelMetric(Base):
    __tablename__ = "model_metrics"
    id: Mapped[int] = mapped_column(primary_key=True)
    model_version_id: Mapped[int] = mapped_column(ForeignKey("model_versions.id"), index=True)
    target_name: Mapped[str] = mapped_column(String(80), index=True)
    metric_name: Mapped[str] = mapped_column(String(50))  # mae, rmse, r2, circular_mae
    metric_value: Mapped[float] = mapped_column(Float)
    split_kind: Mapped[str] = mapped_column(String(30), default="validation")
    calculated_at: Mapped[str] = mapped_column(String(40), default=now)


class ModelPrediction(Base):
    __tablename__ = "model_predictions"
    id: Mapped[int] = mapped_column(primary_key=True)
    prediction_id: Mapped[str] = mapped_column(String(64), index=True)
    model_version: Mapped[str] = mapped_column(String(50), index=True)
    location: Mapped[str] = mapped_column(String(160), default="")
    latitude: Mapped[float] = mapped_column(Float, index=True)
    longitude: Mapped[float] = mapped_column(Float, index=True)
    prediction_generated_at: Mapped[str] = mapped_column(String(40), index=True)
    forecast_valid_at: Mapped[str] = mapped_column(String(40), index=True)
    target_name: Mapped[str] = mapped_column(String(80), index=True)
    predicted_value: Mapped[float] = mapped_column(Float)
    actual_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    error: Mapped[float | None] = mapped_column(Float, nullable=True)
    absolute_error: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_features_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)


class PredictionActual(Base):
    __tablename__ = "prediction_actuals"
    id: Mapped[int] = mapped_column(primary_key=True)
    prediction_id: Mapped[str] = mapped_column(String(64), index=True)
    observation_id: Mapped[int] = mapped_column(ForeignKey("weather_observations.id"), index=True)
    matched_at: Mapped[str] = mapped_column(String(40), default=now)
    time_difference_seconds: Mapped[float] = mapped_column(Float, default=0.0)


class TrainingJob(Base):
    __tablename__ = "training_jobs"
    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[str] = mapped_column(String(30), default="QUEUED", index=True)
    # QUEUED, RUNNING, EVALUATING, PROMOTED, REJECTED, FAILED
    trigger_type: Mapped[str] = mapped_column(String(30), default="MANUAL")  # MANUAL, SCHEDULED, DRIFT
    started_at: Mapped[str] = mapped_column(String(40), default=now)
    completed_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    candidate_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    logs: Mapped[str | None] = mapped_column(Text, nullable=True)
    metrics_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class DataQualityReport(Base):
    __tablename__ = "data_quality_reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    timestamp: Mapped[str] = mapped_column(String(40), default=now, index=True)
    provider: Mapped[str] = mapped_column(String(50))
    records_checked: Mapped[int] = mapped_column(default=0)
    duplicates_skipped: Mapped[int] = mapped_column(default=0)
    outliers_flagged: Mapped[int] = mapped_column(default=0)
    missing_fields_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(30), default="PASSED")


class DriftMetric(Base):
    __tablename__ = "drift_metrics"
    id: Mapped[int] = mapped_column(primary_key=True)
    calculated_at: Mapped[str] = mapped_column(String(40), default=now, index=True)
    baseline_period: Mapped[str] = mapped_column(String(100))
    comparison_period: Mapped[str] = mapped_column(String(100))
    target_name: Mapped[str] = mapped_column(String(80), index=True)
    ks_statistic: Mapped[float] = mapped_column(Float, default=0.0)
    p_value: Mapped[float] = mapped_column(Float, default=1.0)
    drift_detected: Mapped[int] = mapped_column(default=0)
    details_json: Mapped[str | None] = mapped_column(Text, nullable=True)


def save_record(key, kind, payload):
    with Session.begin() as db:
        db.merge(Record(key=key, kind=kind, payload=json.dumps(payload), created=now()))
        from sqlalchemy import select, delete
        stale = select(Record.key).where(Record.kind == kind).order_by(Record.created.desc()).offset(2000)
        db.execute(delete(Record).where(Record.key.in_(stale)))


def initialize():
    Base.metadata.create_all(engine)
    from sqlalchemy import inspect, text, select
    insp = inspect(engine)
    existing_locs = {c["name"] for c in insp.get_columns("saved_locations")}
    additions = {
        "district": "VARCHAR(100) DEFAULT ''",
        "state": "VARCHAR(100) DEFAULT ''",
        "radius_km": "FLOAT DEFAULT 25",
        "label": "VARCHAR(20) DEFAULT 'Custom'",
    }
    with engine.begin() as db:
        for name, definition in additions.items():
            if name not in existing_locs:
                db.execute(text(f"ALTER TABLE saved_locations ADD COLUMN {name} {definition}"))

    existing_users = {c["name"] for c in insp.get_columns("users")}
    user_additions = {
        "mobile": "VARCHAR(30)",
        "preferred_language": "VARCHAR(20) DEFAULT 'en'",
        "state": "VARCHAR(100) DEFAULT ''",
        "district": "VARCHAR(100) DEFAULT ''",
        "city": "VARCHAR(100) DEFAULT ''",
        "latitude": "FLOAT",
        "longitude": "FLOAT",
        "is_active": "INTEGER DEFAULT 1",
        "created_at": "VARCHAR(40)",
        "updated_at": "VARCHAR(40)",
        "last_login": "VARCHAR(40)",
    }
    with engine.begin() as db:
        for name, definition in user_additions.items():
            if name not in existing_users:
                db.execute(text(f"ALTER TABLE users ADD COLUMN {name} {definition}"))

    import os
    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")
    if admin_email and admin_password:
        from .auth import hasher
        with Session.begin() as db:
            admin_user = db.scalar(select(User).where(User.email == admin_email.strip().lower()))
            if not admin_user:
                db.add(
                    User(
                        email=admin_email.strip().lower(),
                        name="Administrator",
                        password_hash=hasher.hash(admin_password),
                        role="admin",
                        preferred_language="en",
                    )
                )

