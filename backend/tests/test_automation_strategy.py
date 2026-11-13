from uuid import uuid4
import pytest

from src.domain.automation.context import (
    LocationAutomationContext,
    ZoneAutomationContext,
)
from src.domain.automation.strategy import (
    AggressiveMoistureStrategy,
    ConservativeMoistureStrategy,
    get_automation_strategy,
)


def _make_context(latest_moisture: float | None, low: float = 0.30, high: float = 0.70) -> LocationAutomationContext:
    loc_id = uuid4()
    zone_id = uuid4()
    return LocationAutomationContext(
        location_id=loc_id,
        location_name="North Greenhouse",
        zones=(
            ZoneAutomationContext(
                location_id=loc_id,
                zone_id=zone_id,
                zone_name="Zone A",
                moisture_threshold_low=low,
                moisture_threshold_high=high,
                latest_moisture=latest_moisture,
            ),
        ),
    )


def test_conservative_vs_aggressive_differ_on_same_context() -> None:
    # Moisture 0.42 is above low (0.30) but below midpoint (0.50)
    context = _make_context(latest_moisture=0.42, low=0.30, high=0.70)

    conservative_rec = ConservativeMoistureStrategy().decide(context)
    aggressive_rec = AggressiveMoistureStrategy().decide(context)

    assert conservative_rec.action == "wait"
    assert aggressive_rec.action == "irrigate"
    assert conservative_rec.reason != aggressive_rec.reason


def test_conservative_irrigates_below_low_threshold() -> None:
    context = _make_context(latest_moisture=0.22, low=0.30, high=0.70)
    rec = ConservativeMoistureStrategy().decide(context)

    assert rec.action == "irrigate"
    assert rec.score == pytest.approx(0.08)


def test_zone_without_moisture_sensor_waits_with_clear_reason() -> None:
    context = _make_context(latest_moisture=None)
    rec = AggressiveMoistureStrategy().decide(context)

    assert rec.action == "wait"
    assert "No moisture sensor reading available" in rec.reason


def test_unknown_strategy_key_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Unknown automation strategy"):
        get_automation_strategy("random_rain_dance")