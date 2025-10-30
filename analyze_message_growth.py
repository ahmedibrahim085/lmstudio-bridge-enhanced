#!/usr/bin/env python3
"""
Deep analysis of message/context growth in autonomous execution loops.

This script traces exactly how messages accumulate and calculates the
token overhead with each round.
"""

import asyncio
import sys
import os
import json
from typing import List, Dict, Any

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from mcp_client.connection import MCPConnection
from mcp_client.tool_discovery import ToolDiscovery, SchemaConverter


def estimate_tokens(text: str) -> int:
    """Rough estimate of tokens (1 token ≈ 4 characters for English)."""
    return len(text) // 4


def calculate_tool_schema_size(tools: List[Dict]) -> Dict[str, Any]:
    """Calculate size of tool schemas in tokens."""
    tools_json = json.dumps(tools, indent=2)
    return {
        "tool_count": len(tools),
        "json_size_bytes": len(tools_json),
        "json_size_chars": len(tools_json),
        "estimated_tokens": estimate_tokens(tools_json)
    }


def simulate_autonomous_loop(
    task: str,
    tool_count: int,
    avg_tool_schema_size: int,
    rounds: int = 5
) -> List[Dict[str, Any]]:
    """
    Simulate message growth in autonomous loop.

    Returns list of round statistics.
    """

    # Initialize messages
    messages = [{"role": "user", "content": task}]

    # Tool schemas (passed on EVERY call)
    tool_schemas_tokens = tool_count * avg_tool_schema_size

    statistics = []

    for round_num in range(1, rounds + 1):
        # Calculate current message tokens
        total_message_chars = sum(len(json.dumps(msg)) for msg in messages)
        message_tokens = estimate_tokens(json.dumps(messages, indent=2))

        # Total tokens = messages + tool schemas
        total_tokens = message_tokens + tool_schemas_tokens

        stats = {
            "round": round_num,
            "message_count": len(messages),
            "message_tokens": message_tokens,
            "tool_schema_tokens": tool_schemas_tokens,
            "total_tokens": total_tokens,
            "messages": [
                {
                    "role": msg["role"],
                    "size_chars": len(msg.get("content", "") or "")
                }
                for msg in messages
            ]
        }

        statistics.append(stats)

        # Simulate LLM response with tool calls (typical: 2-3 tool calls)
        # Assistant message with tool calls
        assistant_msg = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": f"call_{round_num}_{i}",
                    "type": "function",
                    "function": {
                        "name": f"tool_{i}",
                        "arguments": '{"param": "value"}'
                    }
                }
                for i in range(2)  # Assume 2 tool calls
            ]
        }
        messages.append(assistant_msg)

        # Tool results (assume 500 chars each)
        for i in range(2):
            tool_result = {
                "role": "tool",
                "tool_call_id": f"call_{round_num}_{i}",
                "content": "Tool result content here (approximately 500 characters)" * 10
            }
            messages.append(tool_result)

    return statistics


