"""Tests for OPP-32 — Schema-Aware Type Coercion.

Verifies that coerce_with_schema() applies JSON parsing for array/object
arguments when the tool's inputSchema declares the expected type, fixing
the 13 WARNs observed in the log (array coercion gap: LLM passes a JSON
string, MCP expects a parsed list).

Test categories:
- Happy: string-encoded arrays/objects coerced correctly (5 tests)
- Negative: invalid JSON, type mismatches stay as original (4 tests)
- Edge: empty string, None, already-correct types, no schema (7 tests)
- Boundary: deeply nested JSON (1 test)
- Integration: safe_call_tool with schema kwarg (2 tests)
- Config: SCHEMA_COERCION_ENABLED=False skips parsing (1 test)
- ToolDiscovery: get_tool_schema returns inputSchema (2 tests)

RED phase: ALL 22 tests fail — coerce_with_schema and
SCHEMA_COERCION_ENABLED do not exist yet.
"""

import os
import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config.constants import LMSTUDIO_TESTING_ENV_VAR  # noqa: E402

os.environ.setdefault(LMSTUDIO_TESTING_ENV_VAR, "1")

# ---------------------------------------------------------------------------
# Lazy import helpers — deferred so pytest can collect all 22 tests even when
# the symbols don't exist yet (RED phase). Each test imports explicitly.
# ---------------------------------------------------------------------------


def _coerce_with_schema():
    """Import coerce_with_schema — raises ImportError until GREEN phase."""
    from mcp_client.type_coercion import coerce_with_schema
    return coerce_with_schema


def _safe_call_tool():
    """Import safe_call_tool — must accept tool_schema kwarg after GREEN phase."""
    from mcp_client.type_coercion import safe_call_tool
    return safe_call_tool


def _schema_coercion_enabled():
    """Import SCHEMA_COERCION_ENABLED — raises ImportError until GREEN phase."""
    from config.constants.tool_config import SCHEMA_COERCION_ENABLED
    return SCHEMA_COERCION_ENABLED


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def array_schema() -> dict[str, Any]:
    """Schema where 'entities' is an array of objects and 'name' is a string."""
    return {
        "type": "object",
        "properties": {
            "entities": {"type": "array", "items": {"type": "object"}},
            "name": {"type": "string"},
        },
        "required": ["entities"],
    }


@pytest.fixture
def object_schema() -> dict[str, Any]:
    """Schema where 'config' is an object and 'name' is a string."""
    return {
        "type": "object",
        "properties": {
            "config": {"type": "object"},
            "name": {"type": "string"},
        },
    }


@pytest.fixture
def mock_session() -> AsyncMock:
    """Minimal async MCP ClientSession mock."""
    session = AsyncMock()
    session.call_tool = AsyncMock(return_value={"content": [{"text": "ok"}]})
    return session


# ===========================================================================
# 1. Happy Path — 5 tests
# ===========================================================================


class TestHappyPath:
    """String-encoded JSON is parsed when schema declares the expected type."""

    def test_string_array_coerced_to_list(self, array_schema):
        """Schema says 'array', value is '[1, 2, 3]' string → coerced to list."""
        coerce_with_schema = _coerce_with_schema()
        args = {"entities": "[1, 2, 3]", "name": "test"}
        result = coerce_with_schema(args, array_schema)
        assert result["entities"] == [1, 2, 3], (
            "String-encoded array should be parsed to a Python list"
        )
        assert isinstance(result["entities"], list)

    def test_string_object_coerced_to_dict(self, object_schema):
        """Schema says 'object', value is '{"key": "val"}' string → coerced to dict."""
        coerce_with_schema = _coerce_with_schema()
        args = {"config": '{"key": "val"}', "name": "test"}
        result = coerce_with_schema(args, object_schema)
        assert result["config"] == {"key": "val"}, (
            "String-encoded object should be parsed to a Python dict"
        )
        assert isinstance(result["config"], dict)

    def test_nested_array_of_objects(self, array_schema):
        """Nested JSON string '[{"name": "test", "age": 5}]' is parsed correctly."""
        coerce_with_schema = _coerce_with_schema()
        raw = '[{"name": "test", "age": 5}]'
        args = {"entities": raw, "name": "x"}
        result = coerce_with_schema(args, array_schema)
        assert result["entities"] == [{"name": "test", "age": 5}]
        assert isinstance(result["entities"], list)
        assert isinstance(result["entities"][0], dict)

    def test_existing_numeric_coercion_preserved(self, array_schema):
        """Regression: existing coerce_tool_arg_types numeric coercion still fires.

        Even when schema coercion is active, a param named 'limit' with value
        '10' should still be coerced to int via coerce_tool_arg_types.
        """
        from mcp_client.type_coercion import coerce_tool_arg_types

        args = {"limit": "10", "path": "/tmp"}
        result = coerce_tool_arg_types(args)
        assert result["limit"] == 10
        assert isinstance(result["limit"], int)

    def test_existing_boolean_coercion_preserved(self, array_schema):
        """Regression: boolean string coercion still works after schema coercion."""
        from mcp_client.type_coercion import coerce_tool_arg_types

        args = {"enabled": "true", "verbose": "false"}
        result = coerce_tool_arg_types(args)
        assert result["enabled"] is True
        assert result["verbose"] is False


