"""Golden Master characterization tests for LLMClient — ARCH-1 Step 0.

These tests capture the EXACT current behavior of LLMClient's 24 public methods
before the Facade refactor. They freeze the API contract: payload shapes, return
types, delegation paths, and error handling. If ANY of these fail after the
refactor, the Facade is not behavior-preserving.

Test categories (Req 07):
- Happy: Tests 1-12 — each public method produces correct payload/response
- Negative: Tests 13-15 — exception mapping for HTTP errors
- Edge: Tests 16-19 — static delegates, health check, default values
- Boundary: Tests 20-24 — thinking budget bounds, model resolution
"""

from unittest.mock import MagicMock, patch, PropertyMock
from typing import Generator

import pytest

from llm.llm_client import LLMClient, _handle_request_exception


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_session():
    """Pre-wired mock requests.Session."""
    session = MagicMock()
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"choices": [{"message": {"content": "hello"}}]}
    response.raise_for_status.return_value = None
    session.post.return_value = response
    session.get.return_value = response
    return session


@pytest.fixture
def client(mock_session):
    """LLMClient with injected mock session."""
    with patch("llm.llm_client.get_config") as mock_config:
        mock_config.return_value.lmstudio.api_base = "http://localhost:1234/v1"
        mock_config.return_value.lmstudio.default_model = "test-model"
        c = LLMClient(session=mock_session)
    return c


# ---------------------------------------------------------------------------
# Happy: Payload shapes for core API methods
# ---------------------------------------------------------------------------

class TestChatCompletionPayload:
    """Happy: chat_completion sends correct payload."""

    def test_basic_payload(self, client, mock_session) -> None:
        with patch.object(client, "_ensure_model_loaded"):
            result = client.chat_completion(
                messages=[{"role": "user", "content": "hi"}],
                temperature=0.5,
                max_tokens=100,
            )

        call_args = mock_session.post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert payload["messages"] == [{"role": "user", "content": "hi"}]
        assert payload["temperature"] == 0.5
        assert payload["max_tokens"] == 100
        assert payload["model"] == "test-model"
        assert "tools" not in payload
        assert result == {"choices": [{"message": {"content": "hello"}}]}

    def test_with_tools(self, client, mock_session) -> None:
        tools = [{"type": "function", "function": {"name": "test"}}]
        with patch.object(client, "_ensure_model_loaded"):
            client.chat_completion(
                messages=[{"role": "user", "content": "hi"}],
                tools=tools,
                tool_choice="required",
            )

        payload = mock_session.post.call_args.kwargs.get("json") or mock_session.post.call_args[1]["json"]
        assert payload["tools"] == tools
        assert payload["tool_choice"] == "required"

    def test_with_response_format(self, client, mock_session) -> None:
        fmt = {"type": "json_object"}
        with patch.object(client, "_ensure_model_loaded"):
            client.chat_completion(
                messages=[{"role": "user", "content": "hi"}],
                response_format=fmt,
            )

        payload = mock_session.post.call_args.kwargs.get("json") or mock_session.post.call_args[1]["json"]
        assert payload["response_format"] == fmt

    def test_advanced_sampling_params(self, client, mock_session) -> None:
        with patch.object(client, "_ensure_model_loaded"):
            client.chat_completion(
                messages=[{"role": "user", "content": "hi"}],
                min_p=0.1,
                top_k=40,
            )

        payload = mock_session.post.call_args.kwargs.get("json") or mock_session.post.call_args[1]["json"]
        assert payload["min_p"] == 0.1
        assert payload["top_k"] == 40


class TestTextCompletionPayload:
    """Happy: text_completion sends correct payload."""

    def test_basic_payload(self, client, mock_session) -> None:
        mock_session.post.return_value.json.return_value = {"choices": [{"text": "world"}]}
        with patch.object(client, "_ensure_model_loaded"):
            result = client.text_completion(prompt="hello", temperature=0.3, max_tokens=50)

        payload = mock_session.post.call_args.kwargs.get("json") or mock_session.post.call_args[1]["json"]
        assert payload["prompt"] == "hello"
        assert payload["temperature"] == 0.3
        assert payload["max_tokens"] == 50
        assert payload["model"] == "test-model"

    def test_with_stop_sequences(self, client, mock_session) -> None:
        with patch.object(client, "_ensure_model_loaded"):
            client.text_completion(prompt="hello", stop_sequences=["END"])

        payload = mock_session.post.call_args.kwargs.get("json") or mock_session.post.call_args[1]["json"]
        assert payload["stop"] == ["END"]


