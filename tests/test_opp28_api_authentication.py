"""Tests for OPP-28: API Authentication for LM Studio Bridge Enhanced.

Covers:
  - api_key constructor param sets Authorization: Bearer header
  - LMS_API_KEY env var as fallback
  - Constructor wins over env var
  - Empty / None / whitespace-only key → no header set
  - HTTP 401 → LLMAuthenticationError
  - Whitespace stripped from key
  - API key never appears in repr/str
  - Very long key accepted
  - Auth constants exist in config.constants
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_config(
    api_base: str = "http://localhost:1234/v1",
    default_model: str = "test-model",
) -> MagicMock:
    mock = MagicMock()
    mock.return_value.lmstudio.api_base = api_base
    mock.return_value.lmstudio.default_model = default_model
    return mock


def _make_http_error(status_code: int) -> requests.exceptions.HTTPError:
    """Build an HTTPError with the given status code."""
    err = requests.exceptions.HTTPError(f"HTTP {status_code}")
    mock_response = MagicMock()
    mock_response.status_code = status_code
    err.response = mock_response
    return err


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _mock_config():
    with patch("llm.http_transport.get_config", _make_mock_config()):
        yield


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

class TestApiKeyConstructor:
    """Constructor api_key param sets Authorization header on the session."""

    @pytest.mark.unit
    def test_api_key_sets_authorization_header(self):
        """api_key='sk-test' → session headers contain 'Authorization: Bearer sk-test'."""
        from llm.http_transport import HTTPTransport

        transport = HTTPTransport(api_key="sk-test")
        assert transport.session.headers["Authorization"] == "Bearer sk-test"
        transport.close()

    @pytest.mark.unit
    def test_api_key_from_env_var(self, monkeypatch):
        """LMS_API_KEY env var is picked up when no constructor api_key given."""
        monkeypatch.setenv("LMS_API_KEY", "sk-from-env")
        from llm.http_transport import HTTPTransport

        transport = HTTPTransport()
        assert transport.session.headers["Authorization"] == "Bearer sk-from-env"
        transport.close()

    @pytest.mark.unit
    def test_api_key_constructor_wins_over_env(self, monkeypatch):
        """Constructor api_key takes precedence over LMS_API_KEY env var."""
        monkeypatch.setenv("LMS_API_KEY", "sk-from-env")
        from llm.http_transport import HTTPTransport

        transport = HTTPTransport(api_key="sk-constructor")
        assert transport.session.headers["Authorization"] == "Bearer sk-constructor"
        transport.close()


# ---------------------------------------------------------------------------
# Negative
# ---------------------------------------------------------------------------

class TestApiKeyAbsent:
    """Empty or None key must not set any Authorization header."""

    @pytest.mark.unit
    def test_empty_api_key_no_header(self):
        """api_key='' (empty string) → no Authorization header set."""
        from llm.http_transport import HTTPTransport

        transport = HTTPTransport(api_key="")
        assert "Authorization" not in transport.session.headers
        transport.close()

    @pytest.mark.unit
    def test_401_response_raises_authentication_error(self):
        """HTTP 401 response → LLMAuthenticationError is raised."""
        from llm.http_transport import handle_request_exception
        from llm.exceptions import LLMAuthenticationError

        http_err = _make_http_error(401)
        with pytest.raises(LLMAuthenticationError):
            handle_request_exception(http_err, operation="Chat completion")


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestApiKeyEdgeCases:
    """Edge-case behaviour for whitespace, None, repr masking."""

    @pytest.mark.unit
    def test_api_key_whitespace_stripped(self):
        """api_key='  sk-test  ' is stripped to 'sk-test' in the header."""
        from llm.http_transport import HTTPTransport

        transport = HTTPTransport(api_key="  sk-test  ")
        assert transport.session.headers["Authorization"] == "Bearer sk-test"
        transport.close()

    @pytest.mark.unit
    def test_api_key_none_no_header(self, monkeypatch):
        """api_key=None (default) with no env var → no Authorization header."""
        monkeypatch.delenv("LMS_API_KEY", raising=False)
        from llm.http_transport import HTTPTransport

        transport = HTTPTransport(api_key=None)
        assert "Authorization" not in transport.session.headers
        transport.close()

    @pytest.mark.unit
    def test_api_key_not_in_repr(self):
        """API key value MUST NOT appear in repr() or str() of the transport."""
        from llm.http_transport import HTTPTransport

        transport = HTTPTransport(api_key="super-secret-key-1234")
        assert "super-secret-key-1234" not in repr(transport)
        assert "super-secret-key-1234" not in str(transport)
        transport.close()


# ---------------------------------------------------------------------------
# Boundary
# ---------------------------------------------------------------------------

class TestApiKeyBoundary:
    """Boundary conditions: very long key, constants import."""

    @pytest.mark.unit
    def test_very_long_api_key_accepted(self):
        """A 1000-character API key is accepted without any validation error."""
        long_key = "sk-" + "x" * 997  # total 1000 chars
        from llm.http_transport import HTTPTransport

        transport = HTTPTransport(api_key=long_key)
        assert transport.session.headers["Authorization"] == f"Bearer {long_key}"
        transport.close()

    @pytest.mark.unit
    def test_auth_constants_exist(self):
        """ENV_LMS_API_KEY and AUTH_HEADER_PREFIX must be importable from config.constants."""
        from config.constants import ENV_LMS_API_KEY, AUTH_HEADER_PREFIX

        assert ENV_LMS_API_KEY == "LMS_API_KEY"
        assert AUTH_HEADER_PREFIX == "Bearer"
