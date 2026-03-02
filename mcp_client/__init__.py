"""MCP client functionality for connecting to other MCP servers.

Two server configuration modes:
- **Static** (startup-time): ``MCPDiscovery`` reads ``.mcp.json`` files to
  discover servers available for the entire session.
- **Dynamic** (per-request): ``EphemeralIntegration`` attaches MCP servers
  to individual ``/api/v1/chat`` requests via the ``integrations`` parameter
  (LM Studio 0.4+).
"""

from .connection import MCPConnection, MCPConnectionManager
from .ephemeral import EphemeralIntegration, build_integrations_payload, validate_integration
from .executor import ToolExecutor, BatchToolExecutor
from .persistent_session import PersistentMCPSession
from .roots_manager import RootsManager
from .tool_discovery import ToolDiscovery, SchemaConverter, ToolRegistry
from .type_coercion import coerce_tool_arg_types, safe_call_tool, NUMERIC_PARAMS

__all__ = [
    "MCPConnection",
    "MCPConnectionManager",
    "EphemeralIntegration",
    "build_integrations_payload",
    "validate_integration",
    "ToolDiscovery",
    "SchemaConverter",
    "ToolRegistry",
    "ToolExecutor",
    "BatchToolExecutor",
    "RootsManager",
    "PersistentMCPSession",
    "coerce_tool_arg_types",
    "safe_call_tool",
    "NUMERIC_PARAMS",
]
