import asyncio
from typing import Any
from fastapi import WebSocket


class DashboardConnectionManager:
    """Manages connected dashboard WebSocket clients and broadcasts JSON envelopes."""

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    @property
    def active_count(self) -> int:
        return len(self._connections)

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)
        if self._loop is None:
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                pass

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    async def broadcast_json(self, message: dict[str, Any]) -> None:
        dead: list[WebSocket] = []
        for ws in list(self._connections):
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections.discard(ws)

    def broadcast_threadsafe(self, message: dict[str, Any]) -> None:
        """Schedules a JSON broadcast on the FastAPI event loop from sync services or worker threads."""
        if not self._connections:
            return
        try:
            running_loop = asyncio.get_running_loop()
            running_loop.create_task(self.broadcast_json(message))
            return
        except RuntimeError:
            pass

        if self._loop is not None and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self.broadcast_json(message), self._loop)


dashboard_ws_manager = DashboardConnectionManager()