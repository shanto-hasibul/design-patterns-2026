from collections.abc import Callable
from datetime import datetime
from typing import Any
from uuid import UUID

from src.application.actuators.dto import ActuatorExecutionDto
from src.application.devices.actuator_state_service import ActuatorNotFoundError
from src.domain.actuators.ports import ActuatorPort, PolicyViolationError
from src.infrastructure.adapters.actuators.logging_decorator import (
    LoggingActuatorDecorator,
)
from src.infrastructure.adapters.actuators.max_runtime_decorator import (
    MaxRuntimeActuatorDecorator,
)
from src.infrastructure.adapters.actuators.simulation import (
    SimulationActuatorAdapter,
)
from src.infrastructure.persistence.actuator_state_repository import (
    ActuatorStateRepository,
)
from src.infrastructure.persistence.device_repository import DeviceRepository
from src.infrastructure.persistence.execution_log_repository import (
    ExecutionLogEntry,
    ExecutionLogRepository,
)


def build_decorated_actuator_port(
    state_repo: ActuatorStateRepository,
    log_repo: ExecutionLogRepository,
    clock: Callable[[], datetime] | None = None,
) -> LoggingActuatorDecorator:
    """Composes Logging -> MaxRuntime -> SimulationActuatorAdapter."""
    inner_adapter = SimulationActuatorAdapter()
    runtime_guarded: ActuatorPort = MaxRuntimeActuatorDecorator(
        inner=inner_adapter,
        state_lookup=state_repo.get_state_record,
        clock=clock,
    )
    return LoggingActuatorDecorator(
        inner=runtime_guarded,
        log_writer=log_repo.append_log,
    )


class ActuatorExecutionService:
    def __init__(
        self,
        device_repo: DeviceRepository,
        state_repo: ActuatorStateRepository,
        log_repo: ExecutionLogRepository,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._device_repo = device_repo
        self._log_repo = log_repo
        self._port = build_decorated_actuator_port(state_repo, log_repo, clock=clock)

    def apply_command(
        self,
        device_id: UUID,
        command: str,
        payload: dict[str, Any] | None = None,
    ) -> ActuatorExecutionDto:
        device = self._device_repo.get_device(device_id)
        if device is None or device.role != "actuator":
            raise ActuatorNotFoundError(f"Actuator '{device_id}' not found.")

        try:
            self._port.apply(device_id, command, payload or {})
        except PolicyViolationError:
            # Logging decorator has already persisted the blocked execution row
            pass

        entry: ExecutionLogEntry | None = self._port.last_logged
        if entry is None:
            recent = self._log_repo.list_recent(limit=1, device_id=device_id)
            entry = recent[0]

        return self._to_dto(entry)

    def list_executions(
        self, limit: int = 20, device_id: UUID | None = None
    ) -> list[ActuatorExecutionDto]:
        entries = self._log_repo.list_recent(limit=limit, device_id=device_id)
        return [self._to_dto(e) for e in entries]

    @staticmethod
    def _to_dto(entry: ExecutionLogEntry) -> ActuatorExecutionDto:
        return ActuatorExecutionDto(
            id=entry.id,
            device_id=entry.device_id,
            success=entry.success,
            policy_applied=entry.policy_applied,
            message=entry.message,
            created_at=entry.created_at,
        )