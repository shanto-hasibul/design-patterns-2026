# Phase 5 — Adapter questions

**Pattern / focus:** Adapter.

**Read first:** [Guide 05](../../materials/guides/05-adapter.md) · [Requirements](requirements.md)

## A. Pattern

1. State the intent of Adapter in plain language. What problem appears when business code speaks a vendor or legacy protocol (odd field names, units, XML, status codes) directly?

> [!NOTE]
> ***Your Answer***
>
> The intent of the Adapter pattern is to convert the incompatible interface or raw data format of an existing component into a clean target interface that the rest of the application expects. When core business logic speaks directly to vendor or legacy protocols—such as proprietary millivolt packets, vendor-specific unit codes (`PCT_VWC`), or raw MQTT payloads—the domain and application layers become tightly coupled to external SDK quirks, scattering translation conditionals across services and forcing widespread rewrites whenever a hardware vendor or protocol changes.

2. Name the participants (**target / port**, **adaptee**, **adapter**, **client**). What does the adapter translate, and what must it **not** decide (business policy)?

> [!NOTE]
> ***Your Answer***
>
> - **Target / Port (`SensorPort`, `ActuatorPort`)**: The domain interface defining `read(device) -> Reading` and `apply(device_id, command, payload)`.
> - **Adaptee (`VendorRawPacket`, inbound MQTT payload dict, or in-process random generator)**: The incompatible raw data shape or driver mechanism being wrapped.
> - **Adapter (`SimulationSensorAdapter`, `VendorStubSensorAdapter`, `MqttSensorAdapter`, `SimulationActuatorAdapter`)**: Implements the domain port and translates raw input/output shapes into normalized domain structures.
> - **Client (`ReadingIngest`, `SimulationSampler`)**: Interacts solely with `SensorPort` and normalized `Reading` objects without knowing which concrete adapter produced them.
>
> The adapter translates **syntax, field names, scaling factors, unit labels, and timestamps** into a normalized `Reading`, and it must **not** decide business policy such as irrigation thresholds, alert triggers, or sampling schedules.

3. GoF distinguishes an **object adapter** (composition) from a **class adapter** (inheritance). Which does modern code prefer, and why?

> [!NOTE]
> ***Your Answer***
>
> Modern code strongly prefers **object adapters** (composition) over class adapters (multiple inheritance). With composition, the adapter holds a reference to the adaptee (or receives raw payload structures) and implements the target `SensorPort` interface, which avoids rigid inheritance hierarchies, works cleanly even when an adaptee is a `dict`, `final` class, or third-party SDK object, and allows wrapping an entire family of adaptee subtypes without subclassing each one.

## B. This phase of the application

4. What is `SensorPort` in this lab, and what normalized value type (for example `Reading`) do adapters return? Why do application services depend on the port rather than on a simulation driver or vendor SDK?

> [!NOTE]
> ***Your Answer***
>
> `SensorPort` (`backend/src/domain/sensors/ports.py`) is an abstract domain interface declaring `read(device: Device) -> Reading`, and every sensor adapter returns a normalized frozen `Reading` value object containing `device_id`, `value: float`, `unit: str`, `source: str`, and a timezone-aware `recorded_at: datetime`. Application services like `ReadingIngest` depend on `SensorPort` rather than concrete simulation drivers or vendor SDKs so that persistence, validation, and downstream rule evaluation remain completely decoupled from how sensor values are generated or transported.

5. You need three translations onto the same normalized reading: a simulation adapter, a vendor stub, and an MQTT translator that accepts a payload dict. Why is the different raw shape the point of the exercise? How does `source` (`simulation`, `vendor`, or `mqtt`) show which adapter produced the reading, and why must the MQTT translator not open a broker in this phase? Phase 12 may deliver that same dict on a device HTTP route or through an optional broker — why must this phase still not open either transport?

> [!NOTE]
> ***Your Answer***
>
> Having distinct raw shapes—generated ranges in `SimulationSensorAdapter`, proprietary `VendorRawPacket` fields (`raw_millivolts`, `scale_factor`, `uom_code`) in `VendorStubSensorAdapter`, and `{"value": 0.41, "unit": "vwc"}` dicts in `MqttSensorAdapter`—proves that the Adapter pattern isolates heterogeneous external formats behind one uniform `Reading` contract. The `source` field (`"simulation"`, `"vendor"`, or `"mqtt"`) provides provenance metadata on every persisted row so operators and diagnostics can verify which adapter translated the measurement.
>
> `MqttSensorAdapter` must not open a broker socket—and Phase 5 must not open either device HTTP ingest or an MQTT subscriber—because transport/network lifecycle management belongs to the outer infrastructure layer in Phase 12, whereas Phase 5 isolates pure payload translation so it can be unit-tested deterministically without network sockets.

