# Adapter Pattern — Sensor & Actuator Ports

## Problem
A smart greenhouse integrates heterogeneous data sources: in-process software **simulation** generators, proprietary third-party **vendor** SDK packets (`raw_millivolts`, `scale_factor`, `uom_code`, `epoch_ms`), and **MQTT** JSON payloads (`{"value": 0.41, "unit": "vwc"}`). If application services or HTTP routers handle each raw format directly with conditional branches, every new sensor driver or transport protocol forces changes across persistence, API, and later Strategy evaluation.

## Solution
We define domain **Port** interfaces (`SensorPort` in `backend/src/domain/sensors/ports.py` and `ActuatorPort` in `backend/src/domain/actuators/ports.py`) and implement dedicated **Adapters** that translate external or generated payloads into a single normalized domain value object (`Reading` in `backend/src/domain/sensors/reading.py`):

1. **`SimulationSensorAdapter` (`infrastructure/adapters/sensors/simulation.py`)**: Generates values within realistic ranges (`0.2–0.6 vwc` for moisture, `200–2000 lux` for light) with `source="simulation"`.
2. **`VendorStubSensorAdapter` (`infrastructure/adapters/sensors/vendor_stub.py`)**: Accepts proprietary `VendorRawPacket` payloads (`raw_millivolts * scale_factor`, `PCT_VWC` / `LUX_PAR`) and translates them into `Reading` with `source="vendor"`.
3. **`MqttSensorAdapter` (`infrastructure/adapters/sensors/mqtt.py`)**: Translates inbound `{ "value": ..., "unit": ... }` dictionaries into `Reading` with `source="mqtt"` without opening a broker connection in the domain.
4. **`SimulationActuatorAdapter` (`infrastructure/adapters/actuators/simulation.py`)**: Implements `ActuatorPort.apply(device_id, command, payload)` in memory so Phase 9 (Decorator) and Phase 10 (Command) can wrap and invoke actuators uniformly.

## Adapter Selection Rule
`select_sensor_adapter(device)` (`backend/src/infrastructure/adapters/sensors/__init__.py`) inspects `device.default_config`:
- `default_config.protocol == "simulation"` (default) → `SimulationSensorAdapter`
- `default_config.protocol == "mqtt"` → `MqttSensorAdapter`
- `default_config.vendor_stub == True` or `default_config.adapter == "vendor"` → `VendorStubSensorAdapter`

## Where to Look in Code
- **Domain Ports & Reading**: `backend/src/domain/sensors/ports.py`, `backend/src/domain/sensors/reading.py`, `backend/src/domain/actuators/ports.py`
- **Concrete Sensor Adapters**: `backend/src/infrastructure/adapters/sensors/`
- **Simulation Actuator Adapter**: `backend/src/infrastructure/adapters/actuators/simulation.py`
- **Single Writer Ingest & Sampler**: `backend/src/application/readings/service.py` (`ReadingIngest`), `backend/src/application/readings/sampler.py` (`SimulationSampler`)
- **Repository & ORM**: `backend/src/infrastructure/persistence/reading_repository.py`, `models.py`

## Extension Exercise: Adding a Third Vendor Adapter (Modbus Soil Probe)
1. Create `ModbusSoilSensorAdapter(SensorPort)` in `backend/src/infrastructure/adapters/sensors/modbus.py` that translates register integers into `Reading(..., unit="vwc", source="vendor")`.
2. Register `"modbus"` in `select_sensor_adapter()` without modifying `ReadingIngest`, `ReadingRepository`, or the FastAPI router.