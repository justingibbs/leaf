"""LEAF Agent - PydanticAI-powered automation assistant.

The agent helps users create Cards through natural language conversation.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext

from leaf.cards import CardCreate, ProgramConfig, TriggerConfig, create_card
from leaf.core.config import get_default_model

from .prompts import CARD_PROPOSAL_TEMPLATE, SYSTEM_PROMPT
from .tools import (
    CardProposal,
    DirectoryListing,
    FileContent,
    list_project_directory,
    read_project_file,
    write_project_file,
)


@dataclass
class AgentContext:
    """Context passed to the agent for each request."""

    project_path: Path
    project_name: str
    pending_proposal: CardProposal | None = None


def create_leaf_agent() -> Agent[AgentContext, str]:
    """Create and configure the LEAF agent.

    Returns:
        Configured PydanticAI Agent
    """
    model = get_default_model()

    # Create agent with model (e.g., gateway/google-vertex:gemini-2.0-flash for Pydantic AI Gateway)
    agent = Agent(
        model,
        system_prompt=SYSTEM_PROMPT,
        deps_type=AgentContext,
        output_type=str,
    )

    # Register tools
    @agent.tool
    async def propose_card(ctx: RunContext[AgentContext], proposal: CardProposal) -> str:
        """Propose a new card to the user for confirmation.

        Use this when you want to create a card - describe what it will do
        and let the user confirm before creating it.

        Args:
            proposal: The card proposal with name, trigger, and code
        """
        # Store the proposal for later creation
        ctx.deps.pending_proposal = proposal

        # Generate trigger description
        trigger_desc = proposal.trigger_type
        if proposal.trigger_folder:
            trigger_desc += f" in '{proposal.trigger_folder}'"
        if proposal.trigger_pattern:
            trigger_desc += f" matching '{proposal.trigger_pattern}'"

        # Format the proposal message
        return CARD_PROPOSAL_TEMPLATE.format(
            name=proposal.name,
            trigger_description=trigger_desc,
            description=proposal.description,
            code_overview=_summarize_code(proposal.code),
        )

    @agent.tool
    async def create_card_now(ctx: RunContext[AgentContext], proposal: CardProposal) -> str:
        """Create a card immediately without proposing first.

        Use this when the user says "just do it" or explicitly asks you to create
        without confirmation. Also use this after a proposal has been accepted.

        Args:
            proposal: The card to create
        """
        try:
            # Create the card using the cards module
            card_data = CardCreate(
                name=proposal.name,
                description=proposal.description,
                user_prompt=proposal.description,
                trigger_config=TriggerConfig(
                    type=proposal.trigger_type,
                    folder=proposal.trigger_folder,
                    pattern=proposal.trigger_pattern,
                ),
                program_config=ProgramConfig(
                    language="python",
                    entrypoint="main.py",
                    dependencies=proposal.dependencies,
                ),
            )

            card = create_card(card_data)

            # Write the actual code to the program file
            program_dir = ctx.deps.project_path / card.program_path
            main_file = program_dir / "main.py"
            main_file.write_text(proposal.code)

            # Clear pending proposal
            ctx.deps.pending_proposal = None

            return f"Created card '{card.name}' (ID: {card.id}). The automation is now active!"

        except Exception as e:
            return f"Error creating card: {e}"

    @agent.tool
    async def read_file(ctx: RunContext[AgentContext], path: str) -> FileContent:
        """Read a file from the project folder.

        Args:
            path: Path relative to project root (e.g., "data/input.csv")
        """
        return read_project_file(ctx.deps.project_path, path)

    @agent.tool
    async def write_file(ctx: RunContext[AgentContext], path: str, content: str) -> str:
        """Write or update a file in the project folder.

        Args:
            path: Path relative to project root
            content: Content to write
        """
        return write_project_file(ctx.deps.project_path, path, content)

    @agent.tool
    async def list_directory(
        ctx: RunContext[AgentContext], path: str = "."
    ) -> DirectoryListing:
        """List files and folders in a directory.

        Args:
            path: Path relative to project root (default: project root)
        """
        return list_project_directory(ctx.deps.project_path, path)

    @agent.tool
    async def call_mcp_tool(
        ctx: RunContext[AgentContext],
        server_id: str,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Call an MCP tool from a connected MCP server.

        Use this to access external capabilities like web fetching,
        database queries, or other integrations.

        Args:
            server_id: The MCP server ID (e.g., "fetch", "filesystem")
            tool_name: The name of the tool to call
            arguments: Arguments to pass to the tool
        """
        from leaf.mcp.registry import get_mcp_registry

        registry = get_mcp_registry()

        if server_id not in registry.connected_servers:
            return {
                "success": False,
                "output": "",
                "error": f"MCP server '{server_id}' is not connected. "
                "Use /api/mcp/servers/{server_id}/connect to connect it first.",
            }

        try:
            result = await registry.call_tool(server_id, tool_name, arguments or {})
            return result
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": str(e),
            }

    @agent.tool
    async def list_mcp_tools(ctx: RunContext[AgentContext]) -> list[dict[str, Any]]:
        """List all available MCP tools from connected servers.

        Use this to discover what MCP tools are available before calling them.
        """
        from leaf.mcp.registry import get_mcp_registry

        registry = get_mcp_registry()
        all_tools = registry.get_all_tools()

        result = []
        for server_id, tools in all_tools.items():
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

    return agent


def _summarize_code(code: str) -> str:
    """Create a brief summary of code for display."""
    lines = code.strip().split("\n")
    if len(lines) <= 10:
        return f"```python\n{code}\n```"

    # Show first 5 and last 3 lines
    preview = "\n".join(lines[:5])
    preview += f"\n... ({len(lines) - 8} more lines) ...\n"
    preview += "\n".join(lines[-3:])
    return f"```python\n{preview}\n```"


# Global agent instance (created lazily)
_agent: Agent[AgentContext, str] | None = None


def get_agent() -> Agent[AgentContext, str]:
    """Get or create the global LEAF agent."""
    global _agent
    if _agent is None:
        _agent = create_leaf_agent()
    return _agent


async def chat(
    message: str,
    project_path: Path,
    project_name: str,
    message_history: list[dict[str, Any]] | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """Send a message to the LEAF agent and get a response.

    Args:
        message: User's message
        project_path: Path to the current project
        project_name: Name of the current project
        message_history: Previous messages in the conversation

    Returns:
        Tuple of (response text, updated message history)
    """
    agent = get_agent()
    context = AgentContext(project_path=project_path, project_name=project_name)

    # Run the agent
    result = await agent.run(
        message,
        deps=context,
        message_history=message_history,
    )

    return result.output, result.all_messages()


async def chat_stream(
    message: str,
    project_path: Path,
    project_name: str,
    message_history: list[dict[str, Any]] | None = None,
):
    """Stream a response from the LEAF agent.

    Args:
        message: User's message
        project_path: Path to the current project
        project_name: Name of the current project
        message_history: Previous messages in the conversation

    Yields:
        Chunks of the response as they're generated
    """
    agent = get_agent()
    context = AgentContext(project_path=project_path, project_name=project_name)

    async with agent.run_stream(
        message,
        deps=context,
        message_history=message_history,
    ) as result:
        async for chunk in result.stream_text():
            yield chunk
