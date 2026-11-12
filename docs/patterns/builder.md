# Builder Pattern — Location Configuration

## Intent in This Project
Creating a valid greenhouse **location configuration** requires assembling a parent `Location` along with one or more child `Zone` definitions, each carrying volumetric water content (VWC) moisture thresholds (`0.0` to `1.0`, `low < high`) and an irrigation schedule. `LocationConfigBuilder` (`backend/src/domain/locations/config_builder.py`) constructs this composite `LocationConfig` step-by-step and validates all cross-field invariants in `build()` before any database transaction begins.

## Why Builder (Not Factory Method or Abstract Factory)
- **Factory Method (Phase 2)** selects and instantiates a single sensor variant (`moisture_sensor` vs. `light_sensor`).
- **Abstract Factory (Phase 3)** provisions a pre-defined family of matching sensors and actuators (`simulation` vs. `edge`).
- **Builder (Phase 4)** assembles a complex, multi-part aggregate (`Location` + variable number of `Zone`s with caller-supplied names, threshold bounds, and schedules) step-by-step and enforces whole-aggregate invariants at the final `build()` step.

## Where Validation Lives
All domain invariants live in `backend/src/domain/locations/config_builder.py` (`LocationConfigBuilder.build()` and `validate_zone_fields()`), raising `ConfigurationError`:
1. Non-empty `location_name`.
2. At least one zone per location.
3. Non-empty, unique zone names within the same location.
4. `moisture_threshold_low` and `moisture_threshold_high` within `[0.0, 1.0]` with `low < high`.

## Why `location_id` Naming Is Used
While the domain context remains a smart greenhouse, the relational schema and REST endpoints use `locations` and `location_id` (rather than `greenhouse_id`) so physical or logical sites (rooms, wings, bays, or greenhouses) are modeled consistently across phases.

## Why Device Assignment Is Not a Builder Method
`LocationConfigBuilder` does **not** have an `add_device()` method because devices are created independently in Phases 2–3, and zones do not have database primary keys (`zones.id`) until `LocationConfig` is persisted. Assigning or unassigning a device is an operational state update handled by `ZoneAssignmentService` (`PATCH /api/devices/{id}/zone`), which sets both `devices.zone_id` and `devices.location_id` (copied from the target zone) without rebuilding the location.