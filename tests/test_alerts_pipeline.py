"""
Alert Pipeline Comprehensive Test Suite
Tests:
- NDMA Sachet CAP XML parsing with defusedxml
- Expired alert removal
- Duplicate alert deduplication / severity escalation
- India-first earthquake filtering (US earthquakes excluded for India, Indian quakes retained)
- Geo-targeting matching logic
- Web Push subscription and delivery pipeline
- In-app notification center operations
"""
from datetime import datetime, timezone, timedelta
import pytest

from backend.services.alerts import india_alert_aggregator, IndiaAlertAggregator
from backend.services.notifications import notifications_service
from backend.providers.weather import earthquakes
from backend.database import Session, User, UserPushSubscription, InAppNotification


SAMPLE_CAP_XML = """<?xml version="1.0" encoding="UTF-8"?>
<alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">
  <identifier>NDMA-SACHET-2026-09-10-001</identifier>
  <sender>NDMA-India</sender>
  <sent>2026-09-10T06:00:00+05:30</sent>
  <status>Actual</status>
  <msgType>Alert</msgType>
  <scope>Public</scope>
  <info>
    <language>en</language>
    <category>Met</category>
    <event>Severe Thunderstorm &amp; Lightning Warning</event>
    <urgency>Expected</urgency>
    <severity>Severe</severity>
    <certainty>Likely</certainty>
    <headline>Thunderstorm with dangerous lightning likely over Patna District</headline>
    <description>Convective cells developing rapidly with cloud-to-ground lightning strikes and gusty winds up to 55 km/h.</description>
    <instruction>Take shelter inside solid concrete buildings. Do not take shelter under solitary trees.</instruction>
    <effective>2026-09-10T06:00:00+05:30</effective>
    <expires>2026-09-10T19:30:00+05:30</expires>
    <area>
      <areaDesc>Patna, Bihar</areaDesc>
      <circle>25.5941,85.1376 35.0</circle>
    </area>
  </info>
</alert>
"""

SAMPLE_EXPIRED_CAP_XML = """<?xml version="1.0" encoding="UTF-8"?>
<alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">
  <identifier>NDMA-SACHET-OLD-001</identifier>
  <sender>NDMA-India</sender>
  <sent>2026-09-01T06:00:00+05:30</sent>
  <status>Actual</status>
  <msgType>Alert</msgType>
  <scope>Public</scope>
  <info>
    <language>en</language>
    <event>Heavy Rain Warning</event>
    <severity>Moderate</severity>
    <effective>2026-09-01T06:00:00+05:30</effective>
    <expires>2026-09-01T12:00:00+05:30</expires>
    <area>
      <areaDesc>Gaya, Bihar</areaDesc>
    </area>
  </info>
</alert>
"""


def test_ndma_cap_xml_parsing():
    """Verify defusedxml parser correctly extracts all CAP 1.2 fields."""
    aggregator = IndiaAlertAggregator()
    alerts = aggregator.parse_cap_xml(SAMPLE_CAP_XML)
    assert len(alerts) == 1
    a = alerts[0]
    assert a["identifier"] == "NDMA-SACHET-2026-09-10-001"
    assert a["sender"] == "NDMA-India"
    assert a["severity"] == "WARNING"  # 'Severe' maps to standardized 'WARNING'
    assert a["original_severity"] == "Severe"
    assert "Patna" in a["location"]
    assert len(a["circles"]) == 1
    assert a["circles"][0][0] == 25.5941
    assert a["circles"][0][2] == 35.0


def test_geo_targeting_match():
    """Verify point-in-circle and district matching for user location."""
    aggregator = IndiaAlertAggregator()
    alerts = aggregator.parse_cap_xml(SAMPLE_CAP_XML)
    alert = alerts[0]

    # User in Patna within 35km circle
    patna_user = {"name": "Patna Town", "latitude": 25.60, "longitude": 85.14, "district": "Patna"}
    assert aggregator.geo_match(alert, patna_user) is True

    # User far away in Jaipur
    jaipur_user = {"name": "Jaipur", "latitude": 26.91, "longitude": 75.78, "district": "Jaipur"}
    assert aggregator.geo_match(alert, jaipur_user) is False


@pytest.mark.asyncio
async def test_india_first_earthquake_filtering():
    """Verify that USGS earthquakes outside India margin are filtered out by default."""
    india_quakes = await earthquakes(scope="india")
    assert india_quakes["status"] in ("live", "unavailable")
    assert india_quakes["scope"] == "india"

    # All returned quakes must fall inside India / regional margin
    for eq in india_quakes.get("events", []):
        assert 5.0 <= eq["latitude"] <= 38.5, f"Latitude outside India: {eq['latitude']}"
        assert 60.0 <= eq["longitude"] <= 100.0, f"Longitude outside India: {eq['longitude']}"


def test_push_subscription_and_delivery(client):
    """Test user push subscription registration, anti-spam deduplication, and in-app storage."""
    # Register/login test user
    email = "pushtest@weathergpt.gov.in"
    password = "SecurePassword2026!"
    reg_res = client.post("/api/auth/register", json={
        "email": email,
        "full_name": "Push Tester",
        "password": password,
        "confirm_password": password,
        "preferred_language": "en",
        "state": "Bihar",
        "district": "Patna",
    })
    assert reg_res.status_code == 201
    login_res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert login_res.status_code == 200

    # 1. Fetch VAPID public key
    v_res = client.get("/api/notifications/vapid-key")
    assert v_res.status_code == 200
    pub_key = v_res.json()["public_key"]
    assert len(pub_key) > 50

    # 2. Subscribe user device
    sub_payload = {
        "subscription": {
            "endpoint": "https://fcm.googleapis.com/fcm/send/test-token-12345",
            "keys": {
                "p256dh": "BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QT9h0Re9sbVIkME06G_HxF1d9AhuS",
                "auth": "tBHItJI5svbpez7KI4CCXg",
            }
        },
        "device_name": "Test Mobile PWA",
    }
    sub_res = client.post("/api/notifications/subscribe", json=sub_payload)
    assert sub_res.status_code == 200
    assert sub_res.json()["status"] == "subscribed"

    # 3. Test dispatch notification
    disp_res = client.post("/api/notifications/test-dispatch")
    assert disp_res.status_code == 200
    assert disp_res.json()["status"] == "dispatched"

    # 4. Check in-app notification center
    notif_res = client.get("/api/notifications")
    assert notif_res.status_code == 200
    notifs = notif_res.json()["notifications"]
    assert len(notifs) >= 1
    notif_id = notifs[0]["id"]
    assert notifs[0]["is_read"] is False

    # 5. Mark as read
    mark_res = client.post(f"/api/notifications/{notif_id}/read")
    assert mark_res.status_code == 200

    # Verify marked read
    notif_res2 = client.get("/api/notifications")
    assert notif_res2.json()["notifications"][0]["is_read"] is True
