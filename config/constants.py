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
NATIVE_MODELS_ENDPOINT = "/api/v1/models"  # LM Studio native REST API (richer than /v1/models)
ANTHROPIC_MESSAGES_ENDPOINT = "messages"  # Path segment for _get_endpoint (api_base already has /v1)

# Anthropic API Defaults
DEFAULT_ANTHROPIC_MAX_TOKENS = 4096  # Anthropic requires max_tokens (no default in protocol)
DEFAULT_ANTHROPIC_API_VERSION = "2023-06-01"  # anthropic-version header value

# LM Studio Native REST API Endpoints (Model Lifecycle)
LMS_LOAD_MODEL_ENDPOINT = "/api/v1/models/load"
LMS_UNLOAD_MODEL_ENDPOINT = "/api/v1/models/unload"
LMS_DOWNLOAD_MODEL_ENDPOINT = "/api/v1/download"
LMS_REST_LOAD_TIMEOUT = 120.0  # 2 minutes for model loading
LMS_REST_DEFAULT_TIMEOUT = 10.0  # 10 seconds for quick checks

# JIT (Just-In-Time) Model Loading TTL (seconds)
# Per-inference-request TTL: model auto-unloads after idle for this duration
JIT_TTL_DEFAULT = 1800       # 30 minutes for general requests
JIT_TTL_EMBEDDING = 900      # 15 minutes for embedding requests (shorter-lived)
JIT_TTL_AUTONOMOUS = 10800   # 3 hours for autonomous tasks (long-running)

# Timeout Configuration (seconds)
DEFAULT_REQUEST_TIMEOUT = 120.0
DEFAULT_CONNECTION_TIMEOUT = 10.0
DEFAULT_READ_TIMEOUT = 300.0
# Default timeout for LLM API calls via LLMClient
# Set to 58s to accommodate slower models (Magistral: 45-46s response time)
# Still safely under Claude Code's 60-second MCP timeout limit
# See: https://github.com/anthropics/claude-code/issues/7575
DEFAULT_LLM_TIMEOUT = 58

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
MAX_CONSECUTIVE_ERRORS = 3  # Abort autonomous loop after this many consecutive errors

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
VERSION = "4.0.0"
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

# ==============================================================================
# OPP-18: HEADLESS DEPLOYMENT (llmster) — Health Check Configuration
# ==============================================================================

# Timeout for health-check HTTP calls (seconds)
# Short by design — this is a liveness probe, not a data fetch
HEALTH_CHECK_TIMEOUT = 5.0

# LM Studio diagnostics endpoint (available in 0.4.x headless/GUI)
# Returns server type, version, uptime
DIAGNOSTICS_ENDPOINT = "/api/v1/diagnostics"

# LM Studio system status endpoint (fallback if diagnostics not available)
SYSTEM_STATUS_ENDPOINT = "/api/v1/system/status"

# HTTP response header that identifies the LM Studio server variant
# Value is "gui" or "headless" when present
SERVER_TYPE_HEADER = "x-lmstudio-server-type"

# Process name used by the llmster headless daemon
# Used as a last-resort process-name fallback for type detection
LLMSTER_PROCESS_NAME = "llmster"

# How often (seconds) to re-check server health in long-running contexts
HEALTH_CHECK_INTERVAL = 30.0

# Known server type string values returned by the diagnostics endpoint
SERVER_TYPE_GUI = "gui"
SERVER_TYPE_HEADLESS = "headless"

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

# ==============================================================================
# OPP-08: SMART MODEL SELECTION — Task-to-capability mapping and scoring weights
# ==============================================================================

# Maps task_type strings → ModelCapabilities attribute names
# Used in: model_registry/selector.py (SmartModelSelector._classify_task)
TASK_CAPABILITY_MAP: dict[str, str] = {
    "code_generation": "coding",
    "code_review": "coding",
    "coding": "coding",
    "summarization": "long_context",
    "long_document": "long_context",
    "reasoning": "reasoning",
    "analysis": "reasoning",
    "math": "reasoning",
    "tool_use": "tool_calling",
    "agents": "tool_calling",
    "function_calling": "tool_calling",
    "vision": "vision",
    "image_analysis": "vision",
    "multimodal": "vision",
}

# Scoring weights for smart model selection
# Used in: model_registry/selector.py (SmartModelSelector._score_model)
SELECTION_WEIGHT_CAPABILITY = 1.0   # Weight for the primary capability score
SELECTION_WEIGHT_CONFIDENCE = 1.0   # Weight for the confidence multiplier

