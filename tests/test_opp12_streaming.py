"""Tests for OPP-12: SSE Streaming Support.

Tests for:
- parse_sse_stream() generator in llm/sse_parser.py
- stream_chat_completion() on LLMClient
- stream_create_response() on LLMClient
- stream_anthropic_messages() on LLMClient
- Regression: existing non-streaming methods still work
"""

import json
from unittest.mock import MagicMock, patch

import pytest
import requests

from config.constants import SSE_DATA_PREFIX, SSE_DONE_SENTINEL, STREAM_READ_TIMEOUT
from llm.exceptions import LLMConnectionError, LLMTimeoutError
from llm.llm_client import LLMClient
from llm.sse_parser import parse_sse_stream

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client():
    """Create LLMClient with mocked config (no real LM Studio needed)."""
    with patch("llm.llm_client.get_config") as mock_cfg:
        mock_cfg.return_value.lmstudio.api_base = "http://localhost:1234/v1"
        mock_cfg.return_value.lmstudio.default_model = "test-model"
        client = LLMClient()
    return client


def _mock_streaming_response(lines: list[bytes]) -> MagicMock:
    """Build a mock requests.Response that streams the given byte lines."""
    resp = MagicMock(spec=requests.Response)
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.iter_lines.return_value = iter(lines)
    return resp


def _sse_data_line(payload: dict) -> bytes:
    """Encode a dict as an SSE data line."""
    return f"data: {json.dumps(payload)}".encode()


def _sse_done_line() -> bytes:
    """Return the SSE [DONE] sentinel line."""
    return b"data: [DONE]"


# ---------------------------------------------------------------------------
# Phase 1: parse_sse_stream() unit tests
# ---------------------------------------------------------------------------


