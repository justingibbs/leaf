"""WebSocket handler for real-time event streaming.

Clients connect to /ws and receive events as they occur.
"""

import asyncio
import json
from datetime import datetime
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from leaf.projects.context import get_current_project


class ConnectionManager:
    """Manages WebSocket connections and broadcasts events."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast a message to all connected clients."""
        if not self.active_connections:
            return

        # Serialize the message once
        data = json.dumps(message, default=str)

        # Send to all connections, removing any that fail
        disconnected = []
        async with self._lock:
            for connection in self.active_connections:
                try:
                    await connection.send_text(data)
                except Exception:
                    disconnected.append(connection)

            for connection in disconnected:
                self.active_connections.remove(connection)

    async def send_personal(self, websocket: WebSocket, message: dict[str, Any]) -> None:
        """Send a message to a specific client."""
        data = json.dumps(message, default=str)
        await websocket.send_text(data)

    @property
    def connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self.active_connections)


# Global connection manager instance
manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint handler.

    Clients connect and receive real-time events.
    """
    await manager.connect(websocket)

    # Send initial connection message
    ctx = get_current_project()
    await manager.send_personal(
        websocket,
        {
            "type": "connected",
            "timestamp": datetime.now().isoformat(),
            "project": {
                "id": ctx.id,
                "name": ctx.name,
            }
            if ctx
            else None,
        },
    )

    try:
        while True:
            # Wait for messages from client (for future ping/pong or commands)
            data = await websocket.receive_text()

            # Parse and handle client messages
            try:
                message = json.loads(data)
                msg_type = message.get("type")

                if msg_type == "ping":
                    await manager.send_personal(
                        websocket,
                        {"type": "pong", "timestamp": datetime.now().isoformat()},
                    )
            except json.JSONDecodeError:
                pass  # Ignore malformed messages

    except WebSocketDisconnect:
        await manager.disconnect(websocket)


async def broadcast_event(event_type: str, payload: dict[str, Any]) -> None:
    """Broadcast an event to all connected WebSocket clients.

    This is the main entry point for pushing events to the UI.
    Called by the Event concept when events are emitted.
    """
    await manager.broadcast(
        {
            "type": event_type,
            "timestamp": datetime.now().isoformat(),
            "payload": payload,
        }
    )


async def chat_websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for streaming chat responses.

    Clients send messages and receive streaming responses from the agent.
    """
    await manager.connect(websocket)

    # Send initial connection message
    ctx = get_current_project()
    if not ctx:
        await manager.send_personal(
            websocket,
            {
                "type": "error",
                "message": "No active project. Open a project first.",
            },
        )
        await websocket.close()
        return

    await manager.send_personal(
        websocket,
        {
            "type": "chat.connected",
            "timestamp": datetime.now().isoformat(),
            "project": {"id": ctx.id, "name": ctx.name},
        },
    )

    # Store message history for the session
    message_history: list = []

    try:
        while True:
            # Wait for messages from client
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                msg_type = message.get("type")

                if msg_type == "chat.message":
                    user_message = message.get("content", "")
                    if not user_message:
                        continue

                    # Import here to avoid circular dependency
                    from leaf.agent import chat_stream

                    # Send start indicator
                    await manager.send_personal(
                        websocket,
                        {
                            "type": "chat.response.start",
                            "timestamp": datetime.now().isoformat(),
                        },
                    )

                    # Stream the response
                    full_response = ""
                    try:
                        async for chunk in chat_stream(
                            user_message,
                            ctx.path,
                            ctx.name,
                            message_history if message_history else None,
                        ):
                            full_response += chunk
                            await manager.send_personal(
                                websocket,
                                {
                                    "type": "chat.response.chunk",
                                    "content": chunk,
                                },
                            )

                        # Send end indicator with full response
                        await manager.send_personal(
                            websocket,
                            {
                                "type": "chat.response.end",
                                "content": full_response,
                                "timestamp": datetime.now().isoformat(),
                            },
                        )

                        # Update message history
                        message_history.append({"role": "user", "content": user_message})
                        message_history.append({"role": "assistant", "content": full_response})

                    except Exception as e:
                        await manager.send_personal(
                            websocket,
                            {
                                "type": "chat.error",
                                "message": str(e),
                                "timestamp": datetime.now().isoformat(),
                            },
                        )

                elif msg_type == "chat.clear":
                    # Clear message history
                    message_history = []
                    await manager.send_personal(
                        websocket,
                        {
                            "type": "chat.cleared",
                            "timestamp": datetime.now().isoformat(),
                        },
                    )

                elif msg_type == "ping":
                    await manager.send_personal(
                        websocket,
                        {"type": "pong", "timestamp": datetime.now().isoformat()},
                    )

            except json.JSONDecodeError:
                await manager.send_personal(
                    websocket,
                    {"type": "error", "message": "Invalid JSON"},
                )

    except WebSocketDisconnect:
        await manager.disconnect(websocket)
