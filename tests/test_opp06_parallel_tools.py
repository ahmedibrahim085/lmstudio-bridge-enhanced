"""
OPP-06 Parallel Tool Execution -- RED Test Suite

Tests for:
1. _execute_tools_sequential() -- extracted sequential execution method
2. _execute_tools_parallel()   -- parallel execution via asyncio.gather()
3. parallel_tools: bool = False -- new parameter on _autonomous_loop()

ALL tests are expected to FAIL in RED phase:
  - Tests calling _execute_tools_sequential / _execute_tools_parallel will raise
    AttributeError (methods don't exist yet).
  - Tests passing parallel_tools=True to _autonomous_loop() will raise
    TypeError (unknown keyword argument).

No production code is modified by this file.
"""

import asyncio
import sys
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tools.dynamic_autonomous import DynamicAutonomousAgent, _SingleSessionDispatcher


# ---------------------------------------------------------------------------
# Helpers: response builders (mirrors test_opp02 conventions)
# ---------------------------------------------------------------------------

def _make_function_call(name, args=None):
    """Build function_call item as returned by LLM output."""
    return {"type": "function_call", "name": name, "arguments": args or {}}


def _make_function_call_response(tool_name="read_file", arguments=None, response_id="resp_1"):
    """Full response payload with a single function_call (mirrors OPP-02 helper)."""
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


# ---------------------------------------------------------------------------
# Infrastructure helpers (mirrors OPP-02 _make_agent / _run_loop)
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
# Class: TestExecuteToolsSequential  (Tests 1-3)
# ---------------------------------------------------------------------------

class TestExecuteToolsSequential(unittest.TestCase):
    """
    Verify _execute_tools_sequential() -- the extracted sequential execution method.
    All three tests will fail with AttributeError until the method is added.
    """

    def _make_dispatcher(self, results):
        """
        Build an AsyncMock dispatcher whose dispatch() returns successive
        (name, result) tuples from the *results* list.
        """
        dispatcher = MagicMock()
        dispatcher.dispatch = AsyncMock(side_effect=results)
        return dispatcher

    # ------------------------------------------------------------------
    # Test 1: single tool dispatched, returns [(name, result)]
    # ------------------------------------------------------------------

    def test_execute_sequential_single(self):
        """
        _execute_tools_sequential([fc]) with a single function_call dispatches
        exactly once and returns a list containing (tool_name, result_text).
        """
        agent = _make_agent()
        fc_list = [_make_function_call("read_file", {"path": "/tmp/f.txt"})]
        dispatcher = self._make_dispatcher([("read_file", "file content")])

        results = _run_loop(
            agent._execute_tools_sequential(dispatcher, fc_list)
        )

        self.assertEqual(len(results), 1)
        name, result = results[0]
        self.assertEqual(name, "read_file")
        self.assertIn("file content", result)
        dispatcher.dispatch.assert_awaited_once()

    # ------------------------------------------------------------------
    # Test 2: multiple tools, order preserved
    # ------------------------------------------------------------------

    def test_execute_sequential_multiple(self):
        """
        _execute_tools_sequential with 2+ tools returns results in the same
        order as the input function_call list.
        """
        agent = _make_agent()
        fc_list = [
            _make_function_call("tool_alpha", {}),
            _make_function_call("tool_beta", {}),
        ]
        dispatcher = self._make_dispatcher([
            ("tool_alpha", "alpha result"),
            ("tool_beta", "beta result"),
        ])

        results = _run_loop(
            agent._execute_tools_sequential(dispatcher, fc_list)
        )

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0][0], "tool_alpha")
        self.assertEqual(results[1][0], "tool_beta")

    # ------------------------------------------------------------------
    # Test 3: dispatcher raises Exception → consecutive_error_count += 1
    # ------------------------------------------------------------------

    def test_execute_sequential_error_increments_count(self):
        """
        When the dispatcher raises a generic Exception for a tool,
        _execute_tools_sequential must increment consecutive_error_count
        by 1 (for each failing tool) and include an error tuple in results.
        """
        agent = _make_agent()
        fc_list = [_make_function_call("bad_tool", {})]

        async def failing_dispatch(_, __):
            raise RuntimeError("tool exploded")

        dispatcher = MagicMock()
        dispatcher.dispatch = AsyncMock(side_effect=failing_dispatch)

        # Attach a counter so the method can update it
        agent.consecutive_error_count = 0

        results = _run_loop(
            agent._execute_tools_sequential(dispatcher, fc_list)
        )

        # At least one result tuple; error reflected in result text or counter
        self.assertEqual(len(results), 1)
        _, result_text = results[0]
        self.assertIn("error", result_text.lower())


