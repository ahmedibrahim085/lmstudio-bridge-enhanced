"""Tests for CompletionTools.anthropic_messages error handling.

This module tests the error handling, JSON parsing, and response formatting
of the anthropic_messages method in tools/completions.py (lines 157-192).

Tests cover:
- Happy path: successful message sending
- JSON parse errors: invalid JSON input
- LLM errors: exceptions from llm.anthropic_messages()
- Alternative message formats: lists instead of JSON strings
- Error message context: verifying error details are included
"""

import json
import os
import sys
from unittest.mock import MagicMock

import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tools.completions import CompletionTools


@pytest.fixture
def mock_llm():
    """Create a mocked LLMClient."""
    return MagicMock()


@pytest.fixture
def completion_tools(mock_llm):
    """Create CompletionTools instance with mocked LLM client."""
    return CompletionTools(llm_client=mock_llm)


class TestAnthropicMessagesHappyPath:
    """Happy path tests for anthropic_messages."""

    @pytest.mark.asyncio
    async def test_happy_path_valid_json_string(self, completion_tools, mock_llm):
        """Test successful anthropic_messages with valid JSON string.

        Given: Valid JSON string of messages
        When: anthropic_messages is called
        Then: Returns JSON with LLM response dict
        """
        # Arrange
        messages_json = json.dumps([{"role": "user", "content": "Hello"}])
        expected_response = {
            "id": "msg_123",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "Hi there"}],
            "stop_reason": "end_turn",
        }
        mock_llm.anthropic_messages.return_value = expected_response

        # Act
        result = await completion_tools.anthropic_messages(
            messages=messages_json,
            system="You are helpful",
            max_tokens=4096,
            temperature=0.7,
        )

        # Assert
        result_dict = json.loads(result)
        assert result_dict == expected_response
        assert result_dict["id"] == "msg_123"
        assert result_dict["content"][0]["text"] == "Hi there"

    @pytest.mark.asyncio
    async def test_happy_path_list_messages(self, completion_tools, mock_llm):
        """Test successful anthropic_messages with list messages (not JSON string).

        Given: Messages as a list (not JSON string)
        When: anthropic_messages is called
        Then: Handles both formats correctly and returns JSON response
        """
        # Arrange
        messages_list = [{"role": "user", "content": "Hello"}]
        expected_response = {
            "id": "msg_456",
            "type": "message",
            "content": [{"type": "text", "text": "Response"}],
            "stop_reason": "end_turn",
        }
        mock_llm.anthropic_messages.return_value = expected_response

        # Act
        result = await completion_tools.anthropic_messages(
            messages=messages_list,
            system="Be concise",
        )

        # Assert
        result_dict = json.loads(result)
        assert result_dict == expected_response
        assert result_dict["id"] == "msg_456"

    @pytest.mark.asyncio
    async def test_happy_path_parameters_passed_correctly(self, completion_tools, mock_llm):
        """Test that all parameters are passed correctly to llm.anthropic_messages.

        Given: All parameters filled in
        When: anthropic_messages is called
        Then: All parameters are forwarded to llm.anthropic_messages correctly
        """
        # Arrange
        messages_json = json.dumps([{"role": "user", "content": "Test"}])
        mock_llm.anthropic_messages.return_value = {"content": []}

        # Act
        await completion_tools.anthropic_messages(
            messages=messages_json,
            system="System prompt",
            max_tokens=2048,
            temperature=0.5,
            model="custom-model",
        )

        # Assert - verify LLM was called with correct parameters
        mock_llm.anthropic_messages.assert_called_once_with(
            messages=[{"role": "user", "content": "Test"}],
            system="System prompt",
            max_tokens=2048,
            temperature=0.5,
            model="custom-model",
        )


class TestAnthropicMessagesJsonParseError:
    """Tests for invalid JSON string handling."""

    @pytest.mark.asyncio
    async def test_invalid_json_string_error(self, completion_tools, mock_llm):
        """Test error handling when messages is invalid JSON.

        Given: Invalid JSON string as messages
        When: anthropic_messages is called
        Then: Returns JSON error response (not exception)
        """
        # Arrange
        invalid_json = '{"role": "user", "content": "Hello"'  # Missing closing brace

        # Act
        result = await completion_tools.anthropic_messages(
            messages=invalid_json,
        )

        # Assert
        result_dict = json.loads(result)
        assert "error" in result_dict
        assert "Failed to send Anthropic message" in result_dict["error"]

    @pytest.mark.asyncio
    async def test_empty_json_string_error(self, completion_tools, mock_llm):
        """Test error handling when messages is empty string.

        Given: Empty string as messages
        When: anthropic_messages is called
        Then: Returns JSON error response
        """
        # Arrange
        empty_json = ""

        # Act
        result = await completion_tools.anthropic_messages(
            messages=empty_json,
        )

        # Assert
        result_dict = json.loads(result)
        assert "error" in result_dict
        assert "Failed to send Anthropic message" in result_dict["error"]

    @pytest.mark.asyncio
    async def test_malformed_json_various_errors(self, completion_tools, mock_llm):
        """Test various malformed JSON inputs.

        Given: Various malformed JSON inputs
        When: anthropic_messages is called
        Then: All return error JSON responses
        """
        # Test cases
        test_cases = [
            '{"unclosed": "dict"',
            "[{incomplete}]",
            '{"trailing": "comma",}',
            "{not: valid}",  # Unquoted key
        ]

        for invalid_json in test_cases:
            # Act
            result = await completion_tools.anthropic_messages(
                messages=invalid_json,
            )

            # Assert
            result_dict = json.loads(result)
            assert "error" in result_dict, f"Failed for input: {invalid_json}"
            assert "Failed to send Anthropic message" in result_dict["error"]


