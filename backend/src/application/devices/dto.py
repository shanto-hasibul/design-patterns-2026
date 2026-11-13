from typing import Any, Literal
from uuid import UUID
from pydantic import BaseModel, Field


class DeviceDto(BaseModel):
    id: UUID
    device_type: str
    role: Literal["sensor", "actuator"] | str
    device_family: str
    display_name: str
    default_config: dict[str, Any]
    zone_id: UUID | None = None
    location_id: UUID | None = None
    sampling_interval_seconds: int = 300
    tracking_enabled: bool = True
    state: str | None = None
    allowed_commands: list[str] = Field(default_factory=list)
    allowed_targets: list[str] = Field(default_factory=list)


class AssignZoneRequestDto(BaseModel):
    zone_id: UUID | None = None


class TransitionActuatorRequestDto(BaseModel):
    target: str