"""Phase 4 tests - PydanticAI Agent.

Note: These tests mock the AI model to avoid requiring API keys during testing.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from leaf.agent import AgentContext
from leaf.agent.tools import (
    CardProposal,
    list_project_directory,
    read_project_file,
    write_project_file,
)
from leaf.main import app
from leaf.projects import ProjectManager, get_current_project, set_current_project
from leaf.watcher import stop_all_watches


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
async def project_context(monkeypatch, temp_dir):
    """Create a project and set it as current context."""
    # Set up isolated config
    config_dir = temp_dir / "config"
    config_dir.mkdir()
    monkeypatch.setenv("LEAF_CONFIG_DIR", str(config_dir))

    # Create project directory
    project_dir = temp_dir / "test_project"
    project_dir.mkdir()

    manager = ProjectManager()
    project = manager.create_project(project_dir, "Test Project")
    set_current_project(project)

    yield get_current_project()

    # Cleanup
    await stop_all_watches()
    set_current_project(None)


class TestAgentTools:
    """Test agent tools directly."""

    def test_read_file(self, temp_dir):
        """Test reading a file from the project."""
        # Create a test file
        test_file = temp_dir / "test.txt"
        test_file.write_text("Hello, World!")

        result = read_project_file(temp_dir, "test.txt")

        assert result.exists is True
        assert result.content == "Hello, World!"
        assert result.path == "test.txt"

    def test_read_nonexistent_file(self, temp_dir):
        """Test reading a file that doesn't exist."""
        result = read_project_file(temp_dir, "nonexistent.txt")

        assert result.exists is False
        assert result.content == ""

    def test_read_file_outside_project(self, temp_dir):
        """Test that reading files outside project is blocked."""
        result = read_project_file(temp_dir, "../outside.txt")

        assert result.exists is False
        assert "outside project" in result.content.lower()

    def test_write_file(self, temp_dir):
        """Test writing a file to the project."""
        result = write_project_file(temp_dir, "output.txt", "Test content")

        assert "Successfully" in result
        assert (temp_dir / "output.txt").exists()
        assert (temp_dir / "output.txt").read_text() == "Test content"

    def test_write_file_creates_directories(self, temp_dir):
        """Test that writing creates parent directories."""
        result = write_project_file(temp_dir, "subdir/nested/file.txt", "Nested!")

        assert "Successfully" in result
        assert (temp_dir / "subdir" / "nested" / "file.txt").exists()

    def test_write_file_blocks_leaf_directory(self, temp_dir):
        """Test that writing to .leaf directory is blocked."""
        result = write_project_file(temp_dir, ".leaf/secret.txt", "Hacked!")

        assert "Cannot write" in result
        assert not (temp_dir / ".leaf" / "secret.txt").exists()

    def test_write_file_outside_project(self, temp_dir):
        """Test that writing files outside project is blocked."""
        result = write_project_file(temp_dir, "../outside.txt", "Bad!")

        assert "outside project" in result.lower()

    def test_list_directory(self, temp_dir):
        """Test listing directory contents."""
        # Create some files and directories
        (temp_dir / "file1.txt").write_text("1")
        (temp_dir / "file2.csv").write_text("2")
        (temp_dir / "subdir").mkdir()
        (temp_dir / ".hidden").write_text("hidden")  # Should be excluded

        result = list_project_directory(temp_dir, ".")

        assert "file1.txt" in result.files
        assert "file2.csv" in result.files
        assert "subdir" in result.directories
        # Hidden files should be excluded
        assert ".hidden" not in result.files

    def test_list_nonexistent_directory(self, temp_dir):
        """Test listing a directory that doesn't exist."""
        result = list_project_directory(temp_dir, "nonexistent")

        assert result.files == []
        assert result.directories == []


class TestCardProposal:
    """Test the CardProposal model."""

    def test_card_proposal_creation(self):
        """Test creating a card proposal."""
        proposal = CardProposal(
            name="CSV Analyzer",
            description="Analyzes CSV files and generates reports",
            trigger_type="file_created",
            trigger_folder="inbox",
            trigger_pattern="*.csv",
            code='print("Hello")',
            dependencies=["pandas"],
        )

        assert proposal.name == "CSV Analyzer"
        assert proposal.trigger_type == "file_created"
        assert proposal.trigger_folder == "inbox"
        assert proposal.trigger_pattern == "*.csv"
        assert "pandas" in proposal.dependencies


class TestAgentContext:
    """Test the AgentContext class."""

    def test_agent_context_creation(self, temp_dir):
        """Test creating an agent context."""
        ctx = AgentContext(
            project_path=temp_dir,
            project_name="Test Project",
        )

        assert ctx.project_path == temp_dir
        assert ctx.project_name == "Test Project"
        assert ctx.pending_proposal is None

    def test_agent_context_with_proposal(self, temp_dir):
        """Test agent context with a pending proposal."""
        proposal = CardProposal(
            name="Test Card",
            description="Test",
            trigger_type="manual",
            code="pass",
        )

        ctx = AgentContext(
            project_path=temp_dir,
            project_name="Test Project",
            pending_proposal=proposal,
        )

        assert ctx.pending_proposal is not None
        assert ctx.pending_proposal.name == "Test Card"


