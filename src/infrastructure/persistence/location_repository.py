from uuid import UUID
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from src.domain.locations.entity import Location, LocationConfig, Zone
from src.domain.locations.errors import ConfigurationError
from src.infrastructure.persistence.models import DeviceRow, LocationRow, ZoneRow


class LocationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save_config(self, config: LocationConfig) -> LocationConfig:
        try:
            loc_row = LocationRow(name=config.location.name)
            self._session.add(loc_row)
            self._session.flush()

            zone_rows: list[ZoneRow] = []
            for z in config.location.zones:
                z_row = ZoneRow(
                    location_id=loc_row.id,
                    name=z.name,
                    moisture_threshold_low=z.moisture_threshold_low,
                    moisture_threshold_high=z.moisture_threshold_high,
                    schedule=z.schedule,
                )
                self._session.add(z_row)
                zone_rows.append(z_row)

            self._session.commit()
            self._session.refresh(loc_row)
            for zr in zone_rows:
                self._session.refresh(zr)

            return LocationConfig(
                location=Location(
                    id=loc_row.id,
                    name=loc_row.name,
                    zones=tuple(self._to_zone_domain(zr) for zr in zone_rows),
                )
            )
        except Exception:
            self._session.rollback()
            raise

    def get_config(self, location_id: UUID) -> LocationConfig | None:
        loc_row = self._session.get(LocationRow, location_id)
        if loc_row is None:
            return None

        stmt = (
            select(ZoneRow)
            .where(ZoneRow.location_id == location_id)
            .order_by(ZoneRow.name.asc())
        )
        zone_rows = self._session.scalars(stmt).all()

        return LocationConfig(
            location=Location(
                id=loc_row.id,
                name=loc_row.name,
                zones=tuple(self._to_zone_domain(zr) for zr in zone_rows),
            )
        )

    def list_locations(self) -> list[Location]:
        stmt = select(LocationRow).order_by(LocationRow.created_at.desc())
        rows = self._session.scalars(stmt).all()
        return [Location(id=r.id, name=r.name, zones=()) for r in rows]

    def delete_location(self, location_id: UUID) -> bool:
        loc_row = self._session.get(LocationRow, location_id)
        if loc_row is None:
            return False

        self._session.execute(
            update(DeviceRow)
            .where(DeviceRow.location_id == location_id)
            .values(zone_id=None, location_id=None)
        )
        self._session.delete(loc_row)
        self._session.commit()
        return True

    def add_zone(self, location_id: UUID, zone: Zone) -> Zone | None:
        loc_row = self._session.get(LocationRow, location_id)
        if loc_row is None:
            return None

        existing_zones = self._session.scalars(
            select(ZoneRow).where(ZoneRow.location_id == location_id)
        ).all()
        if any(z.name.lower() == zone.name.lower() for z in existing_zones):
            raise ConfigurationError(
                f"Duplicate zone name '{zone.name}' within the same location."
            )

        z_row = ZoneRow(
            location_id=location_id,
            name=zone.name,
            moisture_threshold_low=zone.moisture_threshold_low,
            moisture_threshold_high=zone.moisture_threshold_high,
            schedule=zone.schedule,
        )
        self._session.add(z_row)
        self._session.commit()
        self._session.refresh(z_row)
        return self._to_zone_domain(z_row)

    def update_zone(
        self, location_id: UUID, zone_id: UUID, updated: Zone
    ) -> Zone | None:
        z_row = self._session.get(ZoneRow, zone_id)
        if z_row is None or z_row.location_id != location_id:
            return None

        sibling_zones = self._session.scalars(
            select(ZoneRow).where(
                ZoneRow.location_id == location_id, ZoneRow.id != zone_id
            )
        ).all()
        if any(z.name.lower() == updated.name.lower() for z in sibling_zones):
            raise ConfigurationError(
                f"Duplicate zone name '{updated.name}' within the same location."
            )

        z_row.name = updated.name
        z_row.moisture_threshold_low = updated.moisture_threshold_low
        z_row.moisture_threshold_high = updated.moisture_threshold_high
        z_row.schedule = updated.schedule
        self._session.commit()
        self._session.refresh(z_row)
        return self._to_zone_domain(z_row)

    def delete_zone(self, location_id: UUID, zone_id: UUID) -> bool:
        z_row = self._session.get(ZoneRow, zone_id)
        if z_row is None or z_row.location_id != location_id:
            return False

        zones_in_loc = self._session.scalars(
            select(ZoneRow).where(ZoneRow.location_id == location_id)
        ).all()
        if len(zones_in_loc) <= 1:
            raise ConfigurationError(
                "Cannot delete the last remaining zone on a location."
            )

        self._session.execute(
            update(DeviceRow)
            .where(DeviceRow.zone_id == zone_id)
            .values(zone_id=None, location_id=None)
        )
        self._session.delete(z_row)
        self._session.commit()
        return True

    def get_zone(self, zone_id: UUID) -> Zone | None:
        z_row = self._session.get(ZoneRow, zone_id)
        if z_row is None:
            return None
        return self._to_zone_domain(z_row)

    @staticmethod
    def _to_zone_domain(row: ZoneRow) -> Zone:
        return Zone(
            id=row.id,
            location_id=row.location_id,
            name=row.name,
            moisture_threshold_low=float(row.moisture_threshold_low),
            moisture_threshold_high=float(row.moisture_threshold_high),
            schedule=dict(row.schedule or {}),
        )