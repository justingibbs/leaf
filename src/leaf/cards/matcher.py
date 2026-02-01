"""Card matcher - matches events to cards.

Evaluates incoming events against card triggers to determine
which cards should be executed.
"""

import fnmatch
from pathlib import Path
from typing import TYPE_CHECKING

from leaf.db.models import Card

from .models import TriggerConfig, TriggerResult

if TYPE_CHECKING:
    from leaf.watcher.file_watcher import FileEvent


def match_file_event(event: "FileEvent") -> list[TriggerResult]:
    """Match a file event against all enabled cards.

    Args:
        event: The file event to match

    Returns:
        List of TriggerResult for cards that match
    """
    from .registry import list_cards

    results: list[TriggerResult] = []
    cards = list_cards(enabled_only=True)

    for card in cards:
        result = evaluate_file_trigger(card, event)
        results.append(result)

    return results


def evaluate_file_trigger(card: Card, event: "FileEvent") -> TriggerResult:
    """Evaluate if a file event matches a card's trigger.

    Args:
        card: The card to check
        event: The file event

    Returns:
        TriggerResult indicating if the card matches
    """
    # Import here to avoid circular dependency
    from leaf.projects.context import require_current_project

    trigger = TriggerConfig(**card.trigger_config)

    # Check if event type matches trigger type
    event_type_map = {
        "file.created": "file_created",
        "file.modified": "file_modified",
    }

    expected_type = event_type_map.get(event.type)
    if expected_type != trigger.type:
        return TriggerResult(
            matches=False,
            card_id=card.id,
            reason=f"Event type '{event.type}' doesn't match trigger type '{trigger.type}'",
        )

    # Check folder match
    if trigger.folder:
        ctx = require_current_project()
        trigger_folder = (ctx.path / trigger.folder).resolve()

        # Check if the event's folder is the trigger folder or a subfolder
        try:
            event.folder.resolve().relative_to(trigger_folder)
        except ValueError:
            return TriggerResult(
                matches=False,
                card_id=card.id,
                reason=f"Event folder '{event.folder}' not in trigger folder '{trigger_folder}'",
            )

    # Check pattern match
    if trigger.pattern:
        if not fnmatch.fnmatch(event.filename, trigger.pattern):
            return TriggerResult(
                matches=False,
                card_id=card.id,
                reason=f"Filename '{event.filename}' doesn't match pattern '{trigger.pattern}'",
            )

    # All checks passed
    folder = trigger.folder or "any"
    pattern = trigger.pattern or "*"
    return TriggerResult(
        matches=True,
        card_id=card.id,
        reason=f"Matched: {trigger.type} in {folder} pattern={pattern}",
    )


def find_matching_cards(event_type: str, payload: dict) -> list[Card]:
    """Find all cards that match an event.

    Args:
        event_type: The event type (e.g., "file.created")
        payload: The event payload

    Returns:
        List of matching cards
    """
    # Import here to avoid circular dependency
    from leaf.projects.context import require_current_project

    from .registry import list_cards

    if not event_type.startswith("file."):
        # Only file events support trigger matching for now
        return []

    # Reconstruct a FileEvent-like object for matching
    cards = list_cards(enabled_only=True)
    matching_cards: list[Card] = []

    ctx = require_current_project()

    for card in cards:
        trigger = TriggerConfig(**card.trigger_config)

        # Check event type
        event_type_map = {
            "file.created": "file_created",
            "file.modified": "file_modified",
        }

        if event_type_map.get(event_type) != trigger.type:
            continue

        # Check folder match
        if trigger.folder:
            trigger_folder = (ctx.path / trigger.folder).resolve()
            event_folder = Path(payload.get("folder", "")).resolve()

            try:
                event_folder.relative_to(trigger_folder)
            except ValueError:
                continue

        # Check pattern match
        if trigger.pattern:
            filename = payload.get("filename", "")
            if not fnmatch.fnmatch(filename, trigger.pattern):
                continue

        matching_cards.append(card)

    return matching_cards


def get_cards_for_watch(watch_id: str) -> list[Card]:
    """Get all cards associated with a watch.

    Args:
        watch_id: The watch ID

    Returns:
        List of cards using this watch
    """
    from .registry import list_cards

    # For card watches, the watch_id is "card_{card_id}"
    if watch_id.startswith("card_"):
        card_id = watch_id[5:]  # Remove "card_" prefix
        cards = list_cards()
        return [c for c in cards if c.id == card_id]
    return []
