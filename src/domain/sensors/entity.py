from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class Sensor:
    device_type: str
    display_name: str
    default_config: dict[str, Any] = field(default_factory=dict)
    id: UUID | None = None
    sampling_interval_seconds: int = 300
    tracking_enabled: bool = True
    zone_id: UUID | None = None
    location_id: UUID | None = None