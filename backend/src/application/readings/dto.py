from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class ReadingDto(BaseModel):
    device_id: UUID
    value: float
    unit: str
    source: str
    recorded_at: datetime


class UpdateSamplingRequestDto(BaseModel):
    sampling_interval_seconds: int
    tracking_enabled: bool