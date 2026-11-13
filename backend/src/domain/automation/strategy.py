from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID

from src.domain.automation.context import (
    LocationAutomationContext,
    ZoneAutomationContext,
)


@dataclass(frozen=True)
class ZoneRecommendation:
    zone_id: UUID
    zone_name: str
    action: str  # "irrigate" | "wait"
    reason: str
    score: float | None = None


@dataclass(frozen=True)
class Recommendation:
    location_id: UUID
    strategy_key: str
    action: str  # "irrigate" | "wait"
    reason: str
    score: float | None = None
    zone_recommendations: tuple[ZoneRecommendation, ...] = ()


class AutomationStrategy(ABC):
    @property
    @abstractmethod
    def key(self) -> str:
        ...

    @abstractmethod
    def decide(self, context: LocationAutomationContext) -> Recommendation:
        ...


class ConservativeMoistureStrategy(AutomationStrategy):
    """Irrigates only when moisture drops strictly below moisture_threshold_low."""

    @property
    def key(self) -> str:
        return "conservative"

    def _decide_zone(self, zone: ZoneAutomationContext) -> ZoneRecommendation:
        if zone.latest_moisture is None:
            return ZoneRecommendation(
                zone_id=zone.zone_id,
                zone_name=zone.zone_name,
                action="wait",
                reason=f"No moisture sensor reading available in zone '{zone.zone_name}'.",
                score=0.0,
            )

        moisture = zone.latest_moisture
        low = zone.moisture_threshold_low
        high = zone.moisture_threshold_high

        if moisture < low:
            deficit = round(low - moisture, 4)
            return ZoneRecommendation(
                zone_id=zone.zone_id,
                zone_name=zone.zone_name,
                action="irrigate",
                reason=(
                    f"Zone '{zone.zone_name}' moisture ({moisture:.2f}) is below "
                    f"low threshold ({low:.2f}); conservative irrigation triggered."
                ),
                score=deficit,
            )

        return ZoneRecommendation(
            zone_id=zone.zone_id,
            zone_name=zone.zone_name,
            action="wait",
            reason=(
                f"Zone '{zone.zone_name}' moisture ({moisture:.2f}) is at or above "
                f"low threshold ({low:.2f}–{high:.2f}); conserving water."
            ),
            score=0.0,
        )

    def decide(self, context: LocationAutomationContext) -> Recommendation:
        if not context.zones:
            return Recommendation(
                location_id=context.location_id,
                strategy_key=self.key,
                action="wait",
                reason="No zones configured for this location.",
                score=0.0,
                zone_recommendations=(),
            )

        zone_recs = tuple(self._decide_zone(z) for z in context.zones)
        irrigating = [zr for zr in zone_recs if zr.action == "irrigate"]

        if irrigating:
            top_score = max((zr.score or 0.0) for zr in irrigating)
            summary = " | ".join(zr.reason for zr in irrigating)
            return Recommendation(
                location_id=context.location_id,
                strategy_key=self.key,
                action="irrigate",
                reason=summary,
                score=top_score,
                zone_recommendations=zone_recs,
            )

        summary = " | ".join(zr.reason for zr in zone_recs)
        return Recommendation(
            location_id=context.location_id,
            strategy_key=self.key,
            action="wait",
            reason=summary,
            score=0.0,
            zone_recommendations=zone_recs,
        )


class AggressiveMoistureStrategy(AutomationStrategy):
    """Irrigates proactively whenever moisture falls below the midpoint between low and high thresholds."""

    @property
    def key(self) -> str:
        return "aggressive"

    def _decide_zone(self, zone: ZoneAutomationContext) -> ZoneRecommendation:
        if zone.latest_moisture is None:
            return ZoneRecommendation(
                zone_id=zone.zone_id,
                zone_name=zone.zone_name,
                action="wait",
                reason=f"No moisture sensor reading available in zone '{zone.zone_name}'.",
                score=0.0,
            )

        moisture = zone.latest_moisture
        low = zone.moisture_threshold_low
        high = zone.moisture_threshold_high
        target_midpoint = round((low + high) / 2.0, 4)

        if moisture < target_midpoint:
            deficit = round(target_midpoint - moisture, 4)
            return ZoneRecommendation(
                zone_id=zone.zone_id,
                zone_name=zone.zone_name,
                action="irrigate",
                reason=(
                    f"Zone '{zone.zone_name}' moisture ({moisture:.2f}) is below "
                    f"aggressive target midpoint ({target_midpoint:.2f}, range {low:.2f}–{high:.2f}); "
                    f"proactive irrigation triggered."
                ),
                score=deficit,
            )

        return ZoneRecommendation(
            zone_id=zone.zone_id,
            zone_name=zone.zone_name,
            action="wait",
            reason=(
                f"Zone '{zone.zone_name}' moisture ({moisture:.2f}) meets or exceeds "
                f"aggressive target midpoint ({target_midpoint:.2f})."
            ),
            score=0.0,
        )

    def decide(self, context: LocationAutomationContext) -> Recommendation:
        if not context.zones:
            return Recommendation(
                location_id=context.location_id,
                strategy_key=self.key,
                action="wait",
                reason="No zones configured for this location.",
                score=0.0,
                zone_recommendations=(),
            )

        zone_recs = tuple(self._decide_zone(z) for z in context.zones)
        irrigating = [zr for zr in zone_recs if zr.action == "irrigate"]

        if irrigating:
            top_score = max((zr.score or 0.0) for zr in irrigating)
            summary = " | ".join(zr.reason for zr in irrigating)
            return Recommendation(
                location_id=context.location_id,
                strategy_key=self.key,
                action="irrigate",
                reason=summary,
                score=top_score,
                zone_recommendations=zone_recs,
            )

        summary = " | ".join(zr.reason for zr in zone_recs)
        return Recommendation(
            location_id=context.location_id,
            strategy_key=self.key,
            action="wait",
            reason=summary,
            score=0.0,
            zone_recommendations=zone_recs,
        )


_STRATEGIES: dict[str, type[AutomationStrategy]] = {
    "conservative": ConservativeMoistureStrategy,
    "aggressive": AggressiveMoistureStrategy,
}


def get_automation_strategy(strategy_key: str) -> AutomationStrategy:
    normalized = strategy_key.strip().lower() if strategy_key else ""
    cls = _STRATEGIES.get(normalized)
    if cls is None:
        supported = ", ".join(sorted(_STRATEGIES.keys()))
        raise ValueError(
            f"Unknown automation strategy '{strategy_key}'. Supported strategies: {supported}"
        )
    return cls()