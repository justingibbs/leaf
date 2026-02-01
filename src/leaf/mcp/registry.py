"""MCP server registry.

Manages active connections to MCP servers and provides access to their tools.
"""

import asyncio
import logging
from typing import Any

from .client import MCPClient, MCPClientError
from .config import MCPServerConfig, list_mcp_servers
from .protocol import MCPTool

logger = logging.getLogger(__name__)


class MCPRegistry:
    """Registry of active MCP server connections."""

    _instance: "MCPRegistry | None" = None

    def __init__(self) -> None:
        """Initialize the registry."""
        self._clients: dict[str, MCPClient] = {}
        self._lock = asyncio.Lock()

    @classmethod
    def get_instance(cls) -> "MCPRegistry":
        """Get the singleton registry instance."""
        if cls._instance is None:
            cls._instance = MCPRegistry()
        return cls._instance

    @property
    def connected_servers(self) -> list[str]:
        """Get list of connected server IDs."""
        return [sid for sid, client in self._clients.items() if client.is_connected]

    async def connect_server(self, config: MCPServerConfig) -> MCPClient:
        """Connect to an MCP server.

        Args:
            config: Server configuration

        Returns:
            Connected MCP client
        """
        async with self._lock:
            # Check if already connected
            existing = self._clients.get(config.id)
            if existing and existing.is_connected:
                return existing

            # Create new client
            client = MCPClient(
                server_id=config.id,
                command=config.command,
                args=config.args,
                env=config.env if config.env else None,
            )

            await client.connect()
            self._clients[config.id] = client

            logger.info(f"Connected to MCP server: {config.name} ({config.id})")
            return client

    async def disconnect_server(self, server_id: str) -> None:
        """Disconnect from an MCP server.

        Args:
            server_id: Server ID
        """
        async with self._lock:
            client = self._clients.pop(server_id, None)
            if client:
                await client.disconnect()
                logger.info(f"Disconnected from MCP server: {server_id}")

    async def disconnect_all(self) -> None:
        """Disconnect from all MCP servers."""
        async with self._lock:
            for server_id, client in list(self._clients.items()):
                try:
                    await client.disconnect()
                    logger.info(f"Disconnected from MCP server: {server_id}")
                except Exception as e:
                    logger.warning(f"Error disconnecting from {server_id}: {e}")
            self._clients.clear()

    def get_client(self, server_id: str) -> MCPClient | None:
        """Get a connected client by server ID.

        Args:
            server_id: Server ID

        Returns:
            MCP client or None if not connected
        """
        client = self._clients.get(server_id)
        if client and client.is_connected:
            return client
        return None

    async def connect_enabled_servers(self) -> list[str]:
        """Connect to all enabled MCP servers.

        Returns:
            List of successfully connected server IDs
        """
        servers = list_mcp_servers(enabled_only=True)
        connected = []

        for server in servers:
            try:
                await self.connect_server(server)
                connected.append(server.id)
            except MCPClientError as e:
                logger.warning(f"Failed to connect to MCP server {server.id}: {e}")

        return connected

    def get_all_tools(self) -> dict[str, list[MCPTool]]:
        """Get all available tools from all connected servers.

        Returns:
            Dict mapping server ID to list of tools
        """
        tools: dict[str, list[MCPTool]] = {}

        for server_id, client in self._clients.items():
            if client.is_connected:
                tools[server_id] = client.tools

        return tools

    def get_tool(self, server_id: str, tool_name: str) -> MCPTool | None:
        """Get a specific tool from a server.

        Args:
            server_id: Server ID
            tool_name: Tool name

        Returns:
            Tool definition or None if not found
        """
        client = self.get_client(server_id)
        if not client:
            return None

        for tool in client.tools:
            if tool.name == tool_name:
                return tool

        return None

    async def call_tool(
        self, server_id: str, tool_name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Call a tool on an MCP server.

        Args:
            server_id: Server ID
            tool_name: Tool name
            arguments: Tool arguments

        Returns:
            Tool result

        Raises:
            MCPClientError: If server not connected or tool call fails
        """
        client = self.get_client(server_id)
        if not client:
            raise MCPClientError(f"Server not connected: {server_id}")

        result = await client.call_tool(tool_name, arguments)

        # Convert result to simpler format
        if result.isError:
            error_msg = ""
            for content in result.content:
                if content.get("type") == "text":
                    error_msg += content.get("text", "")
            raise MCPClientError(f"Tool error: {error_msg}")

        # Extract text content
        output = []
        for content in result.content:
            if content.get("type") == "text":
                output.append(content.get("text", ""))
            elif content.get("type") == "image":
                output.append(f"[Image: {content.get('mimeType', 'unknown')}]")
            elif content.get("type") == "resource":
                output.append(f"[Resource: {content.get('uri', 'unknown')}]")

        return {
            "success": True,
            "output": "\n".join(output) if output else "",
            "raw": result.content,
        }


# Global registry instance
_registry: MCPRegistry | None = None


def get_mcp_registry() -> MCPRegistry:
    """Get the global MCP registry instance."""
    global _registry
    if _registry is None:
        _registry = MCPRegistry()
    return _registry


async def connect_mcp_servers() -> list[str]:
    """Connect to all enabled MCP servers.

    Returns:
        List of connected server IDs
    """
    registry = get_mcp_registry()
    return await registry.connect_enabled_servers()


async def disconnect_mcp_servers() -> None:
    """Disconnect from all MCP servers."""
    registry = get_mcp_registry()
    await registry.disconnect_all()


async def call_mcp_tool(
    server_id: str, tool_name: str, arguments: dict[str, Any]
) -> dict[str, Any]:
    """Call an MCP tool.

    Args:
        server_id: Server ID
        tool_name: Tool name
        arguments: Tool arguments

    Returns:
        Tool result
    """
    registry = get_mcp_registry()
    return await registry.call_tool(server_id, tool_name, arguments)


def get_all_mcp_tools() -> dict[str, list[MCPTool]]:
    """Get all available MCP tools.

    Returns:
        Dict mapping server ID to list of tools
    """
    registry = get_mcp_registry()
    return registry.get_all_tools()
