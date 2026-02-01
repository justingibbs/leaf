"""MCP (Model Context Protocol) integration for LEAF.

Provides client connectivity to MCP servers, allowing the agent and
card programs to use external tools.
"""

from .client import MCPClient, MCPClientError
from .config import (
    MCPServerConfig,
    add_mcp_server,
    disable_mcp_server,
    enable_mcp_server,
    get_mcp_server,
    initialize_builtin_servers,
    list_mcp_servers,
    load_mcp_config,
    remove_mcp_server,
)
from .registry import (
    call_mcp_tool,
    connect_mcp_servers,
    disconnect_mcp_servers,
    get_all_mcp_tools,
    get_mcp_registry,
)

__all__ = [
    # Client
    "MCPClient",
    "MCPClientError",
    # Config
    "MCPServerConfig",
    "add_mcp_server",
    "disable_mcp_server",
    "enable_mcp_server",
    "get_mcp_server",
    "initialize_builtin_servers",
    "list_mcp_servers",
    "load_mcp_config",
    "remove_mcp_server",
    # Registry
    "call_mcp_tool",
    "connect_mcp_servers",
    "disconnect_mcp_servers",
    "get_all_mcp_tools",
    "get_mcp_registry",
]
