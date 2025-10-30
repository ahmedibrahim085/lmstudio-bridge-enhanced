"""Tests for LLM exception hierarchy.

This module tests the exception classes defined in llm/exceptions.py,
ensuring they work correctly and provide useful error information.
"""

import pytest
from datetime import datetime, UTC
from llm.exceptions import (
    LLMError,
    LLMTimeoutError,
    LLMRateLimitError,
    LLMValidationError,
    LLMConnectionError,
    LLMResponseError,
    ModelNotFoundError,
)


def test_base_exception_stores_original():
    """Base exception should store original exception."""
    original = ValueError("original error")
    error = LLMError("wrapped error", original_exception=original)

    assert error.original_exception is original
    assert str(error) == "wrapped error"
    assert isinstance(error.timestamp, datetime)


def test_base_exception_without_original():
    """Base exception should work without original exception."""
    error = LLMError("standalone error")

    assert error.original_exception is None
    assert str(error) == "standalone error"
    assert isinstance(error.timestamp, datetime)


def test_timeout_error_inheritance():
    """LLMTimeoutError should inherit from LLMError."""
    error = LLMTimeoutError("timeout occurred")

    assert isinstance(error, LLMError)
    assert isinstance(error, LLMTimeoutError)
    assert str(error) == "timeout occurred"


def test_rate_limit_error_inheritance():
    """LLMRateLimitError should inherit from LLMError."""
    error = LLMRateLimitError("rate limit exceeded")

    assert isinstance(error, LLMError)
    assert isinstance(error, LLMRateLimitError)


def test_validation_error_inheritance():
    """LLMValidationError should inherit from LLMError."""
    error = LLMValidationError("validation failed")

    assert isinstance(error, LLMError)
    assert isinstance(error, LLMValidationError)


def test_connection_error_inheritance():
    """LLMConnectionError should inherit from LLMError."""
    error = LLMConnectionError("connection failed")

    assert isinstance(error, LLMError)
    assert isinstance(error, LLMConnectionError)


def test_response_error_inheritance():
    """LLMResponseError should inherit from LLMError."""
    error = LLMResponseError("invalid response")

    assert isinstance(error, LLMError)
    assert isinstance(error, LLMResponseError)


def test_model_not_found_includes_available():
    """ModelNotFoundError should include available models."""
    available = ["model1", "model2", "model3"]
    error = ModelNotFoundError("model4", available)

    assert error.model_name == "model4"
    assert error.available_models == available
    assert "model4" in str(error)
    assert "model1" in str(error)
    assert "Available models:" in str(error)


def test_model_not_found_with_empty_list():
    """ModelNotFoundError should handle empty available list."""
    error = ModelNotFoundError("model1", [])

    assert error.model_name == "model1"
    assert error.available_models == []
    assert "model1" in str(error)
    assert "No models are currently available" in str(error)
    assert "Please load a model first" in str(error)


def test_model_not_found_inheritance():
    """ModelNotFoundError should inherit from LLMValidationError."""
    error = ModelNotFoundError("model1", ["model2"])

    assert isinstance(error, LLMValidationError)
    assert isinstance(error, LLMError)
    assert isinstance(error, ModelNotFoundError)


def test_exception_can_be_raised_and_caught():
    """Exceptions should be raisable and catchable."""
    with pytest.raises(LLMError):
        raise LLMError("test error")

    with pytest.raises(ModelNotFoundError):
        raise ModelNotFoundError("test", ["available"])


def test_specific_exception_caught_by_base():
    """Specific exceptions should be caught by base class."""
    try:
        raise LLMTimeoutError("timeout")
    except LLMError as e:
        assert isinstance(e, LLMTimeoutError)
    else:
        pytest.fail("Exception not caught by base class")


def test_model_not_found_caught_by_validation_error():
    """ModelNotFoundError should be caught by LLMValidationError."""
    try:
        raise ModelNotFoundError("test", ["available"])
    except LLMValidationError as e:
        assert isinstance(e, ModelNotFoundError)
    else:
        pytest.fail("ModelNotFoundError not caught by LLMValidationError")


def test_timestamp_is_recent():
    """Exception timestamp should be recent."""
    before = datetime.now(UTC)
    error = LLMError("test")
    after = datetime.now(UTC)

    assert before <= error.timestamp <= after


def test_original_exception_preserved():
    """Original exception should be preserved in chain."""
    original = ValueError("original")
    wrapped = LLMConnectionError("wrapped", original_exception=original)

    assert wrapped.original_exception is original
    assert isinstance(wrapped.original_exception, ValueError)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
