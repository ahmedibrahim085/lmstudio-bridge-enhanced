"""F-1: LoopMetrics tracking must be present in the Anthropic loop.

The _autonomous_loop_anthropic() path is missing all metrics tracking
that exists in _autonomous_loop() — no last_loop_metrics, no round
metrics, no LoopMetrics finally block.

Test categories:
- Happy: Anthropic loop sets last_loop_metrics after completion
- Happy: Round metrics populated with tool call data
- Edge: Anthropic loop sets last_loop_metrics even on abort
- Boundary: Metrics include correct round count and error count
"""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tools.dynamic_autonomous import DynamicAutonomousAgent
from tools.loop_metrics import LoopMetrics, RoundMetrics


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_OPENAI_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
]


def _make_agent() -> DynamicAutonomousAgent:
    """Build agent with mocked LLM and model validator."""
    mock_llm = MagicMock()
    mock_llm.model = "test-model"
    mock_llm.get_default_max_tokens.return_value = 4096
    mock_validator = MagicMock()
    mock_validator.validate_model = AsyncMock()
    agent = DynamicAutonomousAgent(
        llm_client=mock_llm,
        model_validator=mock_validator,
    )
    return agent


def _make_anthropic_tool_response(tool_name: str, args: dict) -> dict:
    """Build an Anthropic response requesting a tool call."""
    return {
        "content": [
            {
                "type": "tool_use",
                "id": f"toolu_{tool_name}",
                "name": tool_name,
                "input": args,
            }
        ],
        "stop_reason": "tool_use",
    }


def _make_anthropic_text_response(text: str) -> dict:
    """Build an Anthropic response with final text (no tool calls)."""
    return {
        "content": [
            {"type": "text", "text": text}
        ],
        "stop_reason": "end_turn",
    }


# ---------------------------------------------------------------------------
# Test 1: last_loop_metrics set after successful Anthropic loop
# ---------------------------------------------------------------------------


class TestAnthropicLoopMetricsSet:
    """F-1: _autonomous_loop_anthropic must set last_loop_metrics."""

    def test_metrics_set_after_final_answer(self) -> None:
        """Anthropic loop with final answer must set last_loop_metrics."""
        agent = _make_agent()
        dispatcher = MagicMock()

        # One round: LLM returns final text immediately
        agent.llm.anthropic_messages = MagicMock(
            return_value=_make_anthropic_text_response("Task complete.")
        )

        asyncio.get_event_loop().run_until_complete(
            agent._autonomous_loop_anthropic(
                dispatcher=dispatcher,
                openai_tools=_OPENAI_TOOLS,
                task="test task",
                max_rounds=5,
                max_tokens=4096,
                model="test-model",
            )
        )

        assert agent.last_loop_metrics is not None, (
            "last_loop_metrics must be set after Anthropic loop completes"
        )
        assert isinstance(agent.last_loop_metrics, LoopMetrics)
        assert agent.last_loop_metrics.final_status == "completed"
        assert agent.last_loop_metrics.total_rounds >= 1

    def test_metrics_set_after_tool_call_then_answer(self) -> None:
        """Anthropic loop with tool call + final answer must have round metrics."""
        agent = _make_agent()
        dispatcher = MagicMock()
        dispatcher.dispatch = AsyncMock(return_value=("read_file", "file content"))

        # Round 0: tool call, Round 1: final answer
        agent.llm.anthropic_messages = MagicMock(
            side_effect=[
                _make_anthropic_tool_response("read_file", {"path": "/test"}),
                _make_anthropic_text_response("Done."),
            ]
        )

        asyncio.get_event_loop().run_until_complete(
            agent._autonomous_loop_anthropic(
                dispatcher=dispatcher,
                openai_tools=_OPENAI_TOOLS,
                task="test task",
                max_rounds=5,
                max_tokens=4096,
                model="test-model",
            )
        )

        metrics = agent.last_loop_metrics
        assert metrics is not None, "last_loop_metrics must be set"
        assert metrics.total_rounds >= 2, "Should have at least 2 rounds (tool + final)"
        assert len(metrics.rounds) >= 1, "Should have at least 1 round metric recorded"
        assert metrics.total_duration_seconds > 0


# ---------------------------------------------------------------------------
# Test 2: Round metrics populated with tool call data
# ---------------------------------------------------------------------------


class TestAnthropicRoundMetrics:
    """F-1: Per-round metrics must track tool calls and errors in Anthropic loop."""

    def test_round_metrics_include_tool_calls(self) -> None:
        """Round with tool call must have tool_calls list in RoundMetrics."""
        agent = _make_agent()
        dispatcher = MagicMock()
        dispatcher.dispatch = AsyncMock(return_value=("read_file", "content"))

        agent.llm.anthropic_messages = MagicMock(
            side_effect=[
                _make_anthropic_tool_response("read_file", {"path": "/f"}),
                _make_anthropic_text_response("Done."),
            ]
        )

        asyncio.get_event_loop().run_until_complete(
            agent._autonomous_loop_anthropic(
                dispatcher=dispatcher,
                openai_tools=_OPENAI_TOOLS,
                task="test",
                max_rounds=5,
                max_tokens=4096,
                model="test-model",
            )
        )

        metrics = agent.last_loop_metrics
        assert metrics is not None
        # Find the round that had tool calls
        tool_rounds = [r for r in metrics.rounds if len(r.tool_calls) > 0]
        assert len(tool_rounds) >= 1, "At least one round must have tool calls recorded"
        assert tool_rounds[0].tool_calls[0]["name"] == "read_file"


