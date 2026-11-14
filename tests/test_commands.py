from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import pytest

from src.application.commands.service import CommandService
from src.domain.commands.base import UnknownCommandError
from src.domain.devices.entity import Device
from src.infrastructure.adapters.actuators.logging_decorator import (
    LoggingActuatorDecorator,
)
from src.infrastructure.adapters.actuators.max_runtime_decorator import (
    MaxRuntimeActuatorDecorator,
)
from src.infrastructure.adapters.actuators.simulation import (
    SimulationActuatorAdapter,
)
from src.infrastructure.persistence.command_log_repository import CommandLogEntry
from src.infrastructure.persistence.execution_log_repository import (
    ExecutionLogEntry,
)


class _FakeCmdDeviceRepo:
    def __init__(self, device: Device) -> None:
        self._device = device

    def get_device(self, device_id: UUID) -> Device | None:
        return self._device if self._device.id == device_id else None


class _FakeCmdStateRepo:
    def __init__(self, initial: str = "idle") -> None:
        self.state = initial
        self.updated_at = datetime.now(timezone.utc)

    def get_state(self, device_id: UUID) -> str:
        return self.state

    def get_state_record(self, device_id: UUID) -> tuple[str, datetime | None]:
        return self.state, self.updated_at

    def save_state(self, device_id: UUID, state: str) -> str:
        self.state = state
        self.updated_at = datetime.now(timezone.utc)
        return state


class _FakeExecLogRepo:
    def __init__(self) -> None:
        self.entries: list[ExecutionLogEntry] = []

    def append_log(
        self,
        device_id: UUID,
        success: bool,
        policy_applied: list[str],
        message: str | None = None,
    ) -> ExecutionLogEntry:
        entry = ExecutionLogEntry(
            id=uuid4(),
            device_id=device_id,
            success=success,
            policy_applied=list(policy_applied),
            message=message,
            created_at=datetime.now(timezone.utc),
        )
        self.entries.append(entry)
        return entry


class _FakeCommandLogRepo:
    def __init__(self) -> None:
        self.entries: list[CommandLogEntry] = []

    def append_log(
        self,
        command_type: str,
        device_id: UUID,
        payload: dict[str, Any],
        status: str,
        error_message: str | None = None,
    ) -> CommandLogEntry:
        entry = CommandLogEntry(
            id=uuid4(),
            command_type=command_type,
            device_id=device_id,
            payload=dict(payload),
            status=status,
            error_message=error_message,
            created_at=datetime.now(timezone.utc),
        )
        self.entries.insert(0, entry)
        return entry

    def list_recent(
        self, limit: int = 50, device_id: UUID | None = None
    ) -> list[CommandLogEntry]:
        return self.entries[:limit]


def _build_test_service(initial_state: str = "idle"):
    dev_id = uuid4()
    pump = Device(
        id=dev_id,
        device_type="water_pump",
        role="actuator",
        device_family="simulation",
        display_name="Test Pump",
    )
    dev_repo = _FakeCmdDeviceRepo(pump)
    state_repo = _FakeCmdStateRepo(initial=initial_state)
    exec_repo = _FakeExecLogRepo()
    cmd_repo = _FakeCommandLogRepo()
    inner = SimulationActuatorAdapter()

    def port_factory():
        guarded = MaxRuntimeActuatorDecorator(
            inner=inner,
            state_lookup=state_repo.get_state_record,
        )
        return LoggingActuatorDecorator(
            inner=guarded,
            log_writer=exec_repo.append_log,
        )

    service = CommandService(
        device_repo=dev_repo,  # type: ignore[arg-type]
        state_repo=state_repo,  # type: ignore[arg-type]
        execution_log_repo=exec_repo,  # type: ignore[arg-type]
        command_log_repo=cmd_repo,  # type: ignore[arg-type]
        port_factory=port_factory,
    )
    return service, dev_id, state_repo, exec_repo, cmd_repo, inner


def test_rejected_command_leaves_state_unchanged_and_writes_log() -> None:
    # Actuator starts in 'idle'; stop_pump is illegal while 'idle'
    service, dev_id, state_repo, exec_repo, cmd_repo, inner = _build_test_service("idle")

    result = service.execute_command("stop_pump", dev_id, {})

    assert result.status == "rejected"
    assert result.error_message is not None
    assert state_repo.state == "idle"
    assert len(inner.history) == 0
    assert len(exec_repo.entries) == 0
    assert len(cmd_repo.entries) == 1
    assert cmd_repo.entries[0].status == "rejected"


def test_successful_start_and_stop_pump_updates_state_and_logs() -> None:
    service, dev_id, state_repo, exec_repo, cmd_repo, inner = _build_test_service("idle")

    start_res = service.execute_command("start_pump", dev_id, {"duration": 15})
    assert start_res.status == "success"
    assert state_repo.state == "running"
    assert len(inner.history) == 1
    assert len(exec_repo.entries) == 1
    assert len(cmd_repo.entries) == 1

    stop_res = service.execute_command("stop_pump", dev_id, {})
    assert stop_res.status == "success"
    assert state_repo.state == "idle"
    assert len(cmd_repo.entries) == 2


def test_unknown_command_raises_without_writing_command_log() -> None:
    service, dev_id, _state_repo, _exec_repo, cmd_repo, _inner = _build_test_service("idle")

    with pytest.raises(UnknownCommandError):
        service.execute_command("launch_missiles", dev_id, {})

    assert len(cmd_repo.entries) == 0