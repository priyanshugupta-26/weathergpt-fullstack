import time
import httpx
from ..config import settings
from ..services.fusion import CAPAlertParser


class CAPProvider:
    def __init__(self):
        self.alerts = []
        self.checked = 0
        self.status = "not_configured"

    async def refresh(self):
        if not settings.cap_feed_url:
            return []
        if time.monotonic() - self.checked < 120:
            return self.alerts
        self.checked = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                async with client.stream("GET", settings.cap_feed_url) as response:
                    response.raise_for_status()
                    payload = b""
                    async for chunk in response.aiter_bytes():
                        payload += chunk
                        if len(payload) > 2_000_000:
                            raise ValueError("CAP too large")
            alerts = CAPAlertParser().parse(payload)
            for alert in alerts:
                if alert["msgType"] in ("Cancel", "Update"):
                    identifiers = [ref.split(",")[1] for ref in alert["references"].split() if len(ref.split(",")) >= 2]
                    self.alerts = [a for a in self.alerts if a["identifier"] not in identifiers]
                if alert["msgType"] != "Cancel":
                    self.alerts = [a for a in self.alerts if a["id"] != alert["id"]] + [alert]
            self.alerts = self.alerts[-200:]
            self.status = "healthy"
        except Exception:
            self.status = "unavailable"
            return []  # Never replay an unverified cached warning as live.
        return self.alerts


cap_provider = CAPProvider()
