from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from src.application.readings.service import ReadingIngest
from src.application.realtime.connection_manager import DashboardConnectionManager
from src.application.realtime.ws_subscriber import WebSocketBroadcastSubscriber
from src.domain.devices.entity import Device
from src.domain.events.bus import EventBus
from src.domain.events.events import ActuatorStateChanged, ThresholdCrossed
from src.domain.sensors.reading import Reading
from src.interfaces.api.devices import (
    DeviceHttpReadingRequestDto,
    get_device_sampling,
    ingest_device_http_reading,
)


class _FakeHttpDeviceRepo:
    def __init__(self, device: Device) -> None:
        self._device = device

    def get_device(self, device_id: UUID) -> Device | None:
        return self._device if self._device.id == device_id else None


class _FakeHttpReadingRepo:
    def __init__(self) -> None:
        self.rows: list[Reading] = []

    def save_reading(self, reading: Reading) -> Reading:
        saved = Reading(
            id=uuid4(),
            device_id=reading.device_id,
            value=reading.value,
            unit=reading.unit,
            source=reading.source,
            recorded_at=reading.recorded_at,
        )
        self.rows.append(saved)
        return saved


def test_device_http_sampling_and_reading_ingest_with_ws_fanout() -> None:
    dev_id = uuid4()
    zone_id = uuid4()
    loc_id = uuid4()
    esp_sensor = Device(
        id=dev_id,
        device_type="moisture_sensor",
        role="sensor",
        device_family="edge",
        display_name="ESP32 Bed Sensor",
        default_config={"protocol": "http", "unit": "vwc"},
        zone_id=zone_id,
        location_id=loc_id,
        sampling_interval_seconds=15,
        tracking_enabled=True,
    )

    dev_repo = _FakeHttpDeviceRepo(esp_sensor)
    reading_repo = _FakeHttpReadingRepo()
    ws_manager = DashboardConnectionManager()
    ws_sub = WebSocketBroadcastSubscriber(manager=ws_manager)

    bus = EventBus()
    bus.subscribe(ws_sub)

    ingest = ReadingIngest(
        device_repo=dev_repo,  # type: ignore[arg-type]
        reading_repo=reading_repo,  # type: ignore[arg-type]
        event_bus=bus,
    )

    # 1. GET /api/devices/{id}/sampling
    sampling = get_device_sampling(dev_id, repo=dev_repo)  # type: ignore[arg-type]
    assert sampling.sampling_interval_seconds == 15
    assert sampling.tracking_enabled is True

    # Unknown device -> 404
    with pytest.raises(HTTPException) as exc_info:
        get_device_sampling(uuid4(), repo=dev_repo)  # type: ignore[arg-type]
    assert exc_info.value.status_code == 404

    # 2. POST /api/devices/{id}/readings -> stores source='http' and broadcasts reading.created
    created_dto = ingest_device_http_reading(
        dev_id,
        DeviceHttpReadingRequestDto(value=0.38, unit="vwc"),
        repo=dev_repo,  # type: ignore[arg-type]
        ingest=ingest,
    )
    assert created_dto.source == "http"
    assert created_dto.value == pytest.approx(0.38)
    assert len(reading_repo.rows) == 1
    assert reading_repo.rows[0].source == "http"

    assert len(ws_sub.sent_envelopes) == 1
    assert ws_sub.sent_envelopes[0]["type"] == "reading.created"
    assert ws_sub.sent_envelopes[0]["payload"]["zone_id"] == str(zone_id)


def test_ws_subscriber_formats_state_and_alert_envelopes() -> None:
    ws_sub = WebSocketBroadcastSubscriber(manager=DashboardConnectionManager())
    dev_id = uuid4()
    zone_id = uuid4()

    ws_sub.handle(
        ActuatorStateChanged(
            device_id=dev_id,
            zone_id=zone_id,
            previous_state="idle",
            new_state="running",
        )
    )
    ws_sub.handle(
        ThresholdCrossed(
            device_id=dev_id,
            zone_id=zone_id,
            moisture=0.19,
            threshold_low=0.30,
            message="Low moisture",
        )
    )

    assert [e["type"] for e in ws_sub.sent_envelopes] == [
        "actuator.state_changed",
        "alert.created",
    ]
    assert ws_sub.sent_envelopes[1]["payload"]["zone_id"] == str(zone_id)