"""Generic LLM client for LM Studio - works with ANY local LLM."""

from .exceptions import (
    LLMConnectionError,
    LLMError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
    LLMValidationError,
    ModelNotFoundError,
)
from .llm_client import LLMClient
from .message_manager import ConversationHistory, Message, MessageFormatter

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
