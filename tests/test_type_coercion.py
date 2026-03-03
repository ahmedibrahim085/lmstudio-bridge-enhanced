#!/usr/bin/env python3
"""
Tests for centralized type coercion.

These tests validate that the type coercion utility correctly
handles type mismatches from smaller LLMs.
"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from unittest.mock import AsyncMock, patch

from mcp_client.type_coercion import (
    coerce_tool_arg_types,
    safe_call_tool,
    NUMERIC_PARAMS,
    _load_numeric_params,
    _DEFAULT_NUMERIC_PARAMS
)


class TestTypeCoercion:
    """Tests for type coercion function."""

    def test_numeric_string_to_int(self):
        """Test coercing numeric strings to integers."""
        args = {'head': '10', 'tail': '5', 'path': '/test'}
        result = coerce_tool_arg_types(args)

        assert result['head'] == 10
        assert isinstance(result['head'], int)
        assert result['tail'] == 5
        assert isinstance(result['tail'], int)
        assert result['path'] == '/test'  # Unchanged

    def test_all_numeric_params(self):
        """Test all known numeric parameters are coerced."""
        args = {param: '100' for param in NUMERIC_PARAMS}
        result = coerce_tool_arg_types(args)

        for param in NUMERIC_PARAMS:
            assert result[param] == 100
            assert isinstance(result[param], int)

    def test_float_fallback(self):
        """Test float fallback for decimal strings."""
        args = {'head': '10.5'}
        result = coerce_tool_arg_types(args)

        assert result['head'] == 10.5
        assert isinstance(result['head'], float)

    def test_invalid_numeric_unchanged(self):
        """Test that invalid numeric strings are unchanged."""
        args = {'head': 'not_a_number'}
        result = coerce_tool_arg_types(args)

        assert result['head'] == 'not_a_number'

    def test_boolean_string_coercion(self):
        """Test coercing boolean strings."""
        args = {
            'flag1': 'true',
            'flag2': 'false',
            'flag3': 'True',
            'flag4': 'FALSE'
        }
        result = coerce_tool_arg_types(args)

        assert result['flag1'] is True
        assert result['flag2'] is False
        assert result['flag3'] is True
        assert result['flag4'] is False

    def test_already_correct_types(self):
        """Test that already correct types are unchanged."""
        args = {
            'head': 10,
            'tail': 5,
            'flag': True,
            'path': '/test'
        }
        result = coerce_tool_arg_types(args)

        assert result == args

    def test_non_dict_input(self):
        """Test that non-dict input is returned unchanged."""
        assert coerce_tool_arg_types(None) is None
        assert coerce_tool_arg_types([1, 2, 3]) == [1, 2, 3]
        assert coerce_tool_arg_types("string") == "string"

    def test_empty_dict(self):
        """Test empty dictionary."""
        result = coerce_tool_arg_types({})
        assert result == {}

    def test_mixed_types(self):
        """Test dictionary with mixed types."""
        args = {
            'head': '20',  # Should be coerced to int
            'limit': 30,   # Already int, unchanged
            'path': '/test',  # String, unchanged
            'enabled': 'true',  # Should be coerced to bool
            'other_flag': True  # Already bool, unchanged
        }
        result = coerce_tool_arg_types(args)

        assert result['head'] == 20
        assert isinstance(result['head'], int)
        assert result['limit'] == 30
        assert result['path'] == '/test'
        assert result['enabled'] is True
        assert result['other_flag'] is True

    def test_non_matching_string_unchanged(self):
        """Test that strings not matching boolean pattern are unchanged."""
        args = {'some_param': 'hello'}
        result = coerce_tool_arg_types(args)

        assert result['some_param'] == 'hello'


class TestNumericParamsConfig:
    """Tests for NUMERIC_PARAMS environment variable configuration."""

    def test_default_params_exist(self):
        """Test that default numeric params are present."""
        # These core params should always exist
        assert 'head' in _DEFAULT_NUMERIC_PARAMS
        assert 'tail' in _DEFAULT_NUMERIC_PARAMS
        assert 'limit' in _DEFAULT_NUMERIC_PARAMS
        assert 'offset' in _DEFAULT_NUMERIC_PARAMS

    def test_load_without_env_var(self, monkeypatch):
        """Test loading params without env var set."""
        monkeypatch.delenv('LMS_EXTRA_NUMERIC_PARAMS', raising=False)
        params = _load_numeric_params()
        assert params == _DEFAULT_NUMERIC_PARAMS

    def test_load_with_env_var_adds_params(self, monkeypatch):
        """Test that env var adds extra numeric params."""
        monkeypatch.setenv('LMS_EXTRA_NUMERIC_PARAMS', 'custom_limit,page_size')
        params = _load_numeric_params()

        # Should contain defaults
        assert 'head' in params
        assert 'tail' in params

        # Should contain extras from env var
        assert 'custom_limit' in params
        assert 'page_size' in params

    def test_load_with_empty_env_var(self, monkeypatch):
        """Test that empty env var doesn't break anything."""
        monkeypatch.setenv('LMS_EXTRA_NUMERIC_PARAMS', '')
        params = _load_numeric_params()
        assert params == _DEFAULT_NUMERIC_PARAMS

    def test_load_with_whitespace_handling(self, monkeypatch):
        """Test that whitespace in env var is handled correctly."""
        monkeypatch.setenv('LMS_EXTRA_NUMERIC_PARAMS', '  custom1 , custom2  ,  ')
        params = _load_numeric_params()

        # Should strip whitespace
        assert 'custom1' in params
        assert 'custom2' in params
        # Should not have empty strings
        assert '' not in params

    def test_numeric_params_includes_defaults(self):
        """Test that loaded NUMERIC_PARAMS includes all defaults."""
        for default_param in _DEFAULT_NUMERIC_PARAMS:
            assert default_param in NUMERIC_PARAMS


