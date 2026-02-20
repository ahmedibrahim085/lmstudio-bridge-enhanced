#!/usr/bin/env python3
"""
Edge case tests for C5 and C6 fixes in tools/dynamic_autonomous.py.

C5: JSON parse errors in tool arguments now surface to the LLM instead
    of silently setting tool_args = {}.

C6: Tool result extraction now uses ToolExecutor.extract_text_content()
    instead of unsafe result.content[0].text.
"""

import json
import os
import sys

import pytest

# Add project root to path so mcp_client imports resolve
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mcp.types import (
    CallToolResult,
    ImageContent,
    TextContent,
)

from mcp_client.executor import ToolExecutor

# ---------------------------------------------------------------------------
# C5: JSON parse error surfacing
# ---------------------------------------------------------------------------


class TestC5JsonParseErrorSurfacing:
    """
    Verify that malformed JSON in tool arguments is surfaced as an explicit
    error message appended to pending_tool_results rather than silently
    swallowed by falling back to an empty dict.

    The fix lives at two locations in dynamic_autonomous.py:
      - Line 595-599  (single-server path,  tool_name)
      - Line 731-735  (multi-server path,   namespaced_tool_name)

    Because both paths are deep inside async MCP sessions we unit-test the
    extracted parse logic directly — the same pattern the production code uses.
    """

    # ------------------------------------------------------------------
    # Helper: replicate the exact C5 fix logic from dynamic_autonomous.py
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_c5_parse_logic(
        tool_name: str,
        tool_args: object,
        pending_tool_results: list,
    ) -> object:
        """
        Mirror of the C5 fix block in dynamic_autonomous.py.

        Returns the parsed tool_args (dict) on success, or appends an error
        tuple to pending_tool_results and returns the original value on failure.
        """
        if isinstance(tool_args, str):
            try:
                tool_args = json.loads(tool_args)
            except json.JSONDecodeError:
                error_msg = (
                    f"Failed to parse tool arguments for '{tool_name}': {str(tool_args)[:200]}"
                )
                pending_tool_results.append((tool_name, f"Error: {error_msg}"))
        return tool_args

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def test_invalid_json_produces_error_in_pending_results(self):
        """C5: Invalid JSON string appends an error to pending_tool_results."""
        tool_name = "test_tool"
        bad_json = "{invalid json"
        pending_tool_results: list = []

        self._apply_c5_parse_logic(tool_name, bad_json, pending_tool_results)

        assert len(pending_tool_results) == 1, (
            "Exactly one error tuple must be appended for a single bad argument"
        )

    def test_invalid_json_error_message_contains_tool_name(self):
        """C5: The surfaced error message includes the tool name."""
        tool_name = "my_special_tool"
        pending_tool_results: list = []

        self._apply_c5_parse_logic(tool_name, "{bad", pending_tool_results)

        _result_tool, error_text = pending_tool_results[0]
        assert tool_name in error_text, (
            f"Expected tool name '{tool_name}' inside error text: {error_text!r}"
        )

    def test_invalid_json_error_message_contains_descriptive_prefix(self):
        """C5: The error message starts with the standard descriptive prefix."""
        tool_name = "some_tool"
        pending_tool_results: list = []

        self._apply_c5_parse_logic(tool_name, "not-json-at-all", pending_tool_results)

        _result_tool, error_text = pending_tool_results[0]
        assert "Failed to parse tool arguments" in error_text

    def test_invalid_json_error_tuple_key_matches_tool_name(self):
        """C5: The first element of the error tuple is the tool_name."""
        tool_name = "key_check_tool"
        pending_tool_results: list = []

        self._apply_c5_parse_logic(tool_name, "[broken", pending_tool_results)

        result_tool, _ = pending_tool_results[0]
        assert result_tool == tool_name

    def test_invalid_json_error_message_is_prefixed_with_error_colon(self):
        """C5: The error value in the tuple starts with 'Error:'."""
        tool_name = "prefix_tool"
        pending_tool_results: list = []

        self._apply_c5_parse_logic(tool_name, "{'bad': json}", pending_tool_results)

        _, error_text = pending_tool_results[0]
        assert error_text.startswith("Error:"), (
            f"Expected error text to start with 'Error:' but got: {error_text!r}"
        )

    def test_valid_json_string_is_parsed_to_dict(self):
        """C5: A valid JSON string is parsed into a dict without any error."""
        tool_name = "valid_tool"
        valid_json = '{"key": "value", "count": 42}'
        pending_tool_results: list = []

        result = self._apply_c5_parse_logic(tool_name, valid_json, pending_tool_results)

        assert result == {"key": "value", "count": 42}
        assert len(pending_tool_results) == 0, "No error should be appended for valid JSON"

    def test_valid_json_empty_object_parses_correctly(self):
        """C5: An empty JSON object string '{}' is parsed to an empty dict."""
        pending_tool_results: list = []
        result = self._apply_c5_parse_logic("tool", "{}", pending_tool_results)

        assert result == {}
        assert len(pending_tool_results) == 0

    def test_dict_tool_args_bypass_json_parsing_entirely(self):
        """C5: When tool_args is already a dict it is returned unchanged."""
        already_parsed = {"already": "parsed", "count": 7}
        pending_tool_results: list = []

        result = self._apply_c5_parse_logic("tool", already_parsed, pending_tool_results)

        assert result == already_parsed
        assert len(pending_tool_results) == 0

    def test_none_tool_args_bypass_json_parsing(self):
        """C5: None tool_args (not a string) passes through without error."""
        pending_tool_results: list = []
        result = self._apply_c5_parse_logic("tool", None, pending_tool_results)

        assert result is None
        assert len(pending_tool_results) == 0

    def test_multi_server_path_uses_namespaced_tool_name(self):
        """C5 multi-server path: error tuple key must be the namespaced name."""
        namespaced_tool_name = "server1__list_files"
        pending_tool_results: list = []

        # The multi-server fix uses namespaced_tool_name instead of tool_name
        self._apply_c5_parse_logic(namespaced_tool_name, "{corrupted", pending_tool_results)

        result_key, error_text = pending_tool_results[0]
        assert result_key == namespaced_tool_name
        assert namespaced_tool_name in error_text

    def test_truncation_of_long_bad_args_in_error_message(self):
        """C5: Extremely long bad arg strings are truncated to 200 chars in the message."""
        tool_name = "truncation_tool"
        long_bad_args = "x" * 500  # definitely not valid JSON
        pending_tool_results: list = []

        self._apply_c5_parse_logic(tool_name, long_bad_args, pending_tool_results)

        _, error_text = pending_tool_results[0]
        # The production code does str(tool_args)[:200], so the snippet in the
        # message must be at most 200 characters long (plus surrounding text).
        # Check that the message does not embed more than 200 'x' characters.
        x_count = error_text.count("x")
        assert x_count <= 200, f"Expected at most 200 'x' chars (truncation), got {x_count}"


