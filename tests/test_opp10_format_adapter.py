"""Tests for OPP-10: Format Adapter — 3-way API format routing."""

import json

import pytest

from config.constants import (
    FORMAT_ANTHROPIC,
    FORMAT_OPENAI,
    FORMAT_RESPONSES,
    SUPPORTED_API_FORMATS,
)
from llm.format_adapter import APIFormat, FormatAdapter
from llm.llm_client import LLMClient

# ==============================================================================
# Group 1: APIFormat enum
# ==============================================================================


class TestAPIFormatEnum:
    """APIFormat enum has correct values."""

    def test_has_openai_value(self):
        assert APIFormat.OPENAI == "openai"

    def test_has_anthropic_value(self):
        assert APIFormat.ANTHROPIC == "anthropic"

    def test_has_responses_value(self):
        assert APIFormat.RESPONSES == "responses"

    def test_values_match_constants(self):
        assert APIFormat.OPENAI == FORMAT_OPENAI
        assert APIFormat.ANTHROPIC == FORMAT_ANTHROPIC
        assert APIFormat.RESPONSES == FORMAT_RESPONSES

    def test_string_comparison(self):
        """APIFormat.OPENAI == 'openai' (str subclass)."""
        assert APIFormat.OPENAI == "openai"
        assert APIFormat.ANTHROPIC == "anthropic"
        assert APIFormat.RESPONSES == "responses"


# ==============================================================================
# Group 2: Tool conversion — OpenAI → Responses
# ==============================================================================


class TestOpenAIToolsToResponses:
    """openai_tools_to_responses() flattens nested function structure."""

    def test_single_tool_happy_path(self):
        """Nested function tool flattened to top-level."""
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ]
        result = FormatAdapter.openai_tools_to_responses(tools)
        assert len(result) == 1
        assert result[0]["type"] == "function"
        assert result[0]["name"] == "get_weather"
        assert result[0]["description"] == "Get weather"
        assert "function" not in result[0]

    def test_multiple_tools_preserved_in_order(self):
        tools = [
            {"type": "function", "function": {"name": "tool_a", "description": "A"}},
            {"type": "function", "function": {"name": "tool_b", "description": "B"}},
        ]
        result = FormatAdapter.openai_tools_to_responses(tools)
        assert len(result) == 2
        assert result[0]["name"] == "tool_a"
        assert result[1]["name"] == "tool_b"

    def test_already_flat_tool_unchanged(self):
        """Tool without nested 'function' key passed through as-is."""
        flat_tool = {"type": "function", "name": "already_flat", "description": "X"}
        result = FormatAdapter.openai_tools_to_responses([flat_tool])
        assert len(result) == 1
        assert result[0]["name"] == "already_flat"

    def test_empty_list_returns_empty(self):
        result = FormatAdapter.openai_tools_to_responses([])
        assert result == []


# ==============================================================================
# Group 3: Tool conversion — OpenAI → Anthropic
# ==============================================================================


class TestOpenAIToolsToAnthropic:
    """openai_tools_to_anthropic() renames parameters → input_schema."""

    def test_single_tool_happy_path(self):
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather for a city",
                    "parameters": {
                        "type": "object",
                        "properties": {"city": {"type": "string"}},
                        "required": ["city"],
                    },
                },
            }
        ]
        result = FormatAdapter.openai_tools_to_anthropic(tools)
        assert len(result) == 1
        assert result[0]["name"] == "get_weather"
        assert result[0]["description"] == "Get weather for a city"
        assert "input_schema" in result[0]
        assert result[0]["input_schema"]["properties"]["city"]["type"] == "string"
        assert "type" not in result[0]
        assert "function" not in result[0]

    def test_missing_description_defaults_to_empty_string(self):
        tools = [
            {"type": "function", "function": {"name": "ping", "parameters": {}}}
        ]
        result = FormatAdapter.openai_tools_to_anthropic(tools)
        assert result[0]["description"] == ""

    def test_multiple_tools_preserved_in_order(self):
        tools = [
            {
                "type": "function",
                "function": {"name": "tool_a", "description": "A", "parameters": {}},
            },
            {
                "type": "function",
                "function": {"name": "tool_b", "description": "B", "parameters": {}},
            },
        ]
        result = FormatAdapter.openai_tools_to_anthropic(tools)
        assert len(result) == 2
        assert result[0]["name"] == "tool_a"
        assert result[1]["name"] == "tool_b"

    def test_empty_list_returns_empty(self):
        result = FormatAdapter.openai_tools_to_anthropic([])
        assert result == []


