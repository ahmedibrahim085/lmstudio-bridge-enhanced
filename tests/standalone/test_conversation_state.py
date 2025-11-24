#!/usr/bin/env python3
"""Test conversation state with previous_response_id."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from llm.llm_client import LLMClient

def test_conversation_state():
    """Test that previous_response_id maintains conversation state."""
    print("="*80)
    print("Testing Conversation State Management")
    print("="*80)

    client = LLMClient()

    # Round 1: First message
    print("\n📍 Round 1: Ask a question")
    response1 = client.create_response(
        input_text="My favorite color is blue. Remember this.",
        previous_response_id=None
    )

    response1_id = response1.get("id")
    print(f"   Response ID: {response1_id}")
    print(f"   Output: {response1.get('output', [])}")

    # Round 2: Follow-up question (should remember)
    print("\n📍 Round 2: Follow-up question (should remember blue)")
    response2 = client.create_response(
        input_text="What is my favorite color?",
        previous_response_id=response1_id  # Link to previous!
    )

    response2_id = response2.get("id")
    print(f"   Response ID: {response2_id}")
    print(f"   Previous Response ID: {response2.get('previous_response_id')}")

    output2 = response2.get("output", [])
    text_output2 = ""
    for item in output2:
        if item.get("type") == "output_text":
            text_output2 = item.get("text", "")

    print(f"   Output: {text_output2[:200]}")

    # Check if it remembered
    if "blue" in text_output2.lower():
        print(f"   ✅ SUCCESS! LLM remembered 'blue' from previous conversation!")
    else:
        print(f"   ❌ FAIL! LLM did NOT remember 'blue'. Conversation state broken!")

    # Round 3: Test without previous_response_id (should NOT remember)
    print("\n📍 Round 3: New conversation (no previous_response_id)")
    response3 = client.create_response(
        input_text="What is my favorite color?",
        previous_response_id=None  # No link!
    )

    output3 = response3.get("output", [])
    text_output3 = ""
    for item in output3:
        if item.get("type") == "output_text":
            text_output3 = item.get("text", "")

    print(f"   Output: {text_output3[:200]}")

    if "blue" not in text_output3.lower() or "don't know" in text_output3.lower() or "didn't" in text_output3.lower():
        print(f"   ✅ CORRECT! LLM doesn't know (new conversation)")
    else:
        print(f"   ⚠️  WARNING! LLM might be guessing or cached")

    print("\n" + "="*80)
    print("Summary:")
    print(f"  Round 1 (set context): ID = {response1_id}")
    print(f"  Round 2 (with previous_id): previous_response_id = {response1_id}")
    print(f"  Round 3 (no previous_id): previous_response_id = None")
    print("\nCheck LM Studio logs:")
    print("  tail -50 ~/.lmstudio/server-logs/2025-10/2025-10-30.1.log | grep 'conversation with'")
    print("  Should show: Round 1 (1 msg), Round 2 (2-3 msgs), Round 3 (1 msg)")
    print("="*80)

if __name__ == "__main__":
    test_conversation_state()
