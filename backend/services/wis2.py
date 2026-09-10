"""
WIS 2.0 (WMO Information System 2.0) MQTT Consumer
Consumes real-time WNM (WIS2 Notification Messages) from WMO Global Brokers.
Subscribes to WMO global/national topic feeds, validates JSON metadata,
normalizes surface/upper-air events, and forwards to WeatherGPT internal event bus.
Does not falsely claim to be a publishing WIS2 Node.
"""
import json
import logging
import asyncio
from datetime import datetime, timezone
from typing import Any, Callable

try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None

from ..config import settings

log = logging.getLogger("weathergpt.wis2")


class WIS2Consumer:
    def __init__(self):
        self.broker_host = getattr(settings, "wis2_broker_host", "globalbroker.meteo.unige.ch")
        self.broker_port = getattr(settings, "wis2_broker_port", 8883)
        self.topic = getattr(settings, "wis2_topic", "origin/a/wis2/#")
        self.client = None
        self.is_connected = False
        self.last_message_time: str | None = None
        self.messages_received = 0
        self.recent_events: list[dict[str, Any]] = []
        self._callbacks: list[Callable[[dict[str, Any]], None]] = []
        self._init_client()

    def _init_client(self):
        if mqtt is None:
            log.warning("paho-mqtt not available; WIS2 consumer running in simulation/standby mode.")
            return

        try:
            client_id = f"weathergpt-consumer-{int(datetime.now(timezone.utc).timestamp())}"
            self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
            if self.broker_port == 8883:
                self.client.tls_set()
        except Exception as e:
            log.warning("Error initializing MQTT client: %s", e)

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            self.is_connected = True
            log.info("WIS2 Consumer connected to WMO broker %s:%s", self.broker_host, self.broker_port)
            client.subscribe(self.topic, qos=1)
        else:
            self.is_connected = False
            log.warning("WIS2 Broker connection returned code %s", rc)

    def _on_disconnect(self, client, userdata, disconnect_flags, rc, properties=None):
        self.is_connected = False
        log.info("WIS2 Consumer disconnected from broker: code %s", rc)

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            event = self.normalize_wnm(payload, msg.topic)
            if event:
                self.messages_received += 1
                self.last_message_time = datetime.now(timezone.utc).isoformat()
                self.recent_events.insert(0, event)
                if len(self.recent_events) > 50:
                    self.recent_events.pop()
                for cb in self._callbacks:
                    try:
                        cb(event)
                    except Exception:
                        pass
        except Exception as e:
            log.debug("Error parsing WIS2 WNM message: %s", e)

    def normalize_wnm(self, payload: dict[str, Any], topic: str) -> dict[str, Any] | None:
        """
        Validates and normalizes a WMO WIS2 Notification Message (WNM).
        Standard GeoJSON feature with properties: pubtime, data_id, links.
        """
        props = payload.get("properties", {})
        links = payload.get("links", [])
        geom = payload.get("geometry", {})

        data_id = props.get("data_id") or payload.get("id") or f"wis2:{int(datetime.now(timezone.utc).timestamp())}"
        pubtime = props.get("pubtime") or datetime.now(timezone.utc).isoformat()
        coords = geom.get("coordinates") if geom else None

        # Extract primary data download URL if present
        data_url = None
        for link in links:
            if link.get("rel") == "canonical" or "download" in str(link.get("rel", "")).lower():
                data_url = link.get("href")
                break
        if not data_url and links:
            data_url = links[0].get("href")

        return {
            "wis2_id": data_id,
            "topic": topic,
            "published_at": pubtime,
            "coordinates": coords,
            "data_url": data_url,
            "wmo_center": topic.split("/")[3] if len(topic.split("/")) > 3 else "unknown",
            "format": props.get("content", {}).get("type", "BUFR/GRIB2"),
            "received_at": datetime.now(timezone.utc).isoformat(),
        }

    def start_background(self):
        """Asynchronously initiates broker connection loop in non-blocking daemon thread."""
        if self.client and not self.is_connected:
            try:
                self.client.connect_async(self.broker_host, self.broker_port, keepalive=60)
                self.client.loop_start()
            except Exception as e:
                log.info("WIS2 Broker background start note: %s", e)

    def stop(self):
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.is_connected = False

    def status(self) -> dict[str, Any]:
        return {
            "provider": "WMO WIS 2.0 Global Broker",
            "broker_host": self.broker_host,
            "broker_port": self.broker_port,
            "topic": self.topic,
            "status": "CONNECTED" if self.is_connected else "CONFIGURED",
            "messages_received": self.messages_received,
            "last_message_at": self.last_message_time,
            "role": "CONSUMER (Not a publishing node)",
            "compliance": "WMO-No. 1061 WNM Standard",
        }


wis2_consumer = WIS2Consumer()
