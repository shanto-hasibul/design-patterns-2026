# Phase 7 — Facade questions

**Pattern / focus:** Facade.

**Read first:** [Guide 07](../../materials/guides/07-facade.md) · [Requirements](requirements.md)

## A. Pattern

1. State the intent of Facade in plain language. What problem appears when every HTTP handler (or every UI screen) repeats the same multi-step dance across repositories and services?

> [!NOTE]
> **_Your Answer_**
>
> The intent of the Facade pattern is to provide a unified, simplified entry point to a complex subsystem of multiple repositories and services. When every FastAPI route handler or React screen repeats the same multi-step sequence of loading locations, querying assigned devices, fetching latest readings, and evaluating strategies, coordination logic becomes duplicated across clients, network chatiness increases, and internal refactoring of any underlying repository breaks every caller.

2. A facade **orchestrates** collaborators. What should it **not** become (a god object that owns all domain logic)? Where should irrigation policy, sensor translation, and persistence stay instead?

> [!NOTE]
> **_Your Answer_**
>
> A facade must **not** become a "god object" that absorbs domain business rules, raw SQL queries, or external protocol translation. Instead, it strictly coordinates existing collaborators:
> - **Irrigation policy** stays in the domain `AutomationStrategy` implementations and `AutomationService` (Phase 6).
> - **Sensor translation** stays in `SensorPort` adapters (`SimulationSensorAdapter`, `VendorStubSensorAdapter`, `MqttSensorAdapter`) and `ReadingIngest` (Phase 5).
> - **Persistence** stays inside dedicated repositories (`LocationRepository`, `DeviceRepository`, `ReadingRepository`, `AutomationRepository`).

3. When should you use Facade, and when should you skip it (a single repository call is enough; or you actually need to **translate** a mismatched interface)?

> [!NOTE]
> **_Your Answer_**
>
> You should use Facade when a client (such as a dashboard overview endpoint) needs to coordinate several repositories and services to assemble a single cohesive workflow or read model. You should skip Facade when an operation is already a simple single-repository call (like `GET /api/locations` listing location summaries), or when the actual goal is converting an incompatible third-party interface into a domain contract—which requires **Adapter** instead.

## B. This phase of the application

4. What does `GET /api/locations/{location_id}/overview` return? Name the main pieces of the overview DTO: location, assigned device counts, and `zones` (thresholds, assigned devices, and those devices’ latest readings, including `tracking_enabled` and `sampling_interval_seconds`), plus strategy key and last recommendation. Why may those reading rows come from the sampler or MQTT ingest, not only from `POST /read`? Why is overview scoped by `location_id`?

> [!NOTE]
> **_Your Answer_**
>
> `GET /api/locations/{location_id}/overview` returns a `LocationOverviewDto` containing:
> - **`location`**: `{ id, name }` for the requested site.
> - **`device_counts`**: `{ sensor, actuator }` counting only devices assigned to zones in that location (`location_id` set and `zone_id` non-null).
> - **`zones`**: Every zone in that location (including empty zones), each carrying `id`, `name`, `moisture_threshold_low`, `moisture_threshold_high`, its assigned `devices` (`id`, `device_type`, `role`, `display_name`), and `latest_readings` (`device_id`, `value`, `unit`, `recorded_at`, plus `tracking_enabled` and `sampling_interval_seconds` copied from the device).
> - **`strategy_key` and `last_recommendation`**: The saved automation strategy key (or `null`) and the on-demand `{ action, reason }` recommendation computed by `AutomationService.evaluate()` when a key is saved (or `null` when none is saved).
>
> Those reading rows may originate from manual `POST /read` triggers, `SimulationSampler`, or `MqttSensorAdapter` ingest because all three paths write normalized rows into the single `sensor_readings` table keyed by `device_id`. The overview is scoped by `location_id` to match the Phase 4 site boundary so each physical greenhouse or room displays only its own zones, assigned hardware, and active automation policy.

5. Why does this phase **not** require a new business table? What already exists from Phases 2–6 that the facade only **composes**?

