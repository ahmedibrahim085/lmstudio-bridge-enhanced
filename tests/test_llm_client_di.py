"""Tests for LLMClient dependency injection — session parameter and ownership (R-1)."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _mock_config():
    """Return a mock get_config that avoids real HTTP."""
    mock = MagicMock()
    mock.return_value.lmstudio.api_base = "http://localhost:1234/v1"
    mock.return_value.lmstudio.default_model = "test-model"
    return mock


class TestLLMClientSessionDI:
    """Tests for optional session injection in LLMClient.__init__."""

    @pytest.mark.unit
    def test_default_creates_real_session(self):
        """When no session is provided, LLMClient creates a real requests.Session and owns it."""
        import requests
        with patch("llm.llm_client.get_config", _mock_config()):
            from llm.llm_client import LLMClient
            client = LLMClient()
            assert isinstance(client.session, requests.Session)
            assert client._owns_session is True
            client.close()

    @pytest.mark.unit
    def test_injected_session_used(self):
        """When a session is provided, LLMClient uses it and does not own it."""
        mock_session = MagicMock()
        with patch("llm.llm_client.get_config", _mock_config()):
            from llm.llm_client import LLMClient
            client = LLMClient(session=mock_session)
            assert client.session is mock_session
            assert client._owns_session is False

    @pytest.mark.unit
    def test_injected_session_no_adapter_setup(self):
        """When a session is provided, HTTPAdapter is NOT instantiated."""
        mock_session = MagicMock()
        with patch("llm.llm_client.get_config", _mock_config()), \
             patch("llm.llm_client.HTTPAdapter") as mock_adapter:
            from llm.llm_client import LLMClient
            LLMClient(session=mock_session)
            mock_adapter.assert_not_called()

    @pytest.mark.unit
    def test_none_session_creates_real(self):
        """Explicitly passing session=None creates a real session (same as default)."""
        import requests
        with patch("llm.llm_client.get_config", _mock_config()):
            from llm.llm_client import LLMClient
            client = LLMClient(session=None)
            assert isinstance(client.session, requests.Session)
            assert client._owns_session is True
            client.close()

    @pytest.mark.unit
    def test_injected_session_routes_http(self):
        """Injected session is actually used for HTTP calls, not just stored."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": [{"message": {"content": "hi"}}]}
        mock_response.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_response

        with patch("llm.llm_client.get_config", _mock_config()):
            from llm.llm_client import LLMClient
            client = LLMClient(session=mock_session)
            try:
                client.chat_completion(messages=[{"role": "user", "content": "test"}])
            except Exception:
                pass  # May fail due to response parsing, that's OK
            assert mock_session.post.called, "Injected session must be used for HTTP calls"

    @pytest.mark.unit
    def test_close_skips_injected_session(self):
        """close() does NOT close an injected session (_owns_session=False)."""
        mock_session = MagicMock()
        with patch("llm.llm_client.get_config", _mock_config()):
            from llm.llm_client import LLMClient
            client = LLMClient(session=mock_session)
            client.close()
            mock_session.close.assert_not_called()

    @pytest.mark.unit
    def test_close_closes_owned_session(self):
        """close() DOES close a session when _owns_session=True."""
        with patch("llm.llm_client.get_config", _mock_config()):
            from llm.llm_client import LLMClient
            client = LLMClient()
            real_session = client.session
            with patch.object(real_session, 'close') as mock_close:
                client.close()
                mock_close.assert_called_once()

    @pytest.mark.unit
    def test_context_manager_respects_ownership(self):
        """Context manager exit does NOT close an injected session."""
        mock_session = MagicMock()
        with patch("llm.llm_client.get_config", _mock_config()):
            from llm.llm_client import LLMClient
            with LLMClient(session=mock_session) as client:
                assert client.session is mock_session
            mock_session.close.assert_not_called()
