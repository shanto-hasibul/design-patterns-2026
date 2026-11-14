from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class Reading:
    device_id: UUID
    value: float
    unit: str
    source: str
    recorded_at: datetime
    id: UUID | None = None