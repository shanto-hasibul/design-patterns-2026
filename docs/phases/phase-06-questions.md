# Phase 6 — Strategy questions

**Pattern / focus:** Strategy.

**Read first:** [Guide 06](../../materials/guides/06-strategy.md) · [Requirements](requirements.md)

## A. Pattern

1. State the intent of Strategy in plain language. How does the **context** use a strategy, and why must “choose which algorithm” stay separate from “run the algorithm”?

> [!NOTE]
> ***Your Answer***
>
> The intent of the Strategy pattern is to define a family of interchangeable algorithms, encapsulate each one in its own class behind a shared interface, and allow the active algorithm to vary independently from the client that uses it. The **context** (`LocationAutomationContext` assembled for `AutomationService`) supplies the domain inputs (latest zone moisture readings and zone threshold bounds) to the selected strategy's `decide(context)` method. Keeping *"choose which algorithm"* (`get_automation_strategy(strategy_key)` resolved from persisted `automation_rules`) separate from *"run the algorithm"* (`strategy.decide(context)`) prevents conditional branching from polluting evaluation logic and lets operators swap policies at runtime without changing how evaluation is orchestrated.

2. Name the participants (**strategy**, **concrete strategies**, **context**, **client**). What goes wrong when all policies live as `if/elif` inside the context (or inside an HTTP router)?

> [!NOTE]
> ***Your Answer***
>
> - **Strategy (`AutomationStrategy` in `domain/automation/strategy.py`)**: Declares the common `key` property and `decide(context) -> Recommendation` interface.
> - **Concrete Strategies (`ConservativeMoistureStrategy`, `AggressiveMoistureStrategy`)**: Implement distinct irrigation decision algorithms using the same input context.
> - **Context (`LocationAutomationContext` / `ZoneAutomationContext` in `domain/automation/context.py`)**: Holds the immutable snapshot of a location's zones, their VWC thresholds, and each zone's latest sensor reading.
> - **Client (`AutomationService` in `application/automation/service.py`)**: Loads the location context and persisted strategy key, resolves the concrete `AutomationStrategy`, and invokes `decide(context)`.
>
> When all policies live inside `if/elif` chains in a router or context object, every new irrigation policy forces edits to core orchestration or HTTP code (violating the Open/Closed Principle), makes unit-testing individual algorithms in isolation harder, and mixes HTTP transport concerns with domain decision math.

3. When should you use Strategy, and when should you skip it (one algorithm only; or the variation is a **lifecycle mode** rather than a chosen policy)?

> [!NOTE]
> ***Your Answer***
>
> You should use Strategy when an application needs multiple interchangeable algorithms for the same task—such as choosing between `"conservative"` and `"aggressive"` irrigation policies per location—and wants to switch or extend those policies cleanly without modifying callers. You should skip Strategy when there is only one fixed rule with no realistic variants (over-engineering), or when the behavioral variation represents internal **lifecycle states** that transition automatically based on system events (which calls for the **State** pattern instead).

## B. This phase of the application

4. In this lab, what does a strategy’s `decide(context)` return (action + reason)? Give a concrete difference you implemented (or were required to implement) between **conservative** and **aggressive** on the **same** moisture reading and zone thresholds.

> [!NOTE]
> ***Your Answer***
>
> In this lab, `decide(context)` returns a `Recommendation` containing `location_id`, `strategy_key`, `action` (`"irrigate"` or `"wait"`), a human-readable `reason`, an optional `score`, and per-zone `ZoneRecommendation` details.
>
> On the exact same zone context—for example, `moisture_threshold_low = 0.30`, `moisture_threshold_high = 0.70`, and `latest_moisture = 0.42`:
> - **`ConservativeMoistureStrategy`** compares `0.42` against `moisture_threshold_low` (`0.30`). Because `0.42 >= 0.30`, it recommends **`"wait"`** to conserve water.
> - **`AggressiveMoistureStrategy`** compares `0.42` against the midpoint `(0.30 + 0.70) / 2 = 0.50`. Because `0.42 < 0.50`, it recommends **`"irrigate"`** proactively to keep soil moisture in the upper half of the target band.

5. Where do the numbers in `LocationAutomationContext` (or your equivalent) come from? Latest moisture may already be in `sensor_readings` from a manual read, the simulation sampler, or MQTT translation — why does this phase not add a scheduler or a broker? Why must strategies receive a plain context object, not SQLAlchemy rows or FastAPI types? Why are thresholds read from **zones**, not hardcoded in the strategy class?

