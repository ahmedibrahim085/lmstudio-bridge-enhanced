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
from pydantic import BaseModel, Field, field_validator

# Import constants
from config.constants import (
    DEFAULT_LMSTUDIO_HOST,
    DEFAULT_LMSTUDIO_PORT,
)

logger = logging.getLogger(__name__)


class LMStudioConfig(BaseModel):
    """Configuration for LM Studio API connection."""

    host: str = Field(..., min_length=1, description="LM Studio host")
    port: int = Field(..., ge=1, le=65535, description="LM Studio port (1-65535)")
    api_base: str = Field(..., min_length=1, description="API base URL")
    default_model: str = Field(..., min_length=1, description="Default model name")

    @field_validator('host')
    @classmethod
    def validate_host(cls, v: str) -> str:
        """Validate host is non-empty."""
        if not v or not v.strip():
            raise ValueError("Host must be a non-empty string")
        return v.strip()

    @field_validator('port')
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Validate port is in valid range."""
        if not (1 <= v <= 65535):
            raise ValueError(f"Port must be between 1-65535, got {v}")
        return v

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
        try:
            host = os.getenv("LMSTUDIO_HOST", DEFAULT_LMSTUDIO_HOST)
            port_str = os.getenv("LMSTUDIO_PORT", str(DEFAULT_LMSTUDIO_PORT))

            # Convert port to integer with error handling
            try:
                port = int(port_str)
            except ValueError:
                raise ValueError(f"Invalid LMSTUDIO_PORT: '{port_str}' is not a valid integer")

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
        except ValueError as e:
            # Re-raise ValueError with clearer context
            raise ValueError(f"Configuration validation error: {e}") from e
        except Exception as e:
            # Catch any other errors (including Pydantic validation errors)
            raise ValueError(f"Failed to load LMStudio configuration: {e}") from e

    @staticmethod
    def _get_first_available_model(api_base: str) -> str:
        """Get first available non-embedding model from LM Studio.

        This method:
        1. First checks if any model is currently loaded (using LMS CLI)
        2. If a model is loaded, uses that (avoids loading a new model)
        3. Otherwise, selects a small model that's likely to load successfully
        4. Prefers models with size indicators (e.g., "3b", "4b", "7b") over large ones

        Args:
            api_base: Base URL for LM Studio API

        Returns:
            First available model name, or "default" if none found
        """
        from config.constants import DEFAULT_MODEL_KEYWORD

        # Step 1: Check if any model is already loaded using LMS CLI
        try:
            from utils.lms_helper import LMSHelper
            if LMSHelper.is_installed():
                loaded_models = LMSHelper.list_loaded_models()
                if loaded_models:
                    # list_loaded_models() returns list of dicts with model info
                    # Extract the identifier (base model name) from first loaded model
                    first_model = loaded_models[0]
                    selected = first_model.get("identifier", "")

                    # CRITICAL: Strip instance suffix (e.g., ":2", ":3") to get base model name
                    # LM Studio adds these suffixes when same model loaded multiple times
                    # We must use base name for config to avoid issues when model reloads
                    selected = LMSHelper._get_base_model_name(selected)

                    if selected:
                        logger.info(f"Using already-loaded model: {selected}")
                        return selected
        except Exception as e:
            logger.debug(f"Could not check loaded models via LMS CLI: {e}")

        # Step 2: Query available models from LM Studio API
        try:
            import requests
            import re

            response = requests.get(
                f"{api_base}/models",
                timeout=5.0
            )
            response.raise_for_status()
            data = response.json()

            # Get all model IDs
            models = [model["id"] for model in data.get("data", [])]

            if not models:
                logger.warning(f"No models available in LM Studio, using '{DEFAULT_MODEL_KEYWORD}'")
                return DEFAULT_MODEL_KEYWORD

            # Filter out embedding models (they start with "text-embedding-")
            non_embedding_models = [
                m for m in models
                if not m.startswith("text-embedding-")
            ]

            if not non_embedding_models:
                # All models are embeddings, just use first one
                logger.warning(
                    "All models are embedding models, using first one: "
                    f"{models[0]}"
                )
                return models[0]

            # Step 3: Prefer smaller models to avoid memory issues
            # Look for models with small size indicators (1b-8b are usually safe)
            def get_model_size(model_name: str) -> int:
                """Extract model size in billions from name. Returns 999 if unknown."""
                # Match patterns like "3b", "4b", "7b", "8b" (case insensitive)
                match = re.search(r'(\d+)b', model_name.lower())
                if match:
                    return int(match.group(1))
                return 999  # Unknown size, sort last

            # Sort by size (smallest first)
            sorted_models = sorted(non_embedding_models, key=get_model_size)

            # Prefer models <= 8B parameters
            small_models = [m for m in sorted_models if get_model_size(m) <= 8]

            if small_models:
                selected = small_models[0]
                logger.info(
                    f"Selected small model '{selected}' from {len(non_embedding_models)} "
                    f"available non-embedding models (preferring <=8B to avoid memory issues)"
                )
            else:
                # No small models, use smallest available
                selected = sorted_models[0]
                logger.warning(
                    f"No small models found, using '{selected}'. "
                    f"This may require significant memory."
                )

            return selected

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


class MCPConfig(BaseModel):
    """Configuration for MCP client connections."""

    default_working_directory: str = Field(..., min_length=1, description="Default working directory for MCP operations")

    @field_validator('default_working_directory')
    @classmethod
    def validate_working_directory(cls, v: str) -> str:
        """Validate working directory is non-empty."""
        if not v or not v.strip():
            raise ValueError("Working directory must be a non-empty string")
        return v.strip()

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
