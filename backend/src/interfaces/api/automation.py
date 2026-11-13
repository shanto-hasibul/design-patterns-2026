from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.application.automation.dto import (
    EvaluateResponseDto,
    SaveStrategyRequestDto,
    StrategyRuleResponseDto,
)
from src.application.automation.service import AutomationService, LocationNotFoundError
from src.infrastructure.persistence.automation_repository import AutomationRepository
from src.infrastructure.persistence.base import get_db

router = APIRouter(prefix="/api/locations/{location_id}/automation", tags=["automation"])


def get_automation_service(db: Session = Depends(get_db)) -> AutomationService:
    return AutomationService(AutomationRepository(db))


@router.get("/strategy", response_model=StrategyRuleResponseDto)
def get_location_strategy(
    location_id: UUID,
    service: AutomationService = Depends(get_automation_service),
) -> StrategyRuleResponseDto:
    try:
        return service.get_strategy(location_id)
    except LocationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.put("/strategy", response_model=StrategyRuleResponseDto)
def save_location_strategy(
    location_id: UUID,
    payload: SaveStrategyRequestDto,
    service: AutomationService = Depends(get_automation_service),
) -> StrategyRuleResponseDto:
    try:
        return service.save_strategy(location_id, payload.strategy_key)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except LocationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post("/evaluate", response_model=EvaluateResponseDto)
def evaluate_location_automation(
    location_id: UUID,
    strategy_key: str | None = Query(
        default=None,
        description="Optional one-off strategy key override; defaults to the persisted strategy.",
    ),
    service: AutomationService = Depends(get_automation_service),
) -> EvaluateResponseDto:
    try:
        return service.evaluate(location_id, override_strategy_key=strategy_key)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except LocationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc