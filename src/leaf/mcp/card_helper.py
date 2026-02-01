"""MCP helper for card programs.

Provides a simple interface for card programs to use MCP tools.
This module is designed to be imported by generated card programs.
"""

import asyncio
import json
import os
from typing import Any


def get_available_tools() -> list[dict[str, Any]]:
    """Get list of available MCP tools.

    Returns:
        List of tool info dicts with 'server_id', 'name', 'description'
    """
    # Import here to avoid circular imports
    from leaf.mcp.registry import get_mcp_registry

    registry = get_mcp_registry()
    tools_by_server = registry.get_all_tools()

    result = []
    for server_id, tools in tools_by_server.items():
        for tool in tools:
            result.append(
                {
                    "server_id": server_id,
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema.properties,
                }
            )

    return result


def call_tool(server_id: str, tool_name: str, **kwargs: Any) -> dict[str, Any]:
    """Call an MCP tool synchronously.

    This is a blocking call suitable for use in card programs.

    Args:
        server_id: MCP server ID
        tool_name: Tool name
        **kwargs: Tool arguments

    Returns:
        Dict with 'success', 'output', and optionally 'error'

    Example:
        result = call_tool("filesystem", "read_file", path="/tmp/data.txt")
        if result["success"]:
            print(result["output"])
    """
    from leaf.mcp.registry import call_mcp_tool

    async def _call():
        return await call_mcp_tool(server_id, tool_name, kwargs)

    try:
        # Get or create event loop
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(_call())
            return result

        # If we're already in an async context, run in a new thread
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, _call())
            return future.result(timeout=30)

    except Exception as e:
        return {
            "success": False,
            "output": "",
            "error": str(e),
        }


async def call_tool_async(
    server_id: str, tool_name: str, **kwargs: Any
) -> dict[str, Any]:
    """Call an MCP tool asynchronously.

    Args:
        server_id: MCP server ID
        tool_name: Tool name
        **kwargs: Tool arguments

    Returns:
        Dict with 'success', 'output', and optionally 'error'

    Example:
        result = await call_tool_async("fetch", "fetch", url="https://example.com")
    """
    from leaf.mcp.registry import call_mcp_tool

    try:
        return await call_mcp_tool(server_id, tool_name, kwargs)
    except Exception as e:
        return {
            "success": False,
            "output": "",
            "error": str(e),
        }


class MCPClient:
    """Simple MCP client for card programs.

    Provides a convenient interface for calling MCP tools.

    Example:
        mcp = MCPClient()

        # List available tools
        for tool in mcp.list_tools():
            print(f"{tool['server_id']}/{tool['name']}: {tool['description']}")

        # Call a tool
        result = mcp.call("filesystem", "read_file", path="./data.txt")
        if result["success"]:
            print(result["output"])
    """

    def list_tools(self) -> list[dict[str, Any]]:
        """List all available MCP tools.

        Returns:
            List of tool info dicts
        """
        return get_available_tools()

    def call(self, server_id: str, tool_name: str, **kwargs: Any) -> dict[str, Any]:
        """Call an MCP tool.

        Args:
            server_id: MCP server ID
            tool_name: Tool name
            **kwargs: Tool arguments

        Returns:
            Tool result dict
        """
        return call_tool(server_id, tool_name, **kwargs)

    async def call_async(
        self, server_id: str, tool_name: str, **kwargs: Any
    ) -> dict[str, Any]:
        """Call an MCP tool asynchronously.

        Args:
            server_id: MCP server ID
            tool_name: Tool name
            **kwargs: Tool arguments

        Returns:
            Tool result dict
        """
        return await call_tool_async(server_id, tool_name, **kwargs)

    def has_tool(self, server_id: str, tool_name: str) -> bool:
        """Check if a tool is available.

        Args:
            server_id: MCP server ID
            tool_name: Tool name

        Returns:
            True if the tool is available
        """
        tools = self.list_tools()
        return any(
            t["server_id"] == server_id and t["name"] == tool_name for t in tools
        )
