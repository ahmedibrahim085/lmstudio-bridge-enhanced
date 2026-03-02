"""Tests for OPP-19 Part 2 — NativeChatClient.

Tests for ``llm.native_chat_client.NativeChatClient``, which wraps the
LM Studio native ``/api/v1/chat`` streaming endpoint and yields
``NativeSSEEvent`` objects.

Test categories (Req 07):
- Happy  (4): yields events, correct endpoint, messages in payload, model in payload
- Negative (3): ConnectionError → LLMConnectionError, Timeout → LLMTimeoutError,
                HTTPError 500 → LLMResponseError
- Edge   (3): default model from transport, stream=True always in payload,
              custom temperature/max_tokens forwarded
- Boundary (2): empty messages list accepted, return type is a generator

RED phase — ``llm/native_chat_client.py`` does not exist yet.
All tests will fail with ImportError until GREEN phase creates the module.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config.constants import LMSTUDIO_TESTING_ENV_VAR  # noqa: E402 — must precede production imports

os.environ.setdefault(LMSTUDIO_TESTING_ENV_VAR, "1")

# ---------------------------------------------------------------------------
# RED-phase import — will raise ImportError until GREEN creates the module
# ---------------------------------------------------------------------------
from llm.native_chat_client import NativeChatClient  # noqa: E402

from config.constants import NATIVE_CHAT_ENDPOINT  # noqa: E402
from llm.exceptions import (  # noqa: E402
    LLMConnectionError,
    LLMResponseError,
    LLMTimeoutError,
)
from llm.native_sse_parser import NativeSSEEvent  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sse_lines(*blocks):
    """Build a list of encoded SSE lines from (event_type, json_str) pairs.

    Each block produces three entries:  ``event: <type>``, ``data: <json>``,
    and a blank separator — matching the native LM Studio wire format.
    """
    lines = []
    for event_type, json_str in blocks:
        lines.append(f"event: {event_type}".encode())
        lines.append(f"data: {json_str}".encode())
        lines.append(b"")
    return lines


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

class MockResponse:
    """Minimal stand-in for a ``requests.Response`` in streaming mode."""

    def __init__(self, lines, status_code=200):
        self._lines = lines
        self.status_code = status_code

    def iter_lines(self):
        return iter(self._lines)

    def raise_for_status(self):
        if self.status_code >= 400:
            from requests.exceptions import HTTPError

            raise HTTPError(response=self)

    def close(self):
        pass


class MockSession:
    """Minimal stand-in for ``requests.Session`` that captures POST args."""

    def __init__(self):
        self.captured = {}
        self._response = MockResponse([])

    def post(self, url, json=None, stream=False, timeout=None):
        self.captured["url"] = url
        self.captured["json"] = json
        self.captured["stream"] = stream
        self.captured["timeout"] = timeout
        return self._response


@pytest.fixture()
def mock_session():
    """Return a fresh MockSession for each test."""
    return MockSession()


@pytest.fixture()
def mock_transport(mock_session):
    """Return a minimal mock HTTPTransport backed by mock_session."""
    transport = type(
        "MockTransport",
        (),
        {
            "model": "test-model",
            "session": mock_session,
            "get_endpoint": lambda self, path: f"http://localhost:1234/{path.lstrip('/')}",
        },
    )()
    return transport


@pytest.fixture(autouse=True)
def mock_jit_loader(monkeypatch):
    """Disable JIT model loading so tests never hit LM Studio.

    Included here for GREEN phase — during RED the ImportError on
    ``llm.native_chat_client`` fires before any fixture runs.
    """
    monkeypatch.setattr("llm.jit_loader.ensure_model_loaded", lambda *a, **kw: None)


# ---------------------------------------------------------------------------
# Happy path tests
# ---------------------------------------------------------------------------

class TestNativeChatClientHappy:
    """Happy: NativeChatClient streams events correctly."""

    @pytest.mark.unit
    def test_native_chat_yields_events(self, mock_transport, mock_session):
        """native_chat() yields NativeSSEEvent objects in stream order.

        Feed three SSE blocks (chat.start → message.delta → chat.end) and
        assert that the generator yields exactly three NativeSSEEvent objects
        with the correct event_type values in order.
        """
        sse_lines = _sse_lines(
            ("chat.start", '{"model": "test-model"}'),
            ("message.delta", '{"content": "Hello"}'),
            ("chat.end", '{"result": {"content": "Hello"}}'),
        )
        mock_session._response = MockResponse(sse_lines)
        mock_transport.session = mock_session

        client = NativeChatClient(mock_transport)
        events = list(client.native_chat(messages=[{"role": "user", "content": "hi"}]))

        assert len(events) == 3
        assert all(isinstance(e, NativeSSEEvent) for e in events)
        assert events[0].event_type == "chat.start"
        assert events[1].event_type == "message.delta"
        assert events[2].event_type == "chat.end"

    @pytest.mark.unit
    def test_native_chat_posts_to_correct_endpoint(self, mock_transport, mock_session):
        """native_chat() POSTs to the URL containing NATIVE_CHAT_ENDPOINT path.

        NATIVE_CHAT_ENDPOINT is ``/api/v1/chat``; the captured URL must
        include that path segment.
        """
        mock_transport.session = mock_session

        client = NativeChatClient(mock_transport)
        list(client.native_chat(messages=[{"role": "user", "content": "hi"}]))

        captured_url = mock_session.captured.get("url", "")
        assert NATIVE_CHAT_ENDPOINT.lstrip("/") in captured_url, (
            f"Expected NATIVE_CHAT_ENDPOINT path '{NATIVE_CHAT_ENDPOINT}' "
            f"in URL, got: {captured_url!r}"
        )

    @pytest.mark.unit
    def test_native_chat_sends_messages_in_payload(self, mock_transport, mock_session):
        """native_chat() includes the 'messages' key in the POST body.

        The exact list passed in must appear verbatim under the ``messages``
        key of the captured JSON payload.
        """
        mock_transport.session = mock_session
        input_messages = [{"role": "user", "content": "hello world"}]

        client = NativeChatClient(mock_transport)
        list(client.native_chat(messages=input_messages))

        payload = mock_session.captured.get("json", {})
        assert "messages" in payload, "POST body must contain 'messages' key"
        assert payload["messages"] == input_messages

    @pytest.mark.unit
    def test_native_chat_passes_model_in_payload(self, mock_transport, mock_session):
        """When model='custom-model' is supplied, it appears in the POST body."""
        mock_transport.session = mock_session

        client = NativeChatClient(mock_transport)
        list(
            client.native_chat(
                messages=[{"role": "user", "content": "hi"}],
                model="custom-model",
            )
        )

        payload = mock_session.captured.get("json", {})
        assert payload.get("model") == "custom-model"


# ---------------------------------------------------------------------------
# Negative tests
# ---------------------------------------------------------------------------

class TestNativeChatClientNegative:
    """Negative: HTTP/network errors are translated to LLM exception types."""

    @pytest.mark.unit
    def test_native_chat_connection_error_raises(self, mock_transport, mock_session):
        """ConnectionError from session.post() becomes LLMConnectionError."""
        import requests

        mock_session.post = lambda *a, **kw: (_ for _ in ()).throw(
            requests.ConnectionError("refused")
        )
        mock_transport.session = mock_session

        client = NativeChatClient(mock_transport)
        with pytest.raises(LLMConnectionError):
            list(client.native_chat(messages=[{"role": "user", "content": "hi"}]))

    @pytest.mark.unit
    def test_native_chat_timeout_raises(self, mock_transport, mock_session):
        """Timeout from session.post() becomes LLMTimeoutError."""
        import requests

        mock_session.post = lambda *a, **kw: (_ for _ in ()).throw(
            requests.Timeout("timed out")
        )
        mock_transport.session = mock_session

        client = NativeChatClient(mock_transport)
        with pytest.raises(LLMTimeoutError):
            list(client.native_chat(messages=[{"role": "user", "content": "hi"}]))

    @pytest.mark.unit
    def test_native_chat_http_error_raises(self, mock_transport, mock_session):
        """HTTP 500 from raise_for_status() becomes LLMResponseError."""
        mock_session._response = MockResponse([], status_code=500)
        mock_transport.session = mock_session

        client = NativeChatClient(mock_transport)
        with pytest.raises(LLMResponseError):
            list(client.native_chat(messages=[{"role": "user", "content": "hi"}]))


# ---------------------------------------------------------------------------
# Edge tests
# ---------------------------------------------------------------------------

class TestNativeChatClientEdge:
    """Edge: Parameter resolution and payload field enforcement."""

    @pytest.mark.unit
    def test_native_chat_uses_transport_model_as_default(self, mock_transport, mock_session):
        """When model=None, the payload uses transport.model ('test-model')."""
        mock_transport.session = mock_session

        client = NativeChatClient(mock_transport)
        list(client.native_chat(messages=[{"role": "user", "content": "hi"}], model=None))

        payload = mock_session.captured.get("json", {})
        assert payload.get("model") == "test-model", (
            f"Expected transport.model 'test-model' in payload, got: {payload.get('model')!r}"
        )

    @pytest.mark.unit
    def test_native_chat_stream_true_in_payload(self, mock_transport, mock_session):
        """The POST body always contains ``'stream': True``.

        NativeChatClient uses streaming unconditionally; this ensures the
        flag is never accidentally omitted.
        """
        mock_transport.session = mock_session

        client = NativeChatClient(mock_transport)
        list(client.native_chat(messages=[{"role": "user", "content": "hi"}]))

        payload = mock_session.captured.get("json", {})
        assert payload.get("stream") is True, (
            f"Expected 'stream': True in payload, got: {payload.get('stream')!r}"
        )

    @pytest.mark.unit
    def test_native_chat_custom_temperature_and_max_tokens(self, mock_transport, mock_session):
        """temperature=0.3 and max_tokens=2048 both appear in the POST body."""
        mock_transport.session = mock_session

        client = NativeChatClient(mock_transport)
        list(
            client.native_chat(
                messages=[{"role": "user", "content": "hi"}],
                temperature=0.3,
                max_tokens=2048,
            )
        )

        payload = mock_session.captured.get("json", {})
        assert payload.get("temperature") == 0.3, (
            f"Expected temperature=0.3, got: {payload.get('temperature')!r}"
        )
        assert payload.get("max_tokens") == 2048, (
            f"Expected max_tokens=2048, got: {payload.get('max_tokens')!r}"
        )


# ---------------------------------------------------------------------------
# Boundary tests
# ---------------------------------------------------------------------------

class TestNativeChatClientBoundary:
    """Boundary: Structural invariants of NativeChatClient."""

    @pytest.mark.unit
    def test_native_chat_empty_messages_accepted(self, mock_transport, mock_session):
        """An empty messages list is forwarded to the server without ValueError.

        The native /api/v1/chat endpoint decides whether an empty list is
        valid; NativeChatClient must not perform pre-validation here.
        """
        mock_transport.session = mock_session

        client = NativeChatClient(mock_transport)
        # Must not raise — just consume the (empty) stream
        list(client.native_chat(messages=[]))

        payload = mock_session.captured.get("json", {})
        assert payload.get("messages") == [], (
            f"Expected empty messages list in payload, got: {payload.get('messages')!r}"
        )

    @pytest.mark.unit
    def test_native_chat_yields_generator_type(self, mock_transport, mock_session):
        """native_chat() returns a generator (has __next__ attribute).

        Consumers must be able to lazily pull events without materialising
        the entire stream — this test confirms the generator protocol.
        """
        mock_transport.session = mock_session

        client = NativeChatClient(mock_transport)
        result = client.native_chat(messages=[{"role": "user", "content": "hi"}])

        assert hasattr(result, "__next__"), (
            f"native_chat() must return a generator; got {type(result).__name__!r}"
        )