class TestSchemaAwareCoercion:
    """Tests for schema-aware array coercion (OPP-32).

    When a tool schema declares a parameter as type:"array", the coercion
    function should wrap single dicts in a list and parse JSON strings.
    """

    ARRAY_SCHEMA = {
        "type": "object",
        "properties": {
            "entities": {"type": "array"},
            "name": {"type": "string"},
        },
    }

    # --- Array: dict → [dict] wrapping ---

    def test_dict_wrapped_in_list(self):
        """Single dict where array expected → wrapped in list."""
        args = {"entities": {"name": "foo"}}
        result = coerce_tool_arg_types(args, schema=self.ARRAY_SCHEMA)
        assert result["entities"] == [{"name": "foo"}]

    def test_nested_dict_wrapped_in_list(self):
        """Nested dict where array expected → wrapped in list."""
        args = {"entities": {"name": "foo", "tags": [1, 2]}}
        result = coerce_tool_arg_types(args, schema=self.ARRAY_SCHEMA)
        assert result["entities"] == [{"name": "foo", "tags": [1, 2]}]

    # --- Array: JSON string parse ---

    def test_json_string_dict_wrapped(self):
        """JSON string of dict where array expected → parse then wrap."""
        args = {"entities": '{"name": "foo"}'}
        result = coerce_tool_arg_types(args, schema=self.ARRAY_SCHEMA)
        assert result["entities"] == [{"name": "foo"}]

    def test_json_string_array_parsed(self):
        """JSON string of array where array expected → parse to list."""
        args = {"entities": '[{"name": "foo"}]'}
        result = coerce_tool_arg_types(args, schema=self.ARRAY_SCHEMA)
        assert result["entities"] == [{"name": "foo"}]

    def test_invalid_json_unchanged(self):
        """Invalid JSON string where array expected → left as-is."""
        args = {"entities": "not json at all"}
        result = coerce_tool_arg_types(args, schema=self.ARRAY_SCHEMA)
        assert result["entities"] == "not json at all"

    def test_scalar_json_string_left_as_is(self):
        """Scalar JSON string (e.g. '42') where array expected → left as-is (F-5)."""
        args = {"entities": "42"}
        result = coerce_tool_arg_types(args, schema=self.ARRAY_SCHEMA)
        # Scalar int parsed from JSON should NOT be wrapped — let MCP validate
        assert result["entities"] == "42"

    def test_scalar_json_bool_string_left_as_is(self):
        """JSON bool string '"hello"' where array expected → left as-is (F-5)."""
        args = {"entities": '"hello"'}
        result = coerce_tool_arg_types(args, schema=self.ARRAY_SCHEMA)
        # Parsed to string scalar — NOT wrapped
        assert result["entities"] == '"hello"'

    # --- Array: already a list ---

    def test_already_list_unchanged(self):
        """List value where array expected → unchanged."""
        args = {"entities": [{"name": "foo"}]}
        result = coerce_tool_arg_types(args, schema=self.ARRAY_SCHEMA)
        assert result["entities"] == [{"name": "foo"}]

    # --- Array: non-wrappable types ---

    def test_int_where_array_expected_unchanged(self):
        """Integer where array expected → left as-is."""
        args = {"entities": 42}
        result = coerce_tool_arg_types(args, schema=self.ARRAY_SCHEMA)
        assert result["entities"] == 42

    def test_none_where_array_expected_unchanged(self):
        """None where array expected → left as-is."""
        args = {"entities": None}
        result = coerce_tool_arg_types(args, schema=self.ARRAY_SCHEMA)
        assert result["entities"] is None

    # --- Array: empty string ---

    def test_empty_string_where_array_expected_unchanged(self):
        """Empty string where array expected → left as-is (F-7)."""
        args = {"entities": ""}
        result = coerce_tool_arg_types(args, schema=self.ARRAY_SCHEMA)
        assert result["entities"] == ""

    # --- No schema: backward compatibility ---

    def test_without_schema_unchanged(self):
        """Without schema param → existing behavior (dict not wrapped)."""
        args = {"entities": {"name": "foo"}}
        result = coerce_tool_arg_types(args)
        assert result["entities"] == {"name": "foo"}

    def test_schema_none_unchanged(self):
        """schema=None → existing behavior (dict not wrapped)."""
        args = {"entities": {"name": "foo"}}
        result = coerce_tool_arg_types(args, schema=None)
        assert result["entities"] == {"name": "foo"}

    # --- Schema without properties ---

    def test_schema_missing_properties_key(self):
        """Schema missing 'properties' key → skip array coercion."""
        schema = {"type": "object"}
        args = {"entities": {"name": "foo"}}
        result = coerce_tool_arg_types(args, schema=schema)
        assert result["entities"] == {"name": "foo"}

    # --- Mixed: array + numeric coercion ---

    def test_mixed_array_and_numeric_coercion(self):
        """Both array and numeric coercion apply in same call (F-6)."""
        schema = {
            "type": "object",
            "properties": {
                "entities": {"type": "array"},
                "limit": {"type": "integer"},
            },
        }
        args = {"entities": {"name": "foo"}, "limit": "10"}
        result = coerce_tool_arg_types(args, schema=schema)
        # Array coercion: dict → [dict]
        assert result["entities"] == [{"name": "foo"}]
        # Numeric coercion: "10" → 10 (existing behavior)
        assert result["limit"] == 10
        assert isinstance(result["limit"], int)

    # --- safe_call_tool: schema param ---

    @pytest.mark.asyncio
    async def test_safe_call_tool_passes_schema(self):
        """safe_call_tool passes schema through to coerce_tool_arg_types."""
        mock_session = AsyncMock()
        mock_session.call_tool = AsyncMock(return_value="ok")
        schema = self.ARRAY_SCHEMA
        args = {"entities": {"name": "foo"}}

        await safe_call_tool(mock_session, "test_tool", args, schema=schema)

        # Verify call_tool received coerced args (dict wrapped in list)
        called_args = mock_session.call_tool.call_args[0][1]
        assert called_args["entities"] == [{"name": "foo"}]

    @pytest.mark.asyncio
    async def test_safe_call_tool_backward_compat(self):
        """safe_call_tool works without schema param (backward compat)."""
        mock_session = AsyncMock()
        mock_session.call_tool = AsyncMock(return_value="ok")
        args = {"entities": {"name": "foo"}}

        await safe_call_tool(mock_session, "test_tool", args)

        # Without schema, dict NOT wrapped
        called_args = mock_session.call_tool.call_args[0][1]
        assert called_args["entities"] == {"name": "foo"}

    # --- Dispatch: schema wiring ---

    @pytest.mark.asyncio
    async def test_single_session_dispatcher_passes_schema(self):
        """_SingleSessionDispatcher.dispatch passes schema to safe_call_tool."""
        from tools.dynamic_autonomous import _SingleSessionDispatcher

        mock_session = AsyncMock()
        mock_session.call_tool = AsyncMock(return_value=AsyncMock(content=[]))
        dispatcher = _SingleSessionDispatcher(mock_session)

        schema = self.ARRAY_SCHEMA
        await dispatcher.dispatch("test_tool", {"entities": {"name": "foo"}}, schema=schema)

        called_args = mock_session.call_tool.call_args[0][1]
        assert called_args["entities"] == [{"name": "foo"}]

    @pytest.mark.asyncio
    async def test_multi_session_dispatcher_passes_schema(self):
        """_MultiSessionDispatcher.dispatch passes schema to safe_call_tool."""
        from tools.dynamic_autonomous import _MultiSessionDispatcher

        mock_session = AsyncMock()
        mock_session.call_tool = AsyncMock(return_value=AsyncMock(content=[]))
        tool_to_session = {"ns__test_tool": ("test_tool", mock_session)}
        dispatcher = _MultiSessionDispatcher(tool_to_session)

        schema = self.ARRAY_SCHEMA
        await dispatcher.dispatch("ns__test_tool", {"entities": {"name": "foo"}}, schema=schema)

        called_args = mock_session.call_tool.call_args[0][1]
        assert called_args["entities"] == [{"name": "foo"}]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
