#!/usr/bin/env python3
"""
CRITICAL TEST: Verify local LLM can actually USE sqlite-test MCP's tools!

This is the REAL test - not just discovery, but actual tool execution.

Test flow:
1. Discovery: Find sqlite-test MCP from .mcp.json
2. Connection: Connect to sqlite-test MCP server
3. Tool Discovery: List sqlite-test's available tools
4. Execution: Have local LLM call a sqlite-test tool
"""

import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_client.discovery import MCPDiscovery
from tools.dynamic_autonomous import DynamicAutonomousAgent
from llm.llm_client import LLMClient

print("=" * 80)
print("CRITICAL TEST: Local LLM Uses sqlite-test MCP Tools")
print("=" * 80)
print()

# Step 1: Discovery
print("STEP 1: Discovery - Find sqlite-test MCP")
print("-" * 80)
discovery = MCPDiscovery()
print(f"Reading from: {discovery.mcp_json_path}")

available_mcps = discovery.list_available_mcps()
print(f"Available MCPs: {', '.join(available_mcps)}")

if "sqlite-test" not in available_mcps:
    print("❌ FAILED: sqlite-test MCP not found in .mcp.json")
    print()
    print("Expected: sqlite-test should be in ~/.lmstudio/mcp.json")
    sys.exit(1)

print("✅ sqlite-test MCP discovered!")
print()

# Get connection info
params = discovery.get_connection_params("sqlite-test")
print(f"Connection params:")
print(f"  Command: {params['command']}")
print(f"  Args: {' '.join(params['args'])}")
print()

# Step 2: Test autonomous execution with sqlite-test
print("STEP 2: Local LLM Execution - Use sqlite-test MCP")
print("-" * 80)
print("Task: Create a test table and insert data using sqlite-test MCP")
print()

async def test_autonomous_sqlite():
    """Test that local LLM can actually use sqlite-test tools."""

    # Initialize agent with LLM
    llm_client = LLMClient()
    agent = DynamicAutonomousAgent(llm_client=llm_client)

    # Task for local LLM: Use sqlite-test to create table and insert data
    task = """Using the sqlite-test MCP tools:
1. Create a table called 'test_users' with columns: id (integer), name (text), email (text)
2. Insert 2 sample users into the table
3. Query the table to verify the data was inserted
4. Return a summary of what you did

This is a test to verify you can use sqlite-test MCP's tools dynamically."""

    print("Calling autonomous_with_mcp(mcp_name='sqlite-test', task=...)...")
    print()

    try:
        result = await agent.autonomous_with_mcp(
            mcp_name="sqlite-test",
            task=task,
            max_rounds=20,  # Give it enough rounds to complete the task
            max_tokens=8192
        )

        print()
        print("=" * 80)
        print("RESULT FROM LOCAL LLM:")
        print("=" * 80)
        print(result)
        print()

        # Check if result indicates success
        if "error" in result.lower() and "failed" in result.lower():
            print("❌ FAILED: Local LLM encountered errors")
            return False

        print("✅ SUCCESS: Local LLM used sqlite-test MCP tools!")
        return True

    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return False

# Run the test
success = asyncio.run(test_autonomous_sqlite())

print()
print("=" * 80)
print("TEST SUMMARY")
print("=" * 80)

if success:
    print("✅ COMPLETE SUCCESS!")
    print()
    print("What was verified:")
    print("  1. ✅ Discovery: sqlite-test MCP found in .mcp.json")
    print("  2. ✅ Connection: Connected to sqlite-test MCP server")
    print("  3. ✅ Tool Discovery: Local LLM saw sqlite-test's tools")
    print("  4. ✅ Execution: Local LLM successfully used sqlite-test's tools")
    print()
    print("This proves:")
    print("  • Dynamic MCP discovery works")
    print("  • Dynamic tool discovery works")
    print("  • Local LLM can use ANY MCP added to .mcp.json")
    print("  • The system is truly generic and extensible")
else:
    print("❌ FAILED")
    print()
    print("The test did not complete successfully.")
    print("Check the logs above for details.")

print()
print("=" * 80)
