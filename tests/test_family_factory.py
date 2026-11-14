import pytest
from src.domain.devices.family_factory import (
    EdgeDeviceFamilyFactory,
    SimulationDeviceFamilyFactory,
    get_family_factory,
)


def test_simulation_factory_creates_coherent_kit() -> None:
    factory = SimulationDeviceFamilyFactory()
    devices = factory.create_device_set()

    assert len(devices) == 4
    assert all(d.device_family == "simulation" for d in devices)
    roles = {d.role for d in devices}
    assert roles == {"sensor", "actuator"}


def test_edge_factory_differs_from_simulation() -> None:
    sim_devices = SimulationDeviceFamilyFactory().create_device_set()
    edge_devices = EdgeDeviceFamilyFactory().create_device_set()

    assert len(edge_devices) == 4
    assert all(d.device_family == "edge" for d in edge_devices)
    assert {d.role for d in edge_devices} == {"sensor", "actuator"}

    sim_by_type = {d.device_type: d for d in sim_devices}
    edge_by_type = {d.device_type: d for d in edge_devices}

    assert sim_by_type.keys() == edge_by_type.keys()
    for dtype in sim_by_type:
        assert sim_by_type[dtype].device_family != edge_by_type[dtype].device_family
        assert (
            sim_by_type[dtype].default_config["protocol"]
            != edge_by_type[dtype].default_config["protocol"]
        )


def test_get_family_factory_registry_and_unknown_error() -> None:
    sim_factory = get_family_factory("simulation")
    edge_factory = get_family_factory("edge")

    assert sim_factory.family_key == "simulation"
    assert edge_factory.family_key == "edge"

    with pytest.raises(ValueError, match="Unknown device family"):
        get_family_factory("mars_colony")