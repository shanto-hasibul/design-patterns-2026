from uuid import UUID
from pydantic import BaseModel


class SaveStrategyRequestDto(BaseModel):
    strategy_key: str


class StrategyRuleResponseDto(BaseModel):
    location_id: UUID
    strategy_key: str


class ZoneRecommendationDto(BaseModel):
    zone_id: UUID
    zone_name: str
    action: str
    reason: str
    score: float | None = None


class EvaluateResponseDto(BaseModel):
    location_id: UUID
    strategy_key: str
    action: str
    reason: str
    score: float | None = None
    zones: list[ZoneRecommendationDto] = []