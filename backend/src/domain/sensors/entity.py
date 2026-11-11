from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


@dataclass
class Sensor:
    device_type: str
    display_name: str
    default_config: dict[str, Any] = field(default_factory=dict)
    id: UUID | None = None