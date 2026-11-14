from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.application.actuators.dto import (
    ActuatorExecutionDto,
    ApplyActuatorRequestDto,
)
from src.application.actuators.service import ActuatorExecutionService
from src.application.devices.actuator_state_service import ActuatorNotFoundError
from src.infrastructure.persistence.actuator_state_repository import (
    ActuatorStateRepository,
)
from src.infrastructure.persistence.base import get_db
from src.infrastructure.persistence.device_repository import DeviceRepository
from src.infrastructure.persistence.execution_log_repository import (
    ExecutionLogRepository,
)

router = APIRouter(prefix="/api/actuators", tags=["actuators"])


def get_actuator_execution_service(
    db: Session = Depends(get_db),
) -> ActuatorExecutionService:
    return ActuatorExecutionService(
        device_repo=DeviceRepository(db),
        state_repo=ActuatorStateRepository(db),
        log_repo=ExecutionLogRepository(db),
    )


@router.get("/executions", response_model=list[ActuatorExecutionDto])
def list_actuator_executions(
    limit: int = Query(default=20, ge=1, le=200),
    device_id: UUID | None = Query(default=None, description="Optional actuator device_id filter"),
    service: ActuatorExecutionService = Depends(get_actuator_execution_service),
) -> list[ActuatorExecutionDto]:
    return service.list_executions(limit=limit, device_id=device_id)


@router.post(
    "/{device_id}/apply",
    response_model=ActuatorExecutionDto,
    status_code=status.HTTP_201_CREATED,
)
def apply_actuator_command(
    device_id: UUID,
    payload: ApplyActuatorRequestDto,
    service: ActuatorExecutionService = Depends(get_actuator_execution_service),
) -> ActuatorExecutionDto:
    try:
        return service.apply_command(device_id, payload.command, payload.payload)
    except ActuatorNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc