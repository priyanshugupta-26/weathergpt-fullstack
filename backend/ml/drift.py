"""WeatherGPT ML Concept and Data Drift Detection Service.
Monitors atmospheric parameter distributions to detect meteorological shifts and seasonal transitions.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
from scipy.stats import ks_2samp
from sqlalchemy import select

from backend.database import Session, WeatherObservation, DriftMetric

log = logging.getLogger("weathergpt.ml.drift")


class DriftDetectionService:
    """Calculates distribution divergence between baseline observations and recent operational telemetry."""

    VARIABLES = [
        ("temperature", "temperature_2m"),
        ("humidity", "relative_humidity_2m"),
        ("surface_pressure", "surface_pressure"),
        ("wind_speed", "wind_speed_10m"),
        ("rainfall", "precipitation"),
    ]

    @classmethod
    def calculate_drift(cls, baseline_days: int = 14, recent_hours: int = 48) -> dict[str, Any]:
        """Runs two-sample Kolmogorov-Smirnov tests across core weather parameters."""
        now_dt = datetime.now(timezone.utc)
        recent_threshold = (now_dt - timedelta(hours=recent_hours)).isoformat()
        baseline_start = (now_dt - timedelta(days=baseline_days)).isoformat()

        with Session() as db:
            recent_rows = db.scalars(
                select(WeatherObservation).where(
                    WeatherObservation.data_type == "OBSERVATION",
                    WeatherObservation.timestamp >= recent_threshold,
                )
            ).all()

            baseline_rows = db.scalars(
                select(WeatherObservation).where(
                    WeatherObservation.data_type == "OBSERVATION",
                    WeatherObservation.timestamp >= baseline_start,
                    WeatherObservation.timestamp < recent_threshold,
                )
            ).all()

        results = {
            "evaluated_at": now_dt.isoformat(),
            "baseline_samples": len(baseline_rows),
            "recent_samples": len(recent_rows),
            "metrics": {},
            "drift_warning": False,
        }

        if len(baseline_rows) < 20 or len(recent_rows) < 10:
            results["message"] = "Insufficient samples to compute statistically valid drift."
            return results

        overall_drift_flag = False

        for attr, label in cls.VARIABLES:
            base_vals = [getattr(r, attr, None) for r in baseline_rows if getattr(r, attr, None) is not None]
            rec_vals = [getattr(r, attr, None) for r in recent_rows if getattr(r, attr, None) is not None]

            if len(base_vals) < 10 or len(rec_vals) < 5:
                continue

            ks_res = ks_2samp(base_vals, rec_vals)
            ks_stat = round(float(ks_res.statistic), 4)
            p_val = round(float(ks_res.pvalue), 4)
            drift_detected = bool(p_val < 0.05 and ks_stat > 0.20)

            if drift_detected:
                overall_drift_flag = True

            base_mean = round(float(np.mean(base_vals)), 2)
            rec_mean = round(float(np.mean(rec_vals)), 2)

            results["metrics"][label] = {
                "ks_statistic": ks_stat,
                "p_value": p_val,
                "drift_detected": drift_detected,
                "baseline_mean": base_mean,
                "recent_mean": rec_mean,
                "delta_mean": round(rec_mean - base_mean, 2),
            }

            try:
                with Session.begin() as db:
                    db.add(
                        DriftMetric(
                            calculated_at=now_dt.isoformat(),
                            baseline_period=f"{baseline_days}d",
                            comparison_period=f"{recent_hours}h",
                            target_name=label,
                            ks_statistic=ks_stat,
                            p_value=p_val,
                            drift_detected=1 if drift_detected else 0,
                            details_json=json.dumps(results["metrics"][label]),
                        )
                    )
            except Exception as e:
                log.warning("Could not persist drift metric for %s: %s", label, e)

        results["drift_warning"] = overall_drift_flag
        return results


drift_service = DriftDetectionService()
