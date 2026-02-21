"""
OPP-07 Loop Observability Metrics -- RED Test Suite

Tests for:
1. RoundMetrics and LoopMetrics dataclasses
2. LoopMetrics.to_dashboard_format() contract
3. Integration of metrics into _autonomous_loop()

RED phase expectations:
  - Tests 1-8 (dataclass + dashboard format): FAIL on NotImplementedError
    from to_dashboard_format() stub.
  - Tests 9-24 (integration): FAIL on AttributeError:
    'DynamicAutonomousAgent' object has no attribute 'last_loop_metrics'

No production code is modified by this file.
"""

import asyncio
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tools.dynamic_autonomous import DynamicAutonomousAgent
from tools.loop_metrics import LoopMetrics, RoundMetrics

# ---------------------------------------------------------------------------
# Helpers: response builders (mirrors OPP-06 conventions)
# ---------------------------------------------------------------------------


def _make_function_call(name, args=None):
    """Build function_call item as returned by LLM output."""
    return {"type": "function_call", "name": name, "arguments": args or {}}


def _make_response(output_items, response_id="resp-001"):
    """Build mock create_response return value."""
    return {"id": response_id, "output": output_items}


def _make_text_output(text):
    """Build text message output item."""
    return {"type": "message", "content": [{"type": "output_text", "text": text}]}


def _make_function_call_response(tool_name="read_file", arguments=None, response_id="resp_1"):
    """Full response payload with a single function_call."""
    return {
        "id": response_id,
        "status": "completed",
        "output": [
            {
                "type": "function_call",
                "name": tool_name,
                "arguments": arguments or {"path": "/tmp/test.txt"},
            }
        ],
    }


def _make_message_response(text="Task complete.", response_id="resp_final"):
    """Full response payload with a text message (final answer)."""
    return {
        "id": response_id,
        "status": "completed",
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": text}],
            }
        ],
    }


def _make_multi_fc_response(tool_names, response_id="resp_multi"):
    """Full response payload with multiple function_calls."""
    return {
        "id": response_id,
        "status": "completed",
        "output": [
            {"type": "function_call", "name": name, "arguments": {}}
            for name in tool_names
        ],
    }


# ---------------------------------------------------------------------------
# Infrastructure helpers (mirrors OPP-06 _make_agent / _run_loop)
# ---------------------------------------------------------------------------


def _make_agent(mock_llm_create_response=None):
    """
    Build a DynamicAutonomousAgent with mocked internals.

    - llm.create_response replaced with mock_llm_create_response (sync MagicMock).
    - model_validator stubbed out.
    - mcp_json_path points to a dummy path.
    """
    mock_llm = MagicMock()
    if mock_llm_create_response is not None:
        mock_llm.create_response = mock_llm_create_response
    else:
        mock_llm.create_response = MagicMock()

    mock_validator = MagicMock()

    agent = DynamicAutonomousAgent.__new__(DynamicAutonomousAgent)
    agent.llm = mock_llm
    agent.model_validator = mock_validator
    agent.mcp_json_path = "/tmp/fake.mcp.json"
    return agent


