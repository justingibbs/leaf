"""App-level API routes.

These routes manage app configuration and the project registry.
They don't require an active project.
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from leaf.core.config import AppConfig, get_app_config, save_app_config
from leaf.projects import ProjectManager, set_current_project
from leaf.projects.registry import ProjectInfo
from leaf.watcher import stop_all_watches

router = APIRouter(prefix="/api", tags=["app"])


# --- Request/Response Models ---


class CreateProjectRequest(BaseModel):
    """Request to create a new project."""

    path: str
    name: str


class OpenProjectRequest(BaseModel):
    """Request to open an existing project folder."""

    path: str


class ProjectResponse(BaseModel):
    """Project information response."""

    id: str
    name: str
    path: str
    created_at: str
    last_opened_at: str

    @classmethod
    def from_project_info(cls, info: ProjectInfo) -> "ProjectResponse":
        return cls(
            id=info.id,
            name=info.name,
            path=info.path,
            created_at=info.created_at.isoformat(),
            last_opened_at=info.last_opened_at.isoformat(),
        )


class SwitchProjectRequest(BaseModel):
    """Request to switch to a project."""

    project_id: str


# --- App Config Routes ---


@router.get("/app/config")
async def get_config() -> AppConfig:
    """Get app configuration."""
    return get_app_config()


@router.put("/app/config")
async def update_config(config: AppConfig) -> AppConfig:
    """Update app configuration."""
    save_app_config(config)
    return config


# --- Project Registry Routes ---


@router.get("/projects")
async def list_projects() -> list[ProjectResponse]:
    """List all registered projects."""
    manager = ProjectManager()
    projects = manager.registry.list_projects()
    return [ProjectResponse.from_project_info(p) for p in projects]


@router.post("/projects")
async def create_project(request: CreateProjectRequest) -> ProjectResponse:
    """Create a new project in the given folder."""
    manager = ProjectManager()

    # Create the folder if it doesn't exist
    path = Path(request.path).expanduser().resolve()
    if not path.exists():
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise HTTPException(status_code=400, detail=f"Cannot create folder: {e}") from e

    try:
        project = manager.create_project(path, request.name)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return ProjectResponse.from_project_info(project)


@router.post("/projects/open")
async def open_project(request: OpenProjectRequest) -> ProjectResponse:
    """Open an existing folder as a project.

    The folder must already contain a .leaf/ directory.
    """
    manager = ProjectManager()

    path = Path(request.path).expanduser().resolve()

    try:
        project = manager.open_project(path)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return ProjectResponse.from_project_info(project)


@router.delete("/projects/{project_id}")
async def remove_project(project_id: str) -> dict:
    """Remove a project from the registry.

    This does NOT delete the project files, only unregisters it.
    """
    manager = ProjectManager()

    project = manager.registry.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

    manager.registry.remove_project(project_id)

    return {"status": "removed", "project_id": project_id}


@router.post("/projects/switch")
async def switch_project(request: SwitchProjectRequest) -> ProjectResponse:
    """Switch to a project, making it the active project.

    This sets the current project context for project-level routes.
    Stops any watches from the previous project.
    """
    manager = ProjectManager()

    project = manager.registry.get_project(request.project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project not found: {request.project_id}")

    # Stop any existing watches
    await stop_all_watches()

    # Update last opened time
    manager.registry.touch_project(request.project_id)

    # Set as current project
    set_current_project(project)

    return ProjectResponse.from_project_info(project)


@router.post("/projects/close")
async def close_project() -> dict:
    """Close the current project.

    Stops all watches.
    """
    await stop_all_watches()
    set_current_project(None)
    return {"status": "closed"}