class TestParseSSEStream:
    """Unit tests for the parse_sse_stream() generator."""

    def test_parse_single_data_event(self):
        """Happy path: single JSON data event is yielded as a dict."""
        chunk = {"id": "c1", "choices": [{"delta": {"content": "Hello"}}]}
        resp = _mock_streaming_response([_sse_data_line(chunk)])

        events = list(parse_sse_stream(resp))

        assert len(events) == 1
        assert events[0] == chunk

    def test_parse_multiple_data_events(self):
        """Multiple JSON data events are all yielded."""
        chunks = [
            {"id": "c1", "choices": [{"delta": {"content": "Hello"}}]},
            {"id": "c2", "choices": [{"delta": {"content": " world"}}]},
        ]
        lines = [_sse_data_line(c) for c in chunks]
        resp = _mock_streaming_response(lines)

        events = list(parse_sse_stream(resp))

        assert len(events) == 2
        assert events[0]["id"] == "c1"
        assert events[1]["id"] == "c2"

    def test_parse_done_sentinel_stops_iteration(self):
        """[DONE] sentinel stops the generator (not yielded as event)."""
        chunk = {"id": "c1", "choices": [{"delta": {"content": "Hi"}}]}
        resp = _mock_streaming_response([_sse_data_line(chunk), _sse_done_line()])

        events = list(parse_sse_stream(resp))

        # Only the real chunk — [DONE] must NOT appear
        assert len(events) == 1
        assert events[0]["id"] == "c1"

    def test_parse_empty_lines_are_skipped(self):
        """Empty lines (SSE field separator) are silently skipped."""
        chunk = {"id": "c1", "choices": [{"delta": {"content": "Hi"}}]}
        resp = _mock_streaming_response([
            b"",            # empty separator
            b"   ",         # whitespace-only line
            _sse_data_line(chunk),
            b"",
            _sse_done_line(),
        ])

        events = list(parse_sse_stream(resp))

        assert len(events) == 1

    def test_parse_non_data_prefixed_lines_skipped(self):
        """Lines that don't start with 'data: ' are ignored (e.g. 'event: ...')."""
        chunk = {"id": "c1", "choices": [{"delta": {"content": "Hi"}}]}
        resp = _mock_streaming_response([
            b"event: content_block_delta",
            _sse_data_line(chunk),
            _sse_done_line(),
        ])

        events = list(parse_sse_stream(resp))

        assert len(events) == 1

    def test_parse_malformed_json_yields_error_event(self):
        """Malformed JSON yields an error dict instead of crashing."""
        resp = _mock_streaming_response([
            b"data: {not valid json}",
            _sse_done_line(),
        ])

        events = list(parse_sse_stream(resp))

        assert len(events) == 1
        assert events[0].get("error") is not None
        assert "parse" in events[0]["error"].lower() or "json" in events[0]["error"].lower()

    def test_parse_connection_error_yields_error_event(self):
        """ConnectionError during iteration yields an error event, does not crash."""
        resp = MagicMock(spec=requests.Response)
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        resp.iter_lines.side_effect = requests.exceptions.ConnectionError("dropped")

        events = list(parse_sse_stream(resp))

        assert len(events) == 1
        assert events[0].get("error") is not None

    def test_parse_chunk_error_mid_stream_yields_error_event(self):
        """ChunkedEncodingError mid-stream yields an error event instead of raising."""
        chunk = {"id": "c1", "choices": [{"delta": {"content": "Hi"}}]}

        def _failing_iter():
            yield _sse_data_line(chunk)
            raise requests.exceptions.ChunkedEncodingError("connection reset")

        resp = MagicMock(spec=requests.Response)
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        resp.iter_lines.return_value = _failing_iter()

        events = list(parse_sse_stream(resp))

        # First chunk yielded fine, then error event
        assert events[0]["id"] == "c1"
        assert events[-1].get("error") is not None

    def test_parse_empty_stream_yields_nothing(self):
        """A response with no lines at all yields zero events."""
        resp = _mock_streaming_response([])

        events = list(parse_sse_stream(resp))

        assert events == []

    def test_parse_only_done_sentinel_yields_nothing(self):
        """A stream that is only [DONE] yields zero events."""
        resp = _mock_streaming_response([_sse_done_line()])

        events = list(parse_sse_stream(resp))

        assert events == []

    def test_parse_nested_json_preserved(self):
        """Nested JSON structures in SSE data are preserved faithfully."""
        chunk = {
            "id": "c1",
            "choices": [{"delta": {"tool_calls": [
                {"index": 0, "function": {"arguments": '{"x": 1}'}}
            ]}}],
        }
        resp = _mock_streaming_response([_sse_data_line(chunk), _sse_done_line()])

        events = list(parse_sse_stream(resp))

        assert len(events) == 1
        assert events[0]["choices"][0]["delta"]["tool_calls"][0]["index"] == 0


# ---------------------------------------------------------------------------
# Constants tests
# ---------------------------------------------------------------------------


class TestSSEConstants:
    """Verify the SSE constants are correctly defined."""

    def test_sse_done_sentinel_value(self):
        """SSE_DONE_SENTINEL must be '[DONE]'."""
        assert SSE_DONE_SENTINEL == "[DONE]"

    def test_sse_data_prefix_value(self):
        """SSE_DATA_PREFIX must be 'data: '."""
        assert SSE_DATA_PREFIX == "data: "

    def test_stream_read_timeout_value(self):
        """STREAM_READ_TIMEOUT must be 300.0 seconds."""
        assert STREAM_READ_TIMEOUT == 300.0


# ---------------------------------------------------------------------------
# Phase 2: LLMClient.stream_chat_completion() tests
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    """Provide a mocked LLMClient instance."""
    return _make_client()


