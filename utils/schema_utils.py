#!/usr/bin/env python3
"""
JSON Schema utilities for structured output validation.

This module provides utilities for validating and working with JSON schemas
used in LM Studio's structured output feature (v0.3.32+).

Usage:
    from utils.schema_utils import validate_json_schema, SchemaValidationResult

    result = validate_json_schema(my_schema)
    if result.valid:
        print("Schema is valid!")
    else:
        print(f"Errors: {result.errors}")
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from config.constants import (
    MAX_JSON_SCHEMA_DEPTH,
    MAX_JSON_SCHEMA_PROPERTIES,
    STRUCTURED_OUTPUT_TYPES
)


@dataclass
class SchemaValidationResult:
    """Result of JSON schema validation.

    Attributes:
        valid: Whether the schema is valid
        errors: List of validation error messages
        warnings: List of non-critical warnings
        corrected_schema: Optional corrected version of the schema
    """
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    corrected_schema: Optional[Dict[str, Any]] = None


def validate_json_schema(schema: Dict[str, Any]) -> SchemaValidationResult:
    """Validate a JSON schema for use with LM Studio structured output.

    Performs comprehensive validation including:
    - Required fields check (type, properties for objects)
    - Depth limit check (prevents overly complex schemas)
    - Property count check (prevents overly large schemas)
    - Type validation (ensures valid JSON schema types)

    Args:
        schema: JSON schema dictionary to validate

    Returns:
        SchemaValidationResult with validation status and any errors/warnings

    Example:
        >>> schema = {
        ...     "type": "object",
        ...     "properties": {"name": {"type": "string"}},
        ...     "required": ["name"]
        ... }
        >>> result = validate_json_schema(schema)
        >>> result.valid
        True
    """
    errors: List[str] = []
    warnings: List[str] = []

    # Check if schema is a dict
    if not isinstance(schema, dict):
        return SchemaValidationResult(
            valid=False,
            errors=["Schema must be a dictionary"]
        )

    # Check for required 'type' field
    if "type" not in schema:
        errors.append("Schema must have a 'type' field")
    else:
        valid_types = ["object", "array", "string", "number", "integer", "boolean", "null"]
        if schema["type"] not in valid_types:
            errors.append(f"Invalid type '{schema['type']}'. Must be one of: {valid_types}")

    # For object types, check properties
    if schema.get("type") == "object":
        if "properties" not in schema:
            warnings.append("Object schema without 'properties' field - LLM may produce any object structure")
        else:
            props = schema["properties"]
            if not isinstance(props, dict):
                errors.append("'properties' must be a dictionary")
            elif len(props) > MAX_JSON_SCHEMA_PROPERTIES:
                errors.append(f"Too many properties ({len(props)}). Maximum: {MAX_JSON_SCHEMA_PROPERTIES}")

    # For array types, check items
    if schema.get("type") == "array":
        if "items" not in schema:
            warnings.append("Array schema without 'items' field - LLM may produce any array elements")

    # Check depth
    depth = _calculate_schema_depth(schema)
    if depth > MAX_JSON_SCHEMA_DEPTH:
        errors.append(f"Schema too deeply nested (depth: {depth}). Maximum: {MAX_JSON_SCHEMA_DEPTH}")

    # Check for common mistakes
    if "required" in schema and not isinstance(schema["required"], list):
        errors.append("'required' must be an array of property names")

    return SchemaValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )


def _calculate_schema_depth(schema: Dict[str, Any], current_depth: int = 1) -> int:
    """Calculate the maximum nesting depth of a JSON schema.

    Args:
        schema: JSON schema dictionary
        current_depth: Current depth level (used for recursion)

    Returns:
        Maximum depth of the schema
    """
    if not isinstance(schema, dict):
        return current_depth

    max_depth = current_depth

    # Check properties (for object types)
    if "properties" in schema and isinstance(schema["properties"], dict):
        for prop_schema in schema["properties"].values():
            if isinstance(prop_schema, dict):
                depth = _calculate_schema_depth(prop_schema, current_depth + 1)
                max_depth = max(max_depth, depth)

    # Check items (for array types)
    if "items" in schema and isinstance(schema["items"], dict):
        depth = _calculate_schema_depth(schema["items"], current_depth + 1)
        max_depth = max(max_depth, depth)

    # Check additionalProperties
    if "additionalProperties" in schema and isinstance(schema["additionalProperties"], dict):
        depth = _calculate_schema_depth(schema["additionalProperties"], current_depth + 1)
        max_depth = max(max_depth, depth)

    return max_depth


def build_response_format(
    schema: Dict[str, Any],
    name: str = "response",
    strict: bool = True
) -> Dict[str, Any]:
    """Build a complete response_format object for LM Studio.

    Wraps a JSON schema in the format expected by LM Studio's
    structured output feature.

    Args:
        schema: JSON schema dictionary defining the output structure
        name: Name for the schema (used for identification)
        strict: Whether to enforce strict schema compliance

    Returns:
        Complete response_format dictionary ready for API use

    Example:
        >>> schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        >>> fmt = build_response_format(schema, name="person")
        >>> fmt["type"]
        'json_schema'
        >>> fmt["json_schema"]["name"]
        'person'
    """
    return {
        "type": "json_schema",
        "json_schema": {
            "name": name,
            "strict": str(strict).lower(),
            "schema": schema
        }
    }


def validate_response_format(response_format: Dict[str, Any]) -> SchemaValidationResult:
    """Validate a complete response_format object.

    Validates the outer structure (type, json_schema wrapper) as well
    as the inner schema.

    Args:
        response_format: Complete response_format dictionary

    Returns:
        SchemaValidationResult with validation status

    Example:
        >>> rf = {"type": "json_schema", "json_schema": {"name": "test", "schema": {...}}}
        >>> result = validate_response_format(rf)
    """
    errors: List[str] = []
    warnings: List[str] = []

    if not isinstance(response_format, dict):
        return SchemaValidationResult(
            valid=False,
            errors=["response_format must be a dictionary"]
        )

    # Check type field
    if "type" not in response_format:
        errors.append("response_format must have a 'type' field")
    elif response_format["type"] not in STRUCTURED_OUTPUT_TYPES:
        errors.append(f"Invalid type '{response_format['type']}'. Must be one of: {STRUCTURED_OUTPUT_TYPES}")

    # For json_schema type, validate the schema
    if response_format.get("type") == "json_schema":
        if "json_schema" not in response_format:
            errors.append("json_schema type requires 'json_schema' field")
        else:
            json_schema = response_format["json_schema"]
            if not isinstance(json_schema, dict):
                errors.append("'json_schema' must be a dictionary")
            else:
                # Check for name
                if "name" not in json_schema:
                    warnings.append("'json_schema' should have a 'name' field for identification")

                # Check for schema
                if "schema" not in json_schema:
                    errors.append("'json_schema' must have a 'schema' field")
                else:
                    # Validate the inner schema
                    inner_result = validate_json_schema(json_schema["schema"])
                    errors.extend(inner_result.errors)
                    warnings.extend(inner_result.warnings)

    return SchemaValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )


__all__ = [
    "SchemaValidationResult",
    "validate_json_schema",
    "validate_response_format",
    "build_response_format"
]
