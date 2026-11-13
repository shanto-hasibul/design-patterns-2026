import random
from datetime import datetime, timezone

from src.domain.devices.entity import Device
from src.domain.sensors.ports import SensorAdapterError, SensorPort
from src.domain.sensors.reading import Reading


class SimulationSensorAdapter(SensorPort):
    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng or random.Random()

    def read(self, device: Device) -> Reading:
        if device.id is None:
            raise SensorAdapterError("Cannot read from an unpersisted device without an id.")

        dtype = device.device_type.lower()
        if "moisture" in dtype:
            val = round(self._rng.uniform(0.2, 0.6), 4)
            unit = str(device.default_config.get("unit") or "vwc")
        elif "light" in dtype:
            val = round(self._rng.uniform(200.0, 2000.0), 2)
            unit = str(device.default_config.get("unit") or "lux")
        else:
            val = round(self._rng.uniform(10.0, 50.0), 2)
            unit = str(device.default_config.get("unit") or "raw")

        return Reading(
            device_id=device.id,
            value=float(val),
            unit=unit,
            source="simulation",
            recorded_at=datetime.now(timezone.utc),
        )