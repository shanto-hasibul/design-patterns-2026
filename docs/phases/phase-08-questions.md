# Phase 8 — State questions

**Pattern / focus:** State.

**Read first:** [Guide 08](../../materials/guides/08-state.md) · [Requirements](requirements.md)

## A. Pattern

1. State the intent of the State pattern in plain language. What problem appears when lifecycle is modelled as boolean flags and scattered `if` guards?

> [!NOTE]
> ***Your Answer***
>
> The intent of the State pattern is to allow an object to alter its behavior when its internal lifecycle state changes by encapsulating each state's rules and valid transitions inside dedicated state objects. When an actuator's lifecycle is modeled using boolean flags (`is_running`, `is_error`, `is_maintenance`) and scattered `if/elif` checks across routers and services, impossible flag combinations can occur (such as being both `running` and in `maintenance`), transition guards are duplicated or forgotten, and adding a new lifecycle state requires editing every conditional block in the codebase.

2. Name the participants (**context**, **state interface**, **concrete states**, **client**). How does a successful command lead to a **transition**, and where do **guards** live?

> [!NOTE]
> ***Your Answer***
>
> - **Context (`ActuatorContext` in `domain/actuators/context.py`)**: Holds the `device_id` and a reference to the current `ActuatorState` object, exposing `state`, `allowed_commands`, `allowed_targets`, and `transition_to(target_state)`.
> - **State Interface (`ActuatorState` in `domain/actuators/state.py`)**: Declares `name`, `allowed_targets`, `allowed_commands`, and `transition_to(target)`.
> - **Concrete States (`OffState`, `IdleState`, `RunningState`, `ErrorState`, `MaintenanceState`)**: Each subclass defines the exact legal outgoing transitions and permitted commands for that lifecycle stage.
> - **Client (`ActuatorStateService` in `application/devices/actuator_state_service.py`)**: Loads the persisted state into `ActuatorContext`, invokes `ctx.transition_to(target)`, and persists the updated state via `ActuatorStateRepository`.
>
> All transition **guards** live inside the domain `ActuatorState` hierarchy (`can_transition_to` / `transition_to`). When a valid command or transition target is requested, the active state object verifies that `target` is in its `allowed_targets` tuple and returns the next concrete `ActuatorState` instance to `ActuatorContext`.

3. What is `allowed_commands` (or equivalent) for? Why is exposing “what can I do **now**?” better than letting the UI guess from a raw state string?

> [!NOTE]
> ***Your Answer***
>
> `allowed_commands` is a list of domain command names (such as `["start_pump", "turn_on_light", "power_off", "enter_maintenance"]` when `"idle"`, or `["stop_pump", "turn_off_light"]` when `"running"`) derived directly from the active `ActuatorState`. Exposing *"what can I do now?"* from the backend prevents the React frontend from duplicating state-machine transition tables in TypeScript, ensuring that if backend lifecycle rules evolve, UI controls and Phase 10 command validators automatically stay synchronized with a single source of truth.

## B. This phase of the application

4. Which actuator states did you implement (for example idle, running, error)? Sketch the **legal** transitions (which command or event moves idle → running, running → idle, into error, and out of error).

> [!NOTE]
> ***Your Answer***
>
> We implemented five concrete lifecycle states in `backend/src/domain/actuators/state.py`: **`off`**, **`idle`**, **`running`**, **`error`**, and **`maintenance`**.
>
> Key legal transitions include:
> - **`off` → `idle`** (via `power_on`), `maintenance`, or `error`.
> - **`idle` → `running`** (via `start_pump` / `turn_on_light`), `off` (`power_off`), `maintenance` (`enter_maintenance`), or `error`.
> - **`running` → `idle`** (via `stop_pump` / `turn_off_light`) or `error` (on hardware/execution fault). Note that `running → maintenance` directly is forbidden until stopped.
> - **`error` → `idle`** (via `reset_error`), `maintenance` (`enter_maintenance`), or `off` (`power_off`).
> - **`maintenance` → `idle`** (via `complete_maintenance`), `off`, or `error`.

5. Why is actuator state stored in `actuator_states` (or equivalent) rather than only in process memory? What must still be true after you restart the backend?

