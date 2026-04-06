"""
Moonjar PMS — WebSocket connection manager.
"""

import json
import logging
from typing import Dict, List
from fastapi import WebSocket

logger = logging.getLogger("moonjar.websocket")


class ConnectionManager:
    """Manages WebSocket connections per user."""

    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.user_factories: Dict[str, str] = {}  # user_id -> factory_id

    async def connect(self, websocket: WebSocket, user_id: str, factory_id: str = None):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        if factory_id:
            self.user_factories[user_id] = factory_id
        logger.info(f"WebSocket connected: user={user_id} factory={factory_id}")

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            self.active_connections[user_id] = [
                ws for ws in self.active_connections[user_id] if ws != websocket
            ]
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                self.user_factories.pop(user_id, None)
        logger.info(f"WebSocket disconnected: user={user_id}")

    async def send_to_user(self, user_id: str, message: dict):
        """Send message to all connections of a specific user."""
        if user_id in self.active_connections:
            data = json.dumps(message)
            for ws in self.active_connections[user_id]:
                try:
                    await ws.send_text(data)
                except Exception:
                    pass

    async def broadcast(self, message: dict, exclude_user: str = None):
        """Broadcast message to all connected users."""
        data = json.dumps(message)
        for user_id, connections in self.active_connections.items():
            if user_id == exclude_user:
                continue
            for ws in connections:
                try:
                    await ws.send_text(data)
                except Exception:
                    pass

    async def send_to_factory(self, factory_id: str, message: dict):
        """Send message to all users in a specific factory."""
        data = json.dumps(message)
        for user_id, connections in self.active_connections.items():
            if self.user_factories.get(user_id) != factory_id:
                continue
            for ws in connections:
                try:
                    await ws.send_text(data)
                except Exception:
                    pass

    @property
    def connection_count(self) -> int:
        return sum(len(conns) for conns in self.active_connections.values())


# Global manager instance
manager = ConnectionManager()
