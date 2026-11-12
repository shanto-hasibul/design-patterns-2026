from src.domain.devices.entity import Device
from src.domain.devices.family_factory import get_family_factory
from src.infrastructure.persistence.device_repository import DeviceRepository


class DeviceFamilyService:
    def __init__(self, repo: DeviceRepository) -> None:
        self._repo = repo

    def provision_family(self, family: str) -> list[Device]:
        factory = get_family_factory(family)
        device_set = factory.create_device_set()
        return self._repo.save_devices(device_set)

    def list_devices(
        self,
        family: str | None = None,
        role: str | None = None,
    ) -> list[Device]:
        return self._repo.list_devices(device_family=family, role=role)