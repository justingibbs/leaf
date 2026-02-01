"""MCP tools integration for PydanticAI agent.

Dynamically creates PydanticAI tool functions from MCP tool definitions.
"""

import json
from typing import Any, Callable

from pydantic import BaseModel, Field, create_model

from .protocol import MCPTool
from .registry import call_mcp_tool, get_all_mcp_tools, get_mcp_registry


class MCPToolResult(BaseModel):
    """Result from calling an MCP tool."""

    server_id: str = Field(description="The MCP server that handled the call")
    tool_name: str = Field(description="The tool that was called")
    success: bool = Field(description="Whether the call succeeded")
    output: str = Field(description="Tool output text")
    error: str | None = Field(default=None, description="Error message if failed")


def create_pydantic_model_from_schema(
    tool_name: str, schema: dict[str, Any]
) -> type[BaseModel]:
    """Create a Pydantic model from a JSON schema.

    Args:
        tool_name: Name of the tool (used for model name)
        schema: JSON schema for the tool input

    Returns:
        Dynamically created Pydantic model
    """
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))

    field_definitions = {}

    for prop_name, prop_schema in properties.items():
        prop_type = prop_schema.get("type", "string")
        prop_desc = prop_schema.get("description", "")

        # Map JSON schema types to Python types
        type_map = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        python_type = type_map.get(prop_type, Any)

        # Handle optional fields
        if prop_name in required:
            field_definitions[prop_name] = (python_type, Field(description=prop_desc))
        else:
            field_definitions[prop_name] = (
                python_type | None,
                Field(default=None, description=prop_desc),
            )

    # Create the model
    model_name = f"MCP_{tool_name.replace('-', '_').replace('.', '_')}_Input"
    return create_model(model_name, **field_definitions)


def create_mcp_tool_function(
    server_id: str, tool: MCPTool
) -> tuple[Callable, type[BaseModel] | None]:
    """Create a callable function for an MCP tool.

    Args:
        server_id: Server ID that provides this tool
        tool: MCP tool definition

    Returns:
        Tuple of (async function, input model class)
    """
    # Create input model from schema
    input_model = None
    if tool.inputSchema.properties:
        input_model = create_pydantic_model_from_schema(
            tool.name, tool.inputSchema.model_dump()
        )

    async def tool_function(**kwargs: Any) -> MCPToolResult:
        """Call the MCP tool."""
        try:
            result = await call_mcp_tool(server_id, tool.name, kwargs)
            return MCPToolResult(
                server_id=server_id,
                tool_name=tool.name,
                success=result.get("success", True),
                output=result.get("output", ""),
            )
        except Exception as e:
            return MCPToolResult(
                server_id=server_id,
                tool_name=tool.name,
                success=False,
                output="",
                error=str(e),
            )

    # Set function metadata
    tool_function.__name__ = f"mcp_{server_id}_{tool.name}".replace("-", "_").replace(".", "_")
    tool_function.__doc__ = tool.description or f"MCP tool: {tool.name}"

    return tool_function, input_model


def get_mcp_tools_for_agent() -> list[dict[str, Any]]:
    """Get all MCP tools formatted for PydanticAI agent.

    Returns:
        List of tool definitions with function, name, and description
    """
    all_tools = get_all_mcp_tools()
    agent_tools = []

    for server_id, tools in all_tools.items():
        for tool in tools:
            func, input_model = create_mcp_tool_function(server_id, tool)

            tool_def = {
                "function": func,
                "name": f"mcp_{server_id}_{tool.name}".replace("-", "_").replace(".", "_"),
                "description": f"[MCP:{server_id}] {tool.description or tool.name}",
                "server_id": server_id,
                "tool_name": tool.name,
                "input_model": input_model,
            }
            agent_tools.append(tool_def)

    return agent_tools


async def call_mcp_tool_by_name(
    qualified_name: str, arguments: dict[str, Any]
) -> MCPToolResult:
    """Call an MCP tool by its qualified name.

    Args:
        qualified_name: Tool name in format "mcp_{server_id}_{tool_name}"
        arguments: Tool arguments

    Returns:
        Tool result
    """
    # Parse the qualified name
    parts = qualified_name.split("_", 2)
    if len(parts) < 3 or parts[0] != "mcp":
        return MCPToolResult(
            server_id="unknown",
            tool_name=qualified_name,
            success=False,
            output="",
            error=f"Invalid MCP tool name format: {qualified_name}",
        )

    server_id = parts[1]
    tool_name = parts[2].replace("_", "-")  # Restore original tool name format

    # Find the actual tool name (may have different separator)
    registry = get_mcp_registry()
    client = registry.get_client(server_id)
    if client:
        for tool in client.tools:
            normalized = tool.name.replace("-", "_").replace(".", "_")
            if normalized == parts[2]:
                tool_name = tool.name
                break

    try:
        result = await call_mcp_tool(server_id, tool_name, arguments)
        return MCPToolResult(
            server_id=server_id,
            tool_name=tool_name,
            success=result.get("success", True),
            output=result.get("output", ""),
        )
    except Exception as e:
        return MCPToolResult(
            server_id=server_id,
            tool_name=tool_name,
            success=False,
            output="",
            error=str(e),
        )


def format_mcp_tools_prompt() -> str:
    """Format MCP tools information for the agent system prompt.

    Returns:
        String describing available MCP tools
    """
    all_tools = get_all_mcp_tools()

    if not all_tools:
        return ""

    lines = ["\n## Available MCP Tools\n"]

    for server_id, tools in all_tools.items():
        if tools:
            lines.append(f"\n### {server_id}\n")
            for tool in tools:
                lines.append(f"- **{tool.name}**: {tool.description or 'No description'}")

                # List parameters
                if tool.inputSchema.properties:
                    lines.append("  Parameters:")
                    for prop, schema in tool.inputSchema.properties.items():
                        required = prop in tool.inputSchema.required
                        req_marker = " (required)" if required else ""
                        desc = schema.get("description", "")
                        lines.append(f"    - `{prop}`{req_marker}: {desc}")

    return "\n".join(lines)
