from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID


class ActuatorPort(ABC):
    @abstractmethod
    def apply(
        self,
        device_id: UUID,
        command: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Apply an actuator command and return an execution receipt."""
        ...