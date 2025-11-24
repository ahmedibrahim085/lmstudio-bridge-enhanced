#!/usr/bin/env python3
"""
Live integration tests for v3.2.0 features.

Tests:
1. Structured Output (JSON Schema) - Phase 1
2. Vision Tools - Phase 2 (requires vision model)

Run with: python3 test_live_features.py
"""

import json
import sys
from llm.llm_client import LLMClient


def test_structured_output():
    """Test structured output with JSON schema."""
    print("\n" + "="*60)
    print("TEST 1: Structured Output (JSON Schema)")
    print("="*60)

    client = LLMClient()

    # Test 1a: Simple JSON object mode
    print("\n1a. Testing json_object mode...")
    try:
        response = client.chat_completion(
            messages=[{"role": "user", "content": "List 3 colors. Return as JSON with a 'colors' array."}],
            response_format={"type": "json_object"},
            max_tokens=200,
            temperature=0.3
        )
        content = response["choices"][0]["message"]["content"]
        print(f"Response: {content}")

        # Try to parse as JSON
        parsed = json.loads(content)
        print(f"✅ Valid JSON returned: {parsed}")
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Test 1b: JSON schema mode
    print("\n1b. Testing json_schema mode...")
    try:
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

        response = client.chat_completion(
            messages=[{"role": "user", "content": "List 3 programming languages."}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "languages",
                    "schema": schema
                }
            },
            max_tokens=200,
            temperature=0.3
        )
        content = response["choices"][0]["message"]["content"]
        print(f"Response: {content}")

        # Try to parse and validate
        parsed = json.loads(content)
        if "languages" in parsed and isinstance(parsed["languages"], list):
            print(f"✅ Schema-conforming JSON: {parsed}")
        else:
            print(f"⚠️ JSON valid but may not match schema: {parsed}")
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")


def test_vision_tools():
    """Test vision tools (requires vision-capable model)."""
    print("\n" + "="*60)
    print("TEST 2: Vision Tools")
    print("="*60)

    # Check for a test image
    import os
    test_images = [
        "/tmp/test_image.png",
        "/tmp/test_image.jpg",
        os.path.expanduser("~/Desktop/test.png"),
        os.path.expanduser("~/Pictures/test.jpg"),
    ]

    test_image = None
    for img in test_images:
        if os.path.exists(img):
            test_image = img
            break

    if not test_image:
        print("\n⚠️ No test image found. Creating a simple test...")
        print("To test vision, provide an image at /tmp/test_image.png")

        # Test the image utilities at least
        print("\n2a. Testing image utilities...")
        from utils.image_utils import detect_input_type, process_image_input, ImageInputType

        # Test URL detection
        url = "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a7/Camponotus_flavomarginatus_ant.jpg/320px-Camponotus_flavomarginatus_ant.jpg"
        input_type = detect_input_type(url)
        print(f"URL detection: {url[:50]}... -> {input_type.value}")

        if input_type == ImageInputType.URL:
            print("✅ URL detection working")
        else:
            print("❌ URL detection failed")

        # Test file path detection
        path = "/path/to/image.png"
        input_type = detect_input_type(path)
        print(f"Path detection: {path} -> {input_type.value}")

        if input_type == ImageInputType.FILE_PATH:
            print("✅ Path detection working")
        else:
            print("❌ Path detection failed")

        # Test vision completion with URL (may fail if model doesn't support vision)
        print("\n2b. Testing vision API call with URL...")
        client = LLMClient()

        try:
            response = client.vision_completion(
                prompt="Describe what you see in this image briefly.",
                images=url,
                max_tokens=200
            )
            content = response["choices"][0]["message"]["content"]
            print(f"Response: {content[:200]}...")
            print("✅ Vision API call succeeded")
        except ValueError as e:
            print(f"❌ Image processing error: {e}")
        except Exception as e:
            error_msg = str(e)
            if "vision" in error_msg.lower() or "image" in error_msg.lower() or "multimodal" in error_msg.lower():
                print(f"⚠️ Model may not support vision: {e}")
            else:
                print(f"❌ Error: {e}")
    else:
        print(f"\nUsing test image: {test_image}")
        from tools.vision import VisionTools
        import asyncio

        tools = VisionTools()

        print("\n2a. Testing analyze_image...")
        result = asyncio.run(tools.analyze_image(test_image))
        print(f"Result: {result[:300]}...")

        print("\n2b. Testing describe_image...")
        result = asyncio.run(tools.describe_image(test_image, style="brief"))
        print(f"Result: {result[:300]}...")


def test_schema_validation():
    """Test JSON schema validation tool."""
    print("\n" + "="*60)
    print("TEST 3: Schema Validation Utility")
    print("="*60)

    from utils.schema_utils import validate_json_schema, build_response_format

    # Test valid schema
    print("\n3a. Testing valid schema...")
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"}
        },
        "required": ["name"]
    }
    result = validate_json_schema(schema)
    print(f"Valid: {result.valid}, Errors: {result.errors}, Warnings: {result.warnings}")
    if result.valid:
        print("✅ Valid schema accepted")
    else:
        print("❌ Valid schema rejected")

    # Test invalid schema
    print("\n3b. Testing invalid schema (missing type)...")
    invalid_schema = {"properties": {"x": {"type": "string"}}}
    result = validate_json_schema(invalid_schema)
    print(f"Valid: {result.valid}, Errors: {result.errors}")
    if not result.valid:
        print("✅ Invalid schema rejected correctly")
    else:
        print("❌ Invalid schema was accepted")

    # Test build_response_format
    print("\n3c. Testing build_response_format helper...")
    fmt = build_response_format(schema, name="person")
    print(f"Built format: {json.dumps(fmt, indent=2)}")
    if fmt["type"] == "json_schema" and "json_schema" in fmt:
        print("✅ Response format built correctly")
    else:
        print("❌ Response format structure incorrect")


def main():
    print("="*60)
    print("LM Studio Bridge v3.2.0 Live Feature Tests")
    print("="*60)

    # Run tests
    test_schema_validation()  # No LLM needed
    test_structured_output()  # Needs LLM
    test_vision_tools()       # Needs vision model

    print("\n" + "="*60)
    print("Tests Complete!")
    print("="*60)


if __name__ == "__main__":
    main()
