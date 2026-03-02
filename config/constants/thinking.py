"""Extended thinking / reasoning configuration constants."""

__all__ = [
    "DEFAULT_THINKING_BUDGET_TOKENS",
    "THINKING_TAG_OPEN",
    "THINKING_TAG_CLOSE",
    "CHARS_PER_TOKEN_ESTIMATE",
    # OPP-21: Native Reasoning Parameter
    "REASONING_EFFORT_LOW",
    "REASONING_EFFORT_MEDIUM",
    "REASONING_EFFORT_HIGH",
    "VALID_REASONING_EFFORTS",
    "REASONING_EFFORT_TOKEN_MAP",
    "DEFAULT_REASONING_EFFORT",
]

# OPP-14: Extended Thinking Configuration
DEFAULT_THINKING_BUDGET_TOKENS = 4096

# Tags used by thinking models (QwQ, DeepSeek-R1, etc.)
THINKING_TAG_OPEN = "<think>"
THINKING_TAG_CLOSE = "</think>"

# Approximate characters per token for budget estimation
CHARS_PER_TOKEN_ESTIMATE = 4

# OPP-21: Native Reasoning Parameter — effort tiers
REASONING_EFFORT_LOW = "low"
REASONING_EFFORT_MEDIUM = "medium"
REASONING_EFFORT_HIGH = "high"
VALID_REASONING_EFFORTS = (REASONING_EFFORT_LOW, REASONING_EFFORT_MEDIUM, REASONING_EFFORT_HIGH)

# Effort → token budget mapping (used internally for effective_max_tokens)
REASONING_EFFORT_TOKEN_MAP: dict = {
    REASONING_EFFORT_LOW: 1024,
    REASONING_EFFORT_MEDIUM: 4096,  # Same as DEFAULT_THINKING_BUDGET_TOKENS
    REASONING_EFFORT_HIGH: 16384,
}

DEFAULT_REASONING_EFFORT = REASONING_EFFORT_MEDIUM
