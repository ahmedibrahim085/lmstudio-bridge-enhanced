"""Tests for OPP-21: Native Reasoning Parameter.

RED phase: These tests FAIL because the `reasoning` parameter does not exist
yet in llm/thinking_client.py and the supporting constants are not yet defined
in config/constants/thinking.py.

Contract (v5.0.0):
- `thinking_completion` and `stream_thinking_completion` accept
  `reasoning: Optional[Dict[str, str]] = None` instead of `thinking_budget`.
- Valid efforts: "low", "medium", "high".
- `reasoning={"effort": "invalid"}` raises ValueError.
- `reasoning={}` raises ValueError (missing "effort" key).
- `reasoning="medium"` (wrong type) raises TypeError or ValueError.
- `reasoning=None` uses the default effort — no error.
- Omitting `reasoning` entirely uses the default effort — no error.
- "low" effort maps to fewer effective_max_tokens than "high".
- "high" effort maps to more effective_max_tokens than "low".
- When reasoning is passed the `_chat_fn` receives it in its call arguments.
- Constants VALID_REASONING_EFFORTS, REASONING_EFFORT_TOKEN_MAP, and
  DEFAULT_REASONING_EFFORT must be importable from config.constants.
"""

from unittest.mock import MagicMock, call, patch

import pytest

from llm.llm_client import LLMClient


# ---------------------------------------------------------------------------
# Shared fixtures  (identical pattern to tests/test_v41_deprecation.py)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _skip_jit():
    """Prevent JIT model loading from contacting LM Studio during tests.

    Patches is_installed() at the jit_loader layer so ensure_model_loaded()
    returns immediately without any CLI or REST calls.
    """
    with patch("llm.jit_loader.LMSHelper.is_installed", return_value=False):
        yield


@pytest.fixture
def client():
    """Return an LLMClient whose HTTP session is fully mocked.

    The mock session's post() returns a minimal valid OpenAI-style response so
    that thinking_completion() can complete without a live LM Studio instance.
    The fixture patches get_config() at the transport layer (the only call site
    during __init__) so no real config loading occurs.
    """
    with patch("llm.http_transport.get_config") as mock_config:
        mock_config.return_value.lmstudio.api_base = "http://localhost:1234/v1"
        mock_config.return_value.lmstudio.default_model = "test-model"

        mock_session = MagicMock()
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            "choices": [{"message": {"content": "hello"}}]
        }
        response.raise_for_status.return_value = None
        mock_session.post.return_value = response

        c = LLMClient(session=mock_session)

    return c


# ---------------------------------------------------------------------------
# Helper: build minimal chat mock for thinking_completion tests
# ---------------------------------------------------------------------------


def _make_chat_mock() -> MagicMock:
    """Return a MagicMock that behaves like LLMClient.chat_completion."""
    mock = MagicMock()
    mock.return_value = {
        "choices": [{"message": {"content": "answer"}}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10},
    }
    return mock


# ===========================================================================
# Test class: ReasoningParameterHappyPath
# ===========================================================================


