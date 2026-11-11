# Factory Method Pattern — Sensors

## Problem
The greenhouse application needs to create heterogeneous sensor devices (such as soil moisture sensors and ambient light sensors), each requiring distinct `device_type` identifiers, default display names, and type-specific `default_config` dictionaries (e.g., `vwc` + `moisture_threshold` vs. `lux`). If HTTP handlers or application services construct concrete sensors directly or rely on scattered `if/elif` blocks, adding new sensor types forces edits across multiple layers and couples the API layer to concrete domain configurations.

## Solution
We apply the **Factory Method** pattern in the domain layer:
1. **`Sensor` (`entity.py`)**: A pure Python domain entity holding `id`, `device_type`, `display_name`, and `default_config`.
2. **`SensorCreator` (`creators.py`)**: An abstract creator defining the factory method `create_sensor(display_name: str | None = None) -> Sensor`.
3. **Concrete Creators (`MoistureSensorCreator`, `LightSensorCreator`)**: Subclasses that encapsulate the exact `device_type` and default configuration dictionary for each sensor kind.
4. **Creator Registry (`get_creator`)**: Maps short request keys (`"moisture"`, `"light"`) to their concrete creator classes and raises a `ValueError` for unsupported types.

## Where to Look in Code
- **Domain Entity**: `backend/src/domain/sensors/entity.py`
- **Abstract & Concrete Creators**: `backend/src/domain/sensors/creators.py`
- **Application Service**: `backend/src/application/sensors/service.py`
- **Repository & ORM**: `backend/src/infrastructure/persistence/device_repository.py` and `models.py`
- **REST Endpoint**: `backend/src/interfaces/api/sensors.py`

## Extension Exercise: Adding a Temperature Sensor
To add a `"temperature"` sensor without modifying `SensorService`, `DeviceRepository`, or the FastAPI router:
1. In `backend/src/domain/sensors/creators.py`, define a new concrete creator:
   ```python
   class TemperatureSensorCreator(SensorCreator):
       def create_sensor(self, display_name: str | None = None) -> Sensor:
           return Sensor(
               id=None,
               device_type="temperature_sensor",
               display_name=display_name or "Greenhouse temperature sensor",
               default_config={
                   "unit": "celsius",
                   "sampling_interval_seconds": 60,
                   "high_temp_alert_celsius": 32.0,
               },
           )