# ==============================================================================
# Group 4: Tool conversion — Anthropic → OpenAI (NEW)
# ==============================================================================


class TestAnthropicToolsToOpenAI:
    """anthropic_tools_to_openai() wraps with type=function, renames input_schema→parameters."""

    def test_single_tool_happy_path(self):
        tools = [
            {
                "name": "get_weather",
                "description": "Get weather for a city",
                "input_schema": {
                    "type": "object",
                    "properties": {"city": {"type": "string"}},
                    "required": ["city"],
                },
            }
        ]
        result = FormatAdapter.anthropic_tools_to_openai(tools)
        assert len(result) == 1
        assert result[0]["type"] == "function"
        assert "function" in result[0]
        func = result[0]["function"]
        assert func["name"] == "get_weather"
        assert func["description"] == "Get weather for a city"
        assert "parameters" in func
        assert func["parameters"]["properties"]["city"]["type"] == "string"
        assert "input_schema" not in func

    def test_tool_without_input_schema(self):
        """Tool without input_schema → no parameters key in function."""
        tools = [{"name": "ping", "description": "Ping the server"}]
        result = FormatAdapter.anthropic_tools_to_openai(tools)
        assert result[0]["type"] == "function"
        func = result[0]["function"]
        assert func["name"] == "ping"
        assert "parameters" not in func

    def test_multiple_tools(self):
        tools = [
            {"name": "tool_a", "description": "A", "input_schema": {}},
            {"name": "tool_b", "description": "B", "input_schema": {}},
        ]
        result = FormatAdapter.anthropic_tools_to_openai(tools)
        assert len(result) == 2
        assert result[0]["function"]["name"] == "tool_a"
        assert result[1]["function"]["name"] == "tool_b"

    def test_empty_list(self):
        result = FormatAdapter.anthropic_tools_to_openai([])
        assert result == []


# ==============================================================================
# Group 5: Tool conversion — Responses → OpenAI (NEW)
# ==============================================================================


class TestResponsesToolsToOpenAI:
    """responses_tools_to_openai() re-wraps flat tool into nested function structure."""

    def test_single_tool_happy_path(self):
        tools = [
            {
                "type": "function",
                "name": "get_weather",
                "description": "Get weather",
                "parameters": {"type": "object", "properties": {}},
            }
        ]
        result = FormatAdapter.responses_tools_to_openai(tools)
        assert len(result) == 1
        assert result[0]["type"] == "function"
        assert "function" in result[0]
        func = result[0]["function"]
        assert func["name"] == "get_weather"
        assert func["description"] == "Get weather"

    def test_multiple_tools(self):
        tools = [
            {"type": "function", "name": "tool_a", "description": "A"},
            {"type": "function", "name": "tool_b", "description": "B"},
        ]
        result = FormatAdapter.responses_tools_to_openai(tools)
        assert len(result) == 2
        assert result[0]["function"]["name"] == "tool_a"
        assert result[1]["function"]["name"] == "tool_b"

    def test_empty_list(self):
        result = FormatAdapter.responses_tools_to_openai([])
        assert result == []


# ==============================================================================
# Group 6: Tool conversion — Cross-chain
# ==============================================================================


