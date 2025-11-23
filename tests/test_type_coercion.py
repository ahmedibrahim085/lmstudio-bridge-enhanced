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

from mcp_client.type_coercion import coerce_tool_arg_types, NUMERIC_PARAMS


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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