class TestReasoningParameterHappyPath:
    """Happy-path tests: valid effort strings must succeed without errors."""

    def test_reasoning_effort_medium_succeeds(self, client):
        """reasoning={"effort": "medium"} returns a valid response dict."""
        with patch.object(LLMClient, "chat_completion", _make_chat_mock()):
            result = client.thinking_completion(
                messages=[{"role": "user", "content": "think"}],
                reasoning={"effort": "medium"},
            )

        assert isinstance(result, dict), (
            "Expected a dict response from thinking_completion with "
            f"reasoning={{'effort': 'medium'}}, got: {type(result)}"
        )
        assert "choices" in result, (
            f"Expected 'choices' key in response dict, got keys: {list(result.keys())}"
        )

    def test_reasoning_effort_low_succeeds(self, client):
        """reasoning={"effort": "low"} returns a valid response dict."""
        with patch.object(LLMClient, "chat_completion", _make_chat_mock()):
            result = client.thinking_completion(
                messages=[{"role": "user", "content": "think"}],
                reasoning={"effort": "low"},
            )

        assert isinstance(result, dict), (
            "Expected a dict response from thinking_completion with "
            f"reasoning={{'effort': 'low'}}, got: {type(result)}"
        )
        assert "choices" in result

    def test_reasoning_effort_high_succeeds(self, client):
        """reasoning={"effort": "high"} returns a valid response dict."""
        with patch.object(LLMClient, "chat_completion", _make_chat_mock()):
            result = client.thinking_completion(
                messages=[{"role": "user", "content": "think"}],
                reasoning={"effort": "high"},
            )

        assert isinstance(result, dict), (
            "Expected a dict response from thinking_completion with "
            f"reasoning={{'effort': 'high'}}, got: {type(result)}"
        )
        assert "choices" in result

    def test_reasoning_effort_in_payload(self, client):
        """When reasoning is passed, _chat_fn receives reasoning dict in its call args.

        The implementation must forward the reasoning dict to the underlying
        chat_completion call so LM Studio 0.4+ can consume it natively.
        """
        chat_mock = _make_chat_mock()
        with patch.object(LLMClient, "chat_completion", chat_mock):
            client.thinking_completion(
                messages=[{"role": "user", "content": "think"}],
                reasoning={"effort": "medium"},
            )

        assert chat_mock.called, "Expected chat_completion to be called"
        _, kwargs = chat_mock.call_args
        assert "reasoning" in kwargs, (
            "Expected 'reasoning' key to be forwarded to _chat_fn kwargs, "
            f"but call_args kwargs were: {kwargs}"
        )
        assert kwargs["reasoning"] == {"effort": "medium"}, (
            f"Expected reasoning={{'effort': 'medium'}} forwarded, "
            f"but got: {kwargs.get('reasoning')!r}"
        )

    def test_stream_reasoning_effort_medium_succeeds(self, client):
        """Streaming path with reasoning={"effort": "medium"} yields without error."""
        with patch.object(
            LLMClient,
            "stream_chat_completion",
            return_value=iter([{"chunk": 1}]),
        ):
            chunks = list(
                client.stream_thinking_completion(
                    messages=[{"role": "user", "content": "think"}],
                    reasoning={"effort": "medium"},
                )
            )

        # The streaming path must not raise; consuming all chunks is sufficient
        assert isinstance(chunks, list), (
            "Expected stream_thinking_completion to return an iterable that yields "
            f"a list when consumed, got: {type(chunks)}"
        )


# ===========================================================================
# Test class: ReasoningParameterNegative
# ===========================================================================


class TestReasoningParameterNegative:
    """Negative tests: invalid inputs must raise appropriate exceptions."""

    def test_reasoning_invalid_effort_raises_value_error(self, client):
        """reasoning={"effort": "invalid"} must raise ValueError.

        Only "low", "medium", "high" are valid effort values.
        """
        with patch.object(LLMClient, "chat_completion", _make_chat_mock()):
            with pytest.raises(ValueError, match="effort"):
                client.thinking_completion(
                    messages=[{"role": "user", "content": "think"}],
                    reasoning={"effort": "invalid"},
                )

    def test_reasoning_empty_dict_raises_value_error(self, client):
        """reasoning={} must raise ValueError because "effort" key is missing."""
        with patch.object(LLMClient, "chat_completion", _make_chat_mock()):
            with pytest.raises(ValueError, match="effort"):
                client.thinking_completion(
                    messages=[{"role": "user", "content": "think"}],
                    reasoning={},
                )

    def test_reasoning_wrong_type_raises(self, client):
        """reasoning="medium" (str, not dict) must raise TypeError or ValueError.

        The parameter must be a dict with an "effort" key, not a bare string.
        """
        with patch.object(LLMClient, "chat_completion", _make_chat_mock()):
            with pytest.raises((TypeError, ValueError)):
                client.thinking_completion(
                    messages=[{"role": "user", "content": "think"}],
                    reasoning="medium",  # type: ignore[arg-type]
                )