class TestCrossChainToolConversion:
    """anthropic→responses and responses→anthropic chain correctly."""

    def test_anthropic_to_responses_chains(self):
        """anthropic→openai→responses produces correct flat structure."""
        tools = [
            {
                "name": "get_weather",
                "description": "Get weather",
                "input_schema": {
                    "type": "object",
                    "properties": {"city": {"type": "string"}},
                },
            }
        ]
        result = FormatAdapter.anthropic_tools_to_responses(tools)
        assert len(result) == 1
        assert result[0]["type"] == "function"
        assert result[0]["name"] == "get_weather"
        # Must be flat (no nested "function" key)
        assert "function" not in result[0]
        assert result[0]["description"] == "Get weather"

    def test_responses_to_anthropic_chains(self):
        """responses→openai→anthropic produces correct Anthropic structure."""
        tools = [
            {
                "type": "function",
                "name": "get_weather",
                "description": "Get weather",
                "parameters": {
                    "type": "object",
                    "properties": {"city": {"type": "string"}},
                },
            }
        ]
        result = FormatAdapter.responses_tools_to_anthropic(tools)
        assert len(result) == 1
        assert result[0]["name"] == "get_weather"
        assert "input_schema" in result[0]
        assert "type" not in result[0]
        assert "function" not in result[0]


# ==============================================================================
# Group 7: adapt_tools master router
# ==============================================================================


class TestAdaptToolsMasterRouter:
    """adapt_tools() dispatches to the correct conversion."""

    _sample_openai = [
        {
            "type": "function",
            "function": {"name": "t", "description": "d", "parameters": {}},
        }
    ]

    def test_same_format_returns_unchanged(self):
        result = FormatAdapter.adapt_tools(
            self._sample_openai, APIFormat.OPENAI, APIFormat.OPENAI
        )
        assert result == self._sample_openai

    def test_openai_to_anthropic(self):
        result = FormatAdapter.adapt_tools(
            self._sample_openai, APIFormat.OPENAI, APIFormat.ANTHROPIC
        )
        assert result[0]["name"] == "t"
        assert "input_schema" in result[0]

    def test_openai_to_responses(self):
        result = FormatAdapter.adapt_tools(
            self._sample_openai, APIFormat.OPENAI, APIFormat.RESPONSES
        )
        assert result[0]["name"] == "t"
        assert "function" not in result[0]

    def test_anthropic_to_openai(self):
        anthropic_tools = [
            {"name": "t", "description": "d", "input_schema": {}}
        ]
        result = FormatAdapter.adapt_tools(
            anthropic_tools, APIFormat.ANTHROPIC, APIFormat.OPENAI
        )
        assert result[0]["type"] == "function"
        assert result[0]["function"]["name"] == "t"

    def test_responses_to_openai(self):
        responses_tools = [
            {"type": "function", "name": "t", "description": "d"}
        ]
        result = FormatAdapter.adapt_tools(
            responses_tools, APIFormat.RESPONSES, APIFormat.OPENAI
        )
        assert result[0]["type"] == "function"
        assert result[0]["function"]["name"] == "t"

    def test_invalid_format_raises_value_error(self):
        with pytest.raises(ValueError):
            FormatAdapter.adapt_tools(
                self._sample_openai,
                "unknown_format",  # type: ignore[arg-type]
                APIFormat.OPENAI,
            )

    def test_same_format_anthropic_returns_unchanged(self):
        tools = [{"name": "t", "description": "d"}]
        result = FormatAdapter.adapt_tools(
            tools, APIFormat.ANTHROPIC, APIFormat.ANTHROPIC
        )
        assert result == tools


# ==============================================================================
# Group 8: Message conversion — OpenAI → Anthropic
# ==============================================================================


class TestOpenAIMessagesToAnthropic:
    """openai_messages_to_anthropic() extracts system prompt from messages."""

    def test_extracts_system_message(self):
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hello"},
        ]
        filtered, system = FormatAdapter.openai_messages_to_anthropic(messages)
        assert system == "You are helpful."
        assert len(filtered) == 1
        assert filtered[0]["role"] == "user"

    def test_filters_system_messages_from_array(self):
        messages = [
            {"role": "system", "content": "Be concise."},
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello!"},
        ]
        filtered, system = FormatAdapter.openai_messages_to_anthropic(messages)
        assert all(m["role"] != "system" for m in filtered)
        assert len(filtered) == 2

    def test_no_system_message_returns_empty_string(self):
        messages = [{"role": "user", "content": "Hi"}]
        filtered, system = FormatAdapter.openai_messages_to_anthropic(messages)
        assert system == ""
        assert len(filtered) == 1

    def test_multiple_system_messages_concatenated(self):
        messages = [
            {"role": "system", "content": "Part 1."},
            {"role": "system", "content": "Part 2."},
            {"role": "user", "content": "Hi"},
        ]
        filtered, system = FormatAdapter.openai_messages_to_anthropic(messages)
        assert "Part 1." in system
        assert "Part 2." in system

    def test_empty_messages_returns_empty_list_and_string(self):
        filtered, system = FormatAdapter.openai_messages_to_anthropic([])
        assert filtered == []
        assert system == ""


