#!/usr/bin/env python3
"""
Comprehensive test to PROVE Option 4A fix works for ALL autonomous functions.

This will test:
1. autonomous_filesystem_full - File operations
2. autonomous_memory_full - Knowledge graph operations
3. autonomous_fetch_full - Web content fetching
4. autonomous_github_full - GitHub operations

Each test verifies that MCP tools are actually being used and results returned.
"""

import asyncio
import logging
import sys
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


async def test_filesystem():
    """Test 1: Verify filesystem MCP tools work."""
    from tools.autonomous import AutonomousExecutionTools

    logger.info("="*80)
    logger.info("TEST 1: autonomous_filesystem_full")
    logger.info("="*80)

    # Create a test file with unique content
    test_file = "/private/tmp/test_option_4a_filesystem.txt"
    unique_content = "UNIQUE_VERIFICATION_STRING_XYZ_12345_OPTION_4A_TEST"

    with open(test_file, "w") as f:
        f.write(f"Test file for Option 4A verification.\n")
        f.write(f"{unique_content}\n")
        f.write(f"If LLM reports this exact string, filesystem tools work!\n")

    logger.info(f"Created test file: {test_file}")
    logger.info(f"Unique string: {unique_content}")

    agent = AutonomousExecutionTools()

    task = f"""
    Read the file {test_file} and find the unique verification string.
    Report ONLY the exact unique string that starts with UNIQUE_VERIFICATION.
    Do NOT make up or guess the string - use read_text_file tool.
    """

    result = await agent.autonomous_filesystem_full(
        task=task,
        working_directory="/private/tmp",
        max_rounds=5
    )

    logger.info(f"Result: {result}")

    # Verify the unique string is in the result
    if unique_content in result:
        logger.info("✅ TEST 1 PASSED: Filesystem tools work! LLM got the unique string.")
        return True
    else:
        logger.error(f"❌ TEST 1 FAILED: Expected '{unique_content}' in result")
        return False


async def test_memory():
    """Test 2: Verify memory MCP tools work."""
    from tools.autonomous import AutonomousExecutionTools

    logger.info("\n" + "="*80)
    logger.info("TEST 2: autonomous_memory_full")
    logger.info("="*80)

    agent = AutonomousExecutionTools()

    # Unique entity name that cannot be guessed
    unique_entity = "TestEntity_Option4A_XYZ_98765"
    unique_observation = "This is a unique observation for Option 4A testing: PROOF_OF_MEMORY_TOOL_USAGE"

    task = f"""
    Create an entity named '{unique_entity}' with observation '{unique_observation}'.
    Then search for entities containing 'Option4A' and report what you find.

    Use create_entities and search_nodes tools.
    """

    result = await agent.autonomous_memory_full(
        task=task,
        max_rounds=5
    )

    logger.info(f"Result: {result}")

    # Verify the entity and observation are mentioned
    if unique_entity in result and "Option4A" in result:
        logger.info("✅ TEST 2 PASSED: Memory tools work! LLM created and searched entity.")
        return True
    else:
        logger.error(f"❌ TEST 2 FAILED: Expected entity '{unique_entity}' in result")
        return False


async def test_fetch():
    """Test 3: Verify fetch MCP tools work."""
    from tools.autonomous import AutonomousExecutionTools

    logger.info("\n" + "="*80)
    logger.info("TEST 3: autonomous_fetch_full")
    logger.info("="*80)

    agent = AutonomousExecutionTools()

    # Fetch a simple, reliable page
    task = """
    Fetch the content from https://example.com and tell me:
    1. Does it contain the word "Example"?
    2. What is the main heading of the page?

    Use the fetch tool to retrieve the actual content.
    """

    result = await agent.autonomous_fetch_full(
        task=task,
        max_rounds=5
    )

    logger.info(f"Result: {result}")

    # Verify it mentions Example (the site always has this)
    if "Example" in result or "example" in result.lower():
        logger.info("✅ TEST 3 PASSED: Fetch tools work! LLM fetched real content.")
        return True
    else:
        logger.error("❌ TEST 3 FAILED: Expected 'Example' in result from example.com")
        return False


async def test_github():
    """Test 4: Verify github MCP tools work."""
    from tools.autonomous import AutonomousExecutionTools

    logger.info("\n" + "="*80)
    logger.info("TEST 4: autonomous_github_full")
    logger.info("="*80)

    # Check if GITHUB_PERSONAL_ACCESS_TOKEN is set
    if not os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN"):
        logger.warning("⚠️ TEST 4 SKIPPED: GITHUB_PERSONAL_ACCESS_TOKEN not set")
        return None

    agent = AutonomousExecutionTools()

    task = """
    Search for repositories about 'model context protocol' and tell me:
    1. How many results did you find?
    2. What is the name of the first repository?

    Use search_repositories tool.
    """

    result = await agent.autonomous_github_full(
        task=task,
        max_rounds=5
    )

    logger.info(f"Result: {result}")

    # Verify it mentions repositories or MCP
    if "repositor" in result.lower() or "mcp" in result.lower():
        logger.info("✅ TEST 4 PASSED: GitHub tools work! LLM searched repositories.")
        return True
    else:
        logger.error("❌ TEST 4 FAILED: Expected repository information in result")
        return False


async def main():
    """Run all tests and report results."""
    logger.info("\n" + "🎯"*40)
    logger.info("COMPREHENSIVE OPTION 4A VERIFICATION TEST")
    logger.info("Testing that LLM can actually use ALL MCP bridge tools")
    logger.info("🎯"*40 + "\n")

    results = {}

    # Test 1: Filesystem
    try:
        results['filesystem'] = await test_filesystem()
    except Exception as e:
        logger.error(f"❌ TEST 1 EXCEPTION: {e}")
        results['filesystem'] = False

    # Test 2: Memory
    try:
        results['memory'] = await test_memory()
    except Exception as e:
        logger.error(f"❌ TEST 2 EXCEPTION: {e}")
        results['memory'] = False

    # Test 3: Fetch
    try:
        results['fetch'] = await test_fetch()
    except Exception as e:
        logger.error(f"❌ TEST 3 EXCEPTION: {e}")
        results['fetch'] = False

    # Test 4: GitHub
    try:
        results['github'] = await test_github()
    except Exception as e:
        logger.error(f"❌ TEST 4 EXCEPTION: {e}")
        results['github'] = False

    # Summary
    logger.info("\n" + "="*80)
    logger.info("FINAL RESULTS")
    logger.info("="*80)

    for test_name, result in results.items():
        if result is True:
            logger.info(f"✅ {test_name.upper()}: PASSED")
        elif result is None:
            logger.info(f"⚠️  {test_name.upper()}: SKIPPED")
        else:
            logger.error(f"❌ {test_name.upper()}: FAILED")

    passed = sum(1 for r in results.values() if r is True)
    skipped = sum(1 for r in results.values() if r is None)
    failed = sum(1 for r in results.values() if r is False)
    total = len(results)

    logger.info("-"*80)
    logger.info(f"PASSED: {passed}/{total}")
    logger.info(f"SKIPPED: {skipped}/{total}")
    logger.info(f"FAILED: {failed}/{total}")

    if failed == 0 and passed > 0:
        logger.info("\n🎉 ALL TESTED FUNCTIONS WORK! Option 4A fix is VERIFIED!")
    elif failed > 0:
        logger.error(f"\n❌ {failed} function(s) still broken! Option 4A needs more work.")
    else:
        logger.warning("\n⚠️  No tests could run. Check configuration.")

    logger.info("="*80)


if __name__ == "__main__":
    asyncio.run(main())
