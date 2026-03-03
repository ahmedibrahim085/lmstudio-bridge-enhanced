#!/usr/bin/env python3
"""
RED phase tests for OPP-39: Context Window Guard.

Tests cover two dispatch paths in tools/dynamic_autonomous.py:
  - Path A: _autonomous_loop()           (Responses API, line 788)
  - Path B: _autonomous_loop_anthropic() (Anthropic API, line 986)

New functionality under test (does NOT exist yet — all tests must FAIL):
  1. DynamicAutonomousAgent._estimate_tokens(payload) static method
  2. context_window parameter on _autonomous_loop()
  3. context_window parameter on _autonomous_loop_anthropic()
  4. context_window parameter on _run_autonomous_dispatch()
  5. Guard logic: cumulative token estimate > CONTEXT_GUARD_THRESHOLD * context_window -> early return
  6. Constants: CONTEXT_GUARD_THRESHOLD, DEFAULT_CONTEXT_WINDOW in config/constants/api.py

WHY tests must FAIL on first run:
  - _estimate_tokens does not exist              -> AttributeError
  - CONTEXT_GUARD_THRESHOLD / DEFAULT_CONTEXT_WINDOW not in config.constants -> ImportError
  - context_window kwarg absent on all 3 methods -> TypeError
"""

import asyncio
import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add project root to path so all imports resolve
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tools.dynamic_autonomous import DynamicAutonomousAgent  # noqa: E402

# ---------------------------------------------------------------------------
# Import the new constants — these MUST fail with ImportError until OPP-39
# is implemented. We catch the ImportError so individual constant tests can
# report the failure precisely rather than blowing up the whole module.
# ---------------------------------------------------------------------------
try:
    from config.constants import CONTEXT_GUARD_THRESHOLD  # noqa: E402
    _CONTEXT_GUARD_THRESHOLD_IMPORTED = True
except ImportError:
    CONTEXT_GUARD_THRESHOLD = None  # type: ignore[assignment]
    _CONTEXT_GUARD_THRESHOLD_IMPORTED = False

try:
    from config.constants import DEFAULT_CONTEXT_WINDOW  # noqa: E402
    _DEFAULT_CONTEXT_WINDOW_IMPORTED = True
except ImportError:
    DEFAULT_CONTEXT_WINDOW = None  # type: ignore[assignment]
    _DEFAULT_CONTEXT_WINDOW_IMPORTED = False

# Existing constant — already present in config/constants/thinking.py
from config.constants import CHARS_PER_TOKEN_ESTIMATE  # noqa: E402


# ==============================================================================
# Helpers
# ==============================================================================

def _make_agent() -> DynamicAutonomousAgent:
    """Construct a DynamicAutonomousAgent without calling __init__ (avoids LLM setup)."""
    agent = DynamicAutonomousAgent.__new__(DynamicAutonomousAgent)
    agent.llm = MagicMock()
    agent.consecutive_error_count = 0
    agent.last_loop_metrics = None
    return agent


def _final_responses_reply() -> dict:
    """Mock LLM response for Path A (Responses API) — final answer, no tool calls."""
    return {
        "id": "resp_test",
        "status": "completed",
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": "Task completed successfully"}],
            }
        ],
    }


def _final_anthropic_reply() -> dict:
    """Mock LLM response for Path B (Anthropic API) — final answer, no tool calls."""
    return {
        "stop_reason": "end_turn",
        "content": [{"type": "text", "text": "Task completed successfully"}],
    }


def _large_payload_exceeding_threshold(context_window: int, threshold: float = 0.80) -> dict:
    """Build a payload whose serialized size is guaranteed to exceed threshold * context_window tokens."""
    # Each token ~4 chars, so target bytes = threshold * context_window * 4 * 1.1 (10% over)
    target_chars = int(threshold * context_window * CHARS_PER_TOKEN_ESTIMATE * 1.1)
    return {"data": "x" * target_chars}


def _payload_at_fraction(context_window: int, fraction: float) -> dict:
    """Build a payload whose token estimate is exactly at the given fraction of context_window."""
    target_chars = int(fraction * context_window * CHARS_PER_TOKEN_ESTIMATE)
    return {"data": "x" * target_chars}


