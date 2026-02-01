"""MCP server configuration management.

Manages global MCP server configurations stored in the app config directory.
"""

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from leaf.core.config import get_config_dir


class MCPServerConfig(BaseModel):
    """Configuration for a single MCP server."""

    id: str = Field(description="Unique identifier for this server")
    name: str = Field(description="Human-readable name")
    command: str = Field(description="Command to run the server")
    args: list[str] = Field(default_factory=list, description="Command arguments")
    env: dict[str, str] = Field(default_factory=dict, description="Environment variables")
    enabled: bool = Field(default=True, description="Whether the server is enabled")
    description: str | None = Field(default=None, description="Server description")


class MCPConfig(BaseModel):
    """Global MCP configuration."""

    servers: dict[str, MCPServerConfig] = Field(
        default_factory=dict, description="Configured MCP servers by ID"
    )


def get_mcp_config_path() -> Path:
    """Get the path to the MCP configuration file."""
    return get_config_dir() / "mcp.json"


def load_mcp_config() -> MCPConfig:
    """Load the global MCP configuration.

    Returns:
        MCPConfig with all configured servers
    """
    config_path = get_mcp_config_path()

    if not config_path.exists():
        return MCPConfig()

    try:
        data = json.loads(config_path.read_text())
        return MCPConfig(**data)
    except Exception:
        return MCPConfig()


def save_mcp_config(config: MCPConfig) -> None:
    """Save the global MCP configuration.

    Args:
        config: Configuration to save
    """
    config_path = get_mcp_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(config.model_dump_json(indent=2))


def add_mcp_server(server: MCPServerConfig) -> MCPConfig:
    """Add or update an MCP server configuration.

    Args:
        server: Server configuration

    Returns:
        Updated configuration
    """
    config = load_mcp_config()
    config.servers[server.id] = server
    save_mcp_config(config)
    return config


def remove_mcp_server(server_id: str) -> MCPConfig:
    """Remove an MCP server configuration.

    Args:
        server_id: Server ID to remove

    Returns:
        Updated configuration
    """
    config = load_mcp_config()
    config.servers.pop(server_id, None)
    save_mcp_config(config)
    return config


def get_mcp_server(server_id: str) -> MCPServerConfig | None:
    """Get a specific MCP server configuration.

    Args:
        server_id: Server ID

    Returns:
        Server configuration or None if not found
    """
    config = load_mcp_config()
    return config.servers.get(server_id)


def list_mcp_servers(enabled_only: bool = False) -> list[MCPServerConfig]:
    """List all configured MCP servers.

    Args:
        enabled_only: If True, only return enabled servers

    Returns:
        List of server configurations
    """
    config = load_mcp_config()
    servers = list(config.servers.values())

    if enabled_only:
        servers = [s for s in servers if s.enabled]

    return servers


def get_builtin_servers() -> list[MCPServerConfig]:
    """Get built-in MCP server configurations.

    These are pre-configured servers that ship with LEAF.
    Users can enable/disable them but the base config is provided.

    Returns:
        List of built-in server configurations
    """
    return [
        MCPServerConfig(
            id="filesystem",
            name="Filesystem",
            command="npx",
            args=["-y", "@anthropic/mcp-server-filesystem", "."],
            description="Read and write files in the current directory",
            enabled=False,  # Disabled by default for security
        ),
        MCPServerConfig(
            id="fetch",
            name="Web Fetch",
            command="npx",
            args=["-y", "@anthropic/mcp-server-fetch"],
            description="Fetch content from URLs",
            enabled=False,
        ),
        MCPServerConfig(
            id="memory",
            name="Memory",
            command="npx",
            args=["-y", "@anthropic/mcp-server-memory"],
            description="Persistent memory storage",
            enabled=False,
        ),
    ]


def initialize_builtin_servers() -> None:
    """Initialize built-in servers in the config if not present."""
    config = load_mcp_config()
    builtins = get_builtin_servers()

    for server in builtins:
        if server.id not in config.servers:
            config.servers[server.id] = server

    save_mcp_config(config)


def enable_mcp_server(server_id: str) -> MCPServerConfig | None:
    """Enable an MCP server.

    Args:
        server_id: Server ID

    Returns:
        Updated server config or None if not found
    """
    config = load_mcp_config()
    server = config.servers.get(server_id)
    if server:
        server.enabled = True
        save_mcp_config(config)
    return server


def disable_mcp_server(server_id: str) -> MCPServerConfig | None:
    """Disable an MCP server.

    Args:
        server_id: Server ID

    Returns:
        Updated server config or None if not found
    """
    config = load_mcp_config()
    server = config.servers.get(server_id)
    if server:
        server.enabled = False
        save_mcp_config(config)
    return server
