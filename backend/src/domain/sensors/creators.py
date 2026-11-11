from abc import ABC, abstractmethod
from src.domain.sensors.entity import Sensor


class SensorCreator(ABC):
    @abstractmethod
    def create_sensor(self, display_name: str | None = None) -> Sensor:
        ...


class MoistureSensorCreator(SensorCreator):
    def create_sensor(self, display_name: str | None = None) -> Sensor:
        name = display_name.strip() if display_name and display_name.strip() else "Soil moisture sensor"
        return Sensor(
            id=None,
            device_type="moisture_sensor",
            display_name=name,
            default_config={
                "unit": "vwc",
                "sampling_interval_seconds": 300,
                "moisture_threshold": 35.0,
            },
        )


class LightSensorCreator(SensorCreator):
    def create_sensor(self, display_name: str | None = None) -> Sensor:
        name = display_name.strip() if display_name and display_name.strip() else "Ambient light sensor"
        return Sensor(
            id=None,
            device_type="light_sensor",
            display_name=name,
            default_config={
                "unit": "lux",
                "sampling_interval_seconds": 120,
            },
        )


_CREATOR_REGISTRY: dict[str, type[SensorCreator]] = {
    "moisture": MoistureSensorCreator,
    "light": LightSensorCreator,
}


def get_creator(sensor_type: str) -> SensorCreator:
    normalized = sensor_type.strip().lower() if sensor_type else ""
    creator_cls = _CREATOR_REGISTRY.get(normalized)
    if creator_cls is None:
        supported = ", ".join(sorted(_CREATOR_REGISTRY.keys()))
        raise ValueError(f"Unknown sensor type '{sensor_type}'. Supported types: {supported}")
    return creator_cls()