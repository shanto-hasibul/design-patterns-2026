from uuid import UUID

from src.application.automation.dto import (
    EvaluateResponseDto,
    StrategyRuleResponseDto,
    ZoneRecommendationDto,
)
from src.domain.automation.strategy import get_automation_strategy
from src.infrastructure.persistence.automation_repository import AutomationRepository


class LocationNotFoundError(LookupError):
    """Raised when the requested location does not exist."""


class AutomationService:
    def __init__(self, repo: AutomationRepository) -> None:
        self._repo = repo

    def get_strategy(self, location_id: UUID) -> StrategyRuleResponseDto:
        context = self._repo.build_location_context(location_id)
        if context is None:
            raise LocationNotFoundError(f"Location '{location_id}' not found.")

        key = self._repo.get_strategy_key(location_id)
        return StrategyRuleResponseDto(location_id=location_id, strategy_key=key)

    def save_strategy(
        self, location_id: UUID, strategy_key: str
    ) -> StrategyRuleResponseDto:
        # Validate strategy key before persisting
        strategy = get_automation_strategy(strategy_key)

        context = self._repo.build_location_context(location_id)
        if context is None:
            raise LocationNotFoundError(f"Location '{location_id}' not found.")

        persisted_key = self._repo.upsert_strategy(location_id, strategy.key)
        return StrategyRuleResponseDto(
            location_id=location_id,
            strategy_key=persisted_key,
        )

    def evaluate(
        self,
        location_id: UUID,
        override_strategy_key: str | None = None,
    ) -> EvaluateResponseDto:
        context = self._repo.build_location_context(location_id)
        if context is None:
            raise LocationNotFoundError(f"Location '{location_id}' not found.")

        active_key = (
            override_strategy_key
            if override_strategy_key
            else self._repo.get_strategy_key(location_id)
        )
        strategy = get_automation_strategy(active_key)
        rec = strategy.decide(context)

        return EvaluateResponseDto(
            location_id=rec.location_id,
            strategy_key=rec.strategy_key,
            action=rec.action,
            reason=rec.reason,
            score=rec.score,
            zones=[
                ZoneRecommendationDto(
                    zone_id=zr.zone_id,
                    zone_name=zr.zone_name,
                    action=zr.action,
                    reason=zr.reason,
                    score=zr.score,
                )
                for zr in rec.zone_recommendations
            ],
        )