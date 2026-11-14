from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from src.application.alerts.subscribers import build_default_event_bus
from src.application.commands.dto import (
    CommandLogResponseDto,
    ExecuteCommandRequestDto,
)
from src.application.commands.service import CommandService
from src.application.devices.actuator_state_service import ActuatorNotFoundError
from src.domain.commands.base import UnknownCommandError
from src.infrastructure.persistence.actuator_state_repository import (
    ActuatorStateRepository,
)
from src.infrastructure.persistence.alert_repository import AlertRepository
from src.infrastructure.persistence.base import get_db
from src.infrastructure.persistence.command_log_repository import (
    CommandLogRepository,
)
from src.infrastructure.persistence.device_repository import DeviceRepository
from src.infrastructure.persistence.execution_log_repository import (
    ExecutionLogRepository,
)

router = APIRouter(prefix="/api/commands", tags=["commands"])


def get_command_service(db: Session = Depends(get_db)) -> CommandService:
    bus = build_default_event_bus(AlertRepository(db))
    return CommandService(
        device_repo=DeviceRepository(db),
        state_repo=ActuatorStateRepository(db),
        execution_log_repo=ExecutionLogRepository(db),
        command_log_repo=CommandLogRepository(db),
        event_bus=bus,
    )


@router.get("", response_model=list[CommandLogResponseDto])
def list_command_history(
    limit: int = Query(default=50, ge=1, le=200),
    device_id: UUID | None = Query(default=None, description="Optional device_id filter"),
    service: CommandService = Depends(get_command_service),
) -> list[CommandLogResponseDto]:
    return service.list_commands(limit=limit, device_id=device_id)


@router.post(
    "",
    response_model=CommandLogResponseDto,
    responses={
        200: {"model": CommandLogResponseDto, "description": "Command executed (success or failed)"},
        409: {"model": CommandLogResponseDto, "description": "Command rejected due to illegal actuator state"},
    },
)
def execute_command(
    payload: ExecuteCommandRequestDto,
    service: CommandService = Depends(get_command_service),
):
    try:
        result = service.execute_command(
            command_type=payload.command_type,
            device_id=payload.device_id,
            payload=payload.payload,
        )
    except ActuatorNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except UnknownCommandError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if result.status == "rejected":
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=result.model_dump(mode="json"),
        )

    return result