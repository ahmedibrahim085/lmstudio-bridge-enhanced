"""Tests for resource cleanup -- BUG 1 fix (resource leak).

Covers:
- LLMClient.close() releases HTTP session
- LLMClient context manager protocol (__enter__/__exit__)
- close() idempotency (safe to call twice)
- image_utils._close_http_session() nullifies module-level session
- _close_http_session() no-ops safely when session is None
"""
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# LLMClient resource cleanup
# ---------------------------------------------------------------------------

class TestLLMClientResourceCleanup:
    """Verify LLMClient properly closes its HTTP session."""

    def _make_client(self, mock_config):
        """Helper: create LLMClient with mocked config."""
        mock_config.return_value.lmstudio.api_base = "http://localhost:1234/v1"
        mock_config.return_value.lmstudio.default_model = "test-model"
        # Import inside helper so mock is active at import time
        from llm.llm_client import LLMClient
        return LLMClient()

    def test_close_calls_session_close(self):
        """close() must call session.close() exactly once."""
        with patch("llm.llm_client.get_config") as mock_config:
            client = self._make_client(mock_config)
            mock_session = MagicMock()
            client.session = mock_session

            client.close()

            mock_session.close.assert_called_once()

    def test_context_manager_closes_session_on_exit(self):
        """Using LLMClient as a context manager closes the session on __exit__."""
        with patch("llm.llm_client.get_config") as mock_config:
            mock_config.return_value.lmstudio.api_base = "http://localhost:1234/v1"
            mock_config.return_value.lmstudio.default_model = "test-model"
            from llm.llm_client import LLMClient

            mock_session = MagicMock()
            with LLMClient() as client:
                client.session = mock_session
            # After the with-block the session must have been closed
            mock_session.close.assert_called_once()

    def test_context_manager_returns_self(self):
        """__enter__ must return the client instance."""
        with patch("llm.llm_client.get_config") as mock_config:
            mock_config.return_value.lmstudio.api_base = "http://localhost:1234/v1"
            mock_config.return_value.lmstudio.default_model = "test-model"
            from llm.llm_client import LLMClient

            client = LLMClient()
            result = client.__enter__()
            client.close()  # cleanup
            assert result is client

    def test_close_is_idempotent(self):
        """Calling close() twice must not raise."""
        with patch("llm.llm_client.get_config") as mock_config:
            client = self._make_client(mock_config)
            # First close
            client.close()
            # Second close must not raise
            client.close()

    def test_close_when_session_is_none(self):
        """close() must not raise when self.session is already None."""
        with patch("llm.llm_client.get_config") as mock_config:
            client = self._make_client(mock_config)
            client.session = None
            # Must not raise
            client.close()

    def test_exit_returns_false(self):
        """__exit__ must return False (exceptions not suppressed)."""
        with patch("llm.llm_client.get_config") as mock_config:
            mock_config.return_value.lmstudio.api_base = "http://localhost:1234/v1"
            mock_config.return_value.lmstudio.default_model = "test-model"
            from llm.llm_client import LLMClient

            client = LLMClient()
            result = client.__exit__(None, None, None)
            assert result is False

    def test_context_manager_closes_on_exception(self):
        """Session must be closed even when an exception occurs inside the with-block."""
        with patch("llm.llm_client.get_config") as mock_config:
            mock_config.return_value.lmstudio.api_base = "http://localhost:1234/v1"
            mock_config.return_value.lmstudio.default_model = "test-model"
            from llm.llm_client import LLMClient

            mock_session = MagicMock()
            with pytest.raises(RuntimeError):
                with LLMClient() as client:
                    client.session = mock_session
                    raise RuntimeError("something went wrong")
            mock_session.close.assert_called_once()


# ---------------------------------------------------------------------------
# image_utils module-level session cleanup
# ---------------------------------------------------------------------------

class TestImageUtilsSessionCleanup:
    """Verify image_utils module session cleanup."""

    def test_close_http_session_closes_and_nullifies(self):
        """_close_http_session() must close the session and set _http_session to None."""
        import utils.image_utils as img
        mock_session = MagicMock()
        img._http_session = mock_session

        img._close_http_session()

        mock_session.close.assert_called_once()
        assert img._http_session is None

    def test_close_http_session_noop_when_none(self):
        """_close_http_session() must be a no-op when _http_session is None."""
        import utils.image_utils as img
        img._http_session = None

        # Must not raise
        img._close_http_session()

        assert img._http_session is None

    def test_close_http_session_is_idempotent(self):
        """Calling _close_http_session() twice must not raise."""
        import utils.image_utils as img
        mock_session = MagicMock()
        img._http_session = mock_session

        img._close_http_session()
        img._close_http_session()  # second call: _http_session is None, must not raise

    def test_close_http_session_exported_in_all(self):
        """_close_http_session must be present in utils.image_utils namespace."""
        import utils.image_utils as img
        assert hasattr(img, "_close_http_session"), (
            "_close_http_session not found in utils.image_utils"
        )
        assert callable(img._close_http_session)
