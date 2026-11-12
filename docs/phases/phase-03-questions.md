# Phase 3 — Abstract Factory questions

**Pattern / focus:** Abstract Factory.

**Read first:** [Guide 03](../../materials/guides/03-abstract-factory.md) · [Requirements](requirements.md)

## A. Pattern

1. State the intent of Abstract Factory in plain language. What goes wrong when related products are chosen independently (`if` format for each piece) instead of as a family?

> [!NOTE]
> ***Your Answer***
>
> The intent of the Abstract Factory pattern is to provide an interface for creating families of related or dependent objects without specifying their concrete classes. When related products are constructed independently using scattered `if/else` blocks for each individual piece, callers can accidentally mix incompatible components—such as pairing a mock simulation sensor with a live GPIO hardware relay—leading to runtime protocol mismatches and inconsistent environment configurations.

2. Name the main participants (**abstract factory**, **concrete factory**, **abstract products**, **concrete products**, **client**). How does choosing a factory at the start commit the client to one family?

> [!NOTE]
> ***Your Answer***
>
> - **Abstract Factory (`DeviceFamilyFactory`)**: Declares the interface (`family_key` and `create_device_set()`) for creating a coherent suite of domain devices.
> - **Concrete Factory (`SimulationDeviceFamilyFactory`, `EdgeDeviceFamilyFactory`)**: Implements the abstract factory to produce a matching kit of sensors and actuators tailored to either the `"simulation"` or `"edge"` environment.
> - **Abstract Products (`Device` with `role="sensor"` or `role="actuator"`)**: Defines the common domain representation shared by all sensors and actuators across families.
> - **Concrete Products (Simulation and Edge sensor/actuator `Device` instances)**: The specific configured devices created by a concrete factory, carrying either mock simulation protocols or physical I2C/GPIO configurations.
> - **Client (`DeviceFamilyService`)**: Resolves a `DeviceFamilyFactory` by its family key and calls `create_device_set()`. Because the client obtains every device in the bundle through that single resolved factory instance, all created sensors and actuators are guaranteed to belong to the same `device_family`.

3. When should you use Abstract Factory, and when should you skip it (for example only one product type per request, or mixing siblings is valid)?

> [!NOTE]
> ***Your Answer***
>
> You should use Abstract Factory when a system must be configured with one of several product families and the products within a family are designed to work together under a shared constraint (such as operating environment or hardware communication protocol). You should skip it when callers only ever instantiate a single standalone product type per request (where Factory Method is sufficient) or when mixing and matching individual devices across different families is completely valid and requires no family-level consistency.

## B. This phase of the application

4. In this lab, what is a **device family**, and what does `create_device_set()` (or your equivalent) return? Why must a simulation kit and an edge kit not mix incompatible siblings?

> [!NOTE]
> ***Your Answer***
>
> In this lab, a **device family** represents an operating environment tier—specifically `"simulation"` (for local software testing) and `"edge"` (for physical greenhouse hardware). Calling `create_device_set()` returns a `list[Device]` containing a coherent 4-device kit: two sensors (`moisture_sensor`, `light_sensor`) and two actuators (`water_pump`, `grow_light`) all tagged with the factory's `device_family`. A simulation kit and an edge kit must not mix incompatible siblings because simulation devices rely on synthetic mock generators (`mock_random`, `mock_relay`), whereas edge devices expect physical bus addresses and pins (`i2c`, `gpio_relay`, `gpio_pwm`); mixing them in one kit would cause hardware driver errors or unintended physical actuation during simulation runs.

5. Phase 2 Factory Method creators still exist. How does Abstract Factory **compose** them rather than replace them? What would you lose if you deleted the sensor creators and inlined all construction inside the family factory?

> [!NOTE]
> ***Your Answer***
>
> Both `SimulationDeviceFamilyFactory` and `EdgeDeviceFamilyFactory` compose Phase 2's `MoistureSensorCreator` and `LightSensorCreator` by calling `create_sensor()` to obtain the canonical `device_type` and base `default_config` (such as `unit: "vwc"`, `moisture_threshold`, or `unit: "lux"`), and then wrapping those base properties into a `Device` enriched with family-specific `protocol` settings. If we deleted the sensor creators and inlined all sensor construction inside the family factories, we would duplicate base sensor domain defaults across every family factory and break the Phase 2 `/api/sensors` single-sensor creation workflow.

