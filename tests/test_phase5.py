"""Phase 5 tests - Execution Engine.

Tests for sandbox execution, runner, and execution API endpoints.
"""

import asyncio
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from leaf.execution import ExecutionResult, Sandbox, SandboxConfig, run_card_program
from leaf.main import app
from leaf.projects import ProjectManager, set_current_project
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
    config_dir = temp_dir / "config"
    config_dir.mkdir()
    monkeypatch.setenv("LEAF_CONFIG_DIR", str(config_dir))

    project_dir = temp_dir / "test_project"
    project_dir.mkdir()

    manager = ProjectManager()
    project = manager.create_project(project_dir, "Test Project")
    set_current_project(project)

    yield project

    await stop_all_watches()
    set_current_project(None)


class TestExecutionResult:
    """Test ExecutionResult dataclass."""

    def test_execution_result_success(self):
        """Test creating a successful execution result."""
        started = datetime.now()
        completed = datetime.now()

        result = ExecutionResult(
            success=True,
            exit_code=0,
            stdout="Hello, World!",
            stderr="",
            started_at=started,
            completed_at=completed,
            duration_seconds=1.5,
            error=None,
        )

        assert result.success is True
        assert result.exit_code == 0
        assert result.stdout == "Hello, World!"
        assert result.error is None

    def test_execution_result_failure(self):
        """Test creating a failed execution result."""
        started = datetime.now()
        completed = datetime.now()

        result = ExecutionResult(
            success=False,
            exit_code=1,
            stdout="",
            stderr="Error: something went wrong",
            started_at=started,
            completed_at=completed,
            duration_seconds=0.5,
            error="Exit code 1",
        )

        assert result.success is False
        assert result.exit_code == 1
        assert "Error" in result.stderr
        assert result.error is not None


class TestSandboxConfig:
    """Test SandboxConfig dataclass."""

    def test_sandbox_config_defaults(self, temp_dir):
        """Test SandboxConfig with default values."""
        config = SandboxConfig(
            card_id="test_card",
            program_path=temp_dir / "program",
            working_dir=temp_dir,
        )

        assert config.card_id == "test_card"
        assert config.timeout_seconds == 300
        assert config.dependencies == []

    def test_sandbox_config_custom(self, temp_dir):
        """Test SandboxConfig with custom values."""
        config = SandboxConfig(
            card_id="test_card",
            program_path=temp_dir / "program",
            working_dir=temp_dir,
            timeout_seconds=60,
            dependencies=["pandas", "numpy"],
        )

        assert config.timeout_seconds == 60
        assert "pandas" in config.dependencies
        assert "numpy" in config.dependencies


