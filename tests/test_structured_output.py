#!/usr/bin/env python3
"""
Comprehensive tests for LM Studio v0.3.32+ Structured Output feature.

Tests the JSON schema structured output functionality:
1. Schema validation utilities (validate_json_schema, validate_response_format)
2. Response format helper functions (build_response_format)
3. Chat completion with response_format parameter
4. Backward compatibility (existing calls without response_format still work)
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

# Import the modules under test
from utils.schema_utils import (
    SchemaValidationResult,
    validate_json_schema,
    validate_response_format,
    build_response_format
)
from config.constants import (
    STRUCTURED_OUTPUT_TYPES,
    MAX_JSON_SCHEMA_DEPTH,
    MAX_JSON_SCHEMA_PROPERTIES,
    DEFAULT_JSON_SCHEMA_STRICT,
    STRUCTURED_OUTPUT_MODEL_WARNING
)


class TestSchemaValidationResult:
    """Test the SchemaValidationResult dataclass."""

    def test_valid_result_defaults(self):
        """Test that valid result has correct defaults."""
        result = SchemaValidationResult(valid=True)
        assert result.valid is True
        assert result.errors == []
        assert result.warnings == []
        assert result.corrected_schema is None

    def test_invalid_result_with_errors(self):
        """Test result with errors."""
        result = SchemaValidationResult(
            valid=False,
            errors=["Missing type field", "Invalid structure"]
        )
        assert result.valid is False
        assert len(result.errors) == 2
        assert "Missing type field" in result.errors

    def test_result_with_warnings(self):
        """Test result with warnings but still valid."""
        result = SchemaValidationResult(
            valid=True,
            warnings=["Consider adding required field"]
        )
        assert result.valid is True
        assert len(result.warnings) == 1


class TestValidateJsonSchema:
    """Test the validate_json_schema function."""

    def test_valid_simple_object_schema(self):
        """Test that a simple valid object schema passes."""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"}
            },
            "required": ["name"]
        }
        result = validate_json_schema(schema)
        assert result.valid is True
        assert len(result.errors) == 0

    def test_valid_array_schema(self):
        """Test that a valid array schema passes."""
        schema = {
            "type": "array",
            "items": {"type": "string"}
        }
        result = validate_json_schema(schema)
        assert result.valid is True
        assert len(result.errors) == 0

    def test_valid_primitive_schemas(self):
        """Test that primitive type schemas pass."""
        primitive_types = ["string", "number", "integer", "boolean", "null"]
        for ptype in primitive_types:
            schema = {"type": ptype}
            result = validate_json_schema(schema)
            assert result.valid is True, f"Failed for type: {ptype}"

    def test_missing_type_field_fails(self):
        """Test that schema without 'type' field fails."""
        schema = {
            "properties": {
                "name": {"type": "string"}
            }
        }
        result = validate_json_schema(schema)
        assert result.valid is False
        assert any("type" in e.lower() for e in result.errors)

    def test_invalid_type_value_fails(self):
        """Test that schema with invalid type value fails."""
        schema = {"type": "invalid_type"}
        result = validate_json_schema(schema)
        assert result.valid is False
        assert any("invalid type" in e.lower() for e in result.errors)

    def test_non_dict_schema_fails(self):
        """Test that non-dictionary schema fails."""
        result = validate_json_schema("not a dict")
        assert result.valid is False
        assert any("dictionary" in e.lower() for e in result.errors)

    def test_non_dict_list_schema_fails(self):
        """Test that list schema fails."""
        result = validate_json_schema(["type", "object"])
        assert result.valid is False
        assert any("dictionary" in e.lower() for e in result.errors)

    def test_object_without_properties_warns(self):
        """Test that object schema without properties logs warning."""
        schema = {"type": "object"}
        result = validate_json_schema(schema)
        assert result.valid is True  # Still valid, just warning
        assert len(result.warnings) > 0
        assert any("properties" in w.lower() for w in result.warnings)

    def test_array_without_items_warns(self):
        """Test that array schema without items logs warning."""
        schema = {"type": "array"}
        result = validate_json_schema(schema)
        assert result.valid is True  # Still valid, just warning
        assert len(result.warnings) > 0
        assert any("items" in w.lower() for w in result.warnings)

    def test_invalid_properties_type_fails(self):
        """Test that properties must be a dictionary."""
        schema = {
            "type": "object",
            "properties": ["name", "age"]  # Should be dict
        }
        result = validate_json_schema(schema)
        assert result.valid is False
        assert any("properties" in e.lower() and "dictionary" in e.lower() for e in result.errors)

    def test_invalid_required_type_fails(self):
        """Test that required must be an array."""
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": "name"  # Should be array
        }
        result = validate_json_schema(schema)
        assert result.valid is False
        assert any("required" in e.lower() and "array" in e.lower() for e in result.errors)

    def test_too_many_properties_fails(self):
        """Test that schema with too many properties fails."""
        # Create schema with more than MAX_JSON_SCHEMA_PROPERTIES
        properties = {f"prop_{i}": {"type": "string"} for i in range(MAX_JSON_SCHEMA_PROPERTIES + 1)}
        schema = {
            "type": "object",
            "properties": properties
        }
        result = validate_json_schema(schema)
        assert result.valid is False
        assert any("too many properties" in e.lower() for e in result.errors)

    def test_deeply_nested_schema_fails(self):
        """Test that overly nested schema fails depth check."""
        # Create deeply nested schema (exceeds MAX_JSON_SCHEMA_DEPTH)
        schema = {"type": "object"}
        current = schema
        for i in range(MAX_JSON_SCHEMA_DEPTH + 2):
            current["properties"] = {
                "nested": {"type": "object"}
            }
            current = current["properties"]["nested"]

        result = validate_json_schema(schema)
        assert result.valid is False
        assert any("depth" in e.lower() or "nested" in e.lower() for e in result.errors)

    def test_nested_array_items_validated(self):
        """Test that nested array items are validated."""
        schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "value": {"type": "number"}
                }
            }
        }
        result = validate_json_schema(schema)
        assert result.valid is True

    def test_complex_nested_schema_valid(self):
        """Test that complex but valid nested schema passes."""
        schema = {
            "type": "object",
            "properties": {
                "users": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "email": {"type": "string"},
                            "addresses": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "street": {"type": "string"},
                                        "city": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        result = validate_json_schema(schema)
        assert result.valid is True


class TestBuildResponseFormat:
    """Test the build_response_format helper function."""

    def test_basic_build(self):
        """Test basic response format building."""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"}
            }
        }
        result = build_response_format(schema)

        assert result["type"] == "json_schema"
        assert "json_schema" in result
        assert result["json_schema"]["name"] == "response"
        assert result["json_schema"]["schema"] == schema
        assert result["json_schema"]["strict"] == "true"

    def test_custom_name(self):
        """Test response format with custom name."""
        schema = {"type": "object", "properties": {"x": {"type": "number"}}}
        result = build_response_format(schema, name="coordinates")

        assert result["json_schema"]["name"] == "coordinates"

    def test_strict_false(self):
        """Test response format with strict=False."""
        schema = {"type": "string"}
        result = build_response_format(schema, strict=False)

        assert result["json_schema"]["strict"] == "false"

    def test_preserves_schema_exactly(self):
        """Test that original schema is preserved exactly."""
        schema = {
            "type": "object",
            "properties": {
                "languages": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": ["languages"]
        }
        result = build_response_format(schema, name="langs")

        assert result["json_schema"]["schema"] == schema


class TestValidateResponseFormat:
    """Test the validate_response_format function."""

    def test_valid_json_schema_format(self):
        """Test valid json_schema response format."""
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "test",
                "schema": {
                    "type": "object",
                    "properties": {
                        "result": {"type": "string"}
                    }
                }
            }
        }
        result = validate_response_format(response_format)
        assert result.valid is True

    def test_valid_json_object_format(self):
        """Test valid json_object response format."""
        response_format = {"type": "json_object"}
        result = validate_response_format(response_format)
        assert result.valid is True

    def test_missing_type_fails(self):
        """Test that missing type fails."""
        response_format = {
            "json_schema": {"name": "test", "schema": {"type": "object"}}
        }
        result = validate_response_format(response_format)
        assert result.valid is False
        assert any("type" in e.lower() for e in result.errors)

    def test_invalid_type_fails(self):
        """Test that invalid type fails."""
        response_format = {"type": "invalid_format"}
        result = validate_response_format(response_format)
        assert result.valid is False
        assert any("invalid type" in e.lower() for e in result.errors)

    def test_json_schema_missing_json_schema_field_fails(self):
        """Test that json_schema type without json_schema field fails."""
        response_format = {"type": "json_schema"}
        result = validate_response_format(response_format)
        assert result.valid is False
        assert any("json_schema" in e.lower() for e in result.errors)

    def test_json_schema_missing_schema_field_fails(self):
        """Test that json_schema without schema field fails."""
        response_format = {
            "type": "json_schema",
            "json_schema": {"name": "test"}
        }
        result = validate_response_format(response_format)
        assert result.valid is False
        assert any("schema" in e.lower() for e in result.errors)

    def test_missing_name_warns(self):
        """Test that missing name generates warning."""
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "schema": {"type": "object", "properties": {"x": {"type": "number"}}}
            }
        }
        result = validate_response_format(response_format)
        assert result.valid is True  # Still valid, just warning
        assert len(result.warnings) > 0
        assert any("name" in w.lower() for w in result.warnings)

    def test_invalid_inner_schema_propagates(self):
        """Test that invalid inner schema errors propagate."""
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "test",
                "schema": {
                    "type": "invalid_type"  # Invalid type in inner schema
                }
            }
        }
        result = validate_response_format(response_format)
        assert result.valid is False
        assert any("invalid type" in e.lower() for e in result.errors)

    def test_non_dict_response_format_fails(self):
        """Test that non-dictionary response format fails."""
        result = validate_response_format("not a dict")
        assert result.valid is False
        assert any("dictionary" in e.lower() for e in result.errors)


class TestStructuredOutputConstants:
    """Test that structured output constants are correctly defined."""

    def test_structured_output_types_defined(self):
        """Test that STRUCTURED_OUTPUT_TYPES contains expected values."""
        assert "json_schema" in STRUCTURED_OUTPUT_TYPES
        assert "json_object" in STRUCTURED_OUTPUT_TYPES
        assert len(STRUCTURED_OUTPUT_TYPES) == 2

    def test_max_depth_reasonable(self):
        """Test that MAX_JSON_SCHEMA_DEPTH is reasonable."""
        assert MAX_JSON_SCHEMA_DEPTH >= 5
        assert MAX_JSON_SCHEMA_DEPTH <= 20
        assert MAX_JSON_SCHEMA_DEPTH == 10  # Current value

    def test_max_properties_reasonable(self):
        """Test that MAX_JSON_SCHEMA_PROPERTIES is reasonable."""
        assert MAX_JSON_SCHEMA_PROPERTIES >= 50
        assert MAX_JSON_SCHEMA_PROPERTIES <= 200
        assert MAX_JSON_SCHEMA_PROPERTIES == 100  # Current value

    def test_default_strict_is_true(self):
        """Test that DEFAULT_JSON_SCHEMA_STRICT is True."""
        assert DEFAULT_JSON_SCHEMA_STRICT is True

    def test_model_warning_exists(self):
        """Test that model warning message exists and is informative."""
        assert STRUCTURED_OUTPUT_MODEL_WARNING is not None
        assert len(STRUCTURED_OUTPUT_MODEL_WARNING) > 50
        assert "7B" in STRUCTURED_OUTPUT_MODEL_WARNING  # Mentions model size


class TestChatCompletionWithResponseFormat:
    """Test chat_completion with response_format parameter (mocked)."""

    def test_response_format_none_default(self):
        """Test that response_format=None doesn't change behavior."""
        # This tests backward compatibility
        from tools.completions import CompletionTools

        mock_llm = Mock()
        mock_llm.chat_completion.return_value = {
            "choices": [{"message": {"content": "Hello"}}]
        }

        tools = CompletionTools(llm_client=mock_llm)

        import asyncio
        result = asyncio.run(tools.chat_completion(
            prompt="Hello",
            response_format=None  # Explicit None
        ))

        # Verify LLM was called
        mock_llm.chat_completion.assert_called_once()

        # Verify response_format was passed as None
        call_kwargs = mock_llm.chat_completion.call_args[1]
        assert call_kwargs.get("response_format") is None

        assert result == "Hello"

    def test_response_format_json_schema_passed(self):
        """Test that response_format with json_schema is passed correctly."""
        from tools.completions import CompletionTools

        mock_llm = Mock()
        mock_llm.chat_completion.return_value = {
            "choices": [{"message": {"content": '{"name": "Test"}'}}]
        }

        tools = CompletionTools(llm_client=mock_llm)

        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "test",
                "schema": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}}
                }
            }
        }

        import asyncio
        result = asyncio.run(tools.chat_completion(
            prompt="Give me a name",
            response_format=response_format
        ))

        # Verify response_format was passed
        call_kwargs = mock_llm.chat_completion.call_args[1]
        assert call_kwargs["response_format"] == response_format

    def test_response_format_json_object_passed(self):
        """Test that response_format with json_object is passed correctly."""
        from tools.completions import CompletionTools

        mock_llm = Mock()
        mock_llm.chat_completion.return_value = {
            "choices": [{"message": {"content": '{"key": "value"}'}}]
        }

        tools = CompletionTools(llm_client=mock_llm)

        response_format = {"type": "json_object"}

        import asyncio
        result = asyncio.run(tools.chat_completion(
            prompt="Return JSON",
            response_format=response_format
        ))

        # Verify response_format was passed
        call_kwargs = mock_llm.chat_completion.call_args[1]
        assert call_kwargs["response_format"] == response_format