6. Readings are **appended** to `sensor_readings` (history grows). Why not keep only the latest value in memory or overwrite a single row, and which later phase consumes this history? Why do a manual read, the simulation sampler, and (later) MQTT share **one** writer of that table? Why does the sampler skip devices with tracking off and MQTT devices, and why do sensor cards poll the latest stored reading until Phase 12?

> [!NOTE]
> ***Your Answer***
>
> Appending every reading to `sensor_readings` (indexed by `(device_id, recorded_at DESC)`) ensures durability across server restarts and preserves time-series history for later **Strategy** evaluation (Phase 6), **Dashboard Overview** latest-reading queries (Phase 7), and **Historical Charts** (Phase 13). Routing manual reads (`POST /api/sensors/{id}/read`), `SimulationSampler`, and future MQTT/device-HTTP ingest through a single writer (`ReadingIngest.record`) guarantees consistent validation, uniform DTO mapping, and a single hook point for Phase 11 Observer events (`reading.created`).
>
> `SimulationSampler` skips devices with `tracking_enabled=False` so paused sensors do not generate unwanted background data, and skips `protocol="mqtt"` devices because edge hardware pushes its own readings rather than being generated in-process. Until Phase 12 introduces WebSocket push events, sensor cards poll `GET /api/sensors/{id}/readings?limit=1` so background sampler rows automatically appear in the UI.

7. `POST /api/sensors/{id}/read` runs an adapter, persists, and returns a DTO. What HTTP status is appropriate when the device is missing versus when the adapter fails? Why must the router never see vendor-shaped types?

> [!NOTE]
> ***Your Answer***
>
> When the target sensor device does not exist, `POST /api/sensors/{id}/read` returns **HTTP `404 Not Found`** (`SensorDeviceNotFoundError`); when the adapter fails to read or translate a malformed payload (`SensorAdapterError`), it returns **HTTP `400 Bad Request`**. The FastAPI router must never import or expose vendor-shaped types (`VendorRawPacket`) so that HTTP contracts remain strictly typed around `ReadingDto` and changes to a vendor's internal payload format never leak into the API layer.

## C. Compare, contrast, and scenarios

8. Contrast Adapter with **Facade**. Adapter changes the **shape** of an existing interface; Facade simplifies **how to use** a subsystem. Give a greenhouse-shaped example of each (Adapter this phase; Facade in Phase 7).

> [!NOTE]
> ***Your Answer***
>
> - **Adapter (Phase 5)**: Converts an incompatible raw interface into an expected domain port without changing overall subsystem scope—for example, `VendorStubSensorAdapter` translates a proprietary `VendorRawPacket` (`raw_millivolts`, `uom_code`) into a normalized `Reading` implementing `SensorPort`.
> - **Facade (Phase 7)**: Provides a single high-level entry point that orchestrates multiple underlying repositories and services to simplify a complex workflow—for example, a dashboard overview facade that gathers a location's zones, assigned devices, latest `sensor_readings`, and recent alerts into one unified summary response.

9. Contrast Adapter with **Decorator**. Both wrap an object. What is different about the interface they present to the client?

> [!NOTE]
> ***Your Answer***
>
> An **Adapter** wraps an adaptee whose interface does *not* match what the client expects and converts it into a **different** target interface (`SensorPort` / `ActuatorPort`). A **Decorator** (such as Phase 9's decorators around `ActuatorPort`) wraps an object that **already implements the same interface** and presents the **exact same interface** to the client while layering on extra behavior (such as logging, retry, or safety checks).

10. A classmate puts irrigation policy (“if moisture < 0.3 then water”) inside the vendor adapter. Why is that a trap? Where should that decision live instead (later Strategy), and what should stay in the adapter?

> [!NOTE]
> ***Your Answer***
>
> Putting irrigation policy inside a vendor adapter is a trap because it couples business decision rules to a specific hardware driver: switching from the vendor adapter to `SimulationSensorAdapter` or `MqttSensorAdapter` would silently drop or duplicate the watering logic, and changing the threshold rules would require editing hardware translation code. Instead, irrigation decision logic belongs in the **Strategy** layer (Phase 6), while the adapter must strictly stay responsible for translating raw sensor signals into normalized `Reading` values.