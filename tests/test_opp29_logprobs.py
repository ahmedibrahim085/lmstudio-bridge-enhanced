"""Tests for OPP-29: Log-Probabilities parameter support.

Covers:
  - logprobs=True, top_logprobs=5 → present in payload
  - logprobs=False → not in payload
  - logprobs=True without top_logprobs → defaults to DEFAULT_TOP_LOGPROBS
  - top_logprobs validation: -1 → ValueError, 25 → ValueError, 0 → ValueError
  - top_logprobs=20 → max valid (boundary)
  - top_logprobs=1 → min valid (boundary)
  - Responses API also supports logprobs
  - Constants exist in config.constants

Test categories (Req 07):
- Happy: Tests 1-2 — logprobs in payload, parsed from response
- Negative: Tests 3-5 — invalid top_logprobs values
- Edge: Tests 6-7 — logprobs=False, logprobs=True with default
- Boundary: Tests 8-10 — top_logprobs min/max, constants
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_config(
    api_base: str = "http://localhost:1234/v1",
    default_model: str = "test-model",
) -> MagicMock:
    mock = MagicMock()
    mock.return_value.lmstudio.api_base = api_base
    mock.return_value.lmstudio.default_model = default_model
    return mock


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _mock_config():
    with patch("llm.http_transport.get_config", _make_mock_config()):
        yield


@pytest.fixture(autouse=True)
def _skip_jit_loading():
    with patch("llm.jit_loader.LMSHelper.is_installed", return_value=False):
        yield


@pytest.fixture
def mock_session():
    session = MagicMock()
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "choices": [{
            "message": {"content": "hello"},
            "logprobs": {
                "content": [
                    {"token": "hello", "logprob": -0.5, "top_logprobs": [
                        {"token": "hello", "logprob": -0.5},
                        {"token": "hi", "logprob": -1.2},
                    ]},
                ]
            },
        }]
    }
    response.raise_for_status.return_value = None
    session.post.return_value = response
    session.get.return_value = response
    return session


@pytest.fixture
def chat_client(mock_session):
    from llm.chat_client import ChatClient
    from llm.http_transport import HTTPTransport

    transport = HTTPTransport(session=mock_session)
    return ChatClient(transport)


@pytest.fixture
def responses_client(mock_session):
    from llm.responses_client import ResponsesClient
    from llm.http_transport import HTTPTransport

    transport = HTTPTransport(session=mock_session)
    return ResponsesClient(transport)


@pytest.fixture
def facade_client(mock_session):
    from llm.llm_client import LLMClient

    return LLMClient(session=mock_session)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

class TestLogprobsHappy:
    """Happy: logprobs and top_logprobs appear in payload."""

    @pytest.mark.unit
    def test_logprobs_true_top5_in_payload(self, chat_client, mock_session):
        """logprobs=True, top_logprobs=5 → both present in payload."""
        chat_client.chat_completion(
            messages=[{"role": "user", "content": "hi"}],
            logprobs=True,
            top_logprobs=5,
        )

        payload = mock_session.post.call_args.kwargs.get("json") or mock_session.post.call_args[1]["json"]
        assert payload["logprobs"] is True
        assert payload["top_logprobs"] == 5

    @pytest.mark.unit
    def test_logprobs_in_responses_api(self, responses_client, mock_session):
        """Responses API also passes logprobs params to payload."""
        mock_session.post.return_value.json.return_value = {"id": "resp_1", "output": []}
        responses_client.create_response(
            input_text="test",
            logprobs=True,
            top_logprobs=3,
        )

        payload = mock_session.post.call_args.kwargs.get("json") or mock_session.post.call_args[1]["json"]
        assert payload["logprobs"] is True
        assert payload["top_logprobs"] == 3


# ---------------------------------------------------------------------------
# Negative
# ---------------------------------------------------------------------------

class TestLogprobsNegative:
    """Negative: invalid top_logprobs values raise ValueError."""

    @pytest.mark.unit
    def test_top_logprobs_negative_raises(self, chat_client):
        """top_logprobs=-1 → ValueError."""
        with pytest.raises(ValueError, match="top_logprobs"):
            chat_client.chat_completion(
                messages=[{"role": "user", "content": "hi"}],
                logprobs=True,
                top_logprobs=-1,
            )

    @pytest.mark.unit
    def test_top_logprobs_too_high_raises(self, chat_client):
        """top_logprobs=25 → ValueError (max 20 per OpenAI spec)."""
        with pytest.raises(ValueError, match="top_logprobs"):
            chat_client.chat_completion(
                messages=[{"role": "user", "content": "hi"}],
                logprobs=True,
                top_logprobs=25,
            )

    @pytest.mark.unit
    def test_top_logprobs_zero_raises(self, chat_client):
        """top_logprobs=0 → ValueError (must be >= 1 when logprobs=True)."""
        with pytest.raises(ValueError, match="top_logprobs"):
            chat_client.chat_completion(
                messages=[{"role": "user", "content": "hi"}],
                logprobs=True,
                top_logprobs=0,
            )


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestLogprobsEdge:
    """Edge: defaults and logprobs=False behaviour."""

    @pytest.mark.unit
    def test_logprobs_false_not_in_payload(self, chat_client, mock_session):
        """logprobs=False → neither logprobs nor top_logprobs in payload."""
        chat_client.chat_completion(
            messages=[{"role": "user", "content": "hi"}],
            logprobs=False,
        )

        payload = mock_session.post.call_args.kwargs.get("json") or mock_session.post.call_args[1]["json"]
        assert "logprobs" not in payload
        assert "top_logprobs" not in payload

    @pytest.mark.unit
    def test_logprobs_true_default_top_logprobs(self, chat_client, mock_session):
        """logprobs=True without top_logprobs → defaults to DEFAULT_TOP_LOGPROBS."""
        from config.constants import DEFAULT_TOP_LOGPROBS

        chat_client.chat_completion(
            messages=[{"role": "user", "content": "hi"}],
            logprobs=True,
        )

        payload = mock_session.post.call_args.kwargs.get("json") or mock_session.post.call_args[1]["json"]
        assert payload["logprobs"] is True
        assert payload["top_logprobs"] == DEFAULT_TOP_LOGPROBS


# ---------------------------------------------------------------------------
# Boundary
# ---------------------------------------------------------------------------

class TestLogprobsBoundary:
    """Boundary: min/max top_logprobs, constants existence."""

    @pytest.mark.unit
    def test_top_logprobs_min_valid(self, chat_client, mock_session):
        """top_logprobs=1 → minimum valid value accepted."""
        chat_client.chat_completion(
            messages=[{"role": "user", "content": "hi"}],
            logprobs=True,
            top_logprobs=1,
        )

        payload = mock_session.post.call_args.kwargs.get("json") or mock_session.post.call_args[1]["json"]
        assert payload["top_logprobs"] == 1

    @pytest.mark.unit
    def test_top_logprobs_max_valid(self, chat_client, mock_session):
        """top_logprobs=20 → maximum valid value accepted."""
        chat_client.chat_completion(
            messages=[{"role": "user", "content": "hi"}],
            logprobs=True,
            top_logprobs=20,
        )

        payload = mock_session.post.call_args.kwargs.get("json") or mock_session.post.call_args[1]["json"]
        assert payload["top_logprobs"] == 20

    @pytest.mark.unit
    def test_logprobs_constants_exist(self):
        """Logprobs constants must be importable from config.constants."""
        from config.constants import (
            DEFAULT_TOP_LOGPROBS,
            MIN_TOP_LOGPROBS,
            MAX_TOP_LOGPROBS,
        )

        assert MIN_TOP_LOGPROBS == 1
        assert MAX_TOP_LOGPROBS == 20
        assert MIN_TOP_LOGPROBS <= DEFAULT_TOP_LOGPROBS <= MAX_TOP_LOGPROBS

    @pytest.mark.unit
    def test_facade_passes_logprobs(self, facade_client, mock_session):
        """LLMClient facade passes logprobs through to ChatClient."""
        facade_client.chat_completion(
            messages=[{"role": "user", "content": "hi"}],
            logprobs=True,
            top_logprobs=10,
        )

        payload = mock_session.post.call_args.kwargs.get("json") or mock_session.post.call_args[1]["json"]
        assert payload["logprobs"] is True
        assert payload["top_logprobs"] == 10
