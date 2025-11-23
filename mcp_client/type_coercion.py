#!/usr/bin/env python3
"""
Centralized type coercion for MCP tool arguments.

This module provides type coercion to help smaller LLMs that may pass
arguments with incorrect types (e.g., strings instead of numbers).

The coercion is applied at the lowest level (executor) to ensure ALL
tool calls go through coercion regardless of the code path:
- dynamic_autonomous.py autonomous loops
- lmstudio_bridge.py direct calls
- mcp_client/executor.py batch operations

This centralizes the fix instead of duplicating it in multiple places.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


# Known numeric parameters from common MCP tools (filesystem, git, etc.)
NUMERIC_PARAMS = {
    'head', 'tail', 'limit', 'offset',
    'max_count', 'context_lines',
    # Additional common numeric params
    'timeout', 'retries', 'depth', 'count',
    'start_line', 'end_line', 'line_number'
}


def coerce_tool_arg_types(args: Dict[str, Any]) -> Dict[str, Any]:
    """Coerce tool argument types to help smaller models.

    Some LLMs (especially smaller ones like llama-3.2-3b) may pass numeric
    parameters as strings (e.g., "10" instead of 10). This causes MCP tools
    to reject the arguments with type errors like:
    "params.head is not of a type(s) number"

    This function attempts to coerce common patterns:
    - Numeric strings to integers for known numeric params (head, tail, limit, offset)
    - Boolean strings to booleans ("true"/"false")

    Args:
        args: Tool arguments dictionary

    Returns:
        Arguments with coerced types where applicable
    """
    if not isinstance(args, dict):
        return args

    coerced = {}
    for key, value in args.items():
        if key in NUMERIC_PARAMS and isinstance(value, str):
            # Try to coerce string to int
            try:
                coerced[key] = int(value)
                logger.debug(f"Coerced '{key}' from string '{value}' to int {coerced[key]}")
            except ValueError:
                # Try float as fallback
                try:
                    coerced[key] = float(value)
                    logger.debug(f"Coerced '{key}' from string '{value}' to float {coerced[key]}")
                except ValueError:
                    coerced[key] = value  # Keep original if conversion fails
        elif isinstance(value, str) and value.lower() in ('true', 'false'):
            # Coerce boolean strings
            coerced[key] = value.lower() == 'true'
            logger.debug(f"Coerced '{key}' from string '{value}' to bool {coerced[key]}")
        else:
            coerced[key] = value

    return coerced


async def safe_call_tool(session, tool_name: str, arguments: Dict[str, Any]):
    """Wrapper for session.call_tool that always applies type coercion.

    This is the SINGLE ENTRY POINT for all tool calls. Using this wrapper
    ensures type coercion is always applied, regardless of the code path.

    Args:
        session: MCP ClientSession with call_tool method
        tool_name: Name of the tool to call
        arguments: Tool arguments (will be coerced)

    Returns:
        CallToolResult from the MCP server

    Example:
        result = await safe_call_tool(session, "read_file", {"path": "/test", "head": "10"})
        # "head": "10" is automatically coerced to "head": 10
    """
    coerced_args = coerce_tool_arg_types(arguments)
    return await session.call_tool(tool_name, coerced_args)


__all__ = ['coerce_tool_arg_types', 'safe_call_tool', 'NUMERIC_PARAMS']
