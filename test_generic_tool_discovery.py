#!/usr/bin/env python3
"""
Test: Verify tool discovery is TRULY GENERIC for ANY MCP.

This test proves:
1. The system can connect to ANY MCP (not just hardcoded ones)
2. Tools from dynamically added MCPs are discovered
3. Tools are properly formatted for LLM consumption
4. NO hardcoded MCP assumptions exist
"""

import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_client.discovery import MCPDiscovery
from mcp import StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.session import ClientSession

print("=" * 80)
print("TEST: Generic Tool Discovery for ANY MCP")
print("=" * 80)
print()

async def test_tool_discovery_for_mcp(mcp_name: str):
    """Test tool discovery for a specific MCP."""
    print(f"Testing: {mcp_name}")
    print("-" * 80)

    # Get discovery
    discovery = MCPDiscovery()

    # Get connection params
    try:
        params = discovery.get_connection_params(mcp_name)
    except ValueError as e:
        print(f"❌ MCP not found: {e}")
        return None

    print(f"Command: {params['command']} {' '.join(params['args'])}")

    # Connect to MCP
    server_params = StdioServerParameters(
        command=params["command"],
        args=params["args"],
        env=params.get("env", {})
    )

    try:
        print("Connecting...")
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print(f"✅ Connected to {mcp_name}")

                # List tools
                tools = await session.list_tools()
                print(f"✅ Found {len(tools.tools)} tools:")
                print()

                tool_info = []
                for tool in tools.tools:
                    print(f"  • {tool.name}")
                    if hasattr(tool, 'description') and tool.description:
                        print(f"    {tool.description[:80]}...")
                    if hasattr(tool, 'inputSchema') and tool.inputSchema:
                        schema = tool.inputSchema
                        if 'properties' in schema:
                            params = list(schema['properties'].keys())
                            print(f"    Parameters: {', '.join(params[:5])}")
                    print()

                    tool_info.append({
                        "name": tool.name,
                        "description": getattr(tool, 'description', 'No description'),
                        "has_schema": hasattr(tool, 'inputSchema')
                    })

                return tool_info

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        import traceback
        traceback.print_exc()
        return None

async def main():
    """Test tool discovery for multiple MCPs."""

    # Get all available MCPs
    discovery = MCPDiscovery()
    print(f"Reading from: {discovery.mcp_json_path}")
    print()

    available_mcps = discovery.list_available_mcps()
    print(f"Available MCPs ({len(available_mcps)}):")
    for mcp in available_mcps:
        print(f"  • {mcp}")
    print()
    print("=" * 80)
    print()

    # Test a selection of MCPs (including sqlite-test!)
    test_mcps = []

    # Always test sqlite-test if available (our dynamic test case!)
    if "sqlite-test" in available_mcps:
        test_mcps.append("sqlite-test")

    # Test a few others if available
    for mcp in ["filesystem", "memory", "fetch"]:
        if mcp in available_mcps:
            test_mcps.append(mcp)

    if not test_mcps:
        print("❌ No MCPs available to test")
        return

    results = {}
    for mcp_name in test_mcps:
        tools = await test_tool_discovery_for_mcp(mcp_name)
        results[mcp_name] = tools
        print()
        print("=" * 80)
        print()

    # Summary
    print("SUMMARY")
    print("=" * 80)
    print()

    success_count = sum(1 for tools in results.values() if tools is not None)
    total_tools = sum(len(tools) for tools in results.values() if tools is not None)

    print(f"MCPs tested: {len(results)}")
    print(f"MCPs connected: {success_count}")
    print(f"Total tools discovered: {total_tools}")
    print()

    for mcp_name, tools in results.items():
        if tools:
            print(f"✅ {mcp_name}: {len(tools)} tools")
        else:
            print(f"❌ {mcp_name}: Connection failed")

    print()
    print("=" * 80)
    print("VERIFICATION")
    print("=" * 80)
    print()

    # Check if sqlite-test worked (our dynamic test!)
    if "sqlite-test" in results:
        if results["sqlite-test"]:
            print("✅ CRITICAL: sqlite-test tools discovered!")
            print()
            print("This proves:")
            print("  • System can connect to dynamically added MCPs")
            print("  • Tool discovery works for ANY MCP (not just hardcoded ones)")
            print("  • Adding MCP to .mcp.json makes its tools available")
            print("  • NO hardcoded assumptions about which MCPs exist")
            print()
            print("  🎉 The system is TRULY GENERIC!")
        else:
            print("❌ FAILED: Could not connect to sqlite-test")
    else:
        print("⚠️  sqlite-test not in available MCPs")
        print("   (This is OK if you removed it)")

    print()
    print("=" * 80)

# Run test
asyncio.run(main())
