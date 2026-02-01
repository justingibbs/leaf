"""Project-level API routes.

These routes require an active project to be set.
They operate on the current project's database.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from leaf.cards import (
    CardCreate,
    CardDetailResponse,
    CardUpdate,
    create_card,
    delete_card,
    get_card,
    list_cards,
    update_card,
)
from leaf.core.events import emit_event
from leaf.db.models import Card, ChatMessage, Event, Execution
from leaf.db.session import get_session
from leaf.projects.context import ProjectContext, get_current_project

router = APIRouter(prefix="/api", tags=["project"])


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


def get_db(ctx: ProjectContext = Depends(require_project)) -> Session:
    """Dependency that provides a database session for the current project."""
    gen = get_session(ctx.database_path)
    session = next(gen)
    try:
        yield session
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


# --- Response Models ---


class ProjectInfoResponse(BaseModel):
    """Current project information."""

    id: str
    name: str
    path: str


class CardSummaryResponse(BaseModel):
    """Card summary response model."""

    id: str
    name: str
    description: str | None
    enabled: bool
    run_count: int
    created_at: str
    last_run_at: str | None


class EventResponse(BaseModel):
    """Event response model."""

    id: str
    type: str
    timestamp: str
    status: str
    payload: dict


class ExecutionResponse(BaseModel):
    """Execution response model."""

    id: str
    card_id: str
    status: str
    started_at: str | None
    completed_at: str | None
    error: str | None


class ManualTriggerResponse(BaseModel):
    """Response for manual card trigger."""

    event_id: str
    card_id: str
    message: str


# --- Project Info Routes ---


@router.get("/project")
async def get_project_info(ctx: ProjectContext = Depends(require_project)) -> ProjectInfoResponse:
    """Get information about the current project."""
    return ProjectInfoResponse(
        id=ctx.id,
        name=ctx.name,
        path=str(ctx.path),
    )


# --- Card Routes ---


@router.get("/cards")
async def api_list_cards(
    enabled_only: bool = False,
    ctx: ProjectContext = Depends(require_project),
) -> list[CardSummaryResponse]:
    """List all cards in the current project."""
    cards = list_cards(enabled_only=enabled_only)
    return [
        CardSummaryResponse(
            id=card.id,
            name=card.name,
            description=card.description,
            enabled=card.enabled,
            run_count=card.run_count,
            created_at=card.created_at.isoformat(),
            last_run_at=card.last_run_at.isoformat() if card.last_run_at else None,
        )
        for card in cards
    ]


@router.post("/cards")
async def api_create_card(
    data: CardCreate,
    ctx: ProjectContext = Depends(require_project),
) -> CardDetailResponse:
    """Create a new card."""
    try:
        card = create_card(data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    # Emit card created event
    await emit_event("card.created", {"card_id": card.id, "name": card.name})

    return _card_to_detail_response(card)


@router.get("/cards/{card_id}")
async def api_get_card(
    card_id: str,
    ctx: ProjectContext = Depends(require_project),
) -> CardDetailResponse:
    """Get a specific card by ID."""
    card = get_card(card_id)
    if not card:
        raise HTTPException(status_code=404, detail=f"Card not found: {card_id}")
    return _card_to_detail_response(card)


@router.put("/cards/{card_id}")
async def api_update_card(
    card_id: str,
    data: CardUpdate,
    ctx: ProjectContext = Depends(require_project),
) -> CardDetailResponse:
    """Update a card."""
    try:
        card = update_card(card_id, data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    # Emit card updated event
    await emit_event("card.updated", {"card_id": card.id})

    return _card_to_detail_response(card)


@router.delete("/cards/{card_id}")
async def api_delete_card(
    card_id: str,
    ctx: ProjectContext = Depends(require_project),
) -> dict:
    """Delete a card."""
    deleted = delete_card(card_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Card not found: {card_id}")

    # Emit card deleted event
    await emit_event("card.deleted", {"card_id": card_id})

    return {"status": "deleted", "card_id": card_id}


@router.post("/cards/{card_id}/enable")
async def api_enable_card(
    card_id: str,
    ctx: ProjectContext = Depends(require_project),
) -> CardDetailResponse:
    """Enable a card."""
    try:
        card = update_card(card_id, CardUpdate(enabled=True))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    await emit_event("card.enabled", {"card_id": card.id})
    return _card_to_detail_response(card)


@router.post("/cards/{card_id}/disable")
async def api_disable_card(
    card_id: str,
    ctx: ProjectContext = Depends(require_project),
) -> CardDetailResponse:
    """Disable a card."""
    try:
        card = update_card(card_id, CardUpdate(enabled=False))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    await emit_event("card.disabled", {"card_id": card.id})
    return _card_to_detail_response(card)


@router.post("/cards/{card_id}/run")
async def api_run_card(
    card_id: str,
    ctx: ProjectContext = Depends(require_project),
) -> ManualTriggerResponse:
    """Manually trigger a card.

    This creates a manual trigger event that will be processed
    by the execution engine (when implemented).
    """
    card = get_card(card_id)
    if not card:
        raise HTTPException(status_code=404, detail=f"Card not found: {card_id}")

    if not card.enabled:
        raise HTTPException(status_code=400, detail="Cannot run disabled card")

    # Emit manual trigger event
    event = await emit_event(
        "card.triggered",
        {
            "card_id": card_id,
            "trigger_type": "manual",
            "triggered_at": datetime.now().isoformat(),
        },
    )

    return ManualTriggerResponse(
        event_id=event.id,
        card_id=card_id,
        message=f"Card '{card.name}' triggered manually",
    )


# --- Event Routes ---


@router.get("/events")
async def list_events(
    limit: int = 50,
    offset: int = 0,
    event_type: str | None = None,
    session: Session = Depends(get_db),
) -> list[EventResponse]:
    """List events in the current project."""
    query = select(Event).order_by(Event.timestamp.desc())

    if event_type:
        query = query.where(Event.type == event_type)

    events = session.exec(query.offset(offset).limit(limit)).all()
    return [
        EventResponse(
            id=event.id,
            type=event.type,
            timestamp=event.timestamp.isoformat(),
            status=event.status,
            payload=event.payload,
        )
        for event in events
    ]


@router.get("/events/{event_id}")
async def get_event(event_id: str, session: Session = Depends(get_db)) -> Event:
    """Get a specific event by ID."""
    event = session.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail=f"Event not found: {event_id}")
    return event


# --- Execution Routes ---


@router.get("/executions")
async def list_executions(
    limit: int = 50,
    offset: int = 0,
    card_id: str | None = None,
    session: Session = Depends(get_db),
) -> list[ExecutionResponse]:
    """List executions in the current project."""
    query = select(Execution).order_by(Execution.started_at.desc())

    if card_id:
        query = query.where(Execution.card_id == card_id)

    executions = session.exec(query.offset(offset).limit(limit)).all()
    return [
        ExecutionResponse(
            id=ex.id,
            card_id=ex.card_id,
            status=ex.status,
            started_at=ex.started_at.isoformat() if ex.started_at else None,
            completed_at=ex.completed_at.isoformat() if ex.completed_at else None,
            error=ex.error,
        )
        for ex in executions
    ]


@router.get("/executions/{execution_id}")
async def get_execution(execution_id: str, session: Session = Depends(get_db)) -> Execution:
    """Get a specific execution by ID."""
    execution = session.get(Execution, execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail=f"Execution not found: {execution_id}")
    return execution


# --- Chat Routes ---


class ChatMessageRequest(BaseModel):
    """Request to send a chat message."""

    content: str


class ChatMessageResponse(BaseModel):
    """Response from the chat agent."""

    user_message_id: str
    assistant_message_id: str
    response: str


@router.post("/chat")
async def send_chat_message(
    request: ChatMessageRequest,
    ctx: ProjectContext = Depends(require_project),
    session: Session = Depends(get_db),
) -> ChatMessageResponse:
    """Send a message to the LEAF agent and get a response.

    This is a non-streaming endpoint. For streaming responses,
    use the /ws/chat WebSocket endpoint.
    """
    import secrets

    from leaf.agent import chat
    from leaf.db.models import ChatMessage as ChatMessageModel

    # Get message history from database
    db_messages = session.exec(
        select(ChatMessageModel).order_by(ChatMessageModel.created_at.asc()).limit(50)
    ).all()

    # Convert to format expected by agent
    message_history = [
        {"role": msg.role, "content": msg.content} for msg in db_messages
    ]

    # Save user message
    user_msg = ChatMessageModel(
        id=f"msg_{secrets.token_hex(8)}",
        role="user",
        content=request.content,
    )
    session.add(user_msg)
    session.commit()

    # Get response from agent
    try:
        response, _ = await chat(
            request.content,
            ctx.path,
            ctx.name,
            message_history if message_history else None,
        )
    except Exception as e:
        response = f"Error: {e}"

    # Save assistant message
    assistant_msg = ChatMessageModel(
        id=f"msg_{secrets.token_hex(8)}",
        role="assistant",
        content=response,
    )
    session.add(assistant_msg)
    session.commit()

    return ChatMessageResponse(
        user_message_id=user_msg.id,
        assistant_message_id=assistant_msg.id,
        response=response,
    )


@router.get("/chat/history")
async def get_chat_history(
    limit: int = 100,
    session: Session = Depends(get_db),
) -> list[ChatMessage]:
    """Get chat history for the current project."""
    messages = session.exec(
        select(ChatMessage).order_by(ChatMessage.created_at.asc()).limit(limit)
    ).all()
    return list(messages)


@router.delete("/chat/history")
async def clear_chat_history(
    session: Session = Depends(get_db),
) -> dict:
    """Clear chat history for the current project."""
    from leaf.db.models import ChatMessage as ChatMessageModel

    messages = session.exec(select(ChatMessageModel)).all()
    for msg in messages:
        session.delete(msg)
    session.commit()

    return {"status": "cleared", "count": len(messages)}


# --- Helper Functions ---


def _card_to_detail_response(card: Card) -> CardDetailResponse:
    """Convert a Card model to a CardDetailResponse."""
    return CardDetailResponse(
        id=card.id,
        name=card.name,
        description=card.description,
        user_prompt=card.user_prompt,
        trigger_config=card.trigger_config,
        program_config=card.program_config,
        program_path=card.program_path,
        timeout_seconds=card.timeout_seconds,
        retry_count=card.retry_count,
        enabled=card.enabled,
        allowed_outputs=card.allowed_outputs,
        created_at=card.created_at.isoformat(),
        updated_at=card.updated_at.isoformat(),
        last_run_at=card.last_run_at.isoformat() if card.last_run_at else None,
        run_count=card.run_count,
    )
