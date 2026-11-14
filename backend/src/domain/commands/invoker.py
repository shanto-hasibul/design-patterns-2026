from typing import Any
from uuid import UUID

from src.domain.actuators.ports import ActuatorPort
from src.domain.commands.base import Command, UnknownCommandError
from src.domain.commands.light import SetLightLevelCommand
from src.domain.commands.pump import StartPumpCommand, StopPumpCommand

_COMMAND_REGISTRY: dict[str, type[Command]] = {
    "start_pump": StartPumpCommand,
    "stop_pump": StopPumpCommand,
    "set_light_level": SetLightLevelCommand,
}


def build_command(
    command_type: str,
    device_id: UUID,
    payload: dict[str, Any] | None = None,
) -> Command:
    normalized = command_type.strip().lower() if command_type else ""
    cmd_cls = _COMMAND_REGISTRY.get(normalized)
    if cmd_cls is None:
        supported = ", ".join(sorted(_COMMAND_REGISTRY.keys()))
        raise UnknownCommandError(
            f"Unknown command_type '{command_type}'. Supported commands: {supported}."
        )
    return cmd_cls(device_id=device_id, payload=payload)


class CommandInvoker:
    """Dispatches concrete Command instances against an ActuatorPort without command_type branching."""

    def invoke(self, command: Command, port: ActuatorPort) -> None:
        command.execute(port)