# ===========================================================================
# Test class: ReasoningParameterEdge
# ===========================================================================


class TestReasoningParameterEdge:
    """Edge-case tests: None and omitted reasoning must use defaults silently."""

    def test_reasoning_none_uses_default(self, client):
        """reasoning=None uses the default effort and raises no error."""
        with patch.object(LLMClient, "chat_completion", _make_chat_mock()):
            result = client.thinking_completion(
                messages=[{"role": "user", "content": "think"}],
                reasoning=None,
            )

        assert isinstance(result, dict), (
            "Expected dict response when reasoning=None (use default), "
            f"got: {type(result)}"
        )

    def test_no_reasoning_param_uses_default(self, client):
        """Omitting reasoning entirely uses the default effort and raises no error."""
        with patch.object(LLMClient, "chat_completion", _make_chat_mock()):
            result = client.thinking_completion(
                messages=[{"role": "user", "content": "think"}],
                # reasoning not passed at all
            )

        assert isinstance(result, dict), (
            "Expected dict response when reasoning param is omitted, "
            f"got: {type(result)}"
        )


# ===========================================================================
# Test class: ReasoningParameterBoundary
# ===========================================================================


class TestReasoningParameterBoundary:
    """Boundary tests: effort level must influence effective_max_tokens."""

    def test_effort_low_maps_to_lower_tokens(self, client):
        """"low" effort must result in a smaller effective_max_tokens than "high".

        The implementation maps effort strings to token budgets; "low" should
        allocate fewer tokens than "high" so users can control inference cost.
        """
        low_mock = _make_chat_mock()
        high_mock = _make_chat_mock()

        with patch.object(LLMClient, "chat_completion", low_mock):
            client.thinking_completion(
                messages=[{"role": "user", "content": "think"}],
                reasoning={"effort": "low"},
            )

        with patch.object(LLMClient, "chat_completion", high_mock):
            client.thinking_completion(
                messages=[{"role": "user", "content": "think"}],
                reasoning={"effort": "high"},
            )

        _, low_kwargs = low_mock.call_args
        _, high_kwargs = high_mock.call_args

        low_tokens = low_kwargs.get("max_tokens")
        high_tokens = high_kwargs.get("max_tokens")

        assert low_tokens is not None, (
            "Expected 'max_tokens' in _chat_fn kwargs for low effort, "
            f"got kwargs: {low_kwargs}"
        )
        assert high_tokens is not None, (
            "Expected 'max_tokens' in _chat_fn kwargs for high effort, "
            f"got kwargs: {high_kwargs}"
        )
        assert low_tokens < high_tokens, (
            f"Expected low effort max_tokens ({low_tokens}) < "
            f"high effort max_tokens ({high_tokens}), but they are equal or reversed."
        )

    def test_effort_high_maps_to_higher_tokens(self, client):
        """"high" effort must result in a larger effective_max_tokens than "low".

        This is the complementary assertion to test_effort_low_maps_to_lower_tokens,
        providing explicit documentation of the high-effort upper bound.
        """
        low_mock = _make_chat_mock()
        high_mock = _make_chat_mock()

        with patch.object(LLMClient, "chat_completion", low_mock):
            client.thinking_completion(
                messages=[{"role": "user", "content": "think"}],
                reasoning={"effort": "low"},
            )

        with patch.object(LLMClient, "chat_completion", high_mock):
            client.thinking_completion(
                messages=[{"role": "user", "content": "think"}],
                reasoning={"effort": "high"},
            )

        _, low_kwargs = low_mock.call_args
        _, high_kwargs = high_mock.call_args

        low_tokens = low_kwargs.get("max_tokens")
        high_tokens = high_kwargs.get("max_tokens")

        assert high_tokens is not None, (
            "Expected 'max_tokens' in _chat_fn kwargs for high effort, "
            f"got kwargs: {high_kwargs}"
        )
        assert low_tokens is not None, (
            "Expected 'max_tokens' in _chat_fn kwargs for low effort, "
            f"got kwargs: {low_kwargs}"
        )
        assert high_tokens > low_tokens, (
            f"Expected high effort max_tokens ({high_tokens}) > "
            f"low effort max_tokens ({low_tokens}), but they are equal or reversed."
        )


