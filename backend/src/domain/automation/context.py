from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class ZoneAutomationContext:
    location_id: UUID
    zone_id: UUID
    zone_name: str
    moisture_threshold_low: float
    moisture_threshold_high: float
    latest_moisture: float | None = None
    latest_light: float | None = None


@dataclass(frozen=True)
class LocationAutomationContext:
    location_id: UUID
    location_name: str
    zones: tuple[ZoneAutomationContext, ...]