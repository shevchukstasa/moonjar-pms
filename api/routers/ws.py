"""WebSocket router — imports ConnectionManager from websocket module."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query

from api.websocket import manager

router = APIRouter()


@router.websocket("/notifications")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    # TODO: Validate JWT token from query param
    user_id = "anonymous"  # Extract from token
    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming messages (ping/pong, etc.)
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
