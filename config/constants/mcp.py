"""MCP server configuration, discovery paths, and package names."""

import os

__all__ = [
    "DEFAULT_FILESYSTEM_ROOT",
    "DEFAULT_LMSTUDIO_MCP_PATH",
    "DEFAULT_MCP_CONFIG_PATH",
    "DEFAULT_MCP_NPX_COMMAND",
    "DEFAULT_MCP_NPX_ARGS",
    "MCP_PACKAGES",
    "MCP_CONFIG_SEARCH_PATHS",
    "MCP_PACKAGE_PATTERNS",
]

# Default root directory for filesystem MCP operations
DEFAULT_FILESYSTEM_ROOT = os.environ.get("MCP_FILESYSTEM_ROOT", os.getcwd())

# Path to LM Studio's MCP configuration file
DEFAULT_LMSTUDIO_MCP_PATH = "~/.lmstudio/mcp.json"

# MCP Configuration
DEFAULT_MCP_CONFIG_PATH = ".mcp.json"

# Default command to run npm-based MCP servers
DEFAULT_MCP_NPX_COMMAND = "npx"
DEFAULT_MCP_NPX_ARGS = ["-y"]

# Official MCP package names
MCP_PACKAGES = {
    "filesystem": "@modelcontextprotocol/server-filesystem",
    "memory": "@modelcontextprotocol/server-memory",
    "github": "@modelcontextprotocol/server-github",
    "fetch": "mcp-server-fetch",
    "sqlite": "mcp-server-sqlite",
    "python": "mcp-server-python-interpreter"
}

# Search paths for MCP configuration files (in priority order)
MCP_CONFIG_SEARCH_PATHS = [
    "~/.lmstudio/mcp.json",    # LM Studio config (HIGHEST PRIORITY for local LLM)
    ".mcp.json",                # Current directory (project-specific config)
    "~/.mcp.json",              # Home directory (user-wide config)
    "../.mcp.json"              # Parent directory (workspace config)
]

# Patterns to identify MCP packages in command arguments
MCP_PACKAGE_PATTERNS = [
    "@modelcontextprotocol",   # Official MCP packages
    "mcp-server"               # Community MCP packages
]
