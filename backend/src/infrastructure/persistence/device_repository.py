from sqlalchemy import select
from sqlalchemy.orm import Session

from src.domain.devices.entity import Device
from src.domain.sensors.entity import Sensor
from src.infrastructure.persistence.models import DeviceRow


class DeviceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save_sensor(self, sensor: Sensor, device_family: str = "simulation") -> Sensor:
        row = DeviceRow(
            device_type=sensor.device_type,
            role="sensor",
            device_family=device_family,
            display_name=sensor.display_name,
            default_config=sensor.default_config,
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

    def save_device(self, device: Device) -> Device:
        row = DeviceRow(
            device_type=device.device_type,
            role=device.role,
            device_family=device.device_family,
            display_name=device.display_name,
            default_config=device.default_config,
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

    @staticmethod
    def _to_sensor_domain(row: DeviceRow) -> Sensor:
        return Sensor(
            id=row.id,
            device_type=row.device_type,
            display_name=row.display_name or "",
            default_config=dict(row.default_config or {}),
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
        )