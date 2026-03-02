"""Tests for OPP-16: Native MCP pass-through via API."""

import pytest
from unittest.mock import patch, MagicMock
import requests

from llm.llm_client import LLMClient
from llm.exceptions import LLMResponseError, LLMTimeoutError


@pytest.fixture
def client():
    """Create an LLMClient with mocked config."""
    with patch("llm.http_transport.get_config") as mock_config:
        mock_config.return_value.lmstudio.api_base = "http://localhost:1234"
        mock_config.return_value.lmstudio.default_model = "test-model"
        c = LLMClient()
    return c


@pytest.fixture
def mock_session(client):
    """Mock the client's HTTP session."""
    mock = MagicMock()
    client.session = mock
    return mock


class TestSupportsNativeMCP:
    """Tests for supports_native_mcp() feature detection."""

    @pytest.mark.xfail(reason="API contract provisional — verify against LM Studio 0.4.3+")
    def test_supports_native_mcp_true(self, client, mock_session):
        """Server returns mcp capability -> True."""
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"capabilities": {"mcp": True}}
        resp.raise_for_status = MagicMock()
        mock_session.get.return_value = resp

        assert client.supports_native_mcp() is True

    @pytest.mark.xfail(reason="API contract provisional — verify against LM Studio 0.4.3+")
    def test_supports_native_mcp_false(self, client, mock_session):
        """Server lacks mcp capability -> False."""
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"capabilities": {}}
        resp.raise_for_status = MagicMock()
        mock_session.get.return_value = resp

        assert client.supports_native_mcp() is False

    def test_supports_native_mcp_connection_error(self, client, mock_session):
        """Connection error -> False (safe default)."""
        mock_session.get.side_effect = requests.exceptions.ConnectionError("refused")

        assert client.supports_native_mcp() is False

    def test_supports_native_mcp_caching(self, client, mock_session):
        """Second call within TTL returns cached result without HTTP."""
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"capabilities": {"mcp": True}}
        resp.raise_for_status = MagicMock()
        mock_session.get.return_value = resp

        # First call hits the network
        result1 = client.supports_native_mcp()
        # Second call should use cache
        result2 = client.supports_native_mcp()

        assert result1 == result2
        # Should only have made ONE GET request (cached on second call)
        assert mock_session.get.call_count == 1


class TestChatCompletionWithNativeMCP:
    """Tests for chat_completion_with_native_mcp()."""

    def test_native_mcp_passes_server_config(self, client, mock_session):
        """MCP server config included in API payload."""
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"choices": [{"message": {"content": "done"}}]}
        resp.raise_for_status = MagicMock()
        mock_session.post.return_value = resp

        mcp_servers = [{"name": "fs", "transport": "stdio", "command": "npx", "args": ["-y", "@anthropic/mcp-fs"]}]

        client.chat_completion_with_native_mcp(
            messages=[{"role": "user", "content": "List files"}],
            mcp_servers=mcp_servers,
        )

        call_kwargs = mock_session.post.call_args
        payload = call_kwargs[1]["json"] if "json" in call_kwargs[1] else call_kwargs.kwargs["json"]
        assert "mcp_servers" in payload
        assert payload["mcp_servers"][0]["name"] == "fs"

    def test_native_mcp_tool_execution(self, client, mock_session):
        """Server-side tool execution response."""
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "choices": [{"message": {"content": "Files: a.txt, b.txt"}}]
        }
        resp.raise_for_status = MagicMock()
        mock_session.post.return_value = resp

        result = client.chat_completion_with_native_mcp(
            messages=[{"role": "user", "content": "List files"}],
            mcp_servers=[{"name": "fs", "transport": "stdio", "command": "cmd"}],
        )

        assert "choices" in result

    def test_native_mcp_validates_server_config(self, client, mock_session):
        """Bad config raises ValueError."""
        with pytest.raises((ValueError, TypeError)):
            client.chat_completion_with_native_mcp(
                messages=[{"role": "user", "content": "Hello"}],
                mcp_servers=[],  # Empty list should raise
            )

    def test_native_mcp_model_override(self, client, mock_session):
        """Model parameter works."""
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"choices": [{"message": {"content": "ok"}}]}
        resp.raise_for_status = MagicMock()
        mock_session.post.return_value = resp

        client.chat_completion_with_native_mcp(
            messages=[{"role": "user", "content": "Hello"}],
            mcp_servers=[{"name": "t", "transport": "stdio", "command": "c"}],
            model="special-model",
        )

        call_kwargs = mock_session.post.call_args
        payload = call_kwargs[1]["json"] if "json" in call_kwargs[1] else call_kwargs.kwargs["json"]
        assert payload["model"] == "special-model"


class TestNativeMCPErrors:
    """Error handling tests."""

    def test_native_mcp_lmstudio_error_mapped(self, client, mock_session):
        """HTTP 500 -> LLMResponseError."""
        resp = MagicMock()
        resp.status_code = 500
        mock_session.post.side_effect = requests.exceptions.HTTPError(response=resp)

        with pytest.raises(LLMResponseError):
            client.chat_completion_with_native_mcp(
                messages=[{"role": "user", "content": "Hello"}],
                mcp_servers=[{"name": "t", "transport": "stdio", "command": "c"}],
            )

    def test_native_mcp_timeout_mapped(self, client, mock_session):
        """Timeout -> LLMTimeoutError."""
        mock_session.post.side_effect = requests.exceptions.Timeout("timeout")

        with pytest.raises(LLMTimeoutError):
            client.chat_completion_with_native_mcp(
                messages=[{"role": "user", "content": "Hello"}],
                mcp_servers=[{"name": "t", "transport": "stdio", "command": "c"}],
            )

    def test_native_mcp_fallback_raises_specific_exception(self, client, mock_session):
        """When native MCP is not supported, raise LLMResponseError with clear message."""
        # Make supports_native_mcp return False
        with patch.object(client, "supports_native_mcp", return_value=False):
            with pytest.raises(LLMResponseError, match="[Nn]ative MCP"):
                client.chat_completion_with_native_mcp(
                    messages=[{"role": "user", "content": "Hello"}],
                    mcp_servers=[{"name": "t", "transport": "stdio", "command": "c"}],
                    require_native=True,
                )
