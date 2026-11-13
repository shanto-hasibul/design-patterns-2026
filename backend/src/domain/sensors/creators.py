from abc import ABC, abstractmethod
from src.domain.sensors.entity import Sensor


class SensorCreator(ABC):
    @abstractmethod
    def create_sensor(self, display_name: str | None = None) -> Sensor:
        ...


class MoistureSensorCreator(SensorCreator):
    def create_sensor(self, display_name: str | None = None) -> Sensor:
        name = (
            display_name.strip()
            if display_name and display_name.strip()
            else "Soil Moisture Sensor"
        )
        return Sensor(
            id=None,
            device_type="moisture_sensor",
            display_name=name,
            default_config={
                "unit": "vwc",
                "protocol": "simulation",
                "sampling_interval_seconds": 300,
                "moisture_threshold": 0.35,
            },
            sampling_interval_seconds=300,
            tracking_enabled=True,
        )


class LightSensorCreator(SensorCreator):
    def create_sensor(self, display_name: str | None = None) -> Sensor:
        name = (
            display_name.strip()
            if display_name and display_name.strip()
            else "PAR Light Sensor"
        )
        return Sensor(
            id=None,
            device_type="light_sensor",
            display_name=name,
            default_config={
                "unit": "lux",
                "protocol": "simulation",
                "sampling_interval_seconds": 180,
                "daylight_lux_target": 12000,
            },
            sampling_interval_seconds=180,
            tracking_enabled=True,
        )


_CREATORS: dict[str, type[SensorCreator]] = {
    "moisture": MoistureSensorCreator,
    "moisture_sensor": MoistureSensorCreator,
    "light": LightSensorCreator,
    "light_sensor": LightSensorCreator,
}


def get_sensor_creator(kind: str) -> SensorCreator:
    normalized = kind.strip().lower() if kind else ""
    creator_cls = _CREATORS.get(normalized)
    if creator_cls is None:
        supported = ", ".join(sorted({"moisture", "light"}))
        raise ValueError(
            f"Unknown sensor type '{kind}'. Supported types: {supported}"
        )
    return creator_cls()