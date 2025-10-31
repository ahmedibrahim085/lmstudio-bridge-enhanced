#!/usr/bin/env python3
"""
Test to verify autonomous_persistent_session (chat_completion path) actually works.
This will confirm that the chat_completion approach DOES return tool results correctly.
"""

import asyncio
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

async def main():
    """Test persistent session with same unique file."""
    from tools.autonomous import AutonomousExecutionTools

    logger.info("="*80)
    logger.info("TEST: autonomous_persistent_session (chat_completion path)")
    logger.info("="*80)

    agent = AutonomousExecutionTools()

    tasks = [
        """Read the file /private/tmp/test_unique_code_20251031_XYZ.py and tell me:
        1. The exact class name
        2. The exact method names
        3. The exact constant name
        4. The exact function name

        DO NOT guess. Use read_text_file tool."""
    ]

    logger.info("\nExecuting with autonomous_persistent_session...")
    logger.info("-"*80)

    results = await agent.autonomous_persistent_session(
        tasks=tasks,
        initial_directory="/private/tmp",
        max_rounds=5
    )

    logger.info("-"*80)
    logger.info(f"RESULT:\n{results[0]}")
    logger.info("="*80)

    # Check if it got the unique names correctly
    if "VeryUniqueClassName_Phoenix_2025_QW3RTY" in results[0]:
        logger.info("✅ SUCCESS: Got the unique class name correctly!")
        logger.info("✅ chat_completion path WORKS - tool results are being returned")
    else:
        logger.error("❌ FAILED: Did not get unique class name")
        logger.error("❌ Even chat_completion path is broken?!")

if __name__ == "__main__":
    asyncio.run(main())
