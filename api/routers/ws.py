"""WebSocket router — authenticated real-time notifications."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from jwt.exceptions import PyJWTError as JWTError

from api.auth import decode_token
from api.websocket import manager
from api.database import SessionLocal
from api.models import ActiveSession

router = APIRouter()


def _validate_ws_token(token: str) -> str | None:
    """Validate JWT from query param or cookie, return user_id or None.

    Also checks that the session (JTI) has not been revoked.
    """
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        jti = payload.get("jti")
        user_id = payload.get("sub")
        if not user_id:
            return None
        # Check session revocation
        if jti:
            db = SessionLocal()
            try:
                session = db.query(ActiveSession).filter(
                    ActiveSession.token_jti == jti,
                    ActiveSession.revoked == False,
                ).first()
                if not session:
                    return None
            finally:
                db.close()
        return user_id
    except (JWTError, Exception):
        return None


@router.websocket("/notifications")
async def websocket_endpoint(websocket: WebSocket, token: str = Query("")):
    user_id = None

    # 1. Try token from query param (explicit JWT)
    if token and token != "cookie":
        user_id = _validate_ws_token(token)

    # 2. Fallback: read access_token from cookies (HttpOnly cookie sent during WS handshake)
    if not user_id:
        cookie_token = websocket.cookies.get("access_token")
        if cookie_token:
            user_id = _validate_ws_token(cookie_token)

    if not user_id:
        await websocket.close(code=4001, reason="Authentication required")
        return

    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming messages (ping/pong keepalive)
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
