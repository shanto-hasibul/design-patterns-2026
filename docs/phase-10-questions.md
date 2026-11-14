# Phase 10 — Command questions

**Pattern / focus:** Command.

**Read first:** [Guide 10](../../materials/guides/10-command.md) · [Requirements](requirements.md)

## A. Pattern

1. State the intent of Command in plain language. What does it mean to **objectify a request**, and what can you do with that object that you cannot do with a bare `actuator.start()` call (queue, audit, undo, history)?

> [!NOTE]
> **_Your Answer***
>
> The intent of the Command pattern is to encapsulate a request—along with its target receiver, action type, and parameters—as a standalone object. **Objectifying a request** turns an ephemeral method call into a first-class data/behavior structure (`StartPumpCommand`, `StopPumpCommand`, `SetLightLevelCommand`) that can be validated before execution, routed through an invoker without conditional branching, queued or scheduled, audited in PostgreSQL (`command_log`), and potentially reversed/undone—none of which is possible with a bare, immediate `actuator.start()` call.

2. Name the participants (**command**, **receiver**, **invoker**, **client**). Who creates the command, who triggers `execute()`, and who actually changes actuator/hardware state?

> [!NOTE]
> **_Your Answer***
>
> - **Command (`Command` base class and `StartPumpCommand`, `StopPumpCommand`, `SetLightLevelCommand` in `domain/commands/`)**: Encapsulates `device_id`, `payload`, `target_state`, and `execute(port)`.
> - **Receiver (`ActuatorPort` stack — `LoggingActuatorDecorator -> MaxRuntimeActuatorDecorator -> SimulationActuatorAdapter`)**: The object that performs the actual policy-guarded hardware/simulation operation when `port.apply(...)` is invoked.
> - **Invoker (`CommandInvoker` in `domain/commands/invoker.py`)**: Accepts a `Command` instance and triggers `command.execute(port)` polymorphically without knowing which concrete command subtype it is running.
> - **Client (`CommandService` / `POST /api/commands` endpoint)**: Resolves the concrete command from the command registry, enforces state guards, passes the command to `CommandInvoker`, updates persisted state, and logs the outcome.

3. If a command supports undo, when must it capture the data needed to reverse the action? Why is “capture **before** mutate” critical?

> [!NOTE]
> **_Your Answer***
>
> A reversible command must capture the prior state and previous configuration parameters (such as the previous light intensity level or prior actuator lifecycle state) **before** mutating the receiver or updating `actuator_states`. Capturing **before** mutating is critical because once `port.apply(...)` and `save_state(...)` overwrite the actuator's settings in memory or PostgreSQL, the original state is permanently lost and cannot be accurately restored if an operator later requests an undo.

## B. This phase of the application

4. Which command types did you implement (for example `start_pump`, `stop_pump`, `set_light_level`)? Why does the HTTP handler create a command and pass it to an **invoker** (or application service) instead of calling the actuator adapter from the router?

> [!NOTE]
> **_Your Answer***
>
> We implemented three concrete command classes registered in `_COMMAND_REGISTRY`: **`StartPumpCommand`** (`"start_pump"`), **`StopPumpCommand`** (`"stop_pump"`), and **`SetLightLevelCommand`** (`"set_light_level"`, defaulting `payload` to `{"level": 1}`). The FastAPI router (`interfaces/api/commands.py`) delegates to `CommandService` and `CommandInvoker` instead of calling an actuator adapter directly so that HTTP routes remain decoupled from concrete actuator implementations, avoid `if command_type == ...` branching, and guarantee that every command consistently passes through Phase 8 state guards, Phase 9 policy decorators, and `command_log` persistence.

5. Walk through the execute path: (1) consult State / `allowed_commands`, (2) if illegal → **rejected**, (3) if legal → decorated `apply`, update `actuator_states`, log **success** or **failed**. Why must a rejected command **not** change actuator state and **not** reach inner `apply`?

> [!NOTE]
> **_Your Answer***
>
> When `CommandService.execute_command()` runs:
> 1. It loads the actuator and instantiates the concrete `Command` from the registry (raising `404` for a missing/non-actuator device and `400` with no log row for an unknown `command_type`).
> 2. It loads the persisted state into `ActuatorContext` and checks `command.command_type in ctx.allowed_commands`. If the command is disallowed in the current state, it writes a `status="rejected"` row to `command_log` (returning HTTP `409 Conflict`) and stops immediately.
> 3. If allowed, `CommandInvoker` invokes `command.execute(port)` against the Phase 9 decorated `ActuatorPort`. If `MaxRuntimeActuatorDecorator` blocks the attempt (`PolicyViolationError`), `command_log` records `status="failed"` (HTTP `200`) and `actuator_states` remains unchanged.
> 4. If `execute(port)` succeeds, `ActuatorContext.transition_to()` updates `actuator_states` (only when `target_state != current_state`), and `command_log` records `status="success"`.
>
> A rejected command must **not** reach `port.apply(...)` or modify `actuator_states` because its precondition failed at the domain state-machine boundary; executing hardware side effects or mutating persisted state on an illegal command would corrupt hardware safety invariants.

