import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.application.alerts.subscribers import build_default_event_bus
from src.application.devices.actuator_state_service import (
    ActuatorNotFoundError,
    ActuatorStateService,
)
from src.application.devices.dto import (
    AssignZoneRequestDto,
    DeviceDto,
    TransitionActuatorRequestDto,
)
from src.application.devices.family_service import DeviceFamilyService
from src.application.devices.mappers import to_device_dto, to_device_dto_list
from src.application.locations.zone_assignment_service import (
    DeviceNotFoundError,
    ZoneAssignmentService,
    ZoneNotFoundError,
)
from src.application.readings.dto import ReadingDto, UpdateSamplingRequestDto
from src.application.readings.service import ReadingIngest
from src.domain.actuators.state import IllegalTransitionError
from src.domain.sensors.ports import SensorAdapterError
from src.infrastructure.adapters.sensors.mqtt import MqttSensorAdapter
from src.infrastructure.mqtt.subscriber import publish_retained_mqtt_config
from src.infrastructure.persistence.actuator_state_repository import (
    ActuatorStateRepository,
)
from src.infrastructure.persistence.alert_repository import AlertRepository
from src.infrastructure.persistence.base import get_db
from src.infrastructure.persistence.device_repository import DeviceRepository
from src.infrastructure.persistence.location_repository import LocationRepository
from src.infrastructure.persistence.reading_repository import ReadingRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/devices", tags=["devices"])


class DeviceSamplingConfigDto(BaseModel):
    sampling_interval_seconds: int
    tracking_enabled: bool


class DeviceHttpReadingRequestDto(BaseModel):
    value: float
    unit: str


def get_family_service(db: Session = Depends(get_db)) -> DeviceFamilyService:
    repo = DeviceRepository(db)
    return DeviceFamilyService(repo)


def get_assignment_service(
    db: Session = Depends(get_db),
) -> ZoneAssignmentService:
    return ZoneAssignmentService(
        device_repo=DeviceRepository(db),
        location_repo=LocationRepository(db),
    )


def get_device_repo(db: Session = Depends(get_db)) -> DeviceRepository:
    return DeviceRepository(db)


def get_state_repo(db: Session = Depends(get_db)) -> ActuatorStateRepository:
    return ActuatorStateRepository(db)


def get_actuator_state_service(
    db: Session = Depends(get_db),
) -> ActuatorStateService:
    bus = build_default_event_bus(AlertRepository(db))
    return ActuatorStateService(
        device_repo=DeviceRepository(db),
        state_repo=ActuatorStateRepository(db),
        event_bus=bus,
    )


def get_reading_ingest(db: Session = Depends(get_db)) -> ReadingIngest:
    bus = build_default_event_bus(AlertRepository(db))
    return ReadingIngest(
        device_repo=DeviceRepository(db),
        reading_repo=ReadingRepository(db),
        event_bus=bus,
    )


@router.get("", response_model=list[DeviceDto])
def list_devices(
    family: str | None = Query(default=None, description="Filter by device family (simulation or edge)"),
    role: str | None = Query(default=None, description="Filter by device role (sensor or actuator)"),
    service: DeviceFamilyService = Depends(get_family_service),
    state_repo: ActuatorStateRepository = Depends(get_state_repo),
) -> list[DeviceDto]:
    devices = service.list_devices(family=family, role=role)
    actuator_ids = [d.id for d in devices if d.role == "actuator" and d.id is not None]
    state_repo.seed_missing_states(actuator_ids)
    states = state_repo.get_states_for_devices(actuator_ids)
    return to_device_dto_list(devices, states_by_id=states)


@router.post("/provision", response_model=list[DeviceDto], status_code=status.HTTP_201_CREATED)
def provision_device_family(
    family: str = Query(..., description="Device family key to provision (simulation or edge)"),
    service: DeviceFamilyService = Depends(get_family_service),
    state_repo: ActuatorStateRepository = Depends(get_state_repo),
) -> list[DeviceDto]:
    try:
        created = service.provision_family(family)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    actuator_ids = [d.id for d in created if d.role == "actuator" and d.id is not None]
    states = state_repo.get_states_for_devices(actuator_ids)
    return to_device_dto_list(created, states_by_id=states)


