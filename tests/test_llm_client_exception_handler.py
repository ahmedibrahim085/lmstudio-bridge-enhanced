"""Tests for _handle_request_exception in llm/llm_client.py.

Covers every branch of the exception-conversion function:
  - requests.exceptions.Timeout          -> LLMTimeoutError
  - requests.exceptions.ConnectionError  -> LLMConnectionError
  - requests.exceptions.HTTPError 429    -> LLMRateLimitError
  - requests.exceptions.HTTPError 500    -> LLMResponseError
  - requests.exceptions.HTTPError 404    -> LLMResponseError
  - requests.exceptions.HTTPError other  -> LLMResponseError
  - requests.exceptions.RequestException -> LLMError
  - unexpected exception type            -> LLMError

Each test also verifies:
  - The raised exception is an instance of the correct custom type
  - The error message contains the `operation` string
  - `.original_exception` is set to the original exception object
"""

import sys
import os

import pytest
import requests
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from llm.llm_client import _handle_request_exception
from llm.exceptions import (
    LLMConnectionError,
    LLMError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_http_error(status_code: int | None) -> requests.exceptions.HTTPError:
    """Build a requests.HTTPError with a mock response object."""
    http_err = requests.exceptions.HTTPError("HTTP error")
    if status_code is not None:
        mock_response = MagicMock()
        mock_response.status_code = status_code
        http_err.response = mock_response
    else:
        http_err.response = None
    return http_err


# ---------------------------------------------------------------------------
# Timeout
# ---------------------------------------------------------------------------

class TestTimeoutBranch:
    """requests.exceptions.Timeout -> LLMTimeoutError"""

    def test_raises_llm_timeout_error(self):
        """Timeout exception maps to LLMTimeoutError."""
        original = requests.exceptions.Timeout("connection timed out")
        with pytest.raises(LLMTimeoutError):
            _handle_request_exception(original)

    def test_message_contains_operation(self):
        """Error message must contain the operation string."""
        original = requests.exceptions.Timeout("timed out")
        with pytest.raises(LLMTimeoutError) as exc_info:
            _handle_request_exception(original, operation="Chat completion")
        assert "Chat completion" in str(exc_info.value)

    def test_original_exception_is_set(self):
        """original_exception attribute must reference the source exception."""
        original = requests.exceptions.Timeout("timed out")
        with pytest.raises(LLMTimeoutError) as exc_info:
            _handle_request_exception(original)
        assert exc_info.value.original_exception is original

    def test_default_operation_label(self):
        """Default operation label 'LLM request' is included in message."""
        original = requests.exceptions.Timeout("timed out")
        with pytest.raises(LLMTimeoutError) as exc_info:
            _handle_request_exception(original)
        assert "LLM request" in str(exc_info.value)


# ---------------------------------------------------------------------------
# ConnectionError
# ---------------------------------------------------------------------------

class TestConnectionErrorBranch:
    """requests.exceptions.ConnectionError -> LLMConnectionError"""

    def test_raises_llm_connection_error(self):
        """ConnectionError maps to LLMConnectionError."""
        original = requests.exceptions.ConnectionError("refused")
        with pytest.raises(LLMConnectionError):
            _handle_request_exception(original)

    def test_message_contains_operation(self):
        original = requests.exceptions.ConnectionError("refused")
        with pytest.raises(LLMConnectionError) as exc_info:
            _handle_request_exception(original, operation="Text completion")
        assert "Text completion" in str(exc_info.value)

    def test_original_exception_is_set(self):
        original = requests.exceptions.ConnectionError("refused")
        with pytest.raises(LLMConnectionError) as exc_info:
            _handle_request_exception(original)
        assert exc_info.value.original_exception is original

    def test_message_mentions_lm_studio(self):
        """Message should hint that LM Studio needs to be running."""
        original = requests.exceptions.ConnectionError("refused")
        with pytest.raises(LLMConnectionError) as exc_info:
            _handle_request_exception(original)
        assert "LM Studio" in str(exc_info.value)


# ---------------------------------------------------------------------------
# HTTPError 429 (Rate Limit)
# ---------------------------------------------------------------------------

class TestHTTPError429Branch:
    """requests.exceptions.HTTPError 429 -> LLMRateLimitError"""

    def test_raises_llm_rate_limit_error(self):
        original = _make_http_error(429)
        with pytest.raises(LLMRateLimitError):
            _handle_request_exception(original)

    def test_message_contains_operation(self):
        original = _make_http_error(429)
        with pytest.raises(LLMRateLimitError) as exc_info:
            _handle_request_exception(original, operation="Generate embeddings")
        assert "Generate embeddings" in str(exc_info.value)

    def test_original_exception_is_set(self):
        original = _make_http_error(429)
        with pytest.raises(LLMRateLimitError) as exc_info:
            _handle_request_exception(original)
        assert exc_info.value.original_exception is original


# ---------------------------------------------------------------------------
# HTTPError 500 (Internal Server Error)
# ---------------------------------------------------------------------------

class TestHTTPError500Branch:
    """requests.exceptions.HTTPError 500 -> LLMResponseError"""

    def test_raises_llm_response_error(self):
        original = _make_http_error(500)
        with pytest.raises(LLMResponseError):
            _handle_request_exception(original)

    def test_message_contains_operation(self):
        original = _make_http_error(500)
        with pytest.raises(LLMResponseError) as exc_info:
            _handle_request_exception(original, operation="Create response")
        assert "Create response" in str(exc_info.value)

    def test_original_exception_is_set(self):
        original = _make_http_error(500)
        with pytest.raises(LLMResponseError) as exc_info:
            _handle_request_exception(original)
        assert exc_info.value.original_exception is original

    def test_message_contains_500(self):
        """Message should mention HTTP 500."""
        original = _make_http_error(500)
        with pytest.raises(LLMResponseError) as exc_info:
            _handle_request_exception(original)
        assert "500" in str(exc_info.value)


# ---------------------------------------------------------------------------
# HTTPError 404 (Not Found)
# ---------------------------------------------------------------------------

class TestHTTPError404Branch:
    """requests.exceptions.HTTPError 404 -> LLMResponseError"""

    def test_raises_llm_response_error(self):
        original = _make_http_error(404)
        with pytest.raises(LLMResponseError):
            _handle_request_exception(original)

    def test_message_contains_operation(self):
        original = _make_http_error(404)
        with pytest.raises(LLMResponseError) as exc_info:
            _handle_request_exception(original, operation="List models")
        assert "List models" in str(exc_info.value)

    def test_original_exception_is_set(self):
        original = _make_http_error(404)
        with pytest.raises(LLMResponseError) as exc_info:
            _handle_request_exception(original)
        assert exc_info.value.original_exception is original

    def test_message_contains_404(self):
        """Message should mention HTTP 404."""
        original = _make_http_error(404)
        with pytest.raises(LLMResponseError) as exc_info:
            _handle_request_exception(original)
        assert "404" in str(exc_info.value)


# ---------------------------------------------------------------------------
# HTTPError other status codes
# ---------------------------------------------------------------------------

class TestHTTPErrorOtherBranch:
    """requests.exceptions.HTTPError with non-special status -> LLMResponseError"""

    @pytest.mark.parametrize("status_code", [400, 403, 503])
    def test_raises_llm_response_error(self, status_code: int):
        original = _make_http_error(status_code)
        with pytest.raises(LLMResponseError):
            _handle_request_exception(original)

    def test_message_contains_operation(self):
        original = _make_http_error(503)
        with pytest.raises(LLMResponseError) as exc_info:
            _handle_request_exception(original, operation="Anthropic messages")
        assert "Anthropic messages" in str(exc_info.value)

    def test_original_exception_is_set(self):
        original = _make_http_error(400)
        with pytest.raises(LLMResponseError) as exc_info:
            _handle_request_exception(original)
        assert exc_info.value.original_exception is original

    def test_message_contains_status_code(self):
        """Message should embed the actual HTTP status code."""
        original = _make_http_error(503)
        with pytest.raises(LLMResponseError) as exc_info:
            _handle_request_exception(original)
        assert "503" in str(exc_info.value)

    def test_none_response_falls_through_to_other(self):
        """HTTPError with response=None lands in the 'else' branch."""
        original = _make_http_error(None)
        with pytest.raises(LLMResponseError):
            _handle_request_exception(original)


# ---------------------------------------------------------------------------
# RequestException (base class, not a sub-type covered above)
# ---------------------------------------------------------------------------

class TestRequestExceptionBranch:
    """requests.exceptions.RequestException -> LLMError"""

    def test_raises_llm_error(self):
        """Generic RequestException maps to base LLMError."""
        original = requests.exceptions.RequestException("generic network failure")
        with pytest.raises(LLMError):
            _handle_request_exception(original)

    def test_not_a_subclass_error(self):
        """Must NOT raise a more-specific subclass for plain RequestException."""
        original = requests.exceptions.RequestException("generic")
        with pytest.raises(LLMError) as exc_info:
            _handle_request_exception(original)
        # Confirm the type is exactly LLMError (not LLMTimeoutError etc.)
        assert type(exc_info.value) is LLMError

    def test_message_contains_operation(self):
        original = requests.exceptions.RequestException("generic")
        with pytest.raises(LLMError) as exc_info:
            _handle_request_exception(original, operation="Stream chat completion")
        assert "Stream chat completion" in str(exc_info.value)

    def test_original_exception_is_set(self):
        original = requests.exceptions.RequestException("generic")
        with pytest.raises(LLMError) as exc_info:
            _handle_request_exception(original)
        assert exc_info.value.original_exception is original


# ---------------------------------------------------------------------------
# Unexpected exception type (else branch)
# ---------------------------------------------------------------------------

class TestUnexpectedExceptionBranch:
    """Unexpected exception types -> LLMError with 'unexpected error' message"""

    def test_raises_llm_error_for_value_error(self):
        original = ValueError("something odd")
        with pytest.raises(LLMError):
            _handle_request_exception(original)

    def test_raises_llm_error_for_runtime_error(self):
        original = RuntimeError("unexpected")
        with pytest.raises(LLMError):
            _handle_request_exception(original)

    def test_message_contains_unexpected(self):
        """Message should include 'unexpected' for unknown error types."""
        original = ValueError("odd")
        with pytest.raises(LLMError) as exc_info:
            _handle_request_exception(original)
        assert "unexpected" in str(exc_info.value).lower()

    def test_message_contains_operation(self):
        original = RuntimeError("odd")
        with pytest.raises(LLMError) as exc_info:
            _handle_request_exception(original, operation="Get model info")
        assert "Get model info" in str(exc_info.value)

    def test_original_exception_is_set(self):
        original = TypeError("bad type")
        with pytest.raises(LLMError) as exc_info:
            _handle_request_exception(original)
        assert exc_info.value.original_exception is original


# ---------------------------------------------------------------------------
# NoReturn contract: function MUST always raise, never return normally
# ---------------------------------------------------------------------------

class TestNoReturnContract:
    """Verify _handle_request_exception always raises and never returns None."""

    @pytest.mark.parametrize("exc", [
        requests.exceptions.Timeout("t"),
        requests.exceptions.ConnectionError("c"),
        requests.exceptions.RequestException("r"),
        ValueError("v"),
    ])
    def test_always_raises(self, exc: Exception):
        """Every code path must raise an exception — never silently return."""
        with pytest.raises(LLMError):
            _handle_request_exception(exc)

    def test_http_errors_always_raise(self):
        """All HTTPError status codes must raise."""
        for code in (429, 500, 404, 400, 503):
            with pytest.raises(LLMResponseError if code != 429 else LLMRateLimitError):
                _handle_request_exception(_make_http_error(code))
