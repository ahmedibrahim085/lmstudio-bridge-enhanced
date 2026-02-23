"""Generic LLM client for LM Studio - works with ANY local LLM."""

from .llm_client import LLMClient
from .message_manager import (
    Message,
    ConversationHistory,
    MessageFormatter
)
from .exceptions import (
    LLMError,
    LLMTimeoutError,
    LLMRateLimitError,
    LLMValidationError,
    LLMConnectionError,
    LLMResponseError,
    ModelNotFoundError,
)

__all__ = [
    "LLMClient",
    "Message",
    "ConversationHistory",
    "MessageFormatter",
    "LLMError",
    "LLMTimeoutError",
    "LLMRateLimitError",
    "LLMValidationError",
    "LLMConnectionError",
    "LLMResponseError",
    "ModelNotFoundError",
]
