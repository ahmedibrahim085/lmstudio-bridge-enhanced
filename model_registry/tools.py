#!/usr/bin/env python3
"""
MCP Tool Definitions for Model Registry.

This module exposes the Model Registry as MCP tools that can be
called by LLMs during autonomous execution.

Tools:
- list_available_models: List all downloaded models with status
- get_model_capabilities: Get detailed capabilities for a model
- refresh_model_registry: Refresh registry (research new, remove old)
"""

import logging
from typing import Dict, List, Optional, Any

from .registry import get_registry, ModelRegistry
from .lms_integration import LMSNotInstalledError, LMSCommandError
from .schemas import ResearchStatus

logger = logging.getLogger(__name__)


# =============================================================================
# Tool Response Formatters
# =============================================================================

def _error_response(error: str, code: str = "error") -> Dict[str, Any]:
    """Format an error response."""
    return {
        "success": False,
        "error": error,
        "error_code": code
    }


def _success_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """Format a success response."""
    return {
        "success": True,
        **data
    }


# =============================================================================
# MCP Tool: list_available_models
# =============================================================================

def list_available_models(
    include_embeddings: bool = False,
    cache_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    List all available models in LM Studio with their status.

    This tool queries LM Studio CLI to get all downloaded models and
    cross-references with the capability registry.

    Args:
        include_embeddings: Whether to include embedding models (default: False)
        cache_path: Optional custom cache path for the registry

    Returns:
        Dictionary containing:
        - available: List of all downloaded model IDs
        - loaded: List of currently loaded model IDs
        - unknown: List of models not yet researched
        - stats: Registry statistics

    Raises:
        LMSNotInstalledError if LMS CLI is not installed

    Example:
        >>> result = list_available_models()
        >>> print(result["available"])
        ["qwen/qwen3-coder-30b", "mistralai/magistral-small-2509", ...]
        >>> print(result["loaded"])
        ["qwen/qwen3-coder-30b"]
    """
    try:
        registry = get_registry(cache_path=cache_path)
        result = registry.list_available_models(
            include_embeddings=include_embeddings
        )
        return _success_response(result)

    except LMSNotInstalledError as e:
        logger.error(f"LMS CLI not installed: {e}")
        return _error_response(
            str(e),
            code="lms_not_installed"
        )
    except LMSCommandError as e:
        logger.error(f"LMS command failed: {e}")
        return _error_response(
            f"LMS command failed: {e.stderr}",
            code="lms_command_error"
        )
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        return _error_response(str(e))


# =============================================================================
# MCP Tool: get_model_capabilities
# =============================================================================

def get_model_capabilities(
    model_name: str,
    auto_research: bool = True,
    cache_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get detailed capabilities and benchmarks for a specific model.

    This tool returns comprehensive information about a model including:
    - Tool calling capability (with BFCL score if available)
    - Vision support
    - Structured output support
    - Reasoning capability
    - Coding capability
    - Context window size
    - Recommended use cases

    Args:
        model_name: The model identifier (e.g., "qwen/qwen3-coder-30b")
        auto_research: Automatically research if not cached (default: True)
        cache_path: Optional custom cache path

    Returns:
        Dictionary containing:
        - model_id: Model identifier
        - capabilities: Detailed capability scores with confidence
        - benchmarks: BFCL and other benchmark data
        - recommended_for: List of recommended use cases
        - research_status: Whether capabilities have been researched

    Example:
        >>> result = get_model_capabilities("qwen/qwen3-coder-30b")
        >>> print(result["capabilities"]["tool_calling"])
        {"supported": 0.933, "confidence": 0.95, "source": "web_research"}
    """
    if not model_name:
        return _error_response(
            "model_name is required",
            code="invalid_argument"
        )

    try:
        registry = get_registry(cache_path=cache_path)
        result = registry.get_model_capabilities(
            model_id=model_name,
            auto_research=auto_research
        )

        if result is None:
            return _error_response(
                f"Model '{model_name}' not found. "
                "Use list_available_models to see available models.",
                code="model_not_found"
            )

        return _success_response(result)

    except LMSNotInstalledError as e:
        return _error_response(str(e), code="lms_not_installed")
    except LMSCommandError as e:
        return _error_response(
            f"LMS command failed: {e.stderr}",
            code="lms_command_error"
        )
    except Exception as e:
        logger.error(f"Error getting model capabilities: {e}")
        return _error_response(str(e))


# =============================================================================
# MCP Tool: refresh_model_registry
# =============================================================================

def refresh_model_registry(
    models: Optional[List[str]] = None,
    force_all: bool = False,
    remove_unavailable: bool = True,
    cache_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Refresh the model capability registry.

    This tool synchronizes the registry with LM Studio:
    - Discovers and researches new models (delta update)
    - Removes models no longer available in LM Studio
    - Optionally re-researches all models

    IMPORTANT: This removes models that are no longer downloaded in LM Studio.

    Args:
        models: Specific model IDs to refresh (None = auto-detect new)
        force_all: Re-research ALL models, not just new ones
        remove_unavailable: Remove models no longer in LM Studio (default: True)
        cache_path: Optional custom cache path

    Returns:
        Dictionary containing:
        - researched: List of newly researched model IDs
        - cached: List of models using cached data
        - removed: List of models removed from registry
        - failed: List of models where research failed

    Example:
        >>> result = refresh_model_registry()
        >>> print(f"Researched {len(result['researched'])} new models")
        >>> print(f"Removed {len(result['removed'])} unavailable models")
    """
    try:
        registry = get_registry(cache_path=cache_path)
        result = registry.refresh_registry_sync(
            models=models,
            force_all=force_all,
            remove_unavailable=remove_unavailable
        )
        return _success_response(result)

    except LMSNotInstalledError as e:
        return _error_response(str(e), code="lms_not_installed")
    except LMSCommandError as e:
        return _error_response(
            f"LMS command failed: {e.stderr}",
            code="lms_command_error"
        )
    except Exception as e:
        logger.error(f"Error refreshing registry: {e}")
        return _error_response(str(e))


# =============================================================================
# Helper Functions for Autonomous Agents
# =============================================================================

def get_best_tool_calling_model(
    loaded_only: bool = True,
    cache_path: Optional[str] = None
) -> Optional[str]:
    """
    Get the best available model for tool calling.

    This is a convenience function for autonomous agents to quickly
    select the best model for tool use tasks.

    Args:
        loaded_only: Only consider currently loaded models
        cache_path: Optional custom cache path

    Returns:
        Model ID of the best tool calling model, or None if none found
    """
    try:
        registry = get_registry(cache_path=cache_path)
        model = registry.get_best_model_for(
            use_case="tool_use",
            loaded_only=loaded_only
        )
        return model.model_id if model else None
    except Exception as e:
        logger.error(f"Error getting best tool calling model: {e}")
        return None


def get_best_coding_model(
    loaded_only: bool = True,
    cache_path: Optional[str] = None
) -> Optional[str]:
    """
    Get the best available model for coding tasks.

    Args:
        loaded_only: Only consider currently loaded models
        cache_path: Optional custom cache path

    Returns:
        Model ID of the best coding model, or None if none found
    """
    try:
        registry = get_registry(cache_path=cache_path)
        model = registry.get_best_model_for(
            use_case="coding",
            loaded_only=loaded_only
        )
        return model.model_id if model else None
    except Exception as e:
        logger.error(f"Error getting best coding model: {e}")
        return None


def get_best_vision_model(
    loaded_only: bool = True,
    cache_path: Optional[str] = None
) -> Optional[str]:
    """
    Get the best available model for vision tasks.

    Args:
        loaded_only: Only consider currently loaded models
        cache_path: Optional custom cache path

    Returns:
        Model ID of the best vision model, or None if none found
    """
    try:
        registry = get_registry(cache_path=cache_path)
        model = registry.get_best_model_for(
            use_case="vision",
            loaded_only=loaded_only
        )
        return model.model_id if model else None
    except Exception as e:
        logger.error(f"Error getting best vision model: {e}")
        return None


# =============================================================================
# Tool Registration for MCP Server
# =============================================================================

# Tool schemas for MCP registration
TOOL_SCHEMAS = {
    "list_available_models": {
        "name": "list_available_models",
        "description": (
            "List all models available in LM Studio with their status. "
            "Returns available, loaded, and unknown (not yet researched) models. "
            "Use this to discover what models are installed and their research status."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "include_embeddings": {
                    "type": "boolean",
                    "description": "Whether to include embedding models",
                    "default": False
                }
            },
            "required": []
        }
    },
    "get_model_capabilities": {
        "name": "get_model_capabilities",
        "description": (
            "Get detailed capabilities and benchmarks for a specific model. "
            "Returns tool calling scores (BFCL), vision support, coding capability, "
            "reasoning ability, and recommended use cases. "
            "Use this to understand what a model is good at before selecting it."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "model_name": {
                    "type": "string",
                    "description": "Model identifier (e.g., 'qwen/qwen3-coder-30b')"
                },
                "auto_research": {
                    "type": "boolean",
                    "description": "Auto-research if not cached",
                    "default": True
                }
            },
            "required": ["model_name"]
        }
    },
    "refresh_model_registry": {
        "name": "refresh_model_registry",
        "description": (
            "Refresh the model capability registry. "
            "Discovers new models, researches their capabilities, and removes "
            "models no longer available in LM Studio. "
            "Use after downloading new models or to clean up stale entries."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "models": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific models to refresh (None = auto-detect new)"
                },
                "force_all": {
                    "type": "boolean",
                    "description": "Re-research ALL models",
                    "default": False
                },
                "remove_unavailable": {
                    "type": "boolean",
                    "description": "Remove models no longer in LM Studio",
                    "default": True
                }
            },
            "required": []
        }
    }
}


def get_tool_handlers() -> Dict[str, callable]:
    """
    Get mapping of tool names to handler functions.

    Returns:
        Dictionary mapping tool names to their handler functions
    """
    return {
        "list_available_models": list_available_models,
        "get_model_capabilities": get_model_capabilities,
        "refresh_model_registry": refresh_model_registry
    }
