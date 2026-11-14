from uuid import UUID

from src.domain.actuators.context import ActuatorContext
from src.domain.devices.entity import Device
from src.domain.events.bus import EventBus
from src.domain.events.events import ActuatorStateChanged
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
        event_bus: EventBus | None = None,
    ) -> None:
        self._device_repo = device_repo
        self._state_repo = state_repo
        self._event_bus = event_bus

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
        previous_state = ctx.state
        new_state = ctx.transition_to(target_state)
        self._state_repo.save_state(device.id, new_state)  # type: ignore[arg-type]

        if self._event_bus is not None and new_state != previous_state:
            self._event_bus.publish(
                ActuatorStateChanged(
                    device_id=device.id,
                    location_id=device.location_id,
                    zone_id=device.zone_id,
                    previous_state=previous_state,
                    new_state=new_state,
                )
            )
        return device, ctx