class TestSandbox:
    """Test Sandbox class."""

    def test_sandbox_venv_path(self, temp_dir):
        """Test that venv path is calculated correctly."""
        program_dir = temp_dir / "program"
        program_dir.mkdir()

        config = SandboxConfig(
            card_id="test",
            program_path=program_dir,
            working_dir=temp_dir,
        )

        sandbox = Sandbox(config)
        assert sandbox.venv_path == program_dir / ".venv"

    @pytest.mark.asyncio
    async def test_sandbox_setup_creates_pyproject(self, temp_dir):
        """Test that setup creates pyproject.toml if missing."""
        program_dir = temp_dir / "program"
        program_dir.mkdir()

        # Create main.py
        main_file = program_dir / "main.py"
        main_file.write_text('print("Hello")')

        config = SandboxConfig(
            card_id="test",
            program_path=program_dir,
            working_dir=temp_dir,
            dependencies=["requests"],
        )

        sandbox = Sandbox(config)

        # Mock uv sync to avoid actually running it
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b"", b""))
            mock_exec.return_value = mock_process

            await sandbox.setup()

        # Check pyproject.toml was created
        pyproject = program_dir / "pyproject.toml"
        assert pyproject.exists()
        content = pyproject.read_text()
        assert "requests" in content
        assert "card-test" in content

    @pytest.mark.asyncio
    async def test_sandbox_setup_missing_main(self, temp_dir):
        """Test that setup fails if main.py is missing."""
        program_dir = temp_dir / "program"
        program_dir.mkdir()

        config = SandboxConfig(
            card_id="test",
            program_path=program_dir,
            working_dir=temp_dir,
        )

        sandbox = Sandbox(config)

        with pytest.raises(FileNotFoundError, match="main.py not found"):
            await sandbox.setup()

    @pytest.mark.asyncio
    async def test_sandbox_run_success(self, temp_dir):
        """Test running a program in the sandbox (mocked)."""
        program_dir = temp_dir / "program"
        program_dir.mkdir()
        (program_dir / "main.py").write_text('print("test")')

        config = SandboxConfig(
            card_id="test",
            program_path=program_dir,
            working_dir=temp_dir,
            timeout_seconds=10,
        )

        sandbox = Sandbox(config)

        # Mock the subprocess execution
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b"test output", b""))
            mock_exec.return_value = mock_process

            result = await sandbox.run()

        assert result.success is True
        assert result.exit_code == 0
        assert result.stdout == "test output"

    @pytest.mark.asyncio
    async def test_sandbox_run_timeout(self, temp_dir):
        """Test that sandbox handles timeout correctly."""
        program_dir = temp_dir / "program"
        program_dir.mkdir()
        (program_dir / "main.py").write_text('import time; time.sleep(100)')

        config = SandboxConfig(
            card_id="test",
            program_path=program_dir,
            working_dir=temp_dir,
            timeout_seconds=1,
        )

        sandbox = Sandbox(config)

        # Mock to simulate timeout
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.kill = AsyncMock()
            mock_process.wait = AsyncMock()

            async def timeout_communicate():
                raise asyncio.TimeoutError()

            mock_process.communicate = timeout_communicate
            mock_exec.return_value = mock_process

            result = await sandbox.run()

        assert result.success is False
        assert result.exit_code == -1
        assert "Timeout" in result.error

    @pytest.mark.asyncio
    async def test_sandbox_run_with_args(self, temp_dir):
        """Test running a program with command line arguments."""
        program_dir = temp_dir / "program"
        program_dir.mkdir()
        (program_dir / "main.py").write_text('import sys; print(sys.argv)')

        config = SandboxConfig(
            card_id="test",
            program_path=program_dir,
            working_dir=temp_dir,
        )

        sandbox = Sandbox(config)

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b"args received", b""))
            mock_exec.return_value = mock_process

            result = await sandbox.run(args=["/path/to/file.csv"])

        assert result.success is True
        # Verify args were passed to the command
        call_args = mock_exec.call_args
        assert "/path/to/file.csv" in call_args[0]

    @pytest.mark.asyncio
    async def test_sandbox_environment_variables(self, temp_dir):
        """Test that sandbox sets correct environment variables."""
        program_dir = temp_dir / "program"
        program_dir.mkdir()
        (program_dir / "main.py").write_text('import os; print(os.environ)')

        config = SandboxConfig(
            card_id="test_card_123",
            program_path=program_dir,
            working_dir=temp_dir,
        )

        sandbox = Sandbox(config)

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b"output", b""))
            mock_exec.return_value = mock_process

            await sandbox.run()

        # Check environment was passed
        call_kwargs = mock_exec.call_args[1]
        env = call_kwargs.get("env", {})
        assert env.get("LEAF_PROJECT_ROOT") == str(temp_dir)
        assert env.get("LEAF_CARD_ID") == "test_card_123"


class TestRunCardProgram:
    """Test the run_card_program convenience function."""

    @pytest.mark.asyncio
    async def test_run_card_program_basic(self, temp_dir):
        """Test basic program execution."""
        program_dir = temp_dir / "program"
        program_dir.mkdir()
        (program_dir / "main.py").write_text('print("hello")')

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b"hello", b""))
            mock_exec.return_value = mock_process

            result = await run_card_program(
                program_path=program_dir,
                working_dir=temp_dir,
                card_id="test",
            )

        assert result.success is True
        assert result.stdout == "hello"

    @pytest.mark.asyncio
    async def test_run_card_program_with_trigger_file(self, temp_dir):
        """Test program execution with trigger file argument."""
        program_dir = temp_dir / "program"
        program_dir.mkdir()
        (program_dir / "main.py").write_text('import sys; print(sys.argv[1])')

        trigger_file = temp_dir / "data" / "input.csv"

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b"processed", b""))
            mock_exec.return_value = mock_process

            result = await run_card_program(
                program_path=program_dir,
                working_dir=temp_dir,
                card_id="test",
                trigger_file=trigger_file,
            )

        assert result.success is True
        # Verify trigger file was passed
        call_args = mock_exec.call_args[0]
        assert str(trigger_file) in call_args