# ==============================================================================
# TestEstimateTokens — unit tests for _estimate_tokens static method
# ==============================================================================


class TestEstimateTokens:
    """Unit tests for DynamicAutonomousAgent._estimate_tokens(payload).

    This static method does not exist yet. All tests fail with AttributeError
    until OPP-39 is implemented.
    """

    def test_estimate_tokens_simple_dict(self):
        """Simple dict: token estimate == len(json.dumps(payload)) // CHARS_PER_TOKEN_ESTIMATE."""
        payload = {"key": "value"}
        serialized = json.dumps(payload)
        expected = len(serialized) // CHARS_PER_TOKEN_ESTIMATE

        # AttributeError until _estimate_tokens is added
        result = DynamicAutonomousAgent._estimate_tokens(payload)

        assert isinstance(result, int), f"Expected int, got {type(result)}"
        assert result == expected, (
            f"Expected {expected} tokens for {repr(serialized)}, got {result}"
        )

    def test_estimate_tokens_empty_dict(self):
        """Empty dict serializes to '{}' (2 chars) -> 0 tokens due to integer division."""
        payload = {}
        serialized = json.dumps(payload)  # '{}'
        expected = len(serialized) // CHARS_PER_TOKEN_ESTIMATE  # 2 // 4 = 0

        result = DynamicAutonomousAgent._estimate_tokens(payload)

        assert isinstance(result, int)
        assert result == expected, (
            f"Empty dict: expected {expected} tokens, got {result}"
        )

    def test_estimate_tokens_large_payload(self):
        """100K-char string value -> ~25K tokens."""
        big_string = "a" * 100_000
        payload = {"data": big_string}
        serialized = json.dumps(payload)
        expected = len(serialized) // CHARS_PER_TOKEN_ESTIMATE  # ~25K

        result = DynamicAutonomousAgent._estimate_tokens(payload)

        assert isinstance(result, int)
        assert result == expected, (
            f"Large payload: expected ~{expected} tokens, got {result}"
        )
        # Sanity: large payload must produce many tokens
        assert result > 20_000, f"Expected > 20000 tokens for 100K-char payload, got {result}"

    def test_estimate_tokens_with_tools_array(self):
        """openai_tools array produces a predictable estimate."""
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "list_directory",
                    "description": "List files in a directory",
                    "parameters": {
                        "type": "object",
                        "properties": {"path": {"type": "string"}},
                        "required": ["path"],
                    },
                },
            }
        ]
        serialized = json.dumps(tools)
        expected = len(serialized) // CHARS_PER_TOKEN_ESTIMATE

        result = DynamicAutonomousAgent._estimate_tokens(tools)

        assert isinstance(result, int)
        assert result == expected, (
            f"Tools array: expected {expected} tokens, got {result}"
        )

    def test_estimate_tokens_non_serializable_fallback(self):
        """Object that cannot be JSON-serialized must return 0 (safe fallback)."""

        class _Unserializable:
            pass

        payload = _Unserializable()

        result = DynamicAutonomousAgent._estimate_tokens(payload)

        assert result == 0, (
            f"Non-serializable payload should return 0, got {result}"
        )


# ==============================================================================
# TestContextGuardResponsesLoop — Path A: _autonomous_loop (Responses API)
# ==============================================================================


