"""Tests for OPP-11: Anthropic /v1/messages endpoint support."""

import pytest
from unittest.mock import patch, MagicMock
import requests

from llm.llm_client import LLMClient
from llm.exceptions import (
    LLMTimeoutError,
    LLMConnectionError,
    LLMRateLimitError,
    LLMResponseError,
)
from config.constants import (
    DEFAULT_ANTHROPIC_API_VERSION,
)


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


def _make_anthropic_response(text="Hello", stop_reason="end_turn"):
    """Helper to create a mock Anthropic API response."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "content": [{"type": "text", "text": text}],
        "model": "test-model",
        "stop_reason": stop_reason,
        "usage": {"input_tokens": 10, "output_tokens": 20},
    }
    resp.raise_for_status = MagicMock()
    return resp


def _make_tool_use_response():
    """Helper to create a mock Anthropic tool use response."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "id": "msg_tool",
        "type": "message",
        "role": "assistant",
        "content": [
            {"type": "tool_use", "id": "toolu_123", "name": "calculator", "input": {"expr": "2+2"}},
        ],
        "model": "test-model",
        "stop_reason": "tool_use",
        "usage": {"input_tokens": 15, "output_tokens": 25},
    }
    resp.raise_for_status = MagicMock()
    return resp


class TestAnthropicMessagesBasic:
    """Basic happy-path tests for anthropic_messages()."""

    def test_anthropic_messages_basic(self, client, mock_session):
        """Happy path: returns content with type='text'."""
        mock_session.post.return_value = _make_anthropic_response("Hi there")

        result = client.anthropic_messages(
            messages=[{"role": "user", "content": "Hello"}]
        )

        assert result["content"][0]["type"] == "text"
        assert result["content"][0]["text"] == "Hi there"
        assert result["stop_reason"] == "end_turn"

    def test_anthropic_messages_system_is_top_level(self, client, mock_session):
        """System prompt goes to payload root, NOT in messages array."""
        mock_session.post.return_value = _make_anthropic_response()

        client.anthropic_messages(
            messages=[{"role": "user", "content": "Hello"}],
            system="You are helpful.",
        )

        call_kwargs = mock_session.post.call_args
        payload = call_kwargs[1]["json"] if "json" in call_kwargs[1] else call_kwargs.kwargs["json"]
        assert payload["system"] == "You are helpful."
        for msg in payload["messages"]:
            assert msg["role"] != "system"

    def test_anthropic_messages_max_tokens_in_payload(self, client, mock_session):
        """max_tokens always included in request payload."""
        mock_session.post.return_value = _make_anthropic_response()

        client.anthropic_messages(
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=2048,
        )

        call_kwargs = mock_session.post.call_args
        payload = call_kwargs[1]["json"] if "json" in call_kwargs[1] else call_kwargs.kwargs["json"]
        assert payload["max_tokens"] == 2048

    def test_anthropic_messages_filters_system_messages(self, client, mock_session):
        """System role messages in the array get filtered out."""
        mock_session.post.return_value = _make_anthropic_response()

        client.anthropic_messages(
            messages=[
                {"role": "system", "content": "I'm a system msg"},
                {"role": "user", "content": "Hello"},
            ]
        )

        call_kwargs = mock_session.post.call_args
        payload = call_kwargs[1]["json"] if "json" in call_kwargs[1] else call_kwargs.kwargs["json"]
        roles = [m["role"] for m in payload["messages"]]
        assert "system" not in roles

    def test_anthropic_messages_model_override(self, client, mock_session):
        """Per-request model override via model param."""
        mock_session.post.return_value = _make_anthropic_response()

        client.anthropic_messages(
            messages=[{"role": "user", "content": "Hello"}],
            model="other-model",
        )

        call_kwargs = mock_session.post.call_args
        payload = call_kwargs[1]["json"] if "json" in call_kwargs[1] else call_kwargs.kwargs["json"]
        assert payload["model"] == "other-model"

    def test_anthropic_messages_includes_version_header(self, client, mock_session):
        """Request includes anthropic-version header."""
        mock_session.post.return_value = _make_anthropic_response()

        client.anthropic_messages(
            messages=[{"role": "user", "content": "Hello"}]
        )

        call_kwargs = mock_session.post.call_args
        headers = call_kwargs[1].get("headers", call_kwargs.kwargs.get("headers", {}))
        assert headers.get("anthropic-version") == DEFAULT_ANTHROPIC_API_VERSION


class TestAnthropicMessagesToolUse:
    """Tool use tests."""

    def test_anthropic_messages_tool_use_response(self, client, mock_session):
        """Tool use response with stop_reason='tool_use'."""
        mock_session.post.return_value = _make_tool_use_response()

        result = client.anthropic_messages(
            messages=[{"role": "user", "content": "Calculate 2+2"}],
            tools=[{"name": "calculator", "description": "Math", "input_schema": {"type": "object"}}],
        )

        assert result["stop_reason"] == "tool_use"
        assert result["content"][0]["type"] == "tool_use"
        assert result["content"][0]["name"] == "calculator"

    def test_anthropic_messages_tool_result_injection(self, client, mock_session):
        """tool_result messages accepted in conversation."""
        mock_session.post.return_value = _make_anthropic_response("The answer is 4")

        result = client.anthropic_messages(
            messages=[
                {"role": "user", "content": "Calculate 2+2"},
                {"role": "assistant", "content": [{"type": "tool_use", "id": "toolu_123", "name": "calc", "input": {}}]},
                {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "toolu_123", "content": "4"}]},
            ]
        )

        assert result["content"][0]["text"] == "The answer is 4"


