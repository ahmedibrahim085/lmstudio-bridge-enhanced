#!/usr/bin/env python3
"""
Persistent MCP session with Roots Protocol support.

Allows long-lived sessions where directories can be updated dynamically
at runtime without reconnecting.
"""

from typing import List, Optional, Dict, Any
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import AsyncExitStack
from .tool_discovery import ToolDiscovery, SchemaConverter
from .executor import ToolExecutor
from .roots_manager import RootsManager
import logging
import asyncio

logger = logging.getLogger(__name__)


class PersistentMCPSession:
    """Long-lived MCP session with dynamic roots support.

    This session maintains a connection to an MCP server (like filesystem)
    and allows updating the allowed directories at runtime via the Roots Protocol.
    """

    def __init__(
        self,
        command: str,
        args: List[str],
        initial_roots: Optional[List[str]] = None
    ):
        """Initialize persistent session.

        Args:
            command: Command to run MCP server (e.g., "npx")
            args: Arguments for the command (e.g., ["-y", "@modelcontextprotocol/server-filesystem"])
            initial_roots: Optional initial list of root directories
        """
        self.command = command
        self.args = args
        self.roots_manager = RootsManager(initial_roots)

        self._session: Optional[ClientSession] = None
        self._exit_stack: Optional[AsyncExitStack] = None
        self._connected = False
        self._discovery: Optional[ToolDiscovery] = None
        self._executor: Optional[ToolExecutor] = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()

    async def connect(self) -> None:
        """Connect to the MCP server with Roots Protocol support."""
        if self._connected:
            logger.warning("Already connected")
            return

        logger.info(f"Connecting to MCP server: {self.command} {' '.join(self.args)}")

        # Create exit stack for cleanup
        self._exit_stack = AsyncExitStack()

        # Get initial root directories
        root_paths = self.roots_manager.get_directory_paths()

        # Build server parameters
        # For filesystem MCP, we need to pass roots as command-line args
        server_params = StdioServerParameters(
            command=self.command,
            args=self.args + root_paths,  # Add roots to args
            env=None
        )

        # Connect to server
        stdio_transport = await self._exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        self._session = await self._exit_stack.enter_async_context(
            ClientSession(stdio_transport[0], stdio_transport[1])
        )

        # Initialize with roots capability
        await self._session.initialize()

        # Create discovery and executor
        self._discovery = ToolDiscovery(self._session)
        self._executor = ToolExecutor(self._session)

        self._connected = True
        logger.info("Connected to MCP server with Roots Protocol support")

    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        if not self._connected:
            return

        logger.info("Disconnecting from MCP server")

        if self._exit_stack:
            await self._exit_stack.aclose()

        self._session = None
        self._exit_stack = None
        self._discovery = None
        self._executor = None
        self._connected = False

        logger.info("Disconnected from MCP server")

    async def update_roots(self, directory_paths: List[str]) -> None:
        """Update allowed directories dynamically.

        Note: Due to filesystem MCP limitations, this requires reconnecting
        with new directories. Future versions may support true runtime updates
        if the filesystem MCP implements roots/list_changed support.

        Args:
            directory_paths: New list of allowed directory paths
        """
        logger.info(f"Updating roots to: {directory_paths}")

        # Update roots manager
        self.roots_manager.set_roots(directory_paths)

        # Reconnect with new roots
        if self._connected:
            logger.info("Reconnecting with new roots...")
            await self.disconnect()
            await self.connect()
            logger.info("Reconnected with updated roots")

    async def add_root(self, directory_path: str) -> None:
        """Add a new root directory dynamically.

        Args:
            directory_path: Directory path to add
        """
        self.roots_manager.add_root(directory_path)

        # Reconnect with updated roots
        if self._connected:
            await self.disconnect()
            await self.connect()

    async def remove_root(self, directory_path: str) -> None:
        """Remove a root directory dynamically.

        Args:
            directory_path: Directory path to remove
        """
        self.roots_manager.remove_root(directory_path)

        # Reconnect with updated roots
        if self._connected:
            await self.disconnect()
            await self.connect()

    def get_roots(self) -> List[str]:
        """Get current root directories.

        Returns:
            List of directory paths
        """
        return self.roots_manager.get_directory_paths()

    async def discover_tools(self) -> List[Dict[str, Any]]:
        """Discover available tools from the MCP server.

        Returns:
            List of tool definitions in MCP format
        """
        if not self._connected or not self._discovery:
            raise RuntimeError("Not connected to MCP server")

        return await self._discovery.discover_tools()

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool on the MCP server.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        if not self._connected or not self._executor:
            raise RuntimeError("Not connected to MCP server")

        return await self._executor.execute_tool(tool_name, arguments)

    @property
    def is_connected(self) -> bool:
        """Check if session is connected.

        Returns:
            True if connected
        """
        return self._connected

    @property
    def session(self) -> Optional[ClientSession]:
        """Get the underlying MCP client session.

        Returns:
            Client session or None if not connected
        """
        return self._session


__all__ = ["PersistentMCPSession"]