> [!NOTE]
> ***Your Answer***
>
> Actuator lifecycle state is persisted in PostgreSQL (`actuator_states` table keyed by `device_id`) rather than held only in FastAPI process memory because physical hardware state is durable across server restarts, container redeploys, and multi-worker instances. After restarting the backend, every actuator must still resolve its exact last persisted state (e.g., `running`, `maintenance`, or `error`) and enforce the same legal transitions without resetting back to `idle`.

6. An **illegal** transition must raise a domain error and **must not** update the database. Why? Which HTTP status is reasonable for that case (400 or 409), and why should the rule live in the domain rather than in React?

> [!NOTE]
> ***Your Answer***
>
> When an illegal transition (such as `running → maintenance` or `error → running`) is attempted, `ActuatorState.transition_to()` raises `IllegalTransitionError` **before** `ActuatorStateService` calls `ActuatorStateRepository.save_state()`, guaranteeing the database never records an invalid state or corrupts audit history. At the API boundary (`POST /api/devices/{id}/transition`), returning **HTTP `409 Conflict`** (or `400 Bad Request`) clearly signals that the requested transition conflicts with the actuator's current lifecycle state. Keeping this rule in the domain rather than only in React ensures direct API callers, background automation jobs, and Phase 10 commands cannot bypass safety guards.

7. Device JSON gains `state` and `allowed_commands`. How does the dashboard use those fields (badges, disable illegal buttons)? How does this prepare **Phase 10 Command**?

> [!NOTE]
> ***Your Answer***
>
> In `DeviceList.tsx`, actuator cards render a prominent `state` badge (`idle`, `running`, `error`, `maintenance`, `off`), display the active `allowed_commands` list, and disable illegal transition buttons with explanatory tooltips explaining why the transition is blocked from the current state. This directly prepares **Phase 10 (Command)** because command objects (`StartPumpCommand`, `StopPumpCommand`, etc.) will consult `allowed_commands` and `ActuatorContext` before executing against the decorated `ActuatorPort`, rejecting commands that are illegal in the actuator's current state.

## C. Compare, contrast, and scenarios

8. Contrast State with **Strategy**. Both look like “context delegates to an object.” Who typically **changes** the active object, and is the variation a **lifecycle** or a **selectable policy**? Give a greenhouse example of each (this phase vs Phase 6).

> [!NOTE]
> ***Your Answer***
>
> - **Strategy (Phase 6)** models a **selectable policy** chosen externally by an operator or configuration—for example, switching a location's irrigation rule between `ConservativeMoistureStrategy` and `AggressiveMoistureStrategy` in `automation_rules`. Strategies do not transition themselves into other strategies.
> - **State (Phase 8)** models an internal **lifecycle** where valid transitions depend on the current state—for example, an actuator moving through `IdleState → RunningState → ErrorState → IdleState` as commands run or faults occur, with each state dictating which transitions are legal next.

9. Contrast State with a pile of booleans (`is_running`, `is_fault`, `is_maintenance`). Why do illegal combinations of flags appear, and how do explicit state objects (or a transition table) prevent that?

> [!NOTE]
> ***Your Answer***
>
> With three independent booleans (`is_running`, `is_fault`, `is_maintenance`), there are $2^3 = 8$ possible combinations, even though states like `is_running=True` and `is_maintenance=True` simultaneously are physically contradictory; partial updates can easily leave stale flags set. Explicit `ActuatorState` objects (and a single `state` string column) make states mutually exclusive by construction—an actuator is in **exactly one** concrete state at any moment, and transitions replace the entire active state object atomically.

10. A classmate puts HTTP status mapping or SQLAlchemy commits **inside** a concrete state class. Another state mutates a flag directly and skips `transition` / `set_state`. Explain why each is a trap.

> [!NOTE]
> ***Your Answer***
>
> - **Putting HTTP status mapping or SQLAlchemy commits inside a concrete state class**: This couples pure domain lifecycle rules to FastAPI and database sessions, making state transitions impossible to unit-test without mocking HTTP/ORM infrastructure and risking partial database commits mid-transition.
> - **Mutating a state field directly and skipping `transition_to()`**: Bypassing `ActuatorContext.transition_to()` circumvents the state machine's guard checks (`allowed_targets`), allowing illegal jumps (such as `off → running` or `error → running`) and leaving `allowed_commands` out of sync with the actual state.