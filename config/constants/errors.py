"""Error messages, success messages, and warning strings."""

__all__ = [
    "ERROR_MODEL_NOT_FOUND",
    "ERROR_CONNECTION_FAILED",
    "ERROR_TIMEOUT",
    "ERROR_VALIDATION_FAILED",
    "ERROR_MCP_NOT_FOUND",
    "ERROR_NO_CHAT_RESPONSE",
    "ERROR_EMPTY_CHAT_RESPONSE",
    "ERROR_NO_TEXT_COMPLETION",
    "ERROR_EMPTY_TEXT_COMPLETION",
    "ERROR_STREAM_NOT_SUPPORTED",
    "ERROR_MESSAGES_NOT_LIST",
    "ERROR_TEMPERATURE_OUT_OF_RANGE",
    "ERROR_MAX_TOKENS_OUT_OF_RANGE",
    "ERROR_MIN_P_OUT_OF_RANGE",
    "ERROR_TOP_K_OUT_OF_RANGE",
    "ERROR_SSRF_BLOCKED_SCHEME",
    "ERROR_SSRF_BLOCKED_HOST",
    "SUCCESS_MODEL_LOADED",
    "SUCCESS_VALIDATION_PASSED",
    "SUCCESS_CACHE_HIT",
    "STRUCTURED_OUTPUT_MODEL_WARNING",
    "VISION_MODEL_WARNING",
]

# Error Messages
ERROR_MODEL_NOT_FOUND = "Model '{model}' not found. Available models: {available}"
ERROR_CONNECTION_FAILED = "Failed to connect to LM Studio at {url}"
ERROR_TIMEOUT = "Request timed out after {timeout} seconds"
ERROR_VALIDATION_FAILED = "Model validation failed: {reason}"
ERROR_MCP_NOT_FOUND = "MCP '{mcp}' not found in configuration"
ERROR_NO_CHAT_RESPONSE = "No response generated from chat completion (empty choices)"
ERROR_EMPTY_CHAT_RESPONSE = "Empty response content from chat completion model"
ERROR_NO_TEXT_COMPLETION = "No completion generated from text completion (empty choices)"
ERROR_EMPTY_TEXT_COMPLETION = "Empty completion content from text completion model"

# H-2: stream=True guard for create_response
ERROR_STREAM_NOT_SUPPORTED = (
    "stream=True is not supported in create_response. "
    "Use the stream_create_response tool for streaming responses."
)

# H-9: type validation after json.loads in anthropic_messages
ERROR_MESSAGES_NOT_LIST = (
    "messages must be a JSON array of message objects, got {actual_type}"
)

# H-10: Input validation bounds
ERROR_TEMPERATURE_OUT_OF_RANGE = (
    "temperature must be between {min} and {max}, got {value}"
)
ERROR_MAX_TOKENS_OUT_OF_RANGE = (
    "max_tokens must be between {min} and {max}, got {value}"
)

# Advanced sampling parameter errors (OPP-26)
ERROR_MIN_P_OUT_OF_RANGE = (
    "min_p must be between {min} and {max}, got {value}"
)
ERROR_TOP_K_OUT_OF_RANGE = (
    "top_k must be between {min} and {max}, got {value}"
)

# SSRF protection errors
ERROR_SSRF_BLOCKED_SCHEME = "URL scheme '{scheme}' not allowed. Only HTTP/HTTPS URLs are accepted for image fetching."
ERROR_SSRF_BLOCKED_HOST = "URL host '{host}' is blocked. Private/internal network addresses are not allowed for image fetching."

# Success Messages
SUCCESS_MODEL_LOADED = "Model '{model}' loaded successfully"
SUCCESS_VALIDATION_PASSED = "Model '{model}' validation passed"
SUCCESS_CACHE_HIT = "Cache hit for model '{model}'"

# Warning Messages
STRUCTURED_OUTPUT_MODEL_WARNING = (
    "Note: Not all models support structured output reliably. "
    "Models with < 7B parameters may produce invalid JSON. "
    "Recommended: Use models like Qwen 7B+, Llama 3 8B+, or Mistral 7B+."
)

VISION_MODEL_WARNING = (
    "Note: Not all models support vision/image input. "
    "Requires multimodal models like LLaVA, GPT-4V compatible, or Qwen-VL. "
    "Text-only models will return an error when given image input."
)
