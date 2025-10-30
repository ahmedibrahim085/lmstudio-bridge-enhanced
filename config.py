#!/usr/bin/env python3
"""
Configuration module for lmstudio-bridge-enhanced MCP server.

This module handles all configuration settings including:
- LM Studio API connection settings
- Default model settings
- MCP connection settings
- Environment variable loading
"""

import os
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class LMStudioConfig:
    """Configuration for LM Studio API connection."""

    host: str
    port: str
    api_base: str
    default_model: str

    @classmethod
    def from_env(cls) -> "LMStudioConfig":
        """Load configuration from environment variables.

        Environment Variables:
            LMSTUDIO_HOST: LM Studio host (default: localhost)
            LMSTUDIO_PORT: LM Studio port (default: 1234)
            DEFAULT_MODEL: Default LLM model to use (default: default)

        Returns:
            LMStudioConfig instance with loaded settings
        """
        host = os.getenv("LMSTUDIO_HOST", "localhost")
        port = os.getenv("LMSTUDIO_PORT", "1234")
        api_base = f"http://{host}:{port}/v1"
        default_model = os.getenv("DEFAULT_MODEL", "default")

        return cls(
            host=host,
            port=port,
            api_base=api_base,
            default_model=default_model
        )

    def get_endpoint(self, path: str) -> str:
        """Get full URL for an API endpoint.

        Args:
            path: API path (e.g., 'models', 'chat/completions')

        Returns:
            Full URL for the endpoint
        """
        return f"{self.api_base}/{path.lstrip('/')}"


@dataclass
class MCPConfig:
    """Configuration for MCP client connections."""

    default_working_directory: str

    @classmethod
    def from_env(cls) -> "MCPConfig":
        """Load MCP configuration from environment variables.

        Environment Variables:
            MCP_WORKING_DIR: Default working directory for MCP operations

        Returns:
            MCPConfig instance with loaded settings
        """
        working_dir = os.getenv("MCP_WORKING_DIR", os.getcwd())

        return cls(default_working_directory=working_dir)


class Config:
    """Main configuration class aggregating all settings."""

    def __init__(
        self,
        lmstudio: Optional[LMStudioConfig] = None,
        mcp: Optional[MCPConfig] = None
    ):
        """Initialize configuration.

        Args:
            lmstudio: LM Studio configuration (loads from env if None)
            mcp: MCP configuration (loads from env if None)
        """
        self.lmstudio = lmstudio or LMStudioConfig.from_env()
        self.mcp = mcp or MCPConfig.from_env()

    @classmethod
    def from_env(cls) -> "Config":
        """Load all configuration from environment variables.

        Returns:
            Config instance with all settings loaded
        """
        return cls(
            lmstudio=LMStudioConfig.from_env(),
            mcp=MCPConfig.from_env()
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary.

        Returns:
            Dictionary representation of configuration
        """
        return {
            "lmstudio": {
                "host": self.lmstudio.host,
                "port": self.lmstudio.port,
                "api_base": self.lmstudio.api_base,
                "default_model": self.lmstudio.default_model
            },
            "mcp": {
                "default_working_directory": self.mcp.default_working_directory
            }
        }


# Global configuration instance (loaded lazily)
_config: Optional[Config] = None


def get_config() -> Config:
    """Get global configuration instance.

    Returns:
        Config instance (creates if not exists)
    """
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config


def reset_config() -> None:
    """Reset global configuration (useful for testing)."""
    global _config
    _config = None


__all__ = [
    "LMStudioConfig",
    "MCPConfig",
    "Config",
    "get_config",
    "reset_config"
]