class TestContextGuardResponsesLoop:
    """Tests for context guard in _autonomous_loop() (Path A — Responses API).

    Tests fail because:
    - context_window parameter does not exist -> TypeError on call
    - Guard logic does not exist -> no early return
    """

    def test_guard_triggers_when_context_exceeded(self):
        """Cumulative token estimate > 80% of 4096 window -> early return with context message."""
        agent = _make_agent()
        context_window = 4096

        large_payload = _large_payload_exceeding_threshold(context_window)

        mock_dispatcher = MagicMock()
        # Return a large response that will push cumulative estimate over threshold
        large_response = {
            "id": "resp_overflow",
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [
                        {"type": "output_text", "text": json.dumps(large_payload)}
                    ],
                }
            ],
        }
        agent.llm.create_response = MagicMock(return_value=large_response)

        # TypeError until context_window param is added; then guard must trigger
        result = asyncio.run(
            agent._autonomous_loop(
                dispatcher=mock_dispatcher,
                openai_tools=[],
                task="test task",
                max_rounds=10,
                max_tokens=1024,
                context_window=context_window,
            )
        )

        assert "context" in result.lower(), (
            f"Expected context-guard early-return message, got: {repr(result)}"
        )

    def test_guard_allows_when_under_threshold(self):
        """Small payload well under 80% -> loop completes normally with task result."""
        agent = _make_agent()
        context_window = 4096

        agent.llm.create_response = MagicMock(return_value=_final_responses_reply())

        result = asyncio.run(
            agent._autonomous_loop(
                dispatcher=MagicMock(),
                openai_tools=[],
                task="small task",
                max_rounds=5,
                max_tokens=1024,
                context_window=context_window,
            )
        )

        assert "Task completed successfully" in result, (
            f"Expected normal completion, got: {repr(result)}"
        )

    def test_guard_uses_custom_context_window(self):
        """context_window=8192 -> threshold is 0.80 * 8192 = 6554 tokens."""
        agent = _make_agent()
        context_window = 8192

        # Payload that exceeds 80% of 8192 but not 80% of 4096
        # 80% * 8192 = 6554 tokens -> 6554 * 4 chars = 26,214 chars
        # 80% * 4096 = 3277 tokens -> 3277 * 4 chars = 13,107 chars
        # Use ~20K chars -> exceeds 8192 threshold, not 4096
        large_payload = {"data": "y" * 20_000}
        large_response = {
            "id": "resp_custom",
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": json.dumps(large_payload)}],
                }
            ],
        }
        agent.llm.create_response = MagicMock(return_value=large_response)

        result = asyncio.run(
            agent._autonomous_loop(
                dispatcher=MagicMock(),
                openai_tools=[],
                task="custom window task",
                max_rounds=10,
                max_tokens=1024,
                context_window=context_window,
            )
        )

        assert "context" in result.lower(), (
            f"Guard should trigger with custom window=8192, got: {repr(result)}"
        )

    def test_guard_with_tool_results_accumulation(self):
        """Multi-round: round 0 small -> OK; round 1 tool results push over threshold -> guard triggers."""
        agent = _make_agent()
        context_window = 4096

        # Round 0: tool call response (small)
        tool_call_response = {
            "id": "resp_round0",
            "status": "completed",
            "output": [
                {
                    "type": "function_call",
                    "name": "list_directory",
                    "call_id": "call_001",
                    "arguments": json.dumps({"path": "/tmp"}),
                }
            ],
        }
        # Round 1: huge response to push cumulative over threshold
        big_text = "z" * (context_window * CHARS_PER_TOKEN_ESTIMATE)
        overflow_response = {
            "id": "resp_round1",
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": big_text}],
                }
            ],
        }

        agent.llm.create_response = MagicMock(
            side_effect=[tool_call_response, overflow_response]
        )

        # Mock dispatcher to handle tool calls
        mock_dispatcher = MagicMock()
        mock_dispatcher.call_tool = AsyncMock(return_value="tool result")

        result = asyncio.run(
            agent._autonomous_loop(
                dispatcher=mock_dispatcher,
                openai_tools=[],
                task="accumulation task",
                max_rounds=10,
                max_tokens=1024,
                context_window=context_window,
            )
        )

        assert "context" in result.lower(), (
            f"Guard should trigger after accumulation, got: {repr(result)}"
        )

    def test_guard_logs_warning_before_abort(self):
        """Guard must call log_error (or equivalent) with token estimate info before returning."""
        agent = _make_agent()
        context_window = 4096

        large_payload = _large_payload_exceeding_threshold(context_window)
        large_response = {
            "id": "resp_log",
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": json.dumps(large_payload)}],
                }
            ],
        }
        agent.llm.create_response = MagicMock(return_value=large_response)

        with patch("tools.dynamic_autonomous.log_error") as mock_log_error:
            asyncio.run(
                agent._autonomous_loop(
                    dispatcher=MagicMock(),
                    openai_tools=[],
                    task="logging task",
                    max_rounds=10,
                    max_tokens=1024,
                    context_window=context_window,
                )
            )
            mock_log_error.assert_called()
            call_args_str = str(mock_log_error.call_args_list)
            assert "token" in call_args_str.lower() or "context" in call_args_str.lower(), (
                f"log_error should mention tokens or context, got: {call_args_str}"
            )

    def test_guard_default_context_window_fallback(self):
        """No context_window param -> uses DEFAULT_CONTEXT_WINDOW (32768).

        With DEFAULT_CONTEXT_WINDOW=32768, a small payload must NOT trigger the guard.
        """
        if not _DEFAULT_CONTEXT_WINDOW_IMPORTED:
            pytest.fail(
                "DEFAULT_CONTEXT_WINDOW not importable from config.constants — "
                "OPP-39 constant not implemented yet"
            )

        agent = _make_agent()
        agent.llm.create_response = MagicMock(return_value=_final_responses_reply())

        # Call without context_window — must not raise TypeError after OPP-39 is done
        result = asyncio.run(
            agent._autonomous_loop(
                dispatcher=MagicMock(),
                openai_tools=[],
                task="default window task",
                max_rounds=5,
                max_tokens=1024,
                # context_window intentionally omitted -> defaults to DEFAULT_CONTEXT_WINDOW
            )
        )

        # Small payload -> guard does NOT fire -> normal completion
        assert "Task completed successfully" in result, (
            f"Default window should not trigger guard for small payload, got: {repr(result)}"
        )

    def test_guard_at_exact_threshold_boundary(self):
        """Payload at exactly 80% of window -> allowed (boundary is exclusive)."""
        if not _CONTEXT_GUARD_THRESHOLD_IMPORTED:
            pytest.fail(
                "CONTEXT_GUARD_THRESHOLD not importable — OPP-39 not implemented yet"
            )

        agent = _make_agent()
        context_window = 4096
        threshold = CONTEXT_GUARD_THRESHOLD  # 0.80

        # Build payload at exactly threshold * context_window tokens
        exact_tokens = int(threshold * context_window)
        exact_chars = exact_tokens * CHARS_PER_TOKEN_ESTIMATE
        boundary_payload = {"data": "b" * exact_chars}

        boundary_response = {
            "id": "resp_boundary",
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": json.dumps(boundary_payload)}],
                }
            ],
        }
        agent.llm.create_response = MagicMock(
            side_effect=[boundary_response, _final_responses_reply()]
        )

        result = asyncio.run(
            agent._autonomous_loop(
                dispatcher=MagicMock(),
                openai_tools=[],
                task="boundary task",
                max_rounds=5,
                max_tokens=1024,
                context_window=context_window,
            )
        )

        # At exactly threshold -> guard does NOT fire -> loop continues to completion
        assert "Task completed successfully" in result, (
            f"Payload at exact threshold should be allowed, got: {repr(result)}"
        )

    def test_guard_just_over_threshold(self):
        """Payload at 80.1% of window -> guard blocks."""
        if not _CONTEXT_GUARD_THRESHOLD_IMPORTED:
            pytest.fail(
                "CONTEXT_GUARD_THRESHOLD not importable — OPP-39 not implemented yet"
            )

        agent = _make_agent()
        context_window = 4096
        threshold = CONTEXT_GUARD_THRESHOLD  # 0.80

        # 80.1% -> just over threshold
        over_tokens = int(threshold * context_window) + 1
        over_chars = over_tokens * CHARS_PER_TOKEN_ESTIMATE
        over_payload = {"data": "o" * over_chars}

        over_response = {
            "id": "resp_over",
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": json.dumps(over_payload)}],
                }
            ],
        }
        agent.llm.create_response = MagicMock(return_value=over_response)

        result = asyncio.run(
            agent._autonomous_loop(
                dispatcher=MagicMock(),
                openai_tools=[],
                task="just over task",
                max_rounds=5,
                max_tokens=1024,
                context_window=context_window,
            )
        )

        assert "context" in result.lower(), (
            f"Payload just over threshold should be blocked, got: {repr(result)}"
        )

    def test_incomplete_response_boosts_estimate(self):
        """status=='incomplete' response -> cumulative estimate is boosted -> guard triggers next round.

        An incomplete response signals the model was cut off (max_tokens hit), meaning
        the actual context usage is likely much higher than the payload suggests.
        The guard implementation must boost the cumulative estimate to account for this.
        """
        agent = _make_agent()
        # Use a larger context window so the incomplete boost is what tips us over
        context_window = 8192

        incomplete_response = {
            "id": "resp_incomplete",
            "status": "incomplete",
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "partial answer..."}],
                }
            ],
        }
        # Second round — would complete normally, but guard should have triggered
        agent.llm.create_response = MagicMock(
            side_effect=[incomplete_response, _final_responses_reply()]
        )

        result = asyncio.run(
            agent._autonomous_loop(
                dispatcher=MagicMock(),
                openai_tools=[],
                task="incomplete task",
                max_rounds=5,
                max_tokens=1024,
                context_window=context_window,
            )
        )

        # Either the guard triggers (context in result) or the loop
        # completed but the incomplete boost must have been applied.
        # Guard should trigger given the boost logic.
        assert "context" in result.lower(), (
            f"Incomplete response boost should trigger guard, got: {repr(result)}"
        )


