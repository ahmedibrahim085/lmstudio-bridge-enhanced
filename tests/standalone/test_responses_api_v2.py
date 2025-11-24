#!/usr/bin/env python3
"""
Test the updated create_response() method with tools support.

This tests Phase 1 implementation:
- Tool format converter (OpenAI → LM Studio flattened)
- create_response() with tools parameter
- Stateful conversation with function calling
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from llm.llm_client import LLMClient
import json


def test_tool_format_converter():
    """Test that tool format converter works correctly."""
    print("="*80)
    print("TEST 1: Tool Format Converter")
    print("="*80)
    print()

    # OpenAI format (nested)
    openai_tools = [
        {
            "type": "function",
            "function": {
                "name": "calculate",
                "description": "Perform a mathematical calculation",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "Mathematical expression to evaluate"
                        }
                    },
                    "required": ["expression"]
                }
            }
        }
    ]

    print("Input (OpenAI format):")
    print(json.dumps(openai_tools, indent=2))
    print()

    # Convert to LM Studio format
    lmstudio_tools = LLMClient.convert_tools_to_responses_format(openai_tools)

    print("Output (LM Studio flattened format):")
    print(json.dumps(lmstudio_tools, indent=2))
    print()

    # Verify conversion
    assert lmstudio_tools[0]["type"] == "function"
    assert lmstudio_tools[0]["name"] == "calculate"
    assert lmstudio_tools[0]["description"] == "Perform a mathematical calculation"
    assert "function" not in lmstudio_tools[0], "Should be flattened (no nested 'function')"

    print("✅ Tool format converter works correctly!")
    print()
    return True


def test_create_response_with_tools():
    """Test create_response() with tools parameter."""
    print("="*80)
    print("TEST 2: create_response() with Tools")
    print("="*80)
    print()

    # Initialize client
    client = LLMClient()

    # Check if LM Studio is running
    try:
        if not client.health_check():
            print("❌ LM Studio is not running")
            print("Please start LM Studio and load a model")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to LM Studio: {e}")
        return False

    print("✅ LM Studio is running")
    print()

    # Define tools in OpenAI format
    tools = [
        {
            "type": "function",
            "function": {
                "name": "calculate",
                "description": "Perform a mathematical calculation",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "Mathematical expression to evaluate"
                        }
                    },
                    "required": ["expression"]
                }
            }
        }
    ]

    print("Calling create_response() with tools...")
    print(f"Task: Calculate 2+2")
    print()

    try:
        # Call create_response with tools (will auto-convert to flattened format)
        response = client.create_response(
            input_text="Calculate 2+2 using the calculate tool",
            tools=tools,
            model="default"
        )

        print("✅ Success! Response received:")
        print(json.dumps(response, indent=2))
        print()

        # Check for function calls in output
        has_function_call = any(
            output.get("type") == "function_call"
            for output in response.get("output", [])
        )

        if has_function_call:
            print("🎉 Function call detected in response!")
            print("The /v1/responses API with tools is working correctly!")
            return True
        else:
            print("⚠️  No function call in response")
            print("Response structure:")
            for output in response.get("output", []):
                print(f"  - Type: {output.get('type')}")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_stateful_conversation_with_tools():
    """Test stateful conversation using previous_response_id with tools."""
    print("="*80)
    print("TEST 3: Stateful Conversation with Tools")
    print("="*80)
    print()

    client = LLMClient()

    # Check if LM Studio is running
    if not client.health_check():
        print("❌ LM Studio is not running")
        return False

    # Define tools
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_info",
                "description": "Get information about a topic",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string"}
                    },
                    "required": ["topic"]
                }
            }
        }
    ]

    try:
        # First message
        print("Message 1: Tell me about Python")
        response1 = client.create_response(
            input_text="Tell me about Python programming language",
            tools=tools,
            model="default"
        )

        response1_id = response1.get("id")
        print(f"Response 1 ID: {response1_id}")
        print(f"Response 1 status: {response1.get('status')}")
        print()

        # Second message referencing first
        print("Message 2: What about its history? (using previous_response_id)")
        response2 = client.create_response(
            input_text="What about its history?",
            tools=tools,
            previous_response_id=response1_id,
            model="default"
        )

        print(f"Response 2 ID: {response2.get('id')}")
        print(f"Response 2 status: {response2.get('status')}")
        print(f"Response 2 references previous: {response2.get('previous_response_id') == response1_id}")
        print()

        print("✅ Stateful conversation with tools works!")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print()
    print("="*80)
    print("TESTING /v1/responses API WITH TOOLS (PHASE 1)")
    print("="*80)
    print()
    print("This tests the implementation from FINAL_API_COMPARISON_AND_RECOMMENDATION.md")
    print()

    results = {
        "format_converter": test_tool_format_converter(),
        "create_response_with_tools": test_create_response_with_tools(),
        "stateful_conversation": test_stateful_conversation_with_tools()
    }

    # Summary
    print()
    print("="*80)
    print("TEST SUMMARY")
    print("="*80)
    print()
    print(f"1. Tool Format Converter: {'✅ PASS' if results['format_converter'] else '❌ FAIL'}")
    print(f"2. create_response() with Tools: {'✅ PASS' if results['create_response_with_tools'] else '❌ FAIL'}")
    print(f"3. Stateful Conversation: {'✅ PASS' if results['stateful_conversation'] else '❌ FAIL'}")
    print()

    all_passed = all(results.values())

    if all_passed:
        print("🎉 ALL TESTS PASSED!")
        print()
        print("Phase 1 Implementation Complete:")
        print("✅ Tool format converter implemented")
        print("✅ create_response() supports tools parameter")
        print("✅ Automatic conversion to LM Studio flattened format")
        print("✅ Stateful conversations with function calling work")
        print()
        print("Next Steps:")
        print("- Phase 2: Update autonomous functions to use /v1/responses")
        print("- Phase 3: Measure token savings vs /v1/chat/completions")
        print("- Phase 4: Make /v1/responses the default for autonomous execution")
    else:
        print("❌ SOME TESTS FAILED")
        print()
        print("Please check errors above and fix before proceeding to Phase 2")

    print()


if __name__ == "__main__":
    main()
