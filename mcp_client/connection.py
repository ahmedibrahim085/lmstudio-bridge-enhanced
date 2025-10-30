#!/usr/bin/env python3
"""
MCP client connection management module.

This module handles connecting to and managing sessions with MCP servers.
"""

import asyncio
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters


class MCPConnection:
    """Manages connection to an MCP server via stdio."""

    def __init__(
        self,
        command: str,
        args: List[str],
        env: Optional[Dict[str, str]] = None
    ):
        """Initialize MCP connection parameters.

        Args:
            command: Command to spawn MCP server (e.g., 'npx', 'uvx', 'docker')
            args: Arguments for the command
            env: Optional environment variables for the server process
        """
        self.command = command
        self.args = args
        self.env = env or {}
        self.server_params = StdioServerParameters(
            command=command,
            args=args,
            env=env
        )
        self.session: Optional[ClientSession] = None
        self._server_info: Optional[Dict[str, Any]] = None

    @asynccontextmanager
    async def connect(self):
        """Connect to MCP server and yield session.

        Yields:
            ClientSession: Active MCP session

        Example:
            async with connection.connect() as session:
                tools = await session.list_tools()
        """
        async with stdio_client(self.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize session
                init_result = await session.initialize()
                self._server_info = {
                    "name": init_result.serverInfo.name,
                    "version": init_result.serverInfo.version,
                    "capabilities": init_result.capabilities
                }
                self.session = session

                try:
                    yield session
                finally:
                    self.session = None

    @property
    def server_info(self) -> Optional[Dict[str, Any]]:
        """Get server information from last connection.

        Returns:
            Dictionary with server name, version, capabilities
        """
        return self._server_info

    @property
    def is_connected(self) -> bool:
        """Check if currently connected.

        Returns:
            True if session is active
        """
        return self.session is not None


class MCPConnectionManager:
    """Manages multiple MCP connections."""

    def __init__(self):
        """Initialize connection manager."""
        self._connections: Dict[str, MCPConnection] = {}
        self._active_sessions: Dict[str, ClientSession] = {}

    def add_connection(
        self,
        name: str,
        command: str,
        args: List[str],
        env: Optional[Dict[str, str]] = None
    ) -> MCPConnection:
        """Add a new MCP connection configuration.

        Args:
            name: Unique name for this connection
            command: Command to spawn MCP server
            args: Arguments for the command
            env: Optional environment variables

        Returns:
            MCPConnection instance
        """
        connection = MCPConnection(command, args, env)
        self._connections[name] = connection
        return connection

    def get_connection(self, name: str) -> Optional[MCPConnection]:
        """Get connection by name.

        Args:
            name: Connection name

        Returns:
            MCPConnection instance or None if not found
        """
        return self._connections.get(name)

    def list_connections(self) -> List[str]:
        """List all configured connection names.

        Returns:
            List of connection names
        """
        return list(self._connections.keys())

    def remove_connection(self, name: str) -> bool:
        """Remove a connection configuration.

        Args:
            name: Connection name

        Returns:
            True if removed, False if not found
        """
        if name in self._connections:
            del self._connections[name]
            return True
        return False

    @asynccontextmanager
    async def connect(self, name: str):
        """Connect to a configured MCP server.

        Args:
            name: Connection name

        Yields:
            ClientSession: Active MCP session

        Raises:
            KeyError: If connection name not found
        """
        if name not in self._connections:
            raise KeyError(f"Connection '{name}' not found")

        connection = self._connections[name]
        async with connection.connect() as session:
            self._active_sessions[name] = session
            try:
                yield session
            finally:
                if name in self._active_sessions:
                    del self._active_sessions[name]

    def is_connected(self, name: str) -> bool:
        """Check if a connection is currently active.

        Args:
            name: Connection name

        Returns:
            True if connected
        """
        return name in self._active_sessions


__all__ = [
    "MCPConnection",
    "MCPConnectionManager"
]
