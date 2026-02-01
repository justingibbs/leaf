"""Event bus for emitting, persisting, and broadcasting events.

Central hub for all events in LEAF. Events are:
1. Persisted to the project's SQLite database
2. Broadcast to all connected WebSocket clients
"""

import asyncio
import secrets
from datetime import datetime
from typing import Any

from leaf.api.websocket import broadcast_event
from leaf.db.models import Event
from leaf.db.session import get_session
from leaf.projects.context import get_current_project
from leaf.watcher.file_watcher import FileEvent


class EventBus:
    """Central event bus for LEAF.

    Handles event emission, persistence, and broadcasting.
    """

    def __init__(self) -> None:
        self._queue: asyncio.Queue[Event] = asyncio.Queue()
        self._running = False
        self._task: asyncio.Task | None = None

    def _generate_event_id(self) -> str:
        """Generate a unique event ID."""
        return f"evt_{secrets.token_hex(8)}"

    async def emit(
        self,
        event_type: str,
        payload: dict[str, Any],
        parent_event_id: str | None = None,
    ) -> Event:
        """Emit an event.

        The event is persisted to the database and broadcast via WebSocket.

        Args:
            event_type: Event type (e.g., "file.created", "card.completed")
            payload: Event-specific data
            parent_event_id: Optional parent event ID for chained events

        Returns:
            The created Event
        """
        ctx = get_current_project()
        if ctx is None:
            raise RuntimeError("No active project")

        # Create event
        event = Event(
            id=self._generate_event_id(),
            type=event_type,
            timestamp=datetime.now(),
            payload=payload,
            status="pending",
            parent_event_id=parent_event_id,
        )

        # Persist to database
        gen = get_session(ctx.database_path)
        session = next(gen)
        try:
            session.add(event)
            session.commit()
            session.refresh(event)
        finally:
            try:
                next(gen)
            except StopIteration:
                pass

        # Broadcast via WebSocket
        await broadcast_event(
            event_type,
            {
                "event_id": event.id,
                "timestamp": event.timestamp.isoformat(),
                "payload": event.payload,
                "status": event.status,
            },
        )

        return event

    async def emit_file_event(self, file_event: FileEvent) -> Event:
        """Emit an event from a FileEvent.

        Convenience method for file watcher events.
        Also triggers execution of matching cards.
        """
        payload = {
            "path": str(file_event.path),
            "folder": str(file_event.folder),
            "filename": file_event.filename,
            "size": file_event.size,
            "watch_id": file_event.watch_id,
            "card_id": file_event.card_id,
        }

        event = await self.emit(file_event.type, payload)

        # Trigger card execution for this file event
        # Import here to avoid circular dependency
        from leaf.execution import process_file_event

        try:
            executions = await process_file_event(
                event_id=event.id,
                event_type=file_event.type,
                payload=payload,
            )

            # Update event status based on executions
            if executions:
                matched_card_ids = [ex.card_id for ex in executions]
                # Use first execution id for now (could be multiple)
                execution_id = executions[0].id if executions else None
                updated_event = await self.update_status(
                    event.id,
                    status="completed",
                    matched_cards=matched_card_ids,
                    execution_id=execution_id,
                )
                if updated_event:
                    event = updated_event
            else:
                # No matching cards - mark as completed with empty matches
                updated_event = await self.update_status(
                    event.id, status="completed", matched_cards=[]
                )
                if updated_event:
                    event = updated_event

        except Exception as e:
            # Mark event as failed if execution errors
            await self.update_status(event.id, status="failed")
            # Log the error but don't re-raise
            print(f"Error processing file event: {e}")

        return event

    async def update_status(
        self,
        event_id: str,
        status: str,
        matched_cards: list[str] | None = None,
        execution_id: str | None = None,
    ) -> Event | None:
        """Update an event's status.

        Args:
            event_id: Event ID
            status: New status (pending, processing, completed, failed)
            matched_cards: List of card IDs that matched this event
            execution_id: Associated execution ID

        Returns:
            Updated Event or None if not found
        """
        ctx = get_current_project()
        if ctx is None:
            raise RuntimeError("No active project")

        gen = get_session(ctx.database_path)
        session = next(gen)
        try:
            event = session.get(Event, event_id)
            if event is None:
                return None

            event.status = status
            if matched_cards is not None:
                event.matched_cards = matched_cards
            if execution_id is not None:
                event.execution_id = execution_id

            session.add(event)
            session.commit()
            session.refresh(event)

            # Broadcast status update
            await broadcast_event(
                "event.updated",
                {
                    "event_id": event.id,
                    "status": event.status,
                    "matched_cards": event.matched_cards,
                    "execution_id": event.execution_id,
                },
            )

            return event
        finally:
            try:
                next(gen)
            except StopIteration:
                pass


# Global event bus instance
event_bus = EventBus()


async def emit_event(
    event_type: str,
    payload: dict[str, Any],
    parent_event_id: str | None = None,
) -> Event:
    """Emit an event (convenience function).

    See EventBus.emit for details.
    """
    return await event_bus.emit(event_type, payload, parent_event_id)


async def emit_file_event(file_event: FileEvent) -> Event:
    """Emit a file event (convenience function).

    See EventBus.emit_file_event for details.
    """
    return await event_bus.emit_file_event(file_event)
