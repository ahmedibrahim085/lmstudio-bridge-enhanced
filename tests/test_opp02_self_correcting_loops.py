"""
OPP-02 Self-Correcting Loops -- Test Suite

Tests for consecutive error tracking, self-correction hints,
finish_reason checking, and reasoning output preservation in the
autonomous loop.

All tests are self-contained -- no LM Studio or MCP instance required.
unittest.mock is used to mock self.llm.create_response and safe_call_tool.
"""

import asyncio
import sys
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Add project root so all imports resolve
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tools.dynamic_autonomous import _SingleSessionDispatcher


# ---------------------------------------------------------------------------
# Helpers: canonical response builders
# ---------------------------------------------------------------------------

def _make_function_call_response(
    tool_name: str = "read_file",
    arguments: dict | None = None,
    response_id: str = "resp_1",
) -> dict:
    """Return a /v1/responses payload that contains a single function_call."""
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


def _make_message_response(
    text: str = "Task complete.",
    response_id: str = "resp_final",
) -> dict:
    """Return a /v1/responses payload with a text message (final answer)."""
    return {
        "id": response_id,
        "status": "completed",
        "output": [
            {
                "type": "message",
                "content": [
                    {"type": "output_text", "text": text}
                ],
            }
        ],
    }


def _make_incomplete_response(
    reason: str = "max_output_tokens",
    response_id: str = "resp_incomplete",
) -> dict:
    """Return a /v1/responses payload with status=incomplete."""
    return {
        "id": response_id,
        "status": "incomplete",
        "incomplete_details": {"reason": reason},
        "output": [
            {
                "type": "message",
                "content": [
                    {"type": "output_text", "text": "Partial answer..."}
                ],
            }
        ],
    }


def _make_reasoning_response(
    reasoning_text: str = "I should use read_file to get the content.",
    tool_name: str = "read_file",
    response_id: str = "resp_reasoning",
) -> dict:
    """Return a /v1/responses payload that contains reasoning + function_call."""
    return {
        "id": response_id,
        "status": "completed",
        "output": [
            {
                "type": "reasoning",
                "content": [
                    {"type": "reasoning_text", "text": reasoning_text}
                ],
            },
            {
                "type": "function_call",
                "name": tool_name,
                "arguments": {"path": "/tmp/test.txt"},
            },
        ],
    }


def _make_agent(mock_llm_create_response=None) -> "DynamicAutonomousAgent":
    """
    Build a DynamicAutonomousAgent with mocked internals.

    - llm.create_response is replaced with mock_llm_create_response
      (if provided, otherwise a plain MagicMock).
    - model_validator is stubbed out.
    - mcp_json_path is set to a dummy path (never read in unit tests).
    """
    from tools.dynamic_autonomous import DynamicAutonomousAgent

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
# Test 1: Constant exists
# ---------------------------------------------------------------------------


class TestMaxConsecutiveErrorsConstant(unittest.TestCase):
    def test_constant_exists(self):
        """MAX_CONSECUTIVE_ERRORS must be an int equal to 3."""
        from config.constants import MAX_CONSECUTIVE_ERRORS

        self.assertIsInstance(MAX_CONSECUTIVE_ERRORS, int)
        self.assertEqual(MAX_CONSECUTIVE_ERRORS, 3)


# ---------------------------------------------------------------------------
# Tests 2-8: Counter behaviour (via _autonomous_loop)
# ---------------------------------------------------------------------------