# ===========================================================================
# Test class: ReasoningParameterConstants
# ===========================================================================


class TestReasoningParameterConstants:
    """Constants tests: required names must be importable from config.constants."""

    def test_reasoning_effort_constants_exist(self):
        """VALID_REASONING_EFFORTS, REASONING_EFFORT_TOKEN_MAP, and
        DEFAULT_REASONING_EFFORT must all be importable from config.constants.

        These constants anchor the valid effort strings and token budgets so
        that validation logic and callers can reference a single source of truth.
        """
        from config.constants import (  # noqa: PLC0415
            DEFAULT_REASONING_EFFORT,
            REASONING_EFFORT_TOKEN_MAP,
            VALID_REASONING_EFFORTS,
        )

        # VALID_REASONING_EFFORTS: must be a collection containing the 3 tiers
        assert "low" in VALID_REASONING_EFFORTS, (
            f"Expected 'low' in VALID_REASONING_EFFORTS, got: {VALID_REASONING_EFFORTS}"
        )
        assert "medium" in VALID_REASONING_EFFORTS, (
            f"Expected 'medium' in VALID_REASONING_EFFORTS, got: {VALID_REASONING_EFFORTS}"
        )
        assert "high" in VALID_REASONING_EFFORTS, (
            f"Expected 'high' in VALID_REASONING_EFFORTS, got: {VALID_REASONING_EFFORTS}"
        )

        # REASONING_EFFORT_TOKEN_MAP: must map each effort to a positive int
        assert isinstance(REASONING_EFFORT_TOKEN_MAP, dict), (
            f"Expected REASONING_EFFORT_TOKEN_MAP to be a dict, "
            f"got: {type(REASONING_EFFORT_TOKEN_MAP)}"
        )
        for effort in ("low", "medium", "high"):
            assert effort in REASONING_EFFORT_TOKEN_MAP, (
                f"Expected '{effort}' key in REASONING_EFFORT_TOKEN_MAP, "
                f"got keys: {list(REASONING_EFFORT_TOKEN_MAP.keys())}"
            )
            tokens = REASONING_EFFORT_TOKEN_MAP[effort]
            assert isinstance(tokens, int) and tokens > 0, (
                f"Expected REASONING_EFFORT_TOKEN_MAP['{effort}'] to be a positive int, "
                f"got: {tokens!r}"
            )

        # Values must be strictly ordered: low < medium < high
        assert (
            REASONING_EFFORT_TOKEN_MAP["low"]
            < REASONING_EFFORT_TOKEN_MAP["medium"]
            < REASONING_EFFORT_TOKEN_MAP["high"]
        ), (
            "Expected REASONING_EFFORT_TOKEN_MAP values to be strictly ordered "
            "low < medium < high, but got: "
            f"low={REASONING_EFFORT_TOKEN_MAP['low']}, "
            f"medium={REASONING_EFFORT_TOKEN_MAP['medium']}, "
            f"high={REASONING_EFFORT_TOKEN_MAP['high']}"
        )

        # DEFAULT_REASONING_EFFORT: must be one of the valid efforts
        assert DEFAULT_REASONING_EFFORT in VALID_REASONING_EFFORTS, (
            f"Expected DEFAULT_REASONING_EFFORT to be in VALID_REASONING_EFFORTS, "
            f"got: {DEFAULT_REASONING_EFFORT!r}"
        )
