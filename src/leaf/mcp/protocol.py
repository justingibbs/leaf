"""MCP Protocol definitions.

Implements the Model Context Protocol JSON-RPC message types.
See: https://modelcontextprotocol.io/
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class JSONRPCRequest(BaseModel):
    """JSON-RPC 2.0 request message."""

    jsonrpc: Literal["2.0"] = "2.0"
    id: int | str
    method: str
    params: dict[str, Any] | None = None


class JSONRPCResponse(BaseModel):
    """JSON-RPC 2.0 response message."""

    jsonrpc: Literal["2.0"] = "2.0"
    id: int | str | None
    result: Any | None = None
    error: dict[str, Any] | None = None


class JSONRPCNotification(BaseModel):
    """JSON-RPC 2.0 notification (no id, no response expected)."""

    jsonrpc: Literal["2.0"] = "2.0"
    method: str
    params: dict[str, Any] | None = None


# MCP-specific types


class MCPCapabilities(BaseModel):
    """Server capabilities."""

    tools: dict[str, Any] | None = None
    resources: dict[str, Any] | None = None
    prompts: dict[str, Any] | None = None


class MCPServerInfo(BaseModel):
    """Server information returned during initialization."""

    name: str
    version: str


class MCPInitializeResult(BaseModel):
    """Result of initialize request."""

    protocolVersion: str
    capabilities: MCPCapabilities
    serverInfo: MCPServerInfo


class MCPToolInputSchema(BaseModel):
    """JSON Schema for tool input."""

    type: str = "object"
    properties: dict[str, Any] = Field(default_factory=dict)
    required: list[str] = Field(default_factory=list)


class MCPTool(BaseModel):
    """An MCP tool definition."""

    name: str
    description: str | None = None
    inputSchema: MCPToolInputSchema = Field(default_factory=MCPToolInputSchema)


class MCPToolsListResult(BaseModel):
    """Result of tools/list request."""

    tools: list[MCPTool]


class MCPToolCallResult(BaseModel):
    """Result of a tool call."""

    content: list[dict[str, Any]]
    isError: bool = False


class MCPResource(BaseModel):
    """An MCP resource definition."""

    uri: str
    name: str
    description: str | None = None
    mimeType: str | None = None


class MCPResourcesListResult(BaseModel):
    """Result of resources/list request."""

    resources: list[MCPResource]


class MCPResourceContent(BaseModel):
    """Content of a resource."""

    uri: str
    mimeType: str | None = None
    text: str | None = None
    blob: str | None = None  # Base64 encoded


class MCPResourceReadResult(BaseModel):
    """Result of resources/read request."""

    contents: list[MCPResourceContent]
