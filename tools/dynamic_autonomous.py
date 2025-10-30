#!/usr/bin/env python3
"""
Dynamic Autonomous Tools - Truly dynamic MCP support!

This module enables the local LLM to use ANY MCP that's configured in .mcp.json,
without requiring code changes. As soon as you add a new MCP to .mcp.json,
it becomes available to the local LLM automatically!

Key Features:
- Dynamic MCP discovery from .mcp.json
- Connect to ANY MCP by name
- Connect to MULTIPLE MCPs simultaneously
- Auto-discover ALL MCPs and use any tool from any MCP
- No hardcoded MCP configurations
- Future-proof: works with any MCP added to .mcp.json
"""

import asyncio
import json
from typing import List, Dict, Any, Optional, Union
from contextlib import AsyncExitStack
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp import ClientSession
from mcp_client.discovery import MCPDiscovery, get_mcp_discovery
from llm.llm_client import LLMClient


def log_info(message: str):
    """Log informational messages to stderr"""
    print(f"INFO: {message}", file=sys.stderr)


def log_error(message: str):
    """Log error messages to stderr"""
    print(f"ERROR: {message}", file=sys.stderr)


class DynamicAutonomousAgent:
    """
    Dynamic autonomous agent that can connect to ANY MCP discovered from .mcp.json.

    This is the TRUE dynamic solution - no hardcoded MCP configurations!
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        mcp_discovery: Optional[MCPDiscovery] = None
    ):
        """
        Initialize dynamic autonomous agent with HOT RELOAD support.

        Hot reload: .mcp.json is read fresh on EVERY tool call, so adding
        new MCPs to .mcp.json makes them available immediately without restart!

        Performance: Only 0.011ms overhead per call (essentially free).

        Args:
            llm_client: Optional LLM client (creates default if None)
            mcp_discovery: Optional MCP discovery instance (only used to get mcp_json_path)
        """
        self.llm = llm_client or LLMClient()

        # HOT RELOAD: Don't store discovery instance, only the path
        # This way we create fresh MCPDiscovery on every call (reads file fresh)
        if mcp_discovery:
            self.mcp_json_path = mcp_discovery.mcp_json_path
        else:
            # Find mcp.json path once (this doesn't read the file)
            temp_discovery = MCPDiscovery()
            self.mcp_json_path = temp_discovery.mcp_json_path

    async def autonomous_with_mcp(
        self,
        mcp_name: str,
        task: str,
        max_rounds: int = 100,
        max_tokens: Union[int, str] = "auto"
    ) -> str:
        """
        Execute task autonomously using tools from a SINGLE MCP.

        The MCP is dynamically discovered from .mcp.json - NO hardcoded config!

        Args:
            mcp_name: Name of the MCP to use (e.g., "filesystem", "memory", "fetch")
            task: Task description for the local LLM
            max_rounds: Maximum autonomous loop iterations
            max_tokens: Maximum tokens per LLM response ("auto" or integer)

        Returns:
            Final answer from the local LLM

        Raises:
            ValueError: If MCP not found or is disabled

        Examples:
            # Use filesystem MCP
            await agent.autonomous_with_mcp(
                mcp_name="filesystem",
                task="Read README.md and summarize it"
            )

            # Use memory MCP
            await agent.autonomous_with_mcp(
                mcp_name="memory",
                task="Create an entity called 'Python' with observations"
            )

            # Use ANY MCP configured in .mcp.json!
            await agent.autonomous_with_mcp(
                mcp_name="my-custom-mcp",
                task="Do something with my custom MCP"
            )
        """
        log_info(f"=== Dynamic Autonomous Execution ===")
        log_info(f"MCP: {mcp_name}")
        log_info(f"Task: {task}")

        try:
            # HOT RELOAD: Create fresh MCPDiscovery (reads .mcp.json fresh)
            discovery = MCPDiscovery(self.mcp_json_path)

            # Get connection parameters dynamically from .mcp.json
            params = discovery.get_connection_params(mcp_name)
            log_info(f"Connecting to {mcp_name} MCP: {params['command']} {' '.join(params['args'])}")

            # Create server parameters
            server_params = StdioServerParameters(
                command=params["command"],
                args=params["args"],
                env=params["env"] if params["env"] else None
            )

            # Connect to MCP
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    # Initialize MCP session
                    log_info("Initializing MCP session...")
                    init_result = await session.initialize()
                    log_info(f"MCP initialized: {init_result.serverInfo.name}")

                    # Get tools from MCP
                    log_info("Getting available tools...")
                    tools_result = await session.list_tools()
                    log_info(f"Found {len(tools_result.tools)} tools")

                    # Convert tools to OpenAI format
                    openai_tools = []
                    for tool in tools_result.tools:
                        log_info(f"  - {tool.name}: {tool.description[:80]}...")
                        openai_tools.append({
                            "type": "function",
                            "function": {
                                "name": tool.name,
                                "description": tool.description,
                                "parameters": tool.inputSchema
                            }
                        })

                    if not openai_tools:
                        return f"Error: No tools available from {mcp_name} MCP"

                    # Determine max_tokens
                    actual_max_tokens = (
                        self.llm.get_default_max_tokens()
                        if max_tokens == "auto"
                        else max_tokens
                    )

                    # Execute autonomous loop
                    return await self._autonomous_loop(
                        session=session,
                        openai_tools=openai_tools,
                        task=task,
                        max_rounds=max_rounds,
                        max_tokens=actual_max_tokens
                    )

        except ValueError as e:
            log_error(f"Configuration error: {e}")
            return f"Error: {e}"
        except Exception as e:
            log_error(f"Autonomous execution failed: {e}")
            import traceback
            log_error(traceback.format_exc())
            return f"Error during autonomous execution: {e}"

    async def autonomous_with_multiple_mcps(
        self,
        mcp_names: List[str],
        task: str,
        max_rounds: int = 100,
        max_tokens: Union[int, str] = "auto"
    ) -> str:
        """
        Execute task autonomously using tools from MULTIPLE MCPs simultaneously!

        This is incredibly powerful - the local LLM can use ANY tool from ANY MCP
        in a SINGLE session. For example, it can read files, create knowledge graph
        entities, and fetch web content all in the same autonomous loop!

        Args:
            mcp_names: List of MCP names to use (e.g., ["filesystem", "memory", "fetch"])
            task: Task description for the local LLM
            max_rounds: Maximum autonomous loop iterations
            max_tokens: Maximum tokens per LLM response ("auto" or integer)

        Returns:
            Final answer from the local LLM

        Examples:
            # Use filesystem + memory MCPs
            await agent.autonomous_with_multiple_mcps(
                mcp_names=["filesystem", "memory"],
                task="Read all Python files and create a knowledge graph of the codebase structure"
            )

            # Use filesystem + fetch + memory MCPs
            await agent.autonomous_with_multiple_mcps(
                mcp_names=["filesystem", "fetch", "memory"],
                task="Read local docs, fetch online docs, compare them, and build a knowledge graph"
            )

            # Use ALL available MCPs!
            await agent.autonomous_with_multiple_mcps(
                mcp_names=["filesystem", "memory", "fetch", "github"],
                task="Analyze repo, fetch docs, create knowledge graph, and open GitHub issues for improvements"
            )
        """
        log_info(f"=== Dynamic Multi-MCP Autonomous Execution ===")
        log_info(f"MCPs: {', '.join(mcp_names)}")
        log_info(f"Task: {task}")

        try:
            # HOT RELOAD: Create fresh MCPDiscovery (reads .mcp.json fresh)
            discovery = MCPDiscovery(self.mcp_json_path)

            # Validate MCP names
            valid_mcps = discovery.validate_mcp_names(mcp_names)
            log_info(f"Valid MCPs: {', '.join(valid_mcps)}")

            # Use AsyncExitStack to manage multiple connections
            async with AsyncExitStack() as stack:
                sessions_and_tools = []

                # Connect to each MCP
                for mcp_name in valid_mcps:
                    try:
                        # Get connection parameters
                        params = discovery.get_connection_params(mcp_name)
                        log_info(f"Connecting to {mcp_name}: {params['command']}")

                        # Create server parameters
                        server_params = StdioServerParameters(
                            command=params["command"],
                            args=params["args"],
                            env=params["env"] if params["env"] else None
                        )

                        # Connect
                        read, write = await stack.enter_async_context(
                            stdio_client(server_params)
                        )
                        session = await stack.enter_async_context(
                            ClientSession(read, write)
                        )

                        # Initialize
                        init_result = await session.initialize()
                        log_info(f"  {mcp_name} initialized: {init_result.serverInfo.name}")

                        # Get tools
                        tools_result = await session.list_tools()
                        log_info(f"  {mcp_name} has {len(tools_result.tools)} tools")

                        # Store session and tools
                        sessions_and_tools.append({
                            "mcp_name": mcp_name,
                            "session": session,
                            "tools": tools_result.tools
                        })

                    except Exception as e:
                        log_error(f"Failed to connect to {mcp_name}: {e}")
                        # Continue with other MCPs

                if not sessions_and_tools:
                    return "Error: Failed to connect to any MCPs"

                # Aggregate ALL tools from ALL MCPs
                all_openai_tools = []
                tool_to_session = {}  # Map tool name to session

                for item in sessions_and_tools:
                    mcp_name = item["mcp_name"]
                    session = item["session"]
                    tools = item["tools"]

                    for tool in tools:
                        # Add namespace prefix to avoid collisions
                        # e.g., "read_file" becomes "filesystem__read_file"
                        namespaced_tool_name = f"{mcp_name}__{tool.name}"

                        log_info(f"  - {namespaced_tool_name}: {tool.description[:60]}...")

                        all_openai_tools.append({
                            "type": "function",
                            "function": {
                                "name": namespaced_tool_name,
                                "description": f"[{mcp_name} MCP] {tool.description}",
                                "parameters": tool.inputSchema
                            }
                        })

                        # Map namespaced name to (original_name, session)
                        tool_to_session[namespaced_tool_name] = (tool.name, session)

                log_info(f"Total tools available: {len(all_openai_tools)} from {len(sessions_and_tools)} MCPs")

                # Determine max_tokens
                actual_max_tokens = (
                    self.llm.get_default_max_tokens()
                    if max_tokens == "auto"
                    else max_tokens
                )

                # Execute autonomous loop with ALL tools
                return await self._autonomous_loop_multi_mcp(
                    tool_to_session=tool_to_session,
                    openai_tools=all_openai_tools,
                    task=task,
                    max_rounds=max_rounds,
                    max_tokens=actual_max_tokens
                )

        except ValueError as e:
            log_error(f"Configuration error: {e}")
            return f"Error: {e}"
        except Exception as e:
            log_error(f"Multi-MCP execution failed: {e}")
            import traceback
            log_error(traceback.format_exc())
            return f"Error during multi-MCP execution: {e}"

    async def autonomous_discover_and_execute(
        self,
        task: str,
        max_rounds: int = 100,
        max_tokens: Union[int, str] = "auto"
    ) -> str:
        """
        Execute task with ALL available MCPs discovered from .mcp.json!

        This is the ULTIMATE dynamic solution - the local LLM automatically gets
        access to EVERY tool from EVERY enabled MCP in .mcp.json!

        Args:
            task: Task description for the local LLM
            max_rounds: Maximum autonomous loop iterations
            max_tokens: Maximum tokens per LLM response ("auto" or integer)

        Returns:
            Final answer from the local LLM

        Examples:
            # Let LLM use ANY tool from ANY MCP!
            await agent.autonomous_discover_and_execute(
                task="Read my codebase, fetch relevant docs online, build a knowledge graph, and create comprehensive documentation"
            )

            # LLM has access to EVERYTHING!
            await agent.autonomous_discover_and_execute(
                task="Analyze this project, compare with GitHub repos, fetch best practices, and suggest improvements"
            )
        """
        log_info("=== Auto-Discovery Autonomous Execution ===")
        log_info("Discovering ALL available MCPs from .mcp.json...")

        # HOT RELOAD: Create fresh MCPDiscovery (reads .mcp.json fresh)
        discovery = MCPDiscovery(self.mcp_json_path)

        # Discover all available MCPs
        available_mcps = discovery.list_available_mcps()
        log_info(f"Found {len(available_mcps)} enabled MCPs: {', '.join(available_mcps)}")

        if not available_mcps:
            return "Error: No MCPs available. Check .mcp.json configuration."

        # Execute with ALL MCPs
        return await self.autonomous_with_multiple_mcps(
            mcp_names=available_mcps,
            task=task,
            max_rounds=max_rounds,
            max_tokens=max_tokens
        )

    async def _autonomous_loop(
        self,
        session: ClientSession,
        openai_tools: List[Dict],
        task: str,
        max_rounds: int,
        max_tokens: int
    ) -> str:
        """Core autonomous loop for single MCP."""
        messages = [{"role": "user", "content": task}]

        for round_num in range(max_rounds):
            log_info(f"\n--- Round {round_num + 1}/{max_rounds} ---")

            # Call LLM
            response = self.llm.chat_completion(
                messages=messages,
                tools=openai_tools,
                tool_choice="auto",
                max_tokens=max_tokens
            )

            if not response.get("choices"):
                return "Error: No response from LLM"

            message = response["choices"][0]["message"]
            log_info(f"LLM response: {message.get('content', 'No content')[:100]}...")

            # Check for tool calls
            if message.get("tool_calls"):
                log_info(f"LLM requested {len(message['tool_calls'])} tool call(s)")
                messages.append(message)

                # Execute tools
                for tool_call in message["tool_calls"]:
                    tool_name = tool_call["function"]["name"]
                    tool_args_str = tool_call["function"]["arguments"]

                    try:
                        tool_args = json.loads(tool_args_str)
                    except json.JSONDecodeError:
                        tool_args = {"raw_args": tool_args_str}

                    log_info(f"Executing {tool_name}")

                    try:
                        result = await session.call_tool(tool_name, tool_args)
                        tool_result = (
                            result.content[0].text if result.content
                            else "Tool executed successfully"
                        )
                        log_info(f"Tool result: {str(tool_result)[:200]}...")
                    except Exception as e:
                        tool_result = f"Error: {e}"
                        log_error(f"Tool execution failed: {e}")

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": str(tool_result)
                    })
            else:
                # Final answer
                log_info("LLM provided final answer")
                return message.get("content", "No content in response")

        return "Task incomplete: Maximum rounds reached"

    async def _autonomous_loop_multi_mcp(
        self,
        tool_to_session: Dict[str, tuple],
        openai_tools: List[Dict],
        task: str,
        max_rounds: int,
        max_tokens: int
    ) -> str:
        """Core autonomous loop for multiple MCPs."""
        messages = [{"role": "user", "content": task}]

        for round_num in range(max_rounds):
            log_info(f"\n--- Round {round_num + 1}/{max_rounds} ---")

            # Call LLM
            response = self.llm.chat_completion(
                messages=messages,
                tools=openai_tools,
                tool_choice="auto",
                max_tokens=max_tokens
            )

            if not response.get("choices"):
                return "Error: No response from LLM"

            message = response["choices"][0]["message"]
            log_info(f"LLM response: {message.get('content', 'No content')[:100]}...")

            # Check for tool calls
            if message.get("tool_calls"):
                log_info(f"LLM requested {len(message['tool_calls'])} tool call(s)")
                messages.append(message)

                # Execute tools
                for tool_call in message["tool_calls"]:
                    namespaced_tool_name = tool_call["function"]["name"]
                    tool_args_str = tool_call["function"]["arguments"]

                    try:
                        tool_args = json.loads(tool_args_str)
                    except json.JSONDecodeError:
                        tool_args = {"raw_args": tool_args_str}

                    # Get original tool name and session
                    if namespaced_tool_name not in tool_to_session:
                        tool_result = f"Error: Unknown tool {namespaced_tool_name}"
                    else:
                        original_tool_name, session = tool_to_session[namespaced_tool_name]
                        log_info(f"Executing {namespaced_tool_name} (original: {original_tool_name})")

                        try:
                            result = await session.call_tool(original_tool_name, tool_args)
                            tool_result = (
                                result.content[0].text if result.content
                                else "Tool executed successfully"
                            )
                            log_info(f"Tool result: {str(tool_result)[:200]}...")
                        except Exception as e:
                            tool_result = f"Error: {e}"
                            log_error(f"Tool execution failed: {e}")

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": str(tool_result)
                    })
            else:
                # Final answer
                log_info("LLM provided final answer")
                return message.get("content", "No content in response")

        return "Task incomplete: Maximum rounds reached"


__all__ = [
    "DynamicAutonomousAgent"
]
