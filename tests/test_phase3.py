"""Phase 3 tests - Cards & Triggers."""

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from leaf.cards import (
    CardCreate,
    CardUpdate,
    TriggerConfig,
    create_card,
    delete_card,
    find_matching_cards,
    get_card,
    list_cards,
    update_card,
)
from leaf.main import app
from leaf.projects import ProjectManager, get_current_project, set_current_project
from leaf.watcher import get_watches, stop_all_watches


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


class TestCardRegistry:
    """Test the card registry functions."""

    @pytest.mark.asyncio
    async def test_create_card(self, project_context):
        """Test creating a card."""
        ctx = project_context

        data = CardCreate(
            name="CSV Analyzer",
            description="Analyzes CSV files",
            user_prompt="Analyze CSV files and generate reports",
            trigger_config=TriggerConfig(
                type="file_created",
                folder="inbox",
                pattern="*.csv",
            ),
        )

        card = create_card(data)

        assert card.id.startswith("card_")
        assert card.name == "CSV Analyzer"
        assert card.description == "Analyzes CSV files"
        assert card.trigger_config["type"] == "file_created"
        assert card.trigger_config["folder"] == "inbox"
        assert card.trigger_config["pattern"] == "*.csv"
        assert card.enabled is True

        # Check program directory was created
        program_dir = ctx.path / card.program_path
        assert program_dir.exists()
        assert (program_dir / "main.py").exists()

    @pytest.mark.asyncio
    async def test_get_card(self, project_context):
        """Test getting a card by ID."""
        data = CardCreate(
            name="Test Card",
            user_prompt="Test prompt",
            trigger_config=TriggerConfig(type="manual"),
        )

        created = create_card(data)
        retrieved = get_card(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == "Test Card"

    @pytest.mark.asyncio
    async def test_get_nonexistent_card(self, project_context):
        """Test getting a card that doesn't exist."""
        card = get_card("card_nonexistent")
        assert card is None

    @pytest.mark.asyncio
    async def test_list_cards(self, project_context):
        """Test listing all cards."""
        # Create a few cards
        for i in range(3):
            create_card(
                CardCreate(
                    name=f"Card {i}",
                    user_prompt=f"Prompt {i}",
                    trigger_config=TriggerConfig(type="manual"),
                )
            )

        cards = list_cards()
        assert len(cards) == 3

    @pytest.mark.asyncio
    async def test_list_enabled_cards_only(self, project_context):
        """Test listing only enabled cards."""
        # Create enabled card
        create_card(
            CardCreate(
                name="Enabled Card",
                user_prompt="Enabled",
                trigger_config=TriggerConfig(type="manual"),
                enabled=True,
            )
        )

        # Create disabled card
        create_card(
            CardCreate(
                name="Disabled Card",
                user_prompt="Disabled",
                trigger_config=TriggerConfig(type="manual"),
                enabled=False,
            )
        )

        all_cards = list_cards()
        enabled_cards = list_cards(enabled_only=True)

        assert len(all_cards) == 2
        assert len(enabled_cards) == 1
        assert enabled_cards[0].name == "Enabled Card"

    @pytest.mark.asyncio
    async def test_update_card(self, project_context):
        """Test updating a card."""
        card = create_card(
            CardCreate(
                name="Original Name",
                user_prompt="Original prompt",
                trigger_config=TriggerConfig(type="manual"),
            )
        )

        updated = update_card(
            card.id,
            CardUpdate(name="Updated Name", description="New description"),
        )

        assert updated.name == "Updated Name"
        assert updated.description == "New description"
        assert updated.user_prompt == "Original prompt"  # Unchanged

    @pytest.mark.asyncio
    async def test_delete_card(self, project_context):
        """Test deleting a card."""
        card = create_card(
            CardCreate(
                name="To Delete",
                user_prompt="Delete me",
                trigger_config=TriggerConfig(type="manual"),
            )
        )

        deleted = delete_card(card.id)
        assert deleted is True

        # Verify it's gone
        retrieved = get_card(card.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_card(self, project_context):
        """Test deleting a card that doesn't exist."""
        deleted = delete_card("card_nonexistent")
        assert deleted is False


class TestCardWatchIntegration:
    """Test that cards properly set up file watchers."""

    @pytest.mark.asyncio
    async def test_card_creates_watch(self, project_context):
        """Test that creating a file-based card creates a watch."""
        ctx = project_context

        # Create inbox folder
        inbox = ctx.path / "inbox"
        inbox.mkdir()

        card = create_card(
            CardCreate(
                name="File Watcher Card",
                user_prompt="Watch for CSV files",
                trigger_config=TriggerConfig(
                    type="file_created",
                    folder="inbox",
                    pattern="*.csv",
                ),
            )
        )

        watches = get_watches()
        assert len(watches) == 1
        assert watches[0].card_id == card.id
        assert watches[0].pattern == "*.csv"

    @pytest.mark.asyncio
    async def test_disabled_card_no_watch(self, project_context):
        """Test that disabled cards don't create watches."""
        ctx = project_context

        inbox = ctx.path / "inbox"
        inbox.mkdir()

        create_card(
            CardCreate(
                name="Disabled Card",
                user_prompt="Watch for CSV files",
                trigger_config=TriggerConfig(
                    type="file_created",
                    folder="inbox",
                    pattern="*.csv",
                ),
                enabled=False,
            )
        )

        watches = get_watches()
        assert len(watches) == 0

    @pytest.mark.asyncio
    async def test_delete_card_removes_watch(self, project_context):
        """Test that deleting a card removes its watch."""
        ctx = project_context

        inbox = ctx.path / "inbox"
        inbox.mkdir()

        card = create_card(
            CardCreate(
                name="Delete Me",
                user_prompt="Watch for files",
                trigger_config=TriggerConfig(
                    type="file_created",
                    folder="inbox",
                    pattern="*",
                ),
            )
        )

        # Verify watch exists
        watches = get_watches()
        assert len(watches) == 1

        # Delete card
        delete_card(card.id)

        # Verify watch is gone
        watches = get_watches()
        assert len(watches) == 0

    @pytest.mark.asyncio
    async def test_disable_card_removes_watch(self, project_context):
        """Test that disabling a card removes its watch."""
        ctx = project_context

        inbox = ctx.path / "inbox"
        inbox.mkdir()

        card = create_card(
            CardCreate(
                name="Disable Me",
                user_prompt="Watch for files",
                trigger_config=TriggerConfig(
                    type="file_created",
                    folder="inbox",
                    pattern="*",
                ),
            )
        )

        # Verify watch exists
        watches = get_watches()
        assert len(watches) == 1

        # Disable card
        update_card(card.id, CardUpdate(enabled=False))

        # Verify watch is gone
        watches = get_watches()
        assert len(watches) == 0

    @pytest.mark.asyncio
    async def test_enable_card_creates_watch(self, project_context):
        """Test that enabling a card creates its watch."""
        ctx = project_context

        inbox = ctx.path / "inbox"
        inbox.mkdir()

        # Create disabled card
        card = create_card(
            CardCreate(
                name="Enable Me",
                user_prompt="Watch for files",
                trigger_config=TriggerConfig(
                    type="file_created",
                    folder="inbox",
                    pattern="*",
                ),
                enabled=False,
            )
        )

        # Verify no watch
        watches = get_watches()
        assert len(watches) == 0

        # Enable card
        update_card(card.id, CardUpdate(enabled=True))

        # Verify watch exists
        watches = get_watches()
        assert len(watches) == 1


class TestTriggerMatching:
    """Test trigger matching logic."""

    @pytest.mark.asyncio
    async def test_match_file_created_event(self, project_context):
        """Test matching a file.created event to cards."""
        ctx = project_context

        inbox = ctx.path / "inbox"
        inbox.mkdir()

        # Create a card that watches for CSV files
        card = create_card(
            CardCreate(
                name="CSV Watcher",
                user_prompt="Watch for CSV files",
                trigger_config=TriggerConfig(
                    type="file_created",
                    folder="inbox",
                    pattern="*.csv",
                ),
            )
        )

        # Create payload matching what a file event would have
        payload = {
            "folder": str(inbox),
            "filename": "data.csv",
            "path": str(inbox / "data.csv"),
        }

        matching = find_matching_cards("file.created", payload)
        assert len(matching) == 1
        assert matching[0].id == card.id

    @pytest.mark.asyncio
    async def test_no_match_wrong_pattern(self, project_context):
        """Test that events with wrong pattern don't match."""
        ctx = project_context

        inbox = ctx.path / "inbox"
        inbox.mkdir()

        create_card(
            CardCreate(
                name="CSV Watcher",
                user_prompt="Watch for CSV files",
                trigger_config=TriggerConfig(
                    type="file_created",
                    folder="inbox",
                    pattern="*.csv",
                ),
            )
        )

        # TXT file shouldn't match
        payload = {
            "folder": str(inbox),
            "filename": "data.txt",
            "path": str(inbox / "data.txt"),
        }

        matching = find_matching_cards("file.created", payload)
        assert len(matching) == 0

    @pytest.mark.asyncio
    async def test_no_match_wrong_folder(self, project_context):
        """Test that events from wrong folder don't match."""
        ctx = project_context

        inbox = ctx.path / "inbox"
        inbox.mkdir()
        other = ctx.path / "other"
        other.mkdir()

        create_card(
            CardCreate(
                name="Inbox Watcher",
                user_prompt="Watch inbox",
                trigger_config=TriggerConfig(
                    type="file_created",
                    folder="inbox",
                    pattern="*",
                ),
            )
        )

        # File in other folder shouldn't match
        payload = {
            "folder": str(other),
            "filename": "data.csv",
            "path": str(other / "data.csv"),
        }

        matching = find_matching_cards("file.created", payload)
        assert len(matching) == 0


class TestCardAPI:
    """Test card API endpoints."""

    def test_create_card_api(self, client, monkeypatch, temp_dir):
        """Test creating a card via API."""
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

        # Create card
        response = client.post(
            "/api/cards",
            json={
                "name": "Test Card",
                "user_prompt": "Test prompt",
                "trigger_config": {"type": "manual"},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Card"
        assert data["id"].startswith("card_")
        assert data["enabled"] is True

        # Clean up
        client.post("/api/projects/close")

    def test_list_cards_api(self, client, monkeypatch, temp_dir):
        """Test listing cards via API."""
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
        client.post(
            "/api/cards",
            json={
                "name": "Card 1",
                "user_prompt": "Prompt 1",
                "trigger_config": {"type": "manual"},
            },
        )

        # List cards
        response = client.get("/api/cards")
        assert response.status_code == 200
        cards = response.json()
        assert len(cards) == 1
        assert cards[0]["name"] == "Card 1"

        # Clean up
        client.post("/api/projects/close")

    def test_get_card_api(self, client, monkeypatch, temp_dir):
        """Test getting a card by ID via API."""
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
                "user_prompt": "Test prompt",
                "trigger_config": {"type": "manual"},
            },
        )
        card_id = response.json()["id"]

        # Get card
        response = client.get(f"/api/cards/{card_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == card_id
        assert data["name"] == "Test Card"

        # Clean up
        client.post("/api/projects/close")

    def test_update_card_api(self, client, monkeypatch, temp_dir):
        """Test updating a card via API."""
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
                "name": "Original Name",
                "user_prompt": "Original prompt",
                "trigger_config": {"type": "manual"},
            },
        )
        card_id = response.json()["id"]

        # Update card
        response = client.put(
            f"/api/cards/{card_id}",
            json={"name": "Updated Name"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"

        # Clean up
        client.post("/api/projects/close")

    def test_delete_card_api(self, client, monkeypatch, temp_dir):
        """Test deleting a card via API."""
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
                "name": "To Delete",
                "user_prompt": "Delete me",
                "trigger_config": {"type": "manual"},
            },
        )
        card_id = response.json()["id"]

        # Delete card
        response = client.delete(f"/api/cards/{card_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"

        # Verify it's gone
        response = client.get(f"/api/cards/{card_id}")
        assert response.status_code == 404

        # Clean up
        client.post("/api/projects/close")

    def test_manual_trigger_api(self, client, monkeypatch, temp_dir):
        """Test manually triggering a card via API."""
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
                "name": "Runnable Card",
                "user_prompt": "Run me",
                "trigger_config": {"type": "manual"},
            },
        )
        card_id = response.json()["id"]

        # Trigger card
        response = client.post(f"/api/cards/{card_id}/run")
        assert response.status_code == 200
        data = response.json()
        assert data["card_id"] == card_id
        assert data["event_id"].startswith("evt_")

        # Check event was created
        response = client.get("/api/events")
        events = response.json()
        trigger_events = [e for e in events if e["type"] == "card.triggered"]
        assert len(trigger_events) >= 1

        # Clean up
        client.post("/api/projects/close")

    def test_cannot_run_disabled_card(self, client, monkeypatch, temp_dir):
        """Test that disabled cards cannot be manually triggered."""
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

        # Create a disabled card
        response = client.post(
            "/api/cards",
            json={
                "name": "Disabled Card",
                "user_prompt": "Cannot run",
                "trigger_config": {"type": "manual"},
                "enabled": False,
            },
        )
        card_id = response.json()["id"]

        # Try to trigger card
        response = client.post(f"/api/cards/{card_id}/run")
        assert response.status_code == 400
        assert "disabled" in response.json()["detail"].lower()

        # Clean up
        client.post("/api/projects/close")
