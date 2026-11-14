from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest

from src.application.readings.sampler import SimulationSampler
from src.application.readings.service import ReadingIngest
from src.domain.devices.entity import Device
from src.domain.sensors.reading import Reading
from src.infrastructure.adapters.actuators.simulation import SimulationActuatorAdapter
from src.infrastructure.adapters.sensors.mqtt import MqttSensorAdapter
from src.infrastructure.adapters.sensors.simulation import SimulationSensorAdapter
from src.infrastructure.adapters.sensors.vendor_stub import (
    VendorRawPacket,
    VendorStubSensorAdapter,
)


def _make_sensor_device(
    device_type: str = "moisture_sensor",
    protocol: str = "simulation",
    interval: int = 60,
    tracking: bool = True,
) -> Device:
    return Device(
        id=uuid4(),
        device_type=device_type,
        role="sensor",
        device_family="simulation" if protocol == "simulation" else "edge",
        display_name="Test Sensor",
        default_config={
            "unit": "vwc" if "moisture" in device_type else "lux",
            "protocol": protocol,
        },
        sampling_interval_seconds=interval,
        tracking_enabled=tracking,
    )


def test_simulation_adapter_stays_in_range_and_sets_source() -> None:
    adapter = SimulationSensorAdapter()
    moisture_dev = _make_sensor_device("moisture_sensor")
    light_dev = _make_sensor_device("light_sensor")

    m_reading = adapter.read(moisture_dev)
    assert m_reading.source == "simulation"
    assert m_reading.unit == "vwc"
    assert 0.2 <= m_reading.value <= 0.6

    l_reading = adapter.read(light_dev)
    assert l_reading.source == "simulation"
    assert l_reading.unit == "lux"
    assert 200.0 <= l_reading.value <= 2000.0


def test_vendor_stub_adapter_translates_proprietary_packet() -> None:
    dev = _make_sensor_device("moisture_sensor")
    raw_packet = VendorRawPacket(
        channel_code="CH_01",
        raw_millivolts=450,
        scale_factor=0.001,
        uom_code="PCT_VWC",
        epoch_ms=1760000000000,
    )
    adapter = VendorStubSensorAdapter(raw_payload=raw_packet)
    reading = adapter.read(dev)

    assert reading.device_id == dev.id
    assert reading.value == pytest.approx(0.45)
    assert reading.unit == "vwc"
    assert reading.source == "vendor"


def test_mqtt_adapter_translates_payload_dict_without_broker() -> None:
    dev = _make_sensor_device("moisture_sensor", protocol="mqtt")
    adapter = MqttSensorAdapter()
    reading = adapter.translate_payload(dev.id, {"value": 0.41, "unit": "vwc"})  # type: ignore[arg-type]

    assert reading.device_id == dev.id
    assert reading.value == pytest.approx(0.41)
    assert reading.unit == "vwc"
    assert reading.source == "mqtt"


def test_simulation_actuator_adapter_records_command() -> None:
    actuator = SimulationActuatorAdapter()
    dev_id = uuid4()
    receipt = actuator.apply(dev_id, "turn_on", {"duration_seconds": 30})

    assert receipt["device_id"] == str(dev_id)
    assert receipt["command"] == "turn_on"
    assert receipt["source"] == "simulation"
    assert len(actuator.history) == 1


class _FakeDeviceRepo:
    def __init__(self, devices: list[Device]) -> None:
        self._devices = {d.id: d for d in devices if d.id is not None}

    def get_device(self, device_id: UUID) -> Device | None:
        return self._devices.get(device_id)

    def list_devices(
        self,
        device_family: str | None = None,
        role: str | None = None,
    ) -> list[Device]:
        return [
            d
            for d in self._devices.values()
            if (role is None or d.role == role)
            and (device_family is None or d.device_family == device_family)
        ]


class _FakeReadingRepo:
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

    def get_latest_reading(self, device_id: UUID) -> Reading | None:
        matching = [r for r in self.rows if r.device_id == device_id]
        if not matching:
            return None
        matching.sort(key=lambda r: r.recorded_at, reverse=True)
        return matching[0]


def test_simulation_sampler_respects_interval_tracking_and_protocol() -> None:
    sim_enabled = _make_sensor_device("moisture_sensor", protocol="simulation", interval=60, tracking=True)
    sim_disabled = _make_sensor_device("moisture_sensor", protocol="simulation", interval=60, tracking=False)
    mqtt_enabled = _make_sensor_device("moisture_sensor", protocol="mqtt", interval=60, tracking=True)

    device_repo = _FakeDeviceRepo([sim_enabled, sim_disabled, mqtt_enabled])
    reading_repo = _FakeReadingRepo()
    ingest = ReadingIngest(device_repo, reading_repo)  # type: ignore[arg-type]
    sampler = SimulationSampler(device_repo, reading_repo, ingest=ingest)  # type: ignore[arg-type]

    t0 = datetime(2026, 10, 6, 12, 0, 0, tzinfo=timezone.utc)

    # First tick: only sim_enabled is sampled
    first_batch = sampler.run_once(t0)
    assert len(first_batch) == 1
    assert first_batch[0].device_id == sim_enabled.id

    # Second tick 30s later (inside 60s interval): skipped
    second_batch = sampler.run_once(t0 + timedelta(seconds=30))
    assert len(second_batch) == 0

    # Third tick 61s later (interval elapsed): sampled again
    third_batch = sampler.run_once(t0 + timedelta(seconds=61))
    assert len(third_batch) == 1
    assert len(reading_repo.rows) == 2