class TestStreamChatCompletion:
    """Tests for LLMClient.stream_chat_completion()."""

    def _make_stream_resp(self, chunks: list[dict]) -> MagicMock:
        lines = [_sse_data_line(c) for c in chunks] + [_sse_done_line()]
        resp = _mock_streaming_response(lines)
        return resp

    def test_stream_chat_completion_yields_chunks(self, client):
        """Happy path: yields parsed dicts for each SSE event."""
        chunk = {"id": "c1", "choices": [{"delta": {"content": "Hello"}}]}
        mock_resp = self._make_stream_resp([chunk])

        with patch.object(client.session, "post", return_value=mock_resp):
            results = list(client.stream_chat_completion(
                messages=[{"role": "user", "content": "Hi"}]
            ))

        assert len(results) == 1
        assert results[0]["id"] == "c1"

    def test_stream_chat_completion_done_not_yielded(self, client):
        """[DONE] sentinel must never appear in the yielded results."""
        chunk = {"id": "c1", "choices": [{"delta": {"content": "A"}}]}
        mock_resp = self._make_stream_resp([chunk])

        with patch.object(client.session, "post", return_value=mock_resp):
            results = list(client.stream_chat_completion(
                messages=[{"role": "user", "content": "Hi"}]
            ))

        for result in results:
            assert result != SSE_DONE_SENTINEL
            assert result.get("error") != SSE_DONE_SENTINEL

    def test_stream_chat_completion_multiple_chunks(self, client):
        """Multiple SSE events are all yielded in order."""
        chunks = [
            {"id": "c1", "choices": [{"delta": {"content": "Hello"}}]},
            {"id": "c2", "choices": [{"delta": {"content": " world"}}]},
            {"id": "c3", "choices": [{"delta": {"content": "!"}}]},
        ]
        mock_resp = self._make_stream_resp(chunks)

        with patch.object(client.session, "post", return_value=mock_resp):
            results = list(client.stream_chat_completion(
                messages=[{"role": "user", "content": "Hi"}]
            ))

        assert len(results) == 3
        assert results[2]["id"] == "c3"

    def test_stream_chat_completion_with_tools(self, client):
        """Tools parameter is forwarded in the request payload."""
        chunk = {"id": "c1", "choices": [{"delta": {"content": "ok"}}]}
        mock_resp = self._make_stream_resp([chunk])

        tools = [{"type": "function", "function": {"name": "calc", "description": "math"}}]

        with patch.object(client.session, "post", return_value=mock_resp) as mock_post:
            list(client.stream_chat_completion(
                messages=[{"role": "user", "content": "calc 2+2"}],
                tools=tools,
            ))

        call_kwargs = mock_post.call_args
        payload = call_kwargs[1].get("json", call_kwargs.kwargs.get("json", {}))
        assert payload.get("tools") == tools
        assert payload.get("stream") is True

    def test_stream_chat_completion_stream_true_in_payload(self, client):
        """stream=True must always be set in the outgoing payload."""
        chunk = {"id": "c1", "choices": [{"delta": {"content": "Hi"}}]}
        mock_resp = self._make_stream_resp([chunk])

        with patch.object(client.session, "post", return_value=mock_resp) as mock_post:
            list(client.stream_chat_completion(
                messages=[{"role": "user", "content": "Hi"}]
            ))

        call_kwargs = mock_post.call_args
        payload = call_kwargs[1].get("json", call_kwargs.kwargs.get("json", {}))
        assert payload.get("stream") is True

    def test_stream_chat_completion_timeout_raises(self, client):
        """requests.Timeout propagates as LLMTimeoutError."""
        timeout_err = requests.exceptions.Timeout("timeout")
        with patch.object(client.session, "post", side_effect=timeout_err):
            with pytest.raises(LLMTimeoutError):
                list(client.stream_chat_completion(
                    messages=[{"role": "user", "content": "Hi"}]
                ))

    def test_stream_chat_completion_connection_error_raises(self, client):
        """requests.ConnectionError propagates as LLMConnectionError."""
        conn_err = requests.exceptions.ConnectionError("refused")
        with patch.object(client.session, "post", side_effect=conn_err):
            with pytest.raises(LLMConnectionError):
                list(client.stream_chat_completion(
                    messages=[{"role": "user", "content": "Hi"}]
                ))


# ---------------------------------------------------------------------------
# Phase 2: LLMClient.stream_create_response() tests
# ---------------------------------------------------------------------------


