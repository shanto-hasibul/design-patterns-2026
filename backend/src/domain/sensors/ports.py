from abc import ABC, abstractmethod
from src.domain.devices.entity import Device
from src.domain.sensors.reading import Reading


class SensorAdapterError(ValueError):
    """Raised when a sensor adapter cannot read or translate a sensor payload."""


class SensorPort(ABC):
    @abstractmethod
    def read(self, device: Device) -> Reading:
        """Read from the sensor and return a normalized domain Reading."""
        ...