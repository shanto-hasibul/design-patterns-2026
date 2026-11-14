# Phase 11 — Observer questions

**Pattern / focus:** Observer.

**Read first:** [Guide 11](../../materials/guides/11-observer.md) · [Requirements](requirements.md)

## A. Pattern

1. State the intent of Observer in plain language. What is a **one-to-many** dependency here, and why must the subject notify dependents **without** knowing their concrete classes?

> [!NOTE]
> ***Your Answer***
>
> The intent of the Observer pattern is to define a one-to-many dependency so that when an important event occurs in one part of the system, all interested listeners are automatically notified without tight coupling. Here, **one** domain occurrence (such as a `ReadingCreated` event from `ReadingIngest`) fans out to **many** independent reactions—persisting an alert in PostgreSQL (`AlertPersistenceSubscriber`), incrementing in-memory counters (`MetricsSubscriber`), and in Phase 12 broadcasting over WebSockets. Notifying dependents solely through a generic subscriber interface prevents core ingestion and command services from depending on concrete persistence, metrics, or transport classes.

2. Name the participants (**subject / event bus**, **observer / subscriber**, **concrete observers**, **event**, **publisher**). What does `subscribe` / `unsubscribe` / `publish` (or `notify`) each do?

> [!NOTE]
> ***Your Answer***
>
> - **Subject / Event Bus (`EventBus` in `domain/events/bus.py`)**: Maintains the registry of active subscriber callbacks and dispatches published events.
> - **Observer / Subscriber (`EventSubscriber` / `SubscriberFn`)**: The uniform `handle(event: DomainEvent) -> None` contract implemented by listeners.
> - **Concrete Observers (`AlertPersistenceSubscriber`, `MetricsSubscriber` in `application/alerts/subscribers.py`)**: Perform concrete reactions such as inserting rows into `alerts` or counting event types.
> - **Event (`DomainEvent`, `ReadingCreated`, `ThresholdCrossed`, `CommandFailed`, `ActuatorStateChanged` in `domain/events/events.py`)**: Immutable value objects carrying event metadata (`device_id`, `location_id`, `zone_id`, and payload fields).
> - **Publisher (`ReadingIngest`, `CommandService`, `ActuatorStateService`)**: Emits domain events to `EventBus` after completing its core state change.
>
> `subscribe(fn)` registers a listener callback and returns an `unsubscribe()` closure that removes that callback from the bus so cleaned-up listeners stop receiving events, while `publish(event)` iterates over registered subscribers and invokes each handler with the event.

3. When should you use Observer, and when should you skip it (only one listener forever; or you need a strict multi-step workflow with guaranteed order)?

> [!NOTE]
> ***Your Answer***
>
> You should use Observer when multiple independent side effects (such as alert persistence, metrics, and WebSocket push notifications) need to react to the same domain occurrence without coupling the publisher to each consumer. You should skip Observer when there will only ever be a single direct collaborator (a normal method call is simpler and easier to trace), or when you need a strict, transactional multi-step workflow with guaranteed ordering and rollback semantics—which belongs in an explicit application service or Facade instead.

## B. This phase of the application

4. Give at least two **domain events** you publish in this lab, including `reading.created` (only when `tracking_enabled` is true), a threshold-crossed event, and command-failed. Who publishes `reading.created`, and why do a manual read, the simulation sampler, and MQTT translation share that one ingest publish? Why must a publisher **not** import the alerts repository or the UI?

> [!NOTE]
> ***Your Answer***
>
> We publish **`ReadingCreated`** (`"reading.created"`), **`ThresholdCrossed`** (`"threshold.crossed"`), **`CommandFailed`** (`"command.failed"`), **`CommandCompleted`** (`"command.completed"`), and **`ActuatorStateChanged`** (`"actuator.state_changed"`).
>
> **`ReadingIngest.record()`** (`backend/src/application/readings/service.py`) is the single publisher of `ReadingCreated`—and only emits it when `device.tracking_enabled` is `True`. Routing manual `POST /read` triggers, `SimulationSampler`, and MQTT payload translation through `ReadingIngest.record()` ensures consistent `location_id`/`zone_id` enrichment and identical tracking-flag enforcement without duplicating publish logic across transports. Publishers must never import `AlertRepository` or UI/WebSocket code so domain and ingestion workflows stay decoupled from how alerts are stored or displayed.

5. What does `AlertPersistenceSubscriber` (or your equivalent) do when it handles an event? Why do alerts live in the `alerts` table so the event feed still shows them after a **refresh**?

