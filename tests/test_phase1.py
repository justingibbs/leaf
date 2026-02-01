"""Phase 1 tests - Foundation."""

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from leaf.core.config import get_app_config, get_config_dir
from leaf.db.session import get_session, init_database
from leaf.main import app
from leaf.projects import ProjectManager, get_current_project, set_current_project


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestAppConfig:
    """Test app-level configuration."""

    def test_get_config_dir(self, monkeypatch, temp_dir):
        """Test getting config directory."""
        monkeypatch.setenv("LEAF_CONFIG_DIR", str(temp_dir))
        assert get_config_dir() == temp_dir

    def test_get_app_config_creates_default(self, monkeypatch, temp_dir):
        """Test that get_app_config creates default config if missing."""
        monkeypatch.setenv("LEAF_CONFIG_DIR", str(temp_dir))
        config = get_app_config()

        assert config.version == "1.0"
        assert config.theme == "system"
        assert (temp_dir / "config.json").exists()


class TestProjectManager:
    """Test project management."""

    def test_create_project(self, monkeypatch, temp_dir):
        """Test creating a new project."""
        # Set up isolated config
        config_dir = temp_dir / "config"
        config_dir.mkdir()
        monkeypatch.setenv("LEAF_CONFIG_DIR", str(config_dir))

        # Create project directory
        project_dir = temp_dir / "my_project"
        project_dir.mkdir()

        manager = ProjectManager()
        project = manager.create_project(project_dir, "My Project")

        assert project.name == "My Project"
        assert Path(project.path).resolve() == project_dir.resolve()
        assert project.id.startswith("proj_")

        # Check .leaf folder was created
        leaf_dir = project_dir / ".leaf"
        assert leaf_dir.exists()
        assert (leaf_dir / "config.json").exists()
        assert (leaf_dir / "leaf.db").exists()
        assert (leaf_dir / "programs").exists()
        assert (leaf_dir / "logs").exists()
        assert (leaf_dir / "outputs").exists()

    def test_create_project_already_exists(self, monkeypatch, temp_dir):
        """Test creating a project in a folder that already has one."""
        config_dir = temp_dir / "config"
        config_dir.mkdir()
        monkeypatch.setenv("LEAF_CONFIG_DIR", str(config_dir))

        project_dir = temp_dir / "my_project"
        project_dir.mkdir()

        manager = ProjectManager()
        manager.create_project(project_dir, "My Project")

        with pytest.raises(ValueError, match="already contains"):
            manager.create_project(project_dir, "Another Project")

    def test_open_project(self, monkeypatch, temp_dir):
        """Test opening an existing project."""
        config_dir = temp_dir / "config"
        config_dir.mkdir()
        monkeypatch.setenv("LEAF_CONFIG_DIR", str(config_dir))

        project_dir = temp_dir / "my_project"
        project_dir.mkdir()

        manager = ProjectManager()
        created = manager.create_project(project_dir, "My Project")

        # Create a new manager (simulating app restart)
        manager2 = ProjectManager()

        # Remove from registry to simulate opening from disk
        manager2.registry.remove_project(created.id)

        # Open the project
        opened = manager2.open_project(project_dir)

        assert opened.id == created.id
        assert opened.name == "My Project"


class TestDatabase:
    """Test database setup."""

    def test_init_database(self, temp_dir):
        """Test database initialization."""
        db_path = temp_dir / "test.db"
        init_database(db_path)

        assert db_path.exists()

    def test_database_session(self, temp_dir):
        """Test database session."""
        db_path = temp_dir / "test.db"
        init_database(db_path)

        # Get a session and verify it works
        gen = get_session(db_path)
        session = next(gen)
        assert session is not None

        # Clean up
        try:
            next(gen)
        except StopIteration:
            pass


class TestProjectContext:
    """Test project context management."""

    def test_set_and_get_current_project(self, monkeypatch, temp_dir):
        """Test setting and getting current project."""
        config_dir = temp_dir / "config"
        config_dir.mkdir()
        monkeypatch.setenv("LEAF_CONFIG_DIR", str(config_dir))

        project_dir = temp_dir / "my_project"
        project_dir.mkdir()

        manager = ProjectManager()
        project = manager.create_project(project_dir, "My Project")

        # No project initially
        assert get_current_project() is None

        # Set current project
        set_current_project(project)
        ctx = get_current_project()

        assert ctx is not None
        assert ctx.id == project.id
        assert ctx.name == "My Project"
        assert ctx.database_path.resolve() == (project_dir / ".leaf" / "leaf.db").resolve()

        # Clear project
        set_current_project(None)
        assert get_current_project() is None


class TestAPI:
    """Test API endpoints."""

    def test_root(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "LEAF"
        assert data["status"] == "running"

    def test_health(self, client):
        """Test health endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_list_projects_empty(self, client, monkeypatch, temp_dir):
        """Test listing projects when none exist."""
        config_dir = temp_dir / "config"
        config_dir.mkdir()
        monkeypatch.setenv("LEAF_CONFIG_DIR", str(config_dir))

        response = client.get("/api/projects")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_and_list_project(self, client, monkeypatch, temp_dir):
        """Test creating and listing a project."""
        config_dir = temp_dir / "config"
        config_dir.mkdir()
        monkeypatch.setenv("LEAF_CONFIG_DIR", str(config_dir))

        project_dir = temp_dir / "my_project"

        # Create project (API should create the folder too)
        response = client.post(
            "/api/projects",
            json={"path": str(project_dir), "name": "My Project"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "My Project"
        project_id = data["id"]

        # List projects
        response = client.get("/api/projects")
        assert response.status_code == 200
        projects = response.json()
        assert len(projects) == 1
        assert projects[0]["id"] == project_id

    def test_switch_project(self, client, monkeypatch, temp_dir):
        """Test switching to a project."""
        config_dir = temp_dir / "config"
        config_dir.mkdir()
        monkeypatch.setenv("LEAF_CONFIG_DIR", str(config_dir))

        project_dir = temp_dir / "my_project"

        # Create project
        response = client.post(
            "/api/projects",
            json={"path": str(project_dir), "name": "My Project"},
        )
        project_id = response.json()["id"]

        # Switch to project
        response = client.post(
            "/api/projects/switch",
            json={"project_id": project_id},
        )
        assert response.status_code == 200

    def test_project_routes_require_active_project(self, client, monkeypatch, temp_dir):
        """Test that project routes fail without active project."""
        config_dir = temp_dir / "config"
        config_dir.mkdir()
        monkeypatch.setenv("LEAF_CONFIG_DIR", str(config_dir))

        # Clear any current project
        set_current_project(None)

        response = client.get("/api/project")
        assert response.status_code == 400
        assert "No active project" in response.json()["detail"]

        response = client.get("/api/cards")
        assert response.status_code == 400

        response = client.get("/api/events")
        assert response.status_code == 400
