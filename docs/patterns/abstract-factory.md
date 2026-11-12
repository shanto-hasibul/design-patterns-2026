# Abstract Factory Pattern — Device Families

## Problem
A smart greenhouse runs in multiple environments—such as a local software **simulation** during development and an **edge** hardware deployment (e.g., Raspberry Pi over I2C/GPIO) in production. Each environment requires a coherent bundle of matching **sensors** (`role="sensor"`) and **actuators** (`role="actuator"`) configured with family-specific protocols, pins/addresses, and labels. If callers assemble devices ad hoc, simulation mock devices and edge GPIO devices can be accidentally mixed or misconfigured.

## Solution
We apply the **Abstract Factory** pattern (`backend/src/domain/devices/family_factory.py`):
1. **`Device` (`domain/devices/entity.py`)**: An immutable domain entity representing both sensors and actuators (`id`, `device_type`, `role`, `device_family`, `display_name`, `default_config`).
2. **`DeviceFamilyFactory`**: An abstract interface declaring `family_key` and `create_device_set() -> list[Device]`.
3. **Concrete Factories (`SimulationDeviceFamilyFactory`, `EdgeDeviceFamilyFactory`)**: Each produces a 4-device kit (2 sensors + 2 actuators). Both factories **compose** the Phase 2 Factory Method creators (`MoistureSensorCreator`, `LightSensorCreator`) for base sensor defaults and enrich them with family-specific `protocol` settings (`mock_*` vs. `i2c`/`gpio_*`).
4. **Application DTO & Mapper (`application/devices/dto.py`, `mappers.py`)**: Keeps the domain `Device` completely free of Pydantic/FastAPI concerns while exposing a strict `DeviceDto` schema at the API boundary.

## Contrast with Factory Method (Phase 2)
- **Factory Method (Phase 2)** focuses on instantiating **one single product kind** (e.g., `MoistureSensorCreator` creates a moisture sensor; `LightSensorCreator` creates a light sensor).
- **Abstract Factory (Phase 3)** focuses on creating **an entire product family** (a coordinated kit of multiple sensors and actuators that belong to the same operating environment: `simulation` or `edge`).

## Where to Look in Code
- **Domain Entity**: `backend/src/domain/devices/entity.py`
- **Abstract & Concrete Factories**: `backend/src/domain/devices/family_factory.py`
- **DTO & Mappers**: `backend/src/application/devices/dto.py`, `backend/src/application/devices/mappers.py`
- **Application Service**: `backend/src/application/devices/family_service.py`
- **Repository & ORM**: `backend/src/infrastructure/persistence/device_repository.py`, `models.py`
- **REST Router**: `backend/src/interfaces/api/devices.py`

## Why Domain `Device` ≠ `DeviceDto`
The domain `Device` is a pure Python frozen dataclass used by domain factories and repository persistence without depending on web frameworks or serialization libraries. `DeviceDto` is a Pydantic model dedicated to HTTP serialization and OpenAPI/Scalar schema generation, mapped explicitly in `application/devices/mappers.py`.

## Extension Exercise: Adding a Third Family (`industrial_plc`)
1. Create a new subclass `IndustrialPlcDeviceFamilyFactory(DeviceFamilyFactory)` in `backend/src/domain/devices/family_factory.py` with `family_key = "industrial_plc"`.
2. Implement `create_device_set()` using `MoistureSensorCreator` and `LightSensorCreator` plus actuators configured with `"protocol": "modbus_tcp"`.
3. Register `"industrial_plc": IndustrialPlcDeviceFamilyFactory` in `_FAMILY_FACTORIES`.