"""Cards module - automation definitions with triggers and programs."""

from .matcher import (
    evaluate_file_trigger,
    find_matching_cards,
    get_cards_for_watch,
    match_file_event,
)
from .models import (
    CardCreate,
    CardDetailResponse,
    CardUpdate,
    ProgramConfig,
    TriggerConfig,
    TriggerResult,
)
from .registry import (
    create_card,
    delete_card,
    disable_card,
    enable_card,
    get_card,
    increment_run_count,
    list_cards,
    setup_all_card_watches,
    update_card,
)

__all__ = [
    # Models
    "CardCreate",
    "CardUpdate",
    "CardDetailResponse",
    "TriggerConfig",
    "ProgramConfig",
    "TriggerResult",
    # Registry
    "create_card",
    "get_card",
    "list_cards",
    "update_card",
    "delete_card",
    "enable_card",
    "disable_card",
    "increment_run_count",
    "setup_all_card_watches",
    # Matcher
    "match_file_event",
    "evaluate_file_trigger",
    "find_matching_cards",
    "get_cards_for_watch",
]
