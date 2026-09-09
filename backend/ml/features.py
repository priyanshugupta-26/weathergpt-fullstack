"""WeatherGPT ML Feature and Target Schema Registry.
Schema-driven feature system guaranteeing exact feature names, order, types, and prevention of future leakage.
"""

import json
import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.config import ROOT

log = logging.getLogger("weathergpt.ml.features")
SCHEMA_PATH = ROOT / "models" / "schema" / "weather_features.json"


class FeatureRegistry:
    """Manages feature definitions and guarantees immutable order and strict metadata."""

    def __init__(self, schema_path: Path = SCHEMA_PATH):
        self.schema_path = schema_path
        self.schema_version = "1.0.0"
        self.features: list[dict[str, Any]] = []
        self.feature_names: list[str] = []
        self.feature_map: dict[str, dict[str, Any]] = {}
        self.targets: list[dict[str, Any]] = []
        self.target_names: list[str] = []
        self.target_map: dict[str, dict[str, Any]] = {}
        self.load()

    def load(self):
        if self.schema_path.exists():
            try:
                data = json.loads(self.schema_path.read_text())
                self.schema_version = data.get("schema_version", "1.0.0")
                self.features = data.get("features", [])
                self.targets = data.get("targets", [])
            except Exception as err:
                log.warning("Could not parse %s: %s. Using default features.", self.schema_path, err)
                self._load_fallback()
        else:
            self._load_fallback()

        self.feature_names = [f["name"] for f in self.features]
        self.feature_map = {f["name"]: f for f in self.features}
        self.target_names = [t["name"] for t in self.targets]
        self.target_map = {t["name"]: t for t in self.targets}

    def _load_fallback(self):
        # 39 physics-informed feature defaults
        self.features = [
            {"name": "latitude", "unit": "deg", "dtype": "float64", "default": 25.5941},
            {"name": "longitude", "unit": "deg", "dtype": "float64", "default": 85.1376},
            {"name": "temperature_2m", "unit": "celsius", "dtype": "float64", "default": 27.0},
            {"name": "relative_humidity_2m", "unit": "percent", "dtype": "float64", "default": 60.0},
            {"name": "dew_point_2m", "unit": "celsius", "dtype": "float64", "default": 18.0},
            {"name": "apparent_temperature", "unit": "celsius", "dtype": "float64", "default": 28.5},
            {"name": "precipitation", "unit": "mm", "dtype": "float64", "default": 0.0},
            {"name": "rain", "unit": "mm", "dtype": "float64", "default": 0.0},
            {"name": "surface_pressure", "unit": "hPa", "dtype": "float64", "default": 1005.0},
            {"name": "et0_fao_evapotranspiration", "unit": "mm", "dtype": "float64", "default": 0.2},
            {"name": "vapour_pressure_deficit", "unit": "kPa", "dtype": "float64", "default": 1.2},
            {"name": "wind_speed_10m", "unit": "km/h", "dtype": "float64", "default": 10.0},
            {"name": "wind_gusts_10m", "unit": "km/h", "dtype": "float64", "default": 14.0},
            {"name": "soil_temperature_0_to_7cm", "unit": "celsius", "dtype": "float64", "default": 27.0},
            {"name": "soil_moisture_0_to_7cm", "unit": "m3/m3", "dtype": "float64", "default": 0.3},
            {"name": "shortwave_radiation", "unit": "W/m2", "dtype": "float64", "default": 400.0},
            {"name": "direct_normal_irradiance", "unit": "W/m2", "dtype": "float64", "default": 300.0},
            {"name": "diffuse_radiation", "unit": "W/m2", "dtype": "float64", "default": 100.0},
            {"name": "cloud_cover", "unit": "percent", "dtype": "float64", "default": 20.0},
            {"name": "wind_u_vector", "unit": "m/s", "dtype": "float64", "default": 0.0},
            {"name": "wind_v_vector", "unit": "m/s", "dtype": "float64", "default": 0.0},
            {"name": "wet_bulb_temp", "unit": "celsius", "dtype": "float64", "default": 22.0},
            {"name": "sin_hour", "unit": "dimensionless", "dtype": "float64", "default": 0.0},
            {"name": "cos_hour", "unit": "dimensionless", "dtype": "float64", "default": 1.0},
            {"name": "sin_day", "unit": "dimensionless", "dtype": "float64", "default": 0.0},
            {"name": "cos_day", "unit": "dimensionless", "dtype": "float64", "default": 1.0},
            {"name": "pressure_tendency_3h", "unit": "hPa", "dtype": "float64", "default": -0.2},
            {"name": "temp_lag_1", "unit": "celsius", "dtype": "float64", "default": 26.7},
            {"name": "humidity_lag_1", "unit": "percent", "dtype": "float64", "default": 62.0},
            {"name": "radiation_lag_1", "unit": "W/m2", "dtype": "float64", "default": 370.0},
            {"name": "temp_lag_2", "unit": "celsius", "dtype": "float64", "default": 26.3},
            {"name": "humidity_lag_2", "unit": "percent", "dtype": "float64", "default": 64.0},
            {"name": "radiation_lag_2", "unit": "W/m2", "dtype": "float64", "default": 340.0},
            {"name": "temp_lag_3", "unit": "celsius", "dtype": "float64", "default": 25.8},
            {"name": "humidity_lag_3", "unit": "percent", "dtype": "float64", "default": 66.0},
            {"name": "radiation_lag_3", "unit": "W/m2", "dtype": "float64", "default": 310.0},
            {"name": "temp_lag_24", "unit": "celsius", "dtype": "float64", "default": 26.5},
            {"name": "humidity_lag_24", "unit": "percent", "dtype": "float64", "default": 59.0},
            {"name": "radiation_lag_24", "unit": "W/m2", "dtype": "float64", "default": 400.0},
        ]
        self.targets = [
            {"name": "temperature_2m", "unit": "celsius", "critical": True, "tolerance_mae": 1.2},
            {"name": "relative_humidity_2m", "unit": "percent", "critical": True, "tolerance_mae": 8.0},
            {"name": "surface_pressure", "unit": "hPa", "critical": True, "tolerance_mae": 2.5},
            {"name": "wind_speed_10m", "unit": "km/h", "critical": True, "tolerance_mae": 4.5},
            {"name": "wind_direction_10m", "unit": "degrees", "is_circular": True, "tolerance_mae": 45.0},
            {"name": "precipitation", "unit": "mm", "critical": False, "tolerance_mae": 1.5},
            {"name": "cloud_cover", "unit": "percent", "critical": False, "tolerance_mae": 15.0},
            {"name": "dew_point_2m", "unit": "celsius", "critical": False, "tolerance_mae": 1.5},
        ]

    @property
    def count(self) -> int:
        return len(self.feature_names)

    @property
    def target_count(self) -> int:
        return len(self.target_names)


