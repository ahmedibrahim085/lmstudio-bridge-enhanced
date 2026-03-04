"""Tests for OPP-33: Pre-dispatch argument validation.

Verifies that ToolCallGuard.validate_args() checks required parameters and
types against a schema before a tool call is dispatched.

Test categories:
- Happy: valid args pass, optional missing is ok, extra args pass, no schema skips
- Negative: missing required, wrong type
- Edge: empty args no required, nested required not validated, schema no properties
- Boundary: returns list[str] always
"""

import pytest

from tools.tool_call_guard import ToolCallGuard


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SIMPLE_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "entities": {"type": "array"},
        "name": {"type": "string"},
    },
    "required": ["entities", "name"],
}

STRING_ONLY_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "query": {"type": "string"},
    },
    "required": ["query"],
}

ARRAY_ONLY_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "items": {"type": "array"},
    },
    "required": ["items"],
}

NO_REQUIRED_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "optional_field": {"type": "string"},
    },
    # No "required" key
}

OPTIONAL_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "required_param": {"type": "string"},
        "optional_param": {"type": "integer"},
    },
    "required": ["required_param"],
}


@pytest.fixture
def guard() -> ToolCallGuard:
    schemas = {
        "memory__create_entities": SIMPLE_SCHEMA,
        "search": STRING_ONLY_SCHEMA,
        "batch_process": ARRAY_ONLY_SCHEMA,
        "no_required_tool": NO_REQUIRED_SCHEMA,
        "optional_tool": OPTIONAL_SCHEMA,
    }
    return ToolCallGuard(tool_schemas=schemas)


# ---------------------------------------------------------------------------
# Happy path tests
# ---------------------------------------------------------------------------


class TestValidArgPassValidation:
    """Happy — all required params present with correct types."""

    def test_valid_args_pass_validation(self, guard: ToolCallGuard) -> None:
        errors = guard.validate_args(
            "memory__create_entities",
            {"entities": [{"name": "Alice"}], "name": "test"},
        )
        assert errors == []

    def test_no_schema_skips_validation(self, guard: ToolCallGuard) -> None:
        """Tool not in schemas dict → empty error list (pass through)."""
        errors = guard.validate_args(
            "unknown_tool",
            {},
        )
        assert errors == []

    def test_empty_args_no_required(self, guard: ToolCallGuard) -> None:
        """Schema with no 'required' key, empty args → pass."""
        errors = guard.validate_args("no_required_tool", {})
        assert errors == []

    def test_optional_param_missing_is_ok(self, guard: ToolCallGuard) -> None:
        """Param in schema properties but not in 'required' → pass."""
        errors = guard.validate_args(
            "optional_tool",
            {"required_param": "hello"},  # optional_param omitted
        )
        assert errors == []

    def test_extra_args_not_in_schema_pass(self, guard: ToolCallGuard) -> None:
        """Args has keys not in schema → pass (no rejection for extra keys)."""
        errors = guard.validate_args(
            "search",
            {"query": "hello", "extra_key": "should_be_ignored", "another": 42},
        )
        assert errors == []


# ---------------------------------------------------------------------------
# Negative tests
# ---------------------------------------------------------------------------


class TestMissingRequiredParam:
    """Negative — required param absent triggers error."""

    def test_missing_required_param(self, guard: ToolCallGuard) -> None:
        """Schema requires 'entities', args missing it → error list non-empty."""
        errors = guard.validate_args(
            "memory__create_entities",
            {"name": "test"},  # missing "entities"
        )
        assert len(errors) >= 1
        assert any("entities" in e for e in errors)

    def test_missing_multiple_required_params(self, guard: ToolCallGuard) -> None:
        """Two required params missing → two errors."""
        errors = guard.validate_args(
            "memory__create_entities",
            {},  # missing both "entities" and "name"
        )
        assert len(errors) == 2

    def test_wrong_type_for_required_string_param(self, guard: ToolCallGuard) -> None:
        """Schema says string, arg is int → error."""
        errors = guard.validate_args(
            "search",
            {"query": 42},  # int instead of string
        )
        assert len(errors) >= 1
        assert any("query" in e for e in errors)

    def test_wrong_type_for_required_array_param(self, guard: ToolCallGuard) -> None:
        """Schema says array, arg is string → error."""
        errors = guard.validate_args(
            "batch_process",
            {"items": "not_an_array"},  # string instead of array
        )
        assert len(errors) >= 1
        assert any("items" in e for e in errors)


