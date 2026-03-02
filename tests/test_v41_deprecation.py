"""Tests for v4.1.0 DeprecationWarning on thinking_budget parameter.

RED phase: These tests FAIL because DeprecationWarning has not been implemented
yet in llm/thinking_client.py. They define the exact contract the implementation
must satisfy in the GREEN phase.

Contract:
- Passing an explicit integer to thinking_budget emits DeprecationWarning
- Passing nothing (default None) emits NO DeprecationWarning
- Warning message names both the deprecated param ("thinking_budget") and the
  replacement API ("reasoning" / "effort")
- stacklevel is set so the warning points to the CALLER's frame, not to
  thinking_client.py internals
"""

import warnings
from unittest.mock import MagicMock, patch

import pytest

from llm.llm_client import LLMClient


# ---------------------------------------------------------------------------
# Shared fixtures
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
# Test class: ThinkingBudgetDeprecation
# ===========================================================================


class TestThinkingBudgetDeprecation:
    """v4.1.0: explicit thinking_budget must emit DeprecationWarning."""

    # ------------------------------------------------------------------
    # thinking_completion — primary (non-streaming) path
    # ------------------------------------------------------------------

    def test_thinking_budget_emits_deprecation_warning(self, client):
        """Explicit thinking_budget=1024 emits at least one DeprecationWarning."""
        with patch.object(LLMClient, "chat_completion", _make_chat_mock()):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                client.thinking_completion(
                    messages=[{"role": "user", "content": "think"}],
                    thinking_budget=1024,
                )

        deprecation_warnings = [
            x for x in w if issubclass(x.category, DeprecationWarning)
        ]
        assert len(deprecation_warnings) >= 1, (
            "Expected at least one DeprecationWarning when thinking_budget is passed "
            f"explicitly, but got: {[str(x.message) for x in w]}"
        )

    def test_thinking_budget_warning_mentions_thinking_budget(self, client):
        """Warning message contains the deprecated parameter name 'thinking_budget'."""
        with patch.object(LLMClient, "chat_completion", _make_chat_mock()):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                client.thinking_completion(
                    messages=[{"role": "user", "content": "think"}],
                    thinking_budget=1024,
                )

        deprecation_warnings = [
            x for x in w if issubclass(x.category, DeprecationWarning)
        ]
        assert len(deprecation_warnings) >= 1
        msg = str(deprecation_warnings[0].message)
        assert "thinking_budget" in msg, (
            f"Expected 'thinking_budget' in warning message, got: {msg!r}"
        )

    def test_thinking_budget_warning_mentions_reasoning(self, client):
        """Warning message contains the replacement API name 'reasoning'."""
        with patch.object(LLMClient, "chat_completion", _make_chat_mock()):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                client.thinking_completion(
                    messages=[{"role": "user", "content": "think"}],
                    thinking_budget=512,
                )

        deprecation_warnings = [
            x for x in w if issubclass(x.category, DeprecationWarning)
        ]
        assert len(deprecation_warnings) >= 1
        msg = str(deprecation_warnings[0].message)
        assert "reasoning" in msg, (
            f"Expected 'reasoning' in warning message, got: {msg!r}"
        )

    def test_deprecation_warning_mentions_effort(self, client):
        """Warning message tells users about reasoning={'effort': ...} replacement."""
        with patch.object(LLMClient, "chat_completion", _make_chat_mock()):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                client.thinking_completion(
                    messages=[{"role": "user", "content": "think"}],
                    thinking_budget=512,
                )

        deprecation_warnings = [
            x for x in w if issubclass(x.category, DeprecationWarning)
        ]
        assert len(deprecation_warnings) >= 1
        msg = str(deprecation_warnings[0].message)
        assert "effort" in msg, (
            f"Expected 'effort' in warning message to guide migration, got: {msg!r}"
        )

    def test_no_thinking_budget_no_warning(self, client):
        """Default thinking_budget (None) does NOT emit DeprecationWarning."""
        with patch.object(LLMClient, "chat_completion", _make_chat_mock()):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                client.thinking_completion(
                    messages=[{"role": "user", "content": "think"}],
                    # thinking_budget omitted — uses default None
                )

        deprecation_warnings = [
            x for x in w if issubclass(x.category, DeprecationWarning)
        ]
        assert len(deprecation_warnings) == 0, (
            "Expected NO DeprecationWarning when thinking_budget is not passed, "
            f"but got: {[str(x.message) for x in deprecation_warnings]}"
        )

    def test_thinking_budget_none_explicit_no_warning(self, client):
        """Explicitly passing thinking_budget=None does NOT emit DeprecationWarning.

        None is the sentinel value meaning 'use the default'; it is not a
        user-provided override, so no migration warning should fire.
        """
        with patch.object(LLMClient, "chat_completion", _make_chat_mock()):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                client.thinking_completion(
                    messages=[{"role": "user", "content": "think"}],
                    thinking_budget=None,
                )

        deprecation_warnings = [
            x for x in w if issubclass(x.category, DeprecationWarning)
        ]
        assert len(deprecation_warnings) == 0, (
            "Expected NO DeprecationWarning for thinking_budget=None, "
            f"but got: {[str(x.message) for x in deprecation_warnings]}"
        )

    def test_deprecation_warning_stacklevel_points_to_caller(self, client):
        """Warning filename must reference this test file, not thinking_client.py.

        stacklevel=3 in warnings.warn() walks up the Facade call chain
        (user -> LLMClient -> ThinkingClient -> warnings.warn) so the warning
        points to the caller's frame.  If stacklevel is wrong (e.g., 1 or 2),
        the warning points inside thinking_client.py and users cannot find
        where in their code to fix the call.
        """
        with patch.object(LLMClient, "chat_completion", _make_chat_mock()):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                client.thinking_completion(
                    messages=[{"role": "user", "content": "think"}],
                    thinking_budget=512,
                )

        deprecation_warnings = [
            x for x in w if issubclass(x.category, DeprecationWarning)
        ]
        assert len(deprecation_warnings) >= 1
        # The warning filename should reference this test file, not the implementation
        warning_filename = deprecation_warnings[0].filename
        assert "test_v41_deprecation" in warning_filename, (
            f"Expected warning to point to test_v41_deprecation (caller frame), "
            f"but warning.filename was: {warning_filename!r}. "
            "Check stacklevel= in warnings.warn() call."
        )

    # ------------------------------------------------------------------
    # stream_thinking_completion — streaming path
    # ------------------------------------------------------------------

    def test_stream_thinking_budget_emits_deprecation_warning(self, client):
        """stream_thinking_completion with explicit thinking_budget emits DeprecationWarning.

        The warning must fire when the generator body executes, which happens
        on the first call to next() — consuming the generator with list() is
        sufficient to trigger it.
        """
        with patch.object(
            LLMClient,
            "stream_chat_completion",
            return_value=iter([]),
        ):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                # Consume the generator so the body actually executes
                list(
                    client.stream_thinking_completion(
                        messages=[{"role": "user", "content": "think"}],
                        thinking_budget=2048,
                    )
                )

        deprecation_warnings = [
            x for x in w if issubclass(x.category, DeprecationWarning)
        ]
        assert len(deprecation_warnings) >= 1, (
            "Expected at least one DeprecationWarning from stream_thinking_completion "
            f"when thinking_budget is explicit, but got: {[str(x.message) for x in w]}"
        )

    def test_stream_thinking_budget_warning_mentions_thinking_budget(self, client):
        """stream_thinking_completion warning message names 'thinking_budget'."""
        with patch.object(
            LLMClient,
            "stream_chat_completion",
            return_value=iter([]),
        ):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                list(
                    client.stream_thinking_completion(
                        messages=[{"role": "user", "content": "think"}],
                        thinking_budget=2048,
                    )
                )

        deprecation_warnings = [
            x for x in w if issubclass(x.category, DeprecationWarning)
        ]
        assert len(deprecation_warnings) >= 1
        msg = str(deprecation_warnings[0].message)
        assert "thinking_budget" in msg, (
            f"Expected 'thinking_budget' in stream warning message, got: {msg!r}"
        )

    def test_stream_no_thinking_budget_no_warning(self, client):
        """stream_thinking_completion with default budget emits NO DeprecationWarning."""
        with patch.object(
            LLMClient,
            "stream_chat_completion",
            return_value=iter([]),
        ):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                list(
                    client.stream_thinking_completion(
                        messages=[{"role": "user", "content": "think"}],
                        # thinking_budget omitted
                    )
                )

        deprecation_warnings = [
            x for x in w if issubclass(x.category, DeprecationWarning)
        ]
        assert len(deprecation_warnings) == 0, (
            "Expected NO DeprecationWarning when stream_thinking_completion is called "
            f"without thinking_budget, but got: {[str(x.message) for x in deprecation_warnings]}"
        )

    def test_stream_thinking_budget_none_explicit_no_warning(self, client):
        """stream_thinking_completion with thinking_budget=None emits NO DeprecationWarning."""
        with patch.object(
            LLMClient,
            "stream_chat_completion",
            return_value=iter([]),
        ):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                list(
                    client.stream_thinking_completion(
                        messages=[{"role": "user", "content": "think"}],
                        thinking_budget=None,
                    )
                )

        deprecation_warnings = [
            x for x in w if issubclass(x.category, DeprecationWarning)
        ]
        assert len(deprecation_warnings) == 0, (
            "Expected NO DeprecationWarning for stream thinking_budget=None, "
            f"but got: {[str(x.message) for x in deprecation_warnings]}"
        )

    def test_stream_deprecation_warning_stacklevel_points_to_caller(self, client):
        """Streaming warning filename must reference this test file, not thinking_client.py."""
        with patch.object(
            LLMClient,
            "stream_chat_completion",
            return_value=iter([]),
        ):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                list(
                    client.stream_thinking_completion(
                        messages=[{"role": "user", "content": "think"}],
                        thinking_budget=512,
                    )
                )

        deprecation_warnings = [
            x for x in w if issubclass(x.category, DeprecationWarning)
        ]
        assert len(deprecation_warnings) >= 1
        warning_filename = deprecation_warnings[0].filename
        assert "test_v41_deprecation" in warning_filename, (
            f"Expected warning to point to test_v41_deprecation (caller frame), "
            f"but warning.filename was: {warning_filename!r}. "
            "Check stacklevel= in warnings.warn() call."
        )
