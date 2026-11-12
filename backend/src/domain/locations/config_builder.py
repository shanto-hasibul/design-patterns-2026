from typing import Any, Self
from src.domain.locations.entity import Location, LocationConfig, Zone
from src.domain.locations.errors import ConfigurationError


def validate_zone_fields(
    name: str,
    moisture_threshold_low: float,
    moisture_threshold_high: float,
    schedule: dict[str, Any] | None = None,
) -> Zone:
    cleaned_name = name.strip() if name else ""
    if not cleaned_name:
        raise ConfigurationError("Zone name is required and cannot be empty.")

    if not (0.0 <= moisture_threshold_low <= 1.0) or not (
        0.0 <= moisture_threshold_high <= 1.0
    ):
        raise ConfigurationError(
            "Moisture thresholds must be between 0.0 and 1.0 (VWC)."
        )

    if moisture_threshold_low >= moisture_threshold_high:
        raise ConfigurationError(
            "moisture_threshold_low must be strictly less than moisture_threshold_high."
        )

    return Zone(
        name=cleaned_name,
        moisture_threshold_low=float(moisture_threshold_low),
        moisture_threshold_high=float(moisture_threshold_high),
        schedule=dict(schedule) if schedule is not None else {},
    )


class LocationConfigBuilder:
    def __init__(self) -> None:
        self._location_name: str | None = None
        self._zones: list[tuple[str, float, float, dict[str, Any] | None]] = []

    def set_location_name(self, name: str) -> Self:
        self._location_name = name
        return self

    def add_zone(
        self,
        name: str,
        moisture_threshold_low: float,
        moisture_threshold_high: float,
        schedule: dict[str, Any] | None = None,
    ) -> Self:
        self._zones.append(
            (name, moisture_threshold_low, moisture_threshold_high, schedule)
        )
        return self

    def build(self) -> LocationConfig:
        cleaned_loc_name = (
            self._location_name.strip() if self._location_name else ""
        )
        if not cleaned_loc_name:
            raise ConfigurationError(
                "Location name is required and cannot be empty."
            )

        if not self._zones:
            raise ConfigurationError(
                "At least one zone is required to build a location configuration."
            )

        built_zones: list[Zone] = []
        seen_names: set[str] = set()

        for z_name, low, high, sched in self._zones:
            zone = validate_zone_fields(z_name, low, high, sched)
            normalized_key = zone.name.lower()
            if normalized_key in seen_names:
                raise ConfigurationError(
                    f"Duplicate zone name '{zone.name}' within the same location."
                )
            seen_names.add(normalized_key)
            built_zones.append(zone)

        location = Location(
            name=cleaned_loc_name,
            zones=tuple(built_zones),
            id=None,
        )
        return LocationConfig(location=location)