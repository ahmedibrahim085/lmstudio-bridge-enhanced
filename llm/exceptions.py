"""Backward-compatibility shim — re-exports from core.exceptions.

Canonical location: core/exceptions.py
This file exists so existing ``from llm.exceptions import …`` still works.
"""

from core.exceptions import (  # noqa: F401
    LLMAuthenticationError,
    LLMConnectionError,
    LLMError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
    LLMValidationError,
    ModelMemoryError,
    ModelNotFoundError,
    get_error_type,
)

__all__ = [
    "LLMError",
    "LLMTimeoutError",
    "LLMRateLimitError",
    "LLMValidationError",
    "LLMAuthenticationError",
    "LLMConnectionError",
    "LLMResponseError",
    "ModelNotFoundError",
    "ModelMemoryError",
    "get_error_type",
]
