from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class Zone:
    name: str
    moisture_threshold_low: float
    moisture_threshold_high: float
    schedule: dict[str, Any] = field(default_factory=dict)
    id: UUID | None = None
    location_id: UUID | None = None


@dataclass(frozen=True)
class Location:
    name: str
    zones: tuple[Zone, ...] = field(default_factory=tuple)
    id: UUID | None = None


@dataclass(frozen=True)
class LocationConfig:
    location: Location