# ---------------------------------------------------------------------------
# C6: Safe tool result extraction via ToolExecutor.extract_text_content
# ---------------------------------------------------------------------------


class TestC6ExtractTextContent:
    """
    Verify ToolExecutor.extract_text_content() handles all content shapes
    safely.  The C6 fix replaced `result.content[0].text` (which crashes on
    empty content lists or non-TextContent items) with this method.
    """

    def test_single_text_content_returns_text(self):
        """C6: TextContent is extracted correctly."""
        result = CallToolResult(content=[TextContent(type="text", text="hello world")])
        assert ToolExecutor.extract_text_content(result) == "hello world"

    def test_empty_content_list_returns_no_content_returned(self):
        """C6: Empty content list returns the safe sentinel string."""
        result = CallToolResult(content=[])
        assert ToolExecutor.extract_text_content(result) == "No content returned"

    def test_multiple_text_items_are_joined(self):
        """C6: Multiple TextContent items are joined with newline."""
        result = CallToolResult(
            content=[
                TextContent(type="text", text="line 1"),
                TextContent(type="text", text="line 2"),
            ]
        )
        text = ToolExecutor.extract_text_content(result)
        assert "line 1" in text
        assert "line 2" in text

    def test_multiple_text_items_joined_with_newline(self):
        """C6: The join separator between text items is a newline."""
        result = CallToolResult(
            content=[
                TextContent(type="text", text="first"),
                TextContent(type="text", text="second"),
            ]
        )
        text = ToolExecutor.extract_text_content(result)
        assert text == "first\nsecond"

    def test_image_content_returns_image_placeholder(self):
        """C6: ImageContent produces a readable placeholder, not a crash."""
        result = CallToolResult(
            content=[ImageContent(type="image", data="base64data", mimeType="image/png")]
        )
        text = ToolExecutor.extract_text_content(result)
        assert "[Image:" in text
        assert "image/png" in text

    def test_mixed_text_and_image_content(self):
        """C6: Mixed TextContent and ImageContent both appear in output."""
        result = CallToolResult(
            content=[
                TextContent(type="text", text="description"),
                ImageContent(type="image", data="xyz", mimeType="image/jpeg"),
            ]
        )
        text = ToolExecutor.extract_text_content(result)
        assert "description" in text
        assert "[Image:" in text

    def test_text_content_with_empty_string(self):
        """C6: TextContent with an empty string value is handled gracefully."""
        result = CallToolResult(content=[TextContent(type="text", text="")])
        # Should return empty string (joined from one empty part), not raise
        text = ToolExecutor.extract_text_content(result)
        assert isinstance(text, str)

    def test_returns_string_type_always(self):
        """C6: extract_text_content always returns a str, never raises."""
        cases = [
            CallToolResult(content=[]),
            CallToolResult(content=[TextContent(type="text", text="ok")]),
            CallToolResult(content=[ImageContent(type="image", data="d", mimeType="image/gif")]),
        ]
        for result in cases:
            out = ToolExecutor.extract_text_content(result)
            assert isinstance(out, str), (
                f"Expected str, got {type(out)} for content={result.content}"
            )

    def test_old_unsafe_access_would_raise_on_empty(self):
        """
        Regression guard: the old pattern result.content[0].text would raise
        IndexError on empty content.  Confirm the new method is safe.
        """
        result = CallToolResult(content=[])

        # Old (unsafe) approach raises IndexError
        with pytest.raises(IndexError):
            _ = result.content[0].text  # type: ignore[index]

        # New (safe) approach does not raise
        text = ToolExecutor.extract_text_content(result)
        assert text == "No content returned"

    def test_old_unsafe_access_would_raise_on_image_content(self):
        """
        Regression guard: result.content[0].text raises AttributeError when
        the first item is an ImageContent (no .text attribute).
        Confirm the new method handles it gracefully.
        """
        result = CallToolResult(
            content=[ImageContent(type="image", data="d", mimeType="image/webp")]
        )

        # Old (unsafe) approach raises AttributeError
        with pytest.raises(AttributeError):
            _ = result.content[0].text  # type: ignore[union-attr]

        # New (safe) approach returns a placeholder string
        text = ToolExecutor.extract_text_content(result)
        assert "Image" in text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
