from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from src.application.automation.service import AutomationService, LocationNotFoundError
from src.application.overview.facade import LocationOverviewFacade
from src.domain.automation.context import (
    LocationAutomationContext,
    ZoneAutomationContext,
)
from src.domain.devices.entity import Device
from src.domain.locations.entity import Location, LocationConfig, Zone
from src.domain.sensors.reading import Reading
from src.interfaces.api.overview import get_location_overview


class _InMemoryOverviewStore:
    def __init__(self) -> None:
        self.locations: dict[UUID, LocationConfig] = {}
        self.devices: dict[UUID, Device] = {}
        self.readings: list[Reading] = []
        self.saved_strategies: dict[UUID, str] = {}

    # LocationRepository methods
    def get_config(self, location_id: UUID) -> LocationConfig | None:
        return self.locations.get(location_id)

    # DeviceRepository methods
    def list_assigned_devices_for_location(self, location_id: UUID) -> list[Device]:
        return [
            d
            for d in self.devices.values()
            if d.location_id == location_id and d.zone_id is not None
        ]

    # ReadingRepository methods
    def get_latest_readings_for_devices(
        self, device_ids: list[UUID]
    ) -> dict[UUID, Reading]:
        result: dict[UUID, Reading] = {}
        for dev_id in device_ids:
            matching = [r for r in self.readings if r.device_id == dev_id]
            if matching:
                matching.sort(key=lambda r: r.recorded_at, reverse=True)
                result[dev_id] = matching[0]
        return result

    # AutomationRepository methods
    def find_saved_strategy_key(self, location_id: UUID) -> str | None:
        return self.saved_strategies.get(location_id)

    def get_strategy_key(self, location_id: UUID) -> str:
        return self.saved_strategies.get(location_id, "conservative")

    def upsert_strategy(self, location_id: UUID, strategy_key: str) -> str:
        self.saved_strategies[location_id] = strategy_key
        return strategy_key

    def build_location_context(
        self, location_id: UUID
    ) -> LocationAutomationContext | None:
        cfg = self.locations.get(location_id)
        if cfg is None:
            return None
        zone_ctxs: list[ZoneAutomationContext] = []
        for z in cfg.location.zones:
            z_sensors = [
                d
                for d in self.devices.values()
                if d.zone_id == z.id and d.role == "sensor" and "moisture" in d.device_type
            ]
            latest_val: float | None = None
            for s in z_sensors:
                if s.id is not None:
                    r = self.get_latest_readings_for_devices([s.id]).get(s.id)
                    if r is not None:
                        latest_val = r.value
            zone_ctxs.append(
                ZoneAutomationContext(
                    location_id=location_id,
                    zone_id=z.id,  # type: ignore[arg-type]
                    zone_name=z.name,
                    moisture_threshold_low=z.moisture_threshold_low,
                    moisture_threshold_high=z.moisture_threshold_high,
                    latest_moisture=latest_val,
                )
            )
        return LocationAutomationContext(
            location_id=location_id,
            location_name=cfg.location.name,
            zones=tuple(zone_ctxs),
        )


def test_overview_returns_strategy_and_readings() -> None:
    store = _InMemoryOverviewStore()
    loc_id = uuid4()
    zone1_id = uuid4()
    zone2_id = uuid4()

    store.locations[loc_id] = LocationConfig(
        location=Location(
            id=loc_id,
            name="Seeded Greenhouse",
            zones=(
                Zone(
                    id=zone1_id,
                    location_id=loc_id,
                    name="Zone 1",
                    moisture_threshold_low=0.30,
                    moisture_threshold_high=0.70,
                ),
                Zone(
                    id=zone2_id,
                    location_id=loc_id,
                    name="Zone 2 (Empty)",
                    moisture_threshold_low=0.25,
                    moisture_threshold_high=0.65,
                ),
            ),
        )
    )

    assigned_sensor_id = uuid4()
    unassigned_sensor_id = uuid4()

    store.devices[assigned_sensor_id] = Device(
        id=assigned_sensor_id,
        device_type="moisture_sensor",
        role="sensor",
        device_family="simulation",
        display_name="Zone 1 Moisture Sensor",
        zone_id=zone1_id,
        location_id=loc_id,
        sampling_interval_seconds=120,
        tracking_enabled=True,
    )
    store.devices[unassigned_sensor_id] = Device(
        id=unassigned_sensor_id,
        device_type="moisture_sensor",
        role="sensor",
        device_family="simulation",
        display_name="Unassigned Spare Sensor",
        zone_id=None,
        location_id=None,
    )

    store.readings.append(
        Reading(
            id=uuid4(),
            device_id=assigned_sensor_id,
            value=0.22,
            unit="vwc",
            source="simulation",
            recorded_at=datetime.now(timezone.utc),
        )
    )

    automation_service = AutomationService(store)  # type: ignore[arg-type]
    facade = LocationOverviewFacade(
        location_repo=store,  # type: ignore[arg-type]
        device_repo=store,  # type: ignore[arg-type]
        reading_repo=store,  # type: ignore[arg-type]
        automation_repo=store,  # type: ignore[arg-type]
        automation_service=automation_service,
    )

    # 1. Unknown location id -> 404 via API handler
    with pytest.raises(HTTPException) as exc_info:
        get_location_overview(uuid4(), facade=facade)
    assert exc_info.value.status_code == 404

    # 2. Before a key is saved: strategy_key and last_recommendation are null
    initial = get_location_overview(loc_id, facade=facade)
    assert initial.location.name == "Seeded Greenhouse"
    assert initial.strategy_key is None
    assert initial.last_recommendation is None
    assert initial.device_counts.sensor == 1
    assert initial.device_counts.actuator == 0

    all_overview_device_ids = {
        d.id for z in initial.zones for d in z.devices
    }
    assert unassigned_sensor_id not in all_overview_device_ids
    assert assigned_sensor_id in all_overview_device_ids

    z1_overview = next(z for z in initial.zones if z.id == zone1_id)
    assert len(z1_overview.latest_readings) == 1
    assert z1_overview.latest_readings[0].value == pytest.approx(0.22)
    assert z1_overview.latest_readings[0].unit == "vwc"
    assert z1_overview.latest_readings[0].tracking_enabled is True
    assert z1_overview.latest_readings[0].sampling_interval_seconds == 120

    z2_overview = next(z for z in initial.zones if z.id == zone2_id)
    assert z2_overview.devices == []
    assert z2_overview.latest_readings == []

    # 3. After saving a strategy key: last_recommendation matches evaluate()
    automation_service.save_strategy(loc_id, "conservative")
    eval_dto = automation_service.evaluate(loc_id)
    after_save = get_location_overview(loc_id, facade=facade)

    assert after_save.strategy_key == "conservative"
    assert after_save.last_recommendation is not None
    assert after_save.last_recommendation.action == eval_dto.action
    assert after_save.last_recommendation.reason == eval_dto.reason