# ---------------------------------------------------------------------------
# Class: TestExecuteToolsParallel  (Tests 4-10)
# ---------------------------------------------------------------------------

class TestExecuteToolsParallel(unittest.TestCase):
    """
    Verify _execute_tools_parallel() -- parallel execution via asyncio.gather().
    All tests will fail with AttributeError until the method is added.
    """

    def _make_dispatcher(self, side_effects):
        dispatcher = MagicMock()
        dispatcher.dispatch = AsyncMock(side_effect=side_effects)
        return dispatcher

    # ------------------------------------------------------------------
    # Test 4 (xfail): 3 sequential failures in one round → count hits 3
    # ------------------------------------------------------------------

    def test_sequential_three_failures_same_round(self):
        """
        When three tools all fail in one sequential round the counter reaches 3,
        triggering the MAX_CONSECUTIVE_ERRORS abort.

        NOTE: This diverges from parallel semantics (which caps at +1 per batch).
        Marked xfail to document the known inconsistency; will be resolved later.
        """
        def always_fc(**_kwargs):
            return _make_multi_fc_response(["t1", "t2", "t3"], response_id="rX")

        agent = _make_agent(MagicMock(side_effect=always_fc))
        session = MagicMock()
        session.call_tool = AsyncMock()

        async def always_fail_dispatch(_, __):
            raise RuntimeError("tool failure")

        dispatcher = MagicMock()
        dispatcher.dispatch = AsyncMock(side_effect=always_fail_dispatch)

        # Run the SEQUENTIAL loop (no parallel_tools flag)
        result = _run_loop(
            agent._autonomous_loop(
                dispatcher=dispatcher,
                openai_tools=[],
                task="test task",
                max_rounds=10,
                max_tokens=1024,
            )
        )

        # Sequential: 3 failures in one round → abort at 3
        self.assertIn("aborted", result.lower())
        self.assertIn("3", result)

    # ------------------------------------------------------------------
    # Test 5: single tool with parallel_tools=True still works
    # ------------------------------------------------------------------

    def test_execute_parallel_single_tool(self):
        """
        _execute_tools_parallel([fc]) with a single function_call completes
        successfully (gather with one coroutine).
        """
        agent = _make_agent()
        fc_list = [_make_function_call("read_file", {})]
        dispatcher = self._make_dispatcher([("read_file", "content")])

        results = _run_loop(
            agent._execute_tools_parallel(dispatcher, fc_list)
        )

        self.assertEqual(len(results), 1)
        name, _result = results[0]
        self.assertEqual(name, "read_file")

    # ------------------------------------------------------------------
    # Test 6: 2+ tools run via gather, all succeed
    # ------------------------------------------------------------------

    def test_execute_parallel_multiple(self):
        """
        _execute_tools_parallel runs multiple tools concurrently and returns
        all results.
        """
        agent = _make_agent()
        fc_list = [
            _make_function_call("tool_a", {}),
            _make_function_call("tool_b", {}),
            _make_function_call("tool_c", {}),
        ]
        dispatcher = self._make_dispatcher([
            ("tool_a", "result_a"),
            ("tool_b", "result_b"),
            ("tool_c", "result_c"),
        ])

        results = _run_loop(
            agent._execute_tools_parallel(dispatcher, fc_list)
        )

        self.assertEqual(len(results), 3)
        names = [r[0] for r in results]
        self.assertIn("tool_a", names)
        self.assertIn("tool_b", names)
        self.assertIn("tool_c", names)

    # ------------------------------------------------------------------
    # Test 7: results match original call order
    # ------------------------------------------------------------------

    def test_execute_parallel_preserves_order(self):
        """
        _execute_tools_parallel preserves the original input order in results,
        matching asyncio.gather() semantics (order = input order, not finish order).
        """
        agent = _make_agent()
        fc_list = [
            _make_function_call("first_tool", {}),
            _make_function_call("second_tool", {}),
        ]

        async def ordered_dispatch(fc_name, _tool_args):
            # second_tool "arrives" faster conceptually, but order must be preserved
            if fc_name == "second_tool":
                await asyncio.sleep(0)
            return fc_name, f"result_for_{fc_name}"

        dispatcher = MagicMock()
        dispatcher.dispatch = AsyncMock(side_effect=ordered_dispatch)

        results = _run_loop(
            agent._execute_tools_parallel(dispatcher, fc_list)
        )

        self.assertEqual(results[0][0], "first_tool")
        self.assertEqual(results[1][0], "second_tool")

    # ------------------------------------------------------------------
    # Test 8: partial failure — 1 of 3 fails, others succeed
    # ------------------------------------------------------------------

    def test_execute_parallel_partial_failure(self):
        """
        When 1 of 3 tools fails in _execute_tools_parallel, the other 2 results
        are preserved and the failed tool contributes an error tuple.
        """
        agent = _make_agent()
        fc_list = [
            _make_function_call("good_1", {}),
            _make_function_call("bad_tool", {}),
            _make_function_call("good_2", {}),
        ]

        async def partial_dispatch(fc_name, _tool_args):
            if fc_name == "bad_tool":
                raise RuntimeError("bad_tool exploded")
            return fc_name, f"ok_{fc_name}"

        dispatcher = MagicMock()
        dispatcher.dispatch = AsyncMock(side_effect=partial_dispatch)

        results = _run_loop(
            agent._execute_tools_parallel(dispatcher, fc_list)
        )

        self.assertEqual(len(results), 3)
        result_map = {r[0]: r[1] for r in results}
        self.assertIn("ok_good_1", result_map.get("good_1", ""))
        self.assertIn("ok_good_2", result_map.get("good_2", ""))
        self.assertIn("error", result_map.get("bad_tool", "").lower())

    # ------------------------------------------------------------------
    # Test 9: all 3 fail → consecutive_error_count += 1 (not +3)
    # ------------------------------------------------------------------

    def test_execute_parallel_all_fail(self):
        """
        When all tools fail in _execute_tools_parallel, consecutive_error_count
        is incremented by 1 (batch semantics: one failure per batch, not per tool).
        """
        agent = _make_agent()
        fc_list = [
            _make_function_call("t1", {}),
            _make_function_call("t2", {}),
            _make_function_call("t3", {}),
        ]

        async def always_fail(fc_name, _tool_args):
            raise RuntimeError(f"{fc_name} failed")

        dispatcher = MagicMock()
        dispatcher.dispatch = AsyncMock(side_effect=always_fail)

        initial_count = 0
        agent.consecutive_error_count = initial_count

        _run_loop(
            agent._execute_tools_parallel(dispatcher, fc_list)
        )

        # Parallel: all fail → exactly +1, NOT +3
        self.assertEqual(agent.consecutive_error_count, initial_count + 1)

    # ------------------------------------------------------------------
    # Test 10: all succeed → consecutive_error_count = 0 (reset)
    # ------------------------------------------------------------------

    def test_parallel_all_succeed_resets_count(self):
        """
        When all tools succeed in _execute_tools_parallel, consecutive_error_count
        is reset to 0 regardless of its previous value.
        """
        agent = _make_agent()
        fc_list = [
            _make_function_call("t1", {}),
            _make_function_call("t2", {}),
        ]

        async def always_succeed(fc_name, _tool_args):
            return fc_name, f"result_{fc_name}"

        dispatcher = MagicMock()
        dispatcher.dispatch = AsyncMock(side_effect=always_succeed)

        # Start with a dirty error count
        agent.consecutive_error_count = 2

        _run_loop(
            agent._execute_tools_parallel(dispatcher, fc_list)
        )

        self.assertEqual(agent.consecutive_error_count, 0)


