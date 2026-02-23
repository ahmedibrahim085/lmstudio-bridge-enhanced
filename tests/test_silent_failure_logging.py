"""Tests for silent failure logging — fix bare except blocks with no logging.

Tests verify that:
- lms_helper.LMSRestClient.is_server_available() logs a WARNING on failure
- lms_helper.LMSRestClient.list_all_models() logs a WARNING (not debug) on failure
- mcp_health_check.MCPHealthChecker.ping_mcp() logs DEBUG on import/connect failure
- llm_client.LLMClient.supports_native_mcp() logs WARNING on failure
- llm_client.LLMClient.list_models_enriched() logs WARNING (not debug) on failure
"""
import logging
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# lms_helper — LMSRestClient
# ---------------------------------------------------------------------------

class TestLmsHelperLogging:
    """Verify LMSRestClient logs on failure instead of silently returning."""

    def _make_rest_client(self):
        """Build a LMSRestClient with a mocked httpx._client."""
        from utils.lms_helper import LMSRestClient
        client = LMSRestClient.__new__(LMSRestClient)
        client.base_url = "http://localhost:1234"
        client._models_endpoint = "/api/v1/models"
        client._default_timeout = 5.0
        client._models_cache = None
        client._models_cache_time = 0.0
        mock_http = MagicMock()
        client._client = mock_http
        return client, mock_http

    def test_is_server_available_logs_warning_on_failure(self, caplog):
        """is_server_available() must log a WARNING when the HTTP call raises."""
        client, mock_http = self._make_rest_client()
        mock_http.get.side_effect = ConnectionError("connection refused")

        with caplog.at_level(logging.WARNING, logger="utils.lms_helper"):
            result = client.is_server_available()

        assert result is False
        warning_messages = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
        assert warning_messages, (
            "Expected at least one WARNING log from is_server_available() on failure, got none. "
            f"All records: {[(r.levelno, r.message) for r in caplog.records]}"
        )
        # The message should reference availability or the check
        combined = " ".join(warning_messages).lower()
        assert any(kw in combined for kw in ("availab", "check", "server", "failed")), (
            f"WARNING message doesn't mention the right context. Got: {warning_messages}"
        )

    def test_list_all_models_logs_warning_on_failure(self, caplog):
        """list_all_models() must log a WARNING (not just DEBUG) when HTTP raises."""
        client, mock_http = self._make_rest_client()
        mock_http.get.side_effect = ConnectionError("connection refused")

        with caplog.at_level(logging.WARNING, logger="utils.lms_helper"):
            result = client.list_all_models()

        assert result is None
        warning_messages = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
        assert warning_messages, (
            "Expected at least one WARNING log from list_all_models() on failure, got none. "
            f"All records: {[(r.levelno, r.message) for r in caplog.records]}"
        )

    def test_is_server_available_exc_info_present(self, caplog):
        """is_server_available() warning must carry exc_info so stack trace is available."""
        client, mock_http = self._make_rest_client()
        mock_http.get.side_effect = RuntimeError("unexpected")

        with caplog.at_level(logging.WARNING, logger="utils.lms_helper"):
            client.is_server_available()

        warning_records = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert warning_records, "No WARNING record found"
        # exc_info is stored as exc_info attribute on the LogRecord; when set,
        # exc_text is populated after formatting.
        record = warning_records[0]
        assert record.exc_info is not None, (
            "Expected exc_info=True on the WARNING record so stack trace is captured. "
            "Did you forget exc_info=True in logger.warning()?"
        )


# ---------------------------------------------------------------------------
# mcp_health_check — MCPHealthChecker.ping_mcp
# ---------------------------------------------------------------------------

class TestMcpHealthCheckLogging:
    """Verify ping_mcp() logs on import/connect failure instead of silently returning."""

    @pytest.mark.asyncio
    async def test_ping_mcp_logs_debug_on_import_failure(self, caplog):
        """ping_mcp() must log at DEBUG level when MCP module import fails."""
        from utils.mcp_health_check import MCPHealthChecker
        checker = MCPHealthChecker()

        # Force the import inside ping_mcp to fail
        with patch.dict("sys.modules", {"mcp_client.connection": None}):
            with caplog.at_level(logging.DEBUG, logger="utils.mcp_health_check"):
                result = await checker.ping_mcp("test_mcp", {"command": "node", "args": []})

        assert result is False
        debug_messages = [r.message for r in caplog.records if r.levelno >= logging.DEBUG]
        assert debug_messages, (
            "Expected at least one DEBUG log from ping_mcp() on import failure, got none. "
            f"All records: {[(r.levelno, r.message) for r in caplog.records]}"
        )

    @pytest.mark.asyncio
    async def test_ping_mcp_logs_warning_on_connect_failure(self, caplog):
        """ping_mcp() inner except must log a WARNING when connection fails."""
        from utils.mcp_health_check import MCPHealthChecker
        checker = MCPHealthChecker()

        # Create a mock MCPConnection that raises on connect
        mock_conn = MagicMock()
        mock_conn.connect = AsyncMock(side_effect=Exception("connection refused"))
        mock_conn_class = MagicMock(return_value=mock_conn)

        mock_module = MagicMock()
        mock_module.MCPConnection = mock_conn_class

        with patch.dict("sys.modules", {"mcp_client.connection": mock_module}):
            with patch("utils.mcp_health_check.MCPConnection", mock_conn_class, create=True):
                with caplog.at_level(logging.WARNING, logger="utils.mcp_health_check"):
                    result = await checker.ping_mcp("test_mcp", {"command": "node", "args": []})

        assert result is False
        # NOTE: the inner except (line 180/183) should now log a warning
        warning_messages = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
        assert warning_messages, (
            "Expected at least one WARNING log from ping_mcp() on connection failure, got none. "
            f"All records: {[(r.levelno, r.message) for r in caplog.records]}"
        )


