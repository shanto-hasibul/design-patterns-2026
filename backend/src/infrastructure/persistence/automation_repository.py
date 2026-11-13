from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.domain.automation.context import (
    LocationAutomationContext,
    ZoneAutomationContext,
)
from src.infrastructure.persistence.models import (
    AutomationRuleRow,
    DeviceRow,
    LocationRow,
    ReadingRow,
    ZoneRow,
)


class AutomationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_saved_strategy_key(self, location_id: UUID) -> str | None:
        stmt = select(AutomationRuleRow).where(
            AutomationRuleRow.location_id == location_id
        )
        row = self._session.scalars(stmt).first()
        return row.strategy_key if row is not None else None

    def get_strategy_key(self, location_id: UUID) -> str:
        saved = self.find_saved_strategy_key(location_id)
        return saved if saved is not None else "conservative"

    def upsert_strategy(
        self,
        location_id: UUID,
        strategy_key: str,
        parameters: dict[str, Any] | None = None,
    ) -> str:
        stmt = select(AutomationRuleRow).where(
            AutomationRuleRow.location_id == location_id
        )
        row = self._session.scalars(stmt).first()
        now = datetime.now(timezone.utc)
        if row is None:
            row = AutomationRuleRow(
                location_id=location_id,
                strategy_key=strategy_key,
                parameters=dict(parameters or {}),
                updated_at=now,
            )
            self._session.add(row)
        else:
            row.strategy_key = strategy_key
            if parameters is not None:
                row.parameters = dict(parameters)
            row.updated_at = now

        self._session.commit()
        self._session.refresh(row)
        return row.strategy_key

    def build_location_context(
        self, location_id: UUID
    ) -> LocationAutomationContext | None:
        loc_row = self._session.get(LocationRow, location_id)
        if loc_row is None:
            return None

        zones = self._session.scalars(
            select(ZoneRow)
            .where(ZoneRow.location_id == location_id)
            .order_by(ZoneRow.name.asc())
        ).all()

        zone_contexts: list[ZoneAutomationContext] = []
        for z in zones:
            zone_sensors = self._session.scalars(
                select(DeviceRow).where(
                    DeviceRow.zone_id == z.id,
                    DeviceRow.role == "sensor",
                )
            ).all()

            latest_moisture: float | None = None
            latest_moisture_ts: datetime | None = None
            latest_light: float | None = None
            latest_light_ts: datetime | None = None

            for sensor in zone_sensors:
                latest_reading = self._session.scalars(
                    select(ReadingRow)
                    .where(ReadingRow.device_id == sensor.id)
                    .order_by(ReadingRow.recorded_at.desc())
                    .limit(1)
                ).first()
                if latest_reading is None:
                    continue

                dtype = sensor.device_type.lower()
                if "moisture" in dtype:
                    if (
                        latest_moisture_ts is None
                        or latest_reading.recorded_at > latest_moisture_ts
                    ):
                        latest_moisture = float(latest_reading.value)
                        latest_moisture_ts = latest_reading.recorded_at
                elif "light" in dtype:
                    if (
                        latest_light_ts is None
                        or latest_reading.recorded_at > latest_light_ts
                    ):
                        latest_light = float(latest_reading.value)
                        latest_light_ts = latest_reading.recorded_at

            zone_contexts.append(
                ZoneAutomationContext(
                    location_id=loc_row.id,
                    zone_id=z.id,
                    zone_name=z.name,
                    moisture_threshold_low=float(z.moisture_threshold_low),
                    moisture_threshold_high=float(z.moisture_threshold_high),
                    latest_moisture=latest_moisture,
                    latest_light=latest_light,
                )
            )

        return LocationAutomationContext(
            location_id=loc_row.id,
            location_name=loc_row.name,
            zones=tuple(zone_contexts),
        )