# ---------------------------------------------------------------------------
# Test 3: Metrics set even on abort (max consecutive errors)
# ---------------------------------------------------------------------------


class TestAnthropicMetricsOnAbort:
    """F-1: last_loop_metrics must be set even when loop aborts on errors."""

    def test_metrics_set_on_llm_errors(self) -> None:
        """Multiple LLM failures aborting the loop must still set metrics."""
        agent = _make_agent()
        dispatcher = MagicMock()

        # Every LLM call fails
        agent.llm.anthropic_messages = MagicMock(
            side_effect=RuntimeError("LLM connection failed")
        )

        result = asyncio.get_event_loop().run_until_complete(
            agent._autonomous_loop_anthropic(
                dispatcher=dispatcher,
                openai_tools=_OPENAI_TOOLS,
                task="test",
                max_rounds=5,
                max_tokens=4096,
                model="test-model",
            )
        )

        assert "aborted" in result.lower() or "error" in result.lower()
        assert agent.last_loop_metrics is not None, (
            "last_loop_metrics must be set even when loop aborts"
        )
        assert agent.last_loop_metrics.final_status == "aborted"
        assert agent.last_loop_metrics.total_errors >= 1


# ---------------------------------------------------------------------------
# Test 4: Metrics reflect max_rounds exhaustion
# ---------------------------------------------------------------------------


class TestAnthropicMetricsMaxRounds:
    """F-1: Metrics must show max_rounds status when loop exhausts rounds."""

    def test_metrics_on_max_rounds(self) -> None:
        """Exhausting max_rounds with only tool calls must produce max_rounds status."""
        agent = _make_agent()
        dispatcher = MagicMock()
        dispatcher.dispatch = AsyncMock(return_value=("read_file", "content"))

        # Always return tool calls — never a final answer
        agent.llm.anthropic_messages = MagicMock(
            return_value=_make_anthropic_tool_response("read_file", {"path": "/f"})
        )

        result = asyncio.get_event_loop().run_until_complete(
            agent._autonomous_loop_anthropic(
                dispatcher=dispatcher,
                openai_tools=_OPENAI_TOOLS,
                task="test",
                max_rounds=3,
                max_tokens=4096,
                model="test-model",
            )
        )

        assert "maximum rounds" in result.lower() or "incomplete" in result.lower()
        assert agent.last_loop_metrics is not None
        assert agent.last_loop_metrics.final_status == "max_rounds"
        assert agent.last_loop_metrics.total_rounds == 3


# ---------------------------------------------------------------------------
# Test 5: G-1 — Metrics set even on unexpected exception (try/finally safety)
# ---------------------------------------------------------------------------


class TestAnthropicMetricsTryFinally:
    """G-1: last_loop_metrics must be set even on unexpected exceptions.

    If an uncaught exception escapes the loop (e.g., from FormatAdapter
    or message building), the try/finally block must still set metrics.
    Without try/finally, last_loop_metrics stays None.
    """

    def test_metrics_set_on_unexpected_exception(self) -> None:
        """Unexpected exception mid-loop must still produce last_loop_metrics.

        The exception must occur AFTER the LLM call succeeds (outside the
        try/except for anthropic_messages) — e.g., in FormatAdapter response
        processing at line 1348. This is the uncovered path G-1 targets.
        """
        agent = _make_agent()
        dispatcher = MagicMock()
        dispatcher.dispatch = AsyncMock(return_value=("read_file", "content"))

        # LLM returns a valid tool-call response
        agent.llm.anthropic_messages = MagicMock(
            return_value=_make_anthropic_tool_response("read_file", {"path": "/f"})
        )

        # Patch FormatAdapter.extract_anthropic_tool_calls to crash
        # This simulates a bug in response parsing AFTER the LLM call succeeds
        with patch(
            "tools.dynamic_autonomous.FormatAdapter.extract_anthropic_tool_calls",
            side_effect=TypeError("unexpected NoneType in response parsing"),
        ), pytest.raises(TypeError, match="unexpected NoneType"):
            asyncio.get_event_loop().run_until_complete(
                agent._autonomous_loop_anthropic(
                    dispatcher=dispatcher,
                    openai_tools=_OPENAI_TOOLS,
                    task="test",
                    max_rounds=5,
                    max_tokens=4096,
                    model="test-model",
                )
            )

        # G-1: Even though an exception escaped, metrics must be set
        assert agent.last_loop_metrics is not None, (
            "last_loop_metrics must be set even when unexpected exception escapes. "
            "Wrap the for-loop in try/finally like _autonomous_loop()."
        )
        assert agent.last_loop_metrics.total_rounds >= 0
        assert agent.last_loop_metrics.total_duration_seconds > 0