def _run_loop(coro):
    """Run an async coroutine in a fresh event loop."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Class: TestRoundMetrics  (Test 1)
# ---------------------------------------------------------------------------


class TestRoundMetrics(unittest.TestCase):
    def test_round_metrics_construction(self):
        """RoundMetrics fields are set correctly."""
        rm = RoundMetrics(
            round_number=1,
            llm_call_duration_seconds=1.5,
            tool_calls=[{"name": "read_file", "duration_seconds": 0.3, "success": True}],
            error_count=0,
        )
        self.assertEqual(rm.round_number, 1)
        self.assertAlmostEqual(rm.llm_call_duration_seconds, 1.5)
        self.assertEqual(len(rm.tool_calls), 1)
        self.assertEqual(rm.error_count, 0)


# ---------------------------------------------------------------------------
# Class: TestLoopMetrics  (Tests 2-5)
# ---------------------------------------------------------------------------


class TestLoopMetrics(unittest.TestCase):
    def test_loop_metrics_construction(self):
        """LoopMetrics fields are set correctly."""
        lm = LoopMetrics(
            total_rounds=3,
            total_duration_seconds=5.0,
            total_tool_calls=7,
            total_errors=1,
            final_status="completed",
        )
        self.assertEqual(lm.total_rounds, 3)
        self.assertEqual(lm.total_errors, 1)
        self.assertEqual(lm.final_status, "completed")
        self.assertEqual(lm.max_rounds_tracked, 100)

    def test_loop_metrics_empty_rounds(self):
        """LoopMetrics with empty rounds list works."""
        lm = LoopMetrics(
            total_rounds=0,
            total_duration_seconds=0.0,
            total_tool_calls=0,
            total_errors=0,
            final_status="completed",
            rounds=[],
        )
        self.assertEqual(len(lm.rounds), 0)

    def test_loop_metrics_to_dashboard_format(self):
        """to_dashboard_format returns correct shape."""
        lm = LoopMetrics(
            total_rounds=2,
            total_duration_seconds=3.5,
            total_tool_calls=4,
            total_errors=0,
            final_status="completed",
        )
        fmt = lm.to_dashboard_format()
        self.assertIn("execution_time_seconds", fmt)
        self.assertIn("token_usage", fmt)
        self.assertIn("rounds", fmt)
        self.assertIn("tool_calls", fmt)
        self.assertIn("errors", fmt)
        self.assertIn("status", fmt)

    def test_dashboard_format_zero_rounds_no_division_error(self):
        """total_rounds=0 doesn't cause ZeroDivisionError."""
        lm = LoopMetrics(
            total_rounds=0,
            total_duration_seconds=0.0,
            total_tool_calls=0,
            total_errors=0,
            final_status="completed",
        )
        fmt = lm.to_dashboard_format()  # Must not raise
        self.assertEqual(fmt["rounds"], 0)


# ---------------------------------------------------------------------------
# Class: TestDashboardFormat  (Tests 6-8)
# ---------------------------------------------------------------------------


class TestDashboardFormat(unittest.TestCase):
    def _make_metrics(self, **kwargs):
        defaults = {
            "total_rounds": 1,
            "total_duration_seconds": 2.5,
            "total_tool_calls": 3,
            "total_errors": 0,
            "final_status": "completed",
        }
        defaults.update(kwargs)
        return LoopMetrics(**defaults)

    def test_dashboard_format_execution_time(self):
        """Key is 'execution_time_seconds'."""
        fmt = self._make_metrics(total_duration_seconds=4.2).to_dashboard_format()
        self.assertAlmostEqual(fmt["execution_time_seconds"], 4.2)

    def test_dashboard_format_token_usage_is_none(self):
        """token_usage is explicitly None."""
        fmt = self._make_metrics().to_dashboard_format()
        self.assertIsNone(fmt["token_usage"])

    def test_dashboard_format_tool_calls(self):
        """tool_calls count in output."""
        fmt = self._make_metrics(total_tool_calls=7).to_dashboard_format()
        self.assertEqual(fmt["tool_calls"], 7)


# ---------------------------------------------------------------------------
# Class: TestLoopMetricsIntegration  (Tests 9-17)
# ---------------------------------------------------------------------------