class TestExecutionAPI:
    """Test execution API endpoints."""

    def test_list_executions_empty(self, client, monkeypatch, temp_dir):
        """Test listing executions when empty."""
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

        # List executions
        response = client.get("/api/executions")
        assert response.status_code == 200
        assert response.json() == []

        # Clean up
        client.post("/api/projects/close")

    def test_get_execution_not_found(self, client, monkeypatch, temp_dir):
        """Test getting a non-existent execution."""
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

        # Try to get non-existent execution
        response = client.get("/api/executions/exec_nonexistent")
        assert response.status_code == 404

        # Clean up
        client.post("/api/projects/close")

    def test_manual_execution_card_not_found(self, client, monkeypatch, temp_dir):
        """Test manual execution with non-existent card."""
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

        # Try to execute non-existent card
        response = client.post(
            "/api/executions/manual",
            json={"card_id": "nonexistent_card"},
        )
        assert response.status_code == 400
        assert "not found" in response.json()["detail"].lower()

        # Clean up
        client.post("/api/projects/close")

    @pytest.mark.asyncio
    async def test_manual_execution_success(self, client, monkeypatch, temp_dir):
        """Test successful manual card execution."""
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

        # Create a card
        response = client.post(
            "/api/cards",
            json={
                "name": "Test Card",
                "description": "A test card",
                "user_prompt": "Test",
                "trigger_config": {"type": "manual"},
            },
        )
        assert response.status_code == 200
        card_data = response.json()
        card_id = card_data["id"]
        program_path = card_data["program_path"]

        # Write actual code to the card's main.py (use program_path from card)
        main_py = project_dir / program_path / "main.py"
        main_py.write_text('print("executed successfully")')

        # Mock the subprocess execution
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b"executed", b""))
            mock_exec.return_value = mock_process

            # Execute manually
            response = client.post(
                "/api/executions/manual",
                json={"card_id": card_id},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["card_id"] == card_id
        assert data["status"] == "completed"
        assert data["id"].startswith("exec_")

        # Verify execution appears in list
        response = client.get("/api/executions")
        assert response.status_code == 200
        executions = response.json()
        assert len(executions) == 1
        assert executions[0]["card_id"] == card_id

        # Clean up
        client.post("/api/projects/close")

    def test_list_executions_with_filters(self, client, monkeypatch, temp_dir):
        """Test listing executions with card_id and status filters."""
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

        # Create two cards
        response1 = client.post(
            "/api/cards",
            json={
                "name": "Card 1",
                "user_prompt": "Test",
                "trigger_config": {"type": "manual"},
            },
        )
        card_data_1 = response1.json()
        card_id_1 = card_data_1["id"]
        program_path_1 = card_data_1["program_path"]

        response2 = client.post(
            "/api/cards",
            json={
                "name": "Card 2",
                "user_prompt": "Test",
                "trigger_config": {"type": "manual"},
            },
        )
        card_data_2 = response2.json()
        card_id_2 = card_data_2["id"]
        program_path_2 = card_data_2["program_path"]

        # Write code to cards (use program_path from card)
        (project_dir / program_path_1 / "main.py").write_text('print("test")')
        (project_dir / program_path_2 / "main.py").write_text('print("test")')

        # Execute both cards
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b"", b""))
            mock_exec.return_value = mock_process

            client.post("/api/executions/manual", json={"card_id": card_id_1})
            client.post("/api/executions/manual", json={"card_id": card_id_2})

        # Filter by card_id
        response = client.get(f"/api/executions?card_id={card_id_1}")
        assert response.status_code == 200
        executions = response.json()
        assert len(executions) == 1
        assert executions[0]["card_id"] == card_id_1

        # Filter by status
        response = client.get("/api/executions?status=completed")
        assert response.status_code == 200
        executions = response.json()
        assert len(executions) == 2
        assert all(ex["status"] == "completed" for ex in executions)

        # Clean up
        client.post("/api/projects/close")


class TestFileEventExecution:
    """Test execution triggered by file events."""

    @pytest.mark.asyncio
    async def test_file_event_triggers_execution(self, monkeypatch, temp_dir):
        """Test that file events trigger card execution."""
        from leaf.cards import create_card
        from leaf.cards.models import CardCreate, ProgramConfig, TriggerConfig
        from leaf.core.events import emit_file_event
        from leaf.projects import ProjectManager, set_current_project
        from leaf.watcher.file_watcher import FileEvent

        config_dir = temp_dir / "config"
        config_dir.mkdir()
        monkeypatch.setenv("LEAF_CONFIG_DIR", str(config_dir))

        project_dir = temp_dir / "test_project"
        project_dir.mkdir()

        manager = ProjectManager()
        project = manager.create_project(project_dir, "Test Project")
        set_current_project(project)

        try:
            # Create inbox folder
            inbox = project_dir / "inbox"
            inbox.mkdir()

            # Create a card that watches inbox for CSV files
            card_data = CardCreate(
                name="CSV Processor",
                description="Processes CSV files",
                user_prompt="Process CSV files",
                trigger_config=TriggerConfig(
                    type="file_created",
                    folder="inbox",
                    pattern="*.csv",
                ),
                program_config=ProgramConfig(dependencies=[]),
            )
            card = create_card(card_data)

            # Write actual code to main.py (use program_path from card)
            program_dir = project_dir / card.program_path
            (program_dir / "main.py").write_text('print("processed")')

            # Create a file event
            test_file = inbox / "data.csv"
            test_file.write_text("col1,col2\n1,2")

            file_event = FileEvent(
                type="file.created",
                path=test_file,
                folder=inbox,
                filename="data.csv",
                size=test_file.stat().st_size,
                watch_id="watch_123",
                card_id=card.id,
            )

            # Mock subprocess to avoid actually running uv
            with patch("asyncio.create_subprocess_exec") as mock_exec:
                mock_process = AsyncMock()
                mock_process.returncode = 0
                mock_process.communicate = AsyncMock(return_value=(b"processed", b""))
                mock_exec.return_value = mock_process

                # Emit the file event
                event = await emit_file_event(file_event)

            # Verify event was processed
            assert event.status == "completed"
            assert event.matched_cards is not None
            assert card.id in event.matched_cards

        finally:
            await stop_all_watches()
            set_current_project(None)
