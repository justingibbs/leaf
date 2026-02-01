"""API routes for execution management."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import select

from leaf.db.models import Execution
from leaf.db.session import get_session
from leaf.projects.context import require_current_project

router = APIRouter(prefix="/api/executions", tags=["executions"])


class ExecutionResponse(BaseModel):
    """Response model for an execution."""

    id: str
    card_id: str
    event_id: str | None
    status: str
    started_at: str | None
    completed_at: str | None
    stdout: str | None
    stderr: str | None
    error: str | None
    result: dict | None


class ManualExecutionRequest(BaseModel):
    """Request to manually execute a card."""

    card_id: str


@router.get("")
async def list_executions(
    card_id: str | None = None,
    status: str | None = None,
    limit: int = 50,
) -> list[ExecutionResponse]:
    """List executions with optional filtering.

    Args:
        card_id: Filter by card ID
        status: Filter by status (pending, running, completed, failed)
        limit: Maximum number of results
    """
    ctx = require_current_project()

    gen = get_session(ctx.database_path)
    session = next(gen)
    try:
        query = select(Execution).order_by(Execution.started_at.desc())

        if card_id:
            query = query.where(Execution.card_id == card_id)
        if status:
            query = query.where(Execution.status == status)

        query = query.limit(limit)
        executions = session.exec(query).all()

        return [
            ExecutionResponse(
                id=ex.id,
                card_id=ex.card_id,
                event_id=ex.event_id,
                status=ex.status,
                started_at=ex.started_at.isoformat() if ex.started_at else None,
                completed_at=ex.completed_at.isoformat() if ex.completed_at else None,
                stdout=ex.stdout,
                stderr=ex.stderr,
                error=ex.error,
                result=ex.result,
            )
            for ex in executions
        ]
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


@router.get("/{execution_id}")
async def get_execution(execution_id: str) -> ExecutionResponse:
    """Get a specific execution by ID."""
    ctx = require_current_project()

    gen = get_session(ctx.database_path)
    session = next(gen)
    try:
        execution = session.get(Execution, execution_id)
        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")

        return ExecutionResponse(
            id=execution.id,
            card_id=execution.card_id,
            event_id=execution.event_id,
            status=execution.status,
            started_at=execution.started_at.isoformat() if execution.started_at else None,
            completed_at=execution.completed_at.isoformat() if execution.completed_at else None,
            stdout=execution.stdout,
            stderr=execution.stderr,
            error=execution.error,
            result=execution.result,
        )
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


@router.post("/manual")
async def execute_card_manually(request: ManualExecutionRequest) -> ExecutionResponse:
    """Manually trigger execution of a card.

    This bypasses the normal trigger mechanism and runs the card immediately.
    """
    from leaf.execution import execute_card

    try:
        execution = await execute_card(card_id=request.card_id)

        return ExecutionResponse(
            id=execution.id,
            card_id=execution.card_id,
            event_id=execution.event_id,
            status=execution.status,
            started_at=execution.started_at.isoformat() if execution.started_at else None,
            completed_at=execution.completed_at.isoformat() if execution.completed_at else None,
            stdout=execution.stdout,
            stderr=execution.stderr,
            error=execution.error,
            result=execution.result,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Execution failed: {e}")
