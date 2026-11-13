from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.domain.devices.entity import Device
from src.domain.sensors.entity import Sensor
from src.infrastructure.persistence.models import DeviceRow


class DeviceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save_sensor(self, sensor: Sensor, device_family: str = "simulation") -> Sensor:
        interval = sensor.sampling_interval_seconds
        if "sampling_interval_seconds" in sensor.default_config:
            try:
                interval = max(5, int(sensor.default_config["sampling_interval_seconds"]))
            except (TypeError, ValueError):
                interval = 300

        row = DeviceRow(
            device_type=sensor.device_type,
            role="sensor",
            device_family=device_family,
            display_name=sensor.display_name,
            default_config=sensor.default_config,
            sampling_interval_seconds=interval,
            tracking_enabled=sensor.tracking_enabled,
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return self._to_sensor_domain(row)

    def list_sensors(self) -> list[Sensor]:
        stmt = (
            select(DeviceRow)
            .where(DeviceRow.role == "sensor")
            .order_by(DeviceRow.created_at.desc())
        )
        rows = self._session.scalars(stmt).all()
        return [self._to_sensor_domain(row) for row in rows]

    def get_device(self, device_id: UUID) -> Device | None:
        row = self._session.get(DeviceRow, device_id)
        if row is None:
            return None
        return self._to_device_domain(row)

    def save_device(self, device: Device) -> Device:
        row = DeviceRow(
            device_type=device.device_type,
            role=device.role,
            device_family=device.device_family,
            display_name=device.display_name,
            default_config=device.default_config,
            zone_id=device.zone_id,
            location_id=device.location_id,
            sampling_interval_seconds=device.sampling_interval_seconds,
            tracking_enabled=device.tracking_enabled,
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return self._to_device_domain(row)

    def save_devices(self, devices: list[Device]) -> list[Device]:
        rows = [
            DeviceRow(
                device_type=d.device_type,
                role=d.role,
                device_family=d.device_family,
                display_name=d.display_name,
                default_config=d.default_config,
                zone_id=d.zone_id,
                location_id=d.location_id,
                sampling_interval_seconds=d.sampling_interval_seconds,
                tracking_enabled=d.tracking_enabled,
            )
            for d in devices
        ]
        self._session.add_all(rows)
        self._session.commit()
        for row in rows:
            self._session.refresh(row)
        return [self._to_device_domain(row) for row in rows]

    def list_devices(
        self,
        device_family: str | None = None,
        role: str | None = None,
    ) -> list[Device]:
        stmt = select(DeviceRow)
        if device_family:
            stmt = stmt.where(DeviceRow.device_family == device_family.strip().lower())
        if role:
            stmt = stmt.where(DeviceRow.role == role.strip().lower())
        stmt = stmt.order_by(DeviceRow.created_at.desc())
        rows = self._session.scalars(stmt).all()
        return [self._to_device_domain(row) for row in rows]

    def list_assigned_devices_for_location(self, location_id: UUID) -> list[Device]:
        stmt = (
            select(DeviceRow)
            .where(
                DeviceRow.location_id == location_id,
                DeviceRow.zone_id.is_not(None),
            )
            .order_by(DeviceRow.created_at.asc())
        )
        rows = self._session.scalars(stmt).all()
        return [self._to_device_domain(row) for row in rows]

    def list_devices_by_zone(self, zone_id: UUID) -> list[Device]:
        stmt = (
            select(DeviceRow)
            .where(DeviceRow.zone_id == zone_id)
            .order_by(DeviceRow.created_at.desc())
        )
        rows = self._session.scalars(stmt).all()
        return [self._to_device_domain(row) for row in rows]

    def update_device_zone(
        self,
        device_id: UUID,
        zone_id: UUID | None,
        location_id: UUID | None,
    ) -> Device | None:
        row = self._session.get(DeviceRow, device_id)
        if row is None:
            return None

        row.zone_id = zone_id
        row.location_id = location_id
        self._session.commit()
        self._session.refresh(row)
        return self._to_device_domain(row)

    def update_device_sampling(
        self,
        device_id: UUID,
        sampling_interval_seconds: int,
        tracking_enabled: bool,
    ) -> Device | None:
        row = self._session.get(DeviceRow, device_id)
        if row is None:
            return None

        row.sampling_interval_seconds = sampling_interval_seconds
        row.tracking_enabled = tracking_enabled
        self._session.commit()
        self._session.refresh(row)
        return self._to_device_domain(row)

    @staticmethod
    def _to_sensor_domain(row: DeviceRow) -> Sensor:
        return Sensor(
            id=row.id,
            device_type=row.device_type,
            display_name=row.display_name or "",
            default_config=dict(row.default_config or {}),
            sampling_interval_seconds=row.sampling_interval_seconds,
            tracking_enabled=row.tracking_enabled,
            zone_id=row.zone_id,
            location_id=row.location_id,
        )

    @staticmethod
    def _to_device_domain(row: DeviceRow) -> Device:
        return Device(
            id=row.id,
            device_type=row.device_type,
            role=row.role,
            device_family=row.device_family,
            display_name=row.display_name or "",
            default_config=dict(row.default_config or {}),
            zone_id=row.zone_id,
            location_id=row.location_id,
            sampling_interval_seconds=row.sampling_interval_seconds,
            tracking_enabled=row.tracking_enabled,
        )