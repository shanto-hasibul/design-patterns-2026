from collections.abc import Callable
from uuid import UUID

from src.application.readings.dto import ReadingDto
from src.domain.devices.entity import Device
from src.domain.events.bus import EventBus
from src.domain.events.events import ReadingCreated
from src.domain.sensors.ports import SensorPort
from src.domain.sensors.reading import Reading
from src.infrastructure.adapters.sensors import select_sensor_adapter
from src.infrastructure.persistence.device_repository import DeviceRepository
from src.infrastructure.persistence.reading_repository import ReadingRepository


class SensorDeviceNotFoundError(LookupError):
    """Raised when a sensor device does not exist."""


class ReadingIngest:
    """Single writer for sensor_readings: manual read, simulation sampler, and translated MQTT readings."""

    def __init__(
        self,
        device_repo: DeviceRepository,
        reading_repo: ReadingRepository,
        adapter_selector: Callable[[Device], SensorPort] = select_sensor_adapter,
        event_bus: EventBus | None = None,
    ) -> None:
        self._device_repo = device_repo
        self._reading_repo = reading_repo
        self._adapter_selector = adapter_selector
        self._event_bus = event_bus

    def record(
        self,
        device_id: UUID,
        translated_reading: Reading | None = None,
    ) -> ReadingDto:
        device = self._device_repo.get_device(device_id)
        if device is None or device.role != "sensor":
            raise SensorDeviceNotFoundError(f"Sensor device '{device_id}' not found.")

        if translated_reading is not None:
            reading_to_save = Reading(
                device_id=device.id,  # type: ignore[arg-type]
                value=translated_reading.value,
                unit=translated_reading.unit,
                source=translated_reading.source,
                recorded_at=translated_reading.recorded_at,
            )
        else:
            adapter = self._adapter_selector(device)
            reading_to_save = adapter.read(device)

        saved = self._reading_repo.save_reading(reading_to_save)

        # Publish reading.created ONLY while tracking_enabled is True
        if self._event_bus is not None and device.tracking_enabled:
            self._event_bus.publish(
                ReadingCreated(
                    device_id=device.id,
                    location_id=device.location_id,
                    zone_id=device.zone_id,
                    value=saved.value,
                    unit=saved.unit,
                    source=saved.source,
                    recorded_at=saved.recorded_at,
                )
            )

        return self.to_dto(saved)

    def list_readings(self, device_id: UUID, limit: int = 20) -> list[ReadingDto]:
        device = self._device_repo.get_device(device_id)
        if device is None or device.role != "sensor":
            raise SensorDeviceNotFoundError(f"Sensor device '{device_id}' not found.")

        rows = self._reading_repo.list_readings_for_device(device_id, limit=limit)
        return [self.to_dto(r) for r in rows]

    @staticmethod
    def to_dto(reading: Reading) -> ReadingDto:
        return ReadingDto(
            device_id=reading.device_id,
            value=reading.value,
            unit=reading.unit,
            source=reading.source,
            recorded_at=reading.recorded_at,
        )