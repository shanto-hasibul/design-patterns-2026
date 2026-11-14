from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, Field


class ExecuteCommandRequestDto(BaseModel):
    command_type: str
    device_id: UUID
    payload: dict[str, Any] = Field(default_factory=dict)


class CommandLogResponseDto(BaseModel):
    id: UUID
    command_type: str
    device_id: UUID
    payload: dict[str, Any]
    status: str  # "success" | "failed" | "rejected"
    error_message: str | None = None
    created_at: datetime