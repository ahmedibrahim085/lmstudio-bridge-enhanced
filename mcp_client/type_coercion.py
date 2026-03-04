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

Configuration:
    NUMERIC_PARAMS can be extended via environment variable:
    LMS_EXTRA_NUMERIC_PARAMS=param1,param2,param3

    This allows adding custom numeric parameters without code changes.
"""

import json
import logging
import os
from typing import Any, Dict, Set

from config.constants.tool_config import SCHEMA_COERCION_ENABLED

logger = logging.getLogger(__name__)


# Default known numeric parameters from common MCP tools (filesystem, git, etc.)
_DEFAULT_NUMERIC_PARAMS = {
    'head', 'tail', 'limit', 'offset',
    'max_count', 'context_lines',
    # Additional common numeric params
    'timeout', 'retries', 'depth', 'count',
    'start_line', 'end_line', 'line_number'
}


def _load_numeric_params() -> Set[str]:
    """Load numeric params from defaults + environment variable.

    Environment variable LMS_EXTRA_NUMERIC_PARAMS can add additional params:
        LMS_EXTRA_NUMERIC_PARAMS=custom_limit,page_size,batch_size

    Returns:
        Set of all numeric parameter names
    """
    params = _DEFAULT_NUMERIC_PARAMS.copy()

    # Load additional params from environment
    extra_params_str = os.environ.get('LMS_EXTRA_NUMERIC_PARAMS', '')
    if extra_params_str:
        extra_params = {p.strip() for p in extra_params_str.split(',') if p.strip()}
        if extra_params:
            logger.debug(f"Adding extra numeric params from env: {extra_params}")
            params.update(extra_params)

    return params


# Loaded at module import time from defaults + LMS_EXTRA_NUMERIC_PARAMS env var
NUMERIC_PARAMS = _load_numeric_params()


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


def coerce_with_schema(args: Dict[str, Any], schema: Dict[str, Any] | None) -> Dict[str, Any]:
    """Coerce tool arguments using MCP tool schema for array/object types.

    Only coerces string values when schema explicitly declares them as
    "type": "array" or "type": "object". This prevents blind JSON parsing.

    Args:
        args: Tool arguments dictionary
        schema: MCP tool inputSchema dict, or None

    Returns:
        New dict with coerced values where applicable (immutable pattern)
    """
    if schema is None or "properties" not in schema:
        return args

    if not SCHEMA_COERCION_ENABLED:
        return args

    coerced: Dict[str, Any] = {}
    schema_properties = schema["properties"]

    for key, value in args.items():
        if key in schema_properties:
            expected_type = schema_properties[key].get("type")
            if (
                expected_type in ("array", "object")
                and isinstance(value, str)
                and value  # non-empty string
            ):
                try:
                    parsed = json.loads(value)
                    if expected_type == "array" and isinstance(parsed, list):
                        coerced[key] = parsed
                        logger.debug(
                            f"Schema-coerced '{key}' from JSON string to list"
                        )
                    elif expected_type == "object" and isinstance(parsed, dict):
                        coerced[key] = parsed
                        logger.debug(
                            f"Schema-coerced '{key}' from JSON string to dict"
                        )
                    else:
                        # Type mismatch: parsed type doesn't match schema type
                        coerced[key] = value
                except (json.JSONDecodeError, ValueError):
                    # Invalid JSON: keep original
                    coerced[key] = value
            else:
                coerced[key] = value
        else:
            coerced[key] = value

    return coerced


async def safe_call_tool(
    session,
    tool_name: str,
    arguments: Dict[str, Any],
    tool_schema: Dict[str, Any] | None = None,
):
    """Wrapper for session.call_tool that always applies type coercion.

    This is the SINGLE ENTRY POINT for all tool calls. Using this wrapper
    ensures type coercion is always applied, regardless of the code path.

    Args:
        session: MCP ClientSession with call_tool method
        tool_name: Name of the tool to call
        arguments: Tool arguments (will be coerced)
        tool_schema: Optional MCP tool inputSchema for schema-aware coercion

    Returns:
        CallToolResult from the MCP server

    Example:
        result = await safe_call_tool(session, "read_file", {"path": "/test", "head": "10"})
        # "head": "10" is automatically coerced to "head": 10
    """
    coerced_args = coerce_tool_arg_types(arguments)
    if tool_schema is not None:
        coerced_args = coerce_with_schema(coerced_args, tool_schema)
    return await session.call_tool(tool_name, coerced_args)


__all__ = ['coerce_tool_arg_types', 'coerce_with_schema', 'safe_call_tool', 'NUMERIC_PARAMS']
