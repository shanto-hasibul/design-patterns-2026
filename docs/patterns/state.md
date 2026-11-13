# State Pattern — Actuator Lifecycle Management

## Problem
Actuators (`water_pump`, `grow_light`) move through operational lifecycle states (`off`, `idle`, `running`, `error`, `maintenance`). Certain commands and transitions are physically unsafe or invalid depending on the actuator's current state—for example, starting a pump directly while it is in `error` or `maintenance` without resetting/clearing it first, or entering `maintenance` directly while `running` without stopping it first. Encoding `if state == "idle": ...` checks in FastAPI route handlers or React components duplicates transition rules and risks persisting invalid states.

## Solution
We model the actuator lifecycle using the **State** pattern (`backend/src/domain/actuators/state.py` and `context.py`) backed by PostgreSQL persistence (`actuator_states` table):
1. **State Objects (`OffState`, `IdleState`, `RunningState`, `ErrorState`, `MaintenanceState`)**: Each concrete subclass of `ActuatorState` encapsulates its own legal outgoing `allowed_targets` and `allowed_commands`.
2. **Domain Context (`ActuatorContext`)**: Wraps the current `ActuatorState` for a `device_id`. Calling `ctx.transition_to(target)` delegates validation to the active state object and raises `IllegalTransitionError` if the edge is forbidden.
3. **Persistence & Seeding (`actuator_states` table)**: Stores `(device_id PK, state, updated_at)` in PostgreSQL so state survives backend restarts. Existing actuators are seeded to `'idle'` in the Alembic migration (`f6c0d451a856_actuator_states.py`), and newly created actuators are initialized to `'idle'` upon persistence.
4. **API Exposure**: `DeviceDto` includes `state`, `allowed_commands`, and `allowed_targets`, and `POST /api/devices/{device_id}/transition` enforces guarded transitions (returning HTTP `409 Conflict` on illegal transitions).

## Legal Transition Table

| Current State | Legal Next States (`allowed_targets`) | Allowed Commands (`allowed_commands`) |
| :--- | :--- | :--- |
| **`off`** | `idle`, `maintenance`, `error` | `power_on`, `enter_maintenance` |
| **`idle`** | `running`, `off`, `maintenance`, `error` | `start_pump`, `turn_on_light`, `power_off`, `enter_maintenance` |
| **`running`** | `idle`, `error` | `stop_pump`, `turn_off_light` |
| **`error`** | `idle`, `maintenance`, `off` | `reset_error`, `enter_maintenance`, `power_off` |
| **`maintenance`** | `idle`, `off`, `error` | `complete_maintenance`, `power_off` |

## Where to Look in Code
- **Domain States & Context**: `backend/src/domain/actuators/state.py`, `backend/src/domain/actuators/context.py`
- **Application Service & DTOs**: `backend/src/application/devices/actuator_state_service.py`, `dto.py`, `mappers.py`
- **Persistence & Migration**: `backend/src/infrastructure/persistence/actuator_state_repository.py`, `models.py`, `backend/alembic/versions/f6c0d451a856_actuator_states.py`
- **API Endpoint**: `backend/src/interfaces/api/devices.py` (`POST /api/devices/{device_id}/transition`)
- **Frontend Badges & Controls**: `frontend/src/components/devices/DeviceList.tsx`# State Pattern — Actuator Lifecycle Management

## Problem
Actuators (`water_pump`, `grow_light`) move through operational lifecycle states (`off`, `idle`, `running`, `error`, `maintenance`). Certain commands and transitions are physically unsafe or invalid depending on the actuator's current state—for example, starting a pump directly while it is in `error` or `maintenance` without resetting/clearing it first, or entering `maintenance` directly while `running` without stopping it first. Encoding `if state == "idle": ...` checks in FastAPI route handlers or React components duplicates transition rules and risks persisting invalid states.

## Solution
We model the actuator lifecycle using the **State** pattern (`backend/src/domain/actuators/state.py` and `context.py`) backed by PostgreSQL persistence (`actuator_states` table):
1. **State Objects (`OffState`, `IdleState`, `RunningState`, `ErrorState`, `MaintenanceState`)**: Each concrete subclass of `ActuatorState` encapsulates its own legal outgoing `allowed_targets` and `allowed_commands`.
2. **Domain Context (`ActuatorContext`)**: Wraps the current `ActuatorState` for a `device_id`. Calling `ctx.transition_to(target)` delegates validation to the active state object and raises `IllegalTransitionError` if the edge is forbidden.
3. **Persistence & Seeding (`actuator_states` table)**: Stores `(device_id PK, state, updated_at)` in PostgreSQL so state survives backend restarts. Existing actuators are seeded to `'idle'` in the Alembic migration (`f6c0d451a856_actuator_states.py`), and newly created actuators are initialized to `'idle'` upon persistence.
4. **API Exposure**: `DeviceDto` includes `state`, `allowed_commands`, and `allowed_targets`, and `POST /api/devices/{device_id}/transition` enforces guarded transitions (returning HTTP `409 Conflict` on illegal transitions).

## Legal Transition Table

| Current State | Legal Next States (`allowed_targets`) | Allowed Commands (`allowed_commands`) |
| :--- | :--- | :--- |
| **`off`** | `idle`, `maintenance`, `error` | `power_on`, `enter_maintenance` |
| **`idle`** | `running`, `off`, `maintenance`, `error` | `start_pump`, `turn_on_light`, `power_off`, `enter_maintenance` |
| **`running`** | `idle`, `error` | `stop_pump`, `turn_off_light` |
| **`error`** | `idle`, `maintenance`, `off` | `reset_error`, `enter_maintenance`, `power_off` |
| **`maintenance`** | `idle`, `off`, `error` | `complete_maintenance`, `power_off` |

## Where to Look in Code
- **Domain States & Context**: `backend/src/domain/actuators/state.py`, `backend/src/domain/actuators/context.py`
- **Application Service & DTOs**: `backend/src/application/devices/actuator_state_service.py`, `dto.py`, `mappers.py`
- **Persistence & Migration**: `backend/src/infrastructure/persistence/actuator_state_repository.py`, `models.py`, `backend/alembic/versions/f6c0d451a856_actuator_states.py`
- **API Endpoint**: `backend/src/interfaces/api/devices.py` (`POST /api/devices/{device_id}/transition`)
- **Frontend Badges & Controls**: `frontend/src/components/devices/DeviceList.tsx`