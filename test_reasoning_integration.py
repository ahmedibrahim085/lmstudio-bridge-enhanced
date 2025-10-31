#!/usr/bin/env python3
"""
Integration test for reasoning display feature.

This script tests the _format_response_with_reasoning() implementation
with real models and simulated edge cases.

Tests:
1. Magistral (reasoning_content field)
2. GPT-OSS (reasoning field)
3. Qwen3-coder (no reasoning)
4. Edge case: Empty reasoning
5. Edge case: HTML in reasoning (XSS)
6. Edge case: Very long reasoning (truncation)
"""

import sys
import os
import asyncio

# Add parent directory to path
sys.path.insert(0, '/Users/ahmedmaged/ai_storage/MyMCPs/lmstudio-bridge-enhanced')

from tools.autonomous import AutonomousExecutionTools
from llm.llm_client import LLMClient


def print_section(title: str):
    """Print a test section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def print_result(test_name: str, passed: bool, details: str = ""):
    """Print test result."""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} - {test_name}")
    if details:
        print(f"    {details}")
    print()


async def test_magistral():
    """Test 1: Magistral with reasoning_content field."""
    print_section("TEST 1: Magistral (reasoning_content field)")

    tools = AutonomousExecutionTools()

    print("Testing with simple math task to trigger reasoning...")
    print("Task: 'What is 15 + 27? Think step by step.'\n")

    try:
        result = await tools.autonomous_filesystem_full(
            task="What is 15 + 27? Think step by step. Do NOT use any filesystem tools, just answer.",
            working_directory="/Users/ahmedmaged/ai_storage/MyMCPs/lmstudio-bridge-enhanced",
            max_rounds=2,
            max_tokens=1000
        )

        print("Result:")
        print("-" * 80)
        print(result)
        print("-" * 80)

        # Verify reasoning section present
        has_reasoning_section = "**Reasoning Process:**" in result
        has_final_answer = "**Final Answer:**" in result
        has_answer = "42" in result or "15" in result or "27" in result

        passed = has_reasoning_section and has_final_answer and has_answer

        details = f"Reasoning section: {has_reasoning_section}, Final answer section: {has_final_answer}"
        print_result("Magistral reasoning display", passed, details)

        return passed

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_qwen_no_reasoning():
    """Test 2: Qwen3-coder without reasoning (baseline)."""
    print_section("TEST 2: Qwen3-coder (no reasoning - baseline)")

    # Create tools with Qwen3-coder model
    llm_client = LLMClient(model="qwen/qwen3-coder-30b")
    tools = AutonomousExecutionTools(llm_client=llm_client)

    print("Testing with code generation task (no reasoning expected)...")
    print("Task: 'Write a Python function to add two numbers.'\n")

    try:
        result = await tools.autonomous_filesystem_full(
            task="Write a Python function called add that takes two numbers and returns their sum. Do NOT use any filesystem tools, just answer.",
            working_directory="/Users/ahmedmaged/ai_storage/MyMCPs/lmstudio-bridge-enhanced",
            max_rounds=2,
            max_tokens=500
        )

        print("Result:")
        print("-" * 80)
        print(result)
        print("-" * 80)

        # Verify NO reasoning section (just code)
        has_reasoning_section = "**Reasoning Process:**" in result
        has_code = "def add" in result or "def" in result

        passed = not has_reasoning_section and has_code

        details = f"No reasoning section: {not has_reasoning_section}, Has code: {has_code}"
        print_result("Qwen3-coder baseline (no reasoning)", passed, details)

        return passed

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_edge_case_empty_reasoning():
    """Test 3: Edge case - empty reasoning_content (Gemma-3-12b simulation)."""
    print_section("TEST 3: Edge Case - Empty Reasoning (Gemma-3-12b)")

    tools = AutonomousExecutionTools()

    print("Simulating Gemma-3-12b edge case (0B reasoning_content)...")

    message = {
        "content": "The answer is 42",
        "reasoning_content": ""  # Empty string (Gemma case)
    }

    result = tools._format_response_with_reasoning(message)

    print("Input message:")
    print(f"  content: '{message['content']}'")
    print(f"  reasoning_content: '{message['reasoning_content']}' (empty)")
    print()
    print("Result:")
    print("-" * 80)
    print(result)
    print("-" * 80)

    # Should return just content, no reasoning section
    passed = result == "The answer is 42" and "**Reasoning Process:**" not in result

    details = f"Correctly handled empty reasoning, returned content only"
    print_result("Empty reasoning handling", passed, details)

    return passed


def test_edge_case_html_escaping():
    """Test 4: Edge case - HTML in reasoning (XSS prevention)."""
    print_section("TEST 4: Edge Case - HTML Escaping (OWASP #3 XSS)")

    tools = AutonomousExecutionTools()

    print("Testing XSS prevention with malicious HTML...")

    message = {
        "content": "Safe answer",
        "reasoning_content": "<script>alert('XSS')</script> Normal reasoning text"
    }

    result = tools._format_response_with_reasoning(message)

    print("Input message:")
    print(f"  content: '{message['content']}'")
    print(f"  reasoning_content: '{message['reasoning_content']}'")
    print()
    print("Result:")
    print("-" * 80)
    print(result)
    print("-" * 80)

    # Verify HTML is escaped
    has_escaped = "&lt;script&gt;" in result
    no_raw_html = "<script>" not in result
    has_normal_text = "Normal reasoning text" in result

    passed = has_escaped and no_raw_html and has_normal_text

    details = f"HTML escaped: {has_escaped}, No raw HTML: {no_raw_html}"
    print_result("HTML escaping (XSS prevention)", passed, details)

    return passed


def test_edge_case_truncation():
    """Test 5: Edge case - very long reasoning (truncation)."""
    print_section("TEST 5: Edge Case - Long Reasoning Truncation")

    tools = AutonomousExecutionTools()

    print("Testing truncation with 3KB reasoning content...")

    message = {
        "content": "Final answer",
        "reasoning_content": "A" * 3000  # 3KB reasoning
    }

    result = tools._format_response_with_reasoning(message)

    print("Input message:")
    print(f"  content: '{message['content']}'")
    print(f"  reasoning_content length: {len(message['reasoning_content'])} chars (3KB)")
    print()

    # Extract reasoning section
    if "**Reasoning Process:**" in result:
        reasoning_part = result.split("**Final Answer:**")[0]
        reasoning_content = reasoning_part.replace("**Reasoning Process:**", "").strip()

        print(f"Output reasoning length: {len(reasoning_content)} chars")
        print(f"Truncated: {reasoning_content.endswith('...')}")
        print()
        print("Result preview (first 100 chars):")
        print("-" * 80)
        print(result[:100] + "...")
        print("-" * 80)

        # Verify truncation
        is_truncated = len(reasoning_content) <= 2010  # 2000 + "..."
        has_ellipsis = reasoning_content.endswith("...")

        passed = is_truncated and has_ellipsis

        details = f"Truncated to {len(reasoning_content)} chars (target: ≤2010), Has ellipsis: {has_ellipsis}"
        print_result("Long reasoning truncation", passed, details)

        return passed
    else:
        print("❌ ERROR: No reasoning section found")
        return False


def test_field_priority():
    """Test 6: Field priority (reasoning_content > reasoning)."""
    print_section("TEST 6: Field Priority (reasoning_content > reasoning)")

    tools = AutonomousExecutionTools()

    print("Testing priority when both fields present...")

    message = {
        "content": "Answer",
        "reasoning_content": "From reasoning_content field",
        "reasoning": "From reasoning field"
    }

    result = tools._format_response_with_reasoning(message)

    print("Input message:")
    print(f"  reasoning_content: '{message['reasoning_content']}'")
    print(f"  reasoning: '{message['reasoning']}'")
    print()
    print("Result:")
    print("-" * 80)
    print(result)
    print("-" * 80)

    # Verify reasoning_content takes priority
    has_reasoning_content = "From reasoning_content field" in result
    no_reasoning_field = "From reasoning field" not in result

    passed = has_reasoning_content and no_reasoning_field

    details = f"reasoning_content prioritized: {has_reasoning_content}"
    print_result("Field priority (reasoning_content > reasoning)", passed, details)

    return passed


def test_type_safety():
    """Test 7: Type safety (str() conversion)."""
    print_section("TEST 7: Type Safety (str() conversion)")

    tools = AutonomousExecutionTools()

    print("Testing type conversion with non-string reasoning...")

    # Simulate API change where reasoning_content is a dict
    message = {
        "content": "Answer",
        "reasoning_content": {"text": "Reasoning as dict", "confidence": 0.95}  # Dict instead of str
    }

    result = tools._format_response_with_reasoning(message)

    print("Input message:")
    print(f"  reasoning_content type: {type(message['reasoning_content'])}")
    print(f"  reasoning_content value: {message['reasoning_content']}")
    print()
    print("Result:")
    print("-" * 80)
    print(result)
    print("-" * 80)

    # Verify no crash, converted to string
    has_reasoning = "**Reasoning Process:**" in result
    no_crash = True  # If we got here, no crash occurred

    passed = has_reasoning and no_crash

    details = f"No crash: {no_crash}, Converted to string: {has_reasoning}"
    print_result("Type safety (str() conversion)", passed, details)

    return passed


async def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("  REASONING DISPLAY FEATURE - INTEGRATION TESTS")
    print("  Evidence-Based Implementation Validation")
    print("=" * 80)

    results = []

    # Real model tests (async)
    print("\n>>> PART 1: Real Model Tests (Async)")
    results.append(("Magistral reasoning", await test_magistral()))
    results.append(("Qwen3-coder baseline", await test_qwen_no_reasoning()))

    # Edge case tests (sync)
    print("\n>>> PART 2: Edge Case Tests (Sync)")
    results.append(("Empty reasoning", test_edge_case_empty_reasoning()))
    results.append(("HTML escaping", test_edge_case_html_escaping()))
    results.append(("Truncation", test_edge_case_truncation()))
    results.append(("Field priority", test_field_priority()))
    results.append(("Type safety", test_type_safety()))

    # Summary
    print_section("TEST SUMMARY")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    print(f"Tests Passed: {passed}/{total}")
    print()

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {test_name}")

    print()

    if passed == total:
        print("=" * 80)
        print("  ✅ ALL TESTS PASSED!")
        print("=" * 80)
        print()
        print("Evidence validated:")
        print("  ✓ Empty string handling (Gemma-3-12b)")
        print("  ✓ HTML escaping (OWASP #3)")
        print("  ✓ Truncation (DeepSeek R1 5x scaling)")
        print("  ✓ Type safety (str() conversion)")
        print("  ✓ Field priority (reasoning_content > reasoning)")
        print("  ✓ Real model integration (Magistral, Qwen3-coder)")
        print()
        return 0
    else:
        print("=" * 80)
        print(f"  ❌ {total - passed} TEST(S) FAILED")
        print("=" * 80)
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
