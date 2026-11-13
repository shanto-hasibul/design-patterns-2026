from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.domain.sensors.reading import Reading
from src.infrastructure.persistence.models import ReadingRow


class ReadingRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save_reading(self, reading: Reading) -> Reading:
        row = ReadingRow(
            device_id=reading.device_id,
            value=reading.value,
            unit=reading.unit,
            source=reading.source,
            recorded_at=reading.recorded_at,
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return self._to_domain(row)

    def list_readings_for_device(
        self, device_id: UUID, limit: int = 20
    ) -> list[Reading]:
        stmt = (
            select(ReadingRow)
            .where(ReadingRow.device_id == device_id)
            .order_by(ReadingRow.recorded_at.desc())
            .limit(max(1, limit))
        )
        rows = self._session.scalars(stmt).all()
        return [self._to_domain(r) for r in rows]

    def get_latest_reading(self, device_id: UUID) -> Reading | None:
        rows = self.list_readings_for_device(device_id, limit=1)
        return rows[0] if rows else None

    @staticmethod
    def _to_domain(row: ReadingRow) -> Reading:
        return Reading(
            id=row.id,
            device_id=row.device_id,
            value=float(row.value),
            unit=row.unit,
            source=row.source,
            recorded_at=row.recorded_at,
        )