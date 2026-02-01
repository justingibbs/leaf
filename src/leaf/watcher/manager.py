"""Watcher manager - connects FileWatcher to EventBus.

Manages the lifecycle of file watchers for the current project.
"""

import secrets
from pathlib import Path

from leaf.watcher.file_watcher import FileEvent, FileWatcher, WatchConfig

# Global watcher instance (one per app, watches current project)
_watcher: FileWatcher | None = None


async def _handle_file_event(event: FileEvent) -> None:
    """Handle a file event from the watcher.

    Emits the event to the event bus.
    """
    # Import here to avoid circular dependency
    from leaf.core.events import emit_file_event

    try:
        await emit_file_event(event)
    except RuntimeError:
        # No active project, ignore
        pass


def get_watcher() -> FileWatcher:
    """Get or create the global file watcher."""
    global _watcher
    if _watcher is None:
        _watcher = FileWatcher(on_event=_handle_file_event)
    return _watcher


def generate_watch_id() -> str:
    """Generate a unique watch ID."""
    return f"watch_{secrets.token_hex(6)}"


def add_watch(
    folder: Path | str,
    pattern: str = "*",
    card_id: str | None = None,
    watch_id: str | None = None,
) -> WatchConfig:
    """Add a folder watch.

    Args:
        folder: Folder to watch (absolute path)
        pattern: Glob pattern for files (e.g., "*.csv")
        card_id: Associated card ID, if any
        watch_id: Optional custom watch ID

    Returns:
        The WatchConfig that was created
    """
    watcher = get_watcher()

    folder_path = Path(folder).resolve()
    config = WatchConfig(
        id=watch_id or generate_watch_id(),
        folder=folder_path,
        pattern=pattern,
        card_id=card_id,
    )

    watcher.add_watch(config)
    return config


def remove_watch(watch_id: str) -> None:
    """Remove a folder watch.

    Args:
        watch_id: ID of the watch to remove
    """
    watcher = get_watcher()
    watcher.remove_watch(watch_id)


def get_watches() -> list[WatchConfig]:
    """Get all active watches."""
    watcher = get_watcher()
    return watcher.get_watches()


async def stop_all_watches() -> None:
    """Stop all watches."""
    global _watcher
    if _watcher is not None:
        await _watcher.stop_all()
        _watcher = None