class TestAnthropicMessagesLlmError:
    """Tests for LLM client exceptions."""

    @pytest.mark.asyncio
    async def test_llm_exception_handling(self, completion_tools, mock_llm):
        """Test error handling when LLM raises exception.

        Given: LLM client raises an exception
        When: anthropic_messages is called
        Then: Returns JSON error response (not propagating exception)
        """
        # Arrange
        messages_json = json.dumps([{"role": "user", "content": "Hello"}])
        mock_llm.anthropic_messages.side_effect = Exception("LLM connection failed")

        # Act
        result = await completion_tools.anthropic_messages(
            messages=messages_json,
        )

        # Assert
        result_dict = json.loads(result)
        assert "error" in result_dict
        assert "Failed to send Anthropic message" in result_dict["error"]
        assert "LLM connection failed" in result_dict["error"]

    @pytest.mark.asyncio
    async def test_llm_timeout_error(self, completion_tools, mock_llm):
        """Test error handling for LLM timeout.

        Given: LLM times out
        When: anthropic_messages is called
        Then: Returns JSON error response with timeout details
        """
        # Arrange
        messages_json = json.dumps([{"role": "user", "content": "Hello"}])
        mock_llm.anthropic_messages.side_effect = TimeoutError("Request timed out after 60s")

        # Act
        result = await completion_tools.anthropic_messages(
            messages=messages_json,
        )

        # Assert
        result_dict = json.loads(result)
        assert "error" in result_dict
        assert "Failed to send Anthropic message" in result_dict["error"]

    @pytest.mark.asyncio
    async def test_llm_runtime_error(self, completion_tools, mock_llm):
        """Test error handling for RuntimeError from LLM.

        Given: LLM raises RuntimeError
        When: anthropic_messages is called
        Then: Returns JSON error response
        """
        # Arrange
        messages_json = json.dumps([{"role": "user", "content": "Hello"}])
        mock_llm.anthropic_messages.side_effect = RuntimeError("Model not loaded")

        # Act
        result = await completion_tools.anthropic_messages(
            messages=messages_json,
        )

        # Assert
        result_dict = json.loads(result)
        assert "error" in result_dict
        assert "Failed to send Anthropic message" in result_dict["error"]
        assert "Model not loaded" in result_dict["error"]


class TestAnthropicMessagesMessageFormats:
    """Tests for handling different message input formats."""

    @pytest.mark.asyncio
    async def test_messages_as_json_array_string(self, completion_tools, mock_llm):
        """Test with messages as JSON array string.

        Given: Messages as JSON array string
        When: anthropic_messages is called
        Then: Successfully parses and processes
        """
        # Arrange
        messages_json = json.dumps([
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ])
        expected_response = {"id": "msg_789", "content": []}
        mock_llm.anthropic_messages.return_value = expected_response

        # Act
        result = await completion_tools.anthropic_messages(
            messages=messages_json,
        )

        # Assert
        result_dict = json.loads(result)
        assert result_dict == expected_response
        # Verify the list was correctly parsed
        mock_llm.anthropic_messages.assert_called_once()
        called_messages = mock_llm.anthropic_messages.call_args[1]["messages"]
        assert len(called_messages) == 2
        assert called_messages[0]["role"] == "user"

    @pytest.mark.asyncio
    async def test_messages_as_list_direct(self, completion_tools, mock_llm):
        """Test with messages passed as list object (not JSON string).

        Given: Messages as Python list (not JSON string)
        When: anthropic_messages is called (isinstance check handles this)
        Then: Successfully processes without JSON parsing
        """
        # Arrange
        messages_list = [
            {"role": "user", "content": "Hello"},
        ]
        expected_response = {"id": "msg_abc", "content": []}
        mock_llm.anthropic_messages.return_value = expected_response

        # Act
        result = await completion_tools.anthropic_messages(
            messages=messages_list,
        )

        # Assert
        result_dict = json.loads(result)
        assert result_dict == expected_response
        # Verify it was passed as-is to LLM
        mock_llm.anthropic_messages.assert_called_once()
        called_messages = mock_llm.anthropic_messages.call_args[1]["messages"]
        assert called_messages == messages_list


