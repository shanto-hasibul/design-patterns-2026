# Phase 4 — Builder questions

**Pattern / focus:** Builder.

**Read first:** [Guide 04](../../materials/guides/04-builder.md) · [Requirements](requirements.md)

## A. Pattern

1. State the intent of Builder in plain language. Why does construction of a complex object need **stepwise assembly** and **validation at the end** (`build()`), instead of a telescoping constructor or a half-filled dict written straight to the database?

> [!NOTE]
> **_Your Answer_**
>
> The intent of the Builder pattern is to separate the step-by-step construction of a complex composite object from its final immutable representation. A complex configuration like a location with multiple zones needs stepwise assembly (`set_location_name()`, `add_zone()`) and end-of-process validation (`build()`) because a single telescoping constructor with nested zone tuples and schedule dictionaries becomes unreadable, while writing a half-filled dictionary straight to PostgreSQL risks persisting incomplete or invalid state before all cross-field invariants (such as requiring at least one zone and unique zone names) can be verified together.

2. Name the main participants (**product**, **builder**, **optional director**, **client**). Until `build()` succeeds, is the intermediate object a finished domain product? Why does that distinction matter?

> [!NOTE]
> **_Your Answer_**
>
> - **Product (`LocationConfig` containing `Location` and its `tuple[Zone, ...]`)**: The finished, immutable domain configuration aggregate produced at the end of construction.
> - **Builder (`LocationConfigBuilder`)**: Accumulates the location name and draft zone parameters step by step and enforces domain validation rules inside `build()`.
> - **Optional Director / Mapper (`build_config_from_dto` in `application/locations/mappers.py`)**: Drives the builder steps in a standard sequence from an incoming request DTO.
> - **Client (`LocationConfigService`)**: Invokes the builder flow and passes the resulting `LocationConfig` to `LocationRepository`.
>
> Until `build()` succeeds, the builder's internal state is merely mutable staging data, **not** a finished domain product. This distinction guarantees that no downstream service or repository can ever hold or persist an unvalidated, partially constructed `LocationConfig`.

3. List at least three kinds of invalid configuration a location/zone `build()` should reject in **this** lab (name, zones, moisture thresholds). Why must those rules live in the **domain** builder, not only in the HTTP layer?

> [!NOTE]
> **_Your Answer_**
>
> `LocationConfigBuilder.build()` rejects:
> 1. **Missing or blank names**: An empty or whitespace-only location name or zone name.
> 2. **Invalid zone collection**: A location with zero zones, or duplicate zone names (case-insensitive) within the same location.
> 3. **Invalid moisture thresholds**: Volumetric water content (VWC) bounds outside `0.0` to `1.0`, or `moisture_threshold_low >= moisture_threshold_high`.
>
> These rules must live in the domain builder rather than only in FastAPI/Pydantic so that domain invariants are enforced regardless of who constructs the configuration (HTTP endpoints, CLI scripts, background jobs, or unit tests) without duplicating business logic across transport layers.

## B. This phase of the application

4. What aggregate does the builder produce (location plus zones)? Why does this course use **`location_id`** (and never `greenhouse_id`) as the name for that scope?

> [!NOTE]
> **_Your Answer_**
>
> The builder produces a `LocationConfig` aggregate wrapping a `Location` entity (`id`, `name`, and an immutable `tuple[Zone, ...]`), where each `Zone` holds `name`, `moisture_threshold_low`, `moisture_threshold_high`, `schedule`, and `location_id`. The course uses `location_id` consistently across tables (`zones.location_id`, `devices.location_id`) and REST endpoints instead of `greenhouse_id` so the relational model can represent any physical or logical cultivation site (such as a greenhouse wing, indoor room, or bay) with uniform foreign-key naming across all later phases.

5. Describe the path from API request to persistence: DTO → builder steps → `build()` → repository. What must **not** be persisted if `build()` raises `ConfigurationError` (or equivalent)? Why does assigning a device wait until the zone row exists, and why does the client send only `zone_id`?