class TestConsecutiveErrorCounter(unittest.TestCase):
    """
    Verify counter increment / reset behaviour by driving _autonomous_loop
    through controlled sequences of LLM responses and tool outcomes.
    """

    def _mock_session(self):
        """Return a mock ClientSession (only call_tool matters)."""
        session = MagicMock()
        session.call_tool = AsyncMock()
        return session

    # ------------------------------------------------------------------
    # Test 2: counter resets to 0 after a successful tool call
    # ------------------------------------------------------------------

    def test_counter_resets_to_zero_after_success(self):
        """
        Sequence:
          round 0 → function_call (tool fails → count=1)
          round 1 → function_call (tool succeeds → count=0)
          round 2 → message "done" (loop exits)
        The loop must NOT abort early because the counter was reset.
        """
        from mcp.types import CallToolResult, TextContent

        success_result = CallToolResult(
            content=[TextContent(type="text", text="file content")]
        )

        responses = iter([
            _make_function_call_response("read_file", response_id="r1"),
            _make_function_call_response("read_file", response_id="r2"),
            _make_message_response("done", response_id="r3"),
        ])

        def create_response_side_effect(**kwargs):
            return next(responses)

        agent = _make_agent(MagicMock(side_effect=create_response_side_effect))
        session = self._mock_session()

        call_count = {"n": 0}

        async def fake_safe_call_tool(session_, name, args):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RuntimeError("transient failure")
            return success_result

        with patch(
            "tools.dynamic_autonomous.safe_call_tool",
            side_effect=fake_safe_call_tool,
        ):
            result = _run_loop(
                agent._autonomous_loop(
                    dispatcher=_SingleSessionDispatcher(session),
                    openai_tools=[],
                    task="test task",
                    max_rounds=10,
                    max_tokens=1024,
                )
            )

        # The loop should complete with the final message, not abort
        self.assertEqual(result, "done")

    # ------------------------------------------------------------------
    # Test 3: counter increments on tool failure
    # ------------------------------------------------------------------

    def test_counter_increments_on_tool_failure(self):
        """
        One tool failure must drive the abort after 3 consecutive failures
        (by returning 3 consecutive tool-raising responses).
        """
        from mcp.types import CallToolResult, TextContent

        # LLM always requests a tool call
        def create_response_side_effect(**kwargs):
            return _make_function_call_response("bad_tool", response_id="rX")

        agent = _make_agent(MagicMock(side_effect=create_response_side_effect))
        session = self._mock_session()

        async def fake_safe_call_tool(session_, name, args):
            raise RuntimeError("persistent tool failure")

        with patch(
            "tools.dynamic_autonomous.safe_call_tool",
            side_effect=fake_safe_call_tool,
        ):
            result = _run_loop(
                agent._autonomous_loop(
                    dispatcher=_SingleSessionDispatcher(session),
                    openai_tools=[],
                    task="test task",
                    max_rounds=20,
                    max_tokens=1024,
                )
            )

        self.assertIn("aborted", result.lower())

    # ------------------------------------------------------------------
    # Test 4: counter increments on LLM call failure
    # ------------------------------------------------------------------

    def test_counter_increments_on_llm_failure(self):
        """
        3 consecutive LLM failures must trigger abort.
        """
        agent = _make_agent(
            MagicMock(side_effect=ConnectionError("LM Studio down"))
        )
        session = self._mock_session()

        result = _run_loop(
            agent._autonomous_loop(
                dispatcher=_SingleSessionDispatcher(session),
                openai_tools=[],
                task="test task",
                max_rounds=20,
                max_tokens=1024,
            )
        )

        self.assertIn("aborted", result.lower())

    # ------------------------------------------------------------------
    # Test 5: counter increments on JSON parse failure
    # ------------------------------------------------------------------

    def test_counter_increments_on_json_parse_failure(self):
        """
        3 consecutive JSON-parse errors must trigger abort.
        A function_call with string arguments that is not valid JSON triggers
        the JSONDecodeError path.
        """
        def create_response_side_effect(**kwargs):
            return {
                "id": "rX",
                "status": "completed",
                "output": [
                    {
                        "type": "function_call",
                        "name": "bad_tool",
                        "arguments": "{this is not valid json!!!",  # string, bad JSON
                    }
                ],
            }

        agent = _make_agent(MagicMock(side_effect=create_response_side_effect))
        session = self._mock_session()

        result = _run_loop(
            agent._autonomous_loop(
                dispatcher=_SingleSessionDispatcher(session),
                openai_tools=[],
                task="test task",
                max_rounds=20,
                max_tokens=1024,
            )
        )

        self.assertIn("aborted", result.lower())

    # ------------------------------------------------------------------
    # Test 6: abort triggers at MAX_CONSECUTIVE_ERRORS
    # ------------------------------------------------------------------

    def test_abort_triggers_at_max_consecutive_errors(self):
        """
        Exactly 3 consecutive LLM failures must return a message containing
        'aborted' (case-insensitive).
        """
        call_count = {"n": 0}

        def create_response_side_effect(**kwargs):
            call_count["n"] += 1
            raise RuntimeError(f"failure #{call_count['n']}")

        agent = _make_agent(MagicMock(side_effect=create_response_side_effect))
        session = self._mock_session()

        result = _run_loop(
            agent._autonomous_loop(
                dispatcher=_SingleSessionDispatcher(session),
                openai_tools=[],
                task="test task",
                max_rounds=20,
                max_tokens=1024,
            )
        )

        self.assertIn("aborted", result.lower())
        # Exactly 3 LLM calls should have been made
        self.assertEqual(call_count["n"], 3)

    # ------------------------------------------------------------------
    # Test 7: abort does NOT trigger before max (count=2 → loop continues)
    # ------------------------------------------------------------------

    def test_abort_does_not_trigger_before_max(self):
        """
        After 2 consecutive LLM failures the loop must still be alive.
        On the 3rd call we return a successful message to confirm this.
        """
        call_count = {"n": 0}

        def create_response_side_effect(**kwargs):
            call_count["n"] += 1
            if call_count["n"] < 3:
                raise RuntimeError(f"failure #{call_count['n']}")
            return _make_message_response("recovered", response_id="r_ok")

        agent = _make_agent(MagicMock(side_effect=create_response_side_effect))
        session = self._mock_session()

        result = _run_loop(
            agent._autonomous_loop(
                dispatcher=_SingleSessionDispatcher(session),
                openai_tools=[],
                task="test task",
                max_rounds=20,
                max_tokens=1024,
            )
        )

        # Loop should have recovered; result should NOT be an abort message
        self.assertNotIn("aborted", result.lower())
        self.assertEqual(result, "recovered")

    # ------------------------------------------------------------------
    # Test 8: counter does not accumulate across resets
    # ------------------------------------------------------------------

    def test_counter_does_not_accumulate_across_resets(self):
        """
        Alternating success/failure pattern must never reach 3 consecutive
        errors: failure → success → failure → success → final message.
        The loop must NOT abort.
        """
        from mcp.types import CallToolResult, TextContent

        success_result = CallToolResult(
            content=[TextContent(type="text", text="ok")]
        )

        # LLM always requests a tool call (until round 4 → final message)
        call_count = {"n": 0}

        def create_response_side_effect(**kwargs):
            call_count["n"] += 1
            if call_count["n"] >= 5:
                return _make_message_response("all done", response_id="r_done")
            return _make_function_call_response("some_tool", response_id=f"r{call_count['n']}")

        tool_call_count = {"n": 0}

        async def alternating_tool(session_, name, args):
            tool_call_count["n"] += 1
            if tool_call_count["n"] % 2 == 1:
                raise RuntimeError("odd failure")
            return success_result

        agent = _make_agent(MagicMock(side_effect=create_response_side_effect))
        session = self._mock_session()

        with patch(
            "tools.dynamic_autonomous.safe_call_tool",
            side_effect=alternating_tool,
        ):
            result = _run_loop(
                agent._autonomous_loop(
                    dispatcher=_SingleSessionDispatcher(session),
                    openai_tools=[],
                    task="test task",
                    max_rounds=20,
                    max_tokens=1024,
                )
            )

        self.assertNotIn("aborted", result.lower())
        self.assertEqual(result, "all done")


