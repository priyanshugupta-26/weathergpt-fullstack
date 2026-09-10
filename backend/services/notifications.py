"""
Geo-targeted Web Push & Native Firebase Cloud Messaging (FCM) Service for WeatherGPT
Implements VAPID-authenticated Web Push (RFC 8291 / RFC 8292), native FCM push,
device token registration, deduplication, anti-spam severity thresholds,
and in-app notification tracking.
"""
import os
import json
import base64
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select, update, delete, func
from py_vapid import Vapid
from cryptography.hazmat.primitives import serialization
from pywebpush import webpush, WebPushException

try:
    import firebase_admin
    from firebase_admin import credentials, messaging
    from firebase_admin.exceptions import FirebaseError
    HAS_FIREBASE = True
except ImportError:
    HAS_FIREBASE = False

from ..database import (
    Session,
    UserPushSubscription,
    InAppNotification,
    User,
    Location,
    PushDevice,
    PushDeliveryLog,
)
from ..config import settings, ROOT

log = logging.getLogger("weathergpt.notifications")

VAPID_FILE = ROOT / "data" / "vapid_keys.json"
FIREBASE_CREDS_FILE = ROOT / "data" / "firebase-service-account.json"


class NotificationService:
    def __init__(self):
        self._public_key_b64: str = ""
        self._private_key_pem: str = ""
        self._firebase_status: str = "NOT CONFIGURED"
        self._firebase_app = None
        self._ensure_vapid_keys()
        self._init_firebase()

    def _ensure_vapid_keys(self):
        """Ensure persistent VAPID keypair exists for Web Push."""
        if settings.vapid_public_key and settings.vapid_private_key:
            self._public_key_b64 = settings.vapid_public_key.strip()
            self._private_key_pem = settings.vapid_private_key.strip()
            return

        if VAPID_FILE.exists():
            try:
                with open(VAPID_FILE, "r") as f:
                    data = json.load(f)
                    if data.get("public_key") and data.get("private_key"):
                        self._public_key_b64 = data["public_key"]
                        self._private_key_pem = data["private_key"]
                        return
            except Exception as e:
                log.warning("Failed to load existing VAPID keys: %s", e)

        try:
            vapid = Vapid()
            vapid.generate_keys()
            raw_pub = vapid.public_key.public_bytes(
                serialization.Encoding.X962,
                serialization.PublicFormat.UncompressedPoint,
            )
            self._public_key_b64 = base64.urlsafe_b64encode(raw_pub).rstrip(b"=").decode("utf-8")
            self._private_key_pem = vapid.private_pem().decode("utf-8")

            VAPID_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(VAPID_FILE, "w") as f:
                json.dump({
                    "public_key": self._public_key_b64,
                    "private_key": self._private_key_pem,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }, f, indent=2)
            log.info("Generated new persistent VAPID keypair for Web Push")
        except Exception as e:
            log.error("Error generating VAPID keys: %s", e)

    def _init_firebase(self):
        """Initialize Firebase Admin SDK for FCM push notifications if credentials available."""
        if not HAS_FIREBASE:
            self._firebase_status = "NOT INSTALLED"
            log.warning("firebase-admin package not available")
            return

        try:
            # Check if an existing app is already initialized
            if firebase_admin._apps:
                self._firebase_app = firebase_admin.get_app()
                self._firebase_status = "CONNECTED"
                log.info("Firebase Admin already initialized")
                return

            cred = None
            # 1. Check raw JSON string in config/env
            if getattr(settings, "firebase_service_account_json", ""):
                raw = settings.firebase_service_account_json.strip()
                try:
                    cert_dict = json.loads(raw)
                    cred = credentials.Certificate(cert_dict)
                except Exception:
                    pass

            # 2. Check file path in settings
            if not cred and getattr(settings, "firebase_credentials_path", ""):
                p = Path(settings.firebase_credentials_path)
                if p.exists():
                    cred = credentials.Certificate(str(p))

            # 3. Check data/firebase-service-account.json
            if not cred and FIREBASE_CREDS_FILE.exists():
                cred = credentials.Certificate(str(FIREBASE_CREDS_FILE))

            # 4. Check GOOGLE_APPLICATION_CREDENTIALS env var
            if not cred and os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
                gac = Path(os.environ["GOOGLE_APPLICATION_CREDENTIALS"])
                if gac.exists():
                    cred = credentials.Certificate(str(gac))

            if cred:
                self._firebase_app = firebase_admin.initialize_app(cred)
                self._firebase_status = "CONNECTED"
                log.info("Firebase Admin successfully initialized for FCM push")
            else:
                self._firebase_status = "NOT CONFIGURED"
                log.info("FIREBASE CONFIG REQUIRED: Place service account credentials in backend/data/firebase-service-account.json or set FIREBASE_SERVICE_ACCOUNT_JSON")
        except Exception as e:
            self._firebase_status = "ERROR"
            log.warning("Firebase Admin initialization error: %s", e)

    @property
    def public_key(self) -> str:
        """Returns applicationServerKey suitable for browser pushManager.subscribe."""
        return self._public_key_b64

    @property
    def firebase_status(self) -> str:
        return self._firebase_status

    # ========================================================
    # Native Push Device Registration (Android / FCM / Web)
    # ========================================================
    def register_device(
        self,
        user_id: int,
        platform: str,
        device_token: str,
        device_name: str = "Device",
        p256dh: str | None = None,
        auth: str | None = None,
    ) -> dict[str, Any]:
        """Registers an Android FCM device token or Web Push subscription."""
        if not device_token:
            raise ValueError("device_token is required")

        norm_platform = (platform or "android").lower()
        now_str = datetime.now(timezone.utc).isoformat()

        with Session.begin() as db:
            existing = db.scalar(
                select(PushDevice).where(PushDevice.device_token == device_token)
            )
            if existing:
                existing.user_id = user_id
                existing.platform = norm_platform
                existing.device_name = device_name
                existing.enabled = 1
                existing.updated_at = now_str
                existing.last_seen = now_str
                dev_id = existing.id
            else:
                new_dev = PushDevice(
                    user_id=user_id,
                    platform=norm_platform,
                    device_token=device_token,
                    device_name=device_name,
                    enabled=1,
                    created_at=now_str,
                    updated_at=now_str,
                    last_seen=now_str,
                )
                db.add(new_dev)
                db.flush()
                dev_id = new_dev.id

        # Also store in WebPush table if browser keys provided
        if p256dh and auth:
            try:
                self.subscribe_user(
                    user_id,
                    {"endpoint": device_token, "keys": {"p256dh": p256dh, "auth": auth}},
                    device_name=device_name,
                )
            except Exception as e:
                log.debug("WebPush table sync error: %s", e)

        return {
            "status": "registered",
            "device_id": dev_id,
            "platform": norm_platform,
            "device_name": device_name,
        }

    def unregister_device(self, user_id: int, device_token: str) -> dict[str, Any]:
        """Disables push notifications for a specific device."""
        now_str = datetime.now(timezone.utc).isoformat()
        with Session.begin() as db:
            db.execute(
                update(PushDevice)
                .where(PushDevice.user_id == user_id, PushDevice.device_token == device_token)
                .values(enabled=0, updated_at=now_str)
            )
            # Also unregister from web push if it exists
            db.execute(
                update(UserPushSubscription)
                .where(UserPushSubscription.user_id == user_id, UserPushSubscription.endpoint == device_token)
                .values(enabled=0)
            )
        return {"status": "unregistered"}

    def get_user_devices(self, user_id: int) -> list[dict[str, Any]]:
        """Returns all registered devices for an authenticated user."""
        with Session() as db:
            devices = db.scalars(
                select(PushDevice).where(PushDevice.user_id == user_id).order_by(PushDevice.id.desc())
            ).all()
            return [
                {
                    "id": d.id,
                    "platform": d.platform,
                    "device_name": d.device_name,
                    "device_token_preview": (d.device_token[:12] + "..." + d.device_token[-8:]) if len(d.device_token) > 24 else d.device_token,
                    "enabled": bool(d.enabled),
                    "created_at": d.created_at,
                    "last_seen": d.last_seen,
                }
                for d in devices
            ]

    # ========================================================
    # Web Push (Browsers / PWA)
    # ========================================================
    def subscribe_user(self, user_id: int, subscription_info: dict[str, Any], device_name: str = "Web Browser") -> dict[str, Any]:
        endpoint = subscription_info.get("endpoint", "")
        keys = subscription_info.get("keys", {})
        p256dh = keys.get("p256dh", "")
        auth = keys.get("auth", "")

        if not endpoint or not p256dh or not auth:
            raise ValueError("Invalid subscription info: missing endpoint or encryption keys")

        now_str = datetime.now(timezone.utc).isoformat()
        with Session.begin() as db:
            existing = db.scalar(
                select(UserPushSubscription).where(
                    UserPushSubscription.user_id == user_id,
                    UserPushSubscription.endpoint == endpoint,
                )
            )
            if existing:
                existing.p256dh = p256dh
                existing.auth = auth
                existing.device_name = device_name
                existing.last_used = now_str
                existing.enabled = 1
                sub_id = existing.id
            else:
                new_sub = UserPushSubscription(
                    user_id=user_id,
                    endpoint=endpoint,
                    p256dh=p256dh,
                    auth=auth,
                    device_name=device_name,
                    created_at=now_str,
                    last_used=now_str,
                    enabled=1,
                )
                db.add(new_sub)
                db.flush()
                sub_id = new_sub.id

        return {"status": "subscribed", "subscription_id": sub_id, "endpoint": endpoint[:40] + "..."}

    def unsubscribe_user(self, user_id: int, endpoint: str):
        with Session.begin() as db:
            db.execute(
                update(UserPushSubscription)
                .where(UserPushSubscription.user_id == user_id, UserPushSubscription.endpoint == endpoint)
                .values(enabled=0)
            )

    # ========================================================
    # In-App Notifications
    # ========================================================
    def get_in_app_notifications(self, user_id: int, unread_only: bool = False, category: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        with Session() as db:
            q = select(InAppNotification).where(InAppNotification.user_id == user_id)
            if unread_only:
                q = q.where(InAppNotification.is_read == 0)
            if category and category.lower() != "all":
                q = q.where(InAppNotification.category == category.lower())
            q = q.order_by(InAppNotification.id.desc()).limit(limit)

            records = db.scalars(q).all()
            return [
                {
                    "id": r.id,
                    "alert_id": r.alert_id,
                    "title": r.title,
                    "message": r.message,
                    "severity": r.severity,
                    "category": r.category,
                    "location": r.location,
                    "source": r.source,
                    "is_read": bool(r.is_read),
                    "created_at": r.created_at,
                    "expires_at": r.expires_at,
                }
                for r in records
            ]

    def mark_as_read(self, user_id: int, notification_id: int):
        with Session.begin() as db:
            db.execute(
                update(InAppNotification)
                .where(InAppNotification.user_id == user_id, InAppNotification.id == notification_id)
                .values(is_read=1)
            )

    def mark_all_read(self, user_id: int):
        with Session.begin() as db:
            db.execute(
                update(InAppNotification)
                .where(InAppNotification.user_id == user_id)
                .values(is_read=1)
            )

    def delete_notification(self, user_id: int, notification_id: int):
        with Session.begin() as db:
            db.execute(
                delete(InAppNotification)
                .where(InAppNotification.user_id == user_id, InAppNotification.id == notification_id)
            )

    # ========================================================
    # FCM Dispatcher & Alert Fusion Delivery
    # ========================================================
    def send_fcm_notification(
        self,
        user_id: int,
        device_token: str,
        title: str,
        body: str,
        data: dict[str, Any] | None = None,
        alert_id: str = "test",
        device_id: int | None = None,
    ) -> dict[str, Any]:
        """Dispatches an FCM push to an Android device and logs delivery."""
        now_str = datetime.now(timezone.utc).isoformat()

        if self._firebase_status != "CONNECTED":
            # Record delivery attempt as NOT_CONFIGURED
            with Session.begin() as db:
                db.add(
                    PushDeliveryLog(
                        alert_id=alert_id,
                        user_id=user_id,
                        device_id=device_id,
                        platform="android",
                        status="NOT_CONFIGURED",
                        sent_at=now_str,
                        error_message="FIREBASE CONFIG REQUIRED: Firebase credentials not configured on backend.",
                    )
                )
            return {
                "status": "not_configured",
                "detail": "FIREBASE CONFIG REQUIRED: Place service account credentials in backend/data/firebase-service-account.json or set FIREBASE_SERVICE_ACCOUNT_JSON.",
            }

        data_payload = {k: str(v) for k, v in (data or {}).items()}
        data_payload["alert_id"] = alert_id
        data_payload["click_action"] = "OPEN_ALERT"

        msg = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data=data_payload,
            token=device_token,
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    channel_id="weathergpt_alerts",
                    priority="max",
                    default_sound=True,
                    click_action="OPEN_ALERT",
                ),
            ),
        )

        try:
            response = messaging.send(msg)
            with Session.begin() as db:
                db.add(
                    PushDeliveryLog(
                        alert_id=alert_id,
                        user_id=user_id,
                        device_id=device_id,
                        platform="android",
                        status="SENT",
                        sent_at=now_str,
                        error_message=None,
                    )
                )
            return {"status": "sent", "message_id": response}
        except messaging.UnregisteredError:
            log.warning("FCM token unregistered for user %s: disabling device", user_id)
            with Session.begin() as db:
                db.execute(
                    update(PushDevice)
                    .where(PushDevice.device_token == device_token)
                    .values(enabled=0)
                )
                db.add(
                    PushDeliveryLog(
                        alert_id=alert_id,
                        user_id=user_id,
                        device_id=device_id,
                        platform="android",
                        status="INVALID_TOKEN",
                        sent_at=now_str,
                        error_message="Device token is no longer registered with FCM",
                    )
                )
            return {"status": "invalid_token", "detail": "Token unregistered"}
        except Exception as ex:
            log.error("FCM push delivery failed: %s", ex)
            with Session.begin() as db:
                db.add(
                    PushDeliveryLog(
                        alert_id=alert_id,
                        user_id=user_id,
                        device_id=device_id,
                        platform="android",
                        status="FAILED",
                        sent_at=now_str,
                        error_message=str(ex)[:300],
                    )
                )
            return {"status": "failed", "detail": str(ex)}

    def deliver_alert_to_user(self, alert: dict[str, Any], user_id: int, primary_location_name: str = "") -> bool:
        """
        Deduplicates, records in-app notification, and dispatches Web Push + FCM Push
        to all registered active devices for user.
        Returns True if delivered, False if suppressed (duplicate/disabled).
        """
        alert_id = str(alert.get("id") or alert.get("identifier") or "alert")
        severity = str(alert.get("severity") or "WARNING").upper()
        headline = alert.get("headline") or alert.get("event") or alert.get("alert_type") or "Severe Weather Alert"
        instruction = alert.get("instruction") or alert.get("recommendation") or alert.get("description") or ""
        source = alert.get("source") or alert.get("data_source") or "IMD / NDMA Sachet"
        loc_desc = alert.get("location") or primary_location_name

        with Session() as db:
            # 1. Anti-spam / Deduplication: check if already notified with same or higher severity
            existing = db.scalar(
                select(InAppNotification).where(
                    InAppNotification.user_id == user_id,
                    InAppNotification.alert_id == alert_id,
                ).order_by(InAppNotification.id.desc())
            )
            if existing:
                rank = {"SEVERE": 3, "WARNING": 2, "WATCH": 1, "INFO": 0}
                if rank.get(severity, 0) <= rank.get(existing.severity, 0):
                    return False

        # 2. Save In-App Notification
        with Session.begin() as db:
            notif = InAppNotification(
                user_id=user_id,
                alert_id=alert_id,
                title=f"⚠ {headline}",
                message=f"{loc_desc}: {instruction[:240]}" if instruction else f"{loc_desc}: Active {headline}",
                severity=severity,
                category=self._categorize_alert(headline),
                location=loc_desc,
                source=source,
                is_read=0,
                created_at=datetime.now(timezone.utc).isoformat(),
                expires_at=alert.get("expires"),
            )
            db.add(notif)

        # 3. Web Push dispatch
        web_payload = json.dumps({
            "title": f"⚠ {headline}",
            "body": f"{loc_desc}: {instruction[:160]}" if instruction else f"{loc_desc}: Active {headline}",
            "icon": "/icons/icon-192.png",
            "badge": "/icons/badge-72.png",
            "tag": f"alert-{alert_id}",
            "data": {
                "alert_id": alert_id,
                "url": f"/alerts/{alert_id}",
                "severity": severity,
            },
        })
        self._send_web_push(user_id, web_payload)

        # 4. Native FCM Push dispatch to all Android Push Devices
        with Session() as db:
            devices = db.scalars(
                select(PushDevice).where(
                    PushDevice.user_id == user_id,
                    PushDevice.enabled == 1,
                    PushDevice.platform == "android",
                )
            ).all()

        for dev in devices:
            self.send_fcm_notification(
                user_id=user_id,
                device_token=dev.device_token,
                title=f"⚠ {headline}",
                body=f"{loc_desc}: {instruction[:160]}" if instruction else f"{loc_desc}: Active {headline}",
                data={
                    "alert_id": alert_id,
                    "url": f"/alerts/{alert_id}",
                    "severity": severity,
                    "source": source,
                },
                alert_id=alert_id,
                device_id=dev.id,
            )

        return True

    def _categorize_alert(self, title: str) -> str:
        lower = title.lower()
        if any(w in lower for w in ["cyclone", "flood", "tsunami", "earthquake", "landslide", "avalanche"]):
            return "disasters"
        if any(w in lower for w in ["rain", "wind", "thunderstorm", "lightning", "hail", "heat", "cold", "fog"]):
            return "weather"
        return "warnings"

    def _send_web_push(self, user_id: int, payload: str):
        if not self._private_key_pem or not self._public_key_b64:
            return

        with Session() as db:
            subs = db.scalars(
                select(UserPushSubscription).where(
                    UserPushSubscription.user_id == user_id,
                    UserPushSubscription.enabled == 1,
                )
            ).all()

        stale_endpoints = []
        for sub in subs:
            sub_info = {
                "endpoint": sub.endpoint,
                "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
            }
            try:
                webpush(
                    subscription_info=sub_info,
                    data=payload,
                    vapid_private_key=self._private_key_pem,
                    vapid_claims={"sub": settings.vapid_claim_email},
                    timeout=5,
                )
            except WebPushException as ex:
                log.info("WebPushException for user %s: %s", user_id, ex)
                if "410" in str(ex) or "404" in str(ex):
                    stale_endpoints.append(sub.endpoint)
            except Exception as e:
                log.debug("Push delivery failed: %s", e)

        if stale_endpoints:
            with Session.begin() as db:
                for ep in stale_endpoints:
                    db.execute(
                        update(UserPushSubscription)
                        .where(UserPushSubscription.endpoint == ep)
                        .values(enabled=0)
                    )

    # ========================================================
    # Admin / System Diagnostics
    # ========================================================
    def send_test_push(
        self,
        user_id: int,
        device_token: str | None = None,
        title: str = "WeatherGPT Test Notification",
        message: str = "This confirms Android push notifications are working.",
    ) -> dict[str, Any]:
        """Admin/user diagnostic test push dispatch."""
        with Session() as db:
            if device_token:
                dev = db.scalar(
                    select(PushDevice).where(
                        PushDevice.device_token == device_token,
                        PushDevice.user_id == user_id,
                    )
                )
            else:
                dev = db.scalar(
                    select(PushDevice)
                    .where(PushDevice.user_id == user_id, PushDevice.enabled == 1)
                    .order_by(PushDevice.id.desc())
                )

        if not dev and not device_token:
            return {
                "status": "error",
                "detail": "No registered push device found for user. Open the Android app or enable notifications in browser first.",
            }

        target_token = dev.device_token if dev else device_token
        target_dev_id = dev.id if dev else None

        res = self.send_fcm_notification(
            user_id=user_id,
            device_token=target_token,
            title=f"🚨 {title}",
            body=message,
            data={"type": "test_push", "timestamp": datetime.now(timezone.utc).isoformat()},
            alert_id="test-push",
            device_id=target_dev_id,
        )

        # Also send web push if device is web or user has active web subs
        self._send_web_push(
            user_id,
            json.dumps({
                "title": f"🚨 {title}",
                "body": message,
                "icon": "/icons/icon-192.png",
                "badge": "/icons/badge-72.png",
                "tag": "test-push",
                "data": {"url": "/notifications"},
            }),
        )

        return res

    def get_system_push_status(self) -> dict[str, Any]:
        """System status of Firebase, Web Push, and Push Devices."""
        today_prefix = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with Session() as db:
            total_devices = db.scalar(
                select(func.count(PushDevice.id)).where(PushDevice.enabled == 1)
            ) or 0
            android_devices = db.scalar(
                select(func.count(PushDevice.id)).where(
                    PushDevice.enabled == 1, PushDevice.platform == "android"
                )
            ) or 0
            web_subs = db.scalar(
                select(func.count(UserPushSubscription.id)).where(
                    UserPushSubscription.enabled == 1
                )
            ) or 0
            deliveries_today = db.scalar(
                select(func.count(PushDeliveryLog.id)).where(
                    PushDeliveryLog.sent_at.like(f"{today_prefix}%"),
                    PushDeliveryLog.status == "SENT",
                )
            ) or 0
            failed_today = db.scalar(
                select(func.count(PushDeliveryLog.id)).where(
                    PushDeliveryLog.sent_at.like(f"{today_prefix}%"),
                    PushDeliveryLog.status.in_(["FAILED", "INVALID_TOKEN"]),
                )
            ) or 0

        return {
            "firebase": self._firebase_status,
            "web_push": "CONNECTED" if (self._public_key_b64 and self._private_key_pem) else "NOT CONFIGURED",
            "vapid_public_key_available": bool(self._public_key_b64),
            "registered_devices_count": total_devices,
            "android_devices_count": android_devices,
            "web_subscribers_count": web_subs,
            "deliveries_today": deliveries_today,
            "failed_deliveries_today": failed_today,
            "fcm_config_instructions": (
                "To enable FCM: place google-services.json in mobile/android/app/ and "
                "place the Firebase service account JSON in backend/data/firebase-service-account.json "
                "or set FIREBASE_SERVICE_ACCOUNT_JSON environment variable."
            ) if self._firebase_status != "CONNECTED" else "FCM is fully connected.",
        }


notifications_service = NotificationService()