# Fallback sort key when scores are tied
# Used in: model_registry/selector.py (SmartModelSelector.select)
SELECTION_FALLBACK_SORT_KEY = "model_id"

# Error code constants for MCP tool responses
# Used in: model_registry/selection_tool.py
SELECTION_ERROR_NO_MODELS = "no_models_available"
SELECTION_ERROR_INTERNAL = "selection_error"

# ==============================================================================
# OPP-12: SSE STREAMING CONFIGURATION
# ==============================================================================

# Sentinel value that signals the end of an SSE stream
# When the data field equals this value, streaming is complete
# Used in: llm/sse_parser.py, llm/llm_client.py streaming methods
SSE_DONE_SENTINEL = "[DONE]"

# Prefix used by SSE protocol for data lines
# Every SSE data line begins with this prefix followed by the payload
# Used in: llm/sse_parser.py (parse_sse_stream)
SSE_DATA_PREFIX = "data: "

# Timeout for streaming responses (seconds)
# Long streams (e.g. large code generation) can take several minutes
# This is separate from DEFAULT_LLM_TIMEOUT which is for non-streaming calls
# Used in: llm/llm_client.py streaming methods
STREAM_READ_TIMEOUT = 300.0

# ==============================================================================
# OPP-14: EXTENDED THINKING CONFIGURATION
# ==============================================================================

# Default thinking token budget (tokens allocated for reasoning)
# Used in: llm/llm_client.py thinking methods
DEFAULT_THINKING_BUDGET_TOKENS = 4096

# Minimum and maximum allowed thinking budget
MIN_THINKING_BUDGET_TOKENS = 128
MAX_THINKING_BUDGET_TOKENS = 32768

# Tags used by thinking models (QwQ, DeepSeek-R1, etc.)
THINKING_TAG_OPEN = "<think>"
THINKING_TAG_CLOSE = "</think>"

# Approximate characters per token for budget estimation
CHARS_PER_TOKEN_ESTIMATE = 4

# ==============================================================================
# OPP-10: FORMAT ADAPTER — 3-way API format routing
# ==============================================================================

# Canonical format identifiers for 3-way routing
# Used in: llm/format_adapter.py
FORMAT_OPENAI = "openai"
FORMAT_ANTHROPIC = "anthropic"
FORMAT_RESPONSES = "responses"

# All supported format identifiers (for validation)
SUPPORTED_API_FORMATS = [FORMAT_OPENAI, FORMAT_ANTHROPIC, FORMAT_RESPONSES]

# ==============================================================================
# OPP-17: DUAL-FORMAT AUTONOMOUS LOOP
# ==============================================================================

# Default API format for autonomous execution
# Used in: tools/dynamic_autonomous.py
DEFAULT_AUTONOMOUS_FORMAT = FORMAT_RESPONSES  # Current behavior preserved

# Maximum messages to keep in Anthropic autonomous loop before trimming
# Keeps initial user task + last N messages to prevent unbounded memory growth
# The Responses loop doesn't need this because LM Studio manages state server-side
MAX_ANTHROPIC_LOOP_MESSAGES = 100

# System prompt template for Anthropic-format autonomous execution
# Anthropic uses top-level system prompt, not a system message in the array
ANTHROPIC_AUTONOMOUS_SYSTEM_TEMPLATE = (
    "You are an autonomous agent with access to tools. "
    "Use the available tools to complete the task. "
    "When done, provide your final answer as plain text."
)

# ==============================================================================
# OPP-09: MULTI-MODAL AUTONOMOUS LOOPS
# ==============================================================================

# Maximum number of images allowed per autonomous loop input
# Used in: llm/multimodal_input.py (MultiModalInput)
MAX_IMAGES_PER_AUTONOMOUS_INPUT = 5

# Default detail level for images in autonomous loop inputs
# Reuses DEFAULT_VISION_DETAIL — "auto" lets the model decide
# Used in: llm/multimodal_input.py (MultiModalInput.to_chat_messages)
MULTIMODAL_DETAIL_DEFAULT = DEFAULT_VISION_DETAIL  # "auto"

# ==============================================================================
# OPP-15: CONVERSATION BRANCHING
# ==============================================================================

# Maximum depth of conversation tree (prevent runaway branching)
MAX_BRANCH_DEPTH = 50

# Maximum number of branches per conversation tree
MAX_BRANCHES_PER_TREE = 100

# Default branch name prefix
DEFAULT_BRANCH_PREFIX = "branch"
