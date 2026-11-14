from uuid import UUID, uuid4
import pytest

from src.application.devices.actuator_state_service import (
    ActuatorNotFoundError,
    ActuatorStateService,
)
from src.domain.actuators.context import ActuatorContext
from src.domain.actuators.state import IllegalTransitionError
from src.domain.devices.entity import Device


def test_domain_legal_and_illegal_transitions() -> None:
    ctx = ActuatorContext(device_id=uuid4(), initial_state="idle")
    assert ctx.state == "idle"
    assert "start_pump" in ctx.allowed_commands

    # Legal: idle -> running
    assert ctx.transition_to("running") == "running"
    assert "stop_pump" in ctx.allowed_commands

    # Illegal: running -> maintenance (must stop to idle or fault to error first)
    with pytest.raises(IllegalTransitionError, match="Illegal actuator transition"):
        ctx.transition_to("maintenance")
    assert ctx.state == "running"

    # Legal: running -> error -> idle
    assert ctx.transition_to("error") == "error"
    assert "reset_error" in ctx.allowed_commands
    assert ctx.transition_to("idle") == "idle"


class _FakeActuatorDeviceRepo:
    def __init__(self, device: Device) -> None:
        self._device = device

    def get_device(self, device_id: UUID) -> Device | None:
        return self._device if self._device.id == device_id else None


class _FakeActuatorStateRepo:
    def __init__(self, initial_state: str = "idle") -> None:
        self.states: dict[UUID, str] = {}
        self.initial = initial_state

    def get_state(self, device_id: UUID) -> str:
        return self.states.get(device_id, self.initial)

    def save_state(self, device_id: UUID, state: str) -> str:
        self.states[device_id] = state
        return state


def test_service_persists_only_on_legal_transition() -> None:
    dev_id = uuid4()
    actuator = Device(
        id=dev_id,
        device_type="water_pump",
        role="actuator",
        device_family="simulation",
        display_name="Sim Pump",
    )
    dev_repo = _FakeActuatorDeviceRepo(actuator)
    state_repo = _FakeActuatorStateRepo("idle")
    service = ActuatorStateService(dev_repo, state_repo)  # type: ignore[arg-type]

    # Illegal transition: off -> running directly is forbidden
    service.transition(dev_id, "off")
    assert state_repo.get_state(dev_id) == "off"

    with pytest.raises(IllegalTransitionError):
        service.transition(dev_id, "running")

    # Persisted state remains 'off'
    assert state_repo.get_state(dev_id) == "off"

    # Legal recovery: off -> idle -> running
    service.transition(dev_id, "idle")
    service.transition(dev_id, "running")
    assert state_repo.get_state(dev_id) == "running"

    # Missing actuator raises ActuatorNotFoundError
    with pytest.raises(ActuatorNotFoundError):
        service.transition(uuid4(), "idle")