class TestChatAPI:
    """Test chat API endpoints."""

    def test_get_chat_history_empty(self, client, monkeypatch, temp_dir):
        """Test getting chat history when empty."""
        config_dir = temp_dir / "config"
        config_dir.mkdir()
        monkeypatch.setenv("LEAF_CONFIG_DIR", str(config_dir))

        # Create and switch to project
        project_dir = temp_dir / "test_project"
        response = client.post(
            "/api/projects",
            json={"path": str(project_dir), "name": "Test"},
        )
        project_id = response.json()["id"]
        client.post("/api/projects/switch", json={"project_id": project_id})

        # Get chat history
        response = client.get("/api/chat/history")
        assert response.status_code == 200
        assert response.json() == []

        # Clean up
        client.post("/api/projects/close")

    def test_clear_chat_history(self, client, monkeypatch, temp_dir):
        """Test clearing chat history."""
        config_dir = temp_dir / "config"
        config_dir.mkdir()
        monkeypatch.setenv("LEAF_CONFIG_DIR", str(config_dir))

        # Create and switch to project
        project_dir = temp_dir / "test_project"
        response = client.post(
            "/api/projects",
            json={"path": str(project_dir), "name": "Test"},
        )
        project_id = response.json()["id"]
        client.post("/api/projects/switch", json={"project_id": project_id})

        # Clear chat history
        response = client.delete("/api/chat/history")
        assert response.status_code == 200
        assert response.json()["status"] == "cleared"

        # Clean up
        client.post("/api/projects/close")

    @patch("leaf.agent.chat")
    def test_send_chat_message(self, mock_chat, client, monkeypatch, temp_dir):
        """Test sending a chat message (mocked agent)."""
        # Mock the chat function as async
        async def mock_chat_fn(*args, **kwargs):
            return ("This is a test response", [])

        mock_chat.side_effect = mock_chat_fn

        config_dir = temp_dir / "config"
        config_dir.mkdir()
        monkeypatch.setenv("LEAF_CONFIG_DIR", str(config_dir))

        # Create and switch to project
        project_dir = temp_dir / "test_project"
        response = client.post(
            "/api/projects",
            json={"path": str(project_dir), "name": "Test"},
        )
        project_id = response.json()["id"]
        client.post("/api/projects/switch", json={"project_id": project_id})

        # Send chat message
        response = client.post(
            "/api/chat",
            json={"content": "Hello, LEAF!"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "This is a test response"
        assert data["user_message_id"].startswith("msg_")
        assert data["assistant_message_id"].startswith("msg_")

        # Verify messages were saved to history
        response = client.get("/api/chat/history")
        messages = response.json()
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello, LEAF!"
        assert messages[1]["role"] == "assistant"

        # Clean up
        client.post("/api/projects/close")


class TestConfigFunctions:
    """Test configuration functions."""

    def test_get_ai_api_key_from_env(self, monkeypatch):
        """Test getting API key from environment."""
        monkeypatch.setenv("PYDANTIC_AI_API_KEY", "test-key-123")

        from leaf.core.config import get_ai_api_key

        assert get_ai_api_key() == "test-key-123"

    def test_get_default_model_from_env(self, monkeypatch):
        """Test getting default model from environment."""
        monkeypatch.setenv("LEAF_MODEL", "google-gla:gemini-1.5-pro")

        from leaf.core.config import get_default_model

        assert get_default_model() == "google-gla:gemini-1.5-pro"

    def test_get_default_model_fallback(self, monkeypatch, temp_dir):
        """Test default model fallback."""
        # Clear environment
        monkeypatch.delenv("LEAF_MODEL", raising=False)

        # Use isolated config dir
        config_dir = temp_dir / "config"
        config_dir.mkdir()
        monkeypatch.setenv("LEAF_CONFIG_DIR", str(config_dir))

        from leaf.core.config import get_default_model

        # Should fall back to default
        model = get_default_model()
        assert "gemini" in model.lower()


class TestEnvExample:
    """Test that .env.example exists and has correct format."""

    def test_env_example_exists(self):
        """Test that .env.example file exists."""
        env_example = Path(__file__).parent.parent / ".env.example"
        assert env_example.exists(), ".env.example file should exist"

    def test_env_example_has_required_keys(self):
        """Test that .env.example has required configuration keys."""
        env_example = Path(__file__).parent.parent / ".env.example"
        content = env_example.read_text()

        assert "PYDANTIC_AI_API_KEY" in content
        assert "LEAF_MODEL" in content