6. Distinguish **`rejected`** vs **`failed`** vs **`success`** in `command_log`. Give one greenhouse example of each. Why is “illegal in this state” not the same as “policy or adapter error after the command was accepted”?

> [!NOTE]
> **_Your Answer***
>
> - **`rejected`**: The command is illegal in the actuator's current lifecycle state (`allowed_commands` check fails before execution). *Example*: Sending `stop_pump` while the water pump is already `"idle"`.
> - **`failed`**: The command was legal for the current state and passed into `ActuatorPort.apply()`, but a runtime policy decorator or hardware adapter aborted execution. *Example*: Sending `set_light_level` on a grow light that has been `"running"` for 30+ minutes, causing `MaxRuntimeActuatorDecorator` to raise `PolicyViolationError("Max run time exceeded")`.
> - **`success`**: The command was permitted by state guards, completed `port.apply()` without policy errors, transitioned `actuator_states` if needed, and committed cleanly. *Example*: Sending `start_pump` while `"idle"`, transitioning the pump to `"running"`.
>
> Separating `"rejected"` (pre-execution state violation, HTTP `409`) from `"failed"` (post-acceptance policy/runtime failure, HTTP `200` with `status="failed"`) lets operators distinguish user/UI sequencing mistakes from hardware safety interventions.

7. Why is `command_log` a **different** table from Phase 9 `actuator_execution_log`? What concern does each log record (operator intent vs policy/adapter attempt)?

> [!NOTE]
> **_Your Answer***
>
> `command_log` and `actuator_execution_log` capture two distinct architectural layers:
> - **`command_log` (Phase 10 — Application/Command Intent)**: Records every high-level command request (`command_type`, `payload`, `status` of `success` / `failed` / `rejected`, and `error_message`), including commands that were `rejected` by state guards before ever touching `ActuatorPort`.
> - **`actuator_execution_log` (Phase 9 — Infrastructure/Port Policy Audit)**: Records low-level `ActuatorPort.apply()` invocations and which decorator policies (`["logging"]` or `["maxRunTime", "logging"]`) evaluated or short-circuited the hardware call.

## C. Compare, contrast, and scenarios

8. Contrast Command with **Strategy**. Strategy is an interchangeable **algorithm** (decide / quote). Command is a **side-effectful request** with history. How do they cooperate in this app (Phase 6 recommends; Phase 10 executes)?

> [!NOTE]
> **_Your Answer***
>
> - **Strategy (Phase 6)** encapsulates a pure, side-effect-free decision algorithm (`ConservativeMoistureStrategy` / `AggressiveMoistureStrategy`) that inspects sensor context and returns a `Recommendation` (`irrigate` or `wait`).
> - **Command (Phase 10)** encapsulates a stateful, side-effectful action (`StartPumpCommand`) with audit history in `command_log`.
>
> They cooperate cleanly across a decide-then-act boundary: Strategy evaluates soil moisture and **recommends** `"irrigate"`, and the operator (or an automation orchestrator) then instantiates and dispatches `StartPumpCommand` through `CommandInvoker` to safely **execute** that recommendation.

9. Contrast Command with **State**. Who **triggers** the action, and who **decides whether it is legal**? Why must commands not bypass state guards?

> [!NOTE]
> **_Your Answer***
>
> - **Command** represents the requested action and **triggers** execution via `CommandInvoker.invoke(command, port)`.
> - **State (`ActuatorContext` / `ActuatorState`)** owns the actuator's lifecycle rules and **decides whether that command is legal right now** via `allowed_commands` and `transition_to()`.
>
> Commands must never bypass state guards because doing so would allow unsafe operations—such as starting a pump while it is locked in `"maintenance"` or `"error"`—and would desynchronize `actuator_states` from physical reality.

10. The controls UI should disable actions that are not in `allowed_commands`. Why must the **backend** still reject illegal commands even if the UI is correct? What happens if a classmate’s command calls the raw adapter and skips State and Decorator?

> [!NOTE]
> **_Your Answer***
>
> Disabling buttons in React (`CommandPanel.tsx`) is purely a UX convenience; direct HTTP clients (`curl`, Swagger/Scalar, automated scripts) or stale browser tabs can still submit `POST /api/commands` with an illegal command, so the backend must remain the authoritative enforcer of state guards. If a classmate's command calls `SimulationActuatorAdapter.apply()` directly and skips State and Decorator, illegal state transitions are never blocked, `actuator_states` is never updated, `MaxRuntimeActuatorDecorator` never enforces the 30-minute safety limit, and `actuator_execution_log` misses the audit row.