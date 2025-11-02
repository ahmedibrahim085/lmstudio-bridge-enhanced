#!/usr/bin/env python3
"""
Test Constants - Configuration for all tests.

This file contains all hardcoded values used in tests, making them
configurable and easy to maintain across different environments.
"""

# Model names (adjust based on available models in LM Studio)
DEFAULT_TEST_MODEL = "qwen/qwen3-coder-30b"
REASONING_MODEL = "mistralai/magistral-small-2509"
CODING_MODEL = "qwen/qwen3-coder-30b"
THINKING_MODEL = "qwen/qwen3-4b-thinking-2507"
SMALL_MODEL = "ibm/granite-4-h-tiny"

# Alternative model names for fallback
FALLBACK_MODELS = [
    "qwen/qwen3-coder-30b",
    "mistralai/magistral-small-2509",
    "qwen/qwen3-4b-thinking-2507",
]

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