class TestLoopMetricsIntegration(unittest.TestCase):
    def _mock_session(self):
        session = MagicMock()
        session.call_tool = AsyncMock()
        return session

    def test_loop_sets_last_loop_metrics(self):
        """last_loop_metrics is set after loop completes."""
        responses = iter([_make_message_response("done", response_id="r1")])
        agent = _make_agent(MagicMock(side_effect=lambda **kw: next(responses)))
        dispatcher = MagicMock()
        dispatcher.dispatch = AsyncMock()

        _run_loop(
            agent._autonomous_loop(
                dispatcher=dispatcher,
                openai_tools=[],
                task="test",
                max_rounds=10,
                max_tokens=1024,
            )
        )

        self.assertIsNotNone(agent.last_loop_metrics)
        self.assertIsInstance(agent.last_loop_metrics, LoopMetrics)

    def test_loop_metrics_counts_tools(self):
        """total_tool_calls reflects the number of tool calls made."""
        responses = iter([
            _make_function_call_response("tool_a", response_id="r1"),
            _make_message_response("done", response_id="r2"),
        ])
        agent = _make_agent(MagicMock(side_effect=lambda **kw: next(responses)))
        dispatcher = MagicMock()
        dispatcher.dispatch = AsyncMock(return_value=("tool_a", "result"))

        _run_loop(
            agent._autonomous_loop(
                dispatcher=dispatcher,
                openai_tools=[],
                task="test",
                max_rounds=10,
                max_tokens=1024,
            )
        )

        self.assertEqual(agent.last_loop_metrics.total_tool_calls, 1)

    def test_loop_metrics_counts_errors(self):
        """total_errors reflects tool dispatch failures."""
        responses = iter([
            _make_function_call_response("bad_tool", response_id="r1"),
            _make_message_response("done", response_id="r2"),
        ])
        agent = _make_agent(MagicMock(side_effect=lambda **kw: next(responses)))

        async def fail_dispatch(name, args):
            raise RuntimeError("tool failed")

        dispatcher = MagicMock()
        dispatcher.dispatch = AsyncMock(side_effect=fail_dispatch)

        _run_loop(
            agent._autonomous_loop(
                dispatcher=dispatcher,
                openai_tools=[],
                task="test",
                max_rounds=10,
                max_tokens=1024,
            )
        )

        self.assertGreaterEqual(agent.last_loop_metrics.total_errors, 1)

    def test_loop_metrics_timing(self):
        """total_duration_seconds is greater than zero."""
        responses = iter([_make_message_response("done", response_id="r1")])
        agent = _make_agent(MagicMock(side_effect=lambda **kw: next(responses)))
        dispatcher = MagicMock()
        dispatcher.dispatch = AsyncMock()

        _run_loop(
            agent._autonomous_loop(
                dispatcher=dispatcher,
                openai_tools=[],
                task="test",
                max_rounds=10,
                max_tokens=1024,
            )
        )

        self.assertGreater(agent.last_loop_metrics.total_duration_seconds, 0)

    def test_loop_metrics_status_completed(self):
        """final_status is 'completed' when loop ends with a text answer."""
        responses = iter([_make_message_response("done", response_id="r1")])
        agent = _make_agent(MagicMock(side_effect=lambda **kw: next(responses)))
        dispatcher = MagicMock()
        dispatcher.dispatch = AsyncMock()

        _run_loop(
            agent._autonomous_loop(
                dispatcher=dispatcher,
                openai_tools=[],
                task="test",
                max_rounds=10,
                max_tokens=1024,
            )
        )

        self.assertEqual(agent.last_loop_metrics.final_status, "completed")

    def test_loop_metrics_status_max_rounds(self):
        """final_status is 'max_rounds' when loop hits the round limit."""
        # Always return function calls so the loop never gets a final answer.
        call_count = {"n": 0}

        def always_fc(**kwargs):
            call_count["n"] += 1
            return _make_function_call_response(
                "tool_x", response_id=f"r{call_count['n']}"
            )

        agent = _make_agent(MagicMock(side_effect=always_fc))
        dispatcher = MagicMock()
        dispatcher.dispatch = AsyncMock(return_value=("tool_x", "result"))

        _run_loop(
            agent._autonomous_loop(
                dispatcher=dispatcher,
                openai_tools=[],
                task="test",
                max_rounds=3,
                max_tokens=1024,
            )
        )

        self.assertEqual(agent.last_loop_metrics.final_status, "max_rounds")

    def test_loop_metrics_status_aborted(self):
        """final_status is 'aborted' when consecutive errors exceed threshold."""
        call_count = {"n": 0}

        def always_fc(**kwargs):
            call_count["n"] += 1
            return _make_function_call_response("bad_tool", response_id="rX")

        agent = _make_agent(MagicMock(side_effect=always_fc))

        async def fail_dispatch(name, args):
            raise RuntimeError("fail")

        dispatcher = MagicMock()
        dispatcher.dispatch = AsyncMock(side_effect=fail_dispatch)

        _run_loop(
            agent._autonomous_loop(
                dispatcher=dispatcher,
                openai_tools=[],
                task="test",
                max_rounds=100,
                max_tokens=1024,
            )
        )

        self.assertEqual(agent.last_loop_metrics.final_status, "aborted")

    def test_autonomous_with_mcp_returns_str(self):
        """_autonomous_loop() still returns a str (contract unchanged)."""
        responses = iter([_make_message_response("done", response_id="r1")])
        agent = _make_agent(MagicMock(side_effect=lambda **kw: next(responses)))
        dispatcher = MagicMock()
        dispatcher.dispatch = AsyncMock()

        result = _run_loop(
            agent._autonomous_loop(
                dispatcher=dispatcher,
                openai_tools=[],
                task="test",
                max_rounds=10,
                max_tokens=1024,
            )
        )

        self.assertIsInstance(result, str)

    def test_metrics_exception_swallowed(self):
        """Metrics failure does not break the loop — result is still returned."""
        responses = iter([_make_message_response("done", response_id="r1")])
        agent = _make_agent(MagicMock(side_effect=lambda **kw: next(responses)))
        dispatcher = MagicMock()
        dispatcher.dispatch = AsyncMock()

        # Patch LoopMetrics to raise on construction
        with patch(
            "tools.dynamic_autonomous.LoopMetrics",
            side_effect=RuntimeError("metrics broken"),
        ):
            result = _run_loop(
                agent._autonomous_loop(
                    dispatcher=dispatcher,
                    openai_tools=[],
                    task="test",
                    max_rounds=10,
                    max_tokens=1024,
                )
            )

        # Loop must still complete successfully
        self.assertEqual(result, "done")


