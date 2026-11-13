from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

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
from src.application.readings.dto import UpdateSamplingRequestDto
from src.domain.actuators.state import IllegalTransitionError
from src.infrastructure.persistence.actuator_state_repository import (
    ActuatorStateRepository,
)
from src.infrastructure.persistence.base import get_db
from src.infrastructure.persistence.device_repository import DeviceRepository
from src.infrastructure.persistence.location_repository import LocationRepository

router = APIRouter(prefix="/api/devices", tags=["devices"])


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
    return ActuatorStateService(
        device_repo=DeviceRepository(db),
        state_repo=ActuatorStateRepository(db),
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

    persisted_state = (
        state_repo.get_state(updated.id)
        if updated.role == "actuator" and updated.id is not None
        else None
    )
    return to_device_dto(updated, persisted_state=persisted_state)


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