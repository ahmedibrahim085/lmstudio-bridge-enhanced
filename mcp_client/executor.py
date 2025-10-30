#!/usr/bin/env python3
"""
MCP tool execution module.

This module handles executing tools on MCP servers and managing
tool call results.
"""

from typing import Dict, Any, Optional, List
from mcp import ClientSession
from mcp.types import CallToolResult, TextContent, ImageContent, EmbeddedResource


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
        result = await self.session.call_tool(tool_name, arguments)
        return result

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


class ToolExecutionTracker:
    """Tracks tool execution history and statistics."""

    def __init__(self):
        """Initialize execution tracker."""
        self._history: List[Dict[str, Any]] = []
        self._stats: Dict[str, Dict[str, int]] = {}

    def record_execution(
        self,
        tool_name: str,
        success: bool,
        execution_time: float,
        error: Optional[str] = None
    ) -> None:
        """Record a tool execution.

        Args:
            tool_name: Name of executed tool
            success: Whether execution succeeded
            execution_time: Execution time in seconds
            error: Error message if failed
        """
        import time

        record = {
            "tool_name": tool_name,
            "success": success,
            "execution_time": execution_time,
            "error": error,
            "timestamp": time.time()
        }

        self._history.append(record)

        # Update statistics
        if tool_name not in self._stats:
            self._stats[tool_name] = {
                "total": 0,
                "success": 0,
                "failure": 0
            }

        self._stats[tool_name]["total"] += 1
        if success:
            self._stats[tool_name]["success"] += 1
        else:
            self._stats[tool_name]["failure"] += 1

    def get_stats(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """Get execution statistics.

        Args:
            tool_name: Optional specific tool name

        Returns:
            Statistics dictionary
        """
        if tool_name:
            return self._stats.get(tool_name, {})

        return self._stats

    def get_history(
        self,
        tool_name: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get execution history.

        Args:
            tool_name: Optional filter by tool name
            limit: Optional limit number of records

        Returns:
            List of execution records
        """
        history = self._history

        if tool_name:
            history = [h for h in history if h["tool_name"] == tool_name]

        if limit:
            history = history[-limit:]

        return history

    def clear_history(self) -> None:
        """Clear execution history."""
        self._history.clear()
        self._stats.clear()


__all__ = [
    "ToolExecutor",
    "BatchToolExecutor",
    "ToolExecutionTracker"
]
