"""Exception hierarchy for LLM operations.

This module defines a comprehensive exception hierarchy for handling errors
in LLM operations, including model validation, connection errors, and
response handling.

All exceptions inherit from LLMError base class which provides:
- Original exception tracking
- Timestamp for error occurrence
- Context information for debugging
"""

from datetime import datetime, UTC
from typing import Optional, List


class LLMError(Exception):
    """Base exception for LLM-related errors.

    All LLM-specific exceptions inherit from this class. It provides
    common functionality for error tracking and debugging.

    Attributes:
        original_exception: The original exception that caused this error (if any)
        timestamp: When this error occurred
    """

    def __init__(self, message: str, original_exception: Optional[Exception] = None):
        """Initialize LLM error.

        Args:
            message: Human-readable error message
            original_exception: Original exception if this wraps another error
        """
        super().__init__(message)
        self.original_exception = original_exception
        self.timestamp = datetime.now(UTC)


class LLMTimeoutError(LLMError):
    """Raised when LLM request times out.

    This indicates that a request to the LLM API took too long to complete.
    Common causes:
    - Network latency
    - Model is overloaded
    - Request is too complex
    """
    pass


class LLMRateLimitError(LLMError):
    """Raised when LLM rate limit is exceeded.

    This indicates that too many requests were made to the LLM API
    in a short period of time.
    """
    pass


class LLMValidationError(LLMError):
    """Raised when LLM response validation fails.

    This indicates that the LLM response did not match expected format
    or constraints.
    """
    pass


class LLMConnectionError(LLMError):
    """Raised when LLM connection fails.

    This indicates that the connection to the LLM API could not be established.
    Common causes:
    - LM Studio not running
    - Wrong host/port configuration
    - Network issues
    - Firewall blocking connection
    """
    pass


class LLMResponseError(LLMError):
    """Raised when LLM response format is invalid.

    This indicates that the LLM returned a response that could not be parsed
    or did not match the expected structure.
    """
    pass


class ModelMemoryError(LLMError):
    """Raised when a model cannot be loaded due to insufficient memory.

    This indicates that the requested model requires more memory than is available.
    Common when trying to load large models (e.g., 70B+) on systems with limited RAM/VRAM.

    Attributes:
        model_name: Name of the model that couldn't be loaded
        required_memory: Estimated memory required (if known)
    """

    def __init__(self, model_name: str, required_memory: str = None, original_exception: Exception = None):
        """Initialize ModelMemoryError.

        Args:
            model_name: Name of the model that was requested
            required_memory: Estimated memory required (e.g., "117.19 GB")
            original_exception: Original exception if this wraps another error
        """
        self.model_name = model_name
        self.required_memory = required_memory

        if required_memory:
            message = (
                f"Model '{model_name}' cannot be loaded - requires approximately {required_memory} of memory. "
                f"Try a smaller model or free up system memory."
            )
        else:
            message = (
                f"Model '{model_name}' cannot be loaded due to insufficient memory. "
                f"Try a smaller model or free up system memory."
            )

        super().__init__(message, original_exception)


class ModelNotFoundError(LLMValidationError):
    """Raised when requested model is not available.

    This indicates that a specific model was requested but is not currently
    available in LM Studio. The error message includes a list of available
    models to help users correct the issue.

    Attributes:
        model_name: The name of the model that was not found
        available_models: List of models that are currently available
    """

    def __init__(self, model_name: str, available_models: List[str]):
        """Initialize ModelNotFoundError.

        Args:
            model_name: Name of the model that was requested
            available_models: List of models currently available in LM Studio
        """
        self.model_name = model_name
        self.available_models = available_models

        # Create helpful error message
        if available_models:
            available_str = ", ".join(available_models)
            message = (
                f"Model '{model_name}' not found. "
                f"Available models: {available_str}"
            )
        else:
            message = (
                f"Model '{model_name}' not found. "
                f"No models are currently available in LM Studio. "
                f"Please load a model first."
            )

        super().__init__(message)


# Exception hierarchy summary:
# LLMError (base)
#   ├── LLMTimeoutError (timeout during request)
#   ├── LLMRateLimitError (too many requests)
#   ├── LLMValidationError (validation failed)
#   │   └── ModelNotFoundError (specific model not available)
#   ├── LLMConnectionError (cannot connect to API)
#   ├── LLMResponseError (invalid response format)
#   └── ModelMemoryError (model too large for available memory)


__all__ = [
    "LLMError",
    "LLMTimeoutError",
    "LLMRateLimitError",
    "LLMValidationError",
    "LLMConnectionError",
    "LLMResponseError",
    "ModelNotFoundError",
    "ModelMemoryError",
]
