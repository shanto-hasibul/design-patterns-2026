# Phase 9 — Decorator questions

**Pattern / focus:** Decorator.

**Read first:** [Guide 09](../../materials/guides/09-decorator.md) · [Requirements](requirements.md)

## A. Pattern

1. State the intent of Decorator in plain language. Why is stacking wrappers a flexible alternative to a combinatorial explosion of subclasses (`LoggingRetryMaxRuntimeActuator`, …)?

> [!NOTE]
> ***Your Answer***
>
> The intent of the Decorator pattern is to attach additional responsibilities or policies (such as execution logging and max-runtime safety guards) to an object dynamically by wrapping it in layers that share the exact same interface. Stacking decorators via composition is far more flexible than inheritance because $N$ policies across $M$ actuator drivers would otherwise require $M \times 2^N$ rigid subclasses (`LoggingSimulationActuator`, `MaxRuntimeSimulationActuator`, `LoggingMaxRuntimeSimulationActuator`, etc.), whereas decorators let us mix, reorder, or omit wrappers at runtime without touching the underlying driver.

2. Name the participants (**component**, **concrete component**, **decorator**, **concrete decorators**). What interface does every decorator present to the caller, and why must that match the wrapped component?

> [!NOTE]
> ***Your Answer***
>
> - **Component (`ActuatorPort` in `domain/actuators/ports.py`)**: Declares the unified `apply(device_id: UUID, command: str, payload: dict) -> None` contract.
> - **Concrete Component (`SimulationActuatorAdapter` in `infrastructure/adapters/actuators/simulation.py`)**: The innermost actuator driver that performs the actual execution.
> - **Decorator / Concrete Decorators (`MaxRuntimeActuatorDecorator` and `LoggingActuatorDecorator`)**: Both implement `ActuatorPort`, hold a reference to an inner `ActuatorPort`, and add cross-cutting behavior before or after delegating to `self._inner.apply(...)`.
>
> Every decorator presents the exact **`ActuatorPort`** interface to the caller. Matching that interface guarantees transparency (Liskov Substitution): callers like `ActuatorExecutionService` and Phase 10 commands interact with `ActuatorPort` identically regardless of how many policy wrappers are stacked around the core adapter.

3. **Order matters.** Using logging and retry (or logging and max-run-time) as an example, explain how wrapping A around B can change what you observe compared with wrapping B around A.

> [!NOTE]
> ***Your Answer***
>
> Wrapping `LoggingActuatorDecorator` **outside** `MaxRuntimeActuatorDecorator` (`Logging -> MaxRuntime -> SimulationActuatorAdapter`) ensures that when `MaxRuntimeActuatorDecorator` blocks an overdue actuator and raises `PolicyViolationError`, the outer logging wrapper catches the exception and records a row with `success=false`, `policy_applied=["maxRunTime", "logging"]`, and `message="Max run time exceeded"`. If the order were reversed (`MaxRuntime -> Logging -> SimulationActuatorAdapter`), `MaxRuntime` would short-circuit and raise *before* reaching the inner `Logging` wrapper, leaving zero audit trail in `actuator_execution_log` whenever a safety block occurs.

## B. This phase of the application

4. What is `ActuatorPort` here, and which **at least two** decorators did you stack around the real adapter (for example logging and max run-time)? Where is the chain wired (composition root / factory), and why not inside the HTTP router?

> [!NOTE]
> ***Your Answer***
>
> `ActuatorPort` is the domain interface defining `apply(device_id, command, payload) -> None`. Around the innermost `SimulationActuatorAdapter`, we stacked two concrete decorators:
> 1. **`MaxRuntimeActuatorDecorator`** (inner policy guard enforcing the 30-minute continuous runtime limit).
> 2. **`LoggingActuatorDecorator`** (outermost audit logger writing every attempt to `actuator_execution_log`).
>
> The chain is wired in the application-layer factory `build_decorated_actuator_port()` inside `backend/src/application/actuators/service.py` rather than inside the FastAPI router (`interfaces/api/actuators.py`) so that HTTP handlers stay thin and any entry point—REST routes, Phase 10 commands, or background automation—automatically receives the exact same policy-wrapped port.

