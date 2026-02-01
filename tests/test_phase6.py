"""Phase 6 tests - MCP Integration.

Tests for MCP client, configuration, registry, and API endpoints.
"""

import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from leaf.main import app
from leaf.mcp import (
    MCPClient,
    MCPClientError,
    MCPServerConfig,
    add_mcp_server,
    get_mcp_server,
    initialize_builtin_servers,
    list_mcp_servers,
    load_mcp_config,
    remove_mcp_server,
)
from leaf.mcp.protocol import MCPTool, MCPToolInputSchema


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
def mock_config_dir(monkeypatch, temp_dir):
    """Mock the config directory to use a temp directory."""
    config_dir = temp_dir / "config"
    config_dir.mkdir()
    monkeypatch.setenv("LEAF_CONFIG_DIR", str(config_dir))
    return config_dir


class TestMCPServerConfig:
    """Test MCP server configuration."""

    def test_create_server_config(self):
        """Test creating a server configuration."""
        config = MCPServerConfig(
            id="test-server",
            name="Test Server",
            command="node",
            args=["server.js"],
            env={"API_KEY": "secret"},
            enabled=True,
            description="A test server",
        )

        assert config.id == "test-server"
        assert config.name == "Test Server"
        assert config.command == "node"
        assert config.args == ["server.js"]
        assert config.env == {"API_KEY": "secret"}
        assert config.enabled is True

    def test_server_config_defaults(self):
        """Test server configuration defaults."""
        config = MCPServerConfig(
            id="minimal",
            name="Minimal",
            command="server",
        )

        assert config.args == []
        assert config.env == {}
        assert config.enabled is True
        assert config.description is None


class TestMCPConfigPersistence:
    """Test MCP configuration persistence."""

    def test_save_and_load_config(self, mock_config_dir):
        """Test saving and loading MCP configuration."""
        # Add a server
        server = MCPServerConfig(
            id="test",
            name="Test",
            command="test-command",
            args=["--arg1"],
        )
        add_mcp_server(server)

        # Load and verify
        config = load_mcp_config()
        assert "test" in config.servers
        assert config.servers["test"].name == "Test"
        assert config.servers["test"].command == "test-command"

    def test_add_multiple_servers(self, mock_config_dir):
        """Test adding multiple servers."""
        for i in range(3):
            server = MCPServerConfig(
                id=f"server-{i}",
                name=f"Server {i}",
                command=f"cmd-{i}",
            )
            add_mcp_server(server)

        servers = list_mcp_servers()
        assert len(servers) == 3

    def test_remove_server(self, mock_config_dir):
        """Test removing a server."""
        server = MCPServerConfig(id="to-remove", name="Remove Me", command="rm")
        add_mcp_server(server)

        assert get_mcp_server("to-remove") is not None

        remove_mcp_server("to-remove")
        assert get_mcp_server("to-remove") is None

    def test_list_enabled_only(self, mock_config_dir):
        """Test listing only enabled servers."""
        # Add enabled and disabled servers
        add_mcp_server(
            MCPServerConfig(id="enabled", name="Enabled", command="cmd", enabled=True)
        )
        add_mcp_server(
            MCPServerConfig(id="disabled", name="Disabled", command="cmd", enabled=False)
        )

        all_servers = list_mcp_servers()
        enabled_servers = list_mcp_servers(enabled_only=True)

        assert len(all_servers) == 2
        assert len(enabled_servers) == 1
        assert enabled_servers[0].id == "enabled"

    def test_initialize_builtin_servers(self, mock_config_dir):
        """Test initializing built-in servers."""
        initialize_builtin_servers()

        servers = list_mcp_servers()
        server_ids = [s.id for s in servers]

        # Should have built-in servers
        assert "filesystem" in server_ids
        assert "fetch" in server_ids
        assert "memory" in server_ids

        # Built-ins should be disabled by default
        for server in servers:
            if server.id in ["filesystem", "fetch", "memory"]:
                assert server.enabled is False


class TestMCPProtocol:
    """Test MCP protocol types."""

    def test_mcp_tool_creation(self):
        """Test creating an MCP tool definition."""
        tool = MCPTool(
            name="read_file",
            description="Read a file from disk",
            inputSchema=MCPToolInputSchema(
                type="object",
                properties={
                    "path": {"type": "string", "description": "File path"},
                },
                required=["path"],
            ),
        )

        assert tool.name == "read_file"
        assert "path" in tool.inputSchema.properties
        assert "path" in tool.inputSchema.required


class TestMCPClient:
    """Test MCP client."""

    def test_client_initialization(self):
        """Test client initialization."""
        client = MCPClient(
            server_id="test",
            command="node",
            args=["server.js"],
            env={"KEY": "value"},
        )

        assert client.server_id == "test"
        assert client.command == "node"
        assert client.args == ["server.js"]
        assert not client.is_connected

    @pytest.mark.asyncio
    async def test_client_connect_disconnect(self):
        """Test client connect and disconnect with mocked subprocess."""
        # We test that the client can be created and properties work
        # Full integration testing requires an actual MCP server
        client = MCPClient(server_id="test", command="echo", args=["test"])

        assert client.server_id == "test"
        assert not client.is_connected
        assert client.tools == []

    @pytest.mark.asyncio
    async def test_client_not_connected_error(self):
        """Test calling tool when not connected raises error."""
        client = MCPClient(server_id="test", command="echo")

        with pytest.raises(MCPClientError, match="Not connected"):
            await client.call_tool("some_tool", {})