class TestCreateResponsePayload:
    """Happy: create_response sends correct payload."""

    def test_basic_payload(self, client, mock_session) -> None:
        mock_session.post.return_value.json.return_value = {"id": "resp_1", "output": []}
        with patch.object(client, "_ensure_model_loaded"):
            result = client.create_response(input_text="test input", model="test-model")

        payload = mock_session.post.call_args.kwargs.get("json") or mock_session.post.call_args[1]["json"]
        assert payload["input"] == "test input"
        assert payload["model"] == "test-model"
        assert payload["stream"] is False
        assert "ttl" in payload

    def test_with_tools_and_previous_response(self, client, mock_session) -> None:
        tools = [{"type": "function", "function": {"name": "calc"}}]
        with patch.object(client, "_ensure_model_loaded"):
            client.create_response(
                input_text="continue",
                tools=tools,
                previous_response_id="resp_0",
                tool_choice="required",
            )

        payload = mock_session.post.call_args.kwargs.get("json") or mock_session.post.call_args[1]["json"]
        assert payload["previous_response_id"] == "resp_0"
        assert payload["tool_choice"] == "required"
        # Tools should be converted to responses format
        assert "tools" in payload


class TestAnthropicMessagesPayload:
    """Happy: anthropic_messages sends correct payload."""

    def test_basic_payload(self, client, mock_session) -> None:
        with patch.object(client, "_ensure_model_loaded"):
            client.anthropic_messages(
                messages=[{"role": "user", "content": "hi"}],
                system="You are helpful.",
                max_tokens=1024,
            )

        payload = mock_session.post.call_args.kwargs.get("json") or mock_session.post.call_args[1]["json"]
        assert payload["messages"] == [{"role": "user", "content": "hi"}]
        assert payload["system"] == "You are helpful."
        assert payload["max_tokens"] == 1024
        # Should have anthropic-version header
        headers = mock_session.post.call_args.kwargs.get("headers") or mock_session.post.call_args[1].get("headers", {})
        assert "anthropic-version" in headers

    def test_filters_system_messages(self, client, mock_session) -> None:
        """System role messages should be filtered from the messages array."""
        with patch.object(client, "_ensure_model_loaded"):
            client.anthropic_messages(
                messages=[
                    {"role": "system", "content": "should be removed"},
                    {"role": "user", "content": "hi"},
                ],
            )

        payload = mock_session.post.call_args.kwargs.get("json") or mock_session.post.call_args[1]["json"]
        assert len(payload["messages"]) == 1
        assert payload["messages"][0]["role"] == "user"


class TestEmbeddingsPayload:
    """Happy: generate_embeddings sends correct payload."""

    def test_basic_payload(self, client, mock_session) -> None:
        mock_session.post.return_value.json.return_value = {"data": [{"embedding": [0.1]}]}
        with patch.object(client, "_ensure_model_loaded"):
            client.generate_embeddings(text="hello world")

        payload = mock_session.post.call_args.kwargs.get("json") or mock_session.post.call_args[1]["json"]
        assert payload["input"] == "hello world"
        assert "ttl" in payload


class TestModelInfoMethods:
    """Happy: Model info methods return correct shapes."""

    def test_list_models(self, client, mock_session) -> None:
        mock_session.get.return_value.json.return_value = {
            "data": [{"id": "model-a"}, {"id": "model-b"}]
        }
        result = client.list_models()
        assert result == ["model-a", "model-b"]

    def test_list_models_enriched_native(self, client, mock_session) -> None:
        mock_session.get.return_value.json.return_value = [
            {"key": "model-a", "type": "llm", "publisher": "test"}
        ]
        result = client.list_models_enriched()
        assert len(result) == 1
        assert result[0]["model_id"] == "model-a"
        assert result[0]["type"] == "llm"

    def test_get_model_info(self, client, mock_session) -> None:
        mock_session.get.return_value.json.return_value = {
            "data": [{"id": "test-model", "owned_by": "user"}]
        }
        result = client.get_model_info("test-model")
        assert result["id"] == "test-model"

    def test_get_default_max_tokens(self, client) -> None:
        assert client.get_default_max_tokens() == 8192


# ---------------------------------------------------------------------------
# Negative: Exception mapping
# ---------------------------------------------------------------------------

class TestExceptionMapping:
    """Negative: _handle_request_exception maps correctly."""

    def test_timeout_maps_to_llm_timeout(self) -> None:
        import requests
        from llm.exceptions import LLMTimeoutError
        with pytest.raises(LLMTimeoutError):
            _handle_request_exception(requests.exceptions.Timeout(), "test")

    def test_connection_error_maps(self) -> None:
        import requests
        from llm.exceptions import LLMConnectionError
        with pytest.raises(LLMConnectionError):
            _handle_request_exception(requests.exceptions.ConnectionError(), "test")

    def test_rate_limit_maps(self) -> None:
        import requests
        from llm.exceptions import LLMRateLimitError
        response = MagicMock()
        response.status_code = 429
        err = requests.exceptions.HTTPError(response=response)
        with pytest.raises(LLMRateLimitError):
            _handle_request_exception(err, "test")


# ---------------------------------------------------------------------------
# Edge: Static delegates and health check
# ---------------------------------------------------------------------------

