#!/usr/bin/env python3
"""Test the fixed text_completion() method."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from llm.llm_client import LLMClient

def test_text_completion_fixed():
    """Test that text_completion now works with model parameter."""
    print("="*80)
    print("Testing Fixed text_completion() API")
    print("="*80)

    client = LLMClient()

    print(f"\n📍 Test: Text completion with model parameter")
    print(f"   Endpoint: {client.api_base}/completions")
    print(f"   Model: {client.model}")
    print(f"   Prompt: 'The capital of France is'")

    try:
        response = client.text_completion(
            prompt="The capital of France is",
            max_tokens=20
        )

        print(f"\n   ✅ SUCCESS!")
        print(f"   Response ID: {response.get('id')}")

        if 'choices' in response and len(response['choices']) > 0:
            text = response['choices'][0].get('text', '')
            print(f"   Completion: {text}")

            usage = response.get('usage', {})
            print(f"\n   Token usage:")
            print(f"      Prompt: {usage.get('prompt_tokens', 0)}")
            print(f"      Completion: {usage.get('completion_tokens', 0)}")
            print(f"      Total: {usage.get('total_tokens', 0)}")

            # Verify reasonable answer
            if "paris" in text.lower():
                print(f"\n   ✅ Reasonable completion generated!")
            else:
                print(f"\n   ℹ️  Completion may vary based on model")

        print("\n" + "="*80)
        print("✅ FIXED: /v1/completions API now working!")
        print("="*80)
        return True

    except Exception as e:
        print(f"\n   ❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_text_completion_fixed()
    sys.exit(0 if success else 1)