# ==============================================================================
# Group 9: Message conversion — Anthropic → OpenAI
# ==============================================================================


class TestAnthropicMessagesToOpenAI:
    """anthropic_messages_to_openai() prepends system message."""

    def test_prepends_system_message(self):
        messages = [{"role": "user", "content": "Hello"}]
        result = FormatAdapter.anthropic_messages_to_openai(messages, system="Be helpful.")
        assert result[0]["role"] == "system"
        assert result[0]["content"] == "Be helpful."
        assert result[1]["role"] == "user"

    def test_empty_system_no_system_message_added(self):
        messages = [{"role": "user", "content": "Hello"}]
        result = FormatAdapter.anthropic_messages_to_openai(messages, system="")
        assert len(result) == 1
        assert result[0]["role"] == "user"

    def test_empty_messages_with_system(self):
        result = FormatAdapter.anthropic_messages_to_openai([], system="Be helpful.")
        assert len(result) == 1
        assert result[0]["role"] == "system"
        assert result[0]["content"] == "Be helpful."


# ==============================================================================
# Group 10: Response parsing — extract_anthropic_tool_calls
# ==============================================================================


class TestExtractAnthropicToolCalls:
    """FormatAdapter.extract_anthropic_tool_calls() extracts tool_use blocks."""

    def test_extracts_tool_use_blocks(self):
        response = {
            "content": [
                {
                    "type": "tool_use",
                    "id": "toolu_1",
                    "name": "calc",
                    "input": {"expr": "2+2"},
                }
            ]
        }
        result = FormatAdapter.extract_anthropic_tool_calls(response)
        assert len(result) == 1
        assert result[0]["id"] == "toolu_1"
        assert result[0]["name"] == "calc"
        assert result[0]["input"] == {"expr": "2+2"}

    def test_no_tool_use_blocks_returns_empty(self):
        response = {"content": [{"type": "text", "text": "Hello"}]}
        result = FormatAdapter.extract_anthropic_tool_calls(response)
        assert result == []

    def test_empty_content_returns_empty(self):
        response = {"content": []}
        result = FormatAdapter.extract_anthropic_tool_calls(response)
        assert result == []


# ==============================================================================
# Group 11: Response parsing — build_anthropic_tool_result
# ==============================================================================


class TestBuildAnthropicToolResult:
    """FormatAdapter.build_anthropic_tool_result() builds correct structure."""

    def test_builds_correct_structure(self):
        result = FormatAdapter.build_anthropic_tool_result("toolu_1", "42")
        assert result["role"] == "user"
        blocks = result["content"]
        assert len(blocks) == 1
        assert blocks[0]["type"] == "tool_result"
        assert blocks[0]["tool_use_id"] == "toolu_1"
        assert blocks[0]["content"] == "42"

    def test_none_content_becomes_empty_string(self):
        result = FormatAdapter.build_anthropic_tool_result("toolu_1", None)
        blocks = result["content"]
        assert blocks[0]["content"] == ""

    def test_dict_content_json_serialized(self):
        result = FormatAdapter.build_anthropic_tool_result("toolu_1", {"answer": 42})
        blocks = result["content"]
        content = blocks[0]["content"]
        assert isinstance(content, str)
        parsed = json.loads(content)
        assert parsed["answer"] == 42

    def test_is_error_flag_included_when_true(self):
        result = FormatAdapter.build_anthropic_tool_result(
            "toolu_1", "error msg", is_error=True
        )
        blocks = result["content"]
        assert blocks[0]["is_error"] is True

    def test_is_error_flag_absent_when_false(self):
        result = FormatAdapter.build_anthropic_tool_result("toolu_1", "ok")
        blocks = result["content"]
        assert "is_error" not in blocks[0]


