from collections.abc import Callable
from datetime import datetime
from typing import Any
from uuid import UUID

from src.application.actuators.service import build_decorated_actuator_port
from src.application.commands.dto import CommandLogResponseDto
from src.application.devices.actuator_state_service import ActuatorNotFoundError
from src.domain.actuators.context import ActuatorContext
from src.domain.actuators.ports import ActuatorPort, PolicyViolationError
from src.domain.commands.invoker import CommandInvoker, build_command
from src.infrastructure.persistence.actuator_state_repository import (
    ActuatorStateRepository,
)
from src.infrastructure.persistence.command_log_repository import (
    CommandLogEntry,
    CommandLogRepository,
)
from src.infrastructure.persistence.device_repository import DeviceRepository
from src.infrastructure.persistence.execution_log_repository import (
    ExecutionLogRepository,
)


class CommandService:
    def __init__(
        self,
        device_repo: DeviceRepository,
        state_repo: ActuatorStateRepository,
        execution_log_repo: ExecutionLogRepository,
        command_log_repo: CommandLogRepository,
        invoker: CommandInvoker | None = None,
        port_factory: Callable[[], ActuatorPort] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._device_repo = device_repo
        self._state_repo = state_repo
        self._execution_log_repo = execution_log_repo
        self._command_log_repo = command_log_repo
        self._invoker = invoker or CommandInvoker()
        self._port_factory = port_factory or (
            lambda: build_decorated_actuator_port(
                state_repo, execution_log_repo, clock=clock
            )
        )

    def execute_command(
        self,
        command_type: str,
        device_id: UUID,
        payload: dict[str, Any] | None = None,
    ) -> CommandLogResponseDto:
        # 1. Missing device or non-actuator -> 404 (ActuatorNotFoundError)
        device = self._device_repo.get_device(device_id)
        if device is None or device.role != "actuator":
            raise ActuatorNotFoundError(f"Actuator '{device_id}' not found.")

        # 2. Unknown command_type -> raises UnknownCommandError (400) and writes NO command_log row
        command = build_command(command_type, device_id, payload)

        # 3. Check allowed_commands for the saved state
        current_state_name = self._state_repo.get_state(device_id)
        ctx = ActuatorContext(device_id=device_id, initial_state=current_state_name)

        if command.command_type not in ctx.allowed_commands:
            err = (
                f"Command '{command.command_type}' is not allowed while actuator is in "
                f"state '{ctx.state}'. Allowed commands: {', '.join(ctx.allowed_commands) or 'none'}."
            )
            entry = self._command_log_repo.append_log(
                command_type=command.command_type,
                device_id=device_id,
                payload=command.payload,
                status="rejected",
                error_message=err,
            )
            return self._to_dto(entry)

        # 4. Execute via invoker against the Phase 9 decorated ActuatorPort stack
        port = self._port_factory()
        try:
            self._invoker.invoke(command, port)
        except PolicyViolationError as exc:
            # Decorator already wrote the failed row to actuator_execution_log; leave state unchanged
            entry = self._command_log_repo.append_log(
                command_type=command.command_type,
                device_id=device_id,
                payload=command.payload,
                status="failed",
                error_message=exc.message,
            )
            return self._to_dto(entry)

        # 5. Transition state via ActuatorContext only when target_state differs from current state
        if command.target_state and command.target_state != ctx.state:
            new_state = ctx.transition_to(command.target_state)
            self._state_repo.save_state(device_id, new_state)

        entry = self._command_log_repo.append_log(
            command_type=command.command_type,
            device_id=device_id,
            payload=command.payload,
            status="success",
            error_message=None,
        )
        return self._to_dto(entry)

    def list_commands(
        self, limit: int = 50, device_id: UUID | None = None
    ) -> list[CommandLogResponseDto]:
        entries = self._command_log_repo.list_recent(limit=limit, device_id=device_id)
        return [self._to_dto(e) for e in entries]

    @staticmethod
    def _to_dto(entry: CommandLogEntry) -> CommandLogResponseDto:
        return CommandLogResponseDto(
            id=entry.id,
            command_type=entry.command_type,
            device_id=entry.device_id,
            payload=entry.payload,
            status=entry.status,
            error_message=entry.error_message,
            created_at=entry.created_at,
        )