#!/usr/bin/env python3
"""Debug conversation state issue."""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from llm.llm_client import LLMClient

def test_conversation_debug():
    """Debug why Round 2 returns empty output."""
    print("="*80)
    print("Debugging Conversation State")
    print("="*80)

    client = LLMClient()

    # Round 1
    print("\n📍 Round 1: Set context")
    response1 = client.create_response(
        input_text="My favorite color is blue.",
        previous_response_id=None
    )
    print(f"Response 1 ID: {response1.get('id')}")
    print(f"Response 1 keys: {list(response1.keys())}")
    print(f"Response 1 status: {response1.get('status')}")
    print(f"Response 1 output length: {len(response1.get('output', []))}")

    # Round 2
    print("\n📍 Round 2: Follow-up with previous_id")
    response2 = client.create_response(
        input_text="What is my favorite color?",
        previous_response_id=response1.get('id')
    )

    print(f"\nResponse 2 FULL JSON:")
    print(json.dumps(response2, indent=2))

    print(f"\nResponse 2 ID: {response2.get('id')}")
    print(f"Response 2 previous_response_id: {response2.get('previous_response_id')}")
    print(f"Response 2 status: {response2.get('status')}")
    print(f"Response 2 output: {response2.get('output')}")
    print(f"Response 2 output length: {len(response2.get('output', []))}")

    # Check if output is actually empty or just not parsed correctly
    if response2.get('output'):
        print(f"\nOutput items:")
        for i, item in enumerate(response2['output']):
            print(f"  Item {i}: type={item.get('type')}, keys={list(item.keys())}")
            if item.get('type') == 'output_text':
                print(f"    Text: {item.get('text', '')[:100]}")

if __name__ == "__main__":
    test_conversation_debug()
