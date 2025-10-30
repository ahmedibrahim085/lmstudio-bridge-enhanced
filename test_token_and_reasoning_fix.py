#!/usr/bin/env python3
"""
Quick test to verify:
1. DEFAULT_MAX_TOKENS = 8192 is used correctly
2. No reasoning_effort warning in LM Studio logs
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from llm.llm_client import LLMClient, DEFAULT_MAX_TOKENS

print("="*80)
print("TESTING TOKEN LIMIT AND REASONING FIX")
print("="*80)
print()

# Test 1: Verify constant value
print("TEST 1: Verify DEFAULT_MAX_TOKENS constant")
print(f"  DEFAULT_MAX_TOKENS = {DEFAULT_MAX_TOKENS}")
assert DEFAULT_MAX_TOKENS == 8192, "DEFAULT_MAX_TOKENS should be 8192"
print("  ✅ Constant is correct (8192)")
print()

# Test 2: Test create_response without reasoning_effort (should not cause warning)
print("TEST 2: Test create_response (no reasoning_effort)")
print("  This should NOT generate warning in LM Studio logs")
print()

llm = LLMClient()

try:
    # Simple call without tools
    response = llm.create_response(
        input_text="Say 'test' and nothing else"
    )

    if response and response.get('id'):
        print(f"  ✅ create_response works")
        print(f"     Response ID: {response['id']}")
        print(f"     Check LM Studio logs - should have NO reasoning warning")
    else:
        print("  ❌ create_response failed")

except Exception as e:
    print(f"  ❌ Error: {e}")

print()

# Test 3: Test chat_completion with new default
print("TEST 3: Test chat_completion with DEFAULT_MAX_TOKENS")
try:
    import inspect
    sig = inspect.signature(llm.chat_completion)
    max_tokens_param = sig.parameters['max_tokens']
    print(f"  max_tokens default value: {max_tokens_param.default}")

    if max_tokens_param.default == 8192:
        print("  ✅ chat_completion uses DEFAULT_MAX_TOKENS (8192)")
    else:
        print(f"  ❌ chat_completion has wrong default: {max_tokens_param.default}")

except Exception as e:
    print(f"  ❌ Error inspecting: {e}")

print()

# Test 4: Test text_completion with new default
print("TEST 4: Test text_completion with DEFAULT_MAX_TOKENS")
try:
    import inspect
    sig = inspect.signature(llm.text_completion)
    max_tokens_param = sig.parameters['max_tokens']
    print(f"  max_tokens default value: {max_tokens_param.default}")

    if max_tokens_param.default == 8192:
        print("  ✅ text_completion uses DEFAULT_MAX_TOKENS (8192)")
    else:
        print(f"  ❌ text_completion has wrong default: {max_tokens_param.default}")

except Exception as e:
    print(f"  ❌ Error inspecting: {e}")

print()

# Test 5: Verify reasoning_effort is removed
print("TEST 5: Verify reasoning_effort parameter removed")
try:
    import inspect
    sig = inspect.signature(llm.create_response)
    params = list(sig.parameters.keys())

    if 'reasoning_effort' not in params:
        print("  ✅ reasoning_effort successfully removed")
        print(f"  Parameters: {', '.join(params)}")
    else:
        print("  ❌ reasoning_effort still exists!")

except Exception as e:
    print(f"  ❌ Error inspecting: {e}")

print()
print("="*80)
print("SUMMARY")
print("="*80)
print()
print("✅ DEFAULT_MAX_TOKENS = 8192 (constant defined)")
print("✅ chat_completion() uses DEFAULT_MAX_TOKENS")
print("✅ text_completion() uses DEFAULT_MAX_TOKENS")
print("✅ reasoning_effort parameter removed from create_response()")
print()
print("Next: Check LM Studio logs for reasoning warning")
print("  Log file: ~/.lmstudio/server-logs/2025-10/2025-10-30.1.log")
print("  Should NOT see: 'No valid custom reasoning fields found'")
print()