# ==============================================================================
# TestContextGuardAnthropicLoop — Path B: _autonomous_loop_anthropic
# ==============================================================================


class TestContextGuardAnthropicLoop:
    """Tests for context guard in _autonomous_loop_anthropic() (Path B — Anthropic API).

    Tests fail because:
    - context_window parameter does not exist on _autonomous_loop_anthropic -> TypeError
    - Guard logic does not exist -> no early return
    """

    def test_anthropic_guard_triggers_on_large_messages(self):
        """messages list + tools > 80% of window -> early return with context message."""
        agent = _make_agent()
        context_window = 4096

        # Return a final answer immediately — the guard should check the payload
        # (messages + tools) BEFORE or AFTER calling the LLM
        large_text = "q" * int(0.85 * context_window * CHARS_PER_TOKEN_ESTIMATE)
        anthropic_response = {
            "stop_reason": "end_turn",
            "content": [{"type": "text", "text": large_text}],
        }
        agent.llm.anthropic_messages = MagicMock(return_value=anthropic_response)

        result = asyncio.run(
            agent._autonomous_loop_anthropic(
                dispatcher=MagicMock(),
                openai_tools=[],
                task="large anthropic task",
                max_rounds=10,
                max_tokens=1024,
                context_window=context_window,
            )
        )

        assert "context" in result.lower(), (
            f"Anthropic guard should trigger on large messages, got: {repr(result)}"
        )

    def test_anthropic_guard_allows_normal_messages(self):
        """Small messages well under threshold -> loop completes normally."""
        agent = _make_agent()
        context_window = 4096

        agent.llm.anthropic_messages = MagicMock(return_value=_final_anthropic_reply())

        result = asyncio.run(
            agent._autonomous_loop_anthropic(
                dispatcher=MagicMock(),
                openai_tools=[],
                task="small anthropic task",
                max_rounds=5,
                max_tokens=1024,
                context_window=context_window,
            )
        )

        assert "Task completed successfully" in result, (
            f"Normal Anthropic loop should complete successfully, got: {repr(result)}"
        )

    def test_anthropic_guard_after_message_trimming(self):
        """Even after MAX_ANTHROPIC_LOOP_MESSAGES trim, still over threshold -> guard triggers.

        This tests that the guard runs AFTER trimming, not before, so an extremely
        large (but trimmed) messages list still gets caught.
        """
        agent = _make_agent()
        context_window = 4096

        # Each round adds a large text response — cumulative estimate grows
        large_text_per_round = "p" * int(0.30 * context_window * CHARS_PER_TOKEN_ESTIMATE)
        anthropic_response_large = {
            "stop_reason": "end_turn",
            "content": [{"type": "text", "text": large_text_per_round}],
        }
        # After 3 rounds of 30%-sized payloads -> 90% cumulative -> guard triggers
        agent.llm.anthropic_messages = MagicMock(
            side_effect=[
                anthropic_response_large,
                anthropic_response_large,
                anthropic_response_large,
                _final_anthropic_reply(),  # Would be round 4, but guard fires at round 3
            ]
        )

        result = asyncio.run(
            agent._autonomous_loop_anthropic(
                dispatcher=MagicMock(),
                openai_tools=[],
                task="trimming + guard task",
                max_rounds=10,
                max_tokens=1024,
                context_window=context_window,
            )
        )

        assert "context" in result.lower(), (
            f"Guard should trigger even after trimming, got: {repr(result)}"
        )