# ---------------------------------------------------------------------------
# Class: TestLoopMetricsEarlyReturns  (Tests 18-22)
# ---------------------------------------------------------------------------


class TestLoopMetricsEarlyReturns(unittest.TestCase):
    def test_loop_metrics_set_on_json_parse_abort(self):
        """last_loop_metrics is populated even when the loop aborts on JSON parse error."""

        def bad_json(**kwargs):
            return {
                "id": "rX",
                "status": "completed",
                "output": [
                    {
                        "type": "function_call",
                        "name": "t",
                        "arguments": "{bad json!!!",
                    }
                ],
            }

        agent = _make_agent(MagicMock(side_effect=bad_json))
        dispatcher = MagicMock()
        dispatcher.dispatch = AsyncMock()

        _run_loop(
            agent._autonomous_loop(
                dispatcher=dispatcher,
                openai_tools=[],
                task="test",
                max_rounds=100,
                max_tokens=1024,
            )
        )

        self.assertIsNotNone(agent.last_loop_metrics)
        self.assertEqual(agent.last_loop_metrics.final_status, "aborted")

    def test_loop_metrics_set_on_keyerror_abort(self):
        """last_loop_metrics is populated on KeyError abort."""

        def always_fc(**kwargs):
            return _make_function_call_response("unknown", response_id="rX")

        agent = _make_agent(MagicMock(side_effect=always_fc))

        async def keyerror_dispatch(name, args):
            raise KeyError(f"Unknown tool {name}")

        dispatcher = MagicMock()
        dispatcher.dispatch = AsyncMock(side_effect=keyerror_dispatch)

        _run_loop(
            agent._autonomous_loop(
                dispatcher=dispatcher,
                openai_tools=[],
                task="test",
                max_rounds=100,
                max_tokens=1024,
            )
        )

        self.assertIsNotNone(agent.last_loop_metrics)
        self.assertEqual(agent.last_loop_metrics.final_status, "aborted")

    def test_loop_metrics_set_on_max_rounds(self):
        """last_loop_metrics is populated and reflects max_rounds status."""

        def always_fc(**kwargs):
            return _make_function_call_response("tool", response_id="rX")

        agent = _make_agent(MagicMock(side_effect=always_fc))
        dispatcher = MagicMock()
        dispatcher.dispatch = AsyncMock(return_value=("tool", "ok"))

        _run_loop(
            agent._autonomous_loop(
                dispatcher=dispatcher,
                openai_tools=[],
                task="test",
                max_rounds=3,
                max_tokens=1024,
            )
        )

        self.assertIsNotNone(agent.last_loop_metrics)
        self.assertEqual(agent.last_loop_metrics.final_status, "max_rounds")
        self.assertEqual(agent.last_loop_metrics.total_rounds, 3)

    def test_loop_metrics_rounds_capped_at_100(self):
        """rounds list in LoopMetrics is capped at max_rounds_tracked (100)."""
        lm = LoopMetrics(
            total_rounds=0,
            total_duration_seconds=0,
            total_tool_calls=0,
            total_errors=0,
            final_status="completed",
            rounds=[],
        )
        for i in range(150):
            rm = RoundMetrics(
                round_number=i,
                llm_call_duration_seconds=0.1,
                tool_calls=[],
                error_count=0,
            )
            lm.rounds.append(rm)
            if len(lm.rounds) > lm.max_rounds_tracked:
                lm.rounds.pop(0)
        self.assertLessEqual(len(lm.rounds), 100)

    def test_loop_metrics_total_errors_cumulative(self):
        """total_errors accumulates across rounds and never resets."""
        # Round 1: function call → dispatch fails (error)
        # Round 2: function call → dispatch succeeds
        # Round 3: final text answer → loop completes
        call_count = {"n": 0}

        def alternating(**kwargs):
            call_count["n"] += 1
            if call_count["n"] <= 2:
                return _make_function_call_response(
                    "tool", response_id=f"r{call_count['n']}"
                )
            return _make_message_response("done", response_id="r_final")

        dispatch_count = {"n": 0}

        async def first_fails(name, args):
            dispatch_count["n"] += 1
            if dispatch_count["n"] == 1:
                raise RuntimeError("error in round 1")
            return name, "ok"

        agent = _make_agent(MagicMock(side_effect=alternating))
        dispatcher = MagicMock()
        dispatcher.dispatch = AsyncMock(side_effect=first_fails)

        _run_loop(
            agent._autonomous_loop(
                dispatcher=dispatcher,
                openai_tools=[],
                task="test",
                max_rounds=10,
                max_tokens=1024,
            )
        )

        # total_errors must include the error from round 1 even though round 2 succeeded
        self.assertGreaterEqual(agent.last_loop_metrics.total_errors, 1)


