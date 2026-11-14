from uuid import UUID
from src.domain.devices.entity import Device
from src.infrastructure.persistence.device_repository import DeviceRepository
from src.infrastructure.persistence.location_repository import LocationRepository


class ZoneNotFoundError(LookupError):
    """Raised when the target zone does not exist or does not belong to the given location."""


class DeviceNotFoundError(LookupError):
    """Raised when the target device does not exist."""


class ZoneAssignmentService:
    def __init__(
        self,
        device_repo: DeviceRepository,
        location_repo: LocationRepository,
    ) -> None:
        self._device_repo = device_repo
        self._location_repo = location_repo

    def assign_device_zone(
        self, device_id: UUID, zone_id: UUID | None
    ) -> Device:
        if zone_id is None:
            updated = self._device_repo.update_device_zone(
                device_id=device_id,
                zone_id=None,
                location_id=None,
            )
            if updated is None:
                raise DeviceNotFoundError(f"Device '{device_id}' not found.")
            return updated

        zone = self._location_repo.get_zone(zone_id)
        if zone is None or zone.location_id is None:
            raise ZoneNotFoundError(f"Zone '{zone_id}' not found.")

        updated = self._device_repo.update_device_zone(
            device_id=device_id,
            zone_id=zone.id,
            location_id=zone.location_id,
        )
        if updated is None:
            raise DeviceNotFoundError(f"Device '{device_id}' not found.")
        return updated

    def list_zone_devices(
        self, location_id: UUID, zone_id: UUID
    ) -> list[Device]:
        zone = self._location_repo.get_zone(zone_id)
        if zone is None or zone.location_id != location_id:
            raise ZoneNotFoundError(
                f"Zone '{zone_id}' not found in location '{location_id}'."
            )
        return self._device_repo.list_devices_by_zone(zone_id)