#!/usr/bin/env python3
"""
Test if LM Studio's /v1/responses endpoint supports function calling (tools).

This is a CRITICAL test that could change our entire optimization strategy!
"""

import requests
import json

LMSTUDIO_API_BASE = "http://localhost:1234/v1"


def test_responses_endpoint_basic():
    """Test basic /v1/responses endpoint (should work)."""
    print("="*80)
    print("TEST 1: Basic /v1/responses (no tools)")
    print("="*80)

    payload = {
        "input": "What is 2+2?",
        "model": "default",
        "stream": False
    }

    print(f"Request: {json.dumps(payload, indent=2)}")
    print()

    try:
        response = requests.post(
            f"{LMSTUDIO_API_BASE}/responses",
            json=payload,
            timeout=30
        )

        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Response: {json.dumps(result, indent=2)}")
            return result
        else:
            print(f"Error: {response.text}")
            return None
    except Exception as e:
        print(f"Exception: {e}")
        return None


def test_responses_endpoint_with_tools():
    """Test /v1/responses with tools parameter (the big question!)."""
    print("\n" + "="*80)
    print("TEST 2: /v1/responses WITH tools parameter")
    print("="*80)
    print("This is the CRITICAL test!")
    print()

    # Simple tool schema
    tools = [
        {
            "type": "function",
            "function": {
                "name": "calculate",
                "description": "Perform a calculation",
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

    payload = {
        "input": "Calculate 2+2 using the calculate tool",
        "model": "default",
        "stream": False,
        "tools": tools,  # ← THE KEY QUESTION: Does this work?
        "tool_choice": "auto"
    }

    print(f"Request: {json.dumps(payload, indent=2)}")
    print()

    try:
        response = requests.post(
            f"{LMSTUDIO_API_BASE}/responses",
            json=payload,
            timeout=30
        )

        print(f"Status: {response.status_code}")
        print()

        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS! /v1/responses SUPPORTS tools!")
            print()
            print(f"Response: {json.dumps(result, indent=2)}")
            print()

            # Check if tool calls are in response
            if "tool_calls" in json.dumps(result):
                print("🎉 TOOL CALLS FOUND IN RESPONSE!")
                print("This means we can use /v1/responses for autonomous execution!")
                return True
            else:
                print("⚠️  No tool_calls in response")
                print("LM Studio might accept tools parameter but not use it")
                return False
        else:
            print("❌ FAILED! /v1/responses does NOT support tools")
            print()
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False


def test_responses_endpoint_stateful():
    """Test stateful conversation with /v1/responses."""
    print("\n" + "="*80)
    print("TEST 3: Stateful conversation (reference previous response)")
    print("="*80)

    # First message
    print("Message 1: What is the capital of France?")
    payload1 = {
        "input": "What is the capital of France?",
        "model": "default",
        "stream": False
    }

    try:
        response1 = requests.post(
            f"{LMSTUDIO_API_BASE}/responses",
            json=payload1,
            timeout=30
        )

        if response1.status_code != 200:
            print(f"Failed: {response1.text}")
            return

        result1 = response1.json()
        response_id = result1.get("id")
        print(f"Response 1 ID: {response_id}")
        print(f"Response 1 content: {result1}")
        print()

        # Second message referencing first
        print("Message 2: What is its population? (referencing previous)")
        payload2 = {
            "input": "What is its population?",
            "previous_response_id": response_id,  # ← Stateful reference!
            "model": "default",
            "stream": False
        }

        response2 = requests.post(
            f"{LMSTUDIO_API_BASE}/responses",
            json=payload2,
            timeout=30
        )

        if response2.status_code == 200:
            result2 = response2.json()
            print("✅ Stateful conversation works!")
            print(f"Response 2: {result2}")
        else:
            print(f"Failed: {response2.text}")

    except Exception as e:
        print(f"Exception: {e}")


def check_lm_studio_running():
    """Check if LM Studio is running."""
    print("="*80)
    print("Checking if LM Studio is running...")
    print("="*80)
    print()

    try:
        response = requests.get(f"{LMSTUDIO_API_BASE}/models", timeout=5)
        if response.status_code == 200:
            models = response.json().get("data", [])
            print(f"✅ LM Studio is running")
            print(f"Models loaded: {len(models)}")
            if models:
                print(f"Current model: {models[0].get('id', 'unknown')}")
            print()
            return True
        else:
            print(f"❌ LM Studio API returned: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ LM Studio is NOT running: {e}")
        print("Please start LM Studio and load a model")
        return False


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("LM STUDIO /v1/responses + TOOLS TEST")
    print("="*80)
    print("Testing if /v1/responses supports function calling (tools parameter)")
    print()

    # Check if LM Studio is running
    if not check_lm_studio_running():
        return

    # Test 1: Basic /v1/responses (should work)
    result1 = test_responses_endpoint_basic()

    # Test 2: /v1/responses with tools (THE BIG QUESTION!)
    supports_tools = test_responses_endpoint_with_tools()

    # Test 3: Stateful conversation
    test_responses_endpoint_stateful()

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print()

    if supports_tools:
        print("🎉 BREAKTHROUGH! /v1/responses SUPPORTS tools!")
        print()
        print("This means:")
        print("✅ We can use stateful API for autonomous execution")
        print("✅ No need to send full message history every round")
        print("✅ Massive token savings")
        print("✅ Faster responses")
        print("✅ Better than context window sliding!")
        print()
        print("RECOMMENDATION: Switch to /v1/responses for autonomous execution")
    else:
        print("❌ /v1/responses does NOT support tools")
        print()
        print("This means:")
        print("✅ Context window sliding is the right solution")
        print("✅ Can't use stateful API for function calling")
        print("✅ Must use /v1/chat/completions with message trimming")
        print()
        print("RECOMMENDATION: Implement context window sliding as planned")

    print()
    print("="*80)


if __name__ == "__main__":
    main()
