"""WeatherGPT ML Prediction Verification Service.
Matches past forecasts against subsequently arrived ground-truth observations to compute rolling verification metrics.
"""

import logging
import math
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
from sqlalchemy import select, func, and_

from backend.database import Session, ModelPrediction, WeatherObservation, PredictionActual

log = logging.getLogger("weathergpt.ml.verification")


class PredictionVsActualService:
    """Logs predictions and asynchronously matches them against actual meteorological observations."""

    @staticmethod
    def log_prediction(
        model_version: str,
        location: str,
        latitude: float,
        longitude: float,
        forecast_valid_at: str,
        predictions: dict[str, float],
        features_hash: str | None = None,
    ) -> str:
        """Stores each individual target prediction for later verification."""
        pred_id = str(uuid.uuid4())
        gen_time = datetime.now(timezone.utc).isoformat()

        with Session.begin() as db:
            for t_name, val in predictions.items():
                rec = ModelPrediction(
                    prediction_id=pred_id,
                    model_version=model_version,
                    location=location,
                    latitude=round(latitude, 3),
                    longitude=round(longitude, 3),
                    prediction_generated_at=gen_time,
                    forecast_valid_at=forecast_valid_at,
                    target_name=t_name,
                    predicted_value=float(val),
                    source_features_hash=features_hash,
                )
                db.add(rec)

        return pred_id

    @staticmethod
    def verify_pending_predictions() -> int:
        """Scans unverified predictions and fills actual_value from real observations."""
        now_iso = datetime.now(timezone.utc).isoformat()
        verified_count = 0

        with Session() as db:
            pending = db.scalars(
                select(ModelPrediction).where(
                    ModelPrediction.actual_value.is_(None),
                    ModelPrediction.forecast_valid_at <= now_iso,
                ).limit(200)
            ).all()

        if not pending:
            return 0

        for pred in pending:
            try:
                target_dt = datetime.fromisoformat(pred.forecast_valid_at.replace("Z", "+00:00"))
                window_start = (target_dt - timedelta(minutes=90)).isoformat()
                window_end = (target_dt + timedelta(minutes=90)).isoformat()

                with Session.begin() as db:
                    # Find nearest real observation in the time and location window
                    obs = db.scalars(
                        select(WeatherObservation).where(
                            WeatherObservation.latitude.between(pred.latitude - 0.2, pred.latitude + 0.2),
                            WeatherObservation.longitude.between(pred.longitude - 0.2, pred.longitude + 0.2),
                            WeatherObservation.data_type == "OBSERVATION",
                            WeatherObservation.timestamp >= window_start,
                            WeatherObservation.timestamp <= window_end,
                        )
                    ).first()

                    if not obs:
                        continue

                    # Extract actual value based on target_name
                    actual_val = None
                    if pred.target_name in ("temperature", "temperature_2m"):
                        actual_val = obs.temperature
                    elif pred.target_name in ("humidity", "relative_humidity_2m"):
                        actual_val = obs.humidity
                    elif pred.target_name in ("pressure", "surface_pressure"):
                        actual_val = obs.surface_pressure
                    elif pred.target_name in ("wind_speed", "wind_speed_10m"):
                        actual_val = obs.wind_speed
                    elif pred.target_name in ("wind_direction", "wind_direction_10m"):
                        actual_val = obs.wind_direction
                    elif pred.target_name in ("precipitation", "rain"):
                        actual_val = obs.precipitation
                    elif pred.target_name == "cloud_cover":
                        actual_val = obs.cloud_cover
                    elif pred.target_name in ("dew_point", "dew_point_2m"):
                        actual_val = obs.dew_point

                    if actual_val is None:
                        continue

                    actual_float = float(actual_val)
                    if pred.target_name in ("wind_direction", "wind_direction_10m"):
                        diff = abs(pred.predicted_value - actual_float) % 360.0
                        abs_err = min(diff, 360.0 - diff)
                        err = abs_err
                    else:
                        err = pred.predicted_value - actual_float
                        abs_err = abs(err)

                    # Update prediction record
                    pred_rec = db.get(ModelPrediction, pred.id)
                    if pred_rec:
                        pred_rec.actual_value = round(actual_float, 2)
                        pred_rec.error = round(err, 2)
                        pred_rec.absolute_error = round(abs_err, 2)

                    db.add(
                        PredictionActual(
                            prediction_id=pred.prediction_id,
                            observation_id=obs.id,
                            time_difference_seconds=abs(
                                (datetime.fromisoformat(obs.timestamp.replace("Z", "+00:00")) - target_dt).total_seconds()
                            ),
                        )
                    )
                    verified_count += 1

            except Exception as e:
                log.warning("Verification error for pred #%d: %s", pred.id, e)

        return verified_count

    @staticmethod
    def get_rolling_accuracy(hours: int = 720) -> dict[str, Any]:
        """Computes rolling MAE and RMSE per target variable over a specified time window."""
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

        with Session() as db:
            rows = db.scalars(
                select(ModelPrediction).where(
                    ModelPrediction.actual_value.is_not(None),
                    ModelPrediction.forecast_valid_at >= cutoff,
                )
            ).all()

        per_target: dict[str, list[float]] = {}
        for r in rows:
            if r.absolute_error is not None:
                per_target.setdefault(r.target_name, []).append(r.absolute_error)

        results = {}
        for t_name, errors in per_target.items():
            results[t_name] = {
                "count": len(errors),
                "mae": round(float(np.mean(errors)), 2),
                "rmse": round(float(np.sqrt(np.mean(np.array(errors) ** 2))), 2),
            }

        return {
            "window_hours": hours,
            "total_verified": len(rows),
            "targets": results,
        }

    @staticmethod
    def get_recent_prediction_series(target_name: str = "temperature_2m", limit: int = 30) -> list[dict[str, Any]]:
        """Returns paired predicted vs actual points for charting."""
        with Session() as db:
            records = db.scalars(
                select(ModelPrediction)
                .where(
                    ModelPrediction.target_name == target_name,
                )
                .order_by(ModelPrediction.id.desc())
                .limit(limit)
            ).all()

        return [
            {
                "time": r.forecast_valid_at,
                "location": r.location,
                "predicted": r.predicted_value,
                "actual": r.actual_value,
                "error": r.absolute_error,
                "version": r.model_version,
            }
            for r in reversed(records)
        ]


verification_service = PredictionVsActualService()
