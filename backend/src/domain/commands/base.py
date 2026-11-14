from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from src.domain.actuators.ports import ActuatorPort


class UnknownCommandError(ValueError):
    """Raised when an unrecognized command_type is requested."""


@dataclass(frozen=True)
class CommandResult:
    status: str  # "success" | "failed" | "rejected"
    error_message: str | None = None


class Command(ABC):
    command_type: str = ""
    target_state: str | None = None

    def __init__(self, device_id: UUID, payload: dict[str, Any] | None = None) -> None:
        self.device_id = device_id
        self.payload: dict[str, Any] = dict(payload or {})

    @abstractmethod
    def execute(self, port: ActuatorPort) -> None:
        """Execute this command against the provided ActuatorPort."""
        ...