#!/usr/bin/env python3
"""
Test script to discover what tools the local LLM can use through each MCP.

This script connects to each MCP and discovers the available tools,
showing exactly what capabilities the local LLM has when running autonomously.
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from mcp_client.connection import MCPConnection
from mcp_client.tool_discovery import ToolDiscovery


async def test_filesystem_mcp():
    """Test what tools are available from filesystem MCP."""
    print("\n" + "="*80)
    print("1. FILESYSTEM MCP TOOLS")
    print("="*80)
    print("Connection: npx -y @modelcontextprotocol/server-filesystem")
    print()

    try:
        connection = MCPConnection(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", os.getcwd()]
        )

        async with connection.connect() as session:
            discovery = ToolDiscovery(session)
            tools = await discovery.discover_tools()

            print(f"✅ Connected successfully")
            print(f"📊 Total tools available: {len(tools)}")
            print()
            print("Available tools for local LLM:")
            print("-" * 80)

            for i, tool in enumerate(tools, 1):
                print(f"{i}. {tool.name}")
                if tool.description:
                    print(f"   Description: {tool.description}")
                print()

            return tools
    except Exception as e:
        print(f"❌ Error connecting to filesystem MCP: {e}")
        import traceback
        traceback.print_exc()
        return []


async def test_memory_mcp():
    """Test what tools are available from memory MCP."""
    print("\n" + "="*80)
    print("2. MEMORY MCP TOOLS (Knowledge Graph)")
    print("="*80)
    print("Connection: npx -y @modelcontextprotocol/server-memory")
    print()

    try:
        connection = MCPConnection(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-memory"]
        )

        async with connection.connect() as session:
            discovery = ToolDiscovery(session)
            tools = await discovery.discover_tools()

            print(f"✅ Connected successfully")
            print(f"📊 Total tools available: {len(tools)}")
            print()
            print("Available tools for local LLM:")
            print("-" * 80)

            for i, tool in enumerate(tools, 1):
                print(f"{i}. {tool.name}")
                if tool.description:
                    print(f"   Description: {tool.description}")
                print()

            return tools
    except Exception as e:
        print(f"❌ Error connecting to memory MCP: {e}")
        import traceback
        traceback.print_exc()
        return []


async def test_fetch_mcp():
    """Test what tools are available from fetch MCP."""
    print("\n" + "="*80)
    print("3. FETCH MCP TOOLS (Web Content)")
    print("="*80)
    print("Connection: uvx mcp-server-fetch")
    print()

    try:
        connection = MCPConnection(
            command="uvx",
            args=["mcp-server-fetch"]
        )

        async with connection.connect() as session:
            discovery = ToolDiscovery(session)
            tools = await discovery.discover_tools()

            print(f"✅ Connected successfully")
            print(f"📊 Total tools available: {len(tools)}")
            print()
            print("Available tools for local LLM:")
            print("-" * 80)

            for i, tool in enumerate(tools, 1):
                print(f"{i}. {tool.name}")
                if tool.description:
                    print(f"   Description: {tool.description}")

                # Show input schema for fetch tool
                if hasattr(tool, 'inputSchema') and tool.inputSchema:
                    schema = tool.inputSchema
                    if 'properties' in schema:
                        print(f"   Parameters:")
                        for param_name, param_info in schema['properties'].items():
                            param_type = param_info.get('type', 'unknown')
                            param_desc = param_info.get('description', 'No description')
                            print(f"     - {param_name} ({param_type}): {param_desc}")
                print()

            return tools
    except Exception as e:
        print(f"❌ Error connecting to fetch MCP: {e}")
        import traceback
        traceback.print_exc()
        return []


async def test_github_mcp():
    """Test what tools are available from GitHub MCP."""
    print("\n" + "="*80)
    print("4. GITHUB MCP TOOLS")
    print("="*80)
    print("Connection: npx -y @modelcontextprotocol/server-github")
    print()

    try:
        # Get GitHub token if available
        token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN", "")

        connection = MCPConnection(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            env={"GITHUB_PERSONAL_ACCESS_TOKEN": token}
        )

        async with connection.connect() as session:
            discovery = ToolDiscovery(session)
            tools = await discovery.discover_tools()

            print(f"✅ Connected successfully")
            print(f"📊 Total tools available: {len(tools)}")
            print()
            print("Available tools for local LLM:")
            print("-" * 80)

            # Group tools by category
            categories = {
                'Repository': [],
                'File': [],
                'Branch': [],
                'Issue': [],
                'Pull Request': [],
                'Search': [],
                'Other': []
            }

            for tool in tools:
                name = tool.name
                if 'repository' in name or 'repo' in name or 'fork' in name:
                    categories['Repository'].append(tool)
                elif 'file' in name or 'push' in name:
                    categories['File'].append(tool)
                elif 'branch' in name:
                    categories['Branch'].append(tool)
                elif 'issue' in name:
                    categories['Issue'].append(tool)
                elif 'pull' in name or 'pr' in name:
                    categories['Pull Request'].append(tool)
                elif 'search' in name:
                    categories['Search'].append(tool)
                else:
                    categories['Other'].append(tool)

            for category, category_tools in categories.items():
                if category_tools:
                    print(f"\n{category} Operations:")
                    for tool in category_tools:
                        print(f"  • {tool.name}")
                        if tool.description:
                            print(f"    {tool.description}")

            print()
            return tools
    except Exception as e:
        print(f"❌ Error connecting to GitHub MCP: {e}")
        import traceback
        traceback.print_exc()
        return []


async def main():
    """Run all MCP tool discovery tests."""
    print("\n" + "="*80)
    print("LOCAL LLM AUTONOMOUS TOOL DISCOVERY")
    print("="*80)
    print("Testing what tools the local LLM can use through each MCP...")
    print()
    print("Note: These are the tools available to your LOCAL LLM (via LM Studio)")
    print("when it runs autonomously through the lmstudio-bridge-enhanced MCP.")
    print()

    # Test each MCP
    filesystem_tools = await test_filesystem_mcp()
    memory_tools = await test_memory_mcp()
    fetch_tools = await test_fetch_mcp()
    github_tools = await test_github_mcp()

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Filesystem MCP: {len(filesystem_tools)} tools")
    print(f"Memory MCP: {len(memory_tools)} tools")
    print(f"Fetch MCP: {len(fetch_tools)} tools")
    print(f"GitHub MCP: {len(github_tools)} tools")
    print("-" * 80)
    print(f"TOTAL TOOLS AVAILABLE TO LOCAL LLM: {len(filesystem_tools) + len(memory_tools) + len(fetch_tools) + len(github_tools)}")
    print("="*80)

    # List autonomous functions available
    print("\n" + "="*80)
    print("AUTONOMOUS FUNCTIONS (What Claude can call)")
    print("="*80)
    print("Claude can call these 5 functions to give the local LLM access to tools:")
    print()
    print("1. autonomous_filesystem_full")
    print(f"   → Gives local LLM access to {len(filesystem_tools)} filesystem tools")
    print()
    print("2. autonomous_memory_full")
    print(f"   → Gives local LLM access to {len(memory_tools)} knowledge graph tools")
    print()
    print("3. autonomous_fetch_full")
    print(f"   → Gives local LLM access to {len(fetch_tools)} web content tools")
    print()
    print("4. autonomous_github_full")
    print(f"   → Gives local LLM access to {len(github_tools)} GitHub tools")
    print()
    print("5. autonomous_persistent_session")
    print(f"   → Gives local LLM multi-task filesystem access with directory switching")
    print()
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
