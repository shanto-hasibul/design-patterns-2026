from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest

from src.domain.actuators.ports import PolicyViolationError
from src.infrastructure.adapters.actuators.logging_decorator import (
    LoggingActuatorDecorator,
)
from src.infrastructure.adapters.actuators.max_runtime_decorator import (
    MaxRuntimeActuatorDecorator,
)
from src.infrastructure.adapters.actuators.simulation import (
    SimulationActuatorAdapter,
)


def test_decorator_chain_allows_and_logs_successful_apply() -> None:
    dev_id = uuid4()
    now = datetime(2026, 11, 14, 1, 0, 0, tzinfo=timezone.utc)
    logs: list[dict] = []

    inner = SimulationActuatorAdapter()
    guarded = MaxRuntimeActuatorDecorator(
        inner=inner,
        state_lookup=lambda _id: ("running", now - timedelta(minutes=10)),
        clock=lambda: now,
    )
    decorated = LoggingActuatorDecorator(
        inner=guarded,
        log_writer=lambda d_id, ok, policies, msg: logs.append(
            {
                "device_id": d_id,
                "success": ok,
                "policy_applied": policies,
                "message": msg,
            }
        ),
    )

    decorated.apply(dev_id, "start_pump", {"duration": 30})

    assert len(inner.history) == 1
    assert len(logs) == 1
    assert logs[0]["success"] is True
    assert logs[0]["policy_applied"] == ["logging"]
    assert logs[0]["message"] is None


def test_max_runtime_decorator_blocks_after_30_minutes_and_logs_failure() -> None:
    dev_id = uuid4()
    now = datetime(2026, 11, 14, 1, 0, 0, tzinfo=timezone.utc)
    logs: list[dict] = []

    inner = SimulationActuatorAdapter()
    guarded = MaxRuntimeActuatorDecorator(
        inner=inner,
        state_lookup=lambda _id: ("running", now - timedelta(minutes=30)),
        clock=lambda: now,
    )
    decorated = LoggingActuatorDecorator(
        inner=guarded,
        log_writer=lambda d_id, ok, policies, msg: logs.append(
            {
                "device_id": d_id,
                "success": ok,
                "policy_applied": policies,
                "message": msg,
            }
        ),
    )

    with pytest.raises(PolicyViolationError, match="Max run time exceeded"):
        decorated.apply(dev_id, "start_pump", {})

    # Inner adapter must NOT be reached when maxRunTime blocks
    assert len(inner.history) == 0

    # Logging decorator still persists failure row
    assert len(logs) == 1
    assert logs[0]["device_id"] == dev_id
    assert logs[0]["success"] is False
    assert logs[0]["policy_applied"] == ["maxRunTime", "logging"]
    assert logs[0]["message"] == "Max run time exceeded"