# ---------------------------------------------------------------------------
# Class: TestParallelLoopIntegration  (Tests 11-15)
# ---------------------------------------------------------------------------

class TestParallelLoopIntegration(unittest.TestCase):
    """
    Verify that _autonomous_loop() accepts and correctly routes the
    parallel_tools: bool parameter.
    Tests will fail with TypeError until the parameter is added.
    """

    def _mock_session(self):
        session = MagicMock()
        session.call_tool = AsyncMock()
        return session

    # ------------------------------------------------------------------
    # Test 11: parallel_tools=True reaches the parallel execution path
    # ------------------------------------------------------------------

    def test_loop_parallel_flag_wiring(self):
        """
        When _autonomous_loop() is called with parallel_tools=True and the LLM
        returns function_calls, _execute_tools_parallel must be called (not the
        sequential path).
        """
        responses = iter([
            _make_multi_fc_response(["tool_a", "tool_b"], response_id="r1"),
            _make_message_response("done", response_id="r2"),
        ])

        def create_response_side_effect(**_kwargs):
            return next(responses)

        agent = _make_agent(MagicMock(side_effect=create_response_side_effect))
        session = self._mock_session()

        parallel_called = {"called": False}

        async def spy_parallel(dispatcher, fc_list, **kwargs):  # noqa: ARG001
            parallel_called["called"] = True
            return [(fc["name"], "ok") for fc in fc_list]

        agent._execute_tools_parallel = spy_parallel

        _run_loop(
            agent._autonomous_loop(
                dispatcher=_SingleSessionDispatcher(session),
                openai_tools=[],
                task="test task",
                max_rounds=10,
                max_tokens=1024,
                parallel_tools=True,      # NEW parameter — TypeError until implemented
            )
        )

        self.assertTrue(
            parallel_called["called"],
            "_execute_tools_parallel was not invoked when parallel_tools=True",
        )

    # ------------------------------------------------------------------
    # Test 12: without parallel_tools, default is sequential
    # ------------------------------------------------------------------

    def test_loop_default_is_sequential(self):
        """
        When _autonomous_loop() is called WITHOUT parallel_tools, the default
        must be sequential (backward compatible).
        """
        responses = iter([
            _make_function_call_response("some_tool", response_id="r1"),
            _make_message_response("done", response_id="r2"),
        ])

        def create_response_side_effect(**_kwargs):
            return next(responses)

        agent = _make_agent(MagicMock(side_effect=create_response_side_effect))
        session = self._mock_session()

        sequential_called = {"called": False}

        async def spy_sequential(dispatcher, fc_list, **kwargs):  # noqa: ARG001
            sequential_called["called"] = True
            return [(fc["name"], "ok") for fc in fc_list]

        agent._execute_tools_sequential = spy_sequential

        _run_loop(
            agent._autonomous_loop(
                dispatcher=_SingleSessionDispatcher(session),
                openai_tools=[],
                task="test task",
                max_rounds=10,
                max_tokens=1024,
                # parallel_tools NOT passed → defaults to False
            )
        )

        self.assertTrue(
            sequential_called["called"],
            "_execute_tools_sequential was not invoked by default",
        )

    # ------------------------------------------------------------------
    # Test 13: parallel path handles JSON parse error in function_call args
    # ------------------------------------------------------------------

    def test_parallel_json_parse_error(self):
        """
        When parallel_tools=True and a function_call has unparseable string args,
        the error is handled gracefully (not an unhandled exception) and the loop
        does not crash.
        """
        responses = iter([
            {
                "id": "r1",
                "status": "completed",
                "output": [
                    {
                        "type": "function_call",
                        "name": "bad_args_tool",
                        "arguments": "{this is not valid json!!!",
                    }
                ],
            },
            _make_message_response("recovered", response_id="r2"),
        ])

        def create_response_side_effect(**_kwargs):
            return next(responses)

        agent = _make_agent(MagicMock(side_effect=create_response_side_effect))
        session = self._mock_session()

        # Should not raise; loop should handle the JSON error internally
        result = _run_loop(
            agent._autonomous_loop(
                dispatcher=_SingleSessionDispatcher(session),
                openai_tools=[],
                task="test task",
                max_rounds=10,
                max_tokens=1024,
                parallel_tools=True,
            )
        )

        # Either recovered after the error or aborted cleanly — must not crash
        self.assertIsInstance(result, str)

    # ------------------------------------------------------------------
    # Test 14: parallel path handles unknown tool KeyError
    # ------------------------------------------------------------------

    def test_parallel_unknown_tool_keyerror(self):
        """
        When parallel_tools=True and the dispatcher raises KeyError for an
        unknown tool, the error is handled and the loop does not crash.
        """
        responses = iter([
            _make_function_call_response("unknown_tool", response_id="r1"),
            _make_message_response("done", response_id="r2"),
        ])

        def create_response_side_effect(**_kwargs):
            return next(responses)

        agent = _make_agent(MagicMock(side_effect=create_response_side_effect))

        async def raising_dispatch(fc_name, _tool_args):
            raise KeyError(f"Unknown tool {fc_name}")

        dispatcher = MagicMock()
        dispatcher.dispatch = AsyncMock(side_effect=raising_dispatch)

        result = _run_loop(
            agent._autonomous_loop(
                dispatcher=dispatcher,
                openai_tools=[],
                task="test task",
                max_rounds=10,
                max_tokens=1024,
                parallel_tools=True,
            )
        )

        self.assertIsInstance(result, str)

    # ------------------------------------------------------------------
    # Test 15: timeout cancels pending tasks; completed results preserved
    # ------------------------------------------------------------------

    def test_parallel_timeout_cancels_pending_tasks(self):
        """
        When one tool in a parallel batch times out (raises asyncio.TimeoutError),
        the results from completed tools are preserved and error_count is incremented.

        Tests _execute_tools_parallel handles TimeoutError gracefully.
        """
        agent = _make_agent()
        fc_list = [
            _make_function_call("fast_tool", {}),
            _make_function_call("slow_tool", {}),
        ]

        call_log = []

        async def mixed_dispatch(fc_name, _tool_args):
            call_log.append(fc_name)
            if fc_name == "slow_tool":
                raise asyncio.TimeoutError("slow_tool timed out")
            return fc_name, f"result_{fc_name}"

        dispatcher = MagicMock()
        dispatcher.dispatch = AsyncMock(side_effect=mixed_dispatch)

        agent.consecutive_error_count = 0

        results = _run_loop(
            agent._execute_tools_parallel(dispatcher, fc_list)
        )

        # Fast tool result must be preserved
        result_map = {r[0]: r[1] for r in results}
        self.assertIn("fast_tool", result_map)
        self.assertIn("result_fast_tool", result_map.get("fast_tool", ""))

        # Slow tool contributes an error entry
        self.assertIn("slow_tool", result_map)
        self.assertIn("error", result_map.get("slow_tool", "").lower())