# ===========================================================================
# 2. Negative — 4 tests
# ===========================================================================


class TestNegative:
    """Coercion fails gracefully; original value preserved on type mismatch."""

    def test_invalid_json_stays_as_string(self, array_schema):
        """Schema says array, value is 'not json at all' → stays as string."""
        coerce_with_schema = _coerce_with_schema()
        args = {"entities": "not json at all", "name": "x"}
        result = coerce_with_schema(args, array_schema)
        assert result["entities"] == "not json at all", (
            "Invalid JSON should not be coerced — keep original string"
        )

    def test_valid_string_not_json_keeps_original(self, array_schema):
        """Schema says array, value is '[note: this is text]' → stays string."""
        coerce_with_schema = _coerce_with_schema()
        args = {"entities": "[note: this is text]", "name": "x"}
        result = coerce_with_schema(args, array_schema)
        assert result["entities"] == "[note: this is text]", (
            "Text that looks array-like but is not valid JSON should be kept"
        )

    def test_schema_says_array_but_parsed_is_object(self, array_schema):
        """Schema says array, JSON parses to object → type mismatch, keep original."""
        coerce_with_schema = _coerce_with_schema()
        args = {"entities": '{"key": "val"}', "name": "x"}
        result = coerce_with_schema(args, array_schema)
        assert result["entities"] == '{"key": "val"}', (
            "If parsed type doesn't match schema type, keep original string"
        )

    def test_schema_says_object_but_parsed_is_array(self, object_schema):
        """Schema says object, JSON parses to array → type mismatch, keep original."""
        coerce_with_schema = _coerce_with_schema()
        args = {"config": "[1, 2, 3]", "name": "x"}
        result = coerce_with_schema(args, object_schema)
        assert result["config"] == "[1, 2, 3]", (
            "If parsed type doesn't match schema type, keep original string"
        )


# ===========================================================================
# 3. Edge Cases — 7 tests
# ===========================================================================


class TestEdgeCases:
    """Boundary inputs and special cases."""

    def test_empty_string_stays_empty(self, array_schema):
        """Schema says array, value is '' → stays ''."""
        coerce_with_schema = _coerce_with_schema()
        args = {"entities": "", "name": "x"}
        result = coerce_with_schema(args, array_schema)
        assert result["entities"] == ""

    def test_none_value_stays_none(self, array_schema):
        """Schema says array, value is None → stays None."""
        coerce_with_schema = _coerce_with_schema()
        args = {"entities": None, "name": "x"}
        result = coerce_with_schema(args, array_schema)
        assert result["entities"] is None

    def test_already_correct_array_unchanged(self, array_schema):
        """Value is already [1, 2, 3] (list) → untouched."""
        coerce_with_schema = _coerce_with_schema()
        args = {"entities": [1, 2, 3], "name": "x"}
        result = coerce_with_schema(args, array_schema)
        assert result["entities"] == [1, 2, 3]
        assert isinstance(result["entities"], list)

    def test_already_correct_dict_unchanged(self, object_schema):
        """Value is already {"key": "val"} (dict) → untouched."""
        coerce_with_schema = _coerce_with_schema()
        args = {"config": {"key": "val"}, "name": "x"}
        result = coerce_with_schema(args, object_schema)
        assert result["config"] == {"key": "val"}
        assert isinstance(result["config"], dict)

    def test_no_schema_falls_back(self):
        """coerce_with_schema(args, None) → returns args unchanged."""
        coerce_with_schema = _coerce_with_schema()
        args = {"entities": "[1, 2, 3]", "limit": "5"}
        result = coerce_with_schema(args, None)
        assert result == args

    def test_schema_no_properties_key(self):
        """Schema is {"type": "object"} with no 'properties' → no-op."""
        coerce_with_schema = _coerce_with_schema()
        schema = {"type": "object"}
        args = {"entities": "[1, 2, 3]"}
        result = coerce_with_schema(args, schema)
        assert result["entities"] == "[1, 2, 3]"

    def test_non_string_value_untouched(self, array_schema):
        """Schema says array, value is integer 42 → stays 42 (not a string)."""
        coerce_with_schema = _coerce_with_schema()
        args = {"entities": 42, "name": "x"}
        result = coerce_with_schema(args, array_schema)
        assert result["entities"] == 42


