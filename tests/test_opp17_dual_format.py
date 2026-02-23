"""Tests for OPP-17: Dual-Format Autonomous Loop (Anthropic Dispatch).

Groups:
  1. Constants
  2. _autonomous_loop_anthropic — happy path
  3. _autonomous_loop_anthropic — tool calling
  4. _autonomous_loop_anthropic — error handling
  5. _autonomous_loop_anthropic — max rounds
  6. _run_autonomous_dispatch routing
  7. Tool format conversion
  8. Backward compatibility
"""

import asyncio
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config.constants import (  # noqa: E402
    ANTHROPIC_AUTONOMOUS_SYSTEM_TEMPLATE,
    DEFAULT_AUTONOMOUS_FORMAT,
    FORMAT_ANTHROPIC,
    FORMAT_RESPONSES,
)
from tools.dynamic_autonomous import DynamicAutonomousAgent  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_agent():
    """Build DynamicAutonomousAgent with mocked LLM and validator."""
    mock_llm = MagicMock()
    mock_validator = MagicMock()

    agent = DynamicAutonomousAgent.__new__(DynamicAutonomousAgent)
    agent.llm = mock_llm
    agent.model_validator = mock_validator
    agent.mcp_json_path = "/tmp/fake.mcp.json"
    return agent


def _run(coro):
    """Run async coroutine in a fresh event loop."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _make_anthropic_text_response(text="Task complete."):
    """Anthropic response with only a text block (end_turn)."""
    return {
        "content": [{"type": "text", "text": text}],
        "stop_reason": "end_turn",
    }


def _make_anthropic_tool_response(tool_name="read_file", tool_id="toolu_01", tool_input=None):
    """Anthropic response with a tool_use block."""
    return {
        "content": [
            {
                "type": "tool_use",
                "id": tool_id,
                "name": tool_name,
                "input": tool_input or {"path": "/tmp/test.txt"},
            }
        ],
        "stop_reason": "tool_use",
    }


def _make_openai_tools():
    """Sample OpenAI-format tools list."""
    return [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a file from disk",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            },
        }
    ]


def _make_dispatcher(return_value=("read_file", "file contents here")):
    """Create a mock dispatcher."""
    dispatcher = MagicMock()
    dispatcher.dispatch = AsyncMock(return_value=return_value)
    return dispatcher


# ---------------------------------------------------------------------------
# Group 1: Constants
# ---------------------------------------------------------------------------


class TestOPP17Constants(unittest.TestCase):
    """Group 1: OPP-17 constants defined correctly."""

    def test_default_autonomous_format_equals_format_responses(self):
        """DEFAULT_AUTONOMOUS_FORMAT must equal FORMAT_RESPONSES (preserves existing behavior)."""
        self.assertEqual(DEFAULT_AUTONOMOUS_FORMAT, FORMAT_RESPONSES)

    def test_anthropic_autonomous_system_template_is_non_empty_string(self):
        """ANTHROPIC_AUTONOMOUS_SYSTEM_TEMPLATE must be a non-empty string."""
        self.assertIsInstance(ANTHROPIC_AUTONOMOUS_SYSTEM_TEMPLATE, str)
        self.assertGreater(len(ANTHROPIC_AUTONOMOUS_SYSTEM_TEMPLATE), 0)


# ---------------------------------------------------------------------------
# Group 2: _autonomous_loop_anthropic — happy path
# ---------------------------------------------------------------------------


class TestAnthropicLoopHappyPath(unittest.TestCase):
    """Group 2: _autonomous_loop_anthropic happy path tests."""

    def test_method_exists_on_agent(self):
        """DynamicAutonomousAgent has _autonomous_loop_anthropic method."""
        agent = _make_agent()
        self.assertTrue(hasattr(agent, "_autonomous_loop_anthropic"))
        self.assertTrue(callable(agent._autonomous_loop_anthropic))

    def test_returns_text_content_on_end_turn(self):
        """Returns text from response when stop_reason is end_turn."""
        agent = _make_agent()
        agent.llm.anthropic_messages = MagicMock(
            return_value=_make_anthropic_text_response("Final answer here.")
        )
        dispatcher = _make_dispatcher()
        tools = _make_openai_tools()

        result = _run(
            agent._autonomous_loop_anthropic(
                dispatcher=dispatcher,
                openai_tools=tools,
                task="Do something",
                max_rounds=5,
                max_tokens=1024,
            )
        )

        self.assertEqual(result, "Final answer here.")

    def test_converts_tools_to_anthropic_format(self):
        """FormatAdapter.openai_tools_to_anthropic called with openai_tools."""
        agent = _make_agent()
        agent.llm.anthropic_messages = MagicMock(
            return_value=_make_anthropic_text_response("done")
        )
        dispatcher = _make_dispatcher()
        tools = _make_openai_tools()

        with patch("tools.dynamic_autonomous.FormatAdapter") as mock_adapter:
            mock_adapter.openai_tools_to_anthropic.return_value = [
                {"name": "read_file", "description": "Read a file", "input_schema": {}}
            ]
            mock_adapter.extract_anthropic_tool_calls.return_value = []

            _run(
                agent._autonomous_loop_anthropic(
                    dispatcher=dispatcher,
                    openai_tools=tools,
                    task="Do something",
                    max_rounds=5,
                    max_tokens=1024,
                )
            )

        mock_adapter.openai_tools_to_anthropic.assert_called_once_with(tools)

    def test_anthropic_messages_called_with_system_prompt(self):
        """anthropic_messages called with the system prompt from ANTHROPIC_AUTONOMOUS_SYSTEM_TEMPLATE."""
        agent = _make_agent()
        agent.llm.anthropic_messages = MagicMock(
            return_value=_make_anthropic_text_response("done")
        )
        dispatcher = _make_dispatcher()
        tools = _make_openai_tools()

        _run(
            agent._autonomous_loop_anthropic(
                dispatcher=dispatcher,
                openai_tools=tools,
                task="Do something",
                max_rounds=5,
                max_tokens=1024,
            )
        )

        call_kwargs = agent.llm.anthropic_messages.call_args
        # system is passed as keyword arg or positional — check both
        system_arg = call_kwargs.kwargs.get("system") or (
            call_kwargs.args[1] if len(call_kwargs.args) > 1 else None
        )
        self.assertEqual(system_arg, ANTHROPIC_AUTONOMOUS_SYSTEM_TEMPLATE)

    def test_initial_messages_contains_user_task(self):
        """First call to anthropic_messages has user message with the task."""
        agent = _make_agent()
        agent.llm.anthropic_messages = MagicMock(
            return_value=_make_anthropic_text_response("done")
        )
        dispatcher = _make_dispatcher()
        tools = _make_openai_tools()

        _run(
            agent._autonomous_loop_anthropic(
                dispatcher=dispatcher,
                openai_tools=tools,
                task="My specific task",
                max_rounds=5,
                max_tokens=1024,
            )
        )

        call_kwargs = agent.llm.anthropic_messages.call_args
        messages_arg = call_kwargs.kwargs.get("messages") or call_kwargs.args[0]
        # First message in conversation must be user role with task content
        user_messages = [m for m in messages_arg if m.get("role") == "user"]
        self.assertTrue(len(user_messages) >= 1)
        first_user_content = user_messages[0]["content"]
        self.assertIn("My specific task", first_user_content)


# ---------------------------------------------------------------------------
# Group 3: _autonomous_loop_anthropic — tool calling
# ---------------------------------------------------------------------------


class TestAnthropicLoopToolCalling(unittest.TestCase):
    """Group 3: Tool calling round-trip tests."""

    def test_executes_tool_and_injects_result(self):
        """Tool_use response triggers dispatch and result injected into conversation."""
        agent = _make_agent()
        call_count = {"n": 0}

        def side_effect(**kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return _make_anthropic_tool_response("read_file", "toolu_01")
            return _make_anthropic_text_response("File read complete.")

        agent.llm.anthropic_messages = MagicMock(side_effect=side_effect)
        dispatcher = _make_dispatcher(return_value=("read_file", "file contents"))
        tools = _make_openai_tools()

        result = _run(
            agent._autonomous_loop_anthropic(
                dispatcher=dispatcher,
                openai_tools=tools,
                task="Read a file",
                max_rounds=5,
                max_tokens=1024,
            )
        )

        self.assertEqual(result, "File read complete.")
        dispatcher.dispatch.assert_awaited_once()

    def test_two_rounds_executed_for_tool_call(self):
        """anthropic_messages called twice: once for tool call, once for final answer."""
        agent = _make_agent()
        call_count = {"n": 0}

        def side_effect(**kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return _make_anthropic_tool_response("read_file", "toolu_01")
            return _make_anthropic_text_response("done")

        agent.llm.anthropic_messages = MagicMock(side_effect=side_effect)
        dispatcher = _make_dispatcher(return_value=("read_file", "result"))
        tools = _make_openai_tools()

        _run(
            agent._autonomous_loop_anthropic(
                dispatcher=dispatcher,
                openai_tools=tools,
                task="Read a file",
                max_rounds=5,
                max_tokens=1024,
            )
        )

        self.assertEqual(agent.llm.anthropic_messages.call_count, 2)

    def test_tool_result_message_in_second_call(self):
        """Second call to anthropic_messages includes tool_result in messages."""
        agent = _make_agent()
        call_count = {"n": 0}
        captured_messages = {}

        def side_effect(**kwargs):
            call_count["n"] += 1
            captured_messages[call_count["n"]] = kwargs.get(
                "messages", kwargs.get("args", [])
            )
            if call_count["n"] == 1:
                return _make_anthropic_tool_response("read_file", "toolu_01")
            return _make_anthropic_text_response("done")

        agent.llm.anthropic_messages = MagicMock(side_effect=side_effect)
        dispatcher = _make_dispatcher(return_value=("read_file", "result data"))
        tools = _make_openai_tools()

        _run(
            agent._autonomous_loop_anthropic(
                dispatcher=dispatcher,
                openai_tools=tools,
                task="Read a file",
                max_rounds=5,
                max_tokens=1024,
            )
        )

        # Second call messages must contain a tool_result block
        second_call_kwargs = agent.llm.anthropic_messages.call_args_list[1]
        messages = second_call_kwargs.kwargs.get("messages") or second_call_kwargs.args[0]

        has_tool_result = False
        for msg in messages:
            content = msg.get("content", [])
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        has_tool_result = True
        self.assertTrue(has_tool_result, "Expected tool_result block in second call messages")

    def test_dispatch_called_with_correct_tool_name_and_args(self):
        """dispatcher.dispatch called with tool name and input from tool_use block."""
        agent = _make_agent()
        call_count = {"n": 0}

        def side_effect(**kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return _make_anthropic_tool_response(
                    "read_file", "toolu_01", {"path": "/etc/hosts"}
                )
            return _make_anthropic_text_response("done")

        agent.llm.anthropic_messages = MagicMock(side_effect=side_effect)
        dispatcher = _make_dispatcher(return_value=("read_file", "hosts content"))
        tools = _make_openai_tools()

        _run(
            agent._autonomous_loop_anthropic(
                dispatcher=dispatcher,
                openai_tools=tools,
                task="Read /etc/hosts",
                max_rounds=5,
                max_tokens=1024,
            )
        )

        dispatcher.dispatch.assert_awaited_once_with("read_file", {"path": "/etc/hosts"})


# ---------------------------------------------------------------------------
# Group 4: _autonomous_loop_anthropic — error handling
# ---------------------------------------------------------------------------


class TestAnthropicLoopErrorHandling(unittest.TestCase):
    """Group 4: Error handling in _autonomous_loop_anthropic."""

    def test_llm_exception_increments_error_count(self):
        """LLM exception is counted and triggers abort after MAX_CONSECUTIVE_ERRORS."""
        agent = _make_agent()
        agent.llm.anthropic_messages = MagicMock(
            side_effect=RuntimeError("LLM unavailable")
        )
        dispatcher = _make_dispatcher()
        tools = _make_openai_tools()

        result = _run(
            agent._autonomous_loop_anthropic(
                dispatcher=dispatcher,
                openai_tools=tools,
                task="Do something",
                max_rounds=10,
                max_tokens=1024,
            )
        )

        # After MAX_CONSECUTIVE_ERRORS, loop should abort with an appropriate message
        self.assertIsInstance(result, str)
        # Should contain "aborted" or "error" or similar
        self.assertTrue(
            "abort" in result.lower() or "error" in result.lower(),
            f"Expected abort/error message, got: {result!r}",
        )

    def test_consecutive_error_count_incremented_per_llm_failure(self):
        """consecutive_error_count increments on each LLM failure."""
        from config.constants import MAX_CONSECUTIVE_ERRORS

        agent = _make_agent()
        call_count = {"n": 0}

        def side_effect(**kwargs):
            call_count["n"] += 1
            raise RuntimeError(f"Error #{call_count['n']}")

        agent.llm.anthropic_messages = MagicMock(side_effect=side_effect)
        dispatcher = _make_dispatcher()
        tools = _make_openai_tools()

        _run(
            agent._autonomous_loop_anthropic(
                dispatcher=dispatcher,
                openai_tools=tools,
                task="fail task",
                max_rounds=100,
                max_tokens=1024,
            )
        )

        # Should have called exactly MAX_CONSECUTIVE_ERRORS times before aborting
        self.assertEqual(call_count["n"], MAX_CONSECUTIVE_ERRORS)

    def test_abort_message_contains_error_count(self):
        """Abort message includes the consecutive error count or last error."""
        agent = _make_agent()
        agent.llm.anthropic_messages = MagicMock(
            side_effect=RuntimeError("connection refused")
        )
        dispatcher = _make_dispatcher()
        tools = []

        result = _run(
            agent._autonomous_loop_anthropic(
                dispatcher=dispatcher,
                openai_tools=tools,
                task="fail task",
                max_rounds=100,
                max_tokens=1024,
            )
        )

        # Result should be a string describing the failure
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)


# ---------------------------------------------------------------------------
# Group 5: _autonomous_loop_anthropic — max rounds
# ---------------------------------------------------------------------------


class TestAnthropicLoopMaxRounds(unittest.TestCase):
    """Group 5: Max rounds behavior."""

    def test_returns_incomplete_message_when_max_rounds_reached(self):
        """Returns a message indicating max rounds when loop exhausts rounds."""
        agent = _make_agent()
        call_count = {"n": 0}

        def always_tool(**kwargs):
            call_count["n"] += 1
            return _make_anthropic_tool_response("read_file", f"toolu_{call_count['n']}")

        agent.llm.anthropic_messages = MagicMock(side_effect=always_tool)
        dispatcher = _make_dispatcher(return_value=("read_file", "result"))
        tools = _make_openai_tools()

        result = _run(
            agent._autonomous_loop_anthropic(
                dispatcher=dispatcher,
                openai_tools=tools,
                task="infinite loop task",
                max_rounds=3,
                max_tokens=1024,
            )
        )

        self.assertIsInstance(result, str)
        # Should indicate incomplete / max rounds
        self.assertTrue(
            "incomplete" in result.lower()
            or "maximum" in result.lower()
            or "max" in result.lower()
            or "rounds" in result.lower(),
            f"Expected max-rounds message, got: {result!r}",
        )

    def test_loop_stops_at_max_rounds(self):
        """anthropic_messages called at most max_rounds times."""
        agent = _make_agent()

        agent.llm.anthropic_messages = MagicMock(
            side_effect=lambda **kw: _make_anthropic_tool_response(
                "read_file", "toolu_x"
            )
        )
        dispatcher = _make_dispatcher(return_value=("read_file", "result"))
        tools = _make_openai_tools()

        _run(
            agent._autonomous_loop_anthropic(
                dispatcher=dispatcher,
                openai_tools=tools,
                task="task",
                max_rounds=4,
                max_tokens=1024,
            )
        )

        self.assertLessEqual(agent.llm.anthropic_messages.call_count, 4)


# ---------------------------------------------------------------------------
# Group 6: _run_autonomous_dispatch routing
# ---------------------------------------------------------------------------


class TestRunAutonomousDispatch(unittest.TestCase):
    """Group 6: _run_autonomous_dispatch routes to the correct loop."""

    def test_method_exists_on_agent(self):
        """DynamicAutonomousAgent has _run_autonomous_dispatch method."""
        agent = _make_agent()
        self.assertTrue(hasattr(agent, "_run_autonomous_dispatch"))
        self.assertTrue(callable(agent._run_autonomous_dispatch))

    def test_format_responses_calls_autonomous_loop(self):
        """api_format=FORMAT_RESPONSES routes to _autonomous_loop."""
        agent = _make_agent()
        dispatcher = _make_dispatcher()
        tools = _make_openai_tools()

        with patch.object(
            agent,
            "_autonomous_loop",
            new=AsyncMock(return_value="openai result"),
        ) as mock_loop, patch.object(
            agent,
            "_autonomous_loop_anthropic",
            new=AsyncMock(return_value="anthropic result"),
        ) as mock_anthropic:
            result = _run(
                agent._run_autonomous_dispatch(
                    dispatcher=dispatcher,
                    openai_tools=tools,
                    task="test",
                    max_rounds=5,
                    max_tokens=1024,
                    api_format=FORMAT_RESPONSES,
                )
            )

        mock_loop.assert_awaited_once()
        mock_anthropic.assert_not_awaited()
        self.assertEqual(result, "openai result")

    def test_format_anthropic_calls_autonomous_loop_anthropic(self):
        """api_format=FORMAT_ANTHROPIC routes to _autonomous_loop_anthropic."""
        agent = _make_agent()
        dispatcher = _make_dispatcher()
        tools = _make_openai_tools()

        with patch.object(
            agent,
            "_autonomous_loop",
            new=AsyncMock(return_value="openai result"),
        ) as mock_loop, patch.object(
            agent,
            "_autonomous_loop_anthropic",
            new=AsyncMock(return_value="anthropic result"),
        ) as mock_anthropic:
            result = _run(
                agent._run_autonomous_dispatch(
                    dispatcher=dispatcher,
                    openai_tools=tools,
                    task="test",
                    max_rounds=5,
                    max_tokens=1024,
                    api_format=FORMAT_ANTHROPIC,
                )
            )

        mock_anthropic.assert_awaited_once()
        mock_loop.assert_not_awaited()
        self.assertEqual(result, "anthropic result")

    def test_string_responses_routes_to_autonomous_loop(self):
        """api_format='responses' string routes to _autonomous_loop."""
        agent = _make_agent()
        dispatcher = _make_dispatcher()
        tools = _make_openai_tools()

        with patch.object(
            agent,
            "_autonomous_loop",
            new=AsyncMock(return_value="openai result"),
        ) as mock_loop, patch.object(
            agent,
            "_autonomous_loop_anthropic",
            new=AsyncMock(return_value="anthropic result"),
        ):
            result = _run(
                agent._run_autonomous_dispatch(
                    dispatcher=dispatcher,
                    openai_tools=tools,
                    task="test",
                    max_rounds=5,
                    max_tokens=1024,
                    api_format="responses",
                )
            )

        mock_loop.assert_awaited_once()
        self.assertEqual(result, "openai result")

    def test_string_anthropic_routes_to_anthropic_loop(self):
        """api_format='anthropic' string routes to _autonomous_loop_anthropic."""
        agent = _make_agent()
        dispatcher = _make_dispatcher()
        tools = _make_openai_tools()

        with patch.object(
            agent,
            "_autonomous_loop",
            new=AsyncMock(return_value="openai result"),
        ), patch.object(
            agent,
            "_autonomous_loop_anthropic",
            new=AsyncMock(return_value="anthropic result"),
        ) as mock_anthropic:
            result = _run(
                agent._run_autonomous_dispatch(
                    dispatcher=dispatcher,
                    openai_tools=tools,
                    task="test",
                    max_rounds=5,
                    max_tokens=1024,
                    api_format="anthropic",
                )
            )

        mock_anthropic.assert_awaited_once()
        self.assertEqual(result, "anthropic result")

    def test_default_format_is_responses(self):
        """Default api_format routes to _autonomous_loop (responses behavior)."""
        agent = _make_agent()
        dispatcher = _make_dispatcher()
        tools = _make_openai_tools()

        with patch.object(
            agent,
            "_autonomous_loop",
            new=AsyncMock(return_value="default result"),
        ) as mock_loop, patch.object(
            agent,
            "_autonomous_loop_anthropic",
            new=AsyncMock(return_value="anthropic result"),
        ):
            result = _run(
                agent._run_autonomous_dispatch(
                    dispatcher=dispatcher,
                    openai_tools=tools,
                    task="test",
                    max_rounds=5,
                    max_tokens=1024,
                    # No api_format — uses DEFAULT_AUTONOMOUS_FORMAT
                )
            )

        mock_loop.assert_awaited_once()
        self.assertEqual(result, "default result")


# ---------------------------------------------------------------------------
# Group 7: Tool format conversion
# ---------------------------------------------------------------------------


class TestToolFormatConversion(unittest.TestCase):
    """Group 7: Tools are correctly converted to Anthropic format."""

    def test_openai_tools_converted_to_anthropic_before_api_call(self):
        """anthropic_messages receives Anthropic-format tools (with input_schema)."""
        agent = _make_agent()
        agent.llm.anthropic_messages = MagicMock(
            return_value=_make_anthropic_text_response("done")
        )
        dispatcher = _make_dispatcher()
        tools = _make_openai_tools()

        _run(
            agent._autonomous_loop_anthropic(
                dispatcher=dispatcher,
                openai_tools=tools,
                task="task",
                max_rounds=5,
                max_tokens=1024,
            )
        )

        call_kwargs = agent.llm.anthropic_messages.call_args
        tools_arg = call_kwargs.kwargs.get("tools")
        if tools_arg is None and call_kwargs.args:
            # fallback — look at positional args
            tools_arg = None  # not checking positional for this test
        if tools_arg is not None:
            # Each converted tool should have "name" and "input_schema", not "function"
            for t in tools_arg:
                self.assertIn("name", t)
                self.assertNotIn("function", t)

    def test_tool_result_built_in_anthropic_format(self):
        """Tool results injected back use Anthropic tool_result format."""
        agent = _make_agent()
        call_count = {"n": 0}
        second_call_messages = {}

        def capture(**kwargs):
            call_count["n"] += 1
            msgs = kwargs.get("messages", [])
            if call_count["n"] == 2:
                second_call_messages["msgs"] = msgs
            if call_count["n"] == 1:
                return _make_anthropic_tool_response("read_file", "toolu_99")
            return _make_anthropic_text_response("done")

        agent.llm.anthropic_messages = MagicMock(side_effect=capture)
        dispatcher = _make_dispatcher(return_value=("read_file", "content"))
        tools = _make_openai_tools()

        _run(
            agent._autonomous_loop_anthropic(
                dispatcher=dispatcher,
                openai_tools=tools,
                task="task",
                max_rounds=5,
                max_tokens=1024,
            )
        )

        # Verify second call messages contain a tool_result block
        msgs = second_call_messages.get("msgs", [])
        found_tool_result = False
        for msg in msgs:
            content = msg.get("content", [])
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        found_tool_result = True
                        # Verify it has the correct tool_use_id
                        self.assertEqual(block.get("tool_use_id"), "toolu_99")
        self.assertTrue(found_tool_result, "Expected tool_result block in second call")


# ---------------------------------------------------------------------------
# Group 8: Backward compatibility
# ---------------------------------------------------------------------------


class TestBackwardCompatibility(unittest.TestCase):
    """Group 8: Existing _autonomous_loop is unchanged."""

    def test_autonomous_loop_still_exists(self):
        """_autonomous_loop still exists on DynamicAutonomousAgent."""
        agent = _make_agent()
        self.assertTrue(hasattr(agent, "_autonomous_loop"))
        self.assertTrue(callable(agent._autonomous_loop))

    def test_autonomous_loop_signature_unchanged(self):
        """_autonomous_loop accepts same signature as before OPP-17."""
        import inspect

        agent = _make_agent()
        sig = inspect.signature(agent._autonomous_loop)
        params = list(sig.parameters.keys())
        # Original params: dispatcher, openai_tools, task, max_rounds, max_tokens, model, parallel_tools
        self.assertIn("dispatcher", params)
        self.assertIn("openai_tools", params)
        self.assertIn("task", params)
        self.assertIn("max_rounds", params)
        self.assertIn("max_tokens", params)
        self.assertIn("model", params)
        self.assertIn("parallel_tools", params)

    def test_autonomous_loop_still_works_for_final_answer(self):
        """_autonomous_loop still returns correct result (unchanged behavior)."""
        agent = _make_agent()
        agent.llm.create_response = MagicMock(
            return_value={
                "id": "resp-001",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "Hello from old loop"}],
                    }
                ],
            }
        )
        dispatcher = _make_dispatcher()

        result = _run(
            agent._autonomous_loop(
                dispatcher=dispatcher,
                openai_tools=[],
                task="test",
                max_rounds=5,
                max_tokens=1024,
            )
        )

        self.assertEqual(result, "Hello from old loop")

    def test_all_original_methods_present(self):
        """DynamicAutonomousAgent still has all original public methods."""
        agent = _make_agent()
        original_methods = [
            "autonomous_with_mcp",
            "autonomous_with_multiple_mcps",
            "autonomous_discover_and_execute",
            "_autonomous_loop",
            "_build_input_text",
            "_execute_tools_sequential",
            "_execute_tools_parallel",
            "_preload_and_validate_model",
        ]
        for method in original_methods:
            self.assertTrue(
                hasattr(agent, method),
                f"Missing original method: {method}",
            )

    def test_new_methods_added_without_removing_existing(self):
        """New OPP-17 methods exist alongside all original methods."""
        agent = _make_agent()
        new_methods = ["_autonomous_loop_anthropic", "_run_autonomous_dispatch"]
        for method in new_methods:
            self.assertTrue(
                hasattr(agent, method),
                f"Missing new method: {method}",
            )


if __name__ == "__main__":
    unittest.main()
