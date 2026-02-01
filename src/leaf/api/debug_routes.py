"""Debug API routes for testing.

These routes are for development/testing only.
They allow manual control of watches and events.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from leaf.core.events import emit_event
from leaf.projects.context import ProjectContext, get_current_project
from leaf.watcher import add_watch, get_watches, remove_watch

router = APIRouter(prefix="/api/debug", tags=["debug"])


# --- Dependencies ---


def require_project() -> ProjectContext:
    """Dependency that requires an active project."""
    ctx = get_current_project()
    if ctx is None:
        raise HTTPException(
            status_code=400,
            detail="No active project. Use POST /api/projects/switch first.",
        )
    return ctx


# --- Request/Response Models ---


class AddWatchRequest(BaseModel):
    """Request to add a folder watch."""

    folder: str  # Relative to project root, or absolute
    pattern: str = "*"


class WatchResponse(BaseModel):
    """Watch information response."""

    id: str
    folder: str
    pattern: str
    card_id: str | None


class EmitEventRequest(BaseModel):
    """Request to emit a test event."""

    type: str
    payload: dict


class EventResponse(BaseModel):
    """Event response."""

    id: str
    type: str
    timestamp: str
    status: str


# --- Watch Routes ---


@router.post("/watch")
async def debug_add_watch(
    request: AddWatchRequest,
    ctx: ProjectContext = Depends(require_project),
) -> WatchResponse:
    """Add a folder watch for testing.

    The folder can be relative to the project root or absolute.
    """
    # Resolve folder path
    folder_path = Path(request.folder)
    if not folder_path.is_absolute():
        folder_path = ctx.path / request.folder

    folder_path = folder_path.resolve()

    # Validate folder exists
    if not folder_path.exists():
        raise HTTPException(status_code=404, detail=f"Folder not found: {folder_path}")

    if not folder_path.is_dir():
        raise HTTPException(status_code=400, detail=f"Not a directory: {folder_path}")

    # Validate folder is within project
    try:
        folder_path.relative_to(ctx.path)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Folder must be within project: {ctx.path}",
        )

    try:
        config = add_watch(
            folder=folder_path,
            pattern=request.pattern,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return WatchResponse(
        id=config.id,
        folder=str(config.folder),
        pattern=config.pattern,
        card_id=config.card_id,
    )


@router.delete("/watch/{watch_id}")
async def debug_remove_watch(
    watch_id: str,
    ctx: ProjectContext = Depends(require_project),
) -> dict:
    """Remove a folder watch."""
    remove_watch(watch_id)
    return {"status": "removed", "watch_id": watch_id}


@router.get("/watches")
async def debug_list_watches(
    ctx: ProjectContext = Depends(require_project),
) -> list[WatchResponse]:
    """List all active watches."""
    watches = get_watches()
    return [
        WatchResponse(
            id=w.id,
            folder=str(w.folder),
            pattern=w.pattern,
            card_id=w.card_id,
        )
        for w in watches
    ]


# --- Event Routes ---


@router.post("/event")
async def debug_emit_event(
    request: EmitEventRequest,
    ctx: ProjectContext = Depends(require_project),
) -> EventResponse:
    """Emit a test event.

    Useful for testing event flow without file changes.
    """
    event = await emit_event(request.type, request.payload)

    return EventResponse(
        id=event.id,
        type=event.type,
        timestamp=event.timestamp.isoformat(),
        status=event.status,
    )