# ==============================================================================
# Group 12: Response conversion — openai_response_to_anthropic
# ==============================================================================


class TestOpenAIResponseToAnthropic:
    """openai_response_to_anthropic() converts chat completion to Anthropic format."""

    def test_converts_text_response(self):
        response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Hello there!",
                        "tool_calls": None,
                    },
                    "finish_reason": "stop",
                }
            ]
        }
        result = FormatAdapter.openai_response_to_anthropic(response)
        assert "content" in result
        assert any(
            b.get("type") == "text" and b.get("text") == "Hello there!"
            for b in result["content"]
        )

    def test_handles_tool_calls_in_response(self):
        response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {
                                    "name": "calc",
                                    "arguments": '{"expr": "2+2"}',
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ]
        }
        result = FormatAdapter.openai_response_to_anthropic(response)
        assert "content" in result
        tool_use_blocks = [b for b in result["content"] if b.get("type") == "tool_use"]
        assert len(tool_use_blocks) == 1
        assert tool_use_blocks[0]["name"] == "calc"
        assert tool_use_blocks[0]["id"] == "call_1"

    def test_empty_response_graceful_handling(self):
        result = FormatAdapter.openai_response_to_anthropic({})
        assert "content" in result


# ==============================================================================
# Group 13: Response conversion — anthropic_response_to_openai
# ==============================================================================


class TestAnthropicResponseToOpenAI:
    """anthropic_response_to_openai() converts Anthropic response to OpenAI format."""

    def test_converts_text_content_blocks(self):
        response = {
            "content": [{"type": "text", "text": "Hello!"}],
            "stop_reason": "end_turn",
        }
        result = FormatAdapter.anthropic_response_to_openai(response)
        assert "choices" in result
        assert len(result["choices"]) == 1
        msg = result["choices"][0]["message"]
        assert msg["role"] == "assistant"
        assert "Hello!" in msg["content"]

    def test_handles_tool_use_content_blocks(self):
        response = {
            "content": [
                {
                    "type": "tool_use",
                    "id": "toolu_1",
                    "name": "calc",
                    "input": {"expr": "2+2"},
                }
            ],
            "stop_reason": "tool_use",
        }
        result = FormatAdapter.anthropic_response_to_openai(response)
        assert "choices" in result
        msg = result["choices"][0]["message"]
        assert msg.get("tool_calls") is not None
        assert len(msg["tool_calls"]) == 1
        assert msg["tool_calls"][0]["function"]["name"] == "calc"

    def test_empty_response_graceful_handling(self):
        result = FormatAdapter.anthropic_response_to_openai({})
        assert "choices" in result


# ==============================================================================
# Group 14: Backward compatibility
# ==============================================================================


class TestBackwardCompatibility:
    """LLMClient static methods still work via delegation to FormatAdapter."""

    def test_convert_tools_to_responses_format(self):
        tools = [
            {
                "type": "function",
                "function": {"name": "t", "description": "d", "parameters": {}},
            }
        ]
        result = LLMClient.convert_tools_to_responses_format(tools)
        assert result[0]["name"] == "t"
        assert "function" not in result[0]

    def test_convert_tools_to_anthropic_format(self):
        tools = [
            {
                "type": "function",
                "function": {"name": "t", "description": "d", "parameters": {}},
            }
        ]
        result = LLMClient.convert_tools_to_anthropic_format(tools)
        assert result[0]["name"] == "t"
        assert "input_schema" in result[0]

    def test_extract_anthropic_tool_calls(self):
        response = {
            "content": [
                {"type": "tool_use", "id": "toolu_1", "name": "calc", "input": {}}
            ]
        }
        result = LLMClient.extract_anthropic_tool_calls(response)
        assert len(result) == 1
        assert result[0]["id"] == "toolu_1"

    def test_build_anthropic_tool_result(self):
        result = LLMClient.build_anthropic_tool_result("toolu_1", "42")
        assert result["role"] == "user"
        assert result["content"][0]["content"] == "42"


# ==============================================================================
# Group 15: Constants validation
# ==============================================================================