class TestAnthropicMessagesErrorMessages:
    """Tests for error message content and clarity."""

    @pytest.mark.asyncio
    async def test_error_message_includes_context(self, completion_tools, mock_llm):
        """Test that error response includes original error details.

        Given: LLM raises exception with specific message
        When: anthropic_messages is called
        Then: Error response includes the original exception message
        """
        # Arrange
        messages_json = json.dumps([{"role": "user", "content": "Hello"}])
        original_error = "API key invalid or expired"
        mock_llm.anthropic_messages.side_effect = Exception(original_error)

        # Act
        result = await completion_tools.anthropic_messages(
            messages=messages_json,
        )

        # Assert
        result_dict = json.loads(result)
        assert "error" in result_dict
        assert original_error in result_dict["error"]

    @pytest.mark.asyncio
    async def test_error_message_format_is_consistent(self, completion_tools, mock_llm):
        """Test that error messages follow consistent format.

        Given: Various error scenarios
        When: anthropic_messages is called
        Then: All error responses start with "Failed to send Anthropic message"
        """
        # Test multiple error scenarios
        error_scenarios = [
            (json.dumps([{"role": "user"}]), "invalid json scenario"),  # Missing content
            ('{"invalid": "json"', "parse error scenario"),
        ]

        for messages, scenario in error_scenarios:
            # Act
            result = await completion_tools.anthropic_messages(
                messages=messages,
            )

            # Assert
            result_dict = json.loads(result)
            assert "error" in result_dict, f"No error in {scenario}"
            assert result_dict["error"].startswith("Failed to send Anthropic message"), \
                f"Wrong format in {scenario}"


class TestAnthropicMessagesIntegration:
    """Integration tests combining multiple scenarios."""

    @pytest.mark.asyncio
    async def test_sequential_success_then_error(self, completion_tools, mock_llm):
        """Test that tools object handles success then error correctly.

        Given: First call succeeds, second call fails
        When: anthropic_messages is called twice
        Then: Both calls handle their scenarios correctly
        """
        # Arrange
        messages_json = json.dumps([{"role": "user", "content": "Hello"}])
        expected_response = {"id": "msg_1", "content": []}
        mock_llm.anthropic_messages.return_value = expected_response

        # Act & Assert - First call succeeds
        result1 = await completion_tools.anthropic_messages(messages=messages_json)
        result1_dict = json.loads(result1)
        assert result1_dict == expected_response

        # Arrange - Second call fails
        mock_llm.anthropic_messages.side_effect = Exception("Service error")

        # Act & Assert - Second call returns error
        result2 = await completion_tools.anthropic_messages(messages=messages_json)
        result2_dict = json.loads(result2)
        assert "error" in result2_dict
        assert "Failed to send Anthropic message" in result2_dict["error"]

    @pytest.mark.asyncio
    async def test_response_is_always_valid_json(self, completion_tools, mock_llm):
        """Test that response is always valid JSON regardless of outcome.

        Given: Various success and error scenarios
        When: anthropic_messages is called
        Then: Response is always valid JSON that can be parsed
        """
        # Test that we can always parse the result as JSON
        test_cases = [
            (json.dumps([{"role": "user", "content": "Q"}]), None),  # Success
            ('{"invalid":', None),  # Parse error
            (json.dumps([{"role": "user"}]), Exception("API error")),  # LLM error
        ]

        for messages, side_effect in test_cases:
            if side_effect:
                mock_llm.anthropic_messages.side_effect = side_effect
            else:
                mock_llm.anthropic_messages.side_effect = None
                mock_llm.anthropic_messages.return_value = {"id": "test"}

            # Act
            result = await completion_tools.anthropic_messages(messages=messages)

            # Assert - can always parse as JSON
            try:
                parsed = json.loads(result)
                assert isinstance(parsed, dict)
            except json.JSONDecodeError:
                pytest.fail(f"Response is not valid JSON: {result}")

    @pytest.mark.asyncio
    async def test_error_does_not_raise_exception(self, completion_tools, mock_llm):
        """Test that anthropic_messages never raises exception (returns error JSON instead).

        Given: Various error conditions
        When: anthropic_messages is called
        Then: No exceptions are raised, only error JSON responses
        """
        # Test various error conditions
        error_scenarios = [
            (json.dumps([{"role": "user"}]), Exception("LLM failed")),
            ('invalid json', None),
            ('[{]', None),
        ]

        for messages, side_effect in error_scenarios:
            if side_effect:
                mock_llm.anthropic_messages.side_effect = side_effect

            # Act - should not raise exception
            try:
                result = await completion_tools.anthropic_messages(
                    messages=messages,
                )
                # Assert - got a result
                assert isinstance(result, str)
                json.loads(result)  # Valid JSON
            except Exception as e:
                pytest.fail(f"anthropic_messages raised {type(e).__name__}: {e}")
