from typing import Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.application.sensors.service import SensorService
from src.infrastructure.persistence.base import get_db
from src.infrastructure.persistence.device_repository import DeviceRepository

router = APIRouter(prefix="/api/sensors", tags=["sensors"])


class CreateSensorRequest(BaseModel):
    type: str
    display_name: str | None = None


class SensorResponse(BaseModel):
    id: UUID
    device_type: str
    display_name: str
    default_config: dict[str, Any]


def get_sensor_service(db: Session = Depends(get_db)) -> SensorService:
    repo = DeviceRepository(db)
    return SensorService(repo)


@router.get("", response_model=list[SensorResponse])
def list_sensors(service: SensorService = Depends(get_sensor_service)) -> list[SensorResponse]:
    sensors = service.list_sensors()
    return [
        SensorResponse(
            id=s.id,  # type: ignore[arg-type]
            device_type=s.device_type,
            display_name=s.display_name,
            default_config=s.default_config,
        )
        for s in sensors
    ]


@router.post("", response_model=SensorResponse, status_code=status.HTTP_201_CREATED)
def create_sensor(
    payload: CreateSensorRequest,
    service: SensorService = Depends(get_sensor_service),
) -> SensorResponse:
    try:
        sensor = service.create_sensor(
            sensor_type=payload.type,
            display_name=payload.display_name,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return SensorResponse(
        id=sensor.id,  # type: ignore[arg-type]
        device_type=sensor.device_type,
        display_name=sensor.display_name,
        default_config=sensor.default_config,
    )