> [!NOTE]
> ***Your Answer***
>
> `AutomationRepository.build_location_context(location_id)` assembles `LocationAutomationContext` by loading the location's zones (`zones.moisture_threshold_low`, `zones.moisture_threshold_high`) and querying `sensor_readings` for the most recent reading among moisture sensors assigned to each `zone_id` (returning `None` for zones without an assigned moisture sensor rather than borrowing readings from other zones).
>
> This phase does not add a scheduler or MQTT broker because reading ingestion is already handled by Phase 5's shared `ReadingIngest` pipeline (`POST /read`, `SimulationSampler`, and future Phase 12 MQTT ingest); Strategy purely consumes persisted rows from `sensor_readings`. Strategies receive a plain frozen `LocationAutomationContext` instead of SQLAlchemy ORM rows or FastAPI models so domain decision logic has zero database or HTTP dependencies and can be tested with simple in-memory fixtures. Thresholds are read from each `Zone` rather than hardcoded in the strategy class so each zone can enforce crop-specific moisture ranges while sharing the same strategy algorithm.

6. The active `strategy_key` is **persisted** per `location_id` (for example in `automation_rules`). Why must `POST .../automation/evaluate` use the **saved** key rather than a key the client sends only in that request? What happens on the next evaluate after the operator changes strategy but moisture stays the same?

> [!NOTE]
> ***Your Answer***
>
> Persisting `strategy_key` per `location_id` in `automation_rules` makes the chosen irrigation policy durable system configuration rather than transient UI state, ensuring background evaluations, page refreshes, and future Facade/Command workflows all apply the operator's configured policy consistently. When an operator updates the saved strategy via `PUT /api/locations/{location_id}/automation/strategy` (for example from `"conservative"` to `"aggressive"`) and calls `POST .../automation/evaluate` without any new sensor readings arriving, `AutomationService` loads the newly persisted `strategy_key` and evaluates the exact same moisture reading under the new algorithm—producing a different recommendation (`"irrigate"` instead of `"wait"`).

7. Strategy **recommends** (irrigate / wait). It should not itself start a pump. Why keep **decide** separate from **execute**? Which later pattern is meant to carry out the action?

> [!NOTE]
> ***Your Answer***
>
> Keeping **decide** (`AutomationStrategy.decide()`) separate from **execute** keeps strategy classes pure, side-effect-free, and safe to preview or audit without physically triggering water pumps or grow lights during dry-run evaluations. Carrying out the actual actuator execution, queuing, and undo/audit logging belongs to the **Command** pattern (Phase 10), which invokes the decorated `ActuatorPort` (Phase 9).

## C. Compare, contrast, and scenarios

8. Contrast Strategy with **State** (Phase 8). Both delegate to an object with the same shape. Who typically **changes** the active object, and is the variation a **policy** or a **lifecycle**?

> [!NOTE]
> ***Your Answer***
>
> Both Strategy and State delegate work to a polymorphic collaborator behind a shared interface, but they differ in intent and control over transitions:
> - **Strategy (Phase 6)** represents an externally chosen **policy** (e.g., `"conservative"` vs. `"aggressive"` irrigation). An external actor—such as an operator via the UI/API—explicitly selects and persists which strategy is active, and strategies do not transition themselves into another strategy.
> - **State (Phase 8)** represents an internal **lifecycle mode** of an entity or controller (e.g., `Idle`, `Irrigating`, `Cooldown`, `Fault`). The context or the state objects themselves automatically transition from one state to the next in response to domain events and timers.

9. Contrast Strategy with **Adapter** (Phase 5) and with **Builder** (Phase 4). Which one translates a foreign API, which one assembles a valid aggregate, and which one swaps an algorithm?

> [!NOTE]
> ***Your Answer***
>
> - **Builder (Phase 4)** assembles a complex, multi-part aggregate (`LocationConfig` with a location and validated zones) step-by-step before persistence.
> - **Adapter (Phase 5)** translates incompatible external or vendor-specific data shapes (`VendorRawPacket`, MQTT dicts) into a unified domain port (`SensorPort` / `Reading`).
> - **Strategy (Phase 6)** swaps interchangeable business decision algorithms (`ConservativeMoistureStrategy` vs. `AggressiveMoistureStrategy`) behind a common `AutomationStrategy` interface.

10. A classmate writes one “mega-strategy” that still contains `if conservative` / `if aggressive` inside a single class. Another strategy class calls the actuator adapter to water immediately. Explain why each is a trap.

> [!NOTE]
> ***Your Answer***
>
> - **A single "mega-strategy" with `if conservative` / `if aggressive` branches**: This fakes the Strategy pattern structurally while keeping all conditional branching coupled inside one class, meaning adding a third policy still requires editing existing strategy code and risks regressions across unrelated algorithms.
> - **A strategy class calling `ActuatorPort` directly to water immediately**: This mixes policy evaluation with hardware side effects, making it impossible to call `POST .../automation/evaluate` as a safe preview, bypassing safety/logging decorators (Phase 9) and command audit trails (Phase 10), and violating single responsibility.