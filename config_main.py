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
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

# Import constants
from config.constants import (
    DEFAULT_LMSTUDIO_HOST,
    DEFAULT_LMSTUDIO_PORT,
)

logger = logging.getLogger(__name__)


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
            DEFAULT_MODEL: Default LLM model to use (default: auto-detect first available)

        Returns:
            LMStudioConfig instance with loaded settings
        """
        host = os.getenv("LMSTUDIO_HOST", DEFAULT_LMSTUDIO_HOST)
        port = os.getenv("LMSTUDIO_PORT", str(DEFAULT_LMSTUDIO_PORT))
        api_base = f"http://{host}:{port}/v1"

        # Get default model - either from env or auto-detect
        default_model = os.getenv("DEFAULT_MODEL")

        if not default_model:
            # Auto-detect: fetch available models and use first non-embedding one
            default_model = cls._get_first_available_model(api_base)
            logger.info(f"Auto-detected default model: {default_model}")

        return cls(
            host=host,
            port=port,
            api_base=api_base,
            default_model=default_model
        )

    @staticmethod
    def _get_first_available_model(api_base: str) -> str:
        """Get first available non-embedding model from LM Studio.

        This method queries LM Studio's /v1/models endpoint and returns
        the first available model that isn't an embedding model.

        Args:
            api_base: Base URL for LM Studio API

        Returns:
            First available model name, or "default" if none found
        """
        try:
            import requests

            response = requests.get(
                f"{api_base}/models",
                timeout=5.0
            )
            response.raise_for_status()
            data = response.json()

            # Get all model IDs
            models = [model["id"] for model in data.get("data", [])]

            if not models:
                from config.constants import DEFAULT_MODEL_KEYWORD
                logger.warning(f"No models available in LM Studio, using '{DEFAULT_MODEL_KEYWORD}'")
                return DEFAULT_MODEL_KEYWORD

            # Filter out embedding models (they start with "text-embedding-")
            non_embedding_models = [
                m for m in models
                if not m.startswith("text-embedding-")
            ]

            if non_embedding_models:
                selected = non_embedding_models[0]
                logger.info(
                    f"Selected model '{selected}' from {len(non_embedding_models)} "
                    f"available non-embedding models"
                )
                return selected
            else:
                # All models are embeddings, just use first one
                logger.warning(
                    "All models are embedding models, using first one: "
                    f"{models[0]}"
                )
                return models[0]

        except Exception as e:
            logger.warning(
                f"Failed to auto-detect model from LM Studio: {e}. "
                f"Using '{DEFAULT_MODEL_KEYWORD}'"
            )
            return DEFAULT_MODEL_KEYWORD

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
