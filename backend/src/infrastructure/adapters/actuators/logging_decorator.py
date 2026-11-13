from collections.abc import Callable
from typing import Any
from uuid import UUID

from src.domain.actuators.ports import ActuatorPort, PolicyViolationError


class LoggingActuatorDecorator(ActuatorPort):
    """Outermost decorator that persists every execution attempt (success or policy failure)."""

    def __init__(
        self,
        inner: ActuatorPort,
        log_writer: Callable[[UUID, bool, list[str], str | None], Any],
    ) -> None:
        self._inner = inner
        self._log_writer = log_writer
        self.last_logged: Any = None

    def apply(
        self,
        device_id: UUID,
        command: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        try:
            self._inner.apply(device_id, command, payload or {})
        except PolicyViolationError as exc:
            self.last_logged = self._log_writer(
                device_id,
                False,
                [exc.policy_name, "logging"],
                exc.message,
            )
            raise

        self.last_logged = self._log_writer(
            device_id,
            True,
            ["logging"],
            None,
        )