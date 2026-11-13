from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.infrastructure.persistence.models import ActuatorStateRow


class ActuatorStateRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_state(self, device_id: UUID) -> str:
        row = self._session.get(ActuatorStateRow, device_id)
        if row is None:
            return "idle"
        return row.state

    def get_states_for_devices(self, device_ids: list[UUID]) -> dict[UUID, str]:
        if not device_ids:
            return {}
        stmt = select(ActuatorStateRow).where(
            ActuatorStateRow.device_id.in_(device_ids)
        )
        rows = self._session.scalars(stmt).all()
        return {r.device_id: r.state for r in rows}

    def save_state(self, device_id: UUID, state: str) -> str:
        row = self._session.get(ActuatorStateRow, device_id)
        now = datetime.now(timezone.utc)
        if row is None:
            row = ActuatorStateRow(
                device_id=device_id,
                state=state,
                updated_at=now,
            )
            self._session.add(row)
        else:
            row.state = state
            row.updated_at = now

        self._session.commit()
        self._session.refresh(row)
        return row.state

    def seed_missing_states(self, actuator_ids: list[UUID]) -> None:
        if not actuator_ids:
            return
        existing = self.get_states_for_devices(actuator_ids)
        now = datetime.now(timezone.utc)
        added = False
        for dev_id in actuator_ids:
            if dev_id not in existing:
                self._session.add(
                    ActuatorStateRow(device_id=dev_id, state="idle", updated_at=now)
                )
                added = True
        if added:
            self._session.commit()