# ==============================================================================
# TestContextGuardConstants — validate new constants
# ==============================================================================


class TestContextGuardConstants:
    """Validate that CONTEXT_GUARD_THRESHOLD and DEFAULT_CONTEXT_WINDOW are properly defined.

    Both tests fail with ImportError until OPP-39 adds the constants to api.py.
    """

    def test_context_guard_threshold_valid(self):
        """CONTEXT_GUARD_THRESHOLD must be importable, be a float in (0, 1)."""
        if not _CONTEXT_GUARD_THRESHOLD_IMPORTED:
            pytest.fail(
                "CONTEXT_GUARD_THRESHOLD not importable from config.constants — "
                "add it to config/constants/api.py (expected: 0.8)"
            )

        assert isinstance(CONTEXT_GUARD_THRESHOLD, float), (
            f"CONTEXT_GUARD_THRESHOLD must be float, got {type(CONTEXT_GUARD_THRESHOLD)}"
        )
        assert 0.0 < CONTEXT_GUARD_THRESHOLD < 1.0, (
            f"CONTEXT_GUARD_THRESHOLD must be in (0, 1), got {CONTEXT_GUARD_THRESHOLD}"
        )
        assert CONTEXT_GUARD_THRESHOLD == 0.8, (
            f"CONTEXT_GUARD_THRESHOLD design spec is 0.8, got {CONTEXT_GUARD_THRESHOLD}"
        )

    def test_default_context_window_valid(self):
        """DEFAULT_CONTEXT_WINDOW must be importable, be a positive int."""
        if not _DEFAULT_CONTEXT_WINDOW_IMPORTED:
            pytest.fail(
                "DEFAULT_CONTEXT_WINDOW not importable from config.constants — "
                "add it to config/constants/api.py (expected: 32768)"
            )

        assert isinstance(DEFAULT_CONTEXT_WINDOW, int), (
            f"DEFAULT_CONTEXT_WINDOW must be int, got {type(DEFAULT_CONTEXT_WINDOW)}"
        )
        assert DEFAULT_CONTEXT_WINDOW > 0, (
            f"DEFAULT_CONTEXT_WINDOW must be positive, got {DEFAULT_CONTEXT_WINDOW}"
        )
        assert DEFAULT_CONTEXT_WINDOW == 32768, (
            f"DEFAULT_CONTEXT_WINDOW design spec is 32768, got {DEFAULT_CONTEXT_WINDOW}"
        )


