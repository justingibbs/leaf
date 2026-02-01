"""Card registry - CRUD operations for cards.

Manages card lifecycle including creation, updates, deletion,
and coordinating with the file watcher for trigger setup.
"""

import secrets
from datetime import datetime

from sqlmodel import select

from leaf.db.models import Card
from leaf.db.session import get_session

from .models import CardCreate, CardUpdate, TriggerConfig


def generate_card_id() -> str:
    """Generate a unique card ID."""
    return f"card_{secrets.token_hex(8)}"


def generate_program_slug(name: str) -> str:
    """Generate a URL-safe slug from a card name."""
    # Simple slug generation
    slug = name.lower().replace(" ", "-")
    # Remove non-alphanumeric characters except hyphens
    slug = "".join(c for c in slug if c.isalnum() or c == "-")
    # Add a random suffix for uniqueness
    suffix = secrets.token_hex(3)
    return f"{slug}-{suffix}"


def create_card(data: CardCreate) -> Card:
    """Create a new card.

    Args:
        data: Card creation data

    Returns:
        The created Card
    """
    # Import here to avoid circular dependency
    from leaf.projects.context import require_current_project

    ctx = require_current_project()

    card_id = generate_card_id()
    program_slug = generate_program_slug(data.name)
    program_path = f".leaf/programs/{program_slug}"

    # Create the program directory
    program_dir = ctx.path / program_path
    program_dir.mkdir(parents=True, exist_ok=True)

    # Create a placeholder main.py
    main_file = program_dir / "main.py"
    if not main_file.exists():
        main_file.write_text(
            f'''"""Generated program for card: {data.name}

User prompt: {data.user_prompt}
"""

import sys
from pathlib import Path


def main():
    """Main entry point."""
    # TODO: Implement based on user prompt
    print(f"Card triggered with args: {{sys.argv[1:]}}")


if __name__ == "__main__":
    main()
'''
        )

    card = Card(
        id=card_id,
        name=data.name,
        description=data.description,
        user_prompt=data.user_prompt,
        trigger_config=data.trigger_config.model_dump(),
        program_config=data.program_config.model_dump(),
        program_path=program_path,
        timeout_seconds=data.timeout_seconds,
        retry_count=data.retry_count,
        enabled=data.enabled,
        allowed_outputs=data.allowed_outputs,
    )

    # Persist to database
    gen = get_session(ctx.database_path)
    session = next(gen)
    try:
        session.add(card)
        session.commit()
        session.refresh(card)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    # Set up file watcher if this is a file-based trigger
    if data.enabled:
        _setup_card_watch(card)

    return card


