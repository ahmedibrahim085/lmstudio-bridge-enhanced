#!/usr/bin/env python3
"""
Registration module for dynamic autonomous tools.

This registers the truly dynamic MCP tools with FastMCP.
"""

import logging
from typing import List, Union, Optional, Annotated
from pydantic import Field
from config.constants import DEFAULT_MAX_TOKENS, DEFAULT_VISION_DETAIL

logger = logging.getLogger(__name__)
from llm.llm_client import LLMClient
from tools.dynamic_autonomous import DynamicAutonomousAgent, DEFAULT_MAX_ROUNDS


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
            description="Maximum rounds for autonomous loop (default: 10000, no artificial limit - lets local LLM work until task complete)"
        )] = DEFAULT_MAX_ROUNDS,
        max_tokens: Annotated[
            Union[int, str],
            Field(
                description="Maximum tokens per LLM response ('auto' for default, or integer to override)"
            )
        ] = "auto",
        model: Annotated[Optional[str], Field(
            description="Optional model name to use (None = use default model from config, 'default' = use default, or specify model by name)"
        )] = None
    ) -> str:
        """
        Execute task autonomously using tools from a SINGLE MCP server.

        This delegates the task to a LOCAL LLM which autonomously uses MCP tools to complete it.

        ⚠️ **MULTI-MODEL DELEGATION - CRITICAL PARAMETER** ⚠️

        **To ask a SPECIFIC LOCAL MODEL to do the task, use the `model` parameter:**

        ```python
        # ✅ CORRECT - Delegate to gemma-3
        autonomous_with_mcp(
            mcp_name="filesystem",
            task="Generate a happy cat description",
            model="google/gemma-3-12b"  # ← THIS specifies which model does the work!
        )

        # ✅ CORRECT - Delegate to qwen coder
        autonomous_with_mcp(
            mcp_name="filesystem",
            task="Write Python code",
            model="qwen/qwen3-coder-30b"  # ← THIS model will write the code!
        )

        # ❌ WRONG - Missing model parameter (uses default model)
        autonomous_with_mcp(
            mcp_name="filesystem",
            task="Tell google/gemma-3 to generate photo"
            # ← NO MODEL PARAMETER = default model does it, NOT gemma-3!
        )

        # ❌ VERY WRONG - Calling wrong tool
        lms_ensure_model_loaded("gemma-3")  # ← This is for PRELOADING, NOT delegation!
        autonomous_with_mcp(...)  # ← Still uses default model!
        ```

        **When User Says**: "Tell [model name] to do [task]"
        **You MUST Pass**: `model="[exact model name]"` parameter!

        **Examples of User Requests → Your Parameters:**
        - User: "Ask gemma-3 to generate cat photo" → `model="google/gemma-3-12b"`
        - User: "Tell qwen coder to write code" → `model="qwen/qwen3-coder-30b"`
        - User: "Have the thinking model analyze this" → `model="qwen/qwen3-4b-thinking-2507"`

        ## When to Use This Tool
        ✅ Use when:
        - User requests file/directory operations → use mcp_name="filesystem"
        - User requests web content fetching → use mcp_name="fetch"
        - User requests knowledge storage/retrieval → use mcp_name="memory"
        - User requests GitHub operations → use mcp_name="github"
        - Task clearly needs ONE specific MCP's tools
        - **User requests a SPECIFIC MODEL to do a task** → use `model` parameter!

        ❌ Do NOT use for:
        - Simple questions you can answer → Answer directly!
        - Tasks requiring multiple MCPs → Use autonomous_with_multiple_mcps instead
        - Conversational responses → You handle conversation!
        - General knowledge questions → No MCP needed!

        ## MCP Selection Decision Tree 🌳
        **Which MCP should I use?**

        📁 **filesystem** - Choose when task mentions:
        - "read file", "write file", "create directory", "list files"
        - "search for", "find all", "analyze code", "modify file"
        - Working with local files/directories
        - Examples: "Read README.md", "Find all Python files", "Create config.json"

        🌐 **fetch** - Choose when task mentions:
        - "fetch URL", "download webpage", "get website content"
        - "retrieve from", "access online", "web content"
        - Working with web resources
        - Examples: "Fetch docs from example.com", "Download webpage content"

        🧠 **memory** - Choose when task mentions:
        - "remember", "store knowledge", "create entity", "knowledge graph"
        - "recall", "search knowledge", "add observation"
        - Building/querying knowledge structures
        - Examples: "Remember user prefers Python", "Create knowledge graph"

        💻 **github** - Choose when task mentions:
        - "GitHub", "repository", "pull request", "issue"
        - "search repos", "create PR", "list issues"
        - GitHub-specific operations
        - Examples: "Create issue in my repo", "List all open PRs"

        ## Multimedia & Content Types 🎨🖼️📹
        **Local LLM can request ANY content through MCPs**:
        - ✅ Text files, code, markdown (always supported)
        - ✅ Images, audio, video (if MCP and LLM support it)
        - ✅ Documents, data files, binaries

        **Content Handling**: Local LLM decides accept/reject based on its capabilities.

        ## Examples
        ✅ CORRECT:
        User: "Read my README file and summarize it"
        Action: autonomous_with_mcp(mcp_name="filesystem", task="Read README.md and summarize")
        Reason: File operation → filesystem MCP

        ✅ CORRECT:
        User: "Fetch Python docs and extract async features"
        Action: autonomous_with_mcp(mcp_name="fetch", task="Fetch python.org/asyncio docs...")
        Reason: Web fetching → fetch MCP

        ❌ INCORRECT:
        User: "What is Python?"
        Wrong: autonomous_with_mcp(mcp_name="fetch", task="What is Python?")
        Correct: Answer directly - "Python is a high-level programming language..."
        Reason: General knowledge question - no MCP needed!

        ❌ INCORRECT:
        User: "Hello, how are you?"
        Wrong: autonomous_with_mcp(mcp_name="filesystem", task="Hello")
        Correct: Answer directly - "I'm here to help! What can I do for you?"
        Reason: Conversational greeting - YOU handle this!

        Args:
            mcp_name: MCP server name ('filesystem', 'memory', 'fetch', 'github', or any custom MCP)
            task: Task description for the local LLM to execute
            max_rounds: Maximum autonomous loop iterations (default: 10000)
            max_tokens: Maximum tokens per LLM response ("auto" or integer)
            model: Optional specific model to use

        Returns:
            Final answer from the local LLM after autonomous tool usage

        Note: The MCP is dynamically discovered from .mcp.json - NO hardcoded configuration!
        """
        return await agent.autonomous_with_mcp(
            mcp_name=mcp_name,
            task=task,
            max_rounds=max_rounds,
            max_tokens=max_tokens,
            model=model
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
            description="Maximum rounds for autonomous loop (default: 10000, no artificial limit - lets local LLM work until task complete)"
        )] = DEFAULT_MAX_ROUNDS,
        max_tokens: Annotated[
            Union[int, str],
            Field(
                description="Maximum tokens per LLM response ('auto' for default, or integer to override)"
            )
        ] = "auto",
        model: Annotated[Optional[str], Field(
            description="Optional model name to use (None = use default model from config, 'default' = use default, or specify model by name)"
        )] = None
    ) -> str:
        """
        Execute task autonomously using tools from MULTIPLE MCP servers simultaneously.

        This delegates to LOCAL LLM which can use ANY tool from ANY specified MCP in single session.

        ⚠️ **MULTI-MODEL DELEGATION - CRITICAL PARAMETER** ⚠️

        **To ask a SPECIFIC LOCAL MODEL to do the task, use the `model` parameter:**

        ```python
        # ✅ CORRECT - Delegate to gemma-3 with multiple MCPs
        autonomous_with_multiple_mcps(
            mcp_names=["filesystem", "memory"],
            task="Analyze files and build knowledge graph",
            model="google/gemma-3-12b"  # ← THIS specifies which model does the work!
        )

        # ❌ WRONG - Missing model parameter (uses default model)
        autonomous_with_multiple_mcps(
            mcp_names=["filesystem", "fetch"],
            task="Tell google/gemma-3 to compare docs"
            # ← NO MODEL PARAMETER = default model does it, NOT gemma-3!
        )
        ```

        **When User Says**: "Tell [model name] to do [task]"
        **You MUST Pass**: `model="[exact model name]"` parameter!

        ## When to Use This Tool
        ✅ Use when task requires:
        - Reading local files AND fetching web content
        - File operations AND knowledge graph creation
        - Multiple data sources (local + web + GitHub)
        - Cross-MCP workflows (e.g., "Read file, fetch docs, build knowledge graph")

        ❌ Do NOT use for:
        - Single MCP tasks → Use autonomous_with_mcp instead (simpler)
        - Simple questions → Answer directly!
        - Conversational responses → You handle conversation!
        - When you don't know which MCPs needed → Use autonomous_discover_and_execute

        ## Common MCP Combinations 🔗
        **When to combine MCPs:**

        📁+🧠 **filesystem + memory**:
        - "Analyze codebase and build knowledge graph"
        - "Read files and store findings in knowledge base"

        🌐+📁 **fetch + filesystem**:
        - "Download docs and compare with local docs"
        - "Fetch examples and save locally"

        📁+💻 **filesystem + github**:
        - "Analyze local repo and compare with GitHub projects"
        - "Read code and create GitHub issue with findings"

        📁+🌐+🧠 **filesystem + fetch + memory**:
        - "Read local docs, fetch online docs, compare, and build knowledge graph"

        ## Multimedia & Content Types 🎨🖼️📹
        **Local LLM can request ANY content through MCPs**:
        - ✅ Files, images, audio, video, documents, data

        **Content Handling**: Local LLM decides accept/reject based on capabilities.

        ## Examples
        ✅ CORRECT:
        User: "Read Python files and create knowledge graph"
        Action: autonomous_with_multiple_mcps(mcp_names=["filesystem", "memory"], task="...")
        Reason: Needs filesystem (read) + memory (knowledge graph)

        ✅ CORRECT:
        User: "Fetch docs online and compare with local files"
        Action: autonomous_with_multiple_mcps(mcp_names=["fetch", "filesystem"], task="...")
        Reason: Needs fetch (web) + filesystem (local files)

        ❌ INCORRECT:
        User: "Read README file"
        Wrong: autonomous_with_multiple_mcps(mcp_names=["filesystem"], task="Read README")
        Correct: autonomous_with_mcp(mcp_name="filesystem", task="Read README")
        Reason: Only needs ONE MCP - use simpler tool!

        ❌ INCORRECT:
        User: "What is the capital of France?"
        Wrong: autonomous_with_multiple_mcps(mcp_names=["fetch"], task="What is capital of France?")
        Correct: Answer directly - "The capital of France is Paris"
        Reason: General knowledge - no MCP needed!

        Args:
            mcp_names: List of MCP server names to use simultaneously
            task: Task description for the local LLM to execute
            max_rounds: Maximum autonomous loop iterations (default: 10000)
            max_tokens: Maximum tokens per LLM response ("auto" or integer)
            model: Optional specific model to use

        Returns:
            Final answer from the local LLM after using tools from multiple MCPs

        Note: Local LLM can use ANY tool from ANY specified MCP in a single autonomous session!
        """
        return await agent.autonomous_with_multiple_mcps(
            mcp_names=mcp_names,
            task=task,
            max_rounds=max_rounds,
            max_tokens=max_tokens,
            model=model
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
            description="Maximum rounds for autonomous loop (default: 10000, no artificial limit - lets local LLM work until task complete)"
        )] = DEFAULT_MAX_ROUNDS,
        max_tokens: Annotated[
            Union[int, str],
            Field(
                description="Maximum tokens per LLM response ('auto' for default, or integer to override)"
            )
        ] = "auto",
        model: Annotated[Optional[str], Field(
            description="Optional model name to use (None = use default model from config, 'default' = use default, or specify model by name)"
        )] = None
    ) -> str:
        """
        Execute task with ALL available MCP servers auto-discovered from .mcp.json.

        This delegates to LOCAL LLM with access to EVERY tool from EVERY enabled MCP!

        ⚠️ **MULTI-MODEL DELEGATION - CRITICAL PARAMETER** ⚠️

        **To ask a SPECIFIC LOCAL MODEL to do the task, use the `model` parameter:**

        ```python
        # ✅ CORRECT - Delegate complex task to gemma-3
        autonomous_discover_and_execute(
            task="Analyze project and create comprehensive docs",
            model="google/gemma-3-12b"  # ← THIS specifies which model does the work!
        )

        # ❌ WRONG - Missing model parameter (uses default model)
        autonomous_discover_and_execute(
            task="Tell google/gemma-3 to analyze project"
            # ← NO MODEL PARAMETER = default model does it, NOT gemma-3!
        )
        ```

        **When User Says**: "Tell [model name] to do [task]"
        **You MUST Pass**: `model="[exact model name]"` parameter!

        ## When to Use This Tool
        ✅ Use when:
        - Complex task and you're unsure which MCPs needed
        - Task might require multiple different MCPs
        - Want local LLM to decide which tools to use
        - Maximum flexibility needed

        ❌ Do NOT use for:
        - You know exactly which MCP needed → Use autonomous_with_mcp (more efficient)
        - Simple questions → Answer directly!
        - Conversational responses → You handle conversation!
        - Tasks clearly needing specific MCPs → Use autonomous_with_mcp/autonomous_with_multiple_mcps

        ## When This Tool Shines ✨
        **Best for:**
        - Complex multi-stage workflows
        - Tasks with unpredictable tool needs
        - "Figure it out" scenarios where local LLM chooses approach
        - Maximum tool availability

        **Trade-off**: Presents ALL tools (can be 50+) → May overwhelm smaller models

        ## Multimedia & Content Types 🎨🖼️📹
        **Local LLM can request ANY content through ANY MCP**:
        - ✅ Everything supported by all configured MCPs

        **Content Handling**: Local LLM decides what to request based on available tools.

        ## Examples
        ✅ CORRECT:
        User: "Analyze project and create comprehensive documentation"
        Action: autonomous_discover_and_execute(task="Analyze project...")
        Reason: Complex task, unclear which MCPs needed - let LLM figure it out

        ✅ CORRECT:
        User: "Do whatever is needed to improve this codebase"
        Action: autonomous_discover_and_execute(task="Improve codebase")
        Reason: Open-ended task - LLM needs access to all tools

        ❌ INCORRECT:
        User: "Read README file"
        Wrong: autonomous_discover_and_execute(task="Read README")
        Correct: autonomous_with_mcp(mcp_name="filesystem", task="Read README")
        Reason: Clearly needs filesystem only - be specific!

        ❌ INCORRECT:
        User: "What's 2+2?"
        Wrong: autonomous_discover_and_execute(task="What's 2+2?")
        Correct: Answer directly - "4"
        Reason: Simple calculation - no tools needed!

        Args:
            task: Task description for the local LLM to execute
            max_rounds: Maximum autonomous loop iterations (default: 10000)
            max_tokens: Maximum tokens per LLM response ("auto" or integer)
            model: Optional specific model to use

        Returns:
            Final answer from the local LLM after using any tools from any MCPs

        Note: Gives local LLM access to ALL tools from ALL MCPs - powerful but can present 50+ tools!
        """
        return await agent.autonomous_discover_and_execute(
            task=task,
            max_rounds=max_rounds,
            max_tokens=max_tokens,
            model=model
        )

    @mcp.tool()
    async def list_available_mcps() -> str:
        """
        List all available MCP servers discovered from .mcp.json configuration.

        ## When to Use This Tool
        ✅ Use when:
        - User asks "what MCPs are available?"
        - User asks "what can the local LLM do?"
        - You need to know which MCPs are configured
        - Debugging tool availability

        ❌ Do NOT use for:
        - You already know which MCPs to use
        - Every single task (wasteful)

        Returns:
            Formatted string listing all available MCPs with their descriptions

        Example output:
            Available MCPs (5):
            1. filesystem - MCP server: @modelcontextprotocol/server-filesystem
            2. memory - MCP server: @modelcontextprotocol/server-memory
            3. fetch - MCP server: mcp-server-fetch
            4. github - MCP server: @modelcontextprotocol/server-github
            5. python-interpreter - MCP server: mcp-server-python-interpreter

            To use any of these MCPs, call:
              autonomous_with_mcp(mcp_name='<name>', task='<task>')
              autonomous_with_multiple_mcps(mcp_names=['<name1>', '<name2>'], task='<task>')
              autonomous_discover_and_execute(task='<task>')  # Uses ALL MCPs!

        Note: MCPs are dynamically discovered from .mcp.json configuration.
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
            logger.error("Error listing MCPs: %s", e, exc_info=True)
            return f"Error listing MCPs: {e}"

    @mcp.tool()
    async def autonomous_with_images(
        mcp_name: Annotated[str, Field(
            description="Name of the MCP to use (e.g., 'filesystem', 'memory', 'fetch')"
        )],
        task: Annotated[str, Field(
            min_length=1,
            max_length=10000,
            description="Task for the local LLM to execute autonomously"
        )],
        images: Annotated[List[str], Field(
            description="List of image inputs: file paths, URLs, or base64 strings"
        )],
        max_rounds: Annotated[int, Field(
            ge=1,
            description="Maximum rounds for autonomous loop (default: 10000)"
        )] = DEFAULT_MAX_ROUNDS,
        max_tokens: Annotated[int, Field(
            description="Maximum tokens per LLM response"
        )] = DEFAULT_MAX_TOKENS,
        model: Annotated[Optional[str], Field(
            description="Optional model name to use (None = default)"
        )] = None,
        detail: Annotated[str, Field(
            description="Vision detail level ('auto', 'low', 'high')"
        )] = DEFAULT_VISION_DETAIL,
    ) -> str:
        """Execute task autonomously with image inputs using tools from a SINGLE MCP.

        Combines multi-modal image processing with autonomous MCP tool execution.
        Images are processed and their metadata is included in the task context
        so the LLM can reason about visual content while using MCP tools.

        Supports file paths, URLs, and base64-encoded images.

        Args:
            mcp_name: MCP server name
            task: Task description for the local LLM
            images: List of image inputs (file paths, URLs, or base64 strings)
            max_rounds: Maximum autonomous loop iterations
            max_tokens: Maximum tokens per LLM response
            model: Optional specific model to use
            detail: Vision detail level

        Returns:
            Final answer from the local LLM after autonomous tool usage with images
        """
        return await agent.autonomous_with_images(
            mcp_name=mcp_name,
            task=task,
            images=images,
            max_rounds=max_rounds,
            max_tokens=max_tokens,
            model=model,
            detail=detail,
        )


__all__ = [
    "register_dynamic_autonomous_tools"
]
