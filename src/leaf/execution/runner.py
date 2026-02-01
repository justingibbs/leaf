"""Execution runner - coordinates card program execution.

Manages the lifecycle of executions including:
- Creating execution records
- Running programs via sandbox
- Handling retries
- Emitting events
"""

import asyncio
import secrets
from datetime import datetime
from pathlib import Path

from leaf.db.models import Execution
from leaf.db.session import get_session

from .sandbox import ExecutionResult, run_card_program


def generate_execution_id() -> str:
    """Generate a unique execution ID."""
    return f"exec_{secrets.token_hex(8)}"


async def execute_card(
    card_id: str,
    event_id: str | None = None,
    trigger_file: Path | None = None,
) -> Execution:
    """Execute a card's program.

    Creates an execution record, runs the program, handles retries,
    and emits appropriate events.

    Args:
        card_id: The card to execute
        event_id: The event that triggered this execution (optional)
        trigger_file: The file that triggered this execution (optional)

    Returns:
        The Execution record with results
    """
    # Import here to avoid circular dependencies
    from leaf.cards import get_card, increment_run_count
    from leaf.core.events import emit_event
    from leaf.projects.context import require_current_project

    ctx = require_current_project()
    card = get_card(card_id)

    if not card:
        raise ValueError(f"Card not found: {card_id}")

    if not card.enabled:
        raise ValueError(f"Card is disabled: {card_id}")

    # Create execution record
    execution_id = generate_execution_id()
    execution = Execution(
        id=execution_id,
        card_id=card_id,
        event_id=event_id,
        status="pending",
        started_at=datetime.now(),
    )

    # Save to database
    gen = get_session(ctx.database_path)
    session = next(gen)
    try:
        session.add(execution)
        session.commit()
        session.refresh(execution)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    # Emit execution started event
    await emit_event(
        "execution.started",
        {
            "execution_id": execution_id,
            "card_id": card_id,
            "event_id": event_id,
        },
    )

    # Get program configuration
    program_config = card.program_config or {}
    dependencies = program_config.get("dependencies", [])

    # Run with retries
    retry_count = card.retry_count
    attempts = 0
    result: ExecutionResult | None = None

    while attempts <= retry_count:
        attempts += 1

        # Update status to running
        execution.status = "running"
        gen = get_session(ctx.database_path)
        session = next(gen)
        try:
            session.add(execution)
            session.commit()
        finally:
            try:
                next(gen)
            except StopIteration:
                pass

        # Run the program
        program_path = ctx.path / card.program_path
        result = await run_card_program(
            program_path=program_path,
            working_dir=ctx.path,
            card_id=card_id,
            trigger_file=trigger_file,
            timeout_seconds=card.timeout_seconds,
            dependencies=dependencies,
        )

        if result.success:
            break

        # If failed and we have retries left, emit retry event
        if attempts <= retry_count:
            await emit_event(
                "execution.retry",
                {
                    "execution_id": execution_id,
                    "card_id": card_id,
                    "attempt": attempts,
                    "max_attempts": retry_count + 1,
                    "error": result.error or result.stderr[:200],
                },
            )
            # Brief delay before retry
            await asyncio.sleep(1)

    # Update execution with results
    execution.status = "completed" if result.success else "failed"
    execution.completed_at = result.completed_at
    execution.stdout = result.stdout
    execution.stderr = result.stderr
    execution.error = result.error
    execution.result = {
        "exit_code": result.exit_code,
        "duration_seconds": result.duration_seconds,
        "attempts": attempts,
    }

    # Save final state
    gen = get_session(ctx.database_path)
    session = next(gen)
    try:
        session.add(execution)
        session.commit()
        session.refresh(execution)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    # Increment card run count
    increment_run_count(card_id)

    # Emit completion/failure event
    if result.success:
        await emit_event(
            "execution.completed",
            {
                "execution_id": execution_id,
                "card_id": card_id,
                "duration_seconds": result.duration_seconds,
            },
        )
    else:
        await emit_event(
            "execution.failed",
            {
                "execution_id": execution_id,
                "card_id": card_id,
                "error": result.error or result.stderr[:500],
                "attempts": attempts,
            },
        )

    return execution


async def execute_card_for_event(
    card_id: str,
    event_id: str,
    payload: dict,
) -> Execution:
    """Execute a card in response to a file event.

    Args:
        card_id: The card to execute
        event_id: The triggering event ID
        payload: The event payload (contains file info)

    Returns:
        The Execution record
    """
    # Extract trigger file from payload
    trigger_file = None
    if "path" in payload:
        trigger_file = Path(payload["path"])

    return await execute_card(
        card_id=card_id,
        event_id=event_id,
        trigger_file=trigger_file,
    )


async def process_file_event(event_id: str, event_type: str, payload: dict) -> list[Execution]:
    """Process a file event and execute matching cards.

    Args:
        event_id: The event ID
        event_type: The event type (e.g., "file.created")
        payload: The event payload

    Returns:
        List of executions that were created
    """
    # Import here to avoid circular dependencies
    from leaf.cards import find_matching_cards

    # Find cards that match this event
    matching_cards = find_matching_cards(event_type, payload)

    if not matching_cards:
        return []

    # Execute each matching card
    executions = []
    for card in matching_cards:
        try:
            execution = await execute_card_for_event(
                card_id=card.id,
                event_id=event_id,
                payload=payload,
            )
            executions.append(execution)
        except Exception as e:
            # Log error but continue with other cards
            print(f"Error executing card {card.id}: {e}")

    return executions
