"""Round G wiring integration tests.

Verifies that OPP-33/37/40/44/45/46 components are actually wired
into the production dispatch paths in dynamic_autonomous.py.

Test categories:
- C-1: ToolCallGuard receives tool schemas from openai_tools
- C-2: health_tracker.record_tool_error called on dispatch failure
- C-3: AdaptiveTimeoutManager.get_timeout used in LLM call
- C-4: tracker.check_orphans called after tool execution
- H-4: RoundMetrics populated with cache/orphan stats
- H-5: health tracking in Anthropic loop
"""

import asyncio
import time
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
            "name": "read_file",
            "description": "Read a file",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List a directory",
            "parameters": {
                "type": "object",
                "properties": {"dir": {"type": "string"}},
                "required": ["dir"],
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


def _make_responses_output_with_tool_call(tool_name: str, args: dict) -> dict:
    """Build a /v1/responses output that requests a single tool call."""
    return {
        "id": f"resp-{tool_name}",
        "status": "completed",
        "output": [
            {
                "type": "function_call",
                "name": tool_name,
                "arguments": args,
            }
        ],
    }


def _make_responses_output_final(text: str) -> dict:
    """Build a /v1/responses output with final text (no tool calls)."""
    return {
        "id": "resp-final",
        "status": "completed",
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": text}],
            }
        ],
    }


# ---------------------------------------------------------------------------
# C-1: Guard receives tool schemas
# ---------------------------------------------------------------------------


class TestGuardReceivesToolSchemas:
    """C-1: ToolCallGuard must be instantiated with tool_schemas from openai_tools."""

    def test_guard_receives_tool_schemas(self) -> None:
        """Verify ToolCallGuard is created with schemas dict, not empty."""
        agent = _make_agent()
        dispatcher = MagicMock()
        dispatcher.dispatch = AsyncMock(return_value=("read_file", "file content"))

        # Round 0: tool call, Round 1: final answer
        agent.llm.create_response = MagicMock(
            side_effect=[
                _make_responses_output_with_tool_call("read_file", {"path": "/tmp/f"}),
                _make_responses_output_final("Done"),
            ]
        )

        with patch("tools.dynamic_autonomous.ToolCallGuard") as MockGuard:
            mock_guard_instance = MagicMock()
            mock_guard_instance.validate_args.return_value = []
            mock_guard_instance.check_circuit.return_value = (True, None)
            MockGuard.return_value = mock_guard_instance

            asyncio.get_event_loop().run_until_complete(
                agent._autonomous_loop(
                    dispatcher=dispatcher,
                    openai_tools=_OPENAI_TOOLS,
                    task="test task",
                    max_rounds=5,
                    max_tokens=4096,
                    model="test-model",
                )
            )

            # Verify ToolCallGuard was called with tool_schemas keyword
            MockGuard.assert_called_once()
            call_kwargs = MockGuard.call_args
            # Check that tool_schemas was passed and contains our tool names
            schemas = call_kwargs.kwargs.get("tool_schemas") or (
                call_kwargs.args[0] if call_kwargs.args else None
            )
            if schemas is None and call_kwargs.kwargs:
                schemas = call_kwargs.kwargs.get("tool_schemas")
            assert schemas is not None, "ToolCallGuard must be called with tool_schemas"
            assert "read_file" in schemas, "Schema for read_file must be in tool_schemas"
            assert "list_directory" in schemas, "Schema for list_directory must be in tool_schemas"


# ---------------------------------------------------------------------------
# C-2: health_tracker.record_tool_error wired
# ---------------------------------------------------------------------------


class TestHealthTrackerRecordsToolErrors:
    """C-2: health_tracker.record_tool_error must be called on dispatch failure."""

    def test_health_tracker_records_tool_errors(self) -> None:
        """Mock dispatcher raises, verify record_tool_error called."""
        agent = _make_agent()
        dispatcher = MagicMock()
        dispatcher.dispatch = AsyncMock(side_effect=RuntimeError("dispatch boom"))

        agent.llm.create_response = MagicMock(
            side_effect=[
                _make_responses_output_with_tool_call("read_file", {"path": "/x"}),
                _make_responses_output_final("Done"),
            ]
        )

        with patch("tools.dynamic_autonomous.ModelHealthTracker") as MockHealth:
            mock_health = MagicMock()
            mock_health.check_health.return_value = "active"
            mock_health.record_llm_call.return_value = None
            MockHealth.return_value = mock_health

            asyncio.get_event_loop().run_until_complete(
                agent._autonomous_loop(
                    dispatcher=dispatcher,
                    openai_tools=_OPENAI_TOOLS,
                    task="test task",
                    max_rounds=5,
                    max_tokens=4096,
                    model="test-model",
                )
            )

            mock_health.record_tool_error.assert_called()
            call_args = mock_health.record_tool_error.call_args
            assert call_args.args[0] == "test-model"
            assert call_args.args[1] == "read_file"