# ---------------------------------------------------------------------------
# Class: TestLoopMetricsConnectionErrors  (Tests 23-24)
# ---------------------------------------------------------------------------


class TestLoopMetricsConnectionErrors(unittest.TestCase):
    def test_loop_metrics_set_on_llm_connection_error(self):
        """ConnectionError from LLM → loop aborts but last_loop_metrics is still set."""
        import requests

        def connection_error(**kwargs):
            raise requests.exceptions.ConnectionError("LLM unreachable")

        agent = _make_agent(MagicMock(side_effect=connection_error))
        dispatcher = MagicMock()
        dispatcher.dispatch = AsyncMock()

        _run_loop(
            agent._autonomous_loop(
                dispatcher=dispatcher,
                openai_tools=[],
                task="test",
                max_rounds=10,
                max_tokens=1024,
            )
        )

        self.assertIsNotNone(agent.last_loop_metrics)

    def test_loop_metrics_set_on_max_consecutive_errors(self):
        """MAX_CONSECUTIVE_ERRORS threshold → status='aborted' with error count >= 5."""
        # Use max_rounds=100 so the abort comes from errors, not round limit.
        call_count = {"n": 0}

        def always_fc(**kwargs):
            call_count["n"] += 1
            return _make_function_call_response("bad", response_id="rX")

        agent = _make_agent(MagicMock(side_effect=always_fc))

        async def always_fail(name, args):
            raise RuntimeError("fail")

        dispatcher = MagicMock()
        dispatcher.dispatch = AsyncMock(side_effect=always_fail)

        _run_loop(
            agent._autonomous_loop(
                dispatcher=dispatcher,
                openai_tools=[],
                task="test",
                max_rounds=100,
                max_tokens=1024,
            )
        )

        self.assertIsNotNone(agent.last_loop_metrics)
        self.assertEqual(agent.last_loop_metrics.final_status, "aborted")
        self.assertGreaterEqual(agent.last_loop_metrics.total_errors, 3)


if __name__ == "__main__":
    unittest.main()
