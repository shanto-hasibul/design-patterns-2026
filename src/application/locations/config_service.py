from typing import Any
from uuid import UUID

from src.application.locations.dto import CreateLocationConfigRequestDto
from src.application.locations.mappers import build_config_from_dto
from src.domain.locations.config_builder import validate_zone_fields
from src.domain.locations.entity import Location, LocationConfig, Zone
from src.infrastructure.persistence.location_repository import LocationRepository


class LocationConfigService:
    def __init__(self, repo: LocationRepository) -> None:
        self._repo = repo

    def create_config(
        self, request_dto: CreateLocationConfigRequestDto
    ) -> LocationConfig:
        built_config = build_config_from_dto(request_dto)
        return self._repo.save_config(built_config)

    def get_config(self, location_id: UUID) -> LocationConfig | None:
        return self._repo.get_config(location_id)

    def list_locations(self) -> list[Location]:
        return self._repo.list_locations()

    def delete_location(self, location_id: UUID) -> bool:
        return self._repo.delete_location(location_id)

    def add_zone(
        self,
        location_id: UUID,
        name: str,
        moisture_threshold_low: float,
        moisture_threshold_high: float,
        schedule: dict[str, Any] | None = None,
    ) -> Zone | None:
        validated = validate_zone_fields(
            name=name,
            moisture_threshold_low=moisture_threshold_low,
            moisture_threshold_high=moisture_threshold_high,
            schedule=schedule,
        )
        return self._repo.add_zone(location_id, validated)

    def update_zone(
        self,
        location_id: UUID,
        zone_id: UUID,
        name: str,
        moisture_threshold_low: float,
        moisture_threshold_high: float,
        schedule: dict[str, Any] | None = None,
    ) -> Zone | None:
        validated = validate_zone_fields(
            name=name,
            moisture_threshold_low=moisture_threshold_low,
            moisture_threshold_high=moisture_threshold_high,
            schedule=schedule,
        )
        return self._repo.update_zone(location_id, zone_id, validated)

    def delete_zone(self, location_id: UUID, zone_id: UUID) -> bool:
        return self._repo.delete_zone(location_id, zone_id)