@router.patch("/{device_id}/zone", response_model=DeviceDto)
def assign_device_to_zone(
    device_id: UUID,
    payload: AssignZoneRequestDto,
    service: ZoneAssignmentService = Depends(get_assignment_service),
    state_repo: ActuatorStateRepository = Depends(get_state_repo),
) -> DeviceDto:
    try:
        updated = service.assign_device_zone(device_id, payload.zone_id)
    except (DeviceNotFoundError, ZoneNotFoundError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    persisted_state = (
        state_repo.get_state(updated.id)
        if updated.role == "actuator" and updated.id is not None
        else None
    )
    return to_device_dto(updated, persisted_state=persisted_state)


@router.get("/{device_id}/sampling", response_model=DeviceSamplingConfigDto)
def get_device_sampling(
    device_id: UUID,
    repo: DeviceRepository = Depends(get_device_repo),
) -> DeviceSamplingConfigDto:
    """Device HTTP endpoint: ESP32 controllers GET their sampling interval and tracking flag."""
    device = repo.get_device(device_id)
    if device is None:
        logger.warning("Unknown device_id '%s' requested GET /sampling; dropping.", device_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device '{device_id}' not found.",
        )
    return DeviceSamplingConfigDto(
        sampling_interval_seconds=device.sampling_interval_seconds,
        tracking_enabled=device.tracking_enabled,
    )


@router.patch("/{device_id}/sampling", response_model=DeviceDto)
def update_device_sampling(
    device_id: UUID,
    payload: UpdateSamplingRequestDto,
    repo: DeviceRepository = Depends(get_device_repo),
    state_repo: ActuatorStateRepository = Depends(get_state_repo),
) -> DeviceDto:
    if payload.sampling_interval_seconds < 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="sampling_interval_seconds must be at least 5 seconds.",
        )

    updated = repo.update_device_sampling(
        device_id=device_id,
        sampling_interval_seconds=payload.sampling_interval_seconds,
        tracking_enabled=payload.tracking_enabled,
    )
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device '{device_id}' not found.",
        )

    protocol = str(updated.default_config.get("protocol", "")).lower()
    if protocol == "mqtt" and updated.id is not None:
        publish_retained_mqtt_config(
            device_id=updated.id,
            sampling_interval_seconds=updated.sampling_interval_seconds,
            tracking_enabled=updated.tracking_enabled,
        )

    persisted_state = (
        state_repo.get_state(updated.id)
        if updated.role == "actuator" and updated.id is not None
        else None
    )
    return to_device_dto(updated, persisted_state=persisted_state)


@router.post(
    "/{device_id}/readings",
    response_model=ReadingDto,
    status_code=status.HTTP_201_CREATED,
)
def ingest_device_http_reading(
    device_id: UUID,
    payload: DeviceHttpReadingRequestDto,
    repo: DeviceRepository = Depends(get_device_repo),
    ingest: ReadingIngest = Depends(get_reading_ingest),
) -> ReadingDto:
    """Device HTTP endpoint: translates {value, unit} with source='http' and delegates to ReadingIngest."""
    device = repo.get_device(device_id)
    if device is None or device.role != "sensor":
        logger.warning("Unknown sensor device_id '%s' posted to /readings; dropping.", device_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sensor device '{device_id}' not found.",
        )

    try:
        translated = MqttSensorAdapter.translate_payload(
            device,
            payload.model_dump(),
            source="http",
        )
    except SensorAdapterError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return ingest.record(device_id, translated_reading=translated)


@router.post("/{device_id}/transition", response_model=DeviceDto)
def transition_actuator_state(
    device_id: UUID,
    payload: TransitionActuatorRequestDto,
    service: ActuatorStateService = Depends(get_actuator_state_service),
) -> DeviceDto:
    try:
        device, ctx = service.transition(device_id, payload.target)
    except ActuatorNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except IllegalTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return to_device_dto(device, persisted_state=ctx.state)