# ---------------------------------------------------------------------------
# Tests 9-12: Self-correction hint (_build_input_text)
# ---------------------------------------------------------------------------


class TestSelfCorrectionHint(unittest.TestCase):
    """
    Verify _build_input_text() injects (or withholds) the self-correction hint
    based on consecutive_error_count.
    """

    def setUp(self):
        from tools.dynamic_autonomous import DynamicAutonomousAgent
        self.build = DynamicAutonomousAgent._build_input_text

    def test_no_hint_when_no_errors(self):
        """Test 9: count=0 → no hint in output text."""
        text = self.build(
            round_num=1,
            task="do something",
            pending_tool_results=[],
            consecutive_error_count=0,
        )
        self.assertNotIn("consecutive error", text.lower())

    def test_no_hint_when_single_error(self):
        """Test 10: count=1 → no hint (threshold is >= 2)."""
        text = self.build(
            round_num=1,
            task="do something",
            pending_tool_results=[],
            consecutive_error_count=1,
        )
        self.assertNotIn("consecutive error", text.lower())

    def test_hint_injected_at_count_two(self):
        """Test 11: count=2 → 'consecutive errors' appears in output text."""
        text = self.build(
            round_num=1,
            task="do something",
            pending_tool_results=[],
            consecutive_error_count=2,
        )
        self.assertIn("consecutive error", text.lower())

    def test_hint_absent_on_first_round(self):
        """Test 12: round_num=0 → raw task text, no hint injection."""
        task = "Just do the task"
        text = self.build(
            round_num=0,
            task=task,
            pending_tool_results=[],
            consecutive_error_count=5,  # high error count but round 0
        )
        # On first round the input is simply the task
        self.assertEqual(text, task)


