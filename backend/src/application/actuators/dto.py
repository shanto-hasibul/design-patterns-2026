from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, Field


class ActuatorExecutionDto(BaseModel):
    id: UUID
    device_id: UUID
    success: bool
    policy_applied: list[str]
    message: str | None = None
    created_at: datetime


class ApplyActuatorRequestDto(BaseModel):
    command: str
    payload: dict[str, Any] = Field(default_factory=dict)