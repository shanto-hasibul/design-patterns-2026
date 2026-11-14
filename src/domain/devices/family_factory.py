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
                "protocol": "simulation",
                "simulated_noise": 0.05,
            },
            sampling_interval_seconds=300,
            tracking_enabled=True,
        )
        light_sensor = Device(
            id=None,
            device_type=light_proto.device_type,
            role="sensor",
            device_family=self.family_key,
            display_name=light_proto.display_name,
            default_config={
                **light_proto.default_config,
                "protocol": "simulation",
                "simulated_noise": 0.02,
            },
            sampling_interval_seconds=180,
            tracking_enabled=True,
        )
        water_pump = Device(
            id=None,
            device_type="water_pump",
            role="actuator",
            device_family=self.family_key,
            display_name="Sim Irrigation Water Pump",
            default_config={
                "protocol": "simulation",
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
                "protocol": "simulation",
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
        moisture_proto = MoistureSensorCreator().create_sensor("Edge MQTT Soil Moisture Probe")
        light_proto = LightSensorCreator().create_sensor("Edge MQTT BH1750 LUX Sensor")

        moisture_sensor = Device(
            id=None,
            device_type=moisture_proto.device_type,
            role="sensor",
            device_family=self.family_key,
            display_name=moisture_proto.display_name,
            default_config={
                **moisture_proto.default_config,
                "protocol": "mqtt",
                "topic": "greenhouse/edge/moisture",
            },
            sampling_interval_seconds=300,
            tracking_enabled=True,
        )
        light_sensor = Device(
            id=None,
            device_type=light_proto.device_type,
            role="sensor",
            device_family=self.family_key,
            display_name=light_proto.display_name,
            default_config={
                **light_proto.default_config,
                "protocol": "mqtt",
                "topic": "greenhouse/edge/light",
            },
            sampling_interval_seconds=180,
            tracking_enabled=True,
        )
        water_pump = Device(
            id=None,
            device_type="water_pump",
            role="actuator",
            device_family=self.family_key,
            display_name="Edge MQTT Relay Water Pump",
            default_config={
                "protocol": "mqtt",
                "topic": "greenhouse/edge/pump",
                "flow_rate_lpm": 4.0,
            },
        )
        grow_light = Device(
            id=None,
            device_type="grow_light",
            role="actuator",
            device_family=self.family_key,
            display_name="Edge MQTT PWM Grow Light Bar",
            default_config={
                "protocol": "mqtt",
                "topic": "greenhouse/edge/grow_light",
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