class TestConstantsValidation:
    """Constants in config.constants are correct."""

    def test_format_openai_is_string(self):
        assert isinstance(FORMAT_OPENAI, str)

    def test_format_anthropic_is_string(self):
        assert isinstance(FORMAT_ANTHROPIC, str)

    def test_format_responses_is_string(self):
        assert isinstance(FORMAT_RESPONSES, str)

    def test_supported_api_formats_contains_all_three(self):
        assert FORMAT_OPENAI in SUPPORTED_API_FORMATS
        assert FORMAT_ANTHROPIC in SUPPORTED_API_FORMATS
        assert FORMAT_RESPONSES in SUPPORTED_API_FORMATS

    def test_constants_match_enum_values(self):
        assert FORMAT_OPENAI == APIFormat.OPENAI
        assert FORMAT_ANTHROPIC == APIFormat.ANTHROPIC
        assert FORMAT_RESPONSES == APIFormat.RESPONSES


# ==============================================================================
# Group 16: Coverage gap — passthrough for non-function tools
# ==============================================================================


class TestToolPassthrough:
    """Tools without type='function' are passed through unchanged."""

    def test_openai_to_anthropic_passthrough_non_function_tool(self):
        tools = [{"type": "custom", "name": "special"}]
        result = FormatAdapter.openai_tools_to_anthropic(tools)
        assert result == [{"type": "custom", "name": "special"}]

    def test_responses_to_openai_passthrough_non_function_tool(self):
        tools = [{"type": "custom", "name": "special"}]
        result = FormatAdapter.responses_tools_to_openai(tools)
        assert result == [{"type": "custom", "name": "special"}]


# ==============================================================================
# Group 17: Coverage gap — adapt_messages
# ==============================================================================


class TestAdaptMessages:
    """Test the adapt_messages master router."""

    def test_same_format_returns_unchanged(self):
        msgs = [{"role": "user", "content": "Hi"}]
        result = FormatAdapter.adapt_messages(msgs, "openai", "openai")
        assert result is msgs

    def test_openai_to_anthropic_messages(self):
        msgs = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hello"},
        ]
        filtered, system = FormatAdapter.adapt_messages(msgs, "openai", "anthropic")
        assert system == "You are helpful."
        assert len(filtered) == 1
        assert filtered[0]["role"] == "user"

    def test_anthropic_to_openai_messages(self):
        msgs = [{"role": "user", "content": "Hello"}]
        result = FormatAdapter.adapt_messages(
            msgs, "anthropic", "openai", system="Be nice"
        )
        assert result[0]["role"] == "system"
        assert result[0]["content"] == "Be nice"

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError, match="Unsupported format"):
            FormatAdapter.adapt_messages([], "invalid", "openai")

    def test_unimplemented_pair_raises(self):
        with pytest.raises(ValueError, match="not implemented"):
            FormatAdapter.adapt_messages([], "openai", "responses")


# ==============================================================================
# Group 18: Coverage gap — response conversion error paths
# ==============================================================================


class TestResponseConversionErrors:
    """Test error paths in response conversion methods."""

    def test_openai_to_anthropic_malformed_json_arguments(self):
        response = {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "tool_calls": [{
                        "id": "tc1",
                        "function": {
                            "name": "test",
                            "arguments": "not-valid-json{{"
                        }
                    }]
                },
                "finish_reason": "tool_calls"
            }]
        }
        result = FormatAdapter.openai_response_to_anthropic(response)
        tool_use = [b for b in result["content"] if b["type"] == "tool_use"]
        assert len(tool_use) == 1
        assert tool_use[0]["input"] == {}  # fallback for bad JSON

    def test_openai_to_anthropic_missing_choices_key(self):
        response = {}
        result = FormatAdapter.openai_response_to_anthropic(response)
        assert "content" in result

    def test_anthropic_to_openai_missing_content_key(self):
        response = {}
        result = FormatAdapter.anthropic_response_to_openai(response)
        assert "choices" in result

    def test_anthropic_to_openai_type_error_in_content(self):
        response = {"content": None}
        result = FormatAdapter.anthropic_response_to_openai(response)
        assert "choices" in result
