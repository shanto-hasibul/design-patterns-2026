from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from src.domain.actuators.ports import ActuatorPort


class SimulationActuatorAdapter(ActuatorPort):
    """Innermost simulation actuator adapter (in-memory record only; no GPIO)."""

    def __init__(self) -> None:
        self.history: list[dict[str, Any]] = []

    def apply(
        self,
        device_id: UUID,
        command: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        self.history.append(
            {
                "device_id": str(device_id),
                "command": command,
                "payload": dict(payload or {}),
                "source": "simulation",
                "applied_at": datetime.now(timezone.utc).isoformat(),
            }
        )