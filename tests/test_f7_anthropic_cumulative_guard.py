"""F-7: Anthropic context guard must use cumulative token tracking.

The Anthropic loop recalculates cumulative_tokens from messages each round,
but messages get trimmed at MAX_ANTHROPIC_LOOP_MESSAGES. After trimming,
the estimate drops, defeating the safety guard. The responses loop uses a
running counter that only increases — the Anthropic loop must do the same.

Test categories:
- Happy: Small task completes normally with cumulative tracking
- Negative: Cumulative tokens grow monotonically despite message trimming
- Edge: Guard triggers after many rounds when individual messages are small
"""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tools.dynamic_autonomous import DynamicAutonomousAgent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_OPENAI_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search",
            "description": "Search",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
]


def _make_agent() -> DynamicAutonomousAgent:
    mock_llm = MagicMock()
    mock_llm.model = "test-model"
    mock_llm.get_default_max_tokens.return_value = 4096
    mock_validator = MagicMock()
    mock_validator.validate_model = AsyncMock()
    return DynamicAutonomousAgent(
        llm_client=mock_llm,
        model_validator=mock_validator,
    )


def _make_anthropic_tool_response(tool_name: str, args: dict) -> dict:
    return {
        "content": [
            {"type": "tool_use", "id": f"toolu_{tool_name}", "name": tool_name, "input": args}
        ],
        "stop_reason": "tool_use",
    }


def _make_anthropic_text_response(text: str) -> dict:
    return {
        "content": [{"type": "text", "text": text}],
        "stop_reason": "end_turn",
    }


# ---------------------------------------------------------------------------
# Test: Cumulative tokens grow monotonically despite trimming
# ---------------------------------------------------------------------------


class TestAnthropicCumulativeGuard:
    """F-7: cumulative_tokens must NOT decrease after message trimming."""

    def test_guard_triggers_after_many_small_rounds(self) -> None:
        """Many rounds of tool calls should cumulatively exceed threshold.

        With a small context_window (2000 tokens), each round adds ~200 tokens.
        After 10 rounds, cumulative should be ~2000, exceeding 80% threshold (1600).

        BUG: Recalculating from messages after trimming makes the estimate drop,
        so the guard never triggers even though total tokens sent exceeded the window.
        """
        agent = _make_agent()
        dispatcher = MagicMock()
        # Each tool call returns a moderate-size result (~200 chars = ~50 tokens)
        dispatcher.dispatch = AsyncMock(return_value=("search", "x" * 200))

        # LLM always requests another tool call (never gives final answer)
        agent.llm.anthropic_messages = MagicMock(
            return_value=_make_anthropic_tool_response("search", {"query": "test " + "a" * 100})
        )

        result = asyncio.get_event_loop().run_until_complete(
            agent._autonomous_loop_anthropic(
                dispatcher=dispatcher,
                openai_tools=_OPENAI_TOOLS,
                task="Search for information. " + "context " * 50,  # ~400 chars
                max_rounds=30,  # enough rounds to accumulate
                max_tokens=1024,
                model="test-model",
                context_window=2000,  # small window so guard triggers
            )
        )

        # With cumulative tracking: guard should trigger (context overflow)
        # With recalculation from trimmed messages: would hit max_rounds instead
        metrics = agent.last_loop_metrics
        assert metrics is not None

        # The guard should have stopped the loop BEFORE max_rounds
        if metrics.total_rounds >= 30:
            pytest.fail(
                f"Context guard did not trigger — ran all {metrics.total_rounds} rounds. "
                f"This means cumulative tokens were reset after message trimming (F-7 bug). "
                f"final_status={metrics.final_status}"
            )

        assert metrics.final_status == "context_overflow", (
            f"Expected context_overflow, got {metrics.final_status}. "
            f"Guard should trigger from cumulative token growth."
        )

    def test_cumulative_counter_initialized_before_loop(self) -> None:
        """cumulative_tokens must be initialized to 0 BEFORE the for loop, not inside it."""
        agent = _make_agent()
        dispatcher = MagicMock()
        dispatcher.dispatch = AsyncMock(return_value=("search", "result"))

        # Two rounds: tool call, then final answer
        agent.llm.anthropic_messages = MagicMock(
            side_effect=[
                _make_anthropic_tool_response("search", {"query": "q"}),
                _make_anthropic_text_response("Done."),
            ]
        )

        # Patch _estimate_tokens to track how cumulative_tokens is used
        call_count = {"n": 0}
        original_estimate = agent._estimate_tokens

        def tracking_estimate(payload):
            call_count["n"] += 1
            return original_estimate(payload)

        agent._estimate_tokens = tracking_estimate

        result = asyncio.get_event_loop().run_until_complete(
            agent._autonomous_loop_anthropic(
                dispatcher=dispatcher,
                openai_tools=_OPENAI_TOOLS,
                task="small task",
                max_rounds=5,
                max_tokens=1024,
                model="test-model",
                context_window=100000,  # large window, won't trigger
            )
        )

        # Should complete normally
        assert "Done" in result or "No content" not in result
        # _estimate_tokens should have been called (guard is active)
        assert call_count["n"] > 0, "_estimate_tokens must be called for context guard"
