#!/usr/bin/env python3
"""
Configuration Constants for LM Studio Bridge Enhanced.

This module contains all default values and configuration constants
used throughout the application. Following best practices - NO hardcoded
values in production code.

Usage:
    from config.constants import DEFAULT_LMSTUDIO_HOST, DEFAULT_LMSTUDIO_PORT

    # Use constants instead of hardcoded values
    host = os.getenv("LMSTUDIO_HOST", DEFAULT_LMSTUDIO_HOST)
    port = int(os.getenv("LMSTUDIO_PORT", DEFAULT_LMSTUDIO_PORT))
"""

# LM Studio Server Configuration
DEFAULT_LMSTUDIO_HOST = "localhost"
DEFAULT_LMSTUDIO_PORT = 1234
DEFAULT_LMSTUDIO_BASE_URL = f"http://{DEFAULT_LMSTUDIO_HOST}:{DEFAULT_LMSTUDIO_PORT}"

# API Endpoints
API_VERSION = "v1"
MODELS_ENDPOINT = "/v1/models"
CHAT_COMPLETIONS_ENDPOINT = "/v1/chat/completions"
COMPLETIONS_ENDPOINT = "/v1/completions"
EMBEDDINGS_ENDPOINT = "/v1/embeddings"
RESPONSES_ENDPOINT = "/v1/responses"

# Timeout Configuration (seconds)
DEFAULT_REQUEST_TIMEOUT = 120.0
DEFAULT_CONNECTION_TIMEOUT = 10.0
DEFAULT_READ_TIMEOUT = 300.0

# Retry Configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_BASE_DELAY = 1.0
DEFAULT_RETRY_MAX_DELAY = 60.0

# Model Validation
MODEL_CACHE_TTL_SECONDS = 60  # 60-second cache for model validation
MODEL_VALIDATION_TIMEOUT = 5.0

# LLM Generation Defaults
DEFAULT_MAX_TOKENS = 8192
DEFAULT_TEMPERATURE = 0.7
DEFAULT_TOP_P = 0.9
DEFAULT_FREQUENCY_PENALTY = 0.0
DEFAULT_PRESENCE_PENALTY = 0.0

# Autonomous Execution
DEFAULT_MAX_ROUNDS = 10000  # High limit - let LLM work until task complete
DEFAULT_AUTONOMOUS_TIMEOUT = 600  # 10 minutes per autonomous task

# Logging
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# File Paths
DEFAULT_LOG_DIR = "logs"
DEFAULT_CACHE_DIR = ".cache"
DEFAULT_CONFIG_DIR = "config"

# MCP Configuration
DEFAULT_MCP_CONFIG_PATH = ".mcp.json"
DEFAULT_MCP_TIMEOUT = 30.0

# Performance Targets (for testing)
CACHE_VALIDATION_TARGET_MS = 0.1  # Target: < 0.1ms for cached validation
MEMORY_OVERHEAD_TARGET_MB = 10.0  # Target: < 10 MB memory overhead

# Test Configuration
TEST_TIMEOUT = 120  # 2 minutes
SHORT_TEST_TIMEOUT = 30
LONG_TEST_TIMEOUT = 300
SLOW_TEST_THRESHOLD_SECONDS = 30

# Error Messages
ERROR_MODEL_NOT_FOUND = "Model '{model}' not found. Available models: {available}"
ERROR_CONNECTION_FAILED = "Failed to connect to LM Studio at {url}"
ERROR_TIMEOUT = "Request timed out after {timeout} seconds"
ERROR_VALIDATION_FAILED = "Model validation failed: {reason}"
ERROR_MCP_NOT_FOUND = "MCP '{mcp}' not found in configuration"

# Success Messages
SUCCESS_MODEL_LOADED = "Model '{model}' loaded successfully"
SUCCESS_VALIDATION_PASSED = "Model '{model}' validation passed"
SUCCESS_CACHE_HIT = "Cache hit for model '{model}'"

# HTTP Status Codes (for reference)
HTTP_OK = 200
HTTP_BAD_REQUEST = 400
HTTP_NOT_FOUND = 404
HTTP_TIMEOUT = 408
HTTP_RATE_LIMIT = 429
HTTP_SERVER_ERROR = 500

# Feature Flags
ENABLE_CACHING = True
ENABLE_RETRY = True
ENABLE_LOGGING = True
ENABLE_METRICS = True

# Version Info
VERSION = "2.0.0"
API_VERSION_SUPPORTED = "1.0"
MIN_PYTHON_VERSION = "3.9"

# Environment Variable Names (for documentation)
ENV_LMSTUDIO_HOST = "LMSTUDIO_HOST"
ENV_LMSTUDIO_PORT = "LMSTUDIO_PORT"
ENV_LOG_LEVEL = "LOG_LEVEL"
ENV_MAX_RETRIES = "MAX_RETRIES"
ENV_REQUEST_TIMEOUT = "REQUEST_TIMEOUT"
