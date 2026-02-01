"""Project initialization and management.

Handles creating and opening projects, initializing .leaf/ folders.
"""

import secrets
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

from leaf.db.session import init_database
from leaf.projects.registry import ProjectInfo, ProjectRegistry


class ProjectConfig(BaseModel):
    """Project-specific configuration stored in .leaf/config.json."""

    version: str = "1.0"
    project_id: str
    name: str
    created_at: datetime
    model: str | None = None  # Override app default


class ProjectManager:
    """Manages project creation, opening, and initialization."""

    def __init__(self) -> None:
        self.registry = ProjectRegistry()

    def _generate_project_id(self) -> str:
        """Generate a unique project ID."""
        return f"proj_{secrets.token_hex(6)}"

    def _get_leaf_dir(self, project_path: Path) -> Path:
        """Get the .leaf directory for a project."""
        return project_path / ".leaf"

    def _init_leaf_folder(self, project_path: Path, project_id: str, name: str) -> None:
        """Initialize the .leaf folder structure for a project."""
        import json

        leaf_dir = self._get_leaf_dir(project_path)

        # Create directory structure
        (leaf_dir / "programs").mkdir(parents=True, exist_ok=True)
        (leaf_dir / "logs").mkdir(parents=True, exist_ok=True)
        (leaf_dir / "outputs").mkdir(parents=True, exist_ok=True)

        # Create project config
        config = ProjectConfig(
            project_id=project_id,
            name=name,
            created_at=datetime.now(),
        )

        config_file = leaf_dir / "config.json"
        with open(config_file, "w") as f:
            json.dump(config.model_dump(mode="json"), f, indent=2, default=str)

        # Initialize the database
        init_database(leaf_dir / "leaf.db")

    def _is_initialized(self, project_path: Path) -> bool:
        """Check if a folder has been initialized as a LEAF project."""
        leaf_dir = self._get_leaf_dir(project_path)
        config_file = leaf_dir / "config.json"
        return config_file.exists()

    def _load_project_config(self, project_path: Path) -> ProjectConfig:
        """Load the project config from .leaf/config.json."""
        import json

        config_file = self._get_leaf_dir(project_path) / "config.json"

        with open(config_file) as f:
            data = json.load(f)

        return ProjectConfig.model_validate(data)

    def create_project(self, path: str | Path, name: str) -> ProjectInfo:
        """Create a new project in the given folder.

        Args:
            path: Path to the folder to create the project in
            name: Human-readable name for the project

        Returns:
            ProjectInfo for the new project

        Raises:
            ValueError: If the folder already contains a LEAF project
            FileNotFoundError: If the folder doesn't exist
        """
        project_path = Path(path).resolve()

        if not project_path.exists():
            raise FileNotFoundError(f"Folder does not exist: {project_path}")

        if not project_path.is_dir():
            raise ValueError(f"Path is not a directory: {project_path}")

        # Check if already initialized
        if self._is_initialized(project_path):
            raise ValueError(f"Folder already contains a LEAF project: {project_path}")

        # Check if already in registry
        existing = self.registry.get_project_by_path(project_path)
        if existing:
            raise ValueError(f"Project already registered at {project_path}")

        # Generate ID and initialize
        project_id = self._generate_project_id()
        now = datetime.now()

        # Initialize .leaf folder
        self._init_leaf_folder(project_path, project_id, name)

        # Create project info and register
        project = ProjectInfo(
            id=project_id,
            name=name,
            path=str(project_path),
            created_at=now,
            last_opened_at=now,
        )

        self.registry.add_project(project)

        return project

    def open_project(self, path: str | Path) -> ProjectInfo:
        """Open an existing project folder.

        If the folder is not registered, it will be added to the registry.
        If the folder is not initialized, this will fail.

        Args:
            path: Path to the project folder

        Returns:
            ProjectInfo for the project

        Raises:
            ValueError: If the folder is not a valid LEAF project
            FileNotFoundError: If the folder doesn't exist
        """
        project_path = Path(path).resolve()

        if not project_path.exists():
            raise FileNotFoundError(f"Folder does not exist: {project_path}")

        if not project_path.is_dir():
            raise ValueError(f"Path is not a directory: {project_path}")

        # Check if initialized
        if not self._is_initialized(project_path):
            raise ValueError(f"Folder is not a LEAF project: {project_path}")

        # Check if already registered
        existing = self.registry.get_project_by_path(project_path)
        if existing:
            self.registry.touch_project(existing.id)
            # Ensure database is initialized (in case project was moved)
            init_database(self._get_leaf_dir(project_path) / "leaf.db")
            return existing

        # Load config and register
        config = self._load_project_config(project_path)
        now = datetime.now()

        project = ProjectInfo(
            id=config.project_id,
            name=config.name,
            path=str(project_path),
            created_at=config.created_at,
            last_opened_at=now,
        )

        self.registry.add_project(project)

        # Ensure database is initialized
        init_database(self._get_leaf_dir(project_path) / "leaf.db")

        return project

    def get_project_path(self, project_id: str) -> Path | None:
        """Get the path for a registered project."""
        project = self.registry.get_project(project_id)
        if project:
            return Path(project.path)
        return None

    def get_database_path(self, project_id: str) -> Path | None:
        """Get the database path for a project."""
        project_path = self.get_project_path(project_id)
        if project_path:
            return project_path / ".leaf" / "leaf.db"
        return None
