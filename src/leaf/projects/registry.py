"""Project registry management.

Manages ~/.leaf/projects.json - the list of known projects.
"""

import json
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

from leaf.core.config import get_config_dir


class ProjectInfo(BaseModel):
    """Information about a registered project."""

    id: str
    name: str
    path: str
    created_at: datetime
    last_opened_at: datetime


class ProjectsFile(BaseModel):
    """Schema for ~/.leaf/projects.json."""

    version: str = "1.0"
    projects: list[ProjectInfo] = Field(default_factory=list)


class ProjectRegistry:
    """Manages the project registry at ~/.leaf/projects.json."""

    def __init__(self) -> None:
        self._config_dir = get_config_dir()
        self._registry_file = self._config_dir / "projects.json"

    def _load(self) -> ProjectsFile:
        """Load the projects registry file."""
        if not self._registry_file.exists():
            return ProjectsFile()

        with open(self._registry_file) as f:
            data = json.load(f)

        return ProjectsFile.model_validate(data)

    def _save(self, registry: ProjectsFile) -> None:
        """Save the projects registry file."""
        self._config_dir.mkdir(parents=True, exist_ok=True)

        with open(self._registry_file, "w") as f:
            json.dump(
                registry.model_dump(mode="json"),
                f,
                indent=2,
                default=str,
            )

    def list_projects(self) -> list[ProjectInfo]:
        """List all registered projects, sorted by last opened."""
        registry = self._load()
        return sorted(registry.projects, key=lambda p: p.last_opened_at, reverse=True)

    def get_project(self, project_id: str) -> ProjectInfo | None:
        """Get a project by ID."""
        registry = self._load()
        for project in registry.projects:
            if project.id == project_id:
                return project
        return None

    def get_project_by_path(self, path: str | Path) -> ProjectInfo | None:
        """Get a project by path."""
        path_str = str(Path(path).resolve())
        registry = self._load()
        for project in registry.projects:
            if str(Path(project.path).resolve()) == path_str:
                return project
        return None

    def add_project(self, project: ProjectInfo) -> None:
        """Add a project to the registry."""
        registry = self._load()

        # Check if already exists by path
        existing = self.get_project_by_path(project.path)
        if existing:
            raise ValueError(f"Project already registered at {project.path}")

        registry.projects.append(project)
        self._save(registry)

    def update_project(self, project: ProjectInfo) -> None:
        """Update a project in the registry."""
        registry = self._load()

        for i, p in enumerate(registry.projects):
            if p.id == project.id:
                registry.projects[i] = project
                self._save(registry)
                return

        raise ValueError(f"Project not found: {project.id}")

    def remove_project(self, project_id: str) -> None:
        """Remove a project from the registry (does not delete files)."""
        registry = self._load()
        registry.projects = [p for p in registry.projects if p.id != project_id]
        self._save(registry)

    def touch_project(self, project_id: str) -> None:
        """Update last_opened_at for a project."""
        project = self.get_project(project_id)
        if project:
            project.last_opened_at = datetime.now()
            self.update_project(project)
