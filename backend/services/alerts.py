"""Transparent screening thresholds, never official warnings or calibrated probabilities."""

import hashlib
from datetime import datetime, timezone, timedelta


class DisasterDetectionService:
    def evaluate(self, weather, name="Selected location"):
        if weather.get("status") != "live":
            return []
        c = weather.get("current", {})
        alerts = []
        rules = [
            (
                "Heat",
                c.get("temperature_2m"),
                40,
                "WARNING",
                "High temperature",
                "Reduce strenuous outdoor activity and check local heat guidance.",
            ),
            (
                "Wind",
                c.get("wind_gusts_10m"),
                60,
                "WARNING",
                "Strong wind gusts",
                "Secure loose objects and check official travel advisories.",
            ),
            (
                "Weather",
                c.get("precipitation"),
                15,
                "WARNING",
                "Intense precipitation",
                "Avoid waterlogged roads and monitor official rainfall warnings.",
            ),
        ]
        if c.get("temperature_2m") is not None and c["temperature_2m"] < -10:
            rules.append(
                (
                    "Weather",
                    1,
                    1,
                    "WATCH",
                    "Severe cold screening",
                    "Limit exposure and protect against cold.",
                )
            )
        for kind, value, threshold, severity, title, advice in rules:
            if value is None or value < threshold:
                continue
            stamp = weather.get("timestamp", "")
            alerts.append(
                {
                    "id": hashlib.sha256(
                        f"{kind}:{weather.get('latitude')}:{weather.get('longitude')}:{stamp}".encode()
                    ).hexdigest()[:20],
                    "alert_type": kind,
                    "severity": severity,
                    "confidence": None,
                    "location": name,
                    "coordinates": {
                        "latitude": weather.get("latitude"),
                        "longitude": weather.get("longitude"),
                    },
                    "timestamp": stamp,
                    "expires": (
                        datetime.now(timezone.utc) + timedelta(minutes=30)
                    ).isoformat(),
                    "description": title,
                    "recommendation": advice,
                    "data_source": weather.get("source"),
                    "model_source": "Rule screening · not an official warning",
                    "official": False,
                }
            )
        return alerts

    def prediction(self, features):
        alerts = self.evaluate(
            {"status": "live", "current": features, "source": "User-supplied features"}
        )
        return {
            "event": alerts[0]["description"] if alerts else "No threshold triggered",
            "risk": "elevated" if alerts else "undetermined",
            "confidence": None,
            "severity": alerts[0]["severity"] if alerts else "INFO",
            "recommendations": [a["recommendation"] for a in alerts],
            "mode": "rules",
            "model_source": "Non-model threshold screening",
            "limitations": "This is not an all-hazards assessment. Floods, cyclones and storms require additional data.",
        }


alerts_service = DisasterDetectionService()
