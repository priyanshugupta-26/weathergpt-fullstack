"""Only build automatic ML features when every named training input is available."""

import hashlib
import logging
from datetime import datetime, timezone, timedelta
from models.adapters.adapter import disaster_model

log = logging.getLogger("weathergpt.prediction")


def model_alerts(weather, name):
    if weather.get("status") != "live" or disaster_model.model is None:
        return []
    schema = disaster_model.schema
    expected = schema["features"]
    available = weather.get("current", {})
    if any(key not in available or available[key] is None for key in expected):
        return []
    try:
        prediction = disaster_model.predict({key: available[key] for key in expected})
        mapping = schema.get("alert_mapping", {}).get(str(prediction["prediction"]))
        if not mapping:
            return []
        severity = mapping.get("severity")
        if severity not in [
            "INFO",
            "WATCH",
            "WARNING",
            "SEVERE",
            "EMERGENCY",
        ] or not mapping.get("recommendation"):
            log.warning("invalid_model_alert_mapping")
            return []
        identity = f"model:{weather.get('latitude')}:{weather.get('longitude')}:{weather.get('timestamp')}:{prediction['prediction']}"
        return [
            {
                "id": hashlib.sha256(identity.encode()).hexdigest()[:20],
                "alert_type": mapping.get("alert_type", "Weather"),
                "severity": severity,
                "confidence": prediction["confidence"],
                "location": name,
                "coordinates": {
                    "latitude": weather.get("latitude"),
                    "longitude": weather.get("longitude"),
                },
                "timestamp": weather.get("timestamp"),
                "expires": (
                    datetime.now(timezone.utc) + timedelta(minutes=30)
                ).isoformat(),
                "description": mapping.get(
                    "description", str(prediction["prediction"])
                ),
                "recommendation": mapping["recommendation"],
                "data_source": weather.get("source"),
                "model_source": prediction["model_source"],
                "official": False,
            }
        ]
    except Exception:
        log.exception("automatic_model_prediction_failed")
        return []
