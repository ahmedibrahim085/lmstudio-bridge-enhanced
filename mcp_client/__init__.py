"""MCP client functionality for connecting to other MCP servers."""

from .connection import MCPConnection, MCPConnectionManager
from .tool_discovery import ToolDiscovery, SchemaConverter, ToolRegistry
from .executor import ToolExecutor, BatchToolExecutor, ToolExecutionTracker
from .roots_manager import RootsManager
from .persistent_session import PersistentMCPSession
from .type_coercion import coerce_tool_arg_types, safe_call_tool, NUMERIC_PARAMS

__all__ = [
    "MCPConnection",
    "MCPConnectionManager",
    "ToolDiscovery",
    "SchemaConverter",
    "ToolRegistry",
    "ToolExecutor",
    "BatchToolExecutor",
    "ToolExecutionTracker",
    "RootsManager",
    "PersistentMCPSession",
    "coerce_tool_arg_types",
    "safe_call_tool",
    "NUMERIC_PARAMS"
]
