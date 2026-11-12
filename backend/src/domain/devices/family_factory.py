from abc import ABC, abstractmethod
from src.domain.devices.entity import Device
from src.domain.sensors.creators import LightSensorCreator, MoistureSensorCreator


class DeviceFamilyFactory(ABC):
    @property
    @abstractmethod
    def family_key(self) -> str:
        ...

    @abstractmethod
    def create_device_set(self) -> list[Device]:
        ...


class SimulationDeviceFamilyFactory(DeviceFamilyFactory):
    @property
    def family_key(self) -> str:
        return "simulation"

    def create_device_set(self) -> list[Device]:
        moisture_proto = MoistureSensorCreator().create_sensor("Sim Soil Moisture Sensor")
        light_proto = LightSensorCreator().create_sensor("Sim Ambient Light Sensor")

        moisture_sensor = Device(
            id=None,
            device_type=moisture_proto.device_type,
            role="sensor",
            device_family=self.family_key,
            display_name=moisture_proto.display_name,
            default_config={
                **moisture_proto.default_config,
                "protocol": "mock_random",
                "simulated_noise": 0.05,
            },
        )
        light_sensor = Device(
            id=None,
            device_type=light_proto.device_type,
            role="sensor",
            device_family=self.family_key,
            display_name=light_proto.display_name,
            default_config={
                **light_proto.default_config,
                "protocol": "mock_sine_wave",
                "simulated_noise": 0.02,
            },
        )
        water_pump = Device(
            id=None,
            device_type="water_pump",
            role="actuator",
            device_family=self.family_key,
            display_name="Sim Irrigation Water Pump",
            default_config={
                "protocol": "mock_relay",
                "flow_rate_lpm": 2.5,
                "max_runtime_seconds": 60,
            },
        )
        grow_light = Device(
            id=None,
            device_type="grow_light",
            role="actuator",
            device_family=self.family_key,
            display_name="Sim LED Grow Light Array",
            default_config={
                "protocol": "mock_pwm",
                "spectrum": "full_spectrum_sim",
                "default_intensity_percent": 75,
            },
        )
        return [moisture_sensor, light_sensor, water_pump, grow_light]


class EdgeDeviceFamilyFactory(DeviceFamilyFactory):
    @property
    def family_key(self) -> str:
        return "edge"

    def create_device_set(self) -> list[Device]:
        moisture_proto = MoistureSensorCreator().create_sensor("Edge I2C Soil Moisture Probe")
        light_proto = LightSensorCreator().create_sensor("Edge BH1750 LUX Sensor")

        moisture_sensor = Device(
            id=None,
            device_type=moisture_proto.device_type,
            role="sensor",
            device_family=self.family_key,
            display_name=moisture_proto.display_name,
            default_config={
                **moisture_proto.default_config,
                "protocol": "i2c",
                "i2c_address": "0x36",
                "bus": 1,
            },
        )
        light_sensor = Device(
            id=None,
            device_type=light_proto.device_type,
            role="sensor",
            device_family=self.family_key,
            display_name=light_proto.display_name,
            default_config={
                **light_proto.default_config,
                "protocol": "i2c",
                "i2c_address": "0x23",
                "bus": 1,
            },
        )
        water_pump = Device(
            id=None,
            device_type="water_pump",
            role="actuator",
            device_family=self.family_key,
            display_name="Edge GPIO Relay Water Pump",
            default_config={
                "protocol": "gpio_relay",
                "gpio_pin": 17,
                "active_high": True,
                "flow_rate_lpm": 4.0,
            },
        )
        grow_light = Device(
            id=None,
            device_type="grow_light",
            role="actuator",
            device_family=self.family_key,
            display_name="Edge PWM Grow Light Bar",
            default_config={
                "protocol": "gpio_pwm",
                "gpio_pin": 18,
                "frequency_hz": 1000,
                "default_intensity_percent": 80,
            },
        )
        return [moisture_sensor, light_sensor, water_pump, grow_light]


_FAMILY_FACTORIES: dict[str, type[DeviceFamilyFactory]] = {
    "simulation": SimulationDeviceFamilyFactory,
    "edge": EdgeDeviceFamilyFactory,
}


def get_family_factory(family: str) -> DeviceFamilyFactory:
    normalized = family.strip().lower() if family else ""
    factory_cls = _FAMILY_FACTORIES.get(normalized)
    if factory_cls is None:
        supported = ", ".join(sorted(_FAMILY_FACTORIES.keys()))
        raise ValueError(f"Unknown device family '{family}'. Supported families: {supported}")
    return factory_cls()