# ---------------------------------------------------------------------------
# llm_client — LLMClient
# ---------------------------------------------------------------------------

class TestLLMClientLogging:
    """Verify LLMClient internal methods log on failure."""

    def _make_client(self):
        """Construct LLMClient with mocked config."""
        with patch("llm.llm_client.get_config") as mock_cfg:
            mock_cfg.return_value.lmstudio.api_base = "http://localhost:1234/v1"
            mock_cfg.return_value.lmstudio.default_model = "test-model"
            from llm.llm_client import LLMClient
            client = LLMClient()
        return client

    def test_supports_native_mcp_logs_warning_on_failure(self, caplog):
        """supports_native_mcp() must log a WARNING when the HTTP call fails."""
        client = self._make_client()
        # Force a fresh check (bypass cache)
        client._native_mcp_supported = None
        client._native_mcp_checked_at = 0.0
        client.session.get = MagicMock(side_effect=Exception("connection refused"))

        with caplog.at_level(logging.WARNING, logger="llm.llm_client"):
            result = client.supports_native_mcp()

        assert result is False
        warning_messages = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
        assert warning_messages, (
            "Expected at least one WARNING log from supports_native_mcp() on failure, got none. "
            f"All records: {[(r.levelno, r.message) for r in caplog.records]}"
        )
        combined = " ".join(warning_messages).lower()
        assert any(kw in combined for kw in ("mcp", "native", "check", "failed")), (
            f"WARNING message doesn't reference MCP check. Got: {warning_messages}"
        )

    def test_supports_native_mcp_exc_info_present(self, caplog):
        """supports_native_mcp() warning must include exc_info for stack traces."""
        client = self._make_client()
        client._native_mcp_supported = None
        client._native_mcp_checked_at = 0.0
        client.session.get = MagicMock(side_effect=RuntimeError("unexpected"))

        with caplog.at_level(logging.WARNING, logger="llm.llm_client"):
            client.supports_native_mcp()

        warning_records = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert warning_records, "No WARNING record found"
        assert warning_records[0].exc_info is not None, (
            "Expected exc_info=True on the WARNING record. Did you forget exc_info=True?"
        )

    def test_list_models_enriched_logs_warning_on_failure(self, caplog):
        """list_models_enriched() must log WARNING (not just DEBUG) when native API fails."""
        client = self._make_client()

        # Make native /api/v1/models fail, but /v1/models succeed (for fallback)
        fallback_resp = MagicMock()
        fallback_resp.raise_for_status = MagicMock()
        fallback_resp.json.return_value = {"data": [{"id": "test-model"}]}

        native_resp = MagicMock()
        native_resp.raise_for_status.side_effect = Exception("404 not found")

        def fake_get(url, **kwargs):
            if "api/v1/models" in url:
                raise Exception("native API unavailable")
            return fallback_resp

        client.session.get = MagicMock(side_effect=fake_get)

        with caplog.at_level(logging.WARNING, logger="llm.llm_client"):
            result = client.list_models_enriched()

        # Should still return fallback data
        assert result == [{"model_id": "test-model"}]

        warning_messages = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
        assert warning_messages, (
            "Expected at least one WARNING log from list_models_enriched() on native API failure, "
            f"got none. All records: {[(r.levelno, r.message) for r in caplog.records]}"
        )

    def test_list_models_enriched_exc_info_present(self, caplog):
        """list_models_enriched() warning must include exc_info for stack traces."""
        client = self._make_client()

        fallback_resp = MagicMock()
        fallback_resp.raise_for_status = MagicMock()
        fallback_resp.json.return_value = {"data": []}

        def fake_get(url, **kwargs):
            if "api/v1/models" in url:
                raise RuntimeError("unexpected native API error")
            return fallback_resp

        client.session.get = MagicMock(side_effect=fake_get)

        with caplog.at_level(logging.WARNING, logger="llm.llm_client"):
            client.list_models_enriched()

        warning_records = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert warning_records, "No WARNING record found"
        assert warning_records[0].exc_info is not None, (
            "Expected exc_info=True on the WARNING record. Did you forget exc_info=True?"
        )