# ---------------------------------------------------------------------------
# Tests 13-15: LLM exception handling and tool failure abort
# ---------------------------------------------------------------------------


class TestExceptionHandling(unittest.TestCase):

    def _mock_session(self):
        session = MagicMock()
        session.call_tool = AsyncMock()
        return session

    def test_llm_exception_is_caught_and_counted(self):
        """
        Test 13: Mock LLM raises once then returns final message.
        Loop must NOT crash; it must continue and return the final answer.
        """
        call_count = {"n": 0}

        def create_response_side_effect(**kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise ConnectionError("transient LLM error")
            return _make_message_response("recovered fine", response_id="r2")

        agent = _make_agent(MagicMock(side_effect=create_response_side_effect))
        session = self._mock_session()

        result = _run_loop(
            agent._autonomous_loop(
                dispatcher=_SingleSessionDispatcher(session),
                openai_tools=[],
                task="test task",
                max_rounds=20,
                max_tokens=1024,
            )
        )

        self.assertNotIn("aborted", result.lower())
        self.assertEqual(result, "recovered fine")

    def test_three_consecutive_llm_failures_abort_loop(self):
        """
        Test 14: 3 consecutive LLM failures → returns abort message.
        """
        agent = _make_agent(
            MagicMock(side_effect=ConnectionError("LM Studio down"))
        )
        session = self._mock_session()

        result = _run_loop(
            agent._autonomous_loop(
                dispatcher=_SingleSessionDispatcher(session),
                openai_tools=[],
                task="test task",
                max_rounds=20,
                max_tokens=1024,
            )
        )

        self.assertIn("aborted", result.lower())
        # Must mention error count or context
        self.assertIn("3", result)

    def test_three_consecutive_tool_failures_abort_loop(self):
        """
        Test 15: 3 consecutive tool failures → returns abort message.
        """
        def create_response_side_effect(**kwargs):
            return _make_function_call_response("fail_tool", response_id="rX")

        agent = _make_agent(MagicMock(side_effect=create_response_side_effect))
        session = self._mock_session()

        async def always_fail_tool(session_, name, args):
            raise RuntimeError("tool always fails")

        with patch(
            "tools.dynamic_autonomous.safe_call_tool",
            side_effect=always_fail_tool,
        ):
            result = _run_loop(
                agent._autonomous_loop(
                    dispatcher=_SingleSessionDispatcher(session),
                    openai_tools=[],
                    task="test task",
                    max_rounds=20,
                    max_tokens=1024,
                )
            )

        self.assertIn("aborted", result.lower())


# ---------------------------------------------------------------------------
# Tests 16-17: finish_reason checking
# ---------------------------------------------------------------------------


class TestFinishReasonChecking(unittest.TestCase):
    """
    Verify that status='incomplete' triggers a warning log, and
    status='completed' does not.
    """

    def _mock_session(self):
        session = MagicMock()
        session.call_tool = AsyncMock()
        return session

    def test_finish_reason_length_detected(self):
        """
        Test 16: status='incomplete' with reason='max_output_tokens' →
        log_error (or log_info) is called with information about the truncation.
        We check that a warning is logged via the logging framework.
        """
        from mcp.types import CallToolResult, TextContent

        responses = iter([
            _make_incomplete_response("max_output_tokens", response_id="r_inc"),
            _make_message_response("done after incomplete", response_id="r_done"),
        ])

        def create_response_side_effect(**kwargs):
            return next(responses)

        agent = _make_agent(MagicMock(side_effect=create_response_side_effect))
        session = self._mock_session()

        logged_messages = []

        with patch(
            "tools.dynamic_autonomous.log_error",
            side_effect=lambda msg: logged_messages.append(msg),
        ):
            _run_loop(
                agent._autonomous_loop(
                    dispatcher=_SingleSessionDispatcher(session),
                    openai_tools=[],
                    task="test task",
                    max_rounds=10,
                    max_tokens=1024,
                )
            )

        # At least one log_error call must mention 'incomplete' or 'max_output_tokens'
        incomplete_logged = any(
            "incomplete" in m.lower() or "max_output_tokens" in m.lower()
            for m in logged_messages
        )
        self.assertTrue(
            incomplete_logged,
            f"Expected 'incomplete' or 'max_output_tokens' in logged messages. Got: {logged_messages}",
        )

    def test_finish_reason_complete_no_warning(self):
        """
        Test 17: status='completed' → no warning logged about incomplete/truncation.
        """
        from mcp.types import CallToolResult, TextContent

        responses = iter([
            _make_message_response("all good", response_id="r1"),
        ])

        def create_response_side_effect(**kwargs):
            return next(responses)

        agent = _make_agent(MagicMock(side_effect=create_response_side_effect))
        session = self._mock_session()

        logged_messages = []

        with patch(
            "tools.dynamic_autonomous.log_error",
            side_effect=lambda msg: logged_messages.append(msg),
        ):
            _run_loop(
                agent._autonomous_loop(
                    dispatcher=_SingleSessionDispatcher(session),
                    openai_tools=[],
                    task="test task",
                    max_rounds=10,
                    max_tokens=1024,
                )
            )

        # No log_error about 'incomplete' for a completed response
        incomplete_logged = any(
            "incomplete" in m.lower() or "max_output_tokens" in m.lower()
            for m in logged_messages
        )
        self.assertFalse(
            incomplete_logged,
            f"No 'incomplete' warning expected for completed response. Got: {logged_messages}",
        )


# ---------------------------------------------------------------------------
# Test 18: Reasoning output is logged, not dropped
# ---------------------------------------------------------------------------


class TestReasoningOutputLogged(unittest.TestCase):

    def _mock_session(self):
        session = MagicMock()
        session.call_tool = AsyncMock()
        return session

    def test_reasoning_output_logged_not_dropped(self):
        """
        Test 18: type='reasoning' items must trigger a log_info call
        (i.e., the text is not silently skipped).
        """
        from mcp.types import CallToolResult, TextContent

        success_result = CallToolResult(
            content=[TextContent(type="text", text="result")]
        )

        responses = iter([
            _make_reasoning_response(
                reasoning_text="I need to call read_file first",
                tool_name="read_file",
                response_id="r_reason",
            ),
            _make_message_response("final answer", response_id="r_final"),
        ])

        def create_response_side_effect(**kwargs):
            return next(responses)

        agent = _make_agent(MagicMock(side_effect=create_response_side_effect))
        session = self._mock_session()

        logged_info_messages = []

        async def fake_safe_call_tool(session_, name, args):
            return success_result

        with patch(
            "tools.dynamic_autonomous.safe_call_tool",
            side_effect=fake_safe_call_tool,
        ):
            with patch(
                "tools.dynamic_autonomous.log_info",
                side_effect=lambda msg: logged_info_messages.append(msg),
            ):
                _run_loop(
                    agent._autonomous_loop(
                        dispatcher=_SingleSessionDispatcher(session),
                        openai_tools=[],
                        task="test task",
                        max_rounds=10,
                        max_tokens=1024,
                    )
                )

        # At least one log_info call must mention 'reasoning'
        reasoning_logged = any(
            "reasoning" in m.lower() for m in logged_info_messages
        )
        self.assertTrue(
            reasoning_logged,
            f"Expected 'reasoning' in logged info messages. Got: {logged_info_messages}",
        )


# ---------------------------------------------------------------------------
# Test 19: _build_input_text with pending tool results
# ---------------------------------------------------------------------------


class TestBuildInputText(unittest.TestCase):

    def setUp(self):
        from tools.dynamic_autonomous import DynamicAutonomousAgent
        self.build = DynamicAutonomousAgent._build_input_text

    def test_build_input_text_with_pending_results(self):
        """
        Test 19: When round_num > 0 and pending_tool_results is non-empty,
        the output text must include each tool name and its result.
        """
        pending = [
            ("read_file", "hello world file content"),
            ("list_dir", "[file1.txt, file2.txt]"),
        ]

        text = self.build(
            round_num=1,
            task="original task",
            pending_tool_results=pending,
            consecutive_error_count=0,
        )

        self.assertIn("read_file", text)
        self.assertIn("hello world file content", text)
        self.assertIn("list_dir", text)
        self.assertIn("[file1.txt, file2.txt]", text)

    def test_build_input_text_round_zero_returns_task(self):
        """Additional sanity: round 0 must return the raw task string."""
        task = "My special task"
        text = self.build(
            round_num=0,
            task=task,
            pending_tool_results=[("tool", "result")],
            consecutive_error_count=0,
        )
        self.assertEqual(text, task)

    def test_build_input_text_no_pending_results_returns_continue(self):
        """round > 0 with empty pending_tool_results returns 'Continue...' text."""
        text = self.build(
            round_num=2,
            task="task",
            pending_tool_results=[],
            consecutive_error_count=0,
        )
        self.assertIn("continue", text.lower())


if __name__ == "__main__":
    unittest.main()