# ==============================================================================
# TestContextGuardDispatch — _run_autonomous_dispatch passes context_window through
# ==============================================================================


class TestContextGuardDispatch:
    """Verify that _run_autonomous_dispatch accepts and forwards context_window.

    Fails with TypeError until context_window param is added to _run_autonomous_dispatch.
    """

    def test_run_autonomous_dispatch_accepts_context_window(self):
        """_run_autonomous_dispatch must accept context_window and pass it to both loops."""
        agent = _make_agent()

        # We do NOT actually run the dispatch — just verify the call succeeds
        # with context_window kwarg.  Use FORMAT_RESPONSES path (mocks _autonomous_loop).
        from config.constants import FORMAT_RESPONSES  # noqa: E402

        # Patch both loop methods to be no-ops so we can inspect the call
        called_with_context_window = {}

        async def fake_loop(*args, **kwargs):
            called_with_context_window["value"] = kwargs.get("context_window")
            return "dispatch test done"

        agent._autonomous_loop = fake_loop  # type: ignore[method-assign]
        agent._autonomous_loop_anthropic = fake_loop  # type: ignore[method-assign]

        # TypeError until context_window param exists on _run_autonomous_dispatch
        result = asyncio.run(
            agent._run_autonomous_dispatch(
                dispatcher=MagicMock(),
                openai_tools=[],
                task="dispatch task",
                max_rounds=5,
                max_tokens=1024,
                api_format=FORMAT_RESPONSES,
                context_window=8192,
            )
        )

        assert result == "dispatch test done", (
            f"Dispatch should return loop result, got: {repr(result)}"
        )
        assert called_with_context_window.get("value") == 8192, (
            f"context_window must be forwarded to loop, got: {called_with_context_window}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
