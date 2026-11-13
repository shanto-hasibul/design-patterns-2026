from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.application.readings.dto import ReadingDto
from src.application.readings.service import ReadingIngest, SensorDeviceNotFoundError
from src.application.sensors.service import SensorService
from src.domain.sensors.entity import Sensor
from src.domain.sensors.ports import SensorAdapterError
from src.infrastructure.persistence.base import get_db
from src.infrastructure.persistence.device_repository import DeviceRepository
from src.infrastructure.persistence.reading_repository import ReadingRepository

router = APIRouter(prefix="/api/sensors", tags=["sensors"])


class CreateSensorRequest(BaseModel):
    type: str
    display_name: str | None = None


class SensorDto(BaseModel):
    id: UUID
    device_type: str
    display_name: str
    default_config: dict[str, Any]
    sampling_interval_seconds: int = 300
    tracking_enabled: bool = True
    zone_id: UUID | None = None
    location_id: UUID | None = None

    @classmethod
    def from_domain(cls, sensor: Sensor) -> "SensorDto":
        if sensor.id is None:
            raise ValueError("Persisted sensor must have an id")
        return cls(
            id=sensor.id,
            device_type=sensor.device_type,
            display_name=sensor.display_name,
            default_config=sensor.default_config,
            sampling_interval_seconds=sensor.sampling_interval_seconds,
            tracking_enabled=sensor.tracking_enabled,
            zone_id=sensor.zone_id,
            location_id=sensor.location_id,
        )


def get_sensor_service(db: Session = Depends(get_db)) -> SensorService:
    repo = DeviceRepository(db)
    return SensorService(repo)


def get_reading_ingest(db: Session = Depends(get_db)) -> ReadingIngest:
    return ReadingIngest(
        device_repo=DeviceRepository(db),
        reading_repo=ReadingRepository(db),
    )


@router.get("", response_model=list[SensorDto])
def list_sensors(
    service: SensorService = Depends(get_sensor_service),
) -> list[SensorDto]:
    sensors = service.list_sensors()
    return [SensorDto.from_domain(s) for s in sensors]


@router.post("", response_model=SensorDto, status_code=status.HTTP_201_CREATED)
def create_sensor(
    payload: CreateSensorRequest,
    service: SensorService = Depends(get_sensor_service),
) -> SensorDto:
    try:
        created = service.register_sensor(payload.type, payload.display_name)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return SensorDto.from_domain(created)


@router.post(
    "/{sensor_id}/read",
    response_model=ReadingDto,
    status_code=status.HTTP_201_CREATED,
)
def trigger_sensor_read(
    sensor_id: UUID,
    ingest: ReadingIngest = Depends(get_reading_ingest),
) -> ReadingDto:
    try:
        return ingest.record(sensor_id)
    except SensorDeviceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except SensorAdapterError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/{sensor_id}/readings",
    response_model=list[ReadingDto],
)
def get_sensor_readings(
    sensor_id: UUID,
    limit: int = Query(default=20, ge=1, le=500),
    ingest: ReadingIngest = Depends(get_reading_ingest),
) -> list[ReadingDto]:
    try:
        return ingest.list_readings(sensor_id, limit=limit)
    except SensorDeviceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc