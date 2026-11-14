from src.application.locations.dto import (
    CreateLocationConfigRequestDto,
    LocationConfigResponseDto,
    LocationSummaryDto,
    ZoneResponseDto,
)
from src.domain.locations.config_builder import LocationConfigBuilder
from src.domain.locations.entity import Location, LocationConfig, Zone


def build_config_from_dto(dto: CreateLocationConfigRequestDto) -> LocationConfig:
    builder = LocationConfigBuilder().set_location_name(dto.location_name)
    for z in dto.zones:
        builder.add_zone(
            name=z.name,
            moisture_threshold_low=z.moisture_threshold_low,
            moisture_threshold_high=z.moisture_threshold_high,
            schedule=z.schedule,
        )
    return builder.build()


def to_zone_response_dto(zone: Zone) -> ZoneResponseDto:
    if zone.id is None or zone.location_id is None:
        raise ValueError("Cannot map an unpersisted Zone to ZoneResponseDto")
    return ZoneResponseDto(
        id=zone.id,
        location_id=zone.location_id,
        name=zone.name,
        moisture_threshold_low=zone.moisture_threshold_low,
        moisture_threshold_high=zone.moisture_threshold_high,
        schedule=dict(zone.schedule),
    )


def to_location_summary_dto(location: Location) -> LocationSummaryDto:
    if location.id is None:
        raise ValueError("Cannot map an unpersisted Location to LocationSummaryDto")
    return LocationSummaryDto(id=location.id, name=location.name)


def to_location_config_response_dto(
    config: LocationConfig,
) -> LocationConfigResponseDto:
    return LocationConfigResponseDto(
        location=to_location_summary_dto(config.location),
        zones=[to_zone_response_dto(z) for z in config.location.zones],
    )