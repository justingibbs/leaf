"""Phase 2 tests - File Watching & Events."""

import asyncio
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from leaf.core.events import emit_event
from leaf.db.models import Event
from leaf.db.session import get_session
from leaf.main import app
from leaf.projects import ProjectManager, get_current_project, set_current_project
from leaf.watcher import FileWatcher, WatchConfig, add_watch, get_watches, stop_all_watches
from leaf.watcher.file_watcher import FileEvent


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


class TestFileWatcher:
    """Test the FileWatcher class."""

    @pytest.mark.asyncio
    async def test_watcher_creation(self, temp_dir):
        """Test creating a file watcher."""
        events = []

        async def on_event(event: FileEvent):
            events.append(event)

        watcher = FileWatcher(on_event=on_event)
        assert watcher is not None

    @pytest.mark.asyncio
    async def test_add_watch(self, temp_dir):
        """Test adding a watch."""
        events = []

        async def on_event(event: FileEvent):
            events.append(event)

        watcher = FileWatcher(on_event=on_event)

        watch_dir = temp_dir / "watch_me"
        watch_dir.mkdir()

        config = WatchConfig(
            id="test_watch",
            folder=watch_dir,
            pattern="*.txt",
        )

        watcher.add_watch(config)
        assert watcher.has_watch("test_watch")

        await watcher.stop_all()

    @pytest.mark.asyncio
    async def test_watch_file_created(self, temp_dir):
        """Test that file creation triggers an event."""
        events = []
        event_received = asyncio.Event()

        async def on_event(event: FileEvent):
            events.append(event)
            event_received.set()

        watcher = FileWatcher(on_event=on_event, debounce_ms=50)

        watch_dir = temp_dir / "watch_me"
        watch_dir.mkdir()

        config = WatchConfig(
            id="test_watch",
            folder=watch_dir,
            pattern="*.txt",
        )

        watcher.add_watch(config)

        # Give watcher time to start
        await asyncio.sleep(0.1)

        # Create a file
        test_file = watch_dir / "test.txt"
        test_file.write_text("hello")

        # Wait for event (with timeout)
        try:
            await asyncio.wait_for(event_received.wait(), timeout=2.0)
        except TimeoutError:
            pytest.fail("Timeout waiting for file event")

        await watcher.stop_all()

        assert len(events) >= 1
        assert events[0].type == "file.created"
        assert events[0].filename == "test.txt"

    @pytest.mark.asyncio
    async def test_pattern_filtering(self, temp_dir):
        """Test that only matching files trigger events."""
        events = []

        async def on_event(event: FileEvent):
            events.append(event)

        watcher = FileWatcher(on_event=on_event, debounce_ms=50)

        watch_dir = temp_dir / "watch_me"
        watch_dir.mkdir()

        config = WatchConfig(
            id="test_watch",
            folder=watch_dir,
            pattern="*.csv",  # Only CSV files
        )

        watcher.add_watch(config)

        # Give watcher time to start
        await asyncio.sleep(0.1)

        # Create a non-matching file
        (watch_dir / "test.txt").write_text("hello")

        # Create a matching file
        (watch_dir / "data.csv").write_text("a,b,c")

        # Wait a bit for events to process
        await asyncio.sleep(0.3)

        await watcher.stop_all()

        # Should only have CSV event
        csv_events = [e for e in events if e.filename == "data.csv"]
        txt_events = [e for e in events if e.filename == "test.txt"]

        assert len(csv_events) >= 1
        assert len(txt_events) == 0

    @pytest.mark.asyncio
    async def test_ignore_hidden_files(self, temp_dir):
        """Test that hidden files are ignored."""
        events = []

        async def on_event(event: FileEvent):
            events.append(event)

        watcher = FileWatcher(on_event=on_event, debounce_ms=50)

        watch_dir = temp_dir / "watch_me"
        watch_dir.mkdir()

        config = WatchConfig(
            id="test_watch",
            folder=watch_dir,
            pattern="*",
        )

        watcher.add_watch(config)

        # Give watcher time to start
        await asyncio.sleep(0.1)

        # Create a hidden file
        (watch_dir / ".hidden").write_text("secret")

        # Create a regular file
        (watch_dir / "visible.txt").write_text("hello")

        # Wait a bit for events to process
        await asyncio.sleep(0.3)

        await watcher.stop_all()

        # Should only have visible file event
        hidden_events = [e for e in events if ".hidden" in e.filename]
        visible_events = [e for e in events if e.filename == "visible.txt"]

        assert len(hidden_events) == 0
        assert len(visible_events) >= 1