class TestStaticDelegates:
    """Edge: Static methods delegate to FormatAdapter."""

    def test_convert_tools_to_responses_format(self) -> None:
        tools = [{"type": "function", "function": {"name": "test", "description": "d", "parameters": {}}}]
        result = LLMClient.convert_tools_to_responses_format(tools)
        assert isinstance(result, list)
        assert result[0]["name"] == "test"

    def test_convert_tools_to_anthropic_format(self) -> None:
        tools = [{"type": "function", "function": {"name": "test", "description": "d", "parameters": {}}}]
        result = LLMClient.convert_tools_to_anthropic_format(tools)
        assert isinstance(result, list)
        assert result[0]["name"] == "test"

    def test_extract_anthropic_tool_calls(self) -> None:
        response = {"content": [{"type": "tool_use", "id": "t1", "name": "fn", "input": {}}]}
        result = LLMClient.extract_anthropic_tool_calls(response)
        assert len(result) == 1
        assert result[0]["name"] == "fn"

    def test_build_anthropic_tool_result(self) -> None:
        result = LLMClient.build_anthropic_tool_result("t1", "ok")
        assert result["role"] == "user"
        assert result["content"][0]["type"] == "tool_result"


class TestHealthCheck:
    """Edge: health_check returns bool without raising."""

    def test_healthy(self, client, mock_session) -> None:
        assert client.health_check() is True

    def test_unhealthy(self, client, mock_session) -> None:
        mock_session.get.side_effect = ConnectionError("down")
        assert client.health_check() is False


# ---------------------------------------------------------------------------
# Boundary: Thinking budget and model resolution
# ---------------------------------------------------------------------------

class TestThinkingBudgetBounds:
    """Boundary: thinking_completion validates budget range."""

    def test_default_budget_applied(self, client, mock_session) -> None:
        from config.constants import DEFAULT_THINKING_BUDGET_TOKENS
        with patch.object(client, "_ensure_model_loaded"):
            client.thinking_completion(
                messages=[{"role": "user", "content": "think"}],
            )

        payload = mock_session.post.call_args.kwargs.get("json") or mock_session.post.call_args[1]["json"]
        from config.constants import DEFAULT_MAX_TOKENS
        assert payload["max_tokens"] == DEFAULT_THINKING_BUDGET_TOKENS + DEFAULT_MAX_TOKENS

    def test_budget_too_low_raises(self, client) -> None:
        with pytest.raises(ValueError, match="thinking_budget must be between"):
            client.thinking_completion(
                messages=[{"role": "user", "content": "think"}],
                thinking_budget=0,
            )

    def test_budget_too_high_raises(self, client) -> None:
        with pytest.raises(ValueError, match="thinking_budget must be between"):
            client.thinking_completion(
                messages=[{"role": "user", "content": "think"}],
                thinking_budget=999999999,
            )


class TestModelResolution:
    """Boundary: Per-request model override vs default."""

    def test_default_model_used(self, client, mock_session) -> None:
        with patch.object(client, "_ensure_model_loaded"):
            client.chat_completion(messages=[{"role": "user", "content": "hi"}])

        payload = mock_session.post.call_args.kwargs.get("json") or mock_session.post.call_args[1]["json"]
        assert payload["model"] == "test-model"

    def test_per_request_model_override(self, client, mock_session) -> None:
        with patch.object(client, "_ensure_model_loaded"):
            client.chat_completion(
                messages=[{"role": "user", "content": "hi"}],
                model="override-model",
            )

        payload = mock_session.post.call_args.kwargs.get("json") or mock_session.post.call_args[1]["json"]
        assert payload["model"] == "override-model"


class TestContextManager:
    """Edge: LLMClient works as context manager."""

    def test_context_manager_closes_session(self) -> None:
        with patch("llm.llm_client.get_config") as mock_config:
            mock_config.return_value.lmstudio.api_base = "http://localhost:1234/v1"
            mock_config.return_value.lmstudio.default_model = "test"
            mock_session = MagicMock()
            client = LLMClient(session=mock_session)
            # Injected session — _owns_session is False, so close() should NOT close it
            client.__enter__()
            client.__exit__(None, None, None)
            # Session should NOT be closed (not owned)
            mock_session.close.assert_not_called()

    def test_owned_session_closes(self) -> None:
        with patch("llm.llm_client.get_config") as mock_config:
            mock_config.return_value.lmstudio.api_base = "http://localhost:1234/v1"
            mock_config.return_value.lmstudio.default_model = "test"
            with patch("llm.llm_client.requests.Session") as mock_sess_cls:
                mock_sess = MagicMock()
                mock_sess_cls.return_value = mock_sess
                client = LLMClient()  # Creates own session
                client.close()
                mock_sess.close.assert_called_once()


class TestIsThinkingCapable:
    """Edge: is_thinking_capable delegates to ModelMetadata."""

    def test_thinking_model(self) -> None:
        assert LLMClient.is_thinking_capable("qwen/qwq-32b") is True

    def test_non_thinking_model(self) -> None:
        assert LLMClient.is_thinking_capable("qwen/qwen3-coder-30b") is False
