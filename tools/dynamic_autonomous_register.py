#!/usr/bin/env python3
"""
Registration module for dynamic autonomous tools.

This registers the truly dynamic MCP tools with FastMCP.
"""

from typing import List, Union, Optional, Annotated
from pydantic import Field
from llm.llm_client import LLMClient
from tools.dynamic_autonomous import DynamicAutonomousAgent


def register_dynamic_autonomous_tools(mcp, llm_client: Optional[LLMClient] = None):
    """
    Register dynamic autonomous tools with FastMCP server.

    These tools enable the local LLM to use ANY MCP discovered from .mcp.json!

    Args:
        mcp: FastMCP server instance
        llm_client: Optional LLM client
    """
    agent = DynamicAutonomousAgent(llm_client)

    @mcp.tool()
    async def autonomous_with_mcp(
        mcp_name: Annotated[str, Field(
            description="Name of the MCP to use (e.g., 'filesystem', 'memory', 'fetch', 'github')"
        )],
        task: Annotated[str, Field(
            min_length=1,
            max_length=10000,
            description="Task for the local LLM to execute autonomously"
        )],
        max_rounds: Annotated[int, Field(
            ge=1,
            description="Maximum rounds for autonomous loop (default: 100)"
        )] = 100,
        max_tokens: Annotated[
            Union[int, str],
            Field(
                description="Maximum tokens per LLM response ('auto' for default, or integer to override)"
            )
        ] = "auto"
    ) -> str:
        """
        Execute task autonomously using tools from a SINGLE MCP.

        The MCP is dynamically discovered from .mcp.json - NO hardcoded configuration!

        This tool works with ANY MCP configured in .mcp.json. As soon as you add
        a new MCP to .mcp.json, it becomes available to this tool automatically!

        Args:
            mcp_name: Name of the MCP to use (must be enabled in .mcp.json)
            task: Task description for the local LLM
            max_rounds: Maximum autonomous loop iterations (default: 100)
            max_tokens: Maximum tokens per LLM response ("auto" or integer)

        Returns:
            Final answer from the local LLM after autonomous tool usage

        Examples:
            # Use filesystem MCP
            autonomous_with_mcp(
                mcp_name="filesystem",
                task="Read README.md and summarize the key features"
            )

            # Use memory MCP
            autonomous_with_mcp(
                mcp_name="memory",
                task="Create an entity called 'Python' with observations about its features"
            )

            # Use fetch MCP
            autonomous_with_mcp(
                mcp_name="fetch",
                task="Fetch https://example.com and summarize the content"
            )

            # Use ANY custom MCP you add to .mcp.json!
            autonomous_with_mcp(
                mcp_name="my-custom-mcp",
                task="Do something with my custom MCP"
            )
        """
        return await agent.autonomous_with_mcp(
            mcp_name=mcp_name,
            task=task,
            max_rounds=max_rounds,
            max_tokens=max_tokens
        )

    @mcp.tool()
    async def autonomous_with_multiple_mcps(
        mcp_names: Annotated[List[str], Field(
            description="List of MCP names to use (e.g., ['filesystem', 'memory', 'fetch'])"
        )],
        task: Annotated[str, Field(
            min_length=1,
            max_length=10000,
            description="Task for the local LLM to execute autonomously"
        )],
        max_rounds: Annotated[int, Field(
            ge=1,
            description="Maximum rounds for autonomous loop (default: 100)"
        )] = 100,
        max_tokens: Annotated[
            Union[int, str],
            Field(
                description="Maximum tokens per LLM response ('auto' for default, or integer to override)"
            )
        ] = "auto"
    ) -> str:
        """
        Execute task autonomously using tools from MULTIPLE MCPs simultaneously!

        This is incredibly powerful - the local LLM can use ANY tool from ANY MCP
        in a SINGLE session. For example, it can read files, create knowledge graph
        entities, and fetch web content all in the same autonomous loop!

        All MCPs are dynamically discovered from .mcp.json - NO hardcoded configuration!

        Args:
            mcp_names: List of MCP names to use (must be enabled in .mcp.json)
            task: Task description for the local LLM
            max_rounds: Maximum autonomous loop iterations (default: 100)
            max_tokens: Maximum tokens per LLM response ("auto" or integer)

        Returns:
            Final answer from the local LLM after using tools from multiple MCPs

        Examples:
            # Use filesystem + memory MCPs
            autonomous_with_multiple_mcps(
                mcp_names=["filesystem", "memory"],
                task="Read all Python files in tools/ and create a knowledge graph of the codebase structure"
            )

            # Use filesystem + fetch + memory MCPs
            autonomous_with_multiple_mcps(
                mcp_names=["filesystem", "fetch", "memory"],
                task="Read local docs, fetch online docs from example.com, compare them, and build a knowledge graph"
            )

            # Use filesystem + github + memory MCPs
            autonomous_with_multiple_mcps(
                mcp_names=["filesystem", "github", "memory"],
                task="Analyze local repo, search GitHub for similar projects, and create a knowledge graph of similarities"
            )
        """
        return await agent.autonomous_with_multiple_mcps(
            mcp_names=mcp_names,
            task=task,
            max_rounds=max_rounds,
            max_tokens=max_tokens
        )

    @mcp.tool()
    async def autonomous_discover_and_execute(
        task: Annotated[str, Field(
            min_length=1,
            max_length=10000,
            description="Task for the local LLM to execute autonomously"
        )],
        max_rounds: Annotated[int, Field(
            ge=1,
            description="Maximum rounds for autonomous loop (default: 100)"
        )] = 100,
        max_tokens: Annotated[
            Union[int, str],
            Field(
                description="Maximum tokens per LLM response ('auto' for default, or integer to override)"
            )
        ] = "auto"
    ) -> str:
        """
        Execute task with ALL available MCPs discovered from .mcp.json!

        This is the ULTIMATE dynamic solution - the local LLM automatically gets
        access to EVERY tool from EVERY enabled MCP in .mcp.json!

        As soon as you add a new MCP to .mcp.json and enable it, the local LLM
        can use its tools - NO code changes required!

        Args:
            task: Task description for the local LLM
            max_rounds: Maximum autonomous loop iterations (default: 100)
            max_tokens: Maximum tokens per LLM response ("auto" or integer)

        Returns:
            Final answer from the local LLM after using any tools from any MCPs

        Examples:
            # Let LLM use ANY tool from ANY MCP!
            autonomous_discover_and_execute(
                task="Read my codebase, fetch relevant docs online, build a knowledge graph, and create comprehensive documentation"
            )

            # LLM has access to EVERYTHING!
            autonomous_discover_and_execute(
                task="Analyze this project, compare with similar GitHub repos, fetch best practices from web, and suggest improvements"
            )

            # Works with ANY MCPs in .mcp.json!
            autonomous_discover_and_execute(
                task="Use any tools you need from any available MCPs to complete this complex task"
            )
        """
        return await agent.autonomous_discover_and_execute(
            task=task,
            max_rounds=max_rounds,
            max_tokens=max_tokens
        )

    @mcp.tool()
    async def list_available_mcps() -> str:
        """
        List all available MCPs discovered from .mcp.json.

        This tool shows which MCPs are currently enabled and available for
        the local LLM to use with the autonomous tools.

        Returns:
            Formatted string listing all available MCPs with their descriptions

        Example:
            list_available_mcps()
            # Returns:
            # Available MCPs (5):
            # 1. filesystem - MCP server: @modelcontextprotocol/server-filesystem
            # 2. memory - MCP server: @modelcontextprotocol/server-memory
            # 3. fetch - MCP server: mcp-server-fetch
            # 4. github - MCP server: @modelcontextprotocol/server-github
            # 5. python-interpreter - MCP server: mcp-server-python-interpreter
        """
        try:
            from mcp_client.discovery import get_mcp_discovery

            discovery = get_mcp_discovery()
            mcps = discovery.list_all_mcps_info()

            if not mcps:
                return "No MCPs available. Check .mcp.json configuration."

            result = f"Available MCPs ({len(mcps)}):\n\n"
            for i, mcp in enumerate(mcps, 1):
                result += f"{i}. {mcp['name']}\n"
                result += f"   Command: {mcp['command']} {' '.join(mcp['args'][:2])}\n"
                result += f"   Description: {mcp['description']}\n"
                if mcp['env']:
                    result += f"   Env vars: {', '.join(mcp['env'].keys())}\n"
                result += "\n"

            result += f"To use any of these MCPs, call:\n"
            result += f"  autonomous_with_mcp(mcp_name='<name>', task='<task>')\n"
            result += f"  autonomous_with_multiple_mcps(mcp_names=['<name1>', '<name2>'], task='<task>')\n"
            result += f"  autonomous_discover_and_execute(task='<task>')  # Uses ALL MCPs!\n"

            return result

        except Exception as e:
            return f"Error listing MCPs: {e}"


__all__ = [
    "register_dynamic_autonomous_tools"
]