async def analyze_real_mcp_tools():
    """Analyze tool schemas from real MCPs."""

    print("="*80)
    print("ANALYZING REAL MCP TOOL SCHEMAS")
    print("="*80)
    print()

    results = {}

    # 1. Filesystem MCP
    print("1. Filesystem MCP")
    print("-" * 80)
    try:
        connection = MCPConnection(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", os.getcwd()]
        )
        async with connection.connect() as session:
            discovery = ToolDiscovery(session)
            tools = await discovery.discover_tools()
            openai_tools = SchemaConverter.mcp_tools_to_openai(tools)

            size_info = calculate_tool_schema_size(openai_tools)
            results["filesystem"] = size_info

            print(f"Tool count: {size_info['tool_count']}")
            print(f"JSON size: {size_info['json_size_bytes']:,} bytes")
            print(f"Estimated tokens: {size_info['estimated_tokens']:,}")
            print()
    except Exception as e:
        print(f"Error: {e}\n")

    # 2. Memory MCP
    print("2. Memory MCP")
    print("-" * 80)
    try:
        connection = MCPConnection(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-memory"]
        )
        async with connection.connect() as session:
            discovery = ToolDiscovery(session)
            tools = await discovery.discover_tools()
            openai_tools = SchemaConverter.mcp_tools_to_openai(tools)

            size_info = calculate_tool_schema_size(openai_tools)
            results["memory"] = size_info

            print(f"Tool count: {size_info['tool_count']}")
            print(f"JSON size: {size_info['json_size_bytes']:,} bytes")
            print(f"Estimated tokens: {size_info['estimated_tokens']:,}")
            print()
    except Exception as e:
        print(f"Error: {e}\n")

    # 3. Fetch MCP
    print("3. Fetch MCP")
    print("-" * 80)
    try:
        connection = MCPConnection(
            command="uvx",
            args=["mcp-server-fetch"]
        )
        async with connection.connect() as session:
            discovery = ToolDiscovery(session)
            tools = await discovery.discover_tools()
            openai_tools = SchemaConverter.mcp_tools_to_openai(tools)

            size_info = calculate_tool_schema_size(openai_tools)
            results["fetch"] = size_info

            print(f"Tool count: {size_info['tool_count']}")
            print(f"JSON size: {size_info['json_size_bytes']:,} bytes")
            print(f"Estimated tokens: {size_info['estimated_tokens']:,}")
            print()
    except Exception as e:
        print(f"Error: {e}\n")

    # 4. GitHub MCP
    print("4. GitHub MCP")
    print("-" * 80)
    try:
        connection = MCPConnection(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            env={"GITHUB_PERSONAL_ACCESS_TOKEN": os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN", "")}
        )
        async with connection.connect() as session:
            discovery = ToolDiscovery(session)
            tools = await discovery.discover_tools()
            openai_tools = SchemaConverter.mcp_tools_to_openai(tools)

            size_info = calculate_tool_schema_size(openai_tools)
            results["github"] = size_info

            print(f"Tool count: {size_info['tool_count']}")
            print(f"JSON size: {size_info['json_size_bytes']:,} bytes")
            print(f"Estimated tokens: {size_info['estimated_tokens']:,}")
            print()
    except Exception as e:
        print(f"Error: {e}\n")

    return results


def find_lm_studio_logs():
    """Find LM Studio log files."""

    print("="*80)
    print("FINDING LM STUDIO LOGS")
    print("="*80)
    print()

    possible_locations = [
        # macOS
        os.path.expanduser("~/Library/Logs/LM Studio/"),
        os.path.expanduser("~/Library/Application Support/LM Studio/"),
        os.path.expanduser("~/Library/Application Support/LM Studio/logs/"),
        os.path.expanduser("~/.lmstudio/logs/"),

        # Linux
        os.path.expanduser("~/.config/lm-studio/logs/"),
        os.path.expanduser("~/.local/share/LM Studio/logs/"),

        # Windows (if running on Windows)
        os.path.expanduser("~/AppData/Roaming/LM Studio/logs/"),
        os.path.expanduser("~/AppData/Local/LM Studio/logs/"),
    ]

    found_locations = []

    for location in possible_locations:
        if os.path.exists(location):
            print(f"✅ FOUND: {location}")

            # List files
            try:
                files = os.listdir(location)
                if files:
                    print(f"   Files: {len(files)} files")
                    for f in sorted(files)[:5]:  # Show first 5
                        file_path = os.path.join(location, f)
                        size = os.path.getsize(file_path)
                        print(f"   - {f} ({size:,} bytes)")
                    if len(files) > 5:
                        print(f"   ... and {len(files) - 5} more files")
                else:
                    print("   (empty directory)")
                print()
                found_locations.append(location)
            except Exception as e:
                print(f"   Error reading directory: {e}\n")
        else:
            print(f"❌ NOT FOUND: {location}")

    if not found_locations:
        print("\n⚠️  No LM Studio log directories found!")
        print("LM Studio might:")
        print("  - Not be installed")
        print("  - Store logs in a different location")
        print("  - Not have created logs yet")
        print()
        print("Try checking LM Studio's Developer Tools:")
        print("  1. Open LM Studio")
        print("  2. Go to Settings/Preferences")
        print("  3. Look for 'Developer' or 'Logs' section")

    return found_locations


async def main():
    """Main analysis function."""

    print("\n" + "="*80)
    print("ULTRA-DEEP MESSAGE GROWTH ANALYSIS")
    print("="*80)
    print()

    # Part 1: Analyze real MCP tool schemas
    print("PART 1: Real MCP Tool Schema Sizes")
    print("="*80)
    mcp_results = await analyze_real_mcp_tools()

    # Part 2: Simulate autonomous loop
    print("\n" + "="*80)
    print("PART 2: Autonomous Loop Message Growth Simulation")
    print("="*80)
    print()

    # Use average tool schema size from real MCPs
    if mcp_results:
        avg_schema_tokens = sum(r["estimated_tokens"] for r in mcp_results.values()) / len(mcp_results)
    else:
        avg_schema_tokens = 5000  # Conservative estimate

    task = "Analyze the codebase and create a summary"

    print(f"Task: {task}")
    print(f"Average tool schema size: {avg_schema_tokens:,.0f} tokens")
    print()

    # Simulate for memory MCP (9 tools)
    if "memory" in mcp_results:
        print("\n" + "-"*80)
        print("Simulation: Memory MCP (9 tools)")
        print("-"*80)

        stats = simulate_autonomous_loop(
            task=task,
            tool_count=mcp_results["memory"]["tool_count"],
            avg_tool_schema_size=mcp_results["memory"]["estimated_tokens"] // mcp_results["memory"]["tool_count"],
            rounds=5
        )

        print(f"\n{'Round':<8} {'Messages':<10} {'Msg Tokens':<12} {'Tool Tokens':<12} {'Total Tokens':<12} {'Growth':<10}")
        print("-" * 80)

        prev_total = 0
        for s in stats:
            growth = f"+{s['total_tokens'] - prev_total}" if prev_total > 0 else "-"
            print(f"{s['round']:<8} {s['message_count']:<10} {s['message_tokens']:<12,} {s['tool_schema_tokens']:<12,} {s['total_tokens']:<12,} {growth:<10}")
            prev_total = s['total_tokens']

        print()
        print(f"⚠️  Token growth per round: ~{(stats[-1]['total_tokens'] - stats[0]['total_tokens']) // len(stats):,} tokens")
        print(f"⚠️  Final token count: {stats[-1]['total_tokens']:,} tokens")

    # Simulate for GitHub MCP (26 tools)
    if "github" in mcp_results:
        print("\n" + "-"*80)
        print("Simulation: GitHub MCP (26 tools)")
        print("-"*80)

        stats = simulate_autonomous_loop(
            task=task,
            tool_count=mcp_results["github"]["tool_count"],
            avg_tool_schema_size=mcp_results["github"]["estimated_tokens"] // mcp_results["github"]["tool_count"],
            rounds=5
        )

        print(f"\n{'Round':<8} {'Messages':<10} {'Msg Tokens':<12} {'Tool Tokens':<12} {'Total Tokens':<12} {'Growth':<10}")
        print("-" * 80)

        prev_total = 0
        for s in stats:
            growth = f"+{s['total_tokens'] - prev_total}" if prev_total > 0 else "-"
            print(f"{s['round']:<8} {s['message_count']:<10} {s['message_tokens']:<12,} {s['tool_schema_tokens']:<12,} {s['total_tokens']:<12,} {growth:<10}")
            prev_total = s['total_tokens']

        print()
        print(f"⚠️  Token growth per round: ~{(stats[-1]['total_tokens'] - stats[0]['total_tokens']) // len(stats):,} tokens")
        print(f"⚠️  Final token count: {stats[-1]['total_tokens']:,} tokens")

    # Part 3: Find LM Studio logs
    print("\n" + "="*80)
    print("PART 3: LM Studio Log Locations")
    print("="*80)
    print()

    log_locations = find_lm_studio_logs()

    # Part 4: Analysis and recommendations
    print("\n" + "="*80)
    print("PART 4: ROOT CAUSE ANALYSIS")
    print("="*80)
    print()

    print("🔍 IDENTIFIED ISSUES:")
    print()

    print("1. **Tool Schemas Sent Every Round**")
    print("   - Tool schemas are included in EVERY API call")
    print("   - Memory MCP: ~{:,} tokens per call (tool schemas alone)".format(
        mcp_results.get("memory", {}).get("estimated_tokens", 0)))
    print("   - GitHub MCP: ~{:,} tokens per call (tool schemas alone)".format(
        mcp_results.get("github", {}).get("estimated_tokens", 0)))
    print()

    print("2. **Message History Accumulates**")
    print("   - Full conversation history sent every round")
    print("   - Each tool call adds assistant message + tool result(s)")
    print("   - Linear growth: Round 1 = 1 msg, Round 5 = ~11 messages")
    print()

    print("3. **Combined Effect**")
    print("   - Total tokens = Message tokens + Tool schema tokens")
    print("   - Message tokens grow linearly with rounds")
    print("   - Tool schema tokens stay constant but are LARGE")
    print("   - Result: Rapid token growth, slower responses, higher costs")
    print()

    print("\n" + "="*80)
    print("PART 5: RECOMMENDATIONS")
    print("="*80)
    print()

    print("🛠️  OPTIMIZATION STRATEGIES:")
    print()

    print("1. **Context Window Sliding** (Easy)")
    print("   - Keep only last N messages (e.g., last 10)")
    print("   - Prevents unbounded growth")
    print("   - Trade-off: LLM loses older context")
    print()

    print("2. **Tool Result Truncation** (Medium)")
    print("   - Truncate large tool results to essential info")
    print("   - Keep first/last N characters")
    print("   - Trade-off: May lose important details")
    print()

    print("3. **Summarization** (Hard)")
    print("   - Periodically summarize conversation")
    print("   - Replace old messages with summary")
    print("   - Trade-off: Requires extra LLM call")
    print()

    print("4. **Tool Schema Optimization** (Medium)")
    print("   - Minimize tool descriptions")
    print("   - Remove unnecessary schema details")
    print("   - Trade-off: Less helpful tool descriptions")
    print()

    print("5. **Stateful API** (Hard, Not Feasible)")
    print("   - Use LM Studio's /v1/responses endpoint")
    print("   - Problem: Doesn't support function calling")
    print("   - Not viable for autonomous execution")
    print()

    print("\n" + "="*80)
    print("CONCLUSION")
    print("="*80)
    print()
    print("✅ This is NOT a bug - it's the standard OpenAI API pattern")
    print("⚠️  However, it DOES cause performance degradation with long conversations")
    print("🎯 Recommended: Implement context window sliding (keep last 10 messages)")
    print()


if __name__ == "__main__":
    asyncio.run(main())
