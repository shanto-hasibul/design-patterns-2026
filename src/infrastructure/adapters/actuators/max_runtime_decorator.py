from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from src.domain.actuators.ports import ActuatorPort, PolicyViolationError

MAX_RUNTIME_THRESHOLD = timedelta(minutes=30)


class MaxRuntimeActuatorDecorator(ActuatorPort):
    """Blocks execution when the actuator has been in 'running' state for at least 30 minutes."""

    def __init__(
        self,
        inner: ActuatorPort,
        state_lookup: Callable[[UUID], tuple[str, datetime | None]],
        clock: Callable[[], datetime] | None = None,
        max_duration: timedelta = MAX_RUNTIME_THRESHOLD,
    ) -> None:
        self._inner = inner
        self._state_lookup = state_lookup
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._max_duration = max_duration

    def apply(
        self,
        device_id: UUID,
        command: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        state_name, updated_at = self._state_lookup(device_id)
        if state_name == "running" and updated_at is not None:
            now = self._clock()
            if now.tzinfo is None:
                now = now.replace(tzinfo=timezone.utc)
            last_updated = (
                updated_at.replace(tzinfo=timezone.utc)
                if updated_at.tzinfo is None
                else updated_at
            )
            if (now - last_updated) >= self._max_duration:
                raise PolicyViolationError(
                    policy_name="maxRunTime",
                    message="Max run time exceeded",
                )

        self._inner.apply(device_id, command, payload or {})