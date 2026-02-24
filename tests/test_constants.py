#!/usr/bin/env python3
"""
Test Constants — Configuration for all tests.

Non-model constants are static. Model constants use PEP 562 module-level
__getattr__ for lazy resolution via discover_models(), so they automatically
resolve to actually-available models at first access.

Import interface is unchanged:
    from tests.test_constants import REASONING_MODEL  # still works
"""

import logging

from config.constants import (
    DEFAULT_FALLBACK_MODEL,
    DEFAULT_REVIEW_MODEL,
    DEFAULT_SMALL_MODEL,
    DEFAULT_THINKING_MODEL,
    DEFAULT_VISION_MODEL,
)

logger = logging.getLogger(__name__)

# ==============================================================================
# STATIC CONSTANTS — never change at runtime
# ==============================================================================

# MCP names
FILESYSTEM_MCP = "filesystem"
MEMORY_MCP = "memory"
FETCH_MCP = "fetch"
GITHUB_MCP = "github"

# Test timeouts (seconds)
DEFAULT_TIMEOUT = 120
SHORT_TIMEOUT = 30
LONG_TIMEOUT = 300

# Max rounds for autonomous execution
DEFAULT_MAX_ROUNDS = 20
SHORT_MAX_ROUNDS = 10  # Increased from 5: gives LLM more attempts to discover correct paths
LONG_MAX_ROUNDS = 50
E2E_TEST_MAX_ROUNDS = 5  # Budget: 5 × DEFAULT_LLM_TIMEOUT(58s) = 290s < LONG_TEST_TIMEOUT(300s)

# Performance targets
CACHE_VALIDATION_TARGET_MS = 0.1  # < 0.1ms
MEMORY_OVERHEAD_TARGET_MB = 10.0  # < 10 MB

# Cache configuration
CACHE_TTL_SECONDS = 60  # 60-second cache TTL
CACHE_TEST_DELAY_SECONDS = 2  # Wait time for cache tests

# Benchmark configuration
BENCHMARK_VALIDATION_RUNS = 100  # Number of cached validations to test
BENCHMARK_CONCURRENT_RUNS = 50  # Number of concurrent validations

# Test tasks (generic, work with any accessible directory)
SIMPLE_TASK = "What is 2+2? Just give me the number."
LIST_FILES_TASK = "Use the list_directory tool to list files in your working directory and describe what you find. What types of files are present?"
COUNT_FILES_TASK = "Use the list_directory tool to count how many files are in your working directory."
EXPLAIN_TASK = "Use the list_directory tool to explore your working directory structure and explain what you observe."

# E2E test tasks (designed to work with filesystem restrictions)
# Note: CRITICAL - LLM must call list_directory() with NO path parameter to get the allowed directory
# - Filesystem MCP has a configured working directory (/Users/ahmedmaged/ai_storage)
# - Calling list_directory() with no arguments returns files in that directory
# - Do NOT tell LLM to guess paths - it will try /workspace, /home/user, etc.
E2E_ANALYSIS_TASK = "Call the list_directory tool with no arguments (don't provide a path parameter) to see what files are available, then describe what types of files you find."
E2E_IMPLEMENTATION_TASK = "Based on the files you found, describe what this project might be about."

# Invalid test values
INVALID_MODEL_NAME = "definitely-not-a-real-model-name-12345"
INVALID_MCP_NAME = "nonexistent-mcp-xyz"

# Error messages (for assertion checks)
ERROR_KEYWORDS = ["error", "Error", "ERROR", "failed", "Failed", "FAILED"]
NO_CONTENT_MESSAGE = "No content in response"

# File paths (relative to test directory)
TEST_DATA_DIR = "test_data"
TEST_OUTPUT_DIR = "test_output"

# Logging configuration
LOG_LEVEL = "INFO"
VERBOSE_LOGGING = False

# Test markers
SLOW_TEST_THRESHOLD_SECONDS = 30  # Tests taking > 30s are marked as slow

# Alternative model names for fallback (static list for backward compat)
FALLBACK_MODELS = [
    DEFAULT_FALLBACK_MODEL,
    DEFAULT_REVIEW_MODEL,
    DEFAULT_THINKING_MODEL,
]

# ==============================================================================
# DYNAMIC MODEL CONSTANTS — resolved lazily via PEP 562 __getattr__
# ==============================================================================

# Mapping: attribute name → (discovery role, static fallback)
_MODEL_ATTR_MAP = {
    "DEFAULT_TEST_MODEL": ("chat", DEFAULT_FALLBACK_MODEL),
    "REASONING_MODEL": ("reasoning", DEFAULT_REVIEW_MODEL),
    "CODING_MODEL": ("coding", DEFAULT_FALLBACK_MODEL),
    "THINKING_MODEL": ("thinking", DEFAULT_THINKING_MODEL),
    "SMALL_MODEL": ("small", DEFAULT_SMALL_MODEL),
    "VISION_MODEL": ("vision", DEFAULT_VISION_MODEL),
}

# Cache: once resolved, values are stored here so __getattr__ is only called once
_resolved_cache: dict = {}
_discovery_done = False


def _ensure_discovery():
    """Run model discovery exactly once, populating _resolved_cache for all dynamic attrs.

    Resolve-once semantics: the first call runs discover_models() and caches
    every dynamic attribute. Subsequent calls are no-ops (_discovery_done guard).
    On failure, all attrs get their static fallback from _MODEL_ATTR_MAP.
    Results are frozen — changing LM Studio state after first access has no effect.
    """
    global _discovery_done
    if _discovery_done:
        return

    _discovery_done = True

    try:
        from tests.fixtures.model_discovery import discover_models

        discovered = discover_models()

        for attr_name, (role, fallback) in _MODEL_ATTR_MAP.items():
            resolved = discovered.roles.get(role, fallback)
            _resolved_cache[attr_name] = resolved

        if discovered.lmstudio_available:
            logger.debug(
                f"Dynamic model resolution: {_resolved_cache}"
            )
        else:
            logger.debug("LM Studio unavailable — using static fallbacks")

    except Exception as e:
        logger.debug(f"Model discovery failed ({e}), using static fallbacks")
        for attr_name, (_role, fallback) in _MODEL_ATTR_MAP.items():
            _resolved_cache[attr_name] = fallback


def __getattr__(name: str):
    """PEP 562: resolve model constants lazily on first access.

    On first access of any dynamic attr (e.g., DEFAULT_TEST_MODEL),
    _ensure_discovery() runs once, resolving ALL dynamic attrs and storing
    them in module globals. Subsequent accesses hit globals directly —
    __getattr__ is never called again for that name.
    """
    if name in _MODEL_ATTR_MAP:
        _ensure_discovery()
        if name in _resolved_cache:
            # Store in module globals so __getattr__ isn't called again
            globals()[name] = _resolved_cache[name]
            return _resolved_cache[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
