from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID


class PolicyViolationError(ValueError):
    """Raised when an actuator decorator policy (such as maxRunTime) blocks execution."""

    def __init__(self, policy_name: str, message: str) -> None:
        self.policy_name = policy_name
        self.message = message
        super().__init__(message)


class ActuatorPort(ABC):
    @abstractmethod
    def apply(
        self,
        device_id: UUID,
        command: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        """Apply an actuator command through the port (or decorator chain)."""
        ...