class TestAnthropicMessagesJIT:
    """JIT model loading tests."""

    def test_anthropic_messages_jit_loading(self, client, mock_session):
        """_ensure_model_loaded() called with JIT_TTL_DEFAULT via AnthropicClient."""
        mock_session.post.return_value = _make_anthropic_response()

        with patch("llm.chat_client.ChatClient._ensure_model_loaded") as mock_jit:
            client.anthropic_messages(
                messages=[{"role": "user", "content": "Hello"}]
            )
            mock_jit.assert_called_once()
            call_args = mock_jit.call_args
            assert call_args[1].get("ttl") is not None or len(call_args[0]) >= 2


class TestAnthropicMessagesErrors:
    """Error handling tests."""

    def test_anthropic_messages_timeout(self, client, mock_session):
        """requests.Timeout -> LLMTimeoutError."""
        mock_session.post.side_effect = requests.exceptions.Timeout("timeout")

        with pytest.raises(LLMTimeoutError):
            client.anthropic_messages(
                messages=[{"role": "user", "content": "Hello"}]
            )

    def test_anthropic_messages_connection_error(self, client, mock_session):
        """requests.ConnectionError -> LLMConnectionError."""
        mock_session.post.side_effect = requests.exceptions.ConnectionError("refused")

        with pytest.raises(LLMConnectionError):
            client.anthropic_messages(
                messages=[{"role": "user", "content": "Hello"}]
            )

    def test_anthropic_messages_rate_limit_429(self, client, mock_session):
        """HTTP 429 -> LLMRateLimitError."""
        resp = MagicMock()
        resp.status_code = 429
        mock_session.post.side_effect = requests.exceptions.HTTPError(response=resp)

        with pytest.raises(LLMRateLimitError):
            client.anthropic_messages(
                messages=[{"role": "user", "content": "Hello"}]
            )

    def test_anthropic_messages_retry_on_500(self, client, mock_session):
        """HTTP 500 maps to LLMResponseError (retried by decorator)."""
        resp_500 = MagicMock()
        resp_500.status_code = 500
        mock_session.post.side_effect = requests.exceptions.HTTPError(response=resp_500)

        with pytest.raises(LLMResponseError):
            client.anthropic_messages(
                messages=[{"role": "user", "content": "Hello"}]
            )


class TestAnthropicMessagesEdgeCases:
    """Edge case tests."""

    def test_anthropic_messages_empty_messages_with_system(self, client, mock_session):
        """Empty messages list with system prompt."""
        mock_session.post.return_value = _make_anthropic_response()

        client.anthropic_messages(messages=[], system="You are helpful.")

        call_kwargs = mock_session.post.call_args
        payload = call_kwargs[1]["json"] if "json" in call_kwargs[1] else call_kwargs.kwargs["json"]
        assert payload["system"] == "You are helpful."
        assert payload["messages"] == []

    def test_anthropic_messages_multi_turn_alternating(self, client, mock_session):
        """Multi-turn user/assistant/user conversation."""
        mock_session.post.return_value = _make_anthropic_response("World")

        client.anthropic_messages(
            messages=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": [{"type": "text", "text": "Hi"}]},
                {"role": "user", "content": "How are you?"},
            ]
        )

        call_kwargs = mock_session.post.call_args
        payload = call_kwargs[1]["json"] if "json" in call_kwargs[1] else call_kwargs.kwargs["json"]
        assert len(payload["messages"]) == 3

    def test_anthropic_messages_system_conflict_prefers_param(self, client, mock_session):
        """BOTH system param AND role=system message -> param wins, message filtered."""
        mock_session.post.return_value = _make_anthropic_response()

        client.anthropic_messages(
            messages=[
                {"role": "system", "content": "I'm from messages"},
                {"role": "user", "content": "Hello"},
            ],
            system="I'm the param",
        )

        call_kwargs = mock_session.post.call_args
        payload = call_kwargs[1]["json"] if "json" in call_kwargs[1] else call_kwargs.kwargs["json"]
        assert payload["system"] == "I'm the param"
        roles = [m["role"] for m in payload["messages"]]
        assert "system" not in roles

    def test_anthropic_messages_empty_content_returns_default(self, client, mock_session):
        """content=[] response returns response as-is (no IndexError)."""
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "id": "msg_empty",
            "type": "message",
            "role": "assistant",
            "content": [],
            "stop_reason": "end_turn",
        }
        resp.raise_for_status = MagicMock()
        mock_session.post.return_value = resp

        result = client.anthropic_messages(
            messages=[{"role": "user", "content": "Hello"}]
        )
        assert result["content"] == []

    def test_anthropic_messages_zero_max_tokens_in_payload(self, client, mock_session):
        """max_tokens=0 must be in payload, NOT silently dropped by falsy check."""
        mock_session.post.return_value = _make_anthropic_response()

        client.anthropic_messages(
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=0,
        )

        call_kwargs = mock_session.post.call_args
        payload = call_kwargs[1]["json"] if "json" in call_kwargs[1] else call_kwargs.kwargs["json"]
        assert "max_tokens" in payload
        assert payload["max_tokens"] == 0

    def test_anthropic_messages_duplicate_system_different_values(self, client, mock_session):
        """system='A' param + role=system 'B' message -> param wins, message REMOVED."""
        mock_session.post.return_value = _make_anthropic_response()

        client.anthropic_messages(
            messages=[
                {"role": "system", "content": "B"},
                {"role": "user", "content": "Hello"},
            ],
            system="A",
        )

        call_kwargs = mock_session.post.call_args
        payload = call_kwargs[1]["json"] if "json" in call_kwargs[1] else call_kwargs.kwargs["json"]
        assert payload["system"] == "A"
        for msg in payload["messages"]:
            assert msg["role"] != "system"
