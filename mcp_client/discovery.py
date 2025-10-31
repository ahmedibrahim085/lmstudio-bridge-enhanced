#!/usr/bin/env python3
"""
Dynamic MCP discovery - reads .mcp.json to discover available MCPs.

This module enables TRULY dynamic MCP support where the local LLM can use
ANY MCP that's configured in either:
- Claude Code's .mcp.json (project configuration)
- Any other .mcp.json file specified by path
"""

import json
import os
from typing import Dict, List, Optional, Any
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

        return {
            "command": config["command"],
            "args": config["args"],
            "env": config.get("env", {})
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


__all__ = [
    "MCPDiscovery",
    "get_mcp_discovery"
]
