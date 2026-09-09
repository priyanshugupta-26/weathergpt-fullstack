"""WeatherGPT ML Data Quality Engine.
Performs physical validation, boundary checks, duplicate rejection, and outlier flagging.
"""

import logging
import math
from datetime import datetime, timezone
from typing import Any

from backend.database import Session, DataQualityReport

log = logging.getLogger("weathergpt.ml.quality")


class DataQualityService:
    """Validates raw meteorological observations against physics boundaries and quality constraints."""

    BOUNDARIES = {
        "temperature": (-50.0, 60.0),       # °C
        "feels_like": (-60.0, 70.0),        # °C
        "humidity": (0.0, 100.0),           # %
        "dew_point": (-55.0, 45.0),         # °C
        "surface_pressure": (800.0, 1100.0),# hPa
        "mslp": (850.0, 1100.0),            # hPa
        "pressure": (800.0, 1100.0),        # hPa
        "wind_speed": (0.0, 450.0),         # km/h
        "wind_direction": (0.0, 360.0),     # deg
        "wind_gust": (0.0, 500.0),          # km/h
        "precipitation": (0.0, 400.0),      # mm in 1h
        "rainfall": (0.0, 400.0),           # mm in 1h
        "cloud_cover": (0.0, 100.0),        # %
        "visibility": (0.0, 100000.0),      # m
        "shortwave_radiation": (0.0, 1500.0),# W/m2
        "soil_temperature": (-40.0, 70.0),  # °C
        "soil_moisture": (0.0, 1.0),        # m3/m3
    }

    @classmethod
    def validate_observation(cls, obs: dict[str, Any]) -> tuple[bool, str, list[str]]:
        """Validates an observation record.
        
        Returns:
            (is_valid, quality_flag, issues)
            quality_flag can be:
            - 'VALID': passed all quality checks
            - 'SUSPICIOUS': passed basic physical viability but has suspicious outliers
            - 'REJECTED': fatally flawed (missing coordinates, invalid timestamp, impossible physics)
        """
        issues: list[str] = []

        # 1. Coordinate check
        lat = obs.get("latitude")
        lon = obs.get("longitude")
        if lat is None or lon is None:
            return False, "REJECTED", ["Missing latitude or longitude"]
        try:
            lat = float(lat)
            lon = float(lon)
            if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
                return False, "REJECTED", [f"Coordinates out of bounds: lat={lat}, lon={lon}"]
        except (ValueError, TypeError):
            return False, "REJECTED", ["Invalid coordinate types"]

        # 2. Timestamp check
        ts = obs.get("timestamp")
        if not ts:
            return False, "REJECTED", ["Missing observation timestamp"]
        try:
            # Validate ISO timestamp format
            datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        except Exception:
            return False, "REJECTED", [f"Invalid ISO timestamp: {ts}"]

        # 3. Physics boundaries
        fatal_error = False
        suspicious = False

        for field, (low, high) in cls.BOUNDARIES.items():
            val = obs.get(field)
            if val is not None:
                try:
                    num_val = float(val)
                    if not math.isfinite(num_val):
                        issues.append(f"{field} is non-finite: {val}")
                        fatal_error = True
                        continue

                    # Extreme breach -> Fatal
                    if field in ("temperature", "humidity", "surface_pressure", "precipitation"):
                        if field == "humidity" and (num_val < 0.0 or num_val > 100.0):
                            issues.append(f"Physical humidity violation: {num_val}%")
                            fatal_error = True
                        elif field == "precipitation" and num_val < 0.0:
                            issues.append(f"Negative precipitation violation: {num_val} mm")
                            fatal_error = True
                        elif field == "temperature" and (num_val < -60.0 or num_val > 70.0):
                            issues.append(f"Extreme impossible temperature: {num_val}°C")
                            fatal_error = True
                        elif field == "surface_pressure" and (num_val < 700.0 or num_val > 1200.0):
                            issues.append(f"Extreme impossible pressure: {num_val} hPa")
                            fatal_error = True

                    # Boundary breach -> Suspicious outlier
                    if num_val < low or num_val > high:
                        issues.append(f"Outlier in {field}: {num_val} (expected {low}..{high})")
                        suspicious = True

                except (ValueError, TypeError):
                    issues.append(f"Cannot cast {field} to float: {val}")
                    suspicious = True

        if fatal_error:
            return False, "REJECTED", issues
        elif suspicious:
            return True, "SUSPICIOUS", issues
        else:
            return True, "VALID", []

    @classmethod
    def record_quality_report(
        cls,
        provider: str,
        records_checked: int,
        duplicates_skipped: int,
        outliers_flagged: int,
        missing_fields_ratio: float = 0.0,
        status: str = "PASSED",
    ):
        """Persists a data quality report row to the database."""
        try:
            with Session.begin() as db:
                report = DataQualityReport(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    provider=provider,
                    records_checked=records_checked,
                    duplicates_skipped=duplicates_skipped,
                    outliers_flagged=outliers_flagged,
                    missing_fields_ratio=missing_fields_ratio,
                    status=status,
                )
                db.add(report)
        except Exception as e:
            log.error("Failed to save data quality report: %s", e)