def get_card(card_id: str) -> Card | None:
    """Get a card by ID.

    Args:
        card_id: The card ID

    Returns:
        The Card or None if not found
    """
    # Import here to avoid circular dependency
    from leaf.projects.context import require_current_project

    ctx = require_current_project()

    gen = get_session(ctx.database_path)
    session = next(gen)
    try:
        return session.get(Card, card_id)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def list_cards(enabled_only: bool = False) -> list[Card]:
    """List all cards in the current project.

    Args:
        enabled_only: If True, only return enabled cards

    Returns:
        List of cards
    """
    # Import here to avoid circular dependency
    from leaf.projects.context import require_current_project

    ctx = require_current_project()

    gen = get_session(ctx.database_path)
    session = next(gen)
    try:
        query = select(Card).order_by(Card.created_at.desc())
        if enabled_only:
            query = query.where(Card.enabled.is_(True))
        return list(session.exec(query).all())
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def update_card(card_id: str, data: CardUpdate) -> Card:
    """Update a card.

    Args:
        card_id: The card ID
        data: Update data (only provided fields will be updated)

    Returns:
        The updated Card

    Raises:
        ValueError: If card not found
    """
    # Import here to avoid circular dependency
    from leaf.projects.context import require_current_project

    ctx = require_current_project()

    gen = get_session(ctx.database_path)
    session = next(gen)
    try:
        card = session.get(Card, card_id)
        if not card:
            raise ValueError(f"Card not found: {card_id}")

        # Track if we need to update the watcher
        old_enabled = card.enabled
        old_trigger = TriggerConfig(**card.trigger_config)

        # Apply updates
        if data.name is not None:
            card.name = data.name
        if data.description is not None:
            card.description = data.description
        if data.trigger_config is not None:
            card.trigger_config = data.trigger_config.model_dump()
        if data.program_config is not None:
            card.program_config = data.program_config.model_dump()
        if data.timeout_seconds is not None:
            card.timeout_seconds = data.timeout_seconds
        if data.retry_count is not None:
            card.retry_count = data.retry_count
        if data.enabled is not None:
            card.enabled = data.enabled
        if data.allowed_outputs is not None:
            card.allowed_outputs = data.allowed_outputs

        card.updated_at = datetime.now()

        session.add(card)
        session.commit()
        session.refresh(card)

        # Handle watcher updates
        new_trigger = TriggerConfig(**card.trigger_config)

        # If trigger changed or enabled state changed, update watcher
        if old_enabled and (
            not card.enabled or old_trigger.model_dump() != new_trigger.model_dump()
        ):
            _remove_card_watch(card)

        if card.enabled and (
            not old_enabled or old_trigger.model_dump() != new_trigger.model_dump()
        ):
            _setup_card_watch(card)

        return card
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def delete_card(card_id: str) -> bool:
    """Delete a card.

    Args:
        card_id: The card ID

    Returns:
        True if deleted, False if not found
    """
    # Import here to avoid circular dependency
    from leaf.projects.context import require_current_project

    ctx = require_current_project()

    gen = get_session(ctx.database_path)
    session = next(gen)
    try:
        card = session.get(Card, card_id)
        if not card:
            return False

        # Remove watcher first
        _remove_card_watch(card)

        # Delete the card
        session.delete(card)
        session.commit()
        return True
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def enable_card(card_id: str) -> Card:
    """Enable a card.

    Args:
        card_id: The card ID

    Returns:
        The updated Card
    """
    return update_card(card_id, CardUpdate(enabled=True))


def disable_card(card_id: str) -> Card:
    """Disable a card.

    Args:
        card_id: The card ID

    Returns:
        The updated Card
    """
    return update_card(card_id, CardUpdate(enabled=False))


def increment_run_count(card_id: str) -> None:
    """Increment the run count for a card.

    Args:
        card_id: The card ID
    """
    # Import here to avoid circular dependency
    from leaf.projects.context import require_current_project

    ctx = require_current_project()

    gen = get_session(ctx.database_path)
    session = next(gen)
    try:
        card = session.get(Card, card_id)
        if card:
            card.run_count += 1
            card.last_run_at = datetime.now()
            session.add(card)
            session.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def _setup_card_watch(card: Card) -> None:
    """Set up file watching for a card if it has a file-based trigger.

    Args:
        card: The card
    """
    # Import here to avoid circular dependency
    from leaf.projects.context import require_current_project
    from leaf.watcher import add_watch

    trigger = TriggerConfig(**card.trigger_config)

    if trigger.type not in ("file_created", "file_modified"):
        return

    if not trigger.folder:
        return

    ctx = require_current_project()

    # Resolve folder path relative to project
    folder_path = ctx.path / trigger.folder
    if not folder_path.exists():
        folder_path.mkdir(parents=True, exist_ok=True)

    add_watch(
        folder=folder_path,
        pattern=trigger.pattern or "*",
        card_id=card.id,
        watch_id=f"card_{card.id}",
    )


def _remove_card_watch(card: Card) -> None:
    """Remove file watching for a card.

    Args:
        card: The card
    """
    # Import here to avoid circular dependency
    from leaf.watcher import remove_watch

    watch_id = f"card_{card.id}"
    remove_watch(watch_id)


def setup_all_card_watches() -> None:
    """Set up watches for all enabled cards.

    Called when a project is opened to restore watches.
    """
    cards = list_cards(enabled_only=True)
    for card in cards:
        _setup_card_watch(card)
