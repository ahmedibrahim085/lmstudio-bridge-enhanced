"""Backward-compatibility shim — re-exports from core.exceptions.

Canonical location: core/exceptions.py
This file exists so existing ``from llm.exceptions import …`` still works.
"""

from core.exceptions import (  # noqa: F401
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
    "LLMConnectionError",
    "LLMResponseError",
    "ModelNotFoundError",
    "ModelMemoryError",
    "get_error_type",
]
