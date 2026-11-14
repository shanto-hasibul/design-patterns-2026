from typing import Any
from uuid import UUID
from pydantic import BaseModel, Field


class ZoneInputDto(BaseModel):
    name: str
    moisture_threshold_low: float
    moisture_threshold_high: float
    schedule: dict[str, Any] = Field(default_factory=dict)


class CreateLocationConfigRequestDto(BaseModel):
    location_name: str
    zones: list[ZoneInputDto]


class LocationSummaryDto(BaseModel):
    id: UUID
    name: str


class ZoneResponseDto(BaseModel):
    id: UUID
    location_id: UUID
    name: str
    moisture_threshold_low: float
    moisture_threshold_high: float
    schedule: dict[str, Any]


class LocationConfigResponseDto(BaseModel):
    location: LocationSummaryDto
    zones: list[ZoneResponseDto]