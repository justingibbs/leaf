"""MCP stdio client.

Connects to MCP servers via stdio (stdin/stdout) communication.
"""

import asyncio
import json
import logging
from typing import Any

from .protocol import (
    JSONRPCNotification,
    JSONRPCRequest,
    JSONRPCResponse,
    MCPInitializeResult,
    MCPResourceReadResult,
    MCPResourcesListResult,
    MCPTool,
    MCPToolCallResult,
    MCPToolsListResult,
)

logger = logging.getLogger(__name__)


class MCPClientError(Exception):
    """Error from MCP client operations."""

    pass


class MCPClient:
    """Client for communicating with MCP servers over stdio."""

    def __init__(
        self,
        server_id: str,
        command: str,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        """Initialize the MCP client.

        Args:
            server_id: Unique identifier for this server
            command: Command to run the server
            args: Arguments to pass to the command
            env: Environment variables for the server process
        """
        self.server_id = server_id
        self.command = command
        self.args = args or []
        self.env = env

        self._process: asyncio.subprocess.Process | None = None
        self._request_id = 0
        self._pending_requests: dict[int, asyncio.Future] = {}
        self._reader_task: asyncio.Task | None = None
        self._initialized = False
        self._server_info: MCPInitializeResult | None = None
        self._tools: list[MCPTool] = []

    @property
    def is_connected(self) -> bool:
        """Check if the client is connected to the server."""
        return self._process is not None and self._process.returncode is None

    @property
    def tools(self) -> list[MCPTool]:
        """Get the list of available tools."""
        return self._tools

    async def connect(self) -> None:
        """Connect to the MCP server and initialize."""
        if self.is_connected:
            return

        try:
            # Start the server process
            self._process = await asyncio.create_subprocess_exec(
                self.command,
                *self.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self.env,
            )

            # Start reading responses
            self._reader_task = asyncio.create_task(self._read_responses())

            # Initialize the connection
            await self._initialize()

            # Get available tools
            await self._list_tools()

        except Exception as e:
            await self.disconnect()
            raise MCPClientError(f"Failed to connect to MCP server: {e}") from e

    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        if self._reader_task:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass
            self._reader_task = None

        if self._process:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self._process.kill()
                await self._process.wait()
            self._process = None

        self._initialized = False
        self._tools = []
        self._pending_requests.clear()

    async def _initialize(self) -> None:
        """Send initialize request to the server."""
        result = await self._send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "leaf",
                    "version": "0.1.0",
                },
            },
        )

        self._server_info = MCPInitializeResult(**result)
        self._initialized = True

        # Send initialized notification
        await self._send_notification("notifications/initialized", {})

    async def _list_tools(self) -> None:
        """Get the list of available tools from the server."""
        result = await self._send_request("tools/list", {})
        tools_result = MCPToolsListResult(**result)
        self._tools = tools_result.tools

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> MCPToolCallResult:
        """Call a tool on the MCP server.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool call result
        """
        if not self.is_connected:
            raise MCPClientError("Not connected to MCP server")

        result = await self._send_request(
            "tools/call",
            {
                "name": name,
                "arguments": arguments,
            },
        )

        return MCPToolCallResult(**result)

    async def list_resources(self) -> list:
        """List available resources."""
        if not self.is_connected:
            raise MCPClientError("Not connected to MCP server")

        result = await self._send_request("resources/list", {})
        resources_result = MCPResourcesListResult(**result)
        return resources_result.resources

    async def read_resource(self, uri: str) -> MCPResourceReadResult:
        """Read a resource by URI.

        Args:
            uri: Resource URI

        Returns:
            Resource content
        """
        if not self.is_connected:
            raise MCPClientError("Not connected to MCP server")

        result = await self._send_request(
            "resources/read",
            {"uri": uri},
        )

        return MCPResourceReadResult(**result)

    async def _send_request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Send a request and wait for response.

        Args:
            method: RPC method name
            params: Method parameters

        Returns:
            Response result
        """
        if not self._process or not self._process.stdin:
            raise MCPClientError("Not connected")

        self._request_id += 1
        request_id = self._request_id

        request = JSONRPCRequest(
            id=request_id,
            method=method,
            params=params,
        )

        # Create future for response
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending_requests[request_id] = future

        try:
            # Send request
            message = request.model_dump_json() + "\n"
            self._process.stdin.write(message.encode())
            await self._process.stdin.drain()

            # Wait for response with timeout
            result = await asyncio.wait_for(future, timeout=30.0)
            return result

        except asyncio.TimeoutError:
            self._pending_requests.pop(request_id, None)
            raise MCPClientError(f"Request timed out: {method}")

        except Exception as e:
            self._pending_requests.pop(request_id, None)
            raise MCPClientError(f"Request failed: {e}") from e

    async def _send_notification(self, method: str, params: dict[str, Any]) -> None:
        """Send a notification (no response expected).

        Args:
            method: RPC method name
            params: Method parameters
        """
        if not self._process or not self._process.stdin:
            raise MCPClientError("Not connected")

        notification = JSONRPCNotification(
            method=method,
            params=params,
        )

        message = notification.model_dump_json() + "\n"
        self._process.stdin.write(message.encode())
        await self._process.stdin.drain()

    async def _read_responses(self) -> None:
        """Read responses from the server stdout."""
        if not self._process or not self._process.stdout:
            return

        try:
            while True:
                line = await self._process.stdout.readline()
                if not line:
                    break

                try:
                    data = json.loads(line.decode())
                    response = JSONRPCResponse(**data)

                    if response.id is not None:
                        future = self._pending_requests.pop(response.id, None)
                        if future and not future.done():
                            if response.error:
                                future.set_exception(
                                    MCPClientError(
                                        f"RPC error: {response.error.get('message', 'Unknown error')}"
                                    )
                                )
                            else:
                                future.set_result(response.result)

                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from MCP server: {line}")
                except Exception as e:
                    logger.warning(f"Error processing MCP response: {e}")

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error reading from MCP server: {e}")

    async def __aenter__(self) -> "MCPClient":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.disconnect()
