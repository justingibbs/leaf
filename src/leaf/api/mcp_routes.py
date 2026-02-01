"""API routes for MCP server management."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from leaf.mcp import (
    MCPServerConfig,
    add_mcp_server,
    disable_mcp_server,
    enable_mcp_server,
    get_mcp_server,
    initialize_builtin_servers,
    list_mcp_servers,
    remove_mcp_server,
)
from leaf.mcp.registry import get_mcp_registry

router = APIRouter(prefix="/api/mcp", tags=["mcp"])


class MCPServerCreate(BaseModel):
    """Request to create/add an MCP server."""

    id: str = Field(description="Unique identifier")
    name: str = Field(description="Human-readable name")
    command: str = Field(description="Command to run the server")
    args: list[str] = Field(default_factory=list, description="Command arguments")
    env: dict[str, str] = Field(default_factory=dict, description="Environment variables")
    enabled: bool = Field(default=True)
    description: str | None = None


class MCPServerResponse(BaseModel):
    """Response model for an MCP server."""

    id: str
    name: str
    command: str
    args: list[str]
    env: dict[str, str]
    enabled: bool
    description: str | None
    connected: bool = False


class MCPToolResponse(BaseModel):
    """Response model for an MCP tool."""

    server_id: str
    name: str
    description: str | None
    parameters: dict[str, Any]


class MCPToolCallRequest(BaseModel):
    """Request to call an MCP tool."""

    server_id: str
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class MCPToolCallResponse(BaseModel):
    """Response from an MCP tool call."""

    success: bool
    output: str
    error: str | None = None


@router.get("/servers")
async def list_servers() -> list[MCPServerResponse]:
    """List all configured MCP servers."""
    # Initialize built-in servers on first access
    initialize_builtin_servers()

    servers = list_mcp_servers()
    registry = get_mcp_registry()

    return [
        MCPServerResponse(
            id=s.id,
            name=s.name,
            command=s.command,
            args=s.args,
            env=s.env,
            enabled=s.enabled,
            description=s.description,
            connected=s.id in registry.connected_servers,
        )
        for s in servers
    ]


@router.get("/servers/{server_id}")
async def get_server(server_id: str) -> MCPServerResponse:
    """Get a specific MCP server configuration."""
    server = get_mcp_server(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    registry = get_mcp_registry()

    return MCPServerResponse(
        id=server.id,
        name=server.name,
        command=server.command,
        args=server.args,
        env=server.env,
        enabled=server.enabled,
        description=server.description,
        connected=server.id in registry.connected_servers,
    )


@router.post("/servers")
async def create_server(data: MCPServerCreate) -> MCPServerResponse:
    """Add a new MCP server configuration."""
    server = MCPServerConfig(
        id=data.id,
        name=data.name,
        command=data.command,
        args=data.args,
        env=data.env,
        enabled=data.enabled,
        description=data.description,
    )

    add_mcp_server(server)

    return MCPServerResponse(
        id=server.id,
        name=server.name,
        command=server.command,
        args=server.args,
        env=server.env,
        enabled=server.enabled,
        description=server.description,
        connected=False,
    )


@router.delete("/servers/{server_id}")
async def delete_server(server_id: str) -> dict[str, str]:
    """Remove an MCP server configuration."""
    server = get_mcp_server(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    # Disconnect if connected
    registry = get_mcp_registry()
    if server_id in registry.connected_servers:
        await registry.disconnect_server(server_id)

    remove_mcp_server(server_id)

    return {"status": "deleted"}


@router.post("/servers/{server_id}/enable")
async def enable_server(server_id: str) -> MCPServerResponse:
    """Enable an MCP server."""
    server = enable_mcp_server(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    registry = get_mcp_registry()

    return MCPServerResponse(
        id=server.id,
        name=server.name,
        command=server.command,
        args=server.args,
        env=server.env,
        enabled=server.enabled,
        description=server.description,
        connected=server.id in registry.connected_servers,
    )


@router.post("/servers/{server_id}/disable")
async def disable_server(server_id: str) -> MCPServerResponse:
    """Disable an MCP server."""
    server = disable_mcp_server(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    # Disconnect if connected
    registry = get_mcp_registry()
    if server_id in registry.connected_servers:
        await registry.disconnect_server(server_id)

    return MCPServerResponse(
        id=server.id,
        name=server.name,
        command=server.command,
        args=server.args,
        env=server.env,
        enabled=server.enabled,
        description=server.description,
        connected=False,
    )


@router.post("/servers/{server_id}/connect")
async def connect_server(server_id: str) -> MCPServerResponse:
    """Connect to an MCP server."""
    server = get_mcp_server(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    if not server.enabled:
        raise HTTPException(status_code=400, detail="Server is disabled")

    registry = get_mcp_registry()
    try:
        await registry.connect_server(server)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect: {e}")

    return MCPServerResponse(
        id=server.id,
        name=server.name,
        command=server.command,
        args=server.args,
        env=server.env,
        enabled=server.enabled,
        description=server.description,
        connected=True,
    )


@router.post("/servers/{server_id}/disconnect")
async def disconnect_server(server_id: str) -> MCPServerResponse:
    """Disconnect from an MCP server."""
    server = get_mcp_server(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    registry = get_mcp_registry()
    await registry.disconnect_server(server_id)

    return MCPServerResponse(
        id=server.id,
        name=server.name,
        command=server.command,
        args=server.args,
        env=server.env,
        enabled=server.enabled,
        description=server.description,
        connected=False,
    )


@router.get("/tools")
async def list_tools() -> list[MCPToolResponse]:
    """List all available MCP tools from connected servers."""
    registry = get_mcp_registry()
    all_tools = registry.get_all_tools()

    result = []
    for server_id, tools in all_tools.items():
        for tool in tools:
            result.append(
                MCPToolResponse(
                    server_id=server_id,
                    name=tool.name,
                    description=tool.description,
                    parameters=tool.inputSchema.properties,
                )
            )

    return result


@router.post("/tools/call")
async def call_tool(request: MCPToolCallRequest) -> MCPToolCallResponse:
    """Call an MCP tool."""
    registry = get_mcp_registry()

    if request.server_id not in registry.connected_servers:
        raise HTTPException(
            status_code=400, detail=f"Server not connected: {request.server_id}"
        )

    try:
        result = await registry.call_tool(
            request.server_id, request.tool_name, request.arguments
        )
        return MCPToolCallResponse(
            success=result.get("success", True),
            output=result.get("output", ""),
        )
    except Exception as e:
        return MCPToolCallResponse(
            success=False,
            output="",
            error=str(e),
        )


@router.post("/connect-all")
async def connect_all_servers() -> dict[str, list[str]]:
    """Connect to all enabled MCP servers."""
    registry = get_mcp_registry()
    connected = await registry.connect_enabled_servers()
    return {"connected": connected}


@router.post("/disconnect-all")
async def disconnect_all_servers() -> dict[str, str]:
    """Disconnect from all MCP servers."""
    registry = get_mcp_registry()
    await registry.disconnect_all()
    return {"status": "disconnected"}
