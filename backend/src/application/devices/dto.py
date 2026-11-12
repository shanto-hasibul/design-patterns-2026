from typing import Any, Literal
from uuid import UUID
from pydantic import BaseModel


class DeviceDto(BaseModel):
    id: UUID
    device_type: str
    role: Literal["sensor", "actuator"] | str
    device_family: str
    display_name: str
    default_config: dict[str, Any]