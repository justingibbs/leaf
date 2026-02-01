"""File watcher using watchfiles.

Watches folders for file changes and emits events.
"""

import asyncio
import fnmatch
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from watchfiles import Change, awatch

# Patterns to always ignore
IGNORED_PATTERNS = [
    ".*",  # Hidden files/folders
    "__pycache__",
    "*.pyc",
    "*.pyo",
    "node_modules",
    "*.swp",
    "*.swo",
    "*~",
    ".git",
    ".leaf",
]


@dataclass
class WatchConfig:
    """Configuration for a folder watch."""

    id: str
    folder: Path  # Absolute path to watch
    pattern: str = "*"  # Glob pattern (e.g., "*.csv")
    card_id: str | None = None  # Associated card, if any


@dataclass
class FileEvent:
    """A file system event."""

    type: str  # file.created, file.modified, file.deleted
    path: Path  # Absolute path
    folder: Path  # Watched folder
    filename: str
    size: int | None  # None for deleted files
    timestamp: datetime = field(default_factory=datetime.now)
    watch_id: str | None = None
    card_id: str | None = None


class FileWatcher:
    """Watches folders for file changes.

    Manages multiple watch configurations and emits events
    when matching files change.
    """

    def __init__(
        self,
        on_event: Callable[[FileEvent], Coroutine],
        debounce_ms: int = 100,
    ) -> None:
        """Initialize the file watcher.

        Args:
            on_event: Async callback for file events
            debounce_ms: Debounce delay in milliseconds
        """
        self._on_event = on_event
        self._debounce_ms = debounce_ms
        self._watches: dict[str, WatchConfig] = {}
        self._watch_tasks: dict[str, asyncio.Task] = {}
        self._stop_events: dict[str, asyncio.Event] = {}
        self._pending_events: dict[str, FileEvent] = {}
        self._debounce_tasks: dict[str, asyncio.Task] = {}

    def _should_ignore(self, path: Path) -> bool:
        """Check if a path should be ignored."""
        # Check each part of the path
        for part in path.parts:
            for pattern in IGNORED_PATTERNS:
                if fnmatch.fnmatch(part, pattern):
                    return True
        return False

    def _matches_pattern(self, filename: str, pattern: str) -> bool:
        """Check if a filename matches a glob pattern."""
        return fnmatch.fnmatch(filename, pattern)

    def _change_to_event_type(self, change: Change) -> str:
        """Convert watchfiles Change to event type."""
        if change == Change.added:
            return "file.created"
        elif change == Change.modified:
            return "file.modified"
        elif change == Change.deleted:
            return "file.deleted"
        return "file.unknown"

    async def _debounced_emit(self, key: str, event: FileEvent) -> None:
        """Emit an event after debounce delay."""
        await asyncio.sleep(self._debounce_ms / 1000)

        # Get the latest event for this key (may have been updated)
        if key in self._pending_events:
            final_event = self._pending_events.pop(key)
            await self._on_event(final_event)

        # Clean up
        if key in self._debounce_tasks:
            del self._debounce_tasks[key]

    def _schedule_event(self, event: FileEvent) -> None:
        """Schedule an event with debouncing."""
        key = f"{event.path}:{event.type}"

        # Store/update the pending event
        self._pending_events[key] = event

        # Cancel existing debounce task if any
        if key in self._debounce_tasks:
            self._debounce_tasks[key].cancel()

        # Schedule new debounce task
        self._debounce_tasks[key] = asyncio.create_task(
            self._debounced_emit(key, event)
        )

    async def _watch_folder(self, config: WatchConfig) -> None:
        """Watch a single folder for changes."""
        stop_event = self._stop_events[config.id]

        try:
            async for changes in awatch(
                config.folder,
                stop_event=stop_event,
                debounce=self._debounce_ms,
                recursive=True,
            ):
                for change, path_str in changes:
                    path = Path(path_str)

                    # Skip ignored paths
                    if self._should_ignore(path):
                        continue

                    # Skip directories
                    if path.is_dir():
                        continue

                    # Check pattern match
                    if not self._matches_pattern(path.name, config.pattern):
                        continue

                    # Get file size (if exists)
                    try:
                        size = path.stat().st_size if path.exists() else None
                    except OSError:
                        size = None

                    # Create event
                    event = FileEvent(
                        type=self._change_to_event_type(change),
                        path=path,
                        folder=config.folder,
                        filename=path.name,
                        size=size,
                        watch_id=config.id,
                        card_id=config.card_id,
                    )

                    # Schedule with debouncing
                    self._schedule_event(event)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            # Log error but don't crash
            print(f"Watch error for {config.folder}: {e}")

    def add_watch(self, config: WatchConfig) -> None:
        """Add a folder watch.

        Args:
            config: Watch configuration
        """
        if config.id in self._watches:
            raise ValueError(f"Watch already exists: {config.id}")

        # Validate folder exists
        if not config.folder.exists():
            raise FileNotFoundError(f"Folder does not exist: {config.folder}")

        if not config.folder.is_dir():
            raise ValueError(f"Path is not a directory: {config.folder}")

        self._watches[config.id] = config
        self._stop_events[config.id] = asyncio.Event()
        self._watch_tasks[config.id] = asyncio.create_task(
            self._watch_folder(config)
        )

    def remove_watch(self, watch_id: str) -> None:
        """Remove a folder watch.

        Args:
            watch_id: ID of the watch to remove
        """
        if watch_id not in self._watches:
            return

        # Signal stop
        if watch_id in self._stop_events:
            self._stop_events[watch_id].set()

        # Cancel task
        if watch_id in self._watch_tasks:
            self._watch_tasks[watch_id].cancel()
            del self._watch_tasks[watch_id]

        # Clean up
        del self._watches[watch_id]
        if watch_id in self._stop_events:
            del self._stop_events[watch_id]

    def get_watches(self) -> list[WatchConfig]:
        """Get all active watches."""
        return list(self._watches.values())

    def has_watch(self, watch_id: str) -> bool:
        """Check if a watch exists."""
        return watch_id in self._watches

    async def stop_all(self) -> None:
        """Stop all watches."""
        watch_ids = list(self._watches.keys())
        for watch_id in watch_ids:
            self.remove_watch(watch_id)

        # Cancel any pending debounce tasks
        for task in self._debounce_tasks.values():
            task.cancel()
        self._debounce_tasks.clear()
        self._pending_events.clear()

        # Wait for tasks to complete
        if self._watch_tasks:
            await asyncio.gather(*self._watch_tasks.values(), return_exceptions=True)
