# Phase 2 — Factory Method questions

**Pattern / focus:** Factory Method.

**Read first:** [Guide 02](../../materials/guides/02-factory-method.md) · [Requirements](requirements.md)

## A. Pattern

1. State the intent of Factory Method in plain language. What problem appears when callers scatter `new` / constructors (or a growing `if type == ...`) across the application?

> [!NOTE]
> ***Your Answer***
>
> The intent of the Factory Method pattern is to define an interface for creating an object while letting subclasses or concrete creators decide which specific class or configuration to instantiate. When callers scatter direct constructor calls or `if type == ...` branches across HTTP handlers and services, every layer becomes tightly coupled to concrete product details, and adding or changing a sensor's defaults requires hunting down and modifying every caller across the codebase.

2. Name the main participants of Factory Method (**product**, **concrete product**, **creator**, **concrete creator**, **client**). For each, give one sentence: what it is responsible for.

> [!NOTE]
> ***Your Answer***
>
> - **Product (`Sensor`)**: Defines the common domain structure and interface of the objects created by the factory method (`id`, `device_type`, `display_name`, and `default_config`).
> - **Concrete Product (Configured `Sensor` instances for moisture/light)**: Represents the specific sensor configurations produced by concrete creators, such as a `"moisture_sensor"` with `vwc` and `moisture_threshold` defaults or a `"light_sensor"` with `lux` defaults.
> - **Creator (`SensorCreator`)**: Declares the abstract factory method `create_sensor(display_name)` that returns a `Sensor` product.
> - **Concrete Creator (`MoistureSensorCreator`, `LightSensorCreator`)**: Overrides `create_sensor` to build and return a `Sensor` with type-specific `device_type` and `default_config` values.
> - **Client (`SensorService`)**: Calls `get_creator(sensor_type)` and invokes `create_sensor()` on the abstract `SensorCreator` interface without knowing how concrete sensor configurations are assembled.

3. How do you add a **new product variant** when creators are polymorphic (new class + registry entry) versus when creation lives in one shared `if/elif` function? Why does that difference matter for extension?

> [!NOTE]
> ***Your Answer***
>
> With polymorphic creators, adding a new sensor variant only requires creating a new `SensorCreator` subclass (for example, `TemperatureSensorCreator`) and registering its key in `_CREATOR_REGISTRY`, leaving existing creator classes untouched. In contrast, a single shared `if/elif` function forces you to modify the same function body every time a new type is introduced. This difference matters because polymorphic creators follow the Open/Closed Principle—isolating each variant's defaults in its own class reduces merge conflicts, simplifies unit testing, and prevents regressions in existing sensor creation logic.

## B. This phase of the application

4. In this lab, what is the **product** and what are the **concrete creators**? Why must the API handler (or sensor service) go through a creator/registry instead of constructing `MoistureSensor` / `LightSensor` itself?

> [!NOTE]
> ***Your Answer***
>
> In this lab, the **product** is the domain `Sensor` dataclass (`backend/src/domain/sensors/entity.py`), and the **concrete creators** are `MoistureSensorCreator` and `LightSensorCreator` (`backend/src/domain/sensors/creators.py`). The API handler and `SensorService` must go through the creator registry (`get_creator`) rather than constructing moisture or light sensors directly so that HTTP and application layers remain decoupled from domain-specific sensor defaults and new sensor types can be added without modifying router or service code.

5. `POST /api/sensors` accepts a short `type` key such as `"moisture"` or `"light"`, while the stored/returned field is `device_type` (for example `moisture_sensor`). Why are those two fields different? Who decides the stored `device_type` and `default_config`?

> [!NOTE]
> ***Your Answer***
>
> The POST request's `type` field (`"moisture"` or `"light"`) is a short selector key used by the client to request a creator from the registry, whereas `device_type` (`"moisture_sensor"` or `"light_sensor"`) is the canonical domain and database identifier persisted in the `devices` table. The **concrete creator** (`MoistureSensorCreator` or `LightSensorCreator`) is solely responsible for deciding both the stored `device_type` string and the `default_config` dictionary.

6. Why is there a single `devices` table with `role="sensor"` instead of a dedicated `sensors` table? What later phase does that choice prepare for?

> [!NOTE]
> ***Your Answer***
>
> Storing sensors in a unified `devices` table with `role="sensor"` (indexed on `role`) avoids splitting hardware inventory across separate tables and allows different kinds of greenhouse hardware to share common identity, metadata, and configuration columns. This directly prepares the schema for **Phase 3 (Abstract Factory)**, which extends the same `devices` table with actuators (`role="actuator"`) and a `device_family` column without redoing sensor persistence.

7. What should happen when the client posts an **unknown** `type`? Where should that rejection be decided (registry/service vs router constructing a concrete class anyway)?

> [!NOTE]
> ***Your Answer***
>
> When a client posts an unknown `type`, the API must reject the request prior to any database insert and return an HTTP `400 Bad Request` with a clear error message. That rejection is decided in the domain/application layer when `get_creator(sensor_type)` raises a `ValueError` for an unrecognized key, which the FastAPI router catches and maps to an HTTP 400 response.

## C. Compare, contrast, and scenarios

8. Contrast Factory Method with a **simple factory** (one function full of `if type == ...`). When is the simple factory “good enough,” and why does this phase still want polymorphic creators?

> [!NOTE]
> ***Your Answer***
>
> A simple factory uses a single function or static method containing an `if/elif/else` switch to construct objects, whereas Factory Method defines an abstract creator interface (`SensorCreator`) with dedicated concrete creator subclasses (`MoistureSensorCreator`, `LightSensorCreator`). A simple factory is good enough when there are only a couple of trivial types that rarely change and require minimal setup. This phase uses polymorphic creators because each sensor kind has distinct domain defaults and validation rules, and **Phase 3 (Abstract Factory)** will compose these creator objects into device-family bundles without rewriting creation logic.

9. Contrast Factory Method with **Abstract Factory** (Phase 3). Factory Method answers which question? Abstract Factory answers which different question? Why is Factory Method enough for Phase 2 sensors?

> [!NOTE]
> ***Your Answer***
>
> **Factory Method** answers the question: *"How do I defer the instantiation of a single kind of product (one sensor) to specialized subclasses?"* **Abstract Factory** (Phase 3) answers a different question: *"How do I create coordinated families of related products (such as matching sensors and actuators belonging to the same `device_family`) together?"* Factory Method is sufficient for Phase 2 because we are only creating individual standalone sensors (`role="sensor"`) rather than multi-device family bundles.

10. A classmate puts SQLAlchemy session commits (or FastAPI request parsing) **inside** a concrete creator. Why is that a trap? Where should persistence and HTTP stay instead?

> [!NOTE]
> ***Your Answer***
>
> Putting SQLAlchemy session commits or FastAPI request parsing inside a concrete creator violates clean architecture by coupling pure domain creation logic to database infrastructure and HTTP transport frameworks. This makes it impossible to run fast, database-free unit tests on the creators or reuse them outside of an HTTP request. Instead, HTTP request parsing and status code mapping belong in the **API layer** (`interfaces/api/sensors.py`), database session management and commits belong in the **infrastructure layer** (`DeviceRepository`), and orchestration belongs in the **application service** (`SensorService`).