from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from src.domain.actuators.ports import ActuatorPort


class SimulationActuatorAdapter(ActuatorPort):
    """In-memory simulation actuator adapter (no physical GPIO). Ready for Phase 9 Decorator wrapping."""

    def __init__(self) -> None:
        self.history: list[dict[str, Any]] = []

    def apply(
        self,
        device_id: UUID,
        command: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        record = {
            "device_id": str(device_id),
            "command": command,
            "payload": dict(payload or {}),
            "source": "simulation",
            "applied_at": datetime.now(timezone.utc).isoformat(),
        }
        self.history.append(record)
        return record