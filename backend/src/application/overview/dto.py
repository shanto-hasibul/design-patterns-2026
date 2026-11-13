from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class OverviewLocationDto(BaseModel):
    id: UUID
    name: str


class OverviewDeviceCountsDto(BaseModel):
    sensor: int
    actuator: int


class OverviewZoneDeviceDto(BaseModel):
    id: UUID
    device_type: str
    role: str
    display_name: str


class OverviewLatestReadingDto(BaseModel):
    device_id: UUID
    value: float
    unit: str
    recorded_at: datetime
    tracking_enabled: bool
    sampling_interval_seconds: int


class OverviewZoneDto(BaseModel):
    id: UUID
    name: str
    moisture_threshold_low: float
    moisture_threshold_high: float
    devices: list[OverviewZoneDeviceDto]
    latest_readings: list[OverviewLatestReadingDto]


class OverviewRecommendationDto(BaseModel):
    action: str
    reason: str


class LocationOverviewDto(BaseModel):
    location: OverviewLocationDto
    device_counts: OverviewDeviceCountsDto
    zones: list[OverviewZoneDto]
    strategy_key: str | None = None
    last_recommendation: OverviewRecommendationDto | None = None