> [!NOTE]
> ***Your Answer***
>
> When `AlertPersistenceSubscriber.handle(event)` receives a `ReadingCreated` event for a moisture (`vwc`) sensor, it checks the reading against the assigned zone's `moisture_threshold_low` (or `0.30` if unassigned) and, if below threshold, calls `AlertRepository.create_alert(...)` to insert an active `"threshold.crossed"` row carrying the device's `location_id` and `zone_id` (or `None` if unassigned). It similarly inserts rows on `ThresholdCrossed`, `CommandFailed`, and `ActuatorStateChanged` (`new_state == "error"`). Persisting alerts in PostgreSQL (`alerts` table) guarantees durability across browser refreshes, server restarts, and location/zone filter queries via `GET /api/alerts`.

6. The dashboard Event feed **polls** `GET /api/alerts` (or events). `services/realtime.ts` is only a **stub**. Why is full WebSocket **not** required in this phase? What should Phase 12 plug into so you do **not** re-implement pub/sub inside socket handlers?

> [!NOTE]
> ***Your Answer***
>
> Full WebSocket streaming is deferred to Phase 12 so Phase 11 can focus cleanly on decoupling publishers from alert persistence via `EventBus` and `AlertPersistenceSubscriber`, while `EventFeed.tsx` polls `GET /api/alerts` every 4 seconds and `frontend/src/services/realtime.ts` defines the `subscribeRealtime()` client contract. In Phase 12, the backend WebSocket manager will simply attach as **another subscriber on the exact same `EventBus`**, rather than re-implementing pub/sub or querying sensors inside socket handlers.

7. Describe the must-demo path: a **tracked** low-moisture reading leads to an alert row that appears in the feed after poll. Which objects collaborate (reading pipeline → bus → subscriber → API → UI), and which object must **not** write the alert directly? What is stored, and what is not published, when `tracking_enabled` is false?

> [!NOTE]
> ***Your Answer***
>
> On the demo path for a tracked moisture sensor (`tracking_enabled=True`) assigned to a zone:
> 1. **`ReadingIngest.record()`** persists the low-moisture reading via `ReadingRepository.save_reading()` and publishes `ReadingCreated(device_id, location_id, zone_id, value, unit, ...)` to **`EventBus`**.
> 2. **`EventBus`** fans out the event to **`AlertPersistenceSubscriber`**, which compares the value against the zone's `moisture_threshold_low` and writes a new row into `alerts` via **`AlertRepository`** (`ReadingIngest` and the sensor adapters must **never** write to `AlertRepository` directly).
> 3. **`EventFeed.tsx`** polls **`GET /api/alerts`** (`interfaces/api/alerts.py`), which queries `AlertRepository` and renders the new alert card in `#events`.
>
> When `tracking_enabled` is `False`, `ReadingIngest.record()` still saves the row to `sensor_readings` (for one-shot reads), **skips** `EventBus.publish(ReadingCreated(...))`, and creates no alert.

## C. Compare, contrast, and scenarios

8. Contrast Observer with **Facade**. Facade simplifies **calling into** a subsystem. Observer **fans out** notifications after something happened. How do both appear in this greenhouse (Phase 7 overview vs this phase)?

> [!NOTE]
> ***Your Answer***
>
> - **Facade (Phase 7 — Inbound Simplification)**: A caller explicitly invokes `LocationOverviewFacade.get_overview(location_id)` to pull and aggregate data across four repositories into one dashboard snapshot.
> - **Observer (Phase 11 — Outbound Fan-Out)**: A publisher emits `ReadingCreated` or `CommandFailed` onto `EventBus` after an action happens, pushing notifications outward to `AlertPersistenceSubscriber` and `MetricsSubscriber` without knowing who is listening.

9. Contrast Observer with **Command**. Command captures **intent to act**. Observer propagates **outcomes**. How can `execute()` publish an event without the command class knowing who persists alerts?

> [!NOTE]
> ***Your Answer***
>
> **Command** (`StartPumpCommand`, `StopPumpCommand`) encapsulates the **intent to act** on an actuator, whereas **Observer** (`EventBus`) propagates the **outcome** (`CommandCompleted`, `CommandFailed`, `ActuatorStateChanged`) after execution. `CommandService` (or the invoker wrapper) publishes the outcome event to `EventBus` once `command.execute(port)` finishes; neither the command class nor `CommandService` imports `AlertPersistenceSubscriber` or `AlertRepository`, leaving alert persistence completely decoupled behind the bus.

10. One subscriber throws during `notify` / `publish` and aborts the loop, so later subscribers never run. Why is that a trap? What should the bus do so a failing alert writer does not block metrics (or later WebSocket) subscribers?

> [!NOTE]
> ***Your Answer***
>
> If an unhandled exception in one subscriber aborts `EventBus.publish()` mid-loop, a transient failure in `AlertPersistenceSubscriber` (such as a database lock or constraint error) would prevent `MetricsSubscriber` and Phase 12's WebSocket broadcaster from ever receiving the event. To prevent one faulty observer from starving others, `EventBus.publish()` should wrap each subscriber invocation in a `try...except Exception` block, log the subscriber failure for diagnostics, and continue notifying the remaining subscribers in the loop.