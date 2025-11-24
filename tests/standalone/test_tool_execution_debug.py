#!/usr/bin/env python3
"""
Debug test to see what the LLM actually returns when given tools.
This will log the complete response structure to understand why tools aren't being used.
"""

import asyncio
import logging
import sys

# Set up detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/tool_execution_debug.log')
    ]
)

logger = logging.getLogger(__name__)

async def main():
    """Test tool execution with debug logging."""
    from tools.autonomous import AutonomousExecutionTools

    logger.info("="*80)
    logger.info("TOOL EXECUTION DEBUG TEST")
    logger.info("="*80)

    logger.info("\nTest: Ask LLM to read /private/tmp/test_unique_code_20251031_XYZ.py")
    logger.info("This file has unique unpredictable names that cannot be hallucinated")
    logger.info("-"*80)

    agent = AutonomousExecutionTools()

    task = """
    Read the file /private/tmp/test_unique_code_20251031_XYZ.py and tell me:
    1. The exact class name
    2. The exact method names
    3. The exact constant name
    4. The exact function name

    DO NOT guess or make up names. Use the read_text_file tool to read the actual file.
    """

    result = await agent.autonomous_filesystem_full(
        task=task,
        working_directory="/private/tmp",
        max_rounds=5
    )

    logger.info("-"*80)
    logger.info(f"FINAL RESULT:\n{result}")
    logger.info("="*80)
    logger.info("\nCheck /tmp/tool_execution_debug.log for detailed response structures")

if __name__ == "__main__":
    asyncio.run(main())
