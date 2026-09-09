"""WeatherGPT ML Training Service.
Implements leak-free time-series sample construction, chronological validation,
multi-output regression training, per-target weather metrics, and Champion vs Challenger promotion gating.
"""

import asyncio
import json
import logging
import math
import traceback
from datetime import datetime, timezone
from typing import Any

import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.multioutput import MultiOutputRegressor
from sqlalchemy import select

from backend.database import Session, WeatherObservation, ModelVersion, TrainingJob
from backend.ml.features import feature_registry, MLFeatureBuilder, FeatureValidator
from backend.ml.registry import model_registry

log = logging.getLogger("weathergpt.ml.training")


def circular_angular_mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Calculates Mean Absolute Error for angular degrees [0..360), accounting for circular wrap-around.
    e.g., 359° and 1° are 2° apart, not 358°.
    """
    diff = np.abs(y_true - y_pred) % 360.0
    circular_diff = np.minimum(diff, 360.0 - diff)
    return float(np.mean(circular_diff))


class WeatherTrainingService:
    """Orchestrates end-to-end multi-output weather model training, evaluation, and promotion."""

    def __init__(self):
        self.is_training = False
        self.last_job_id: int | None = None

    def construct_training_dataset(
        self,
        min_samples: int = 40,
    ) -> tuple[np.ndarray, np.ndarray, list[str], list[str], dict[str, Any]]:
        """Extracts chronological observations from SQL and builds leak-free (X, Y) training arrays.
        
        For each point (lat, lon) at time T:
          X(T) = features derived strictly from observations at or before T.
          Y(T) = actual observation values at time T+1h.
        """
        with Session() as db:
            obs_rows = db.scalars(
                select(WeatherObservation)
                .where(WeatherObservation.data_type == "OBSERVATION")
                .order_by(WeatherObservation.latitude, WeatherObservation.longitude, WeatherObservation.timestamp.asc())
            ).all()

        if len(obs_rows) < min_samples:
            raise ValueError(
                f"Insufficient observation samples for training: found {len(obs_rows)}, require at least {min_samples}"
            )

        # Group observations by station / grid location
        loc_groups: dict[tuple[float, float], list[WeatherObservation]] = {}
        for r in obs_rows:
            loc_key = (round(r.latitude, 3), round(r.longitude, 3))
            loc_groups.setdefault(loc_key, []).append(r)

        feature_names = feature_registry.feature_names
        target_names = feature_registry.target_names

        X_rows = []
        Y_rows = []
        timestamps = []

        for loc_key, records in loc_groups.items():
            if len(records) < 4:
                continue

            # Convert records to dictionary format for fast lag lookup
            records_dict = []
            for rec in records:
                records_dict.append({
                    "id": rec.id,
                    "latitude": rec.latitude,
                    "longitude": rec.longitude,
                    "timestamp": rec.timestamp,
                    "temperature_2m": rec.temperature,
                    "relative_humidity_2m": rec.humidity,
                    "dew_point_2m": rec.dew_point,
                    "apparent_temperature": rec.feels_like,
                    "surface_pressure": rec.surface_pressure,
                    "wind_speed_10m": rec.wind_speed,
                    "wind_direction_10m": rec.wind_direction,
                    "wind_gusts_10m": rec.wind_gust,
                    "precipitation": rec.precipitation or 0.0,
                    "rain": rec.rainfall or 0.0,
                    "cloud_cover": rec.cloud_cover,
                    "soil_temperature_0_to_7cm": rec.soil_temperature,
                    "soil_moisture_0_to_7cm": rec.soil_moisture,
                    "shortwave_radiation": rec.shortwave_radiation,
                    "direct_normal_irradiance": rec.direct_normal_irradiance,
                    "diffuse_radiation": rec.diffuse_radiation,
                    "et0_fao_evapotranspiration": rec.et0_fao_evapotranspiration,
                    "vapour_pressure_deficit": rec.vapour_pressure_deficit,
                })

            for i in range(len(records_dict) - 1):
                cur_obs = records_dict[i]
                next_obs = records_dict[i + 1]

                # Check that next_obs is within 1 to 3 hours ahead (avoid huge time gaps)
                try:
                    t_cur = datetime.fromisoformat(cur_obs["timestamp"].replace("Z", "+00:00"))
                    t_next = datetime.fromisoformat(next_obs["timestamp"].replace("Z", "+00:00"))
                    time_diff_hours = (t_next - t_cur).total_seconds() / 3600.0
                    if not (0.5 <= time_diff_hours <= 3.5):
                        continue
                except Exception:
                    continue

                # Build past lags from earlier records in the series (strictly <= i)
                past_lags = {}
                if i >= 1:
                    past_lags["lag_1h"] = records_dict[i - 1]
                if i >= 2:
                    past_lags["lag_2h"] = records_dict[i - 2]
                if i >= 3:
                    past_lags["lag_3h"] = records_dict[i - 3]
                if i >= 24:
                    past_lags["lag_24h"] = records_dict[i - 24]

                # Build feature vector at time T
                feat_dict = MLFeatureBuilder.build_features_from_obs(cur_obs, past_lags, feature_registry)
                feat_vector = [feat_dict[name] for name in feature_names]

                # Build target vector at time T+1
                target_vector = []
                has_missing_target = False
                for t_name in target_names:
                    val = next_obs.get(t_name)
                    if val is None or not math.isfinite(float(val)):
                        # If primary target like temp or humidity is missing, skip sample
                        if feature_registry.target_map.get(t_name, {}).get("critical", False):
                            has_missing_target = True
                            break
                        val = cur_obs.get(t_name, 0.0) or 0.0
                    target_vector.append(float(val))

                if has_missing_target:
                    continue

                X_rows.append(feat_vector)
                Y_rows.append(target_vector)
                timestamps.append(cur_obs["timestamp"])

        if len(X_rows) < min_samples:
            raise ValueError(f"Insufficient contiguous time-series pairs: only {len(X_rows)} samples constructed.")

        X = np.array(X_rows, dtype=np.float64)
        Y = np.array(Y_rows, dtype=np.float64)

        metadata = {
            "total_samples": len(X),
            "start_time": min(timestamps) if timestamps else None,
            "end_time": max(timestamps) if timestamps else None,
            "feature_count": len(feature_names),
            "target_count": len(target_names),
        }

        return X, Y, feature_names, target_names, metadata

    def evaluate_model(
        self,
        model: Any,
        X_val: np.ndarray,
        Y_val: np.ndarray,
        target_names: list[str],
    ) -> dict[str, Any]:
        """Calculates per-target MAE, RMSE, R2, circular angular MAE, and multi-output aggregate score."""
        Y_pred = model.predict(X_val)
        if Y_pred.ndim == 1:
            Y_pred = Y_pred.reshape(-1, 1)

        metrics: dict[str, Any] = {"per_target": {}, "aggregate": {}}
        maes = []
        rmses = []

        for idx, t_name in enumerate(target_names):
            y_t = Y_val[:, idx]
            y_p = Y_pred[:, idx]

            is_circ = feature_registry.target_map.get(t_name, {}).get("is_circular", False)
            if is_circ:
                mae = circular_angular_mae(y_t, y_p)
            else:
                mae = float(np.mean(np.abs(y_t - y_p)))

            rmse = float(np.sqrt(np.mean((y_t - y_p) ** 2)))
            var_yt = float(np.var(y_t))
            r2 = float(1.0 - (rmse ** 2 / (var_yt + 1e-6)))

            metrics["per_target"][t_name] = {
                "mae": round(mae, 3),
                "rmse": round(rmse, 3),
                "r2": round(r2, 3),
                "unit": feature_registry.target_map.get(t_name, {}).get("unit", ""),
            }
            maes.append(mae)
            rmses.append(rmse)

        metrics["aggregate"] = {
            "mean_mae": round(float(np.mean(maes)), 3),
            "mean_rmse": round(float(np.mean(rmses)), 3),
            "val_samples": int(len(X_val)),
        }
        return metrics

    def compare_challenger_against_champion(
        self,
        challenger_metrics: dict[str, Any],
        champion_metrics: dict[str, Any] | None,
    ) -> tuple[bool, str]:
        """Validates if challenger model should be promoted over the champion.
        
        Rules:
        - If no champion exists: promote immediately as v001.
        - Challenger must improve or match overall aggregate score.
        - Critical targets (temperature, humidity, wind, pressure) must not degrade beyond tolerance.
        """
        if not champion_metrics or "aggregate" not in champion_metrics:
            return True, "Initial model bootstrap: established first Champion"

        challenger_mae = challenger_metrics.get("aggregate", {}).get("mean_mae", 999.0)
        champion_mae = champion_metrics.get("aggregate", {}).get("mean_mae", 999.0)

        # Check critical targets tolerance
        challenger_targets = challenger_metrics.get("per_target", {})
        champion_targets = champion_metrics.get("per_target", {})

        for t_name, t_meta in feature_registry.target_map.items():
            if t_meta.get("critical", False):
                c_mae = challenger_targets.get(t_name, {}).get("mae")
                p_mae = champion_targets.get(t_name, {}).get("mae")
                tol = t_meta.get("tolerance_mae", 1.0)
                if c_mae is not None and p_mae is not None:
                    # Degradation check
                    if c_mae > p_mae + tol:
                        return False, f"Rejected: Critical target '{t_name}' degraded by {round(c_mae - p_mae, 2)} > tolerance ({tol})"

        # Overall aggregate improvement check
        if challenger_mae <= champion_mae * 1.02:  # Improved or within 2% margin with better consistency
            return True, f"Challenger improved aggregate MAE: {challenger_mae} vs Champion: {champion_mae}"
        else:
            return False, f"Challenger MAE ({challenger_mae}) did not outperform Champion ({champion_mae})"

    def run_training_job(
        self,
        trigger_type: str = "MANUAL",
        algorithm_name: str = "HistGradientBoosting",
    ) -> dict[str, Any]:
        """Synchronous execution of training pipeline; suitable for running in thread pools."""
        self.is_training = True
        job_id = None
        new_version = model_registry.next_version_tag()

        with Session.begin() as db:
            job = TrainingJob(
                status="RUNNING",
                trigger_type=trigger_type,
                started_at=datetime.now(timezone.utc).isoformat(),
                candidate_version=new_version,
                logs=f"Started training job for candidate version {new_version}...\n",
            )
            db.add(job)
            db.flush()
            job_id = job.id
            self.last_job_id = job_id

        try:
            log.info("Job #%d: Constructing time-series training dataset...", job_id)
            X, Y, feat_names, targ_names, meta = self.construct_training_dataset()

            # Chronological 80/20 time-series split
            n_samples = len(X)
            split_idx = int(n_samples * 0.8)
            X_train, X_val = X[:split_idx], X[split_idx:]
            Y_train, Y_val = Y[:split_idx], Y[split_idx:]

            log.info(
                "Job #%d: Split: %d train samples, %d validation holdout samples.",
                job_id,
                len(X_train),
                len(X_val),
            )

            # Select and train algorithm
            log.info("Job #%d: Training multi-output %s regressor...", job_id, algorithm_name)
            base_est = HistGradientBoostingRegressor(
                max_iter=100,
                learning_rate=0.08,
                max_leaf_nodes=31,
                random_state=42,
            )
            model = MultiOutputRegressor(base_est)
            model.fit(X_train, Y_train)

            # Evaluate on validation holdout
            log.info("Job #%d: Evaluating challenger metrics on holdout set...", job_id)
            challenger_metrics = self.evaluate_model(model, X_val, Y_val, targ_names)

            # Save versioned artifact
            model_metadata = {
                "model_name": "weathergpt_ml",
                "version": new_version,
                "algorithm": algorithm_name,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "training_rows": len(X_train),
                "validation_rows": len(X_val),
                "training_start": meta["start_time"],
                "training_end": meta["end_time"],
                "metrics": challenger_metrics,
            }
            artifact_path = model_registry.save_artifact(
                new_version,
                model,
                model_metadata,
                challenger_metrics,
                feat_names,
                targ_names,
            )

            # Retrieve active champion metrics for gating comparison
            champion = model_registry.active_champion or model_registry.load_active_champion()
            champion_metrics = champion.metadata.get("metrics") if champion else None

            should_promote, decision_reason = self.compare_challenger_against_champion(
                challenger_metrics, champion_metrics
            )

            status = "CHAMPION" if should_promote else "REJECTED"

            with Session.begin() as db:
                v_row = ModelVersion(
                    model_name="weathergpt_ml",
                    model_type="multi_output_regressor",
                    version=new_version,
                    algorithm=algorithm_name,
                    training_start=meta["start_time"],
                    training_end=meta["end_time"],
                    training_rows=len(X_train),
                    feature_schema_version=feature_registry.schema_version,
                    target_schema_version=feature_registry.schema_version,
                    metrics=json.dumps(challenger_metrics),
                    artifact_path=str(artifact_path),
                    status=status,
                    parent_model=model_registry.active_champion.version if model_registry.active_champion else None,
                    promotion_reason=decision_reason,
                )
                db.add(v_row)

                # Update job status
                job_rec = db.get(TrainingJob, job_id)
                if job_rec:
                    job_rec.status = "PROMOTED" if should_promote else "REJECTED"
                    job_rec.completed_at = datetime.now(timezone.utc).isoformat()
                    job_rec.metrics_summary = json.dumps(challenger_metrics)
                    job_rec.logs = (job_rec.logs or "") + f"Evaluation decision: {decision_reason}\nFinal Status: {status}\n"

            if should_promote:
                model_registry.promote_challenger(new_version, reason=decision_reason)
            else:
                model_registry.reject_challenger(new_version, reason=decision_reason)

            log.info("Job #%d complete: %s (%s)", job_id, status, decision_reason)
            return {
                "job_id": job_id,
                "version": new_version,
                "status": status,
                "decision": decision_reason,
                "metrics": challenger_metrics,
            }

        except Exception as e:
            err_msg = traceback.format_exc()
            log.error("Training job #%d failed: %s", job_id, e)
            with Session.begin() as db:
                if job_id:
                    job_rec = db.get(TrainingJob, job_id)
                    if job_rec:
                        job_rec.status = "FAILED"
                        job_rec.error_message = str(e)
                        job_rec.logs = (job_rec.logs or "") + f"ERROR: {err_msg}\n"
            raise e
        finally:
            self.is_training = False


training_service = WeatherTrainingService()