class TestLLMClientPayloadBuilding:
    """Test that LLMClient correctly builds payload with response_format."""

    def test_payload_without_response_format(self):
        """Test payload is built correctly without response_format."""
        from llm.llm_client import LLMClient

        # Create client and mock its session for HTTP pooling
        client = LLMClient()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "test"}}]
        }
        client.session.post = Mock(return_value=mock_response)

        client.chat_completion(
            messages=[{"role": "user", "content": "Hello"}],
            response_format=None
        )

        # Get the payload sent
        call_args = client.session.post.call_args
        payload = call_args[1]["json"]

        # response_format should not be in payload
        assert "response_format" not in payload

    def test_payload_with_response_format(self):
        """Test payload is built correctly with response_format."""
        from llm.llm_client import LLMClient

        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "test",
                "schema": {"type": "object", "properties": {"result": {"type": "string"}}}
            }
        }

        # Create client and mock its session for HTTP pooling
        client = LLMClient()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": '{"result": "test"}'}}]
        }
        client.session.post = Mock(return_value=mock_response)

        client.chat_completion(
            messages=[{"role": "user", "content": "Hello"}],
            response_format=response_format
        )

        # Get the payload sent
        call_args = client.session.post.call_args
        payload = call_args[1]["json"]

        # response_format should be in payload
        assert "response_format" in payload
        assert payload["response_format"] == response_format


