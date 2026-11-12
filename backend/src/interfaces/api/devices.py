from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.application.devices.dto import DeviceDto
from src.application.devices.family_service import DeviceFamilyService
from src.application.devices.mappers import to_device_dto_list
from src.infrastructure.persistence.base import get_db
from src.infrastructure.persistence.device_repository import DeviceRepository

router = APIRouter(prefix="/api/devices", tags=["devices"])


def get_family_service(db: Session = Depends(get_db)) -> DeviceFamilyService:
    repo = DeviceRepository(db)
    return DeviceFamilyService(repo)


@router.get("", response_model=list[DeviceDto])
def list_devices(
    family: str | None = Query(default=None, description="Filter by device family (simulation or edge)"),
    role: str | None = Query(default=None, description="Filter by device role (sensor or actuator)"),
    service: DeviceFamilyService = Depends(get_family_service),
) -> list[DeviceDto]:
    devices = service.list_devices(family=family, role=role)
    return to_device_dto_list(devices)


@router.post("/provision", response_model=list[DeviceDto], status_code=status.HTTP_201_CREATED)
def provision_device_family(
    family: str = Query(..., description="Device family key to provision (simulation or edge)"),
    service: DeviceFamilyService = Depends(get_family_service),
) -> list[DeviceDto]:
    try:
        created = service.provision_family(family)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return to_device_dto_list(created)