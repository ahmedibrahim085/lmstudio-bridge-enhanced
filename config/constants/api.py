"""API endpoints, format identifiers, HTTP status codes, and Anthropic defaults."""

__all__ = [
    "API_VERSION",
    "API_VERSION_SUPPORTED",
    "MODELS_ENDPOINT",
    "CHAT_COMPLETIONS_ENDPOINT",
    "COMPLETIONS_ENDPOINT",
    "EMBEDDINGS_ENDPOINT",
    "RESPONSES_ENDPOINT",
    "NATIVE_MODELS_ENDPOINT",
    "ANTHROPIC_MESSAGES_ENDPOINT",
    "LMS_LOAD_MODEL_ENDPOINT",
    "LMS_UNLOAD_MODEL_ENDPOINT",
    "LMS_DOWNLOAD_MODEL_ENDPOINT",
    "DEFAULT_ANTHROPIC_MAX_TOKENS",
    "DEFAULT_ANTHROPIC_API_VERSION",
    "FORMAT_OPENAI",
    "FORMAT_ANTHROPIC",
    "FORMAT_RESPONSES",
    "SUPPORTED_API_FORMATS",
    "DEFAULT_AUTONOMOUS_FORMAT",
    "MAX_ANTHROPIC_LOOP_MESSAGES",
    "ANTHROPIC_AUTONOMOUS_SYSTEM_TEMPLATE",
    "HTTP_OK",
    "HTTP_BAD_REQUEST",
    "HTTP_NOT_FOUND",
    "HTTP_TIMEOUT",
    "HTTP_RATE_LIMIT",
    "HTTP_SERVER_ERROR",
]

# API Endpoints
API_VERSION = "v1"
API_VERSION_SUPPORTED = "1.0"
MODELS_ENDPOINT = "/v1/models"
CHAT_COMPLETIONS_ENDPOINT = "/v1/chat/completions"
COMPLETIONS_ENDPOINT = "/v1/completions"
EMBEDDINGS_ENDPOINT = "/v1/embeddings"
RESPONSES_ENDPOINT = "/v1/responses"
NATIVE_MODELS_ENDPOINT = "/api/v1/models"  # LM Studio native REST API (richer than /v1/models)
ANTHROPIC_MESSAGES_ENDPOINT = "messages"  # Path segment for _get_endpoint (api_base already has /v1)

# LM Studio Native REST API Endpoints (Model Lifecycle)
LMS_LOAD_MODEL_ENDPOINT = "/api/v1/models/load"
LMS_UNLOAD_MODEL_ENDPOINT = "/api/v1/models/unload"
LMS_DOWNLOAD_MODEL_ENDPOINT = "/api/v1/download"

# Anthropic API Defaults
DEFAULT_ANTHROPIC_MAX_TOKENS = 4096  # Anthropic requires max_tokens (no default in protocol)
DEFAULT_ANTHROPIC_API_VERSION = "2023-06-01"  # anthropic-version header value

# OPP-10: Format Adapter — 3-way API format routing
FORMAT_OPENAI = "openai"
FORMAT_ANTHROPIC = "anthropic"
FORMAT_RESPONSES = "responses"
SUPPORTED_API_FORMATS = [FORMAT_OPENAI, FORMAT_ANTHROPIC, FORMAT_RESPONSES]

# OPP-17: Dual-format autonomous loop
DEFAULT_AUTONOMOUS_FORMAT = FORMAT_RESPONSES  # Current behavior preserved
MAX_ANTHROPIC_LOOP_MESSAGES = 100
ANTHROPIC_AUTONOMOUS_SYSTEM_TEMPLATE = (
    "You are an autonomous agent with access to tools. "
    "Use the available tools to complete the task. "
    "When done, provide your final answer as plain text."
)

# HTTP Status Codes
HTTP_OK = 200
HTTP_BAD_REQUEST = 400
HTTP_NOT_FOUND = 404
HTTP_TIMEOUT = 408
HTTP_RATE_LIMIT = 429
HTTP_SERVER_ERROR = 500
