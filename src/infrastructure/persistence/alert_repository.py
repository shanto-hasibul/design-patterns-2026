from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.infrastructure.persistence.models import AlertRow, ZoneRow


@dataclass(frozen=True)
class AlertEntry:
    id: UUID
    location_id: UUID | None
    zone_id: UUID | None
    device_id: UUID | None
    severity: str
    message: str
    event_type: str
    status: str
    created_at: datetime
    acknowledged_at: datetime | None = None


class AlertRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_alert(
        self,
        event_type: str,
        message: str,
        severity: str = "warning",
        location_id: UUID | None = None,
        zone_id: UUID | None = None,
        device_id: UUID | None = None,
        status: str = "active",
    ) -> AlertEntry:
        row = AlertRow(
            location_id=location_id,
            zone_id=zone_id,
            device_id=device_id,
            severity=severity,
            message=message,
            event_type=event_type,
            status=status,
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return self._to_domain(row)

    def get_zone_moisture_low(self, zone_id: UUID) -> float | None:
        row = self._session.get(ZoneRow, zone_id)
        if row is None:
            return None
        return float(row.moisture_threshold_low)

    def list_alerts(
        self,
        status: str | None = None,
        location_id: UUID | None = None,
        zone_id: UUID | None = None,
        since: datetime | None = None,
        limit: int = 50,
    ) -> list[AlertEntry]:
        stmt = select(AlertRow)
        if status:
            stmt = stmt.where(AlertRow.status == status.strip().lower())
        if location_id is not None:
            stmt = stmt.where(AlertRow.location_id == location_id)
        if zone_id is not None:
            stmt = stmt.where(AlertRow.zone_id == zone_id)
        if since is not None:
            ts = since.replace(tzinfo=timezone.utc) if since.tzinfo is None else since
            stmt = stmt.where(AlertRow.created_at >= ts)

        stmt = stmt.order_by(AlertRow.created_at.desc()).limit(max(1, limit))
        rows = self._session.scalars(stmt).all()
        return [self._to_domain(r) for r in rows]

    @staticmethod
    def _to_domain(row: AlertRow) -> AlertEntry:
        return AlertEntry(
            id=row.id,
            location_id=row.location_id,
            zone_id=row.zone_id,
            device_id=row.device_id,
            severity=row.severity,
            message=row.message,
            event_type=row.event_type,
            status=row.status,
            created_at=row.created_at,
            acknowledged_at=row.acknowledged_at,
        )