class TestStreamCreateResponse:
    """Tests for LLMClient.stream_create_response()."""

    def _make_response_chunk(self, text: str = "Hello") -> dict:
        return {
            "id": "resp_1",
            "object": "response.chunk",
            "output": [{"type": "text", "text": text}],
        }

    def test_stream_create_response_yields_chunks(self, client):
        """Happy path: yields parsed SSE dicts from /v1/responses."""
        chunk = self._make_response_chunk("Hello")
        lines = [_sse_data_line(chunk), _sse_done_line()]
        mock_resp = _mock_streaming_response(lines)

        with patch.object(client.session, "post", return_value=mock_resp):
            results = list(client.stream_create_response(input_text="Hello"))

        assert len(results) == 1
        assert results[0]["id"] == "resp_1"

    def test_stream_create_response_stream_true_in_payload(self, client):
        """stream=True must appear in the request payload."""
        chunk = self._make_response_chunk()
        lines = [_sse_data_line(chunk), _sse_done_line()]
        mock_resp = _mock_streaming_response(lines)

        with patch.object(client.session, "post", return_value=mock_resp) as mock_post:
            list(client.stream_create_response(input_text="Hi"))

        call_kwargs = mock_post.call_args
        payload = call_kwargs[1].get("json", call_kwargs.kwargs.get("json", {}))
        assert payload.get("stream") is True

    def test_stream_create_response_with_tools(self, client):
        """Tools are forwarded and converted to LM Studio format."""
        chunk = self._make_response_chunk()
        lines = [_sse_data_line(chunk), _sse_done_line()]
        mock_resp = _mock_streaming_response(lines)

        tools = [{"type": "function", "function": {"name": "search", "description": "Search"}}]

        with patch.object(client.session, "post", return_value=mock_resp) as mock_post:
            list(client.stream_create_response(input_text="Find X", tools=tools))

        call_kwargs = mock_post.call_args
        payload = call_kwargs[1].get("json", call_kwargs.kwargs.get("json", {}))
        # Tools converted to LM Studio flat format
        assert payload.get("tools") is not None

    def test_stream_create_response_done_not_yielded(self, client):
        """[DONE] sentinel is consumed internally and never yielded."""
        chunk = self._make_response_chunk()
        lines = [_sse_data_line(chunk), _sse_done_line()]
        mock_resp = _mock_streaming_response(lines)

        with patch.object(client.session, "post", return_value=mock_resp):
            results = list(client.stream_create_response(input_text="Hi"))

        assert len(results) == 1


# ---------------------------------------------------------------------------
# Phase 2: LLMClient.stream_anthropic_messages() tests
# ---------------------------------------------------------------------------