feature_registry = FeatureRegistry()


class FeatureValidator:
    """Validates feature completeness, finite values, and strict order."""

    @staticmethod
    def validate_features(features: dict[str, float] | list[float], expected_names: list[str]) -> list[float]:
        if isinstance(features, (list, tuple)):
            if len(features) != len(expected_names):
                raise ValueError(
                    f"Feature length mismatch: expected {len(expected_names)} features, got {len(features)}"
                )
            values = [float(v) for v in features]
        elif isinstance(features, dict):
            missing = [name for name in expected_names if name not in features]
            if missing:
                raise ValueError(f"Missing required features: {missing}")
            values = [float(features[name]) for name in expected_names]
        else:
            raise TypeError("Features must be a dictionary or ordered sequence of numbers")

        for idx, val in enumerate(values):
            if not math.isfinite(val):
                raise ValueError(f"Feature '{expected_names[idx]}' contains non-finite value: {val}")

        return values


class MLFeatureBuilder:
    """Builds features from an observation dictionary and historical observations without data leakage."""

    @staticmethod
    def compute_wet_bulb(temp: float, rh: float) -> float:
        """Stull psychrometric empirical wet-bulb temperature formulation."""
        rh_clamped = max(1.0, min(100.0, rh))
        return round(
            temp * math.atan(0.151977 * math.sqrt(rh_clamped + 8.313659))
            + math.atan(temp + rh_clamped)
            - math.atan(rh_clamped - 1.676331)
            + 0.00391838 * (rh_clamped ** 1.5) * math.atan(0.023101 * rh_clamped)
            - 4.686035,
            2,
        )

    @staticmethod
    def compute_wind_vectors(wind_speed_kmh: float, wind_direction_deg: float) -> tuple[float, float]:
        """Converts wind speed (km/h) and meteorological direction (deg) to zonal (u) & meridional (v) m/s."""
        v_ms = max(0.0, wind_speed_kmh) / 3.6
        rad = math.radians(wind_direction_deg % 360)
        # Meteorological convention: wind coming FROM direction
        wind_u = -v_ms * math.sin(rad)
        wind_v = -v_ms * math.cos(rad)
        return round(wind_u, 4), round(wind_v, 4)

    @staticmethod
    def compute_cyclical_time(dt: datetime) -> tuple[float, float, float, float]:
        """Harmonic sin/cos encodings for 24-hour diurnal and 365.25-day annual cycles."""
        hour = dt.hour + dt.minute / 60.0
        doy = dt.timetuple().tm_yday
        sin_hour = math.sin(2 * math.pi * hour / 24.0)
        cos_hour = math.cos(2 * math.pi * hour / 24.0)
        sin_day = math.sin(2 * math.pi * doy / 365.25)
        cos_day = math.cos(2 * math.pi * doy / 365.25)
        return round(sin_hour, 4), round(cos_hour, 4), round(sin_day, 4), round(cos_day, 4)

    @classmethod
    def build_features_from_obs(
        cls,
        current_obs: dict[str, Any],
        past_lags: dict[str, dict[str, Any]] | None = None,
        registry: FeatureRegistry = feature_registry,
    ) -> dict[str, float]:
        """Constructs an exact dictionary of features for time T based ONLY on information available at or before T.
        
        Args:
            current_obs: Observation dictionary at time T.
            past_lags: Optional dictionary mapping lag identifiers like 'lag_1h', 'lag_2h', 'lag_3h', 'lag_24h'
                       to earlier observation dictionaries.
            registry: FeatureRegistry defining the target feature set.
        """
        past_lags = past_lags or {}

        # 1. Base telemetry
        lat = float(current_obs.get("latitude") if current_obs.get("latitude") is not None else 25.5941)
        lon = float(current_obs.get("longitude") if current_obs.get("longitude") is not None else 85.1376)
        temp = float(current_obs.get("temperature") if current_obs.get("temperature") is not None else current_obs.get("temperature_2m", 27.0))
        rh = float(current_obs.get("humidity") if current_obs.get("humidity") is not None else current_obs.get("relative_humidity_2m", 60.0))
        dew = float(current_obs.get("dew_point") if current_obs.get("dew_point") is not None else current_obs.get("dew_point_2m", temp - ((100 - rh) / 5)))
        app_temp = float(current_obs.get("feels_like") if current_obs.get("feels_like") is not None else current_obs.get("apparent_temperature", temp + 1.5))
        precip = float(current_obs.get("precipitation") if current_obs.get("precipitation") is not None else 0.0)
        rain = float(current_obs.get("rainfall") if current_obs.get("rainfall") is not None else current_obs.get("rain", precip))
        press = float(current_obs.get("surface_pressure") if current_obs.get("surface_pressure") is not None else current_obs.get("pressure", 1005.0))
        et0 = float(current_obs.get("et0_fao_evapotranspiration") if current_obs.get("et0_fao_evapotranspiration") is not None else 0.2)
        vpd = float(current_obs.get("vapour_pressure_deficit") if current_obs.get("vapour_pressure_deficit") is not None else 1.2)
        wind_speed = float(current_obs.get("wind_speed") if current_obs.get("wind_speed") is not None else current_obs.get("wind_speed_10m", 10.0))
        wind_dir = float(current_obs.get("wind_direction") if current_obs.get("wind_direction") is not None else current_obs.get("wind_direction_10m", 90.0))
        wind_gust = float(current_obs.get("wind_gust") if current_obs.get("wind_gust") is not None else current_obs.get("wind_gusts_10m", wind_speed * 1.4))
        soil_temp = float(current_obs.get("soil_temperature") if current_obs.get("soil_temperature") is not None else current_obs.get("soil_temperature_0_to_7cm", temp))
        soil_moist = float(current_obs.get("soil_moisture") if current_obs.get("soil_moisture") is not None else current_obs.get("soil_moisture_0_to_7cm", 0.3))
        shortwave = float(current_obs.get("shortwave_radiation") if current_obs.get("shortwave_radiation") is not None else 400.0)
        dni = float(current_obs.get("direct_normal_irradiance") if current_obs.get("direct_normal_irradiance") is not None else 300.0)
        diffuse = float(current_obs.get("diffuse_radiation") if current_obs.get("diffuse_radiation") is not None else 100.0)
        cloud = float(current_obs.get("cloud_cover") if current_obs.get("cloud_cover") is not None else 20.0)

        # 2. Physics transformations
        wind_u, wind_v = cls.compute_wind_vectors(wind_speed, wind_dir)
        wet_bulb = cls.compute_wet_bulb(temp, rh)

        # 3. Cyclical time transformations
        obs_time = current_obs.get("timestamp")
        if obs_time:
            try:
                dt = datetime.fromisoformat(str(obs_time).replace("Z", "+00:00"))
            except Exception:
                dt = datetime.now(timezone.utc)
        else:
            dt = datetime.now(timezone.utc)

        sin_h, cos_h, sin_d, cos_d = cls.compute_cyclical_time(dt)

        # 4. Lag values and pressure tendency
        # Extract from past_lags if provided, otherwise fallback gracefully
        lag_1 = past_lags.get("lag_1h", {})
        lag_2 = past_lags.get("lag_2h", {})
        lag_3 = past_lags.get("lag_3h", {})
        lag_24 = past_lags.get("lag_24h", {})

        p_3h_ago = lag_3.get("surface_pressure", lag_3.get("pressure", press + 0.2))
        pressure_tendency_3h = round(press - float(p_3h_ago), 2)

        temp_lag_1 = float(lag_1.get("temperature", lag_1.get("temperature_2m", current_obs.get("temp_lag_1", temp - 0.3))))
        hum_lag_1 = float(lag_1.get("humidity", lag_1.get("relative_humidity_2m", current_obs.get("humidity_lag_1", rh + 2.0))))
        rad_lag_1 = float(lag_1.get("shortwave_radiation", current_obs.get("radiation_lag_1", max(0.0, shortwave - 30.0))))

        temp_lag_2 = float(lag_2.get("temperature", lag_2.get("temperature_2m", current_obs.get("temp_lag_2", temp - 0.7))))
        hum_lag_2 = float(lag_2.get("humidity", lag_2.get("relative_humidity_2m", current_obs.get("humidity_lag_2", rh + 4.0))))
        rad_lag_2 = float(lag_2.get("shortwave_radiation", current_obs.get("radiation_lag_2", max(0.0, shortwave - 60.0))))

        temp_lag_3 = float(lag_3.get("temperature", lag_3.get("temperature_2m", current_obs.get("temp_lag_3", temp - 1.2))))
        hum_lag_3 = float(lag_3.get("humidity", lag_3.get("relative_humidity_2m", current_obs.get("humidity_lag_3", rh + 6.0))))
        rad_lag_3 = float(lag_3.get("shortwave_radiation", current_obs.get("radiation_lag_3", max(0.0, shortwave - 90.0))))

        temp_lag_24 = float(lag_24.get("temperature", lag_24.get("temperature_2m", current_obs.get("temp_lag_24", temp - 0.5))))
        hum_lag_24 = float(lag_24.get("humidity", lag_24.get("relative_humidity_2m", current_obs.get("humidity_lag_24", rh - 1.0))))
        rad_lag_24 = float(lag_24.get("shortwave_radiation", current_obs.get("radiation_lag_24", shortwave)))

        features_pool = {
            "latitude": lat,
            "longitude": lon,
            "temperature_2m": temp,
            "relative_humidity_2m": rh,
            "dew_point_2m": dew,
            "apparent_temperature": app_temp,
            "precipitation": precip,
            "rain": rain,
            "surface_pressure": press,
            "et0_fao_evapotranspiration": et0,
            "vapour_pressure_deficit": vpd,
            "wind_speed_10m": wind_speed,
            "wind_gusts_10m": wind_gust,
            "soil_temperature_0_to_7cm": soil_temp,
            "soil_moisture_0_to_7cm": soil_moist,
            "shortwave_radiation": shortwave,
            "direct_normal_irradiance": dni,
            "diffuse_radiation": diffuse,
            "cloud_cover": cloud,
            "wind_u_vector": wind_u,
            "wind_v_vector": wind_v,
            "wet_bulb_temp": wet_bulb,
            "sin_hour": sin_h,
            "cos_hour": cos_h,
            "sin_day": sin_d,
            "cos_day": cos_d,
            "pressure_tendency_3h": pressure_tendency_3h,
            "temp_lag_1": temp_lag_1,
            "humidity_lag_1": hum_lag_1,
            "radiation_lag_1": rad_lag_1,
            "temp_lag_2": temp_lag_2,
            "humidity_lag_2": hum_lag_2,
            "radiation_lag_2": rad_lag_2,
            "temp_lag_3": temp_lag_3,
            "humidity_lag_3": hum_lag_3,
            "radiation_lag_3": rad_lag_3,
            "temp_lag_24": temp_lag_24,
            "humidity_lag_24": hum_lag_24,
            "radiation_lag_24": rad_lag_24,
        }

        # Return features strictly conforming to the registry's defined names and order
        ordered_features = {}
        for name in registry.feature_names:
            if name in features_pool:
                ordered_features[name] = float(features_pool[name])
            else:
                default_val = registry.feature_map.get(name, {}).get("default", 0.0)
                ordered_features[name] = float(current_obs.get(name, default_val))

        return ordered_features
