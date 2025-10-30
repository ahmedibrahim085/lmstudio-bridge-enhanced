#!/usr/bin/env python3
"""Test chat_completion() with multiple rounds to verify message history is sent."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from llm.llm_client import LLMClient

def test_chat_completion_multiround():
    """Test that chat_completion sends growing message history."""
    print("="*80)
    print("Testing chat_completion() with Multiple Rounds")
    print("="*80)

    client = LLMClient()

    # Start conversation
    messages = [
        {"role": "user", "content": "My favorite color is blue."}
    ]

    print("\n📍 Round 1: Initial message")
    print(f"   Messages being sent: {len(messages)}")
    print(f"   Content: {messages}")

    response1 = client.chat_completion(
        messages=messages,
        max_tokens=100
    )

    # Append assistant response
    assistant_msg = response1["choices"][0]["message"]
    messages.append({
        "role": "assistant",
        "content": assistant_msg.get("content", "")
    })

    print(f"   ✅ Response received")
    print(f"   Messages after Round 1: {len(messages)}")

    # Round 2: Follow-up question
    print("\n📍 Round 2: Follow-up question (should have 3 messages)")
    messages.append({
        "role": "user",
        "content": "What is my favorite color?"
    })

    print(f"   Messages being sent: {len(messages)}")
    print(f"   Message history:")
    for i, msg in enumerate(messages):
        content_preview = msg["content"][:50] + "..." if len(msg["content"]) > 50 else msg["content"]
        print(f"     {i+1}. {msg['role']}: {content_preview}")

    response2 = client.chat_completion(
        messages=messages,
        max_tokens=100
    )

    assistant_msg2 = response2["choices"][0]["message"]
    response_text = assistant_msg2.get("content", "")

    print(f"\n   ✅ Response received")
    print(f"   Response: {response_text[:200]}")

    # Check if it remembered
    if "blue" in response_text.lower():
        print(f"\n   ✅ SUCCESS! LLM remembered 'blue' from Round 1!")
    else:
        print(f"\n   ❌ FAIL! LLM did NOT remember 'blue'. Message history not working!")

    # Append assistant response
    messages.append({
        "role": "assistant",
        "content": response_text
    })

    # Round 3: Another follow-up
    print("\n📍 Round 3: Another follow-up (should have 5 messages)")
    messages.append({
        "role": "user",
        "content": "What else can you tell me about that color?"
    })

    print(f"   Messages being sent: {len(messages)}")
    print(f"   Message history:")
    for i, msg in enumerate(messages):
        content_preview = msg["content"][:40] + "..." if len(msg["content"]) > 40 else msg["content"]
        print(f"     {i+1}. {msg['role']}: {content_preview}")

    response3 = client.chat_completion(
        messages=messages,
        max_tokens=100
    )

    response_text3 = response3["choices"][0]["message"].get("content", "")
    print(f"\n   ✅ Response received")
    print(f"   Response: {response_text3[:200]}")

    print("\n" + "="*80)
    print("Check LM Studio logs NOW:")
    print("  tail -10 ~/.lmstudio/server-logs/2025-10/2025-10-30.1.log | grep 'conversation with'")
    print("\nExpected:")
    print("  Round 1: 'conversation with 1 messages'  (initial message)")
    print("  Round 2: 'conversation with 3 messages'  (user + assistant + user)")
    print("  Round 3: 'conversation with 5 messages'  (user + assistant + user + assistant + user)")
    print("="*80)

if __name__ == "__main__":
    test_chat_completion_multiround()
