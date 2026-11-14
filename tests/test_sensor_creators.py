import pytest
from src.domain.sensors.creators import (
    LightSensorCreator,
    MoistureSensorCreator,
    get_creator,
)


def test_moisture_creator_defaults() -> None:
    creator = MoistureSensorCreator()
    sensor = creator.create_sensor()

    assert sensor.id is None
    assert sensor.device_type == "moisture_sensor"
    assert sensor.display_name == "Soil moisture sensor"
    assert "moisture_threshold" in sensor.default_config
    assert sensor.default_config["unit"] == "vwc"


def test_light_creator_defaults() -> None:
    creator = LightSensorCreator()
    sensor = creator.create_sensor()

    assert sensor.id is None
    assert sensor.device_type == "light_sensor"
    assert sensor.display_name == "Ambient light sensor"
    assert sensor.default_config["unit"] == "lux"
    assert sensor.default_config != MoistureSensorCreator().create_sensor().default_config


def test_get_creator_registry_and_unknown_type() -> None:
    moisture = get_creator("moisture").create_sensor(display_name="Zone A Moisture")
    light = get_creator("light").create_sensor()

    assert moisture.device_type == "moisture_sensor"
    assert moisture.display_name == "Zone A Moisture"
    assert light.device_type == "light_sensor"

    with pytest.raises(ValueError, match="Unknown sensor type"):
        get_creator("unknown_sensor")