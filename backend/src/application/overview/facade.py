from uuid import UUID

from src.application.automation.service import AutomationService, LocationNotFoundError
from src.application.overview.dto import (
    LocationOverviewDto,
    OverviewDeviceCountsDto,
    OverviewLatestReadingDto,
    OverviewLocationDto,
    OverviewRecommendationDto,
    OverviewZoneDeviceDto,
    OverviewZoneDto,
)
from src.infrastructure.persistence.automation_repository import AutomationRepository
from src.infrastructure.persistence.device_repository import DeviceRepository
from src.infrastructure.persistence.location_repository import LocationRepository
from src.infrastructure.persistence.reading_repository import ReadingRepository


class LocationOverviewFacade:
    """Single read entry point aggregating location, zones, assigned devices, latest readings, and strategy."""

    def __init__(
        self,
        location_repo: LocationRepository,
        device_repo: DeviceRepository,
        reading_repo: ReadingRepository,
        automation_repo: AutomationRepository,
        automation_service: AutomationService,
    ) -> None:
        self._location_repo = location_repo
        self._device_repo = device_repo
        self._reading_repo = reading_repo
        self._automation_repo = automation_repo
        self._automation_service = automation_service

    def get_overview(self, location_id: UUID) -> LocationOverviewDto:
        # 1. Single load of location and its zones
        config = self._location_repo.get_config(location_id)
        if config is None:
            raise LocationNotFoundError(f"Location '{location_id}' not found.")

        # 2. Single query for devices assigned to this location (location_id set & zone_id non-null)
        assigned_devices = self._device_repo.list_assigned_devices_for_location(location_id)
        assigned_ids = [d.id for d in assigned_devices if d.id is not None]

        # 3. Single batch query for newest reading per assigned device
        latest_by_device = self._reading_repo.get_latest_readings_for_devices(assigned_ids)

        # Group assigned devices by zone_id
        devices_by_zone: dict[UUID, list] = {}
        sensor_count = 0
        actuator_count = 0
        for dev in assigned_devices:
            if dev.zone_id is None:
                continue
            devices_by_zone.setdefault(dev.zone_id, []).append(dev)
            if dev.role == "sensor":
                sensor_count += 1
            elif dev.role == "actuator":
                actuator_count += 1

        zone_dtos: list[OverviewZoneDto] = []
        for zone in config.location.zones:
            assert zone.id is not None
            z_devices = devices_by_zone.get(zone.id, [])
            z_device_dtos: list[OverviewZoneDeviceDto] = []
            z_reading_dtos: list[OverviewLatestReadingDto] = []

            for dev in z_devices:
                if dev.id is None:
                    continue
                z_device_dtos.append(
                    OverviewZoneDeviceDto(
                        id=dev.id,
                        device_type=dev.device_type,
                        role=dev.role,
                        display_name=dev.display_name,
                    )
                )
                latest = latest_by_device.get(dev.id)
                if latest is not None:
                    z_reading_dtos.append(
                        OverviewLatestReadingDto(
                            device_id=dev.id,
                            value=latest.value,
                            unit=latest.unit,
                            recorded_at=latest.recorded_at,
                            tracking_enabled=dev.tracking_enabled,
                            sampling_interval_seconds=dev.sampling_interval_seconds,
                        )
                    )

            zone_dtos.append(
                OverviewZoneDto(
                    id=zone.id,
                    name=zone.name,
                    moisture_threshold_low=zone.moisture_threshold_low,
                    moisture_threshold_high=zone.moisture_threshold_high,
                    devices=z_device_dtos,
                    latest_readings=z_reading_dtos,
                )
            )

        # 4. Read saved strategy key; evaluate only when a key is saved
        saved_key = self._automation_repo.find_saved_strategy_key(location_id)
        last_recommendation: OverviewRecommendationDto | None = None
        if saved_key is not None:
            eval_result = self._automation_service.evaluate(
                location_id, override_strategy_key=saved_key
            )
            last_recommendation = OverviewRecommendationDto(
                action=eval_result.action,
                reason=eval_result.reason,
            )

        return LocationOverviewDto(
            location=OverviewLocationDto(
                id=config.location.id,  # type: ignore[arg-type]
                name=config.location.name,
            ),
            device_counts=OverviewDeviceCountsDto(
                sensor=sensor_count,
                actuator=actuator_count,
            ),
            zones=zone_dtos,
            strategy_key=saved_key,
            last_recommendation=last_recommendation,
        )