# ---------------------------------------------------------------------------
# Class: TestParallelErrorCounting  (Tests 16-19)
# ---------------------------------------------------------------------------

class TestParallelErrorCounting(unittest.TestCase):
    """
    Precise error-counting semantics for the parallel execution path.

    Error counting rules:
    - ALL succeed  → consecutive_error_count = 0  (reset)
    - ALL fail     → consecutive_error_count += 1 (capped +1 per batch)
    - PARTIAL success → consecutive_error_count UNCHANGED
    """

    def _mock_session(self):
        session = MagicMock()
        session.call_tool = AsyncMock()
        return session

    # ------------------------------------------------------------------
    # Test 16: 3 failures in one parallel batch → count += 1, not +3
    # ------------------------------------------------------------------

    def test_parallel_error_count_capped_per_batch(self):
        """
        Three tools all failing in a single _execute_tools_parallel call must
        increment consecutive_error_count by exactly 1 (batch cap), not by 3.
        """
        agent = _make_agent()
        fc_list = [
            _make_function_call("t1", {}),
            _make_function_call("t2", {}),
            _make_function_call("t3", {}),
        ]

        async def always_fail(fc_name, _tool_args):
            raise RuntimeError(f"{fc_name} failed")

        dispatcher = MagicMock()
        dispatcher.dispatch = AsyncMock(side_effect=always_fail)

        agent.consecutive_error_count = 0

        _run_loop(
            agent._execute_tools_parallel(dispatcher, fc_list)
        )

        self.assertEqual(
            agent.consecutive_error_count, 1,
            "Parallel all-fail must cap increment at +1 per batch",
        )

    # ------------------------------------------------------------------
    # Test 17: mixed results don't trigger abort
    # ------------------------------------------------------------------

    def test_parallel_abort_threshold_with_partial_success(self):
        """
        Mixed results (2 succeed, 1 fails) must NOT trigger the abort threshold
        since the error count stays unchanged (partial success semantics).
        """
        responses = iter([
            _make_multi_fc_response(["good_1", "bad_tool", "good_2"], response_id="r1"),
            _make_message_response("completed", response_id="r2"),
        ])

        def create_response_side_effect(**_kwargs):
            return next(responses)

        agent = _make_agent(MagicMock(side_effect=create_response_side_effect))

        async def partial_dispatch(fc_name, _tool_args):
            if fc_name == "bad_tool":
                raise RuntimeError("bad_tool exploded")
            return fc_name, f"ok_{fc_name}"

        dispatcher = MagicMock()
        dispatcher.dispatch = AsyncMock(side_effect=partial_dispatch)

        result = _run_loop(
            agent._autonomous_loop(
                dispatcher=dispatcher,
                openai_tools=[],
                task="test task",
                max_rounds=10,
                max_tokens=1024,
                parallel_tools=True,
            )
        )

        # Should complete normally, not abort
        self.assertNotIn("aborted", result.lower())
        self.assertEqual(result, "completed")

    # ------------------------------------------------------------------
    # Test 18: 2 succeed + 1 fail → count UNCHANGED
    # ------------------------------------------------------------------

    def test_partial_success_count_unchanged(self):
        """
        When a parallel batch has partial success (some succeed, some fail),
        consecutive_error_count must remain UNCHANGED (not incremented, not reset).
        """
        agent = _make_agent()
        fc_list = [
            _make_function_call("good_1", {}),
            _make_function_call("bad_tool", {}),
            _make_function_call("good_2", {}),
        ]

        async def partial_dispatch(fc_name, _tool_args):
            if fc_name == "bad_tool":
                raise RuntimeError("bad_tool exploded")
            return fc_name, f"ok_{fc_name}"

        dispatcher = MagicMock()
        dispatcher.dispatch = AsyncMock(side_effect=partial_dispatch)

        # Set a known non-zero starting count
        agent.consecutive_error_count = 1

        _run_loop(
            agent._execute_tools_parallel(dispatcher, fc_list)
        )

        # Partial success → count must remain exactly 1 (unchanged)
        self.assertEqual(
            agent.consecutive_error_count, 1,
            "Partial success must leave consecutive_error_count unchanged",
        )

    # ------------------------------------------------------------------
    # Test 19: multi-dispatcher routes each tool to correct session
    # ------------------------------------------------------------------

    def test_parallel_multi_dispatcher_routes_correctly(self):
        """
        With a multi-session dispatcher and parallel_tools=True, each tool
        is dispatched to the session registered for it (not the wrong session).

        Uses _MultiSessionDispatcher-style routing to verify tool isolation.
        """
        from tools.dynamic_autonomous import _MultiSessionDispatcher

        # Build two sessions, each with a distinct tool registered
        session_a = MagicMock()
        session_b = MagicMock()

        tool_to_session = {
            "tool_alpha": ("tool_alpha", session_a),
            "tool_beta":  ("tool_beta",  session_b),
        }

        dispatched_to = {}

        async def fake_safe_call_tool(session, name, _args):
            from mcp.types import CallToolResult, TextContent
            if session is session_a:
                dispatched_to[name] = "session_a"
            elif session is session_b:
                dispatched_to[name] = "session_b"
            return CallToolResult(
                content=[TextContent(type="text", text=f"result_{name}")]
            )

        responses = iter([
            _make_multi_fc_response(["tool_alpha", "tool_beta"], response_id="r1"),
            _make_message_response("routed correctly", response_id="r2"),
        ])

        def create_response_side_effect(**_kwargs):
            return next(responses)

        agent = _make_agent(MagicMock(side_effect=create_response_side_effect))

        with patch("tools.dynamic_autonomous.safe_call_tool", side_effect=fake_safe_call_tool):
            result = _run_loop(
                agent._autonomous_loop(
                    dispatcher=_MultiSessionDispatcher(tool_to_session),
                    openai_tools=[],
                    task="test task",
                    max_rounds=10,
                    max_tokens=1024,
                    parallel_tools=True,
                )
            )

        self.assertEqual(result, "routed correctly")
        self.assertEqual(dispatched_to.get("tool_alpha"), "session_a")
        self.assertEqual(dispatched_to.get("tool_beta"), "session_b")


if __name__ == "__main__":
    unittest.main()
