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
ENV_MCP_FILESYSTEM_ROOT = "MCP_FILESYSTEM_ROOT"

# ==============================================================================
# MODEL CONFIGURATION - Default models for different operations
# ==============================================================================

# Default fallback model when no model is specified in API calls
# Used in: lmstudio_bridge.py:296 (fallback when model resolution fails)
DEFAULT_FALLBACK_MODEL = "qwen/qwen3-coder-30b"

# Default model for autonomous execution tasks (coding, analysis, implementation)
# Used in: lmstudio_bridge.py:423, tools/dynamic_autonomous.py:129,261,430
#          tools/dynamic_autonomous_register.py:82,163,231
DEFAULT_AUTONOMOUS_MODEL = "qwen/qwen3-coder-30b"

# Default model for code review tasks (smaller, faster for review)
# Used in: run_code_review.py:60, retry_magistral.py:38
DEFAULT_REVIEW_MODEL = "mistralai/magistral-small-2509"

# Default model for thinking/reasoning tasks
# Used in: get_llm_reviews.py:155
DEFAULT_THINKING_MODEL = "qwen/qwen3-4b-thinking-2507"

# Example model name for documentation and docstrings
# Used in: tools/lms_cli_tools.py docstrings, examples
EXAMPLE_MODEL_NAME = "qwen/qwen3-coder-30b"

# List of models to use for comprehensive code reviews
# Used in: get_llm_reviews.py:141,148,155 (multiple model reviews)
REVIEW_MODELS = [
    "mistralai/magistral-small-2509",   # Fast, efficient for quick reviews
    "qwen/qwen3-coder-30b",             # Coding specialist
    "qwen/qwen3-4b-thinking-2507"       # Deep reasoning
]

# Special keyword meaning "use currently loaded model in LM Studio"
# Used in: Multiple files for model parameter defaults
# When a function receives model="default", it means "use whatever is loaded"
DEFAULT_MODEL_KEYWORD = "default"

# ==============================================================================
# FILE PATHS - System and configuration paths
# ==============================================================================

# Default root directory for filesystem MCP operations
# Can be overridden by MCP_FILESYSTEM_ROOT environment variable
# Used in: lmstudio_bridge.py:373 (filesystem MCP allowed directory)
# Falls back to current working directory if not set
import os
DEFAULT_FILESYSTEM_ROOT = os.environ.get("MCP_FILESYSTEM_ROOT", os.getcwd())

# Path to LM Studio's MCP configuration file
# Used in: benchmark_hot_reload.py:35, mcp_client/discovery.py
DEFAULT_LMSTUDIO_MCP_PATH = "~/.lmstudio/mcp.json"

# ==============================================================================
# MCP SERVER CONFIGURATION - Commands and package names
# ==============================================================================

# Default command to run npm-based MCP servers
# Used in: lmstudio_bridge.py:369, tools/autonomous.py:240,308,492,637
DEFAULT_MCP_NPX_COMMAND = "npx"

# Default arguments for npx command (always use -y for non-interactive)
# Used when spawning MCP servers via npx
DEFAULT_MCP_NPX_ARGS = ["-y"]

# Official MCP package names - centralized to avoid typos and ensure consistency
# Used in: lmstudio_bridge.py:372, tools/autonomous.py:234,308-309,492-493,637-638
MCP_PACKAGES = {
    "filesystem": "@modelcontextprotocol/server-filesystem",
    "memory": "@modelcontextprotocol/server-memory",
    "github": "@modelcontextprotocol/server-github",
    "fetch": "mcp-server-fetch",
    "sqlite": "mcp-server-sqlite",
    "python": "mcp-server-python-interpreter"
}

# ==============================================================================
# MCP DISCOVERY CONFIGURATION - Where to find MCP configs
# ==============================================================================

# Search paths for MCP configuration files (in priority order)
# Used in: mcp_client/discovery.py:65-71
MCP_CONFIG_SEARCH_PATHS = [
    "~/.lmstudio/mcp.json",    # LM Studio config (HIGHEST PRIORITY for local LLM)
    ".mcp.json",                # Current directory (project-specific config)
    "~/.mcp.json",              # Home directory (user-wide config)
    "../.mcp.json"              # Parent directory (workspace config)
]

# Patterns to identify MCP packages in command arguments
# Used in: mcp_client/discovery.py:215 (package detection logic)
MCP_PACKAGE_PATTERNS = [
    "@modelcontextprotocol",   # Official MCP packages
    "mcp-server"               # Community MCP packages
]

# ==============================================================================
# STRUCTURED OUTPUT CONFIGURATION - JSON Schema support (LM Studio v0.3.32+)
# ==============================================================================

# Supported response format types for structured output
# Used in: llm/llm_client.py, tools/completions.py
STRUCTURED_OUTPUT_TYPES = ["json_schema", "json_object"]

# Default strict mode for JSON schema validation
# When True, LM Studio enforces strict schema compliance
# Used in: tools/completions.py (response_format building)
DEFAULT_JSON_SCHEMA_STRICT = True

# Maximum schema depth for validation (prevent deeply nested schemas)
# Used in: utils/schema_utils.py (schema validation)
MAX_JSON_SCHEMA_DEPTH = 10

# Maximum number of properties in a single schema object
# Used in: utils/schema_utils.py (schema validation)
MAX_JSON_SCHEMA_PROPERTIES = 100

# Warning message for models that may not support structured output
# Models < 7B parameters often produce invalid JSON
STRUCTURED_OUTPUT_MODEL_WARNING = (
    "Note: Not all models support structured output reliably. "
    "Models with < 7B parameters may produce invalid JSON. "
    "Recommended: Use models like Qwen 7B+, Llama 3 8B+, or Mistral 7B+."
)

# ==============================================================================
# VISION CONFIGURATION - Image/multimodal support (LM Studio v0.3.30+)
# ==============================================================================

# Supported image MIME types for vision models
# Used in: utils/image_utils.py, tools/vision.py
SUPPORTED_IMAGE_TYPES = [
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp"
]

# File extensions mapped to MIME types
# Used in: utils/image_utils.py (auto-detection)
IMAGE_EXTENSION_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp"
}

# Maximum image size in bytes (10 MB default)
# LM Studio may have its own limits; this is a client-side guard
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

# Maximum image dimension (width or height) in pixels
# Very large images may cause memory issues
MAX_IMAGE_DIMENSION = 4096

# Default detail level for vision requests
# "auto" lets the model decide, "low" for faster processing, "high" for detail
# Used in: tools/vision.py (image message building)
DEFAULT_VISION_DETAIL = "auto"

# Vision input types for auto-detection
# Used in: utils/image_utils.py (input format detection)
VISION_INPUT_TYPES = ["file_path", "url", "base64"]

# URL patterns for detecting image URLs
# Used in: utils/image_utils.py (URL detection)
IMAGE_URL_PATTERNS = [
    r"^https?://.*\.(jpg|jpeg|png|gif|webp)(\?.*)?$",
    r"^https?://.*",  # Any URL (model will validate)
]

# Base64 data URI prefix pattern
# Used in: utils/image_utils.py (base64 detection)
BASE64_DATA_URI_PREFIX = "data:image/"

# Warning message for models that may not support vision
VISION_MODEL_WARNING = (
    "Note: Not all models support vision/image input. "
    "Requires multimodal models like LLaVA, GPT-4V compatible, or Qwen-VL. "
    "Text-only models will return an error when given image input."
)
