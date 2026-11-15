from typing import Any

from src.application.realtime.connection_manager import (
    DashboardConnectionManager,
    dashboard_ws_manager,
)
from src.domain.events.bus import EventSubscriber
from src.domain.events.events import (
    ActuatorStateChanged,
    CommandFailed,
    DomainEvent,
    ReadingCreated,
    ThresholdCrossed,
)


class WebSocketBroadcastSubscriber(EventSubscriber):
    """Observer subscriber that forwards domain events to connected dashboard WebSocket clients."""

    def __init__(
        self,
        manager: DashboardConnectionManager = dashboard_ws_manager,
    ) -> None:
        self._manager = manager
        self.sent_envelopes: list[dict[str, Any]] = []

    def handle(self, event: DomainEvent) -> None:
        envelopes = self._to_envelopes(event)
        for env in envelopes:
            self.sent_envelopes.append(env)
            self._manager.broadcast_threadsafe(env)

    @staticmethod
    def _to_envelopes(event: DomainEvent) -> list[dict[str, Any]]:
        if isinstance(event, ReadingCreated):
            return [
                {
                    "type": "reading.created",
                    "payload": event.to_payload(),
                }
            ]

        if isinstance(event, ActuatorStateChanged):
            payload = event.to_payload()
            payload.update(
                {
                    "previous_state": event.previous_state,
                    "new_state": event.new_state,
                }
            )
            return [
                {
                    "type": "actuator.state_changed",
                    "payload": payload,
                }
            ]

        if isinstance(event, ThresholdCrossed):
            return [
                {
                    "type": "alert.created",
                    "payload": event.to_payload(),
                }
            ]

        if isinstance(event, CommandFailed):
            payload = event.to_payload()
            payload.update(
                {
                    "command_type": event.command_type,
                    "status": event.status,
                    "error_message": event.error_message,
                }
            )
            return [
                {
                    "type": "alert.created",
                    "payload": payload,
                }
            ]

        return []