6. Why add a `device_family` column on the existing `devices` table (with a default/backfill such as `"simulation"`) instead of a new table per family? What happens to Phase 2 sensor rows if you forget the backfill?

> [!NOTE]
> ***Your Answer***
>
> Adding a `device_family` column (indexed via `ix_devices_family`) to the existing `devices` table keeps all hardware inventory in a single unified schema, allowing `GET /api/devices` to query and filter across families and roles without complex `UNION` queries or schema changes when new families are introduced. If we forgot the server default or backfill (`"simulation"`) when adding a `NOT NULL` `device_family` column, the migration would either fail immediately on databases containing existing Phase 2 sensor rows or leave `NULL` values that crash domain/DTO mapping when loading older sensors.

7. `POST /api/devices/provision` returns a kit (expected size: two sensors and two actuators). `GET /api/devices` can filter by `family` and `role`. Why must the UI be able to filter by family? Why do `/api/sensors` routes from Phase 2 still need to work?

> [!NOTE]
> ***Your Answer***
>
> The UI must filter by `family` so operators inspecting or provisioning a specific environment (`simulation` vs. `edge`) only see the coherent set of devices belonging to that active environment rather than a confusing, mixed list of mock and physical hardware. The `/api/sensors` routes from Phase 2 still need to work to preserve backward compatibility with the existing Sensors dashboard section and to demonstrate that Factory Method (creating individual sensors) and Abstract Factory (provisioning complete multi-device kits) coexist cleanly on top of the same persistence layer.

## C. Compare, contrast, and scenarios

8. Draw the contrast in one paragraph: **Factory Method vs Abstract Factory**. Use the questions “which one product?” versus “which product line?” and mention that Abstract Factory often uses Factory Method–style methods inside.

> [!NOTE]
> ***Your Answer***
>
> **Factory Method** answers the question *"Which one product should be created?"* by focusing on instantiating a single product hierarchy—such as delegating the creation of an individual moisture or light sensor to `MoistureSensorCreator` or `LightSensorCreator`. **Abstract Factory**, in contrast, answers the question *"Which entire product line (family) should be created?"* by producing a coordinated set of multiple distinct product types—such as matching sensors and actuators for `"simulation"` versus `"edge"`. Rather than competing, Abstract Factory frequently uses Factory Method–style creation methods (or composes existing Factory Method creators) inside its concrete factories to construct each individual member of the product family.

9. A DTO or HTTP handler constructs concrete simulation/edge device types directly, bypassing the family factory. What consistency bug can that reintroduce? How should HTTP stay on the abstract factory / service instead?

> [!NOTE]
> ***Your Answer***
>
> If an HTTP handler or DTO constructs simulation or edge devices directly, it bypasses the family factory's encapsulation and can easily introduce partial kits, mismatched `device_family` tags, or incompatible `default_config` protocols (such as assigning an `i2c` bus config to a `"simulation"` sensor). Instead, the HTTP router (`interfaces/api/devices.py`) must remain thin: it should pass the requested `family` key to `DeviceFamilyService.provision_family(family)`, which resolves the `DeviceFamilyFactory`, persists the domain `Device` set via `DeviceRepository`, and maps the resulting domain entities to `DeviceDto` objects using `to_device_dto_list` at the API boundary.

10. Someone proposes a single “god factory” that creates locations, readings, and devices “because we already have a factory.” Why is that a misuse of Abstract Factory?

> [!NOTE]
> ***Your Answer***
>
> A "god factory" that creates greenhouse locations, sensor readings, and hardware devices violates the Single Responsibility Principle and misuses Abstract Factory because locations, time-series readings, and hardware kits have completely different lifecycles and do not form a single cohesive product family that varies together by hardware environment. Abstract Factory is specifically meant for cohesive product families whose variants (`simulation` vs. `edge`) must be switched together; bundling unrelated domain aggregates into one giant factory couples every module of the application to a single class that must be modified whenever any domain concept changes.