# ===========================================================================
# 4. Boundary — 1 test
# ===========================================================================


class TestBoundary:
    """Deep nesting and size boundaries."""

    def test_deeply_nested_object_parsed(self, object_schema):
        """3-level nested JSON string is parsed correctly."""
        coerce_with_schema = _coerce_with_schema()
        raw = '{"level1": {"level2": {"level3": "value"}}}'
        args = {"config": raw, "name": "x"}
        result = coerce_with_schema(args, object_schema)
        assert result["config"] == {"level1": {"level2": {"level3": "value"}}}
        assert isinstance(result["config"], dict)


# ===========================================================================
# 5. Integration — 2 tests
# ===========================================================================


class TestIntegration:
    """safe_call_tool with and without tool_schema kwarg."""

    @pytest.mark.asyncio
    async def test_safe_call_tool_with_schema(self, mock_session, array_schema):
        """safe_call_tool(session, tool, args, tool_schema=schema) applies schema coercion."""
        safe_call_tool = _safe_call_tool()
        args = {"entities": '[{"name": "Alice"}]', "name": "test"}
        await safe_call_tool(
            mock_session, "memory__create_entities", args, tool_schema=array_schema
        )

        mock_session.call_tool.assert_called_once()
        call_args = mock_session.call_tool.call_args
        # Positional: call_tool("tool_name", coerced_args)
        if call_args.args and len(call_args.args) >= 2:
            passed_args = call_args.args[1]
        else:
            passed_args = call_args.kwargs
        assert isinstance(passed_args.get("entities"), list), (
            "safe_call_tool should pass parsed array to session.call_tool, not a string"
        )

    @pytest.mark.asyncio
    async def test_safe_call_tool_without_schema_backward_compat(self, mock_session):
        """safe_call_tool(session, tool, args) still works — no schema param needed."""
        safe_call_tool = _safe_call_tool()
        args = {"limit": "5", "path": "/tmp"}
        # Must not raise — backward-compatible signature
        await safe_call_tool(mock_session, "list_directory", args)
        mock_session.call_tool.assert_called_once()


# ===========================================================================
# 6. Config — 1 test
# ===========================================================================


class TestConfig:
    """SCHEMA_COERCION_ENABLED flag controls coercion."""

    def test_schema_coercion_disabled_skips_parsing(self, array_schema, monkeypatch):
        """When SCHEMA_COERCION_ENABLED is False, schema coercion is skipped."""
        coerce_with_schema = _coerce_with_schema()
        monkeypatch.setattr(
            "mcp_client.type_coercion.SCHEMA_COERCION_ENABLED", False
        )
        args = {"entities": "[1, 2, 3]", "name": "x"}
        result = coerce_with_schema(args, array_schema)
        assert result["entities"] == "[1, 2, 3]", (
            "When SCHEMA_COERCION_ENABLED=False, no JSON parsing should occur"
        )


# ===========================================================================
# 7. ToolDiscovery — 2 tests
# ===========================================================================


class TestToolDiscovery:
    """ToolDiscovery.get_tool_schema returns the tool's inputSchema."""

    @pytest.mark.asyncio
    async def test_get_tool_schema_returns_input_schema(self):
        """get_tool_schema('tool_name') returns the tool's inputSchema dict."""
        from mcp_client.tool_discovery import ToolDiscovery
        from mcp.types import Tool

        mock_session = AsyncMock()
        schema = {
            "type": "object",
            "properties": {
                "entities": {"type": "array"},
            },
        }
        tool = Tool(
            name="memory__create_entities",
            description="Create entities",
            inputSchema=schema,
        )
        mock_session.list_tools = AsyncMock(return_value=MagicMock(tools=[tool]))

        discovery = ToolDiscovery(mock_session)
        result = await discovery.get_tool_schema("memory__create_entities")
        assert result == schema, (
            "get_tool_schema should return the inputSchema of the named tool"
        )

    @pytest.mark.asyncio
    async def test_get_tool_schema_returns_none_for_unknown(self):
        """get_tool_schema('unknown') returns None when tool not found."""
        from mcp_client.tool_discovery import ToolDiscovery
        from mcp.types import Tool

        mock_session = AsyncMock()
        tool = Tool(
            name="known_tool",
            description="A known tool",
            inputSchema={"type": "object", "properties": {}},
        )
        mock_session.list_tools = AsyncMock(return_value=MagicMock(tools=[tool]))

        discovery = ToolDiscovery(mock_session)
        result = await discovery.get_tool_schema("unknown_tool")
        assert result is None, (
            "get_tool_schema should return None for unregistered tool names"
        )
