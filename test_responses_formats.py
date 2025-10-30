#!/usr/bin/env python3
"""
Test different tool formats with /v1/responses to find what actually works.
"""

import requests
import json

LMSTUDIO_API_BASE = "http://localhost:1234/v1"


def test_format_1_standard_openai():
    """Test Format 1: Standard OpenAI function format."""
    print("="*80)
    print("FORMAT 1: Standard OpenAI function format")
    print("="*80)

    payload = {
        "input": "Calculate 2+2",
        "model": "default",
        "tools": [{
            "type": "function",
            "function": {
                "name": "calculate",
                "description": "Perform calculation",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "expression": {"type": "string"}
                    }
                }
            }
        }]
    }

    print(json.dumps(payload, indent=2))
    print()

    try:
        response = requests.post(
            f"{LMSTUDIO_API_BASE}/responses",
            json=payload,
            timeout=30
        )

        if response.status_code == 200:
            print("✅ SUCCESS!")
            print(json.dumps(response.json(), indent=2))
            return True
        else:
            print(f"❌ Failed: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False


def test_format_2_alternative():
    """Test Format 2: Alternative format with name at top level."""
    print("\n" + "="*80)
    print("FORMAT 2: Alternative format (name at top level)")
    print("="*80)

    payload = {
        "input": "Calculate 2+2",
        "model": "default",
        "tools": [{
            "type": "function",
            "name": "calculate",  # ← At top level
            "description": "Perform calculation",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string"}
                }
            }
        }]
    }

    print(json.dumps(payload, indent=2))
    print()

    try:
        response = requests.post(
            f"{LMSTUDIO_API_BASE}/responses",
            json=payload,
            timeout=30
        )

        if response.status_code == 200:
            print("✅ SUCCESS!")
            print(json.dumps(response.json(), indent=2))
            return True
        else:
            print(f"❌ Failed: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False


def test_format_3_mcp_remote():
    """Test Format 3: Remote MCP format (requires remote MCP enabled)."""
    print("\n" + "="*80)
    print("FORMAT 3: Remote MCP format")
    print("="*80)

    payload = {
        "input": "Test query",
        "model": "default",
        "tools": [{
            "type": "mcp",
            "server_label": "test",
            "server_url": "http://localhost:3000",
            "allowed_tools": ["test_tool"]
        }]
    }

    print(json.dumps(payload, indent=2))
    print()
    print("Note: This may fail if remote MCP is not enabled in LM Studio settings")
    print()

    try:
        response = requests.post(
            f"{LMSTUDIO_API_BASE}/responses",
            json=payload,
            timeout=30
        )

        if response.status_code == 200:
            print("✅ SUCCESS!")
            print(json.dumps(response.json(), indent=2))
            return True
        else:
            print(f"❌ Failed: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False


def compare_with_chat_completions():
    """Compare with /v1/chat/completions (known to work)."""
    print("\n" + "="*80)
    print("COMPARISON: /v1/chat/completions (known to work)")
    print("="*80)

    payload = {
        "messages": [{"role": "user", "content": "Calculate 2+2"}],
        "model": "default",
        "tools": [{
            "type": "function",
            "function": {
                "name": "calculate",
                "description": "Perform calculation",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "expression": {"type": "string"}
                    }
                }
            }
        }],
        "tool_choice": "auto"
    }

    print(json.dumps(payload, indent=2))
    print()

    try:
        response = requests.post(
            f"{LMSTUDIO_API_BASE}/chat/completions",
            json=payload,
            timeout=30
        )

        if response.status_code == 200:
            print("✅ /v1/chat/completions works!")
            result = response.json()
            print(f"Tool calls: {result.get('choices', [{}])[0].get('message', {}).get('tool_calls', [])}")
            return True
        else:
            print(f"❌ Failed: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False


def main():
    """Test all formats."""
    print("\n" + "="*80)
    print("TESTING ALL /v1/responses TOOL FORMATS")
    print("="*80)
    print()

    # Check LM Studio running
    try:
        response = requests.get(f"{LMSTUDIO_API_BASE}/models", timeout=5)
        if response.status_code != 200:
            print("❌ LM Studio not running")
            return
        print("✅ LM Studio is running\n")
    except:
        print("❌ LM Studio not running")
        return

    # Test all formats
    results = {
        "format1": test_format_1_standard_openai(),
        "format2": test_format_2_alternative(),
        "format3": test_format_3_mcp_remote(),
        "chat_completions": compare_with_chat_completions()
    }

    # Summary
    print("\n" + "="*80)
    print("RESULTS SUMMARY")
    print("="*80)
    print()
    print(f"Format 1 (Standard OpenAI): {'✅ WORKS' if results['format1'] else '❌ FAILED'}")
    print(f"Format 2 (Alternative): {'✅ WORKS' if results['format2'] else '❌ FAILED'}")
    print(f"Format 3 (Remote MCP): {'✅ WORKS' if results['format3'] else '❌ FAILED'}")
    print(f"/v1/chat/completions: {'✅ WORKS' if results['chat_completions'] else '❌ FAILED'}")
    print()

    if results['format1'] or results['format2']:
        print("🎉 /v1/responses DOES support custom functions!")
        print("RECOMMENDATION: Use /v1/responses for autonomous execution")
    elif results['format3']:
        print("⚠️  /v1/responses only supports remote MCP, not custom functions")
        print("RECOMMENDATION: Stick with /v1/chat/completions + context sliding")
    else:
        print("❌ /v1/responses does NOT support function calling")
        print("RECOMMENDATION: Use /v1/chat/completions + context sliding")

    print()


if __name__ == "__main__":
    main()
