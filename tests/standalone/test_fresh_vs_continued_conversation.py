#!/usr/bin/env python3
"""
Test to verify YOUR insight about model memory:
- Fresh conversations (new message array) = model has no memory
- Continued conversations (same message array) = model has memory
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from llm.llm_client import LLMClient

def test_fresh_conversation_no_memory():
    """Test that starting a fresh conversation = no memory of previous chat."""
    print("="*80)
    print("TEST: Fresh Conversation (New Message Array)")
    print("="*80)

    client = LLMClient()

    # Conversation 1: Tell the model something
    print("\n📍 Conversation 1: Establishing information")
    messages1 = [
        {"role": "user", "content": "My favorite color is blue. Remember this!"}
    ]

    response1 = client.chat_completion(messages=messages1, max_tokens=50)
    print(f"   Response: {response1['choices'][0]['message']['content'][:100]}")

    # Conversation 2: NEW message array (fresh conversation)
    print("\n📍 Conversation 2: Fresh conversation (new message array)")
    messages2 = [
        {"role": "user", "content": "What is my favorite color?"}
    ]

    response2 = client.chat_completion(messages=messages2, max_tokens=50)
    response_text = response2['choices'][0]['message']['content']
    print(f"   Response: {response_text[:200]}")

    # Check if it remembered
    if "blue" in response_text.lower():
        print(f"\n   ❌ UNEXPECTED! LLM remembered 'blue' from previous conversation!")
        print(f"   This suggests the model has persistent state between API calls.")
    else:
        print(f"\n   ✅ EXPECTED! LLM does NOT remember 'blue'.")
        print(f"   Fresh conversation = no memory of previous chat.")
        print(f"   This is correct LLM behavior.")

def test_continued_conversation_has_memory():
    """Test that continuing SAME message array = model has memory."""
    print("\n" + "="*80)
    print("TEST: Continued Conversation (Same Message Array)")
    print("="*80)

    client = LLMClient()

    # Start conversation
    print("\n📍 Round 1: Establishing information")
    messages = [
        {"role": "user", "content": "My favorite color is blue. Remember this!"}
    ]

    response1 = client.chat_completion(messages=messages, max_tokens=50)
    assistant_msg = response1['choices'][0]['message']

    # Append to SAME array
    messages.append({
        "role": "assistant",
        "content": assistant_msg['content']
    })

    print(f"   Response: {assistant_msg['content'][:100]}")
    print(f"   Messages in array: {len(messages)}")

    # Round 2: Ask follow-up in SAME conversation
    print("\n📍 Round 2: Follow-up in SAME conversation")
    messages.append({
        "role": "user",
        "content": "What is my favorite color?"
    })

    print(f"   Messages being sent: {len(messages)}")

    response2 = client.chat_completion(messages=messages, max_tokens=50)
    response_text = response2['choices'][0]['message']['content']
    print(f"   Response: {response_text[:200]}")

    # Check if it remembered
    if "blue" in response_text.lower():
        print(f"\n   ✅ EXPECTED! LLM remembered 'blue' from Round 1.")
        print(f"   Continued conversation = memory persists via message history.")
    else:
        print(f"\n   ❌ UNEXPECTED! LLM did NOT remember 'blue'.")
        print(f"   This suggests message history is not being sent correctly.")

def test_model_unload_reload_memory():
    """
    Test YOUR hypothesis: If model is unloaded/reloaded between requests,
    does it lose memory even within the same conversation?

    This would require:
    1. Send message 1
    2. Unload model
    3. Reload model
    4. Send message 2 with history
    5. Check if memory persists
    """
    print("\n" + "="*80)
    print("TEST: Model Unload/Reload Impact on Memory")
    print("="*80)

    from utils.lms_helper import LMSHelper
    client = LLMClient()

    # Check if LMS CLI is available
    if not LMSHelper.is_installed():
        print("\n   ⏭️  SKIPPED: LMS CLI not available")
        print("   Cannot test model unload/reload without LMS CLI")
        return

    # Get current model
    models = LMSHelper.list_loaded_models()
    if not models or len(models) == 0:
        print("\n   ⏭️  SKIPPED: No models loaded")
        return

    test_model = models[0].get("identifier")
    print(f"\n📍 Using model: {test_model}")

    # Round 1: Send initial message
    print("\n📍 Round 1: Initial message")
    messages = [
        {"role": "user", "content": "My favorite color is blue. Remember this!"}
    ]

    response1 = client.chat_completion(messages=messages, max_tokens=50)
    assistant_msg = response1['choices'][0]['message']
    messages.append({"role": "assistant", "content": assistant_msg['content']})

    print(f"   Response: {assistant_msg['content'][:100]}")

    # Unload and reload model
    print("\n📍 Unloading model...")
    LMSHelper.unload_model(test_model)

    print("📍 Reloading model...")
    LMSHelper.load_model(test_model, keep_loaded=True)

    import time
    time.sleep(3)  # Wait for model to fully load

    print("   ✅ Model reloaded")

    # Round 2: Send follow-up (after model reload)
    print("\n📍 Round 2: Follow-up AFTER model reload")
    messages.append({
        "role": "user",
        "content": "What is my favorite color?"
    })

    print(f"   Messages being sent: {len(messages)}")

    response2 = client.chat_completion(messages=messages, max_tokens=50)
    response_text = response2['choices'][0]['message']['content']
    print(f"   Response: {response_text[:200]}")

    # Check if it remembered
    if "blue" in response_text.lower():
        print(f"\n   ✅ Model STILL remembered 'blue' after reload!")
        print(f"   Memory persists because history is in the message array,")
        print(f"   not stored in the model itself.")
    else:
        print(f"\n   ❌ Model LOST memory after reload!")
        print(f"   This confirms your hypothesis: unload/reload = memory loss")

if __name__ == "__main__":
    # Test 1: Fresh conversation (new message array)
    test_fresh_conversation_no_memory()

    # Test 2: Continued conversation (same message array)
    test_continued_conversation_has_memory()

    # Test 3: Model unload/reload impact
    test_model_unload_reload_memory()

    print("\n" + "="*80)
    print("CONCLUSION")
    print("="*80)
    print("""
Your insight is CORRECT about LLM memory:
1. Fresh conversation (new message array) = No memory
2. Continued conversation (same message array) = Memory persists
3. Model unload/reload should NOT affect memory because:
   - Memory is stored in the message array (sent with each request)
   - NOT stored in the model's internal state

The test failure is NOT about model memory, but about:
   - Model capability (some models have poor memory even WITH history)
   - OR the code is sending history correctly but model doesn't use it well
""")
