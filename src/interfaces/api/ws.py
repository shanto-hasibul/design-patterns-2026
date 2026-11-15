from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.application.realtime.connection_manager import dashboard_ws_manager

router = APIRouter(tags=["realtime"])


@router.websocket("/api/ws")
async def dashboard_websocket(websocket: WebSocket) -> None:
    """Dashboard WebSocket channel receiving live Observer events (not for ESP32 devices)."""
    await dashboard_ws_manager.connect(websocket)
    try:
        while True:
            # Keep socket alive; ignore any client ping text frames
            await websocket.receive_text()
    except WebSocketDisconnect:
        dashboard_ws_manager.disconnect(websocket)
    except Exception:
        dashboard_ws_manager.disconnect(websocket)