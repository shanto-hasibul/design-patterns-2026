from datetime import datetime, timezone

from src.application.readings.dto import ReadingDto
from src.application.readings.service import ReadingIngest
from src.domain.devices.entity import Device
from src.infrastructure.adapters.sensors.simulation import SimulationSensorAdapter
from src.infrastructure.persistence.device_repository import DeviceRepository
from src.infrastructure.persistence.reading_repository import ReadingRepository


class SimulationSampler:
    """Periodically samples enabled simulation sensors whose sampling interval has elapsed."""

    def __init__(
        self,
        device_repo: DeviceRepository,
        reading_repo: ReadingRepository,
        ingest: ReadingIngest | None = None,
    ) -> None:
        self._device_repo = device_repo
        self._reading_repo = reading_repo
        self._ingest = ingest or ReadingIngest(device_repo, reading_repo)
        self._sim_adapter = SimulationSensorAdapter()

    def run_once(self, now: datetime | None = None) -> list[ReadingDto]:
        current_time = now or datetime.now(timezone.utc)
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)

        sensors = self._device_repo.list_devices(role="sensor")
        recorded: list[ReadingDto] = []

        for sensor in sensors:
            if sensor.id is None:
                continue
            if not sensor.tracking_enabled:
                continue
            if not self._is_simulation_sensor(sensor):
                continue

            latest = self._reading_repo.get_latest_reading(sensor.id)
            if latest is not None:
                last_ts = latest.recorded_at
                if last_ts.tzinfo is None:
                    last_ts = last_ts.replace(tzinfo=timezone.utc)
                elapsed = (current_time - last_ts).total_seconds()
                if elapsed < sensor.sampling_interval_seconds:
                    continue

            generated = self._sim_adapter.read(sensor)
            timed_reading = type(generated)(
                device_id=generated.device_id,
                value=generated.value,
                unit=generated.unit,
                source="simulation",
                recorded_at=current_time,
            )
            dto = self._ingest.record(sensor.id, translated_reading=timed_reading)
            recorded.append(dto)

        return recorded

    @staticmethod
    def _is_simulation_sensor(device: Device) -> bool:
        cfg = device.default_config or {}
        if cfg.get("vendor_stub") is True or str(cfg.get("adapter", "")).lower() == "vendor":
            return False
        protocol = str(cfg.get("protocol", "simulation")).strip().lower()
        return protocol in ("simulation", "mock_random", "mock_sine_wave", "")