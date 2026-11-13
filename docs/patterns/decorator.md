# Decorator Pattern — Actuator Port Policies & Execution Logging

## Problem
Executing commands on greenhouse actuators (`SimulationActuatorAdapter` or future physical drivers) requires cross-cutting operational policies:
1. **Safety / Max Run-Time Guard**: Prevent running an actuator continuously for 30 minutes or more (`state == "running"` and `now - actuator_states.updated_at >= 30 minutes`).
2. **Audit Execution Logging**: Persist every execution attempt—both completed commands and policy-blocked attempts—into `actuator_execution_log` so operators can inspect outcomes in the dashboard.

Hardcoding these checks inside FastAPI routes or subclassing every actuator driver (`LoggedMaxRuntimeSimulationPump`, `LoggedMaxRuntimeMqttPump`, etc.) causes combinatorial class explosion.

## Solution & Composition Order
We apply the **Decorator** pattern (`backend/src/infrastructure/adapters/actuators/`):
1. **Component Interface (`ActuatorPort` in `domain/actuators/ports.py`)**: Declares `apply(device_id: UUID, command: str, payload: dict) -> None`.
2. **Concrete Component (`SimulationActuatorAdapter`)**: The innermost adapter that performs the core actuator action.
3. **Decorators**:
   - **`MaxRuntimeActuatorDecorator`**: Checks persisted `actuator_states` (`state` and `updated_at`). If the actuator has been `running` for at least 30 minutes, it raises `PolicyViolationError("maxRunTime", "Max run time exceeded")` **without** calling the inner adapter.
   - **`LoggingActuatorDecorator`**: Outermost wrapper that catches `PolicyViolationError` (persisting `success=False`, `policy_applied=["maxRunTime", "logging"]`, `message="Max run time exceeded"`) or logs successful completion (`success=True`, `policy_applied=["logging"]`, `message=None`) into `actuator_execution_log`.

Composition order in `build_decorated_actuator_port()`:
LoggingActuatorDecorator -> MaxRuntimeActuatorDecorator -> SimulationActuatorAdapter

## Decorator vs. Inheritance
- **Inheritance** creates static subclasses at compile/import time; combining logging, max-runtime, and future retry/rate-limit policies across multiple drivers would require 2^N subclasses.
- **Decorator** wraps any `ActuatorPort` at runtime via composition, keeping every wrapper small, single-purpose, and transparent to callers.

## Where to Look in Code
- **Port & Policy Error**: `backend/src/domain/actuators/ports.py`
- **Innermost Adapter & Decorators**: `backend/src/infrastructure/adapters/actuators/simulation.py`, `max_runtime_decorator.py`, `logging_decorator.py`
- **Service & DTOs**: `backend/src/application/actuators/service.py`, `dto.py`
- **Persistence & Migration**: `backend/src/infrastructure/persistence/execution_log_repository.py`, `models.py`, `backend/alembic/versions/a1d2e562b967_actuator_execution_log.py`
- **REST Endpoint & UI**: `backend/src/interfaces/api/actuators.py`, `frontend/src/components/actuators/ExecutionLog.tsx`