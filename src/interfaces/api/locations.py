from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from src.application.devices.dto import DeviceDto
from src.application.devices.mappers import to_device_dto_list
from src.application.locations.config_service import LocationConfigService
from src.application.locations.dto import (
    CreateLocationConfigRequestDto,
    LocationConfigResponseDto,
    LocationSummaryDto,
    ZoneInputDto,
    ZoneResponseDto,
)
from src.application.locations.mappers import (
    to_location_config_response_dto,
    to_location_summary_dto,
    to_zone_response_dto,
)
from src.application.locations.zone_assignment_service import (
    ZoneAssignmentService,
    ZoneNotFoundError,
)
from src.domain.locations.errors import ConfigurationError
from src.infrastructure.persistence.base import get_db
from src.infrastructure.persistence.device_repository import DeviceRepository
from src.infrastructure.persistence.location_repository import LocationRepository

router = APIRouter(prefix="/api/locations", tags=["locations"])


def get_location_service(db: Session = Depends(get_db)) -> LocationConfigService:
    return LocationConfigService(LocationRepository(db))


def get_zone_assignment_service(
    db: Session = Depends(get_db),
) -> ZoneAssignmentService:
    return ZoneAssignmentService(
        device_repo=DeviceRepository(db),
        location_repo=LocationRepository(db),
    )


@router.get("", response_model=list[LocationSummaryDto])
def list_locations(
    service: LocationConfigService = Depends(get_location_service),
) -> list[LocationSummaryDto]:
    locations = service.list_locations()
    return [to_location_summary_dto(loc) for loc in locations]


@router.post(
    "/config",
    response_model=LocationConfigResponseDto,
    status_code=status.HTTP_201_CREATED,
)
def create_location_config(
    payload: CreateLocationConfigRequestDto,
    service: LocationConfigService = Depends(get_location_service),
) -> LocationConfigResponseDto:
    try:
        saved = service.create_config(payload)
    except ConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return to_location_config_response_dto(saved)


@router.get(
    "/{location_id}/config",
    response_model=LocationConfigResponseDto,
)
def get_location_config(
    location_id: UUID,
    service: LocationConfigService = Depends(get_location_service),
) -> LocationConfigResponseDto:
    config = service.get_config(location_id)
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Location '{location_id}' not found.",
        )
    return to_location_config_response_dto(config)


@router.delete(
    "/{location_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_location(
    location_id: UUID,
    service: LocationConfigService = Depends(get_location_service),
) -> Response:
    deleted = service.delete_location(location_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Location '{location_id}' not found.",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{location_id}/zones",
    response_model=ZoneResponseDto,
    status_code=status.HTTP_201_CREATED,
)
def add_zone_to_location(
    location_id: UUID,
    payload: ZoneInputDto,
    service: LocationConfigService = Depends(get_location_service),
) -> ZoneResponseDto:
    try:
        created_zone = service.add_zone(
            location_id=location_id,
            name=payload.name,
            moisture_threshold_low=payload.moisture_threshold_low,
            moisture_threshold_high=payload.moisture_threshold_high,
            schedule=payload.schedule,
        )
    except ConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if created_zone is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Location '{location_id}' not found.",
        )
    return to_zone_response_dto(created_zone)


@router.patch(
    "/{location_id}/zones/{zone_id}",
    response_model=ZoneResponseDto,
)
def update_zone_on_location(
    location_id: UUID,
    zone_id: UUID,
    payload: ZoneInputDto,
    service: LocationConfigService = Depends(get_location_service),
) -> ZoneResponseDto:
    try:
        updated_zone = service.update_zone(
            location_id=location_id,
            zone_id=zone_id,
            name=payload.name,
            moisture_threshold_low=payload.moisture_threshold_low,
            moisture_threshold_high=payload.moisture_threshold_high,
            schedule=payload.schedule,
        )
    except ConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if updated_zone is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Zone '{zone_id}' in location '{location_id}' not found.",
        )
    return to_zone_response_dto(updated_zone)


@router.delete(
    "/{location_id}/zones/{zone_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_zone_from_location(
    location_id: UUID,
    zone_id: UUID,
    service: LocationConfigService = Depends(get_location_service),
) -> Response:
    try:
        deleted = service.delete_zone(location_id, zone_id)
    except ConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Zone '{zone_id}' in location '{location_id}' not found.",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{location_id}/zones/{zone_id}/devices",
    response_model=list[DeviceDto],
)
def list_zone_devices(
    location_id: UUID,
    zone_id: UUID,
    service: ZoneAssignmentService = Depends(get_zone_assignment_service),
) -> list[DeviceDto]:
    try:
        devices = service.list_zone_devices(location_id, zone_id)
    except ZoneNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return to_device_dto_list(devices)