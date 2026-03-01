"""Extended thinking / reasoning configuration constants."""

__all__ = [
    "DEFAULT_THINKING_BUDGET_TOKENS",
    "THINKING_TAG_OPEN",
    "THINKING_TAG_CLOSE",
    "CHARS_PER_TOKEN_ESTIMATE",
]

# OPP-14: Extended Thinking Configuration
DEFAULT_THINKING_BUDGET_TOKENS = 4096

# Tags used by thinking models (QwQ, DeepSeek-R1, etc.)
THINKING_TAG_OPEN = "<think>"
THINKING_TAG_CLOSE = "</think>"

# Approximate characters per token for budget estimation
CHARS_PER_TOKEN_ESTIMATE = 4
