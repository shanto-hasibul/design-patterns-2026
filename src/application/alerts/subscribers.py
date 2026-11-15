import json
import logging
import socket
import threading
from urllib.parse import urlparse
from uuid import UUID

from src.application.alerts.subscribers import build_default_event_bus
from src.application.readings.service import ReadingIngest
from src.infrastructure.adapters.sensors.mqtt import MqttSensorAdapter
from src.infrastructure.persistence.alert_repository import AlertRepository
from src.infrastructure.persistence.base import SessionLocal
from src.infrastructure.persistence.device_repository import DeviceRepository
from src.infrastructure.persistence.reading_repository import ReadingRepository
from src.infrastructure.settings import settings

logger = logging.getLogger(__name__)


def _parse_broker_host_port(broker_url: str, default_port: int = 1883) -> tuple[str, int]:
    if "://" not in broker_url:
        broker_url = f"mqtt://{broker_url}"
    parsed = urlparse(broker_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or default_port
    return host, port


def publish_retained_mqtt_config(
    device_id: UUID,
    sampling_interval_seconds: int,
    tracking_enabled: bool,
    broker_url: str | None = None,
) -> bool:
    """Publishes retained config JSON to greenhouse/devices/{device_id}/config when broker is configured."""
    url = broker_url if broker_url is not None else settings.mqtt_broker_url
    if not url:
        return False

    topic = f"greenhouse/devices/{device_id}/config"
    payload = json.dumps(
        {
            "sampling_interval_seconds": sampling_interval_seconds,
            "tracking_enabled": tracking_enabled,
        }
    ).encode("utf-8")

    try:
        import paho.mqtt.publish as mqtt_publish  # type: ignore[import-untyped]

        host, port = _parse_broker_host_port(url, settings.mqtt_broker_port)
        mqtt_publish.single(
            topic=topic,
            payload=payload,
            qos=1,
            retain=True,
            hostname=host,
            port=port,
        )
        return True
    except Exception as exc:
        logger.warning("MQTT retained config publish skipped/failed for %s: %s", device_id, exc)
        return False


def ingest_mqtt_reading_message(topic: str, raw_payload: bytes | str) -> bool:
    """Handles a message on greenhouse/devices/{device_id}/reading using Phase 5 translator + ReadingIngest."""
    parts = topic.strip("/").split("/")
    if len(parts) != 4 or parts[0] != "greenhouse" or parts[1] != "devices" or parts[3] != "reading":
        logger.warning("Ignoring unexpected MQTT topic: %s", topic)
        return False

    try:
        device_id = UUID(parts[2])
    except ValueError:
        logger.warning("Unknown/invalid device_id in MQTT topic '%s'; dropping.", topic)
        return False

    try:
        text_data = raw_payload.decode("utf-8") if isinstance(raw_payload, bytes) else raw_payload
        body = json.loads(text_data)
    except Exception as exc:
        logger.warning("Invalid JSON on MQTT topic '%s': %s; dropping.", topic, exc)
        return False

    with SessionLocal() as session:
        device_repo = DeviceRepository(session)
        device = device_repo.get_device(device_id)
        if device is None or device.role != "sensor":
            logger.warning("Unknown sensor device_id '%s' from MQTT; dropping.", device_id)
            return False

        try:
            translated = MqttSensorAdapter.translate_payload(
                device, body, source="mqtt"
            )
            bus = build_default_event_bus(AlertRepository(session))
            ingest = ReadingIngest(
                device_repo=device_repo,
                reading_repo=ReadingRepository(session),
                event_bus=bus,
            )
            ingest.record(device_id, translated_reading=translated)
            return True
        except Exception as exc:
            logger.warning("Failed to ingest MQTT reading for '%s': %s", device_id, exc)
            return False


class OptionalMqttSubscriber:
    """Background MQTT subscriber that starts ONLY when MQTT_BROKER_URL is configured."""

    def __init__(self, broker_url: str | None = None, default_port: int = 1883) -> None:
        self._broker_url = broker_url
        self._default_port = default_port
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def is_enabled(self) -> bool:
        return bool(self._broker_url and self._broker_url.strip())

    def start(self) -> None:
        if not self.is_enabled:
            return
        self._thread = threading.Thread(
            target=self._run_loop, name="mqtt-subscriber", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def _run_loop(self) -> None:
        assert self._broker_url is not None
        host, port = _parse_broker_host_port(self._broker_url, self._default_port)
        try:
            import paho.mqtt.client as mqtt  # type: ignore[import-untyped]

            client = mqtt.Client()

            def on_connect(cli, _userdata, _flags, rc):
                if rc == 0:
                    cli.subscribe("greenhouse/devices/+/reading")

            def on_message(_cli, _userdata, msg):
                ingest_mqtt_reading_message(msg.topic, msg.payload)

            client.on_connect = on_connect
            client.on_message = on_message
            client.connect(host, port, keepalive=60)
            while not self._stop_event.is_set():
                client.loop(timeout=1.0)
            client.disconnect()
        except (ImportError, OSError, socket.error) as exc:
            logger.info("MQTT subscriber inactive (%s:%s): %s", host, port, exc)