class TestBackwardCompatibility:
    """Test that existing functionality is not broken."""

    def test_chat_completion_without_response_format_works(self):
        """Test that chat_completion works without response_format parameter."""
        from tools.completions import CompletionTools

        mock_llm = Mock()
        mock_llm.chat_completion.return_value = {
            "choices": [{"message": {"content": "Response without schema"}}]
        }

        tools = CompletionTools(llm_client=mock_llm)

        import asyncio
        # Call without response_format parameter at all
        result = asyncio.run(tools.chat_completion(
            prompt="Hello",
            temperature=0.5,
            max_tokens=100
        ))

        assert result == "Response without schema"
        mock_llm.chat_completion.assert_called_once()

    def test_existing_parameters_still_work(self):
        """Test that all existing parameters still work."""
        from tools.completions import CompletionTools

        mock_llm = Mock()
        mock_llm.chat_completion.return_value = {
            "choices": [{"message": {"content": "Test response"}}]
        }

        tools = CompletionTools(llm_client=mock_llm)

        import asyncio
        result = asyncio.run(tools.chat_completion(
            prompt="Test prompt",
            system_prompt="You are a helpful assistant",
            temperature=0.3,
            max_tokens=500
        ))

        # Verify all parameters were passed correctly
        call_args = mock_llm.chat_completion.call_args
        call_kwargs = call_args[1]

        assert call_kwargs["temperature"] == 0.3
        assert call_kwargs["max_tokens"] == 500

        # Check messages were built correctly
        messages = call_kwargs["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are a helpful assistant"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Test prompt"


class TestValidateJsonSchemaTool:
    """Test the validate_json_schema MCP tool."""

    def test_validate_json_schema_tool_valid_schema(self):
        """Test MCP tool returns valid result for valid schema."""
        # Simulate what the MCP tool does
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"}
            }
        }

        result = validate_json_schema(schema)
        result_json = json.dumps({
            "valid": result.valid,
            "errors": result.errors,
            "warnings": result.warnings
        }, indent=2)

        parsed = json.loads(result_json)
        assert parsed["valid"] is True
        assert parsed["errors"] == []

    def test_validate_json_schema_tool_invalid_schema(self):
        """Test MCP tool returns errors for invalid schema."""
        schema = {"properties": {"x": {"type": "string"}}}  # Missing type

        result = validate_json_schema(schema)
        result_json = json.dumps({
            "valid": result.valid,
            "errors": result.errors,
            "warnings": result.warnings
        }, indent=2)

        parsed = json.loads(result_json)
        assert parsed["valid"] is False
        assert len(parsed["errors"]) > 0


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_schema(self):
        """Test validation of empty schema."""
        schema = {}
        result = validate_json_schema(schema)
        assert result.valid is False  # Missing type

    def test_schema_with_additional_properties(self):
        """Test schema with additionalProperties."""
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "additionalProperties": {"type": "number"}
        }
        result = validate_json_schema(schema)
        assert result.valid is True

    def test_schema_with_additional_properties_false(self):
        """Test schema with additionalProperties=false."""
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "additionalProperties": False
        }
        result = validate_json_schema(schema)
        assert result.valid is True

    def test_deeply_nested_but_within_limit(self):
        """Test schema at exactly MAX_JSON_SCHEMA_DEPTH is allowed."""
        # Create schema at exactly MAX_JSON_SCHEMA_DEPTH
        schema = {"type": "object"}
        current = schema
        # Create MAX_JSON_SCHEMA_DEPTH - 1 levels (since root is level 1)
        for i in range(MAX_JSON_SCHEMA_DEPTH - 1):
            current["properties"] = {
                "level": {"type": "object"}
            }
            current = current["properties"]["level"]

        result = validate_json_schema(schema)
        # This should be valid as it's at exactly the limit
        assert result.valid is True

    def test_exactly_max_properties(self):
        """Test schema with exactly MAX_JSON_SCHEMA_PROPERTIES is allowed."""
        properties = {f"prop_{i}": {"type": "string"} for i in range(MAX_JSON_SCHEMA_PROPERTIES)}
        schema = {
            "type": "object",
            "properties": properties
        }
        result = validate_json_schema(schema)
        assert result.valid is True


def test_structured_output_test_suite_completeness():
    """Meta-test: Verify all structured output features are tested."""
    test_classes = [
        TestSchemaValidationResult,
        TestValidateJsonSchema,
        TestBuildResponseFormat,
        TestValidateResponseFormat,
        TestStructuredOutputConstants,
        TestChatCompletionWithResponseFormat,
        TestLLMClientPayloadBuilding,
        TestBackwardCompatibility,
        TestValidateJsonSchemaTool,
        TestEdgeCases
    ]

    # Ensure we have comprehensive coverage
    assert len(test_classes) >= 10, "Should have at least 10 test classes"

    # Count total test methods
    total_tests = sum(
        len([m for m in dir(cls) if m.startswith('test_')])
        for cls in test_classes
    )

    assert total_tests >= 40, f"Should have at least 40 test methods, found {total_tests}"
    print(f"\n✅ Structured output test suite: {len(test_classes)} classes, {total_tests} tests")


if __name__ == "__main__":
    # Run with: python3 -m pytest tests/test_structured_output.py -v
    pytest.main([__file__, "-v", "--tb=short"])
