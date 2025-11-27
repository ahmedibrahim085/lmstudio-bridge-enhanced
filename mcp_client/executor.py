#!/usr/bin/env python3
"""
MCP tool execution module.

This module handles executing tools on MCP servers and managing
tool call results.
"""

from typing import Dict, Any, Optional, List
from mcp import ClientSession
from mcp.types import CallToolResult, TextContent, ImageContent, EmbeddedResource

from .type_coercion import safe_call_tool


class ToolExecutor:
    """Executes tools on MCP servers."""

    def __init__(self, session: ClientSession):
        """Initialize tool executor.

        Args:
            session: Active MCP client session
        """
        self.session = session

    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> CallToolResult:
        """Execute a tool on the MCP server.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments as dictionary

        Returns:
            CallToolResult from MCP server

        Raises:
            Exception: If tool execution fails
        """
        # Use safe_call_tool wrapper - handles type coercion automatically
        return await safe_call_tool(self.session, tool_name, arguments)

    @staticmethod
    def extract_text_content(result: CallToolResult) -> str:
        """Extract text content from tool result.

        Args:
            result: CallToolResult from MCP

        Returns:
            Extracted text content
        """
        if not result.content:
            return "No content returned"

        text_parts = []
        for content_item in result.content:
            if isinstance(content_item, TextContent):
                text_parts.append(content_item.text)
            elif isinstance(content_item, ImageContent):
                text_parts.append(f"[Image: {content_item.mimeType}]")
            elif isinstance(content_item, EmbeddedResource):
                text_parts.append(f"[Resource: {content_item.resource}]")
            else:
                text_parts.append(f"[Unknown content type]")

        return "\n".join(text_parts)

    @staticmethod
    def format_tool_result(result: CallToolResult) -> Dict[str, Any]:
        """Format tool result for LLM consumption.

        Args:
            result: CallToolResult from MCP

        Returns:
            Formatted dictionary with content and metadata
        """
        return {
            "content": ToolExecutor.extract_text_content(result),
            "is_error": result.isError if hasattr(result, 'isError') else False,
            "raw_content": result.content
        }


class BatchToolExecutor:
    """Handles batch execution of multiple tools."""

    def __init__(self, session: ClientSession):
        """Initialize batch executor.

        Args:
            session: Active MCP client session
        """
        self.executor = ToolExecutor(session)

    async def execute_multiple(
        self,
        tool_calls: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Execute multiple tools in sequence.

        Args:
            tool_calls: List of tool calls with 'name' and 'arguments'

        Returns:
            List of formatted results
        """
        results = []

        for tool_call in tool_calls:
            try:
                tool_name = tool_call.get("name")
                arguments = tool_call.get("arguments", {})

                result = await self.executor.execute_tool(tool_name, arguments)
                formatted = ToolExecutor.format_tool_result(result)

                results.append({
                    "tool_name": tool_name,
                    "success": True,
                    "result": formatted
                })

            except Exception as e:
                results.append({
                    "tool_name": tool_call.get("name", "unknown"),
                    "success": False,
                    "error": str(e)
                })

        return results

    async def execute_parallel(
        self,
        tool_calls: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Execute multiple tools in parallel.

        Args:
            tool_calls: List of tool calls with 'name' and 'arguments'

        Returns:
            List of formatted results
        """
        import asyncio

        async def execute_single(tool_call: Dict[str, Any]) -> Dict[str, Any]:
            try:
                tool_name = tool_call.get("name")
                arguments = tool_call.get("arguments", {})

                result = await self.executor.execute_tool(tool_name, arguments)
                formatted = ToolExecutor.format_tool_result(result)

                return {
                    "tool_name": tool_name,
                    "success": True,
                    "result": formatted
                }

            except Exception as e:
                return {
                    "tool_name": tool_call.get("name", "unknown"),
                    "success": False,
                    "error": str(e)
                }

        # Execute all tools concurrently
        results = await asyncio.gather(
            *[execute_single(tc) for tc in tool_calls],
            return_exceptions=True
        )

        # Handle any exceptions from gather
        formatted_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                formatted_results.append({
                    "tool_name": tool_calls[i].get("name", "unknown"),
                    "success": False,
                    "error": str(result)
                })
            else:
                formatted_results.append(result)

        return formatted_results


__all__ = [
    "ToolExecutor",
    "BatchToolExecutor"
]