> [!NOTE]
> **_Your Answer_**
>
> When `POST /api/locations/config` receives a `CreateLocationConfigRequestDto`, `LocationConfigService` calls `build_config_from_dto()`, which invokes `LocationConfigBuilder().set_location_name(...)`, loops through each zone calling `.add_zone(...)`, and finishes with `.build()`. Only after `build()` returns a valid `LocationConfig` does `LocationRepository.save_config()` insert the `LocationRow` and `ZoneRow` records. If `build()` raises `ConfigurationError`, **nothing** is written to the database—no location row and no zone rows—and the API returns HTTP `400`.
>
> Assigning a device (`PATCH /api/devices/{id}/zone`) waits until after the location config is saved because a zone does not have a database UUID (`zones.id`) during in-memory builder assembly. The client sends only `zone_id` (or `null`) so the client cannot supply a `location_id` that conflicts with the zone's actual parent location; `ZoneAssignmentService` looks up the target zone and copies `zone.location_id` into `devices.location_id` in the same database write.

6. Saving a location and its zones must be **one transaction**. What goes wrong if the location row commits and a later zone insert fails? How does that relate to “no half-built aggregates in the database”?

> [!NOTE]
> **_Your Answer_**
>
> If `LocationRow` were committed in its own transaction before all `ZoneRow` inserts succeeded, a failure on a zone insert would leave an orphaned, zone-less location row in PostgreSQL. That directly violates the domain invariant that every saved location must have at least one valid zone, creating a "half-built aggregate" in persistent storage. Wrapping the location insert and all child zone inserts in a single transaction with `rollback()` on failure ensures atomic all-or-nothing persistence.

7. The configuration wizard UI collects fields in steps. How does that UI map to Builder without turning React (or the HTTP handler) into the place that owns domain validation?

> [!NOTE]
> **_Your Answer_**
>
> `LocationConfigWizard.tsx` lets the user draft a location name and add/remove draft zones interactively in browser state, then submits the assembled payload to `POST /api/locations/config`. While the UI performs basic input checks for immediate user feedback, the authoritative validation remains inside `LocationConfigBuilder.build()` on the backend, and any `ConfigurationError` returned as a `400 Bad Request` is displayed in the UI error banner.

## C. Compare, contrast, and scenarios

8. Contrast Builder with Factory Method and with Abstract Factory. Which pattern answers “which type?”, which answers “which matching kit?”, and which answers “how do we assemble one **valid whole** in steps?”

> [!NOTE]
> **_Your Answer_**
>
> - **Factory Method (Phase 2)** answers *"Which single product type should be created?"* by delegating the instantiation of an individual sensor (`moisture_sensor` vs. `light_sensor`) to a concrete creator.
> - **Abstract Factory (Phase 3)** answers *"Which matching product kit/family should be created?"* by provisioning a coordinated set of sensors and actuators for a specific environment (`simulation` vs. `edge`).
> - **Builder (Phase 4)** answers *"How do we assemble one valid composite whole in steps?"* by accumulating a location name and an arbitrary list of configured zones step by step and validating the entire `LocationConfig` aggregate at `build()`.

9. Fluent method chaining (`builder.add_zone(...).build()`) is a coding style. Why is a fluent interface **not** the same thing as the Builder pattern?

> [!NOTE]
> **_Your Answer_**
>
> A fluent interface is merely a syntactic convenience where methods return `self` (`return self`) so calls can be chained in a single expression. The Builder pattern is an architectural creational pattern defined by separating stepwise state accumulation from final validation and product construction (`build()`); a builder works identically without method chaining, and any ordinary class can return `self` without being a Builder.

10. A classmate validates thresholds only in FastAPI / Pydantic and leaves `build()` empty. Another mutates builder fields after `build()` while treating the product as immutable. Explain why each is a trap.

> [!NOTE]
> **_Your Answer_**
>
> - **Validating only in FastAPI/Pydantic with an empty `build()`**: This leaks core domain invariants into the HTTP transport layer, meaning any internal service, test, or CLI tool calling `LocationConfigBuilder` directly can construct and persist corrupt configurations (such as inverted thresholds or zero zones).
> - **Mutating builder fields after `build()` while sharing references with the product**: If `LocationConfig` and `Location` store direct references to mutable lists or dicts still held by the builder, mutating the builder after `build()` silently corrupts an already-built "immutable" product. Converting zones to an immutable `tuple[Zone, ...]`, copying schedule dicts, and marking `@dataclass(frozen=True)` prevents post-build mutation bugs.