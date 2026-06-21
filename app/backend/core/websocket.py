"""
WebSocket Manager for real-time notifications
"""

from fastapi import WebSocket
from typing import Dict, Set
import json
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time notifications"""

    def __init__(self):
        # Store active connections by user_id
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        logger.info(f"WebSocket connected for user {user_id}")

    def disconnect(self, websocket: WebSocket, user_id: str):
        """Remove a WebSocket connection"""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"WebSocket disconnected for user {user_id}")

    async def send_personal_message(self, message: dict, user_id: str):
        """Send a message to a specific user (all their connections)"""
        if user_id in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending message to user {user_id}: {e}")
                    disconnected.add(connection)

            # Clean up disconnected connections
            for connection in disconnected:
                self.active_connections[user_id].discard(connection)

    async def broadcast_to_role(self, message: dict, role: str):
        """Broadcast a message to all users with a specific role"""
        # This would require tracking user roles, for now we'll implement per-user messaging
        pass

    async def notify_user_status_change(self, user_id: str, status: str, message: str):
        """Notify a user about their account status change"""
        notification = {
            "type": "user_status_change",
            "status": status,
            "message": message,
            "timestamp": str(json.dumps({"default": "now"})),
        }
        await self.send_personal_message(notification, user_id)

    async def notify_new_pending_user(self, admin_ids: list[str], user_data: dict):
        """Notify admins about a new pending user"""
        notification = {
            "type": "new_pending_user",
            "user": user_data,
            "timestamp": str(json.dumps({"default": "now"})),
        }
        for admin_id in admin_ids:
            await self.send_personal_message(notification, admin_id)


# Global connection manager instance
manager = ConnectionManager()

websocket_manager = manager
