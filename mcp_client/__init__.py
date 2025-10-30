"""MCP client functionality for connecting to other MCP servers."""

from .connection import MCPConnection, MCPConnectionManager
from .tool_discovery import ToolDiscovery, SchemaConverter, ToolRegistry
from .executor import ToolExecutor, BatchToolExecutor, ToolExecutionTracker
from .roots_manager import RootsManager
from .persistent_session import PersistentMCPSession

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
    "PersistentMCPSession"
]
