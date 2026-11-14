from datetime import datetime, timezone
from uuid import UUID, uuid4

from src.application.alerts.subscribers import AlertPersistenceSubscriber
from src.application.readings.service import ReadingIngest
from src.domain.devices.entity import Device
from src.domain.events.bus import EventBus
from src.domain.events.events import DomainEvent, ReadingCreated
from src.domain.sensors.reading import Reading
from src.infrastructure.persistence.alert_repository import AlertEntry
from src.interfaces.api.alerts import list_alerts


class _InMemoryAlertRepo:
    def __init__(self, zone_thresholds: dict[UUID, float] | None = None) -> None:
        self.alerts: list[AlertEntry] = []
        self._zone_thresholds = zone_thresholds or {}

    def get_zone_moisture_low(self, zone_id: UUID) -> float | None:
        return self._zone_thresholds.get(zone_id)

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
        entry = AlertEntry(
            id=uuid4(),
            location_id=location_id,
            zone_id=zone_id,
            device_id=device_id,
            severity=severity,
            message=message,
            event_type=event_type,
            status=status,
            created_at=datetime.now(timezone.utc),
        )
        self.alerts.insert(0, entry)
        return entry

    def list_alerts(
        self,
        status: str | None = None,
        location_id: UUID | None = None,
        zone_id: UUID | None = None,
        since: datetime | None = None,
        limit: int = 50,
    ) -> list[AlertEntry]:
        results = self.alerts
        if status:
            results = [a for a in results if a.status == status]
        if location_id is not None:
            results = [a for a in results if a.location_id == location_id]
        if zone_id is not None:
            results = [a for a in results if a.zone_id == zone_id]
        return results[:limit]


class _FakeDeviceRepo:
    def __init__(self, devices: list[Device]) -> None:
        self._devices = {d.id: d for d in devices if d.id is not None}

    def get_device(self, device_id: UUID) -> Device | None:
        return self._devices.get(device_id)


class _FakeReadingRepo:
    def __init__(self) -> None:
        self.rows: list[Reading] = []

    def save_reading(self, reading: Reading) -> Reading:
        saved = Reading(
            id=uuid4(),
            device_id=reading.device_id,
            value=reading.value,
            unit=reading.unit,
            source=reading.source,
            recorded_at=reading.recorded_at,
        )
        self.rows.append(saved)
        return saved


def test_ingest_publishes_only_when_tracking_enabled() -> None:
    tracked_id = uuid4()
    untracked_id = uuid4()
    tracked_dev = Device(
        id=tracked_id,
        device_type="moisture_sensor",
        role="sensor",
        device_family="simulation",
        display_name="Tracked Sensor",
        tracking_enabled=True,
    )
    untracked_dev = Device(
        id=untracked_id,
        device_type="moisture_sensor",
        role="sensor",
        device_family="simulation",
        display_name="Untracked Sensor",
        tracking_enabled=False,
    )

    bus = EventBus()
    published: list[DomainEvent] = []
    bus.subscribe(published.append)

    reading_repo = _FakeReadingRepo()
    ingest = ReadingIngest(
        device_repo=_FakeDeviceRepo([tracked_dev, untracked_dev]),  # type: ignore[arg-type]
        reading_repo=reading_repo,  # type: ignore[arg-type]
        event_bus=bus,
    )

    now = datetime.now(timezone.utc)
    # 1. Tracked device stores row AND publishes reading.created
    ingest.record(
        tracked_id,
        translated_reading=Reading(tracked_id, 0.25, "vwc", "mqtt", now),
    )
    assert len(reading_repo.rows) == 1
    assert len(published) == 1
    assert isinstance(published[0], ReadingCreated)

    # 2. Untracked device stores row but does NOT publish
    ingest.record(
        untracked_id,
        translated_reading=Reading(untracked_id, 0.20, "vwc", "mqtt", now),
    )
    assert len(reading_repo.rows) == 2
    assert len(published) == 1


def test_subscriber_copies_zone_and_location_or_leaves_null_and_filters_api() -> None:
    loc_id = uuid4()
    zone_a = uuid4()
    zone_b = uuid4()
    assigned_dev_id = uuid4()
    unassigned_dev_id = uuid4()

    alert_repo = _InMemoryAlertRepo(zone_thresholds={zone_a: 0.35})
    bus = EventBus()
    bus.subscribe(AlertPersistenceSubscriber(alert_repo))  # type: ignore[arg-type]

    # Assigned sensor low moisture -> alert carries location_id & zone_a
    bus.publish(
        ReadingCreated(
            device_id=assigned_dev_id,
            location_id=loc_id,
            zone_id=zone_a,
            value=0.22,
            unit="vwc",
            source="simulation",
        )
    )
    # Unassigned sensor low moisture -> location_id & zone_id stay None
    bus.publish(
        ReadingCreated(
            device_id=unassigned_dev_id,
            location_id=None,
            zone_id=None,
            value=0.18,
            unit="vwc",
            source="simulation",
        )
    )

    assert len(alert_repo.alerts) == 2
    unassigned_alert = alert_repo.alerts[0]
    assigned_alert = alert_repo.alerts[1]

    assert unassigned_alert.location_id is None
    assert unassigned_alert.zone_id is None
    assert assigned_alert.location_id == loc_id
    assert assigned_alert.zone_id == zone_a

    # GET /api/alerts filtered by zone_a returns only zone_a's alert
    filtered_a = list_alerts(status="active", location_id=loc_id, zone_id=zone_a, repo=alert_repo)  # type: ignore[arg-type]
    assert len(filtered_a) == 1
    assert filtered_a[0].zone_id == zone_a

    filtered_b = list_alerts(status="active", location_id=loc_id, zone_id=zone_b, repo=alert_repo)  # type: ignore[arg-type]
    assert filtered_b == []