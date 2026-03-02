"""Tests for OPP-38 — Fix "default" sentinel escape in HTTP payloads.

Verifies that the literal string "default" (from DEFAULT_MODEL_KEYWORD) never
leaks into HTTP POST bodies sent to LM Studio. Tests cover:

- is_model_sentinel() helper (5 unit tests)
- V1 chat_client.text_completion (3 tests: happy, negative, sentinel intercept)
- V2 responses_client.create_response (4 tests: happy, negative, sentinel intercept, double-default)
- V3 streaming_client.stream_create_response (4 tests: happy, negative, sentinel intercept, double-default)
- V4 native_chat_client.native_chat (4 tests: happy, negative, sentinel intercept, double-default)
- Regression: existing guards G1 chat_completion + G2 anthropic_messages (2 tests)

RED phase: helper tests pass immediately. Client tests MUST FAIL until GREEN
commits (C2-C5) apply the guards.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config.constants import LMSTUDIO_TESTING_ENV_VAR  # noqa: E402

os.environ.setdefault(LMSTUDIO_TESTING_ENV_VAR, "1")

from config.constants import DEFAULT_MODEL_KEYWORD, is_model_sentinel  # noqa: E402
from llm.anthropic_client import AnthropicClient  # noqa: E402
from llm.chat_client import ChatClient  # noqa: E402
from llm.native_chat_client import NativeChatClient  # noqa: E402
from llm.responses_client import ResponsesClient  # noqa: E402
from llm.streaming_client import StreamingClient  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class MockResponse:
    """Minimal stand-in for requests.Response."""

    def __init__(self, json_data=None, status_code=200, lines=None):
        self._json = json_data or {"choices": [{"message": {"content": "ok"}}]}
        self.status_code = status_code
        self._lines = lines or []

    def json(self):
        return self._json

    def raise_for_status(self):
        pass

    def iter_lines(self):
        return iter(self._lines)

    def close(self):
        pass


class MockSession:
    """Captures POST kwargs for payload inspection."""

    def __init__(self, response=None):
        self.captured = {}
        self._response = response or MockResponse()

    def post(self, url, json=None, stream=False, timeout=None, headers=None):
        self.captured["url"] = url
        self.captured["json"] = json
        self.captured["stream"] = stream
        self.captured["timeout"] = timeout
        self.captured["headers"] = headers
        return self._response


def _make_transport(model, session):
    """Build a minimal mock transport."""
    return type(
        "MockTransport",
        (),
        {
            "model": model,
            "session": session,
            "api_base": "http://localhost:1234/v1",
            "get_endpoint": lambda self, path: f"http://localhost:1234/v1/{path.lstrip('/')}",
        },
    )()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _disable_jit(monkeypatch):
    """Prevent JIT model loading so tests never hit LM Studio."""
    monkeypatch.setattr("llm.jit_loader.ensure_model_loaded", lambda *a, **kw: None)


@pytest.fixture()
def session():
    return MockSession()


@pytest.fixture()
def default_transport(session):
    """Transport with model='default' — simulates sentinel escape."""
    return _make_transport("default", session)


@pytest.fixture()
def real_transport(session):
    """Transport with a real model name."""
    return _make_transport("qwen/qwen3-coder-next", session)


# ===========================================================================
# 1. is_model_sentinel() helper — 5 unit tests (pass immediately)
# ===========================================================================

class TestIsModelSentinel:
    """Unit tests for the is_model_sentinel() helper."""

    def test_default_keyword_is_sentinel(self):
        assert is_model_sentinel("default") is True

    def test_none_is_sentinel(self):
        assert is_model_sentinel(None) is True

    def test_empty_string_is_sentinel(self):
        assert is_model_sentinel("") is True

    def test_real_model_not_sentinel(self):
        assert is_model_sentinel("qwen/qwen3-coder-next") is False

    def test_whitespace_not_sentinel(self):
        assert is_model_sentinel(" ") is False


# ===========================================================================
# 2. V1: chat_client.text_completion — 3 tests (FAIL until C2)
# ===========================================================================

class TestV1TextCompletion:
    """V1: ChatClient.text_completion must guard against sentinel."""

    def test_happy_real_model_included(self, real_transport, session):
        """Real model name → payload includes 'model' key."""
        client = ChatClient(real_transport)
        client.text_completion(prompt="hello", model="qwen/qwen3-coder-next")
        payload = session.captured["json"]
        assert payload["model"] == "qwen/qwen3-coder-next"

    def test_negative_sentinel_omitted(self, default_transport, session):
        """model=None with transport.model='default' → 'model' key OMITTED."""
        client = ChatClient(default_transport)
        client.text_completion(prompt="hello")
        payload = session.captured["json"]
        assert "model" not in payload, (
            f"Sentinel 'default' leaked into text_completion payload: {payload}"
        )

    def test_sentinel_intercept_no_default_in_body(self, default_transport, session):
        """Literal 'default' must never appear as model value in POST body."""
        client = ChatClient(default_transport)
        client.text_completion(prompt="hello", model="default")
        payload = session.captured["json"]
        assert payload.get("model") != "default", (
            "Literal 'default' found in text_completion POST body"
        )


# ===========================================================================
# 3. V2: responses_client.create_response — 4 tests (FAIL until C3)
# ===========================================================================

class TestV2CreateResponse:
    """V2: ResponsesClient.create_response must guard after substitution."""

    def test_happy_real_model_included(self, real_transport, session):
        """Real model name → payload includes 'model' key."""
        client = ResponsesClient(real_transport)
        client.create_response(input_text="hello", model="qwen/qwen3-coder-next")
        payload = session.captured["json"]
        assert payload["model"] == "qwen/qwen3-coder-next"

    def test_negative_sentinel_omitted(self, default_transport, session):
        """model='default' with transport.model='default' → 'model' key OMITTED."""
        client = ResponsesClient(default_transport)
        client.create_response(input_text="hello")
        payload = session.captured["json"]
        assert "model" not in payload, (
            f"Sentinel 'default' leaked into create_response payload: {payload}"
        )

    def test_sentinel_intercept_no_default_in_body(self, default_transport, session):
        """Literal 'default' must never appear as model value in POST body."""
        client = ResponsesClient(default_transport)
        client.create_response(input_text="hello", model="default")
        payload = session.captured["json"]
        assert payload.get("model") != "default", (
            "Literal 'default' found in create_response POST body"
        )

    def test_double_default_model_none_transport_default(self, default_transport, session):
        """model=None + transport.model='default' → Pattern B double-default → OMIT."""
        client = ResponsesClient(default_transport)
        client.create_response(input_text="hello", model=None)
        payload = session.captured["json"]
        assert "model" not in payload, (
            f"Double-default leaked into create_response payload: {payload}"
        )


# ===========================================================================
# 4. V3: streaming_client.stream_create_response — 4 tests (FAIL until C4)
# ===========================================================================

class TestV3StreamCreateResponse:
    """V3: StreamingClient.stream_create_response must guard after substitution."""

    def _make_streaming_session(self):
        """Session that returns a streaming response with SSE lines."""
        lines = [b"data: [DONE]"]
        return MockSession(response=MockResponse(lines=lines))

    def test_happy_real_model_included(self, real_transport):
        """Real model name → payload includes 'model' key."""
        session = self._make_streaming_session()
        transport = _make_transport("qwen/qwen3-coder-next", session)
        client = StreamingClient(transport)
        # Consume the generator to trigger the POST
        list(client.stream_create_response(input_text="hello", model="qwen/qwen3-coder-next"))
        payload = session.captured["json"]
        assert payload["model"] == "qwen/qwen3-coder-next"

    def test_negative_sentinel_omitted(self):
        """model='default' with transport.model='default' → 'model' key OMITTED."""
        session = self._make_streaming_session()
        transport = _make_transport("default", session)
        client = StreamingClient(transport)
        list(client.stream_create_response(input_text="hello"))
        payload = session.captured["json"]
        assert "model" not in payload, (
            f"Sentinel 'default' leaked into stream_create_response payload: {payload}"
        )

    def test_sentinel_intercept_no_default_in_body(self):
        """Literal 'default' must never appear as model value in POST body."""
        session = self._make_streaming_session()
        transport = _make_transport("default", session)
        client = StreamingClient(transport)
        list(client.stream_create_response(input_text="hello", model="default"))
        payload = session.captured["json"]
        assert payload.get("model") != "default", (
            "Literal 'default' found in stream_create_response POST body"
        )

    def test_double_default_model_none_transport_default(self):
        """model=None + transport.model='default' → Pattern B double-default → OMIT."""
        session = self._make_streaming_session()
        transport = _make_transport("default", session)
        client = StreamingClient(transport)
        list(client.stream_create_response(input_text="hello", model=None))
        payload = session.captured["json"]
        assert "model" not in payload, (
            f"Double-default leaked into stream_create_response payload: {payload}"
        )


# ===========================================================================
# 5. V4: native_chat_client.native_chat — 4 tests (FAIL until C5)
# ===========================================================================

class TestV4NativeChat:
    """V4: NativeChatClient.native_chat must guard against sentinel."""

    def _make_streaming_session(self):
        """Session returning a native SSE response."""
        lines = [b"event: chat.complete", b"data: {}", b""]
        return MockSession(response=MockResponse(lines=lines))

    def test_happy_real_model_included(self):
        """Real model name → payload includes 'model' key."""
        session = self._make_streaming_session()
        transport = _make_transport("qwen/qwen3-coder-next", session)
        client = NativeChatClient(transport)
        list(client.native_chat(
            messages=[{"role": "user", "content": "hi"}],
            model="qwen/qwen3-coder-next",
        ))
        payload = session.captured["json"]
        assert payload["model"] == "qwen/qwen3-coder-next"

    def test_negative_sentinel_omitted(self):
        """model=None with transport.model='default' → 'model' key OMITTED."""
        session = self._make_streaming_session()
        transport = _make_transport("default", session)
        client = NativeChatClient(transport)
        list(client.native_chat(messages=[{"role": "user", "content": "hi"}]))
        payload = session.captured["json"]
        assert "model" not in payload, (
            f"Sentinel 'default' leaked into native_chat payload: {payload}"
        )

    def test_sentinel_intercept_no_default_in_body(self):
        """Literal 'default' must never appear as model value in POST body."""
        session = self._make_streaming_session()
        transport = _make_transport("default", session)
        client = NativeChatClient(transport)
        list(client.native_chat(
            messages=[{"role": "user", "content": "hi"}],
            model="default",
        ))
        payload = session.captured["json"]
        assert payload.get("model") != "default", (
            "Literal 'default' found in native_chat POST body"
        )

    def test_double_default_model_none_transport_default(self):
        """model=None + transport.model='default' → 'model' key OMITTED."""
        session = self._make_streaming_session()
        transport = _make_transport("default", session)
        client = NativeChatClient(transport)
        list(client.native_chat(
            messages=[{"role": "user", "content": "hi"}],
            model=None,
        ))
        payload = session.captured["json"]
        assert "model" not in payload, (
            f"Double-default leaked into native_chat payload: {payload}"
        )


# ===========================================================================
# 6. Regression: existing guards G1 + G2 still work — 2 tests
# ===========================================================================

class TestRegressionExistingGuards:
    """Regression: existing guards in chat_completion and anthropic_messages."""

    def test_g1_chat_completion_omits_default(self, default_transport, session):
        """G1: ChatClient.chat_completion already guards — sentinel never in payload."""
        client = ChatClient(default_transport)
        client.chat_completion(messages=[{"role": "user", "content": "hi"}])
        payload = session.captured["json"]
        assert "model" not in payload, (
            "Regression: chat_completion guard broke — sentinel leaked"
        )

    def test_g2_anthropic_messages_omits_default(self, default_transport, session):
        """G2: AnthropicClient.anthropic_messages already guards — sentinel never in payload."""
        client = AnthropicClient(default_transport)
        client.anthropic_messages(messages=[{"role": "user", "content": "hi"}])
        payload = session.captured["json"]
        assert "model" not in payload, (
            "Regression: anthropic_messages guard broke — sentinel leaked"
        )