5. Max run-time can **short-circuit**: the inner adapter is never called. Why must a blocked attempt still produce a row in `actuator_execution_log` with `success=false` and the policy named in `policy_applied`?

> [!NOTE]
> ***Your Answer***
>
> Even when `MaxRuntimeActuatorDecorator` short-circuits and prevents the inner `SimulationActuatorAdapter` from running, persisting a row with `success=false`, `policy_applied=["maxRunTime", "logging"]`, and `message="Max run time exceeded"` provides a complete operational audit trail. Operators need visibility into why an irrigation or lighting command did not fire—proving that the safety guard actively intervened rather than the command silently vanishing.

6. How does max run-time know the actuator has been running too long (for example `actuator_states.updated_at` from Phase 8)? Why is that data from **State**, not something the decorator should invent as a second lifecycle?

> [!NOTE]
> ***Your Answer***
>
> `MaxRuntimeActuatorDecorator` queries the persisted lifecycle record from Phase 8 (`ActuatorStateRepository.get_state_record(device_id)`), checking whether `state == "running"` and whether `now - actuator_states.updated_at >= 30 minutes`. Relying on Phase 8's `actuator_states` as the single source of truth avoids inventing a conflicting second lifecycle tracker inside the decorator, ensuring runtime limits stay consistent with actual persisted actuator transitions across server restarts.

7. `GET /api/actuators/executions` feeds the dashboard execution log. Why persist attempts in the database instead of only printing to stdout? What should the UI show after a blocked attempt and a refresh?

> [!NOTE]
> ***Your Answer***
>
> Persisting execution attempts in PostgreSQL (`actuator_execution_log`) rather than only printing to `stdout` makes audit history durable across container restarts, queryable via `GET /api/actuators/executions`, and visible to operators in the web UI. After a blocked attempt and a page refresh, `ExecutionLog.tsx` displays the persisted row marked `BLOCKED` (`success=false`), listing `maxRunTime, logging` under policies and `Max run time exceeded` in the message column.

## C. Compare, contrast, and scenarios

8. Contrast Decorator with **Adapter**. Both wrap. One **keeps** the interface and **adds** behaviour; the other **changes** the interface and **translates**. Which is which in this greenhouse (Phase 9 vs Phase 5)?

> [!NOTE]
> ***Your Answer***
>
> - **Adapter (Phase 5)** **changes** an incompatible interface and **translates** data formats—for example, `VendorStubSensorAdapter` and `MqttSensorAdapter` translate proprietary packets and MQTT dicts into normalized `Reading` objects implementing `SensorPort`.
> - **Decorator (Phase 9)** **keeps** the exact same interface (`ActuatorPort`) and **adds** cross-cutting behavior—`MaxRuntimeActuatorDecorator` and `LoggingActuatorDecorator` wrap `SimulationActuatorAdapter` while still exposing `ActuatorPort.apply(...)`.

9. Contrast Decorator with **inheritance** of combined policies. How does composition let you add or remove a policy without a new subclass for every combination?

> [!NOTE]
> ***Your Answer***
>
> With inheritance, adding a new policy (such as rate-limiting or dry-run mode) requires creating new subclasses for every combination of existing policies and actuator drivers. With Decorator composition, each policy is an independent wrapper accepting an `ActuatorPort` in `__init__`; you can add, remove, or reorder policies simply by changing how objects are nested in `build_decorated_actuator_port()` without creating any new subclasses.

10. A classmate’s decorator changes the method signature “a little” (extra required argument, different return type). Another ignores wrap order and cannot explain whether logging runs once per logical call or per inner attempt. Explain why each is a trap.

> [!NOTE]
> ***Your Answer***
>
> - **Changing the method signature in a decorator**: Breaks substitutability (`ActuatorPort`), forcing callers to type-check which wrapper they hold and destroying the ability to stack decorators interchangeably.
> - **Ignoring wrap order**: Leads to subtle observability bugs—for example, putting `Logging` inside `MaxRuntime` misses blocked attempts altogether, or putting `Logging` inside a `Retry` decorator logs three separate rows for one logical command instead of one outer audit entry.