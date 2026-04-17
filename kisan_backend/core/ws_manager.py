import asyncio
from typing import Dict, List
from fastapi import WebSocket
from loguru import logger
import json

class ConnectionManager:
    """Manages active WebSocket connections by user_id."""
    
    def __init__(self):
        # Map user_id to a list of active WebSocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # Track pending disconnect events for handovers
        self._disconnect_events: Dict[str, asyncio.Event] = {}

    async def connect(self, user_id: str, websocket: WebSocket, heartbeat_timer: int):
        await websocket.accept()
        u_id = str(user_id)
        if u_id not in self.active_connections:
            self.active_connections[u_id] = []
        self.active_connections[u_id].append(websocket)
        
        logger.info(f"🔌 [SOCKET] Connection accepted for User: {u_id}")

        # Send standardized "connected" event with the heartbeat timer
        await self.send_event(
            websocket,
            event="system",
            event_type="connected",
            data={"heartbeat_timer": heartbeat_timer, "message": "Session Guard Active"}
        )

    async def send_event(self, websocket: WebSocket, event: str, event_type: str, data: dict, request_id: str = None):
        """Sends a message following the standardized envelope."""
        payload = {
            "event": event,
            "type": event_type,
            "data": {
                "success": data.get("success", True),
                "message": data.get("message", "Success"),
                "data": data.get("data", data) if "data" not in data else data["data"],
                "request_id": request_id
            }
        }
        # Avoid recursion if data already has success/message
        if "success" in data and "message" in data:
            payload["data"] = {**data, "request_id": request_id}

        await websocket.send_json(payload)

    def disconnect(self, user_id: str, websocket: WebSocket):
        u_id = str(user_id)
        if u_id in self.active_connections:
            if websocket in self.active_connections[u_id]:
                self.active_connections[u_id].remove(websocket)
            if not self.active_connections[u_id]:
                del self.active_connections[u_id]
                # Signal any pending handover waits
                if u_id in self._disconnect_events:
                    self._disconnect_events[u_id].set()
        
        logger.info(f"🧹 [SOCKET] Connection closed for User: {u_id}")

    async def broadcast_to_user(self, user_id: str, event_data: dict):
        """Sends a message to all active sessions of a specific user."""
        u_id = str(user_id)
        if u_id in self.active_connections:
            for connection in list(self.active_connections[u_id]):
                try:
                    await connection.send_json(event_data)
                except Exception:
                    self.disconnect(u_id, connection)

    async def wait_for_user_disconnect(self, user_id: str, timeout: float = 5.0) -> bool:
        """
        Wait until all active sockets for a specific user are closed.
        Returns True if disconnected, False on timeout.
        """
        u_id = str(user_id)
        if u_id not in self.active_connections or not self.active_connections[u_id]:
            return True
        
        event = asyncio.Event()
        self._disconnect_events[u_id] = event
        
        try:
            import asyncio as aio
            await aio.wait_for(event.wait(), timeout=timeout)
            return True
        except Exception:
            # Timeout or other error
            return False
        finally:
            self._disconnect_events.pop(u_id, None)

# Singleton instance
manager = ConnectionManager()
