from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.infrastructure.persistence.models import ActuatorExecutionLogRow


@dataclass(frozen=True)
class ExecutionLogEntry:
    id: UUID
    device_id: UUID
    success: bool
    policy_applied: list[str]
    message: str | None
    created_at: datetime


class ExecutionLogRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def append_log(
        self,
        device_id: UUID,
        success: bool,
        policy_applied: list[str],
        message: str | None = None,
    ) -> ExecutionLogEntry:
        row = ActuatorExecutionLogRow(
            device_id=device_id,
            success=success,
            policy_applied=list(policy_applied),
            message=message,
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return self._to_domain(row)

    def list_recent(
        self, limit: int = 20, device_id: UUID | None = None
    ) -> list[ExecutionLogEntry]:
        stmt = select(ActuatorExecutionLogRow)
        if device_id is not None:
            stmt = stmt.where(ActuatorExecutionLogRow.device_id == device_id)
        stmt = stmt.order_by(ActuatorExecutionLogRow.created_at.desc()).limit(
            max(1, limit)
        )
        rows = self._session.scalars(stmt).all()
        return [self._to_domain(r) for r in rows]

    @staticmethod
    def _to_domain(row: ActuatorExecutionLogRow) -> ExecutionLogEntry:
        return ExecutionLogEntry(
            id=row.id,
            device_id=row.device_id,
            success=row.success,
            policy_applied=list(row.policy_applied or []),
            message=row.message,
            created_at=row.created_at,
        )