#!/usr/bin/env python3
"""Static MCP discovery — reads .mcp.json to discover available MCPs at startup.

This module provides **static** (session-scoped) MCP server discovery by
reading ``.mcp.json`` configuration files. Servers discovered here are
available for the entire session.

For **dynamic** (per-request) MCP server attachment, see
``mcp_client.ephemeral`` which uses the ``integrations`` parameter of
LM Studio's ``/api/v1/chat`` endpoint (LM Studio 0.4+).

Configuration sources:
- Claude Code's .mcp.json (project configuration)
- Any other .mcp.json file specified by path
"""

import glob
import json
import os
import platform
import shutil
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path


class MCPDiscovery:
    """
    Discovers available MCPs from .mcp.json configuration files.

    This enables dynamic MCP support - as soon as you add a new MCP to
    .mcp.json, it becomes available to the local LLM automatically!
    """

    def __init__(self, mcp_json_path: Optional[str] = None):
        """
        Initialize MCP discovery.

        Args:
            mcp_json_path: Optional path to .mcp.json file
                          If not provided, searches for .mcp.json in:
                          1. Current Claude Code project directory
                          2. Current working directory
                          3. User's home directory
        """
        self.mcp_json_path = mcp_json_path or self._find_mcp_json()
        self.mcp_configs: Dict[str, Dict[str, Any]] = {}

        if self.mcp_json_path:
            self.load_configs()

    def _find_mcp_json(self) -> Optional[str]:
        """
        Search for .mcp.json in common locations.

        Priority order:
        1. MCP_JSON_PATH environment variable (if set)
        2. LM Studio's mcp.json (if using local LLM, this is most relevant)
        3. Current working directory
        4. User's home directory
        5. Parent directory

        Returns:
            Path to .mcp.json if found, None otherwise
        """
        possible_paths = []

        # Check environment variable first (allows explicit override)
        if "MCP_JSON_PATH" in os.environ:
            possible_paths.append(os.path.expanduser(os.environ["MCP_JSON_PATH"]))

        # Add standard search locations
        from config.constants import MCP_CONFIG_SEARCH_PATHS
        # Expand paths with proper home directory resolution
        possible_paths.extend([
            os.path.expanduser(path) if path.startswith("~") else
            os.path.join(os.getcwd(), path) if not os.path.isabs(path) else path
            for path in MCP_CONFIG_SEARCH_PATHS
        ])

        for path in possible_paths:
            if os.path.exists(path):
                return path

        return None

    def load_configs(self) -> None:
        """
        Load MCP configurations from .mcp.json.

        Raises:
            FileNotFoundError: If .mcp.json doesn't exist
            json.JSONDecodeError: If .mcp.json is invalid JSON
        """
        if not self.mcp_json_path:
            raise FileNotFoundError("No .mcp.json file found")

        if not os.path.exists(self.mcp_json_path):
            raise FileNotFoundError(f".mcp.json not found at: {self.mcp_json_path}")

        with open(self.mcp_json_path) as f:
            config = json.load(f)

        self.mcp_configs = config.get("mcpServers", {})

    def list_available_mcps(self, include_disabled: bool = False) -> List[str]:
        """
        List names of all available MCPs.

        Args:
            include_disabled: If True, includes disabled MCPs

        Returns:
            List of MCP names

        Example:
            >>> discovery = MCPDiscovery()
            >>> discovery.list_available_mcps()
            ['filesystem', 'memory', 'fetch', 'github', 'python-interpreter']
        """
        if include_disabled:
            return list(self.mcp_configs.keys())

        return [
            name for name, config in self.mcp_configs.items()
            if not config.get("disabled", False)
        ]

    def get_mcp_config(self, mcp_name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific MCP.

        Args:
            mcp_name: Name of the MCP (e.g., "filesystem", "memory")

        Returns:
            Dictionary with MCP configuration (command, args, env)

        Raises:
            ValueError: If MCP not found or is disabled

        Example:
            >>> discovery = MCPDiscovery()
            >>> config = discovery.get_mcp_config("filesystem")
            >>> print(config["command"])
            'npx'
        """
        if mcp_name not in self.mcp_configs:
            available = self.list_available_mcps(include_disabled=True)
            raise ValueError(
                f"MCP '{mcp_name}' not found in configuration. "
                f"Available MCPs: {', '.join(available)}"
            )

        config = self.mcp_configs[mcp_name]

        if config.get("disabled", False):
            raise ValueError(
                f"MCP '{mcp_name}' is disabled in configuration. "
                f"Enable it in .mcp.json to use it."
            )

        return config

    @staticmethod
    def _resolve_node_and_npx() -> Tuple[Optional[str], Optional[str]]:
        """Find node and npx executables using platform-appropriate resolution.

        Strategy 1: shutil.which (works on all platforms)
        Strategy 2: Platform-specific fallbacks (macOS Homebrew)

        Returns:
            Tuple of (node_path, npx_path), either may be None.
        """
        node_path = shutil.which("node") or None
        npx_path = shutil.which("npx") or None

        # If both found, done
        if node_path and npx_path:
            return node_path, npx_path

        # Platform-specific fallback
        if platform.system() == "Darwin":
            hb_node, hb_npx = MCPDiscovery._resolve_homebrew_node()
            node_path = node_path or hb_node
            npx_path = npx_path or hb_npx

        return node_path, npx_path

    @staticmethod
    def _resolve_homebrew_node() -> Tuple[Optional[str], Optional[str]]:
        """macOS Homebrew fallback for node/npx resolution.

        Searches Homebrew Cellar first (actual binaries), then symlink dirs.

        Returns:
            Tuple of (node_path, npx_path), either may be None.
        """
        node_path: Optional[str] = None
        npx_path: Optional[str] = None

        # Strategy 1: Homebrew Cellar (actual binaries, not symlinks)
        node_matches = glob.glob("/opt/homebrew/Cellar/node/*/bin/node")
        if node_matches:
            node_path = sorted(node_matches)[-1]  # Latest version

        npx_matches = glob.glob("/opt/homebrew/Cellar/node/*/bin/npx")
        if npx_matches:
            npx_path = sorted(npx_matches)[-1]

        # Strategy 2: Standard symlink dirs
        for search_dir in ["/opt/homebrew/bin", "/usr/local/bin"]:
            if not node_path:
                candidate = os.path.join(search_dir, "node")
                if os.path.isfile(candidate):
                    node_path = candidate
            if not npx_path:
                candidate = os.path.join(search_dir, "npx")
                if os.path.isfile(candidate):
                    npx_path = candidate

        return node_path, npx_path

    def get_connection_params(self, mcp_name: str) -> Dict[str, Any]:
        """
        Get connection parameters for a specific MCP.

        Args:
            mcp_name: Name of the MCP

        Returns:
            Dictionary with command, args, env for connecting to the MCP

        Example:
            >>> discovery = MCPDiscovery()
            >>> params = discovery.get_connection_params("filesystem")
            >>> print(params)
            {
                'command': 'npx',
                'args': ['-y', '@modelcontextprotocol/server-filesystem', '/path'],
                'env': {}
            }
        """
        config = self.get_mcp_config(mcp_name)

        # Get env from config, or start with empty dict
        env = config.get("env", {}).copy()

        # Add system PATH to subprocess environment
        if "PATH" not in env:
            env["PATH"] = os.environ.get("PATH", "")

        command = config["command"]
        args = config["args"].copy()

        if command == "npx":
            # Resolve node/npx via platform-abstract strategy
            node_path, npx_path = self._resolve_node_and_npx()

            # Replace: npx <args> -> node /path/to/npx <args>
            # This bypasses the shebang issue where env can't find node
            if node_path and npx_path:
                command = node_path
                args = [npx_path] + args

        return {
            "command": command,
            "args": args,
            "env": env
        }

    def get_mcp_info(self, mcp_name: str) -> Dict[str, Any]:
        """
        Get detailed information about an MCP.

        Args:
            mcp_name: Name of the MCP

        Returns:
            Dictionary with MCP information including:
            - name: MCP name
            - command: Command to start the MCP
            - args: Arguments for the command
            - env: Environment variables
            - disabled: Whether the MCP is disabled
            - description: Auto-generated description based on command

        Example:
            >>> discovery = MCPDiscovery()
            >>> info = discovery.get_mcp_info("memory")
            >>> print(info["description"])
            'MCP server: @modelcontextprotocol/server-memory'
        """
        config = self.get_mcp_config(mcp_name)

        # Try to extract a description from the args
        description = f"MCP server: {mcp_name}"
        if config["args"]:
            # Look for package name in args
            for arg in config["args"]:
                from config.constants import MCP_PACKAGE_PATTERNS
                if any(pattern in arg for pattern in MCP_PACKAGE_PATTERNS):
                    description = f"MCP server: {arg}"
                    break

        return {
            "name": mcp_name,
            "command": config["command"],
            "args": config["args"],
            "env": config.get("env", {}),
            "disabled": config.get("disabled", False),
            "description": description
        }

    def list_all_mcps_info(self, include_disabled: bool = False) -> List[Dict[str, Any]]:
        """
        List detailed information for all MCPs.

        Args:
            include_disabled: If True, includes disabled MCPs

        Returns:
            List of dictionaries with MCP information

        Example:
            >>> discovery = MCPDiscovery()
            >>> mcps = discovery.list_all_mcps_info()
            >>> for mcp in mcps:
            ...     print(f"{mcp['name']}: {mcp['description']}")
        """
        mcp_names = self.list_available_mcps(include_disabled=include_disabled)

        result = []
        for name in mcp_names:
            try:
                info = self.get_mcp_info(name)
                result.append(info)
            except ValueError:
                # Skip disabled MCPs if include_disabled=False
                continue

        return result

    def validate_mcp_names(self, mcp_names: List[str]) -> List[str]:
        """
        Validate a list of MCP names and return only valid, enabled ones.

        Args:
            mcp_names: List of MCP names to validate

        Returns:
            List of valid, enabled MCP names

        Raises:
            ValueError: If no valid MCPs found

        Example:
            >>> discovery = MCPDiscovery()
            >>> valid = discovery.validate_mcp_names(["filesystem", "invalid", "memory"])
            >>> print(valid)
            ['filesystem', 'memory']
        """
        valid_mcps = []
        available = self.list_available_mcps()

        for name in mcp_names:
            if name in available:
                valid_mcps.append(name)

        if not valid_mcps:
            raise ValueError(
                f"None of the specified MCPs are available. "
                f"Available MCPs: {', '.join(available)}"
            )

        return valid_mcps


# Singleton instance for convenience
_discovery_instance: Optional[MCPDiscovery] = None


def get_mcp_discovery(mcp_json_path: Optional[str] = None) -> MCPDiscovery:
    """
    Get or create the global MCP discovery instance.

    Args:
        mcp_json_path: Optional path to .mcp.json file

    Returns:
        MCPDiscovery instance

    Example:
        >>> discovery = get_mcp_discovery()
        >>> available = discovery.list_available_mcps()
    """
    global _discovery_instance

    if _discovery_instance is None or mcp_json_path is not None:
        _discovery_instance = MCPDiscovery(mcp_json_path)

    return _discovery_instance


def reset_mcp_discovery() -> None:
    """
    Reset the global MCP discovery instance.

    This is primarily useful for testing to ensure test isolation.
    After calling this function, the next call to get_mcp_discovery()
    will create a fresh instance.

    Example:
        >>> # In test teardown
        >>> reset_mcp_discovery()
    """
    global _discovery_instance
    _discovery_instance = None


__all__ = [
    "MCPDiscovery",
    "get_mcp_discovery",
    "reset_mcp_discovery"
]
