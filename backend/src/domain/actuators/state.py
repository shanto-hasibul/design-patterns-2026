from abc import ABC, abstractmethod


class IllegalTransitionError(ValueError):
    """Raised when an actuator attempts a state transition not permitted from its current state."""


VALID_STATES: frozenset[str] = frozenset(
    {"off", "idle", "running", "error", "maintenance"}
)


class ActuatorState(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def allowed_targets(self) -> tuple[str, ...]:
        ...

    @property
    @abstractmethod
    def allowed_commands(self) -> list[str]:
        ...

    def can_transition_to(self, target: str) -> bool:
        return target in self.allowed_targets

    def transition_to(self, target: str) -> "ActuatorState":
        normalized = target.strip().lower() if target else ""
        if normalized not in VALID_STATES:
            raise IllegalTransitionError(
                f"Unknown actuator state '{target}'. Valid states: {', '.join(sorted(VALID_STATES))}."
            )
        if not self.can_transition_to(normalized):
            allowed = ", ".join(self.allowed_targets) or "none"
            raise IllegalTransitionError(
                f"Illegal actuator transition from '{self.name}' to '{normalized}'. "
                f"Allowed targets from '{self.name}': {allowed}."
            )
        return get_actuator_state(normalized)


class OffState(ActuatorState):
    @property
    def name(self) -> str:
        return "off"

    @property
    def allowed_targets(self) -> tuple[str, ...]:
        return ("idle", "maintenance", "error")

    @property
    def allowed_commands(self) -> list[str]:
        return ["power_on", "enter_maintenance"]


class IdleState(ActuatorState):
    @property
    def name(self) -> str:
        return "idle"

    @property
    def allowed_targets(self) -> tuple[str, ...]:
        return ("running", "off", "maintenance", "error")

    @property
    def allowed_commands(self) -> list[str]:
        return ["start_pump", "turn_on_light", "power_off", "enter_maintenance"]


class RunningState(ActuatorState):
    @property
    def name(self) -> str:
        return "running"

    @property
    def allowed_targets(self) -> tuple[str, ...]:
        return ("idle", "error")

    @property
    def allowed_commands(self) -> list[str]:
        return ["stop_pump", "turn_off_light"]


class ErrorState(ActuatorState):
    @property
    def name(self) -> str:
        return "error"

    @property
    def allowed_targets(self) -> tuple[str, ...]:
        return ("idle", "maintenance", "off")

    @property
    def allowed_commands(self) -> list[str]:
        return ["reset_error", "enter_maintenance", "power_off"]


class MaintenanceState(ActuatorState):
    @property
    def name(self) -> str:
        return "maintenance"

    @property
    def allowed_targets(self) -> tuple[str, ...]:
        return ("idle", "off", "error")

    @property
    def allowed_commands(self) -> list[str]:
        return ["complete_maintenance", "power_off"]


_STATE_INSTANCES: dict[str, ActuatorState] = {
    "off": OffState(),
    "idle": IdleState(),
    "running": RunningState(),
    "error": ErrorState(),
    "maintenance": MaintenanceState(),
}


def get_actuator_state(state_name: str) -> ActuatorState:
    normalized = state_name.strip().lower() if state_name else "idle"
    state_obj = _STATE_INSTANCES.get(normalized)
    if state_obj is None:
        raise IllegalTransitionError(
            f"Unknown actuator state '{state_name}'. Valid states: {', '.join(sorted(VALID_STATES))}."
        )
    return state_obj