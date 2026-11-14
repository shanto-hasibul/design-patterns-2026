from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class DomainEvent:
    event_type: str
    device_id: UUID | None = None
    location_id: UUID | None = None
    zone_id: UUID | None = None
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_payload(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "device_id": str(self.device_id) if self.device_id else None,
            "location_id": str(self.location_id) if self.location_id else None,
            "zone_id": str(self.zone_id) if self.zone_id else None,
            "occurred_at": self.occurred_at.isoformat(),
        }


@dataclass(frozen=True)
class ReadingCreated(DomainEvent):
    value: float = 0.0
    unit: str = ""
    source: str = ""
    recorded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: str = field(default="reading.created", init=False)

    def to_payload(self) -> dict[str, Any]:
        base = super().to_payload()
        base.update(
            {
                "value": self.value,
                "unit": self.unit,
                "source": self.source,
                "recorded_at": self.recorded_at.isoformat(),
            }
        )
        return base


@dataclass(frozen=True)
class ThresholdCrossed(DomainEvent):
    moisture: float = 0.0
    threshold_low: float = 0.30
    message: str = ""
    event_type: str = field(default="threshold.crossed", init=False)

    def to_payload(self) -> dict[str, Any]:
        base = super().to_payload()
        base.update(
            {
                "moisture": self.moisture,
                "threshold_low": self.threshold_low,
                "message": self.message,
            }
        )
        return base


@dataclass(frozen=True)
class CommandCompleted(DomainEvent):
    command_type: str = ""
    status: str = "success"
    error_message: str | None = None
    event_type: str = field(default="command.completed", init=False)


@dataclass(frozen=True)
class CommandFailed(DomainEvent):
    command_type: str = ""
    status: str = "failed"
    error_message: str = ""
    event_type: str = field(default="command.failed", init=False)


@dataclass(frozen=True)
class ActuatorStateChanged(DomainEvent):
    previous_state: str = ""
    new_state: str = ""
    event_type: str = field(default="actuator.state_changed", init=False)