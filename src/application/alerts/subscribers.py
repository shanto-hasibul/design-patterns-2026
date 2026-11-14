from collections import Counter
from collections.abc import Callable
from uuid import UUID

from src.domain.events.bus import EventBus, EventSubscriber
from src.domain.events.events import (
    ActuatorStateChanged,
    CommandFailed,
    DomainEvent,
    ReadingCreated,
    ThresholdCrossed,
)
from src.infrastructure.persistence.alert_repository import AlertRepository

DEFAULT_LOW_MOISTURE_THRESHOLD = 0.30


class AlertPersistenceSubscriber(EventSubscriber):
    """Subscribes to domain events and persists actionable alerts into the alerts table."""

    def __init__(
        self,
        alert_repo: AlertRepository,
        zone_threshold_lookup: Callable[[UUID], float | None] | None = None,
    ) -> None:
        self._alert_repo = alert_repo
        self._zone_threshold_lookup = (
            zone_threshold_lookup or alert_repo.get_zone_moisture_low
        )

    def handle(self, event: DomainEvent) -> None:
        if isinstance(event, ThresholdCrossed):
            self._alert_repo.create_alert(
                event_type=event.event_type,
                message=event.message
                or f"Low soil moisture ({event.moisture:.2f}) crossed threshold ({event.threshold_low:.2f}).",
                severity="warning",
                location_id=event.location_id,
                zone_id=event.zone_id,
                device_id=event.device_id,
            )
            return

        if isinstance(event, ReadingCreated) and event.unit.lower() == "vwc":
            threshold = DEFAULT_LOW_MOISTURE_THRESHOLD
            if event.zone_id is not None:
                zone_low = self._zone_threshold_lookup(event.zone_id)
                if zone_low is not None:
                    threshold = zone_low

            if event.value < threshold:
                self._alert_repo.create_alert(
                    event_type="threshold.crossed",
                    message=(
                        f"Low moisture reading ({event.value:.2f} {event.unit}) "
                        f"below threshold ({threshold:.2f})."
                    ),
                    severity="warning",
                    location_id=event.location_id,
                    zone_id=event.zone_id,
                    device_id=event.device_id,
                )
            return

        if isinstance(event, CommandFailed):
            self._alert_repo.create_alert(
                event_type=event.event_type,
                message=f"Command '{event.command_type}' {event.status}: {event.error_message}",
                severity="critical" if event.status == "failed" else "warning",
                location_id=event.location_id,
                zone_id=event.zone_id,
                device_id=event.device_id,
            )
            return

        if isinstance(event, ActuatorStateChanged) and event.new_state == "error":
            self._alert_repo.create_alert(
                event_type=event.event_type,
                message=f"Actuator entered ERROR state (from '{event.previous_state}').",
                severity="critical",
                location_id=event.location_id,
                zone_id=event.zone_id,
                device_id=event.device_id,
            )


class MetricsSubscriber(EventSubscriber):
    """In-memory counter subscriber (no database table required)."""

    def __init__(self) -> None:
        self.counts: Counter[str] = Counter()

    def handle(self, event: DomainEvent) -> None:
        self.counts[event.event_type] += 1


def build_default_event_bus(alert_repo: AlertRepository) -> EventBus:
    bus = EventBus()
    bus.subscribe(AlertPersistenceSubscriber(alert_repo))
    bus.subscribe(MetricsSubscriber())
    return bus