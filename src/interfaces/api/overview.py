from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.application.automation.service import AutomationService, LocationNotFoundError
from src.application.overview.dto import LocationOverviewDto
from src.application.overview.facade import LocationOverviewFacade
from src.infrastructure.persistence.automation_repository import AutomationRepository
from src.infrastructure.persistence.base import get_db
from src.infrastructure.persistence.device_repository import DeviceRepository
from src.infrastructure.persistence.location_repository import LocationRepository
from src.infrastructure.persistence.reading_repository import ReadingRepository

router = APIRouter(prefix="/api/locations", tags=["overview"])


def get_overview_facade(db: Session = Depends(get_db)) -> LocationOverviewFacade:
    automation_repo = AutomationRepository(db)
    return LocationOverviewFacade(
        location_repo=LocationRepository(db),
        device_repo=DeviceRepository(db),
        reading_repo=ReadingRepository(db),
        automation_repo=automation_repo,
        automation_service=AutomationService(automation_repo),
    )


@router.get("/{location_id}/overview", response_model=LocationOverviewDto)
def get_location_overview(
    location_id: UUID,
    facade: LocationOverviewFacade = Depends(get_overview_facade),
) -> LocationOverviewDto:
    try:
        return facade.get_overview(location_id)
    except LocationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc