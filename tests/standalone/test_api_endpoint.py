#!/usr/bin/env python3
"""Test which API endpoint is actually being called."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from llm.llm_client import LLMClient, DEFAULT_MAX_TOKENS

def test_which_endpoint():
    """Test to see which endpoint is called."""
    print("="*80)
    print("Testing API Endpoint Usage")
    print("="*80)

    client = LLMClient()

    # Test 1: create_response (should use /v1/responses)
    print("\n1. Testing create_response():")
    print(f"   API Base: {client.api_base}")
    print(f"   Expected endpoint: {client.api_base}/responses")

    try:
        response = client.create_response(
            input_text="Say 'test' and nothing else",
            tools=None,
            previous_response_id=None
        )
        print(f"   ✅ Success! Response ID: {response.get('id')}")
        print(f"   Response keys: {list(response.keys())}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 2: chat_completion (should use /v1/chat/completions)
    print("\n2. Testing chat_completion():")
    print(f"   Expected endpoint: {client.api_base}/chat/completions")

    try:
        response = client.chat_completion(
            messages=[{"role": "user", "content": "Say 'test2' and nothing else"}],
            max_tokens=DEFAULT_MAX_TOKENS
        )
        print(f"   ✅ Success! Response keys: {list(response.keys())}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    print("\n" + "="*80)
    print("Check LM Studio logs to see which endpoints were actually called:")
    print("tail -10 ~/.lmstudio/server-logs/2025-10/2025-10-30.1.log")
    print("="*80)

if __name__ == "__main__":
    test_which_endpoint()
