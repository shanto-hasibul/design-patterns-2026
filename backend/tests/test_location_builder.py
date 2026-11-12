import pytest
from src.domain.locations.config_builder import LocationConfigBuilder
from src.domain.locations.errors import ConfigurationError


def test_builder_success_path() -> None:
    config = (
        LocationConfigBuilder()
        .set_location_name("Main Greenhouse")
        .add_zone("Seedling Zone", 0.35, 0.70, {"cron": "0 6 * * *"})
        .add_zone("Flowering Zone", 0.25, 0.60, {"cron": "0 18 * * *"})
        .build()
    )

    assert config.location.name == "Main Greenhouse"
    assert len(config.location.zones) == 2
    assert config.location.zones[0].name == "Seedling Zone"
    assert config.location.zones[0].moisture_threshold_low == 0.35
    assert config.location.zones[0].moisture_threshold_high == 0.70


def test_builder_rejects_missing_location_name() -> None:
    builder = LocationConfigBuilder().add_zone("Zone A", 0.2, 0.6)
    with pytest.raises(ConfigurationError, match="Location name is required"):
        builder.build()


def test_builder_rejects_no_zones() -> None:
    builder = LocationConfigBuilder().set_location_name("Empty House")
    with pytest.raises(ConfigurationError, match="At least one zone is required"):
        builder.build()


def test_builder_rejects_invalid_threshold_ordering_and_bounds() -> None:
    builder_inverted = (
        LocationConfigBuilder()
        .set_location_name("Test House")
        .add_zone("Bad Zone", 0.75, 0.30)
    )
    with pytest.raises(ConfigurationError, match="strictly less than"):
        builder_inverted.build()

    builder_out_of_bounds = (
        LocationConfigBuilder()
        .set_location_name("Test House")
        .add_zone("Out of Bounds", -0.1, 1.2)
    )
    with pytest.raises(ConfigurationError, match="between 0.0 and 1.0"):
        builder_out_of_bounds.build()


def test_builder_rejects_duplicate_zone_names_in_same_location() -> None:
    builder = (
        LocationConfigBuilder()
        .set_location_name("Test House")
        .add_zone("Zone A", 0.2, 0.5)
        .add_zone("zone a", 0.3, 0.6)
    )
    with pytest.raises(ConfigurationError, match="Duplicate zone name"):
        builder.build()