# ---------------------------------------------------------------------------
# Edge / boundary tests
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge and boundary conditions."""

    def test_nested_required_not_validated(self, guard: ToolCallGuard) -> None:
        """Only top-level 'required' is checked; nested object fields are not."""
        nested_schema_guard = ToolCallGuard(
            tool_schemas={
                "nested_tool": {
                    "type": "object",
                    "properties": {
                        "outer": {
                            "type": "object",
                            "properties": {"inner": {"type": "string"}},
                            "required": ["inner"],  # nested required — not checked
                        }
                    },
                    "required": ["outer"],
                }
            }
        )
        # outer is present (even without inner) — only top-level required checked
        errors = nested_schema_guard.validate_args(
            "nested_tool",
            {"outer": {}},  # inner missing, but that's nested — should pass
        )
        assert errors == []

    def test_schema_with_no_properties(self, guard: ToolCallGuard) -> None:
        """Schema is {} → pass through with no errors."""
        empty_schema_guard = ToolCallGuard(tool_schemas={"empty_tool": {}})
        errors = empty_schema_guard.validate_args("empty_tool", {"anything": 1})
        assert errors == []

    def test_validate_args_returns_list(self, guard: ToolCallGuard) -> None:
        """Return type is always list[str], even on success."""
        result = guard.validate_args("search", {"query": "test"})
        assert isinstance(result, list)

    def test_validate_args_returns_list_on_error(self, guard: ToolCallGuard) -> None:
        """Return type is list[str] when validation fails too."""
        result = guard.validate_args("search", {})
        assert isinstance(result, list)
        assert all(isinstance(e, str) for e in result)


# ---------------------------------------------------------------------------
# H-1: Bool/int validation bypass tests
# ---------------------------------------------------------------------------

INTEGER_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "count": {"type": "integer"},
    },
    "required": ["count"],
}

NUMBER_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "value": {"type": "number"},
    },
    "required": ["value"],
}


class TestOptionalParamTypeValidation:
    """M-2: Optional params that ARE provided should be type-checked."""

    def test_optional_param_wrong_type_rejected(self) -> None:
        """Schema says optional 'count' is integer, passing string should error."""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "count": {"type": "integer"},
            },
            "required": ["name"],
        }
        guard = ToolCallGuard(tool_schemas={"tool": schema})
        errors = guard.validate_args("tool", {"name": "ok", "count": "not_int"})
        assert len(errors) >= 1
        assert any("count" in e for e in errors)

    def test_optional_param_correct_type_passes(self) -> None:
        """Optional param with correct type should produce no error."""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "count": {"type": "integer"},
            },
            "required": ["name"],
        }
        guard = ToolCallGuard(tool_schemas={"tool": schema})
        errors = guard.validate_args("tool", {"name": "ok", "count": 42})
        assert errors == []

    def test_optional_param_not_provided_no_error(self) -> None:
        """Optional param not in args should produce no error."""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "count": {"type": "integer"},
            },
            "required": ["name"],
        }
        guard = ToolCallGuard(tool_schemas={"tool": schema})
        errors = guard.validate_args("tool", {"name": "ok"})
        assert errors == []


class TestBooleanIntegerBypass:
    """H-1: bool must not pass validation for integer or number types."""

    def test_boolean_rejected_for_integer_param(self) -> None:
        """Schema says 'integer', passing True should produce a validation error."""
        guard = ToolCallGuard(tool_schemas={"int_tool": INTEGER_SCHEMA})
        errors = guard.validate_args("int_tool", {"count": True})
        assert len(errors) >= 1
        assert any("count" in e for e in errors)

    def test_boolean_rejected_for_number_param(self) -> None:
        """Schema says 'number', passing False should produce a validation error."""
        guard = ToolCallGuard(tool_schemas={"num_tool": NUMBER_SCHEMA})
        errors = guard.validate_args("num_tool", {"value": False})
        assert len(errors) >= 1
        assert any("value" in e for e in errors)
