"""Default model identifiers and role-to-model mappings."""

__all__ = [
    "DEFAULT_FALLBACK_MODEL",
    "DEFAULT_AUTONOMOUS_MODEL",
    "DEFAULT_REVIEW_MODEL",
    "DEFAULT_THINKING_MODEL",
    "DEFAULT_SMALL_MODEL",
    "DEFAULT_VISION_MODEL",
    "EXAMPLE_MODEL_NAME",
    "REVIEW_MODELS",
    "DEFAULT_MODEL_KEYWORD",
    "MODEL_ROLE_KEYWORDS",
]

# Default fallback model when no model is specified in API calls
DEFAULT_FALLBACK_MODEL = "qwen/qwen3-coder-next"

# Default model for autonomous execution tasks (coding, analysis, implementation)
DEFAULT_AUTONOMOUS_MODEL = "qwen/qwen3-coder-next"

# Default model for code review tasks (smaller, faster for review)
DEFAULT_REVIEW_MODEL = "mistralai/magistral-small-2509"

# Default model for thinking/reasoning tasks
DEFAULT_THINKING_MODEL = "qwen/qwen3-4b-thinking-2507"

# Default model for small/lightweight tasks
DEFAULT_SMALL_MODEL = "ibm/granite-4-h-tiny"

# Default model for vision/multimodal tasks
DEFAULT_VISION_MODEL = "qwen/qwen3-vl-8b"

# Example model name for documentation and docstrings
EXAMPLE_MODEL_NAME = "qwen/qwen3-coder-next"

# List of models to use for comprehensive code reviews
REVIEW_MODELS = [
    "mistralai/magistral-small-2509",   # Fast, efficient for quick reviews
    "qwen/qwen3-coder-next",            # Coding specialist
    "qwen/qwen3-4b-thinking-2507"       # Deep reasoning
]

# Special keyword meaning "use currently loaded model in LM Studio"
DEFAULT_MODEL_KEYWORD = "default"

# Keywords for classifying models into roles during test discovery
MODEL_ROLE_KEYWORDS: dict[str, list[str]] = {
    "chat": ["chat", "instruct", "-it-", "-it"],
    "reasoning": ["magistral", "deepseek-r1", "reasoning", "r1"],
    "coding": ["coder", "codestral", "starcoder", "deepseek-coder", "devstral"],
    "thinking": ["thinking", "qwq", "thought"],
    "small": ["tiny", "mini", "small", "1b-", "3b-", "4b-"],
    "vision": ["-vl-", "-vl", "vision", "llava", "multimodal"],
}
