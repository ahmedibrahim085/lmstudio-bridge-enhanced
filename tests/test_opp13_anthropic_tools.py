"""Tests for OPP-13: Anthropic tool format adapters."""

import json

from llm.llm_client import LLMClient


# --- Conversion: OpenAI -> Anthropic ---

class TestConvertToolsToAnthropicFormat:
    """Tests for convert_tools_to_anthropic_format()."""

    def test_convert_single_tool(self):
        """Basic OpenAI -> Anthropic conversion."""
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
        result = LLMClient.convert_tools_to_anthropic_format(tools)
        assert len(result) == 1
        assert result[0]["name"] == "get_weather"
        assert result[0]["description"] == "Get weather for a city"
        assert result[0]["input_schema"]["properties"]["city"]["type"] == "string"
        assert "type" not in result[0]  # No "type": "function" wrapper
        assert "function" not in result[0]

    def test_convert_multiple_tools(self):
        """List preserves order."""
        tools = [
            {"type": "function", "function": {"name": "tool_a", "description": "A", "parameters": {}}},
            {"type": "function", "function": {"name": "tool_b", "description": "B", "parameters": {}}},
        ]
        result = LLMClient.convert_tools_to_anthropic_format(tools)
        assert len(result) == 2
        assert result[0]["name"] == "tool_a"
        assert result[1]["name"] == "tool_b"

    def test_convert_preserves_schema(self):
        """Nested JSON schema unchanged."""
        schema = {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {"id": {"type": "integer"}},
                    },
                }
            },
        }
        tools = [{"type": "function", "function": {"name": "t", "description": "d", "parameters": schema}}]
        result = LLMClient.convert_tools_to_anthropic_format(tools)
        assert result[0]["input_schema"] == schema

    def test_convert_tool_no_parameters(self):
        """Tool without parameters field."""
        tools = [{"type": "function", "function": {"name": "ping", "description": "Ping"}}]
        result = LLMClient.convert_tools_to_anthropic_format(tools)
        assert result[0]["name"] == "ping"
        assert result[0].get("input_schema", {}) == {} or "input_schema" not in result[0]

    def test_convert_skips_non_function(self):
        """Non-function tools passed through as-is."""
        tools = [
            {"type": "function", "function": {"name": "t1", "description": "d1", "parameters": {}}},
            {"type": "other", "name": "t2"},
        ]
        result = LLMClient.convert_tools_to_anthropic_format(tools)
        assert len(result) == 2
        assert result[0]["name"] == "t1"
        # Non-function tool passed through
        assert result[1].get("type") == "other" or result[1].get("name") == "t2"

    def test_convert_schema_additional_properties_false(self):
        """Strict mode schema round-trips correctly."""
        schema = {
            "type": "object",
            "properties": {"x": {"type": "string"}},
            "required": ["x"],
            "additionalProperties": False,
        }
        tools = [{"type": "function", "function": {"name": "strict", "description": "S", "parameters": schema}}]
        result = LLMClient.convert_tools_to_anthropic_format(tools)
        assert result[0]["input_schema"]["additionalProperties"] is False


# --- Extraction: Anthropic response -> tool calls ---

