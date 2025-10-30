#!/usr/bin/env python3
"""
MCP tool discovery and schema conversion module.

This module handles discovering tools from MCP servers and converting
their schemas to OpenAI-compatible format for LLM tool calling.
"""

from typing import List, Dict, Any, Optional
from mcp import ClientSession
from mcp.types import Tool


class ToolDiscovery:
    """Handles tool discovery from MCP servers."""

    def __init__(self, session: ClientSession):
        """Initialize tool discovery.

        Args:
            session: Active MCP client session
        """
        self.session = session
        self._tools_cache: Optional[List[Tool]] = None

    async def discover_tools(self, use_cache: bool = True) -> List[Tool]:
        """Discover all tools from the MCP server.

        Args:
            use_cache: Whether to use cached tools if available

        Returns:
            List of Tool objects from MCP server
        """
        if use_cache and self._tools_cache is not None:
            return self._tools_cache

        tools_result = await self.session.list_tools()
        self._tools_cache = tools_result.tools
        return self._tools_cache

    async def get_tool_by_name(self, name: str) -> Optional[Tool]:
        """Get a specific tool by name.

        Args:
            name: Tool name

        Returns:
            Tool object or None if not found
        """
        tools = await self.discover_tools()
        for tool in tools:
            if tool.name == name:
                return tool
        return None

    async def list_tool_names(self) -> List[str]:
        """Get list of all tool names.

        Returns:
            List of tool names
        """
        tools = await self.discover_tools()
        return [tool.name for tool in tools]

    def clear_cache(self) -> None:
        """Clear the tools cache."""
        self._tools_cache = None


class SchemaConverter:
    """Converts MCP tool schemas to OpenAI-compatible format."""

    @staticmethod
    def mcp_to_openai(tool: Tool) -> Dict[str, Any]:
        """Convert MCP tool schema to OpenAI function format.

        Args:
            tool: MCP Tool object

        Returns:
            Dictionary in OpenAI function calling format
        """
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or f"Tool: {tool.name}",
                "parameters": tool.inputSchema if tool.inputSchema else {
                    "type": "object",
                    "properties": {}
                }
            }
        }

    @staticmethod
    def mcp_tools_to_openai(tools: List[Tool]) -> List[Dict[str, Any]]:
        """Convert multiple MCP tools to OpenAI format.

        Args:
            tools: List of MCP Tool objects

        Returns:
            List of OpenAI function definitions
        """
        return [SchemaConverter.mcp_to_openai(tool) for tool in tools]

    @staticmethod
    def openai_to_mcp_args(openai_args: str) -> Dict[str, Any]:
        """Convert OpenAI tool call arguments to MCP format.

        Args:
            openai_args: JSON string of arguments from OpenAI

        Returns:
            Dictionary of arguments for MCP
        """
        import json
        return json.loads(openai_args) if isinstance(openai_args, str) else openai_args


class ToolRegistry:
    """Registry for managing tools from multiple MCP servers."""

    def __init__(self):
        """Initialize tool registry."""
        self._tools: Dict[str, Dict[str, Any]] = {}  # {mcp_name: {tool_name: tool_data}}
        self._tool_to_mcp: Dict[str, str] = {}  # {tool_name: mcp_name}

    def register_tools(
        self,
        mcp_name: str,
        tools: List[Tool],
        prefix: Optional[str] = None
    ) -> None:
        """Register tools from an MCP server.

        Args:
            mcp_name: Name of the MCP server
            tools: List of Tool objects
            prefix: Optional prefix for tool names (e.g., 'fs_' for filesystem)
        """
        if mcp_name not in self._tools:
            self._tools[mcp_name] = {}

        for tool in tools:
            tool_name = f"{prefix}{tool.name}" if prefix else tool.name

            # Store original tool data with prefixed name
            self._tools[mcp_name][tool_name] = {
                "original_name": tool.name,
                "tool": tool,
                "openai_schema": SchemaConverter.mcp_to_openai(tool)
            }

            # Map tool name to MCP
            self._tool_to_mcp[tool_name] = mcp_name

    def get_all_tools_openai(self) -> List[Dict[str, Any]]:
        """Get all registered tools in OpenAI format.

        Returns:
            List of OpenAI function definitions
        """
        all_tools = []
        for mcp_tools in self._tools.values():
            for tool_data in mcp_tools.values():
                all_tools.append(tool_data["openai_schema"])
        return all_tools

    def get_tools_by_mcp(self, mcp_name: str) -> List[Dict[str, Any]]:
        """Get tools from a specific MCP in OpenAI format.

        Args:
            mcp_name: MCP server name

        Returns:
            List of OpenAI function definitions
        """
        if mcp_name not in self._tools:
            return []

        return [
            tool_data["openai_schema"]
            for tool_data in self._tools[mcp_name].values()
        ]

    def get_original_tool_name(self, prefixed_name: str) -> Optional[str]:
        """Get original MCP tool name from potentially prefixed name.

        Args:
            prefixed_name: Tool name (possibly with prefix)

        Returns:
            Original tool name or None
        """
        mcp_name = self._tool_to_mcp.get(prefixed_name)
        if not mcp_name or mcp_name not in self._tools:
            return None

        tool_data = self._tools[mcp_name].get(prefixed_name)
        if not tool_data:
            return None

        return tool_data["original_name"]

    def get_mcp_for_tool(self, tool_name: str) -> Optional[str]:
        """Get MCP server name for a tool.

        Args:
            tool_name: Tool name (possibly with prefix)

        Returns:
            MCP server name or None
        """
        return self._tool_to_mcp.get(tool_name)

    def list_all_tools(self) -> List[str]:
        """List all registered tool names.

        Returns:
            List of tool names
        """
        return list(self._tool_to_mcp.keys())

    def list_mcps(self) -> List[str]:
        """List all registered MCP server names.

        Returns:
            List of MCP names
        """
        return list(self._tools.keys())

    def clear(self) -> None:
        """Clear all registered tools."""
        self._tools.clear()
        self._tool_to_mcp.clear()


__all__ = [
    "ToolDiscovery",
    "SchemaConverter",
    "ToolRegistry"
]