class TestEventBus:
    """Test the event bus."""

    @pytest.mark.asyncio
    async def test_emit_event(self, project_context):
        """Test emitting an event."""
        _ = project_context  # Ensure project context is active

        event = await emit_event(
            "test.event",
            {"key": "value"},
        )

        assert event.id.startswith("evt_")
        assert event.type == "test.event"
        assert event.payload == {"key": "value"}
        assert event.status == "pending"

    @pytest.mark.asyncio
    async def test_event_persisted(self, project_context):
        """Test that events are persisted to database."""
        ctx = project_context

        event = await emit_event(
            "test.persisted",
            {"data": "test"},
        )

        # Query the database
        gen = get_session(ctx.database_path)
        session = next(gen)
        try:
            db_event = session.get(Event, event.id)
            assert db_event is not None
            assert db_event.type == "test.persisted"
            assert db_event.payload == {"data": "test"}
        finally:
            try:
                next(gen)
            except StopIteration:
                pass


class TestWatcherManager:
    """Test the watcher manager."""

    @pytest.mark.asyncio
    async def test_add_and_remove_watch(self, project_context):
        """Test adding and removing watches."""
        ctx = project_context

        # Create a folder to watch
        watch_dir = ctx.path / "inbox"
        watch_dir.mkdir()

        # Add watch
        config = add_watch(folder=watch_dir, pattern="*.csv")
        assert config.id.startswith("watch_")

        # Check it's in the list
        watches = get_watches()
        assert len(watches) == 1
        assert watches[0].pattern == "*.csv"

        # Clean up
        await stop_all_watches()
        assert len(get_watches()) == 0


class TestDebugAPI:
    """Test debug API endpoints."""

    def test_add_watch_requires_project(self, client, monkeypatch, temp_dir):
        """Test that adding a watch requires an active project."""
        config_dir = temp_dir / "config"
        config_dir.mkdir()
        monkeypatch.setenv("LEAF_CONFIG_DIR", str(config_dir))

        set_current_project(None)

        response = client.post(
            "/api/debug/watch",
            json={"folder": "inbox"},
        )
        assert response.status_code == 400
        assert "No active project" in response.json()["detail"]

    def test_add_watch_success(self, client, monkeypatch, temp_dir):
        """Test adding a watch via API."""
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

        # Create inbox folder
        inbox = project_dir / "inbox"
        inbox.mkdir()

        # Add watch
        response = client.post(
            "/api/debug/watch",
            json={"folder": "inbox", "pattern": "*.csv"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["pattern"] == "*.csv"
        assert "inbox" in data["folder"]

        # List watches
        response = client.get("/api/debug/watches")
        assert response.status_code == 200
        watches = response.json()
        assert len(watches) == 1

        # Clean up
        client.post("/api/projects/close")

    def test_emit_event_via_api(self, client, monkeypatch, temp_dir):
        """Test emitting an event via API."""
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

        # Emit event
        response = client.post(
            "/api/debug/event",
            json={"type": "test.manual", "payload": {"foo": "bar"}},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "test.manual"
        assert data["id"].startswith("evt_")

        # Check it's in the events list
        response = client.get("/api/events")
        assert response.status_code == 200
        events = response.json()
        assert len(events) == 1
        assert events[0]["type"] == "test.manual"

        # Clean up
        client.post("/api/projects/close")
