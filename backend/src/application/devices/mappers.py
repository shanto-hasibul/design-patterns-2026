from src.application.devices.dto import DeviceDto
from src.domain.devices.entity import Device


def to_device_dto(device: Device) -> DeviceDto:
    if device.id is None:
        raise ValueError("Cannot map an unpersisted Device without an id to DeviceDto")
    return DeviceDto(
        id=device.id,
        device_type=device.device_type,
        role=device.role,
        device_family=device.device_family,
        display_name=device.display_name,
        default_config=dict(device.default_config),
    )


def to_device_dto_list(devices: list[Device]) -> list[DeviceDto]:
    return [to_device_dto(d) for d in devices]