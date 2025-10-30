"""Generic LLM client for LM Studio - works with ANY local LLM."""

from .llm_client import LLMClient, AutonomousLLMClient
from .message_manager import (
    Message,
    ConversationHistory,
    ToolCallTracker,
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
    "AutonomousLLMClient",
    "Message",
    "ConversationHistory",
    "ToolCallTracker",
    "MessageFormatter",
    "LLMError",
    "LLMTimeoutError",
    "LLMRateLimitError",
    "LLMValidationError",
    "LLMConnectionError",
    "LLMResponseError",
    "ModelNotFoundError",
]
