from typing import Any
from uuid import UUID

from src.domain.actuators.ports import ActuatorPort
from src.domain.commands.base import Command


class SetLightLevelCommand(Command):
    command_type = "set_light_level"

    def __init__(self, device_id: UUID, payload: dict[str, Any] | None = None) -> None:
        normalized = dict(payload or {})
        if "level" not in normalized:
            normalized["level"] = 1
        super().__init__(device_id, normalized)

    @property
    def target_state(self) -> str:  # type: ignore[override]
        level = self.payload.get("level", 1)
        try:
            numeric = float(level)
        except (TypeError, ValueError):
            numeric = 1.0
        return "idle" if numeric <= 0 else "running"

    def execute(self, port: ActuatorPort) -> None:
        port.apply(self.device_id, self.command_type, self.payload)