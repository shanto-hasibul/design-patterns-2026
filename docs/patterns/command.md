# Command Pattern — Audited Actuator Commands

## Intent
The **Command** pattern encapsulates each actuator request (`StartPumpCommand`, `StopPumpCommand`, `SetLightLevelCommand`) as a standalone domain object implementing `execute(port: ActuatorPort)`. This decouples the HTTP router (`POST /api/commands`) from concrete actuator operations, centralizes state-guard checks and execution logging, and creates an auditable history in PostgreSQL (`command_log`).

## Invoker & Execution Pipeline
1. **Command Registry & Invoker (`domain/commands/invoker.py`)**: `build_command()` maps `command_type` strings to concrete `Command` classes without `if/elif` chains in the router, and `CommandInvoker.invoke(command, port)` delegates execution polymorphically via `command.execute(port)`.
2. **Application Service (`application/commands/service.py`)**:
   - Verifies that `device_id` exists and has `role == "actuator"` (else `404`).
   - Instantiates the concrete `Command` (unknown `command_type` raises `UnknownCommandError` -> `400` with no `command_log` row written).
   - Consults `ActuatorContext.allowed_commands` for the persisted state (Phase 8). If disallowed, logs `status="rejected"` (`409 Conflict`) and leaves `actuator_states` unchanged.
   - Dispatches the command through `CommandInvoker` against the Phase 9 decorated `ActuatorPort` stack (`Logging -> MaxRuntime -> SimulationActuatorAdapter`). If `MaxRuntimeActuatorDecorator` blocks the command, `command_log` records `status="failed"` (`200 OK`) and leaves `actuator_states` unchanged.
   - On success, transitions `ActuatorContext` only if `target_state` differs from the current state (for example, `set_light_level` on an already `running` light stays `running`) and logs `status="success"`.

## Why Use Command Instead of Calling `ActuatorPort` Directly from the Router
Calling `ActuatorPort.apply()` directly from FastAPI routes would scatter state-transition checks, payload normalization (such as defaulting `set_light_level` to `{"level": 1}`), and `command_log` persistence across HTTP handlers, making it impossible to queue, replay, or audit commands uniformly from both REST endpoints and future automation workflows.

## Where to Look in Code
- **Domain Commands & Invoker**: `backend/src/domain/commands/base.py`, `pump.py`, `light.py`, `invoker.py`
- **Application Service & DTOs**: `backend/src/application/commands/service.py`, `dto.py`
- **Persistence & Migration**: `backend/src/infrastructure/persistence/command_log_repository.py`, `models.py`, `backend/alembic/versions/b2e3f673c078_command_log.py`
- **API Endpoints**: `backend/src/interfaces/api/commands.py`
- **Frontend Panel**: `frontend/src/components/commands/CommandPanel.tsx`