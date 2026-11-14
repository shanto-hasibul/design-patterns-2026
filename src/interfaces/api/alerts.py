from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.application.alerts.dto import AlertDto
from src.infrastructure.persistence.alert_repository import (
    AlertEntry,
    AlertRepository,
)
from src.infrastructure.persistence.base import get_db

router = APIRouter(prefix="/api", tags=["alerts"])


def get_alert_repo(db: Session = Depends(get_db)) -> AlertRepository:
    return AlertRepository(db)


def _to_alert_dto(entry: AlertEntry) -> AlertDto:
    return AlertDto(
        id=entry.id,
        location_id=entry.location_id,
        zone_id=entry.zone_id,
        device_id=entry.device_id,
        severity=entry.severity,
        message=entry.message,
        event_type=entry.event_type,
        status=entry.status,
        created_at=entry.created_at,
    )


@router.get("/alerts", response_model=list[AlertDto])
def list_alerts(
    status: str | None = Query(default=None, description="Filter by status (active or resolved)"),
    location_id: UUID | None = Query(default=None, description="Filter by location_id"),
    zone_id: UUID | None = Query(default=None, description="Filter by zone_id"),
    since: datetime | None = Query(default=None, description="Filter alerts created since ISO timestamp"),
    limit: int = Query(default=50, ge=1, le=200),
    repo: AlertRepository = Depends(get_alert_repo),
) -> list[AlertDto]:
    entries = repo.list_alerts(
        status=status,
        location_id=location_id,
        zone_id=zone_id,
        since=since,
        limit=limit,
    )
    return [_to_alert_dto(e) for e in entries]


@router.get("/events", response_model=list[AlertDto])
def list_events(
    since: datetime | None = Query(default=None, description="Filter events created since ISO timestamp"),
    location_id: UUID | None = Query(default=None, description="Filter by location_id"),
    zone_id: UUID | None = Query(default=None, description="Filter by zone_id"),
    limit: int = Query(default=50, ge=1, le=200),
    repo: AlertRepository = Depends(get_alert_repo),
) -> list[AlertDto]:
    entries = repo.list_alerts(
        location_id=location_id,
        zone_id=zone_id,
        since=since,
        limit=limit,
    )
    return [_to_alert_dto(e) for e in entries]