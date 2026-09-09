"""Pickle is executable code: loading requires explicit trust and a validated manifest."""

import json
import math
from typing import Any
try:
    import numpy as np
    _ARRAY_TYPES = (list, tuple, np.ndarray)
except ImportError:
    np = None
    _ARRAY_TYPES = (list, tuple)
from backend.config import ROOT, settings


class ModelAdapter:
    def __init__(self, kind: str):
        self.kind = kind
        self.directory = ROOT / "models"
        self.model = None
        self.schema = None
        self.problem = None
        self.preprocessor = None

    def status(self) -> dict[str, Any]:
        file = self.directory / f"{self.kind}_model.pkl"
        manifest = self.directory / "schema" / f"{self.kind}.json"
        
        # Introspect loaded model attributes
        feature_names = None
        n_features = None
        classes = None
        pipeline_steps = None
        
        if self.model is not None:
            if hasattr(self.model, "feature_names_in_"):
                feature_names = list(self.model.feature_names_in_)
            if hasattr(self.model, "n_features_in_"):
                n_features = int(self.model.n_features_in_)
            if hasattr(self.model, "classes_"):
                classes = [str(c) for c in self.model.classes_]
            if hasattr(self.model, "steps"):
                pipeline_steps = [str(s[0]) for s in self.model.steps]

        return {
            "name": self.kind,
            "status": "loaded"
            if self.model is not None
            else "missing"
            if not file.exists()
            else "disabled",
            "mode": "model" if self.model is not None else "fallback",
            "file_present": file.exists(),
            "schema_present": manifest.exists(),
            "trusted_loading": settings.trusted_models,
            "error": self.problem,
            "expected_features": self.schema.get("features") if self.schema else None,
            "feature_count": len(self.schema.get("features", [])) if self.schema else n_features,
            "introspected": {
                "feature_names_in": feature_names,
                "n_features_in": n_features,
                "classes": classes,
                "pipeline_steps": pipeline_steps,
            },
            "metadata": {
                k: self.schema.get(k)
                for k in ("version", "training_date", "outputs", "metrics", "target_classes")
            } if self.schema else {},
        }

    def load(self):
        file = self.directory / f"{self.kind}_model.pkl"
        manifest_path = self.directory / "schema" / f"{self.kind}.json"
        if not manifest_path.exists():
            manifest_path = self.directory / "schema" / f"{self.kind}.example.json"
        
        if manifest_path.exists():
            try:
                self.schema = json.loads(manifest_path.read_text())
            except Exception as e:
                self.problem = f"ManifestError: {e}"

        if not file.exists() or not settings.trusted_models:
            return

        try:
            if self.schema is None:
                raise ValueError("Model manifest required to load model safely")
            
            features = self.schema.get("features", [])
            if not features or len(features) != len(set(features)):
                raise ValueError("Manifest requires unique ordered feature names")
            if self.schema.get("input_format") not in ("array", "dataframe"):
                raise ValueError("Specify input_format: array or dataframe")

            import pickle
            with file.open("rb") as stream:
                model = pickle.load(stream)

            if hasattr(model, "n_features_in_") and model.n_features_in_ != len(features):
                raise ValueError(
                    f"Model feature count ({model.n_features_in_}) differs from manifest ({len(features)})"
                )

            names = getattr(model, "feature_names_in_", None)
            if names is not None and list(names) != features:
                raise ValueError("Model feature order differs from manifest")

            if self.schema.get("preprocessing") == "preprocessor.pkl":
                pre_path = self.directory / "preprocessor.pkl"
                if pre_path.exists():
                    with pre_path.open("rb") as stream:
                        self.preprocessor = pickle.load(stream)
                    if hasattr(self.preprocessor, "n_features_in_") and self.preprocessor.n_features_in_ != len(features):
                        raise ValueError("Preprocessor feature count differs from manifest")

            self.model = model
            self.problem = None
        except Exception as error:
            self.problem = f"{type(error).__name__}: {error}"

    def predict(self, features: dict[str, float] | list[float]):
        if self.model is None:
            return None

        expected = self.schema.get("features", []) if self.schema else []
        
        # Handle features supplied as a list vs dictionary
        if isinstance(features, (list, tuple)):
            if expected and len(features) != len(expected):
                raise ValueError(
                    f"Expected {len(expected)} features in list, received {len(features)}"
                )
            values = [float(v) for v in features]
        elif isinstance(features, dict):
            if expected:
                missing = set(expected) - set(features)
                unexpected = set(features) - set(expected)
                if missing or unexpected:
                    raise ValueError(
                        f"Feature mismatch. Missing: {sorted(missing)}; unexpected: {sorted(unexpected)}"
                    )
                values = [features[name] for name in expected]
            else:
                values = list(features.values())
        else:
            raise ValueError("Features must be a dictionary or ordered numeric list")

        if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in values):
            raise ValueError("All features must be finite numeric values")

        data = [values]
        if self.schema and self.schema.get("input_format") == "dataframe":
            import pandas as pd
            data = pd.DataFrame(data, columns=expected or None)

        if self.preprocessor is not None:
            data = self.preprocessor.transform(data)

        raw_pred = self.model.predict(data)
        
        # Robust multi-output and scalar extraction
        if hasattr(raw_pred, "ndim") and raw_pred.ndim > 1:
            # e.g., shape (1, n_outputs) -> pred[0]
            first_row = raw_pred[0]
        elif isinstance(raw_pred, (list, tuple)) and len(raw_pred) > 0 and isinstance(raw_pred[0], _ARRAY_TYPES):
            first_row = raw_pred[0]
        else:
            first_row = raw_pred[0] if isinstance(raw_pred, _ARRAY_TYPES) else raw_pred

        if hasattr(first_row, "tolist"):
            first_row = first_row.tolist()

        outputs = self.schema.get("outputs") if self.schema else None
        
        if isinstance(first_row, (list, tuple)):
            if outputs and len(outputs) == len(first_row):
                result = dict(zip(outputs, first_row))
            elif outputs and len(outputs) != len(first_row):
                # Fallback gracefully with named fields instead of crashing
                result = {
                    (outputs[i] if i < len(outputs) else f"output_{i+1}"): val
                    for i, val in enumerate(first_row)
                }
            else:
                result = {f"output_{i+1}": val for i, val in enumerate(first_row)}
        elif isinstance(first_row, dict):
            result = first_row
        else:
            # Scalar output
            val = first_row.item() if hasattr(first_row, "item") else first_row
            result = float(val) if isinstance(val, (int, float)) else val

        confidence = None
        probabilities = None
        if hasattr(self.model, "predict_proba"):
            try:
                proba_raw = self.model.predict_proba(data)[0]
                if hasattr(proba_raw, "tolist"):
                    proba_raw = proba_raw.tolist()
                confidence = float(max(proba_raw))
                classes = getattr(self.model, "classes_", None)
                if classes is not None and len(classes) == len(proba_raw):
                    probabilities = {str(classes[i]): round(float(p), 4) for i, p in enumerate(proba_raw)}
            except Exception:
                pass

        return {
            "prediction": result,
            "confidence": confidence,
            "probabilities": probabilities,
            "mode": "model",
            "model_source": f"{self.kind}_model.pkl",
        }


class FeatureBuilder:
    """Physics-informed and domain telemetry feature engineering for WeatherGPT models."""

    @staticmethod
    def build_weather_features(obs: dict[str, Any], history_lags: list[dict[str, Any]] | None = None) -> dict[str, float]:
        """Builds all 39 continuous thermodynamic and cyclical predictors (from sudish.ipynb)."""
        lat = float(obs.get("latitude") or 25.5941)
        lon = float(obs.get("longitude") or 85.1376)
        temp = float(obs.get("temperature_2m") or 27.0)
        rh = float(obs.get("relative_humidity_2m") or 60.0)
        dew = float(obs.get("dew_point_2m") or (temp - ((100 - rh) / 5)))
        app_temp = float(obs.get("apparent_temperature") or (temp + 1.5))
        precip = float(obs.get("precipitation") or 0.0)
        rain = float(obs.get("rain") or precip)
        press = float(obs.get("surface_pressure") or 1005.0)
        et0 = float(obs.get("et0_fao_evapotranspiration") or 0.2)
        vpd = float(obs.get("vapour_pressure_deficit") or 1.2)
        wind_speed = float(obs.get("wind_speed_10m") or 10.0)
        wind_dir = float(obs.get("wind_direction_10m") or 90.0)
        wind_gusts = float(obs.get("wind_gusts_10m") or (wind_speed * 1.4))
        soil_temp = float(obs.get("soil_temperature_0_to_7cm") or temp)
        soil_moist = float(obs.get("soil_moisture_0_to_7cm") or 0.3)
        shortwave = float(obs.get("shortwave_radiation") or 400.0)
        dni = float(obs.get("direct_normal_irradiance") or 300.0)
        diffuse = float(obs.get("diffuse_radiation") or 100.0)
        cloud = float(obs.get("cloud_cover") or 20.0)

        # 1. Orthogonal Wind Vectors (km/h -> m/s)
        v_ms = wind_speed / 3.6
        rad = math.radians(wind_dir)
        wind_u = -v_ms * math.sin(rad)
        wind_v = -v_ms * math.cos(rad)

        # 2. Psychrometric Wet-Bulb Temperature (Stull formulation)
        wet_bulb = (
            temp * math.atan(0.151977 * math.sqrt(max(0, rh + 8.313659)))
            + math.atan(temp + rh)
            - math.atan(rh - 1.676331)
            + 0.00391838 * (rh ** 1.5) * math.atan(0.023101 * rh)
            - 4.686035
        )

        # 3. Cyclical Harmonic Time Encoding
        import datetime
        now = datetime.datetime.now(datetime.timezone.utc)
        hour = now.hour
        doy = now.timetuple().tm_yday
        sin_hour = math.sin(2 * math.pi * hour / 24.0)
        cos_hour = math.cos(2 * math.pi * hour / 24.0)
        sin_day = math.sin(2 * math.pi * doy / 365.25)
        cos_day = math.cos(2 * math.pi * doy / 365.25)

        # 4. Barometric pressure tendency (3h) and lags (t-1, t-2, t-3, t-24)
        press_tendency_3h = float(obs.get("pressure_tendency_3h") or -0.2)
        
        # Build features dict in EXACT 39-feature sequence
        return {
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
            "wind_gusts_10m": wind_gusts,
            "soil_temperature_0_to_7cm": soil_temp,
            "soil_moisture_0_to_7cm": soil_moist,
            "shortwave_radiation": shortwave,
            "direct_normal_irradiance": dni,
            "diffuse_radiation": diffuse,
            "cloud_cover": cloud,
            "wind_u_vector": round(wind_u, 4),
            "wind_v_vector": round(wind_v, 4),
            "wet_bulb_temp": round(wet_bulb, 2),
            "sin_hour": round(sin_hour, 4),
            "cos_hour": round(cos_hour, 4),
            "sin_day": round(sin_day, 4),
            "cos_day": round(cos_day, 4),
            "pressure_tendency_3h": press_tendency_3h,
            "temp_lag_1": float(obs.get("temp_lag_1", temp - 0.3)),
            "humidity_lag_1": float(obs.get("humidity_lag_1", rh + 2)),
            "radiation_lag_1": float(obs.get("radiation_lag_1", max(0, shortwave - 30))),
            "temp_lag_2": float(obs.get("temp_lag_2", temp - 0.7)),
            "humidity_lag_2": float(obs.get("humidity_lag_2", rh + 4)),
            "radiation_lag_2": float(obs.get("radiation_lag_2", max(0, shortwave - 60))),
            "temp_lag_3": float(obs.get("temp_lag_3", temp - 1.2)),
            "humidity_lag_3": float(obs.get("humidity_lag_3", rh + 6)),
            "radiation_lag_3": float(obs.get("radiation_lag_3", max(0, shortwave - 90))),
            "temp_lag_24": float(obs.get("temp_lag_24", temp - 0.5)),
            "humidity_lag_24": float(obs.get("humidity_lag_24", rh - 1)),
            "radiation_lag_24": float(obs.get("radiation_lag_24", shortwave)),
        }

    @staticmethod
    def build_disaster_features(telemetry: dict[str, Any]) -> dict[str, float]:
        """Builds all 20 disaster features (17 raw sensors + 3 interaction indicators from Disaster_management.ipynb)."""
        temp = float(telemetry.get("temp_2m") or telemetry.get("temperature_2m") or 28.0)
        p1h = float(telemetry.get("precip_1h") or telemetry.get("precipitation") or 0.0)
        r24 = float(telemetry.get("rain_24h") or telemetry.get("rainfall_24h") or 0.0)
        r48 = float(telemetry.get("rain_48h") or (r24 * 1.5))
        ws = float(telemetry.get("wind_speed_10m") or 12.0)
        wg = float(telemetry.get("wind_gusts_10m") or (ws * 1.4))
        sp = float(telemetry.get("surface_pressure") or 1008.0)
        wc = float(telemetry.get("weather_code") or 1.0)
        aqi = float(telemetry.get("us_aqi") or telemetry.get("european_aqi") or 45.0)
        pm = float(telemetry.get("pm2_5") or 22.0)
        river = float(telemetry.get("river_discharge") or 15.0)
        elev = float(telemetry.get("elevation") or 120.0)
        quake_mag = float(telemetry.get("max_quake_mag") or 0.0)
        quake_depth = float(telemetry.get("quake_depth") or 10.0)
        tsu_flag = float(telemetry.get("tsunami_flag") or 0.0)
        cyclone_flag = float(telemetry.get("gdacs_cyclone") or 0.0)
        volcano_flag = float(telemetry.get("gdacs_volcano") or 0.0)

        # 3 Domain engineered interaction indicators
        wind_press_shear = ws / (sp + 1e-5)
        precip_sat_rate = p1h / (r48 + 1.0)
        therm_part_idx = (pm * aqi) / (max(1.0, temp) + 10.0)

        return {
            "temp_2m": temp,
            "precip_1h": p1h,
            "rain_24h": r24,
            "rain_48h": r48,
            "wind_speed_10m": ws,
            "wind_gusts_10m": wg,
            "surface_pressure": sp,
            "weather_code": wc,
            "us_aqi": aqi,
            "pm2_5": pm,
            "river_discharge": river,
            "elevation": elev,
            "max_quake_mag": quake_mag,
            "quake_depth": quake_depth,
            "tsunami_flag": tsu_flag,
            "gdacs_cyclone": cyclone_flag,
            "gdacs_volcano": volcano_flag,
            "wind_pressure_shear": round(wind_press_shear, 6),
            "precipitation_saturation_rate": round(precip_sat_rate, 6),
            "thermal_particulate_index": round(therm_part_idx, 4),
        }


class WeatherModelAdapter(ModelAdapter):
    def __init__(self):
        super().__init__("weather")


class DisasterModelAdapter(ModelAdapter):
    def __init__(self):
        super().__init__("disaster")


weather_model = WeatherModelAdapter()
disaster_model = DisasterModelAdapter()
