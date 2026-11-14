from uuid import UUID
from src.domain.actuators.state import ActuatorState, get_actuator_state


class ActuatorContext:
    """Domain state context guarding lifecycle transitions for a single actuator device."""

    def __init__(self, device_id: UUID, initial_state: str = "idle") -> None:
        self._device_id = device_id
        self._state: ActuatorState = get_actuator_state(initial_state)

    @property
    def device_id(self) -> UUID:
        return self._device_id

    @property
    def state(self) -> str:
        return self._state.name

    @property
    def allowed_commands(self) -> list[str]:
        return list(self._state.allowed_commands)

    @property
    def allowed_targets(self) -> list[str]:
        return list(self._state.allowed_targets)

    def transition_to(self, target_state: str) -> str:
        self._state = self._state.transition_to(target_state)
        return self._state.name