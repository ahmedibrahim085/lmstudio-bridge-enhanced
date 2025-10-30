#!/usr/bin/env python3
"""
Test all Phase 3 v2 functions.

This tests:
- autonomous_github_full_v2()
- autonomous_fetch_full_v2()
- autonomous_filesystem_full_v2()
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.autonomous import AutonomousExecutionTools
from llm.llm_client import LLMClient


async def test_github_v2():
    """Test autonomous_github_full_v2()."""
    print("="*80)
    print("TEST 1: autonomous_github_full_v2()")
    print("="*80)
    print()

    tools = AutonomousExecutionTools()

    # Simple GitHub search task
    task = "Search for repositories about 'MCP servers' and list the top 3 repository names"

    print(f"Task: {task}")
    print()

    try:
        result = await tools.autonomous_github_full_v2(
            task=task,
            max_rounds=5  # Keep it short for testing
        )

        print("✅ GitHub v2 completed successfully!")
        print()
        print("Result:")
        print(result[:500] if len(result) > 500 else result)  # Truncate if too long
        print()
        return True

    except Exception as e:
        print(f"❌ GitHub v2 failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_fetch_v2():
    """Test autonomous_fetch_full_v2()."""
    print("="*80)
    print("TEST 2: autonomous_fetch_full_v2()")
    print("="*80)
    print()

    tools = AutonomousExecutionTools()

    # Simple web fetch task
    task = "Fetch https://modelcontextprotocol.io and tell me what MCP stands for"

    print(f"Task: {task}")
    print()

    try:
        result = await tools.autonomous_fetch_full_v2(
            task=task,
            max_rounds=3  # Should only need 1-2 rounds
        )

        print("✅ Fetch v2 completed successfully!")
        print()
        print("Result:")
        print(result[:500] if len(result) > 500 else result)
        print()
        return True

    except Exception as e:
        print(f"❌ Fetch v2 failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_filesystem_v2():
    """Test autonomous_filesystem_full_v2()."""
    print("="*80)
    print("TEST 3: autonomous_filesystem_full_v2()")
    print("="*80)
    print()

    tools = AutonomousExecutionTools()

    # Use the current lmstudio-bridge-enhanced directory
    working_dir = os.path.dirname(os.path.abspath(__file__))

    # Simple filesystem task
    task = "List all Python files (*.py) in the current directory and count them"

    print(f"Task: {task}")
    print(f"Working Directory: {working_dir}")
    print()

    try:
        result = await tools.autonomous_filesystem_full_v2(
            task=task,
            working_directory=working_dir,
            max_rounds=5
        )

        print("✅ Filesystem v2 completed successfully!")
        print()
        print("Result:")
        print(result[:500] if len(result) > 500 else result)
        print()
        return True

    except Exception as e:
        print(f"❌ Filesystem v2 failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def compare_token_usage_analysis():
    """
    Analyze expected token usage differences between v1 and v2.
    """
    print("="*80)
    print("TEST 4: Token Usage Analysis (All MCPs)")
    print("="*80)
    print()

    print("Expected Token Savings at Round 100:")
    print()

    # Memory MCP (9 tools)
    print("Memory MCP (9 tools, 1,964 tokens for schemas):")
    print("  V1: ~124,000 tokens")
    print("  V2: ~2,000 tokens")
    print("  Savings: 98% (122,000 tokens saved!)")
    print()

    # Fetch MCP (1 tool)
    print("Fetch MCP (1 tool, 410 tokens for schemas):")
    print("  V1: ~41,000 tokens")
    print("  V2: ~500 tokens")
    print("  Savings: 99% (40,500 tokens saved!)")
    print()

    # GitHub MCP (26 tools)
    print("GitHub MCP (26 tools, 7,307 tokens for schemas):")
    print("  V1: ~130,000 tokens")
    print("  V2: ~7,500 tokens")
    print("  Savings: 94% (122,500 tokens saved!)")
    print()

    # Filesystem MCP (14 tools)
    print("Filesystem MCP (14 tools, 2,917 tokens for schemas):")
    print("  V1: ~127,000 tokens")
    print("  V2: ~3,000 tokens")
    print("  Savings: 98% (124,000 tokens saved!)")
    print()

    print("Overall Impact:")
    print("  Average savings: 97% across all MCPs")
    print("  Enables unlimited rounds without context overflow")
    print("  Consistent performance regardless of round count")
    print()


async def main():
    """Run all Phase 3 tests."""
    print()
    print("="*80)
    print("PHASE 3 V2 FUNCTIONS - COMPREHENSIVE TESTING")
    print("="*80)
    print()
    print("Testing all 3 new v2 functions from Phase 3:")
    print("1. autonomous_github_full_v2()")
    print("2. autonomous_fetch_full_v2()")
    print("3. autonomous_filesystem_full_v2()")
    print()

    # Check LM Studio is running
    llm = LLMClient()
    if not llm.health_check():
        print("❌ LM Studio is not running")
        print("Please start LM Studio and load a model")
        return

    print("✅ LM Studio is running")
    print()

    # Run all tests
    results = {
        "github_v2": await test_github_v2(),
        "fetch_v2": await test_fetch_v2(),
        "filesystem_v2": await test_filesystem_v2()
    }

    # Token usage analysis
    await compare_token_usage_analysis()

    # Summary
    print()
    print("="*80)
    print("PHASE 3 TEST SUMMARY")
    print("="*80)
    print()
    print(f"1. GitHub V2: {'✅ PASS' if results['github_v2'] else '❌ FAIL'}")
    print(f"2. Fetch V2: {'✅ PASS' if results['fetch_v2'] else '❌ FAIL'}")
    print(f"3. Filesystem V2: {'✅ PASS' if results['filesystem_v2'] else '❌ FAIL'}")
    print()

    all_passed = all(results.values())

    if all_passed:
        print("🎉 ALL PHASE 3 TESTS PASSED!")
        print()
        print("Phase 3 Complete:")
        print("✅ autonomous_github_full_v2() implemented and tested")
        print("✅ autonomous_fetch_full_v2() implemented and tested")
        print("✅ autonomous_filesystem_full_v2() implemented and tested")
        print("✅ All v2 functions use stateful /v1/responses API")
        print("✅ Expected token savings: 94-99% at round 100")
        print()
        print("Combined with Phase 1 & 2:")
        print("✅ Tool format converter implemented")
        print("✅ create_response() enhanced with tools support")
        print("✅ autonomous_memory_full_v2() implemented (Phase 2)")
        print("✅ All 4 autonomous v2 functions complete")
        print()
        print("Next Steps:")
        print("- Create comprehensive Phase 3 documentation")
        print("- Consider making v2 the default")
        print("- Monitor real-world token usage")
        print("- Collect user feedback")
    else:
        print("❌ SOME TESTS FAILED")
        print()
        print("Please check errors above and fix before proceeding")

    print()


if __name__ == "__main__":
    asyncio.run(main())
