from uuid import UUID

from src.domain.actuators.context import ActuatorContext
from src.domain.devices.entity import Device
from src.infrastructure.persistence.actuator_state_repository import (
    ActuatorStateRepository,
)
from src.infrastructure.persistence.device_repository import DeviceRepository


class ActuatorNotFoundError(LookupError):
    """Raised when the requested actuator device does not exist or is not an actuator."""


class ActuatorStateService:
    def __init__(
        self,
        device_repo: DeviceRepository,
        state_repo: ActuatorStateRepository,
    ) -> None:
        self._device_repo = device_repo
        self._state_repo = state_repo

    def get_context(self, device_id: UUID) -> tuple[Device, ActuatorContext]:
        device = self._device_repo.get_device(device_id)
        if device is None or device.role != "actuator" or device.id is None:
            raise ActuatorNotFoundError(f"Actuator '{device_id}' not found.")

        current_state = self._state_repo.get_state(device.id)
        return device, ActuatorContext(device_id=device.id, initial_state=current_state)

    def transition(
        self, device_id: UUID, target_state: str
    ) -> tuple[Device, ActuatorContext]:
        device, ctx = self.get_context(device_id)
        # Domain guard validates edge and raises IllegalTransitionError if forbidden
        new_state = ctx.transition_to(target_state)
        self._state_repo.save_state(device.id, new_state)  # type: ignore[arg-type]
        return device, ctx