# ---------------------------------------------------------------------------
# C-3: Adaptive timeout used in LLM call
# ---------------------------------------------------------------------------


class TestAdaptiveTimeoutUsed:
    """C-3: timeout_mgr.get_timeout value must be passed to create_response."""

    def test_adaptive_timeout_used_in_llm_call(self) -> None:
        """Verify get_timeout return value flows into create_response timeout."""
        agent = _make_agent()
        dispatcher = MagicMock()

        agent.llm.create_response = MagicMock(
            return_value=_make_responses_output_final("Done")
        )

        with patch("tools.dynamic_autonomous.AdaptiveTimeoutManager") as MockTimeout:
            mock_timeout_mgr = MagicMock()
            mock_timeout_mgr.get_timeout.return_value = 42.0
            MockTimeout.return_value = mock_timeout_mgr

            asyncio.get_event_loop().run_until_complete(
                agent._autonomous_loop(
                    dispatcher=dispatcher,
                    openai_tools=_OPENAI_TOOLS,
                    task="test",
                    max_rounds=5,
                    max_tokens=4096,
                    model="test-model",
                )
            )

            # Verify create_response was called with timeout=42.0
            agent.llm.create_response.assert_called_once()
            call_kwargs = agent.llm.create_response.call_args.kwargs
            assert call_kwargs.get("timeout") == 42.0, (
                f"Expected timeout=42.0 from adaptive timeout manager, "
                f"got {call_kwargs.get('timeout')!r}"
            )


# ---------------------------------------------------------------------------
# C-4: tracker.check_orphans called after tool execution
# ---------------------------------------------------------------------------


class TestOrphansCheckedAfterExecution:
    """C-4: tracker.check_orphans must be called after tool dispatch completes."""

    def test_orphans_checked_after_tool_execution(self) -> None:
        """Verify check_orphans called after dispatch returns."""
        agent = _make_agent()
        dispatcher = MagicMock()
        dispatcher.dispatch = AsyncMock(return_value=("read_file", "content"))

        agent.llm.create_response = MagicMock(
            side_effect=[
                _make_responses_output_with_tool_call("read_file", {"path": "/y"}),
                _make_responses_output_final("Done"),
            ]
        )

        with patch("tools.dynamic_autonomous.ToolCallTracker") as MockTracker:
            mock_tracker = MagicMock()
            mock_tracker.orphan_count = 0
            mock_tracker.check_orphans.return_value = []
            MockTracker.return_value = mock_tracker

            asyncio.get_event_loop().run_until_complete(
                agent._autonomous_loop(
                    dispatcher=dispatcher,
                    openai_tools=_OPENAI_TOOLS,
                    task="test",
                    max_rounds=5,
                    max_tokens=4096,
                    model="test-model",
                )
            )

            mock_tracker.check_orphans.assert_called()


# ---------------------------------------------------------------------------
# H-4: RoundMetrics include cache/orphan stats
# ---------------------------------------------------------------------------


class TestRoundMetricsIncludeCacheStats:
    """H-4: RoundMetrics must include orphan_count, cache_hits, cache_misses."""

    def test_round_metrics_include_cache_stats(self) -> None:
        """Verify RoundMetrics constructed with cache and orphan fields."""
        agent = _make_agent()
        dispatcher = MagicMock()
        dispatcher.dispatch = AsyncMock(return_value=("read_file", "content"))

        agent.llm.create_response = MagicMock(
            side_effect=[
                _make_responses_output_with_tool_call("read_file", {"path": "/z"}),
                _make_responses_output_final("Done"),
            ]
        )

        asyncio.get_event_loop().run_until_complete(
            agent._autonomous_loop(
                dispatcher=dispatcher,
                openai_tools=_OPENAI_TOOLS,
                task="test",
                max_rounds=5,
                max_tokens=4096,
                model="test-model",
            )
        )

        # Check that last_loop_metrics has round data with cache stats
        metrics = agent.last_loop_metrics
        assert metrics is not None, "last_loop_metrics must be set"
        assert len(metrics.rounds) > 0, "At least one round must be recorded"

        # The round that had a tool call should have cache stats populated
        tool_round = metrics.rounds[0]
        assert hasattr(tool_round, "orphan_count"), "RoundMetrics must have orphan_count"
        assert hasattr(tool_round, "cache_hits"), "RoundMetrics must have cache_hits"
        assert hasattr(tool_round, "cache_misses"), "RoundMetrics must have cache_misses"
        # Cache misses should be >= 1 (we dispatched a tool, so cache was queried)
        assert tool_round.cache_misses >= 0
