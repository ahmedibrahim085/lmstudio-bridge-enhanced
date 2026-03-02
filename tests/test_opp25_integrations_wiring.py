"""Tests for OPP-25 Part 2 — integrations parameter wired into NativeChatClient.

Verifies that ``NativeChatClient.native_chat()`` and the ``LLMClient.native_chat()``
facade both accept an ``integrations`` parameter and include the built payload
under the ``"integrations"`` key in the POST body when integrations are provided.

Test categories (Req 07):
- Happy    (4): single integration, allowed_tools, multiple, deduplication
- Negative (2): empty server_id raises before POST, whitespace server_id raises before POST
- Edge     (3): None omitted from payload, [] omitted from payload, other fields unaffected
- Boundary (2): MAX_INTEGRATIONS_PER_REQUEST importable == 20, backward compat (no arg)

RED phase — ``native_chat()`` does not yet accept ``integrations``.
All tests that pass integrations will fail with TypeError until GREEN adds the parameter.
The boundary test ``test_max_integrations_constant_exists`` will pass in RED (constant
already exported). All other tests exercise the not-yet-implemented wiring.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config.constants import LMSTUDIO_TESTING_ENV_VAR  # noqa: E402

os.environ.setdefault(LMSTUDIO_TESTING_ENV_VAR, "1")

# ---------------------------------------------------------------------------
# RED-phase imports — NativeChatClient exists; integrations param does not yet
# ---------------------------------------------------------------------------
from llm.native_chat_client import NativeChatClient  # noqa: E402
from mcp_client.ephemeral import EphemeralIntegration  # noqa: E402
from config.constants import MAX_INTEGRATIONS_PER_REQUEST  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sse_lines(*blocks):
    """Build encoded SSE lines from (event_type, json_str) pairs.

    Each block produces three entries: ``event: <type>``, ``data: <json>``,
    and a blank separator — matching the native LM Studio wire format.
    """
    lines = []
    for event_type, json_str in blocks:
        lines.append(f"event: {event_type}".encode())
        lines.append(f"data: {json_str}".encode())
        lines.append(b"")
    return lines


_MINIMAL_SSE = _sse_lines(
    ("chat.start", '{"model": "test-model"}'),
    ("chat.end", '{"result": {"content": ""}}'),
)


# ---------------------------------------------------------------------------
# Test doubles — same pattern as test_opp19_native_chat_client.py
# ---------------------------------------------------------------------------

class MockResponse:
    """Minimal stand-in for a ``requests.Response`` in streaming mode."""

    def __init__(self, lines=None, status_code=200):
        self._lines = lines if lines is not None else []
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

    def __init__(self, response=None):
        self.captured = {}
        self._response = response if response is not None else MockResponse(_MINIMAL_SSE)
        self.post_called = False

    def post(self, url, json=None, stream=False, timeout=None):
        self.post_called = True
        self.captured["url"] = url
        self.captured["json"] = json
        self.captured["stream"] = stream
        self.captured["timeout"] = timeout
        return self._response


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

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
    """Disable JIT model loading so tests never hit LM Studio."""
    monkeypatch.setattr("llm.jit_loader.ensure_model_loaded", lambda *a, **kw: None)


# ---------------------------------------------------------------------------
# Happy path tests
# ---------------------------------------------------------------------------

class TestIntegrationsHappy:
    """Happy: integrations parameter is accepted and included in the POST body."""

    @pytest.mark.unit
    def test_integrations_included_in_payload(self, mock_transport, mock_session):
        """A single EphemeralIntegration is serialised under 'integrations' in the POST body.

        Constructs one EphemeralIntegration with server_id='my-mcp' and type='mcp',
        passes it via ``integrations=[...]`` to ``native_chat()``, then asserts that:
        - The POST body contains the key ``'integrations'``
        - The list has exactly one entry
        - The entry has ``"type": "mcp"`` and ``"id": "my-mcp"``
        """
        integration = EphemeralIntegration(server_id="my-mcp")

        client = NativeChatClient(mock_transport)
        list(
            client.native_chat(
                messages=[{"role": "user", "content": "hi"}],
                integrations=[integration],
            )
        )

        payload = mock_session.captured.get("json", {})
        assert "integrations" in payload, (
            "POST body must contain 'integrations' key when integrations are provided"
        )
        assert len(payload["integrations"]) == 1, (
            f"Expected 1 integration entry, got {len(payload['integrations'])}"
        )
        entry = payload["integrations"][0]
        assert entry["type"] == "mcp", f"Expected type='mcp', got {entry['type']!r}"
        assert entry["id"] == "my-mcp", f"Expected id='my-mcp', got {entry['id']!r}"

    @pytest.mark.unit
    def test_integrations_with_allowed_tools(self, mock_transport, mock_session):
        """EphemeralIntegration with allowed_tools produces 'allowed_tools' list in payload.

        Constructs an integration with allowed_tools=('read_file', 'write_file'),
        calls ``native_chat()`` with it, then asserts that the serialised entry
        includes ``"allowed_tools": ["read_file", "write_file"]``.
        """
        integration = EphemeralIntegration(
            server_id="fs-server",
            allowed_tools=("read_file", "write_file"),
        )

        client = NativeChatClient(mock_transport)
        list(
            client.native_chat(
                messages=[{"role": "user", "content": "hi"}],
                integrations=[integration],
            )
        )

        payload = mock_session.captured.get("json", {})
        assert "integrations" in payload, "POST body must contain 'integrations'"
        entry = payload["integrations"][0]
        assert "allowed_tools" in entry, (
            "Entry must contain 'allowed_tools' when integration.allowed_tools is set"
        )
        assert entry["allowed_tools"] == ["read_file", "write_file"], (
            f"Expected ['read_file', 'write_file'], got {entry['allowed_tools']!r}"
        )

    @pytest.mark.unit
    def test_multiple_integrations_in_payload(self, mock_transport, mock_session):
        """Two distinct EphemeralIntegrations both appear in the payload list.

        Constructs two integrations with different server_ids and asserts that
        the POST body contains exactly two entries in 'integrations', one for
        each server_id.
        """
        integrations = [
            EphemeralIntegration(server_id="server-alpha"),
            EphemeralIntegration(server_id="server-beta"),
        ]

        client = NativeChatClient(mock_transport)
        list(
            client.native_chat(
                messages=[{"role": "user", "content": "hi"}],
                integrations=integrations,
            )
        )

        payload = mock_session.captured.get("json", {})
        assert "integrations" in payload, "POST body must contain 'integrations'"
        assert len(payload["integrations"]) == 2, (
            f"Expected 2 integration entries, got {len(payload['integrations'])}"
        )
        ids_in_payload = {e["id"] for e in payload["integrations"]}
        assert ids_in_payload == {"server-alpha", "server-beta"}, (
            f"Expected server-alpha and server-beta, got {ids_in_payload!r}"
        )

    @pytest.mark.unit
    def test_integrations_deduplicates_in_payload(self, mock_transport, mock_session):
        """Duplicate server_id entries are deduplicated (last-wins) in the payload.

        Provides two EphemeralIntegration objects with the same server_id but
        different allowed_tools. Asserts that only one entry appears in 'integrations'
        and it reflects the last-provided configuration (last-wins deduplication
        is delegated to build_integrations_payload).
        """
        integrations = [
            EphemeralIntegration(server_id="dup-server", allowed_tools=("tool_a",)),
            EphemeralIntegration(server_id="dup-server", allowed_tools=("tool_b",)),
        ]

        client = NativeChatClient(mock_transport)
        list(
            client.native_chat(
                messages=[{"role": "user", "content": "hi"}],
                integrations=integrations,
            )
        )

        payload = mock_session.captured.get("json", {})
        assert "integrations" in payload, "POST body must contain 'integrations'"
        assert len(payload["integrations"]) == 1, (
            f"Expected 1 entry after deduplication, got {len(payload['integrations'])}"
        )
        entry = payload["integrations"][0]
        assert entry["id"] == "dup-server", (
            f"Expected id='dup-server', got {entry['id']!r}"
        )
        # Last-wins: allowed_tools should be from the second integration
        assert entry.get("allowed_tools") == ["tool_b"], (
            f"Expected last-wins allowed_tools=['tool_b'], got {entry.get('allowed_tools')!r}"
        )


# ---------------------------------------------------------------------------
# Negative tests
# ---------------------------------------------------------------------------

class TestIntegrationsNegative:
    """Negative: invalid integrations raise ValueError before any HTTP call."""

    @pytest.mark.unit
    def test_invalid_integration_raises_before_post(self, mock_transport, mock_session):
        """EphemeralIntegration with empty server_id raises ValueError, no HTTP call made.

        Constructs an integration with server_id='' (empty string), passes it
        to ``native_chat()``, and asserts that ValueError is raised. Also asserts
        that MockSession.post was never called — validation must short-circuit
        before any network activity.
        """
        integration = EphemeralIntegration(server_id="")

        client = NativeChatClient(mock_transport)
        with pytest.raises(ValueError, match="server_id"):
            list(
                client.native_chat(
                    messages=[{"role": "user", "content": "hi"}],
                    integrations=[integration],
                )
            )

        assert not mock_session.post_called, (
            "session.post() must NOT be called when validation raises ValueError"
        )

    @pytest.mark.unit
    def test_integrations_validation_whitespace_id(self, mock_transport, mock_session):
        """EphemeralIntegration with whitespace-only server_id raises ValueError before POST.

        server_id='   ' (three spaces) is semantically empty. Validates that
        the whitespace check in validate_integration() is exercised through the
        native_chat() wiring, and no HTTP call occurs.
        """
        integration = EphemeralIntegration(server_id="   ")

        client = NativeChatClient(mock_transport)
        with pytest.raises(ValueError, match="server_id"):
            list(
                client.native_chat(
                    messages=[{"role": "user", "content": "hi"}],
                    integrations=[integration],
                )
            )

        assert not mock_session.post_called, (
            "session.post() must NOT be called when validation raises ValueError"
        )


# ---------------------------------------------------------------------------
# Edge tests
# ---------------------------------------------------------------------------

class TestIntegrationsEdge:
    """Edge: None and empty-list integrations omit the key; other fields unaffected."""

    @pytest.mark.unit
    def test_integrations_none_omitted_from_payload(self, mock_transport, mock_session):
        """When integrations=None, the 'integrations' key is absent from the POST body.

        Calls ``native_chat()`` with ``integrations=None`` (the default) and
        asserts that the captured JSON payload does NOT contain the key
        'integrations'. Existing fields (messages, model, etc.) must still be present.
        """
        client = NativeChatClient(mock_transport)
        list(
            client.native_chat(
                messages=[{"role": "user", "content": "hi"}],
                integrations=None,
            )
        )

        payload = mock_session.captured.get("json", {})
        assert "integrations" not in payload, (
            f"'integrations' key must be absent when integrations=None, payload keys: {list(payload)}"
        )
        # Core fields must still be present
        assert "messages" in payload, "POST body must still contain 'messages'"
        assert "model" in payload, "POST body must still contain 'model'"

    @pytest.mark.unit
    def test_integrations_empty_list_omitted_from_payload(self, mock_transport, mock_session):
        """When integrations=[], the 'integrations' key is absent from the POST body.

        An empty list is semantically equivalent to no integrations. The POST
        body must not include the 'integrations' key at all when the list is empty.
        """
        client = NativeChatClient(mock_transport)
        list(
            client.native_chat(
                messages=[{"role": "user", "content": "hi"}],
                integrations=[],
            )
        )

        payload = mock_session.captured.get("json", {})
        assert "integrations" not in payload, (
            f"'integrations' key must be absent when integrations=[], payload keys: {list(payload)}"
        )

    @pytest.mark.unit
    def test_integrations_does_not_affect_other_payload_fields(self, mock_transport, mock_session):
        """All other payload fields are present and correct when integrations is provided.

        Passes a full set of parameters (messages, model, temperature, max_tokens,
        stream=True) together with one integration, and asserts that every standard
        field still appears in the POST body with the correct values.
        """
        integration = EphemeralIntegration(server_id="side-effect-check")
        input_messages = [{"role": "user", "content": "check fields"}]

        client = NativeChatClient(mock_transport)
        list(
            client.native_chat(
                messages=input_messages,
                model="explicit-model",
                temperature=0.42,
                max_tokens=512,
                stream=True,
                integrations=[integration],
            )
        )

        payload = mock_session.captured.get("json", {})
        assert payload.get("messages") == input_messages, (
            f"Expected messages={input_messages!r}, got {payload.get('messages')!r}"
        )
        assert payload.get("model") == "explicit-model", (
            f"Expected model='explicit-model', got {payload.get('model')!r}"
        )
        assert payload.get("temperature") == 0.42, (
            f"Expected temperature=0.42, got {payload.get('temperature')!r}"
        )
        assert payload.get("max_tokens") == 512, (
            f"Expected max_tokens=512, got {payload.get('max_tokens')!r}"
        )
        assert payload.get("stream") is True, (
            f"Expected stream=True, got {payload.get('stream')!r}"
        )
        assert "integrations" in payload, (
            "POST body must still contain 'integrations' when integrations are provided"
        )


# ---------------------------------------------------------------------------
# Boundary tests
# ---------------------------------------------------------------------------

class TestIntegrationsBoundary:
    """Boundary: constant availability and backward-compatibility."""

    @pytest.mark.unit
    def test_max_integrations_constant_exists(self):
        """MAX_INTEGRATIONS_PER_REQUEST is importable from config.constants and equals 20.

        This constant guards callers against sending too many integrations in
        one request. It must be importable at the module level and have the
        expected value of 20 as specified in OPP-25.
        """
        assert MAX_INTEGRATIONS_PER_REQUEST == 20, (
            f"Expected MAX_INTEGRATIONS_PER_REQUEST == 20, got {MAX_INTEGRATIONS_PER_REQUEST!r}"
        )

    @pytest.mark.unit
    def test_integration_parameter_defaults_to_none(self, mock_transport, mock_session):
        """Calling native_chat() without the integrations argument works unchanged.

        Ensures backward compatibility: existing callers that do not pass
        ``integrations`` must continue to work without modification, and the
        POST body must not include 'integrations'.
        """
        client = NativeChatClient(mock_transport)
        # Must not raise TypeError — 'integrations' must default to None
        list(client.native_chat(messages=[{"role": "user", "content": "hello"}]))

        payload = mock_session.captured.get("json", {})
        assert "integrations" not in payload, (
            f"'integrations' must be absent when not passed, payload keys: {list(payload)}"
        )
        assert mock_session.post_called, (
            "session.post() must have been called for a normal native_chat() call"
        )
