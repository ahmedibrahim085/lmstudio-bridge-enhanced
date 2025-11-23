#!/usr/bin/env python3
"""
Model Capability Registry for LM Studio Bridge.

This module provides a registry of model capabilities that can be
queried by LLMs during autonomous execution. It integrates with
LM Studio CLI to discover available models and researches their
capabilities through web search and known benchmark data.

Features:
- List all available models in LM Studio
- Get detailed capabilities for any model
- Smart caching with delta updates
- Automatic research of new models
- Removal of unavailable models

Usage:
    from model_registry import (
        list_available_models,
        get_model_capabilities,
        refresh_model_registry
    )

    # List all available models
    result = list_available_models()
    print(result["available"])

    # Get capabilities for a specific model
    caps = get_model_capabilities("qwen/qwen3-coder-30b")
    print(caps["capabilities"]["tool_calling"])

    # Refresh registry (research new, remove old)
    refresh = refresh_model_registry()
    print(f"Researched {len(refresh['researched'])} new models")

Requirements:
    - LM Studio CLI (lms) must be installed
    - Install: brew install lmstudio-ai/lms/lms
    - Or: npm install -g @lmstudio/lms
"""

# Core schemas
from .schemas import (
    ModelMetadata,
    ModelCapabilities,
    CapabilityScore,
    BenchmarkData,
    RegistryStats,
    ModelType,
    CapabilitySource,
    ResearchStatus
)

# LMS Integration
from .lms_integration import (
    LMSIntegration,
    LMSNotInstalledError,
    LMSCommandError
)

# Cache management
from .cache import CacheManager

# Research engine
from .research import (
    ModelResearcher,
    ResearchResult,
    apply_research_to_metadata
)

# Main registry
from .registry import (
    ModelRegistry,
    get_registry,
    reset_registry
)

# MCP Tools (main API)
from .tools import (
    list_available_models,
    get_model_capabilities,
    refresh_model_registry,
    get_best_tool_calling_model,
    get_best_coding_model,
    get_best_vision_model,
    TOOL_SCHEMAS,
    get_tool_handlers
)

__all__ = [
    # Schemas
    "ModelMetadata",
    "ModelCapabilities",
    "CapabilityScore",
    "BenchmarkData",
    "RegistryStats",
    "ModelType",
    "CapabilitySource",
    "ResearchStatus",

    # LMS Integration
    "LMSIntegration",
    "LMSNotInstalledError",
    "LMSCommandError",

    # Cache
    "CacheManager",

    # Research
    "ModelResearcher",
    "ResearchResult",
    "apply_research_to_metadata",

    # Registry
    "ModelRegistry",
    "get_registry",
    "reset_registry",

    # MCP Tools (main API)
    "list_available_models",
    "get_model_capabilities",
    "refresh_model_registry",
    "get_best_tool_calling_model",
    "get_best_coding_model",
    "get_best_vision_model",
    "TOOL_SCHEMAS",
    "get_tool_handlers"
]

__version__ = "1.0.0"
