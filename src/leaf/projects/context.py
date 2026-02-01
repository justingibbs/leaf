"""Current project context management.

Provides global access to the currently active project.

Note: This uses a simple module-level variable instead of ContextVar
because LEAF is a single-user desktop app and we need the project
context to persist across HTTP requests.
"""

from dataclasses import dataclass
from pathlib import Path

from leaf.projects.registry import ProjectInfo


@dataclass
class ProjectContext:
    """Context for the currently active project."""

    project: ProjectInfo

    @property
    def id(self) -> str:
        """Get the project ID."""
        return self.project.id

    @property
    def name(self) -> str:
        """Get the project name."""
        return self.project.name

    @property
    def path(self) -> Path:
        """Get the project path."""
        return Path(self.project.path)

    @property
    def leaf_dir(self) -> Path:
        """Get the .leaf directory."""
        return self.path / ".leaf"

    @property
    def database_path(self) -> Path:
        """Get the database path."""
        return self.leaf_dir / "leaf.db"

    @property
    def programs_dir(self) -> Path:
        """Get the programs directory."""
        return self.leaf_dir / "programs"

    @property
    def logs_dir(self) -> Path:
        """Get the logs directory."""
        return self.leaf_dir / "logs"

    @property
    def outputs_dir(self) -> Path:
        """Get the outputs directory."""
        return self.leaf_dir / "outputs"


class _ProjectContextHolder:
    """Holds the current project context."""

    def __init__(self) -> None:
        self._context: ProjectContext | None = None

    def get(self) -> ProjectContext | None:
        return self._context

    def set(self, project: ProjectInfo | None) -> None:
        if project is None:
            self._context = None
        else:
            self._context = ProjectContext(project=project)


# Global context holder
_holder = _ProjectContextHolder()


def get_current_project() -> ProjectContext | None:
    """Get the current project context."""
    return _holder.get()


def set_current_project(project: ProjectInfo | None) -> None:
    """Set the current project context."""
    _holder.set(project)


def require_current_project() -> ProjectContext:
    """Get the current project context, raising if none is set.

    Raises:
        RuntimeError: If no project is currently active
    """
    ctx = get_current_project()
    if ctx is None:
        raise RuntimeError("No project is currently active")
    return ctx