class TestStreamAnthropicMessages:
    """Tests for LLMClient.stream_anthropic_messages()."""

    def _make_anthropic_chunk(self, text: str = "Hello") -> dict:
        return {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "text_delta", "text": text},
        }

    def test_stream_anthropic_messages_yields_chunks(self, client):
        """Happy path: yields parsed dicts for Anthropic SSE events."""
        chunk = self._make_anthropic_chunk("Hi")
        lines = [_sse_data_line(chunk), _sse_done_line()]
        mock_resp = _mock_streaming_response(lines)

        with patch.object(client.session, "post", return_value=mock_resp):
            results = list(client.stream_anthropic_messages(
                messages=[{"role": "user", "content": "Hello"}]
            ))

        assert len(results) == 1
        assert results[0]["type"] == "content_block_delta"

    def test_stream_anthropic_messages_stream_true_in_payload(self, client):
        """stream=True must appear in the request payload."""
        chunk = self._make_anthropic_chunk()
        lines = [_sse_data_line(chunk), _sse_done_line()]
        mock_resp = _mock_streaming_response(lines)

        with patch.object(client.session, "post", return_value=mock_resp) as mock_post:
            list(client.stream_anthropic_messages(
                messages=[{"role": "user", "content": "Hi"}]
            ))

        call_kwargs = mock_post.call_args
        payload = call_kwargs[1].get("json", call_kwargs.kwargs.get("json", {}))
        assert payload.get("stream") is True

    def test_stream_anthropic_messages_includes_version_header(self, client):
        """anthropic-version header must be set in streaming requests too."""
        from config.constants import DEFAULT_ANTHROPIC_API_VERSION

        chunk = self._make_anthropic_chunk()
        lines = [_sse_data_line(chunk), _sse_done_line()]
        mock_resp = _mock_streaming_response(lines)

        with patch.object(client.session, "post", return_value=mock_resp) as mock_post:
            list(client.stream_anthropic_messages(
                messages=[{"role": "user", "content": "Hi"}]
            ))

        call_kwargs = mock_post.call_args
        headers = call_kwargs[1].get("headers", call_kwargs.kwargs.get("headers", {}))
        assert headers.get("anthropic-version") == DEFAULT_ANTHROPIC_API_VERSION

    def test_stream_anthropic_messages_filters_system_role(self, client):
        """System-role messages are filtered (same as non-streaming counterpart)."""
        chunk = self._make_anthropic_chunk()
        lines = [_sse_data_line(chunk), _sse_done_line()]
        mock_resp = _mock_streaming_response(lines)

        with patch.object(client.session, "post", return_value=mock_resp) as mock_post:
            list(client.stream_anthropic_messages(
                messages=[
                    {"role": "system", "content": "Be concise"},
                    {"role": "user", "content": "Hi"},
                ]
            ))

        call_kwargs = mock_post.call_args
        payload = call_kwargs[1].get("json", call_kwargs.kwargs.get("json", {}))
        roles = [m["role"] for m in payload.get("messages", [])]
        assert "system" not in roles

    def test_stream_anthropic_messages_done_not_yielded(self, client):
        """[DONE] sentinel is consumed internally."""
        chunk = self._make_anthropic_chunk()
        lines = [_sse_data_line(chunk), _sse_done_line()]
        mock_resp = _mock_streaming_response(lines)

        with patch.object(client.session, "post", return_value=mock_resp):
            results = list(client.stream_anthropic_messages(
                messages=[{"role": "user", "content": "Hi"}]
            ))

        assert len(results) == 1


# ---------------------------------------------------------------------------
# Regression: non-streaming methods must still work unchanged
# ---------------------------------------------------------------------------


class TestNonStreamingRegression:
    """Regression tests: existing synchronous methods still work after OPP-12."""

    def _make_chat_response(self, content: str = "Hello") -> MagicMock:
        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {
            "id": "chatcmpl-1",
            "choices": [{"message": {"role": "assistant", "content": content}}],
        }
        return resp

    def _make_anthropic_response(self, text: str = "Hi") -> MagicMock:
        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {
            "id": "msg_1",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": text}],
            "stop_reason": "end_turn",
        }
        return resp

    def _make_responses_response(self) -> MagicMock:
        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {
            "id": "resp_1",
            "output": [{"type": "message", "content": [{"type": "text", "text": "Done"}]}],
        }
        return resp

    def test_chat_completion_still_works(self, client):
        """chat_completion() returns a dict (not a generator) after OPP-12."""
        mock_resp = self._make_chat_response("Hello")
        with patch.object(client.session, "post", return_value=mock_resp):
            result = client.chat_completion(
                messages=[{"role": "user", "content": "Hi"}]
            )
        assert isinstance(result, dict)
        assert result["id"] == "chatcmpl-1"

    def test_anthropic_messages_still_works(self, client):
        """anthropic_messages() returns a dict (not a generator) after OPP-12."""
        mock_resp = self._make_anthropic_response("Hi")
        with patch.object(client.session, "post", return_value=mock_resp):
            result = client.anthropic_messages(
                messages=[{"role": "user", "content": "Hello"}]
            )
        assert isinstance(result, dict)
        assert result["type"] == "message"

    def test_create_response_still_works(self, client):
        """create_response() (stream=False) returns a dict after OPP-12."""
        mock_resp = self._make_responses_response()
        with patch.object(client.session, "post", return_value=mock_resp):
            result = client.create_response(input_text="Hello")
        assert isinstance(result, dict)
        assert result["id"] == "resp_1"