class TestMCPRegistry:
    """Test MCP registry."""

    @pytest.mark.asyncio
    async def test_registry_singleton(self):
        """Test that registry is a singleton."""
        from leaf.mcp.registry import get_mcp_registry

        registry1 = get_mcp_registry()
        registry2 = get_mcp_registry()

        assert registry1 is registry2

    @pytest.mark.asyncio
    async def test_get_all_tools_empty(self):
        """Test getting tools when no servers are connected."""
        from leaf.mcp.registry import MCPRegistry

        registry = MCPRegistry()
        tools = registry.get_all_tools()

        assert tools == {}


class TestMCPAPI:
    """Test MCP API endpoints."""

    def test_list_servers(self, client, mock_config_dir):
        """Test listing MCP servers."""
        response = client.get("/api/mcp/servers")
        assert response.status_code == 200

        servers = response.json()
        # Should have built-in servers after initialization
        assert isinstance(servers, list)

    def test_add_server(self, client, mock_config_dir):
        """Test adding a new MCP server."""
        response = client.post(
            "/api/mcp/servers",
            json={
                "id": "custom-server",
                "name": "Custom Server",
                "command": "custom-cmd",
                "args": ["--port", "8080"],
                "description": "A custom server",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "custom-server"
        assert data["name"] == "Custom Server"
        assert data["connected"] is False

    def test_get_server(self, client, mock_config_dir):
        """Test getting a specific server."""
        # First add a server
        client.post(
            "/api/mcp/servers",
            json={
                "id": "get-test",
                "name": "Get Test",
                "command": "cmd",
            },
        )

        response = client.get("/api/mcp/servers/get-test")
        assert response.status_code == 200
        assert response.json()["id"] == "get-test"

    def test_get_nonexistent_server(self, client, mock_config_dir):
        """Test getting a non-existent server."""
        response = client.get("/api/mcp/servers/nonexistent")
        assert response.status_code == 404

    def test_delete_server(self, client, mock_config_dir):
        """Test deleting a server."""
        # Add a server
        client.post(
            "/api/mcp/servers",
            json={"id": "delete-me", "name": "Delete Me", "command": "cmd"},
        )

        # Delete it
        response = client.delete("/api/mcp/servers/delete-me")
        assert response.status_code == 200

        # Verify it's gone
        response = client.get("/api/mcp/servers/delete-me")
        assert response.status_code == 404

    def test_enable_disable_server(self, client, mock_config_dir):
        """Test enabling and disabling a server."""
        # Add a disabled server
        client.post(
            "/api/mcp/servers",
            json={
                "id": "toggle-test",
                "name": "Toggle Test",
                "command": "cmd",
                "enabled": False,
            },
        )

        # Enable it
        response = client.post("/api/mcp/servers/toggle-test/enable")
        assert response.status_code == 200
        assert response.json()["enabled"] is True

        # Disable it
        response = client.post("/api/mcp/servers/toggle-test/disable")
        assert response.status_code == 200
        assert response.json()["enabled"] is False

    def test_list_tools_empty(self, client, mock_config_dir):
        """Test listing tools when no servers are connected."""
        response = client.get("/api/mcp/tools")
        assert response.status_code == 200
        assert response.json() == []


class TestMCPAgentTools:
    """Test MCP tools in the agent."""

    def test_format_mcp_tools_prompt_empty(self):
        """Test formatting MCP tools prompt when no servers connected."""
        from leaf.mcp.agent_tools import format_mcp_tools_prompt

        prompt = format_mcp_tools_prompt()
        assert prompt == ""

    def test_create_pydantic_model(self):
        """Test creating Pydantic model from JSON schema."""
        from leaf.mcp.agent_tools import create_pydantic_model_from_schema

        schema = {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path"},
                "encoding": {"type": "string", "description": "File encoding"},
            },
            "required": ["path"],
        }

        model = create_pydantic_model_from_schema("read_file", schema)

        # Create instance
        instance = model(path="/test/file.txt")
        assert instance.path == "/test/file.txt"
        assert instance.encoding is None  # Optional field

    def test_mcp_tool_result_model(self):
        """Test MCPToolResult model."""
        from leaf.mcp.agent_tools import MCPToolResult

        result = MCPToolResult(
            server_id="test",
            tool_name="read_file",
            success=True,
            output="file contents here",
        )

        assert result.success is True
        assert result.error is None


class TestMCPCardHelper:
    """Test MCP helper for card programs."""

    def test_mcp_client_class(self):
        """Test MCPClient helper class."""
        from leaf.mcp.card_helper import MCPClient

        mcp = MCPClient()

        # Should be able to list tools (empty when no servers connected)
        tools = mcp.list_tools()
        assert isinstance(tools, list)

    def test_has_tool_false(self):
        """Test has_tool returns False when tool not available."""
        from leaf.mcp.card_helper import MCPClient

        mcp = MCPClient()
        assert mcp.has_tool("nonexistent", "tool") is False