class TestExtractAnthropicToolCalls:
    """Tests for extract_anthropic_tool_calls()."""

    def test_extract_text_only_response(self):
        """No tool calls returns empty list."""
        response = {
            "content": [{"type": "text", "text": "Hello"}],
            "stop_reason": "end_turn",
        }
        result = LLMClient.extract_anthropic_tool_calls(response)
        assert result == []

    def test_extract_single_tool_call(self):
        """One tool_use block extracted."""
        response = {
            "content": [
                {"type": "tool_use", "id": "toolu_1", "name": "calc", "input": {"expr": "2+2"}},
            ],
            "stop_reason": "tool_use",
        }
        result = LLMClient.extract_anthropic_tool_calls(response)
        assert len(result) == 1
        assert result[0]["id"] == "toolu_1"
        assert result[0]["name"] == "calc"
        assert result[0]["input"] == {"expr": "2+2"}

    def test_extract_multiple_tool_calls(self):
        """Multiple tool_use blocks extracted."""
        response = {
            "content": [
                {"type": "tool_use", "id": "toolu_1", "name": "a", "input": {}},
                {"type": "tool_use", "id": "toolu_2", "name": "b", "input": {}},
            ],
            "stop_reason": "tool_use",
        }
        result = LLMClient.extract_anthropic_tool_calls(response)
        assert len(result) == 2

    def test_extract_empty_content(self):
        """Empty content array returns empty list."""
        response = {"content": [], "stop_reason": "end_turn"}
        result = LLMClient.extract_anthropic_tool_calls(response)
        assert result == []

    def test_extract_mixed_text_and_tool_use(self):
        """content=[text_block, tool_use_block] -> only tool_use extracted."""
        response = {
            "content": [
                {"type": "text", "text": "Let me calculate..."},
                {"type": "tool_use", "id": "toolu_1", "name": "calc", "input": {"x": 1}},
            ],
            "stop_reason": "tool_use",
        }
        result = LLMClient.extract_anthropic_tool_calls(response)
        assert len(result) == 1
        assert result[0]["name"] == "calc"

    def test_extract_tool_use_missing_id(self):
        """tool_use block with missing id -> skipped gracefully."""
        response = {
            "content": [
                {"type": "tool_use", "name": "calc", "input": {}},
            ],
            "stop_reason": "tool_use",
        }
        result = LLMClient.extract_anthropic_tool_calls(response)
        # Should skip block with missing id or include with empty id — either is valid
        assert isinstance(result, list)

    def test_extract_tool_use_malformed_id(self):
        """tool_use block with id=None or wrong type -> graceful handling."""
        response = {
            "content": [
                {"type": "tool_use", "id": None, "name": "calc", "input": {}},
                {"type": "tool_use", "id": 123, "name": "other", "input": {}},
            ],
            "stop_reason": "tool_use",
        }
        # Should not crash — graceful handling
        result = LLMClient.extract_anthropic_tool_calls(response)
        assert isinstance(result, list)


# --- Building tool results ---

class TestBuildAnthropicToolResult:
    """Tests for build_anthropic_tool_result()."""

    def test_build_result_success(self):
        """Successful tool result message."""
        result = LLMClient.build_anthropic_tool_result("toolu_1", "42")
        assert result["role"] == "user"
        blocks = result["content"]
        assert len(blocks) == 1
        assert blocks[0]["type"] == "tool_result"
        assert blocks[0]["tool_use_id"] == "toolu_1"
        assert blocks[0]["content"] == "42"

    def test_build_result_error(self):
        """Error result with is_error=True."""
        result = LLMClient.build_anthropic_tool_result("toolu_1", "Division by zero", is_error=True)
        blocks = result["content"]
        assert blocks[0]["is_error"] is True
        assert blocks[0]["content"] == "Division by zero"

    def test_build_result_dict_content(self):
        """dict auto-serialized to JSON string."""
        result = LLMClient.build_anthropic_tool_result("toolu_1", {"answer": 42})
        blocks = result["content"]
        content = blocks[0]["content"]
        assert isinstance(content, str)
        parsed = json.loads(content)
        assert parsed["answer"] == 42

    def test_build_result_none_content(self):
        """None content handled gracefully (empty string)."""
        result = LLMClient.build_anthropic_tool_result("toolu_1", None)
        blocks = result["content"]
        assert isinstance(blocks[0]["content"], str)


# --- Roundtrip ---

class TestAnthropicToolRoundtrip:
    """Full roundtrip: convert -> extract -> build result."""

    def test_roundtrip_conversion(self):
        """convert tools -> (mock) call -> extract -> build result."""
        # 1. Convert OpenAI tools to Anthropic format
        openai_tools = [
            {
                "type": "function",
                "function": {
                    "name": "calculator",
                    "description": "Do math",
                    "parameters": {
                        "type": "object",
                        "properties": {"expr": {"type": "string"}},
                        "required": ["expr"],
                    },
                },
            }
        ]
        anthropic_tools = LLMClient.convert_tools_to_anthropic_format(openai_tools)
        assert anthropic_tools[0]["name"] == "calculator"

        # 2. Simulate Anthropic response with tool_use
        mock_response = {
            "content": [
                {"type": "tool_use", "id": "toolu_abc", "name": "calculator", "input": {"expr": "2+2"}},
            ],
            "stop_reason": "tool_use",
        }

        # 3. Extract tool calls
        calls = LLMClient.extract_anthropic_tool_calls(mock_response)
        assert len(calls) == 1
        assert calls[0]["id"] == "toolu_abc"
        assert calls[0]["name"] == "calculator"

        # 4. Build tool result
        result_msg = LLMClient.build_anthropic_tool_result(
            calls[0]["id"], json.dumps({"result": 4})
        )
        assert result_msg["role"] == "user"
        assert result_msg["content"][0]["type"] == "tool_result"
        assert result_msg["content"][0]["tool_use_id"] == "toolu_abc"
        parsed_content = json.loads(result_msg["content"][0]["content"])
        assert parsed_content["result"] == 4