> [!NOTE]
> **_Your Answer_**
>
> Phase 7 requires no new business tables because Phases 2–6 already persist every piece of state needed for the dashboard snapshot: `locations` and `zones` (Phase 4), `devices` with `role`, `zone_id`, `location_id`, `sampling_interval_seconds`, and `tracking_enabled` (Phases 2–5), `sensor_readings` (Phase 5), and `automation_rules` (Phase 6). `LocationOverviewFacade` simply queries and composes those existing tables into a unified read model.

6. The overview HTTP handler should call **only** the facade, not reading/strategy/device repositories directly. Why? How does that help tests and later changes to the query shape?

> [!NOTE]
> **_Your Answer_**
>
> Keeping the FastAPI router (`interfaces/api/overview.py`) coupled only to `LocationOverviewFacade` keeps HTTP endpoints thin, declarative, and focused solely on DTO serialization and HTTP status mapping. This makes unit and integration testing straightforward—tests can verify the facade or swap in fake repositories in one place—and allows us to optimize SQL query shapes (such as batching latest readings or introducing a SQL view) inside the facade and repositories without touching the HTTP layer.

7. The location selector may use the existing locations list. The Overview cards come from **one** overview fetch, and Refresh repeats that same fetch. Why must the React page not stitch device, reading, and automation calls together to build the same snapshot? How does a new reading or a saved strategy show up on overview without extra frontend glue?

> [!NOTE]
> **_Your Answer_**
>
> If React fetched locations, zones, devices, per-device readings, and strategy evaluation separately and merged them in browser state, the UI would suffer from waterfall network latency, risk inconsistent intermediate states, and duplicate backend grouping logic in TypeScript. Because `OverviewPanel.tsx` fetches the single `/api/locations/{location_id}/overview` endpoint, any new reading stored in `sensor_readings` or any newly persisted `strategy_key` in `automation_rules` automatically appears on the next overview fetch or Refresh click with zero extra client-side stitching.

## C. Compare, contrast, and scenarios

8. Contrast Facade with **Adapter**. One makes an existing interface usable; the other makes a subsystem simpler to call. Which is which, and how do both appear in this greenhouse app (Phase 5 vs Phase 7)?

> [!NOTE]
> **_Your Answer_**
>
> - **Adapter (Phase 5)** makes an existing incompatible interface usable by translating its shape into a target domain port—for example, `VendorStubSensorAdapter` and `MqttSensorAdapter` convert raw vendor packets and MQTT payload dicts into normalized `Reading` objects implementing `SensorPort`.
> - **Facade (Phase 7)** makes a multi-part subsystem simpler to call by hiding several collaborators behind one high-level operation—for example, `LocationOverviewFacade.get_overview()` coordinates four repositories and `AutomationService` to deliver the entire dashboard overview in one call.

9. This phase mentions **N+1** queries. What is an N+1 problem in an overview that lists latest readings for many devices, and what can the facade (or its repository) do about it without putting SQL in the router?

> [!NOTE]
> **_Your Answer_**
>
> An **N+1 query problem** occurs when the application runs 1 query to load the list of `N` assigned devices in a location and then loops over each device in Python to execute `N` separate `SELECT ... ORDER BY recorded_at DESC LIMIT 1` queries against `sensor_readings`. To avoid this without putting SQL in the router, `LocationOverviewFacade` collects all assigned device UUIDs up front and calls `ReadingRepository.get_latest_readings_for_devices(assigned_ids)`, which fetches the newest reading for every assigned device in a single batched `DISTINCT ON (device_id)` SQL query.

10. A classmate hides every error behind a generic “overview failed,” so a missing location, a DB outage, and a strategy error look the same. Why is that a trap for a facade?

> [!NOTE]
> **_Your Answer_**
>
> Swallowing all exceptions behind a generic "overview failed" error destroys diagnostic clarity and breaks proper HTTP semantics: a client cannot distinguish a non-existent `location_id` (`404 Not Found`) from an invalid configuration (`400 Bad Request`) or an actual PostgreSQL connection outage (`500 Internal Server Error`). A well-designed facade should let domain/application errors like `LocationNotFoundError` propagate cleanly so the API boundary can map them to accurate HTTP status codes while letting unexpected infrastructure failures surface clearly in logs and monitoring.