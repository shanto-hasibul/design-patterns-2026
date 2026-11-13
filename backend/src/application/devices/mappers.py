from src.application.devices.dto import DeviceDto
from src.domain.actuators.context import ActuatorContext
from src.domain.devices.entity import Device


def to_device_dto(
    device: Device,
    persisted_state: str | None = None,
) -> DeviceDto:
    if device.id is None:
        raise ValueError("Cannot map an unpersisted Device without an id to DeviceDto")

    state_str: str | None = None
    commands: list[str] = []
    targets: list[str] = []

    if device.role == "actuator":
        ctx = ActuatorContext(
            device_id=device.id,
            initial_state=persisted_state or "idle",
        )
        state_str = ctx.state
        commands = ctx.allowed_commands
        targets = ctx.allowed_targets

    return DeviceDto(
        id=device.id,
        device_type=device.device_type,
        role=device.role,
        device_family=device.device_family,
        display_name=device.display_name,
        default_config=dict(device.default_config),
        zone_id=device.zone_id,
        location_id=device.location_id,
        sampling_interval_seconds=device.sampling_interval_seconds,
        tracking_enabled=device.tracking_enabled,
        state=state_str,
        allowed_commands=commands,
        allowed_targets=targets,
    )


def to_device_dto_list(
    devices: list[Device],
    states_by_id: dict | None = None,
) -> list[DeviceDto]:
    state_map = states_by_id or {}
    return [
        to_device_dto(d, persisted_state=state_map.get(d.id))
        for d in devices
    ]