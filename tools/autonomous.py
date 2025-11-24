#!/usr/bin/env python3
"""
Autonomous execution tool - allows local LLMs to autonomously use MCP tools.

This tool validates the orchestrator pattern where our MCP acts as both
server (serving Claude) and client (connecting to other battle-tested MCPs).
"""

from typing import Optional, Union, List, Dict, Any, Annotated
from pydantic import Field
from mcp_client.connection import MCPConnection
from mcp_client.tool_discovery import ToolDiscovery, SchemaConverter
from mcp_client.executor import ToolExecutor
from mcp_client.persistent_session import PersistentMCPSession
from llm.llm_client import LLMClient
from utils.validation import (
    validate_working_directory,  # Keep for filesystem/security checks
    ValidationError
)
from utils.lms_helper import LMSHelper
from config.constants import (
    DEFAULT_MCP_NPX_COMMAND,
    DEFAULT_MCP_NPX_ARGS,
    MCP_PACKAGES,
    DEFAULT_MAX_ROUNDS
)
import html
import json
import os
import logging

logger = logging.getLogger(__name__)


class AutonomousExecutionTools:
    """Tools for autonomous execution with MCP integration."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """Initialize autonomous execution tools.

        Args:
            llm_client: Optional LLM client (creates default if None)
        """
        self.llm = llm_client or LLMClient()

    # Private helper methods for consolidated implementation

    def _format_response_with_reasoning(self, message: dict) -> str:
        """Extract and format response with reasoning if available.

        Handles two reasoning field formats observed in comprehensive testing:
        - reasoning_content: Used by 10/11 models (DeepSeek, Magistral, Qwen-thinking)
        - reasoning: Used by GPT-OSS only (1/11 models)

        Priority: reasoning_content > reasoning

        Evidence-based safety features:
        1. Empty string handling: Gemma-3-12b observed returning 0B reasoning_content
           (COMPREHENSIVE_MODEL_TESTING.md line ~184)
        2. HTML escaping: XSS prevention (OWASP Top 10 #3, 15,000+ vulnerabilities/year)
           Even terminal output can be logged to web-based log viewers
        3. 20000-char truncation: DeepSeek R1 shows 5x scaling (1.4KB → 6.6KB with high effort)
           (COMPREHENSIVE_MODEL_TESTING.md line ~221)
           Updated limit allows for extended reasoning display from advanced models
        4. Type safety: str() conversion handles API evolution (LM Studio v0.3.9 added reasoning_content)
           Protects against future API changes where field type might change

        Args:
            message: LLM response message dict with optional reasoning fields
                     Format: {"content": "...", "reasoning_content": "...", "reasoning": "..."}

        Returns:
            Formatted string with reasoning (if available) + final answer
            Format with reasoning:
                **Reasoning Process:**
                [reasoning content]

                **Final Answer:**
                [content]
            Format without reasoning:
                [content only]

        Examples:
            >>> # Standard reasoning_content (10/11 models)
            >>> message = {
            ...     "content": "The answer is 42",
            ...     "reasoning_content": "First, I analyzed the question..."
            ... }
            >>> result = self._format_response_with_reasoning(message)
            >>> "**Reasoning Process:**" in result
            True
            >>> "First, I analyzed the question..." in result
            True

            >>> # reasoning field only (GPT-OSS)
            >>> message = {
            ...     "content": "The sky is blue",
            ...     "reasoning": "Light scattering analysis..."
            ... }
            >>> result = self._format_response_with_reasoning(message)
            >>> "Light scattering analysis..." in result
            True

            >>> # No reasoning (baseline models like Qwen3-coder)
            >>> message = {"content": "def add(a, b):\\n    return a + b"}
            >>> result = self._format_response_with_reasoning(message)
            >>> "**Reasoning Process:**" not in result
            True

            >>> # Empty reasoning_content (Gemma-3-12b edge case)
            >>> message = {
            ...     "content": "Answer",
            ...     "reasoning_content": ""  # Empty string
            ... }
            >>> result = self._format_response_with_reasoning(message)
            >>> result
            'Answer'

            >>> # HTML in reasoning (XSS test - OWASP #3)
            >>> message = {
            ...     "content": "Safe",
            ...     "reasoning_content": "<script>alert('XSS')</script> Normal text"
            ... }
            >>> result = self._format_response_with_reasoning(message)
            >>> "<script>" not in result  # Should be escaped
            True
            >>> "&lt;script&gt;" in result  # HTML escaped
            True

            >>> # Very long reasoning (truncation test)
            >>> message = {
            ...     "content": "Answer",
            ...     "reasoning_content": "A" * 25000  # 25KB
            ... }
            >>> result = self._format_response_with_reasoning(message)
            >>> len(result.split("**Final Answer:**")[0]) < 20100  # Truncated at 20K
            True
        """
        # Extract content
        content = message.get("content", "")

        # Get reasoning fields
        reasoning_content = message.get("reasoning_content")
        reasoning = message.get("reasoning")

        # Explicit priority: prefer reasoning_content if it has content
        # This handles the Gemma-3-12b case where reasoning_content is empty string
        # Evidence: COMPREHENSIVE_MODEL_TESTING.md shows Gemma-3-12b returned 0B reasoning_content
        if reasoning_content is not None and str(reasoning_content).strip():
            reasoning = reasoning_content
        else:
            # Fallback to reasoning field (GPT-OSS uses this naming)
            # Evidence: Testing showed 1/11 models (GPT-OSS) uses "reasoning" not "reasoning_content"
            reasoning = reasoning

        # Process reasoning if available
        if reasoning is not None:
            # Convert to string once (type safety - handles API changes)
            # Evidence: LM Studio v0.3.9 added reasoning_content field
            # Future API versions might change field types (e.g., dict with metadata)
            str_reasoning = str(reasoning)
            stripped_reasoning = str_reasoning.strip()

            if stripped_reasoning:
                # Sanitize for XSS prevention (OWASP Top 10 #3)
                # Evidence: 15,000+ XSS vulnerabilities reported annually
                # Even terminal output can be logged to web-based log viewers
                # This is defensive security, not paranoia
                sanitized_reasoning = html.escape(stripped_reasoning)

                # Truncate if too long (based on observed scaling behavior)
                # Evidence: DeepSeek R1 with reasoning_effort="high" shows 5x increase
                # 1.4KB baseline → 6.6KB with high effort (COMPREHENSIVE_MODEL_TESTING.md)
                # Extrapolation: Future models could hit 10KB-20KB+ with extended reasoning
                # Updated: 20000 chars ≈ allows for extended reasoning display
                if len(sanitized_reasoning) > 20000:
                    sanitized_reasoning = sanitized_reasoning[:19997] + "..."

                # Ensure content is clean
                content = content.strip() if content else ""

                # Format with reasoning - using markdown for better readability
                return (
                    f"**Reasoning Process:**\n"
                    f"{sanitized_reasoning}\n\n"
                    f"**Final Answer:**\n"
                    f"{content}"
                )

        # No reasoning available or reasoning was empty - return content only
        return content if content else "No content in response"

    async def _execute_autonomous_with_tools(
        self,
        task: str,
        session: Any,
        openai_tools: List[Dict],
        executor: ToolExecutor,
        max_rounds: int,
        max_tokens: int,
        model: Optional[str] = None,
        response_format: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Core implementation using chat_completion API with explicit tool result passing.

        This implementation WORKS correctly by explicitly passing tool results back
        to the LLM via messages array. This is the proven pattern from autonomous_persistent_session.

        Uses chat_completion API instead of create_response because we need explicit
        control over tool result passing. The create_response API does not currently
        support local tool result passing in a way we understand.

        This is part of Option 4A implementation (user's suggestion).
        Status: WORKING implementation for tool execution
        Date: 2025-10-31

        Args:
            task: The task for the local LLM
            session: Active MCP session
            openai_tools: List of tools in OpenAI format
            executor: Tool executor for the session
            max_rounds: Maximum rounds for autonomous loop
            max_tokens: Maximum tokens per response
            model: Optional model to use (overrides default)
            response_format: Optional structured output format (json_object or json_schema)

        Returns:
            Final answer from the LLM
        """
        # Build messages array (explicit history management)
        messages = [{"role": "user", "content": task}]

        for round_num in range(max_rounds):
            # Call chat_completion with tools
            response = self.llm.chat_completion(
                messages=messages,
                tools=openai_tools,
                tool_choice="auto",
                max_tokens=max_tokens,
                model=model,
                response_format=response_format
            )

            message = response["choices"][0]["message"]

            # Check for tool calls
            if message.get("tool_calls"):
                # Add assistant message to history
                messages.append(message)

                # Execute each tool
                for tool_call in message["tool_calls"]:
                    tool_name = tool_call["function"]["name"]
                    tool_args = json.loads(tool_call["function"]["arguments"])

                    # Execute via MCP
                    result = await executor.execute_tool(tool_name, tool_args)
                    content = ToolExecutor.extract_text_content(result)

                    # ← CRITICAL: Explicitly add tool result to messages
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": content
                    })

                # Continue loop (LLM will see tool results in next call)
                continue
            else:
                # No tool calls - this is the final answer
                return self._format_response_with_reasoning(message)

        return f"Max rounds ({max_rounds}) reached without final answer."

    async def autonomous_filesystem_full(
        self,
        task: str,
        working_directory: Optional[Union[str, List[str]]] = None,
        max_rounds: int = DEFAULT_MAX_ROUNDS,
        max_tokens: Union[int, str] = "auto",
        model: Optional[str] = None,
        response_format: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Full autonomous execution with ALL 14 filesystem MCP tools.

        Now optimized to use stateful /v1/responses API (98% token savings!).
        This function has been internally optimized while maintaining the same
        external interface.

        Provides local LLM access to complete filesystem operations:
        - read_text_file, read_media_file, read_multiple_files
        - write_file, edit_file
        - create_directory, list_directory, directory_tree
        - move_file, search_files, get_file_info
        - list_allowed_directories

        Args:
            task: The task for the local LLM
            working_directory: Directory or list of directories for filesystem operations (optional, uses current directory if not provided)
            max_rounds: Maximum rounds for autonomous loop (default: 100)
            max_tokens: Maximum tokens per response ("auto" for safe default, or integer, default: "auto")
            model: Optional model to use for this task (overrides configured default)

        Returns:
            Local LLM's final answer after autonomous tool usage

        Raises:
            ValidationError: If input parameters are invalid
            Exception: If autonomous execution fails

        Examples:
            # Auto-detect working directory (uses current project)
            autonomous_filesystem_full("Search for all Python files and list them")

            # Single working directory
            autonomous_filesystem_full(
                "Read README.md",
                working_directory="/path/to/project"
            )

            # Multiple working directories (work across multiple projects!)
            autonomous_filesystem_full(
                "Find all TODO comments across both projects",
                working_directory=[
                    "/path/to/project1",
                    "/path/to/project2"
                ]
            )

            # Complex task with custom limits
            autonomous_filesystem_full(
                "Analyze entire codebase and create documentation",
                max_rounds=500,
                max_tokens=8192
            )
        """
        try:
            # 1. Determine max_tokens (Pydantic handles type/range validation)
            if max_tokens == "auto":
                # Use safe default (LM Studio API doesn't expose model's max_context_length)
                actual_max_tokens = self.llm.get_default_max_tokens()
            else:
                # Pydantic already validated it's an int >= 1
                actual_max_tokens = max_tokens

            # 2. Determine working directory/directories (custom validation for filesystem/security)
            if working_directory:
                # User provided directory/directories - validate them
                working_dirs = validate_working_directory(working_directory)
            else:
                # Use current working directory (Claude Code's project directory)
                # This can be overridden by WORKING_DIR environment variable
                default_dir = os.getenv("WORKING_DIR") or os.getcwd()
                # Validate the auto-detected directory
                working_dirs = validate_working_directory(default_dir)

            # Ensure working_dirs is a list for consistent handling
            if isinstance(working_dirs, str):
                working_dirs = [working_dirs]

            # 2.5. PROACTIVE MODEL PRELOADING (Fallback mechanism)
            # Ensure model is loaded before starting autonomous execution
            # This prevents HTTP 404 errors from JIT model auto-unloading
            model_to_use = self.llm.model

            if LMSHelper.is_installed():
                logger.info(f"LMS CLI detected - ensuring model loaded: {model_to_use}")
                try:
                    if LMSHelper.ensure_model_loaded(model_to_use):
                        logger.info(f"✅ Model '{model_to_use}' preloaded and kept loaded (prevents 404)")
                    else:
                        logger.warning(f"⚠️  Could not preload model '{model_to_use}' with LMS CLI")
                except Exception as e:
                    logger.warning(f"⚠️  Error during model preload: {e}")
            else:
                logger.warning(
                    "⚠️  LMS CLI not installed - model may auto-unload causing intermittent 404 errors. "
                    "Install for better reliability: brew install lmstudio-ai/lms/lms"
                )

            # 3. Connect to filesystem MCP with working directory/directories
            # Pass all directories as separate arguments
            connection_args = DEFAULT_MCP_NPX_ARGS + [MCP_PACKAGES["filesystem"]]
            # Add all directories to args
            connection_args.extend(working_dirs)

            connection = MCPConnection(
                command=DEFAULT_MCP_NPX_COMMAND,
                args=connection_args
            )

            async with connection.connect() as session:
                # 2. Discover ALL tools from filesystem MCP
                discovery = ToolDiscovery(session)
                all_tools = await discovery.discover_tools()

                # 3. Convert ALL tools to OpenAI format
                openai_tools = SchemaConverter.mcp_tools_to_openai(all_tools)
                executor = ToolExecutor(session)

                # Uses chat_completion API with explicit tool result passing
                # See Option 4A implementation: OPTION_4A_IMPLEMENTATION_PLAN.md
                return await self._execute_autonomous_with_tools(
                    task=task,
                    session=session,
                    openai_tools=openai_tools,
                    executor=executor,
                    max_rounds=max_rounds,
                    max_tokens=actual_max_tokens,
                    model=model,
                    response_format=response_format
                )

        except Exception as e:
            import traceback
            return f"Error during full filesystem execution: {str(e)}\n\n{traceback.format_exc()}"

    async def create_persistent_session(
        self,
        working_directory: Optional[Union[str, List[str]]] = None
    ) -> PersistentMCPSession:
        """Create a persistent MCP session with Roots Protocol support.

        This creates a long-lived session that allows:
        - Multiple autonomous tasks in the same session
        - Dynamic directory updates without reconnecting
        - Better performance (no connection overhead per task)

        Args:
            working_directory: Initial directory or directories (optional)

        Returns:
            PersistentMCPSession instance

        Example:
            async with tools.create_persistent_session(["/project1"]) as session:
                # Task 1 in project1
                result1 = await session.execute_autonomous_task("Read README.md")

                # Add project2 dynamically
                await session.add_root("/project2")

                # Task 2 across both projects
                result2 = await session.execute_autonomous_task("Compare files")
        """
        # Determine initial roots
        if working_directory:
            working_dirs = validate_working_directory(working_directory)
        else:
            default_dir = os.getenv("WORKING_DIR") or os.getcwd()
            working_dirs = validate_working_directory(default_dir)

        # Ensure list
        if isinstance(working_dirs, str):
            working_dirs = [working_dirs]

        # Create persistent session
        session = PersistentMCPSession(
            command=DEFAULT_MCP_NPX_COMMAND,
            args=DEFAULT_MCP_NPX_ARGS + [MCP_PACKAGES["filesystem"]],
            initial_roots=working_dirs
        )

        return session

    async def autonomous_persistent_session(
        self,
        tasks: List[Dict[str, Any]],
        initial_directory: Optional[Union[str, List[str]]] = None,
        max_rounds: int = DEFAULT_MAX_ROUNDS,
        max_tokens: Union[int, str] = "auto"
    ) -> List[str]:
        """Execute multiple tasks in a persistent session with dynamic directory updates.

        This is the advanced Roots Protocol implementation that allows:
        - Running multiple tasks in one session (no reconnect overhead)
        - Changing working directories between tasks dynamically
        - Adding/removing directories mid-session

        Args:
            tasks: List of task dictionaries with 'task' and optional 'working_directory'
            initial_directory: Initial working directory/directories
            max_rounds: Maximum rounds per task (default: 100)
            max_tokens: Maximum tokens per response ("auto" or integer)

        Returns:
            List of results, one per task

        Examples:
            # Multiple tasks with directory changes
            tasks = [
                {"task": "Read README.md"},
                {
                    "task": "Find all Python files",
                    "working_directory": "/other/project"  # Switch directory!
                },
                {
                    "task": "Compare implementations",
                    "working_directory": ["/project1", "/project2"]  # Multiple!
                }
            ]

            results = await autonomous_persistent_session(tasks)
        """
        try:
            # Determine max_tokens (Pydantic handles type/range validation)
            if max_tokens == "auto":
                actual_max_tokens = self.llm.get_default_max_tokens()
            else:
                # Pydantic already validated it's an int >= 1
                actual_max_tokens = max_tokens

            results = []

            # Create persistent session
            async with await self.create_persistent_session(initial_directory) as session:
                for i, task_config in enumerate(tasks):
                    # Extract task
                    if isinstance(task_config, str):
                        task = task_config
                        new_directory = None
                    elif isinstance(task_config, dict):
                        task = task_config.get("task")
                        new_directory = task_config.get("working_directory")
                    else:
                        results.append(f"Error: Invalid task configuration at index {i}")
                        continue

                    # Pydantic validation happens at tool call level for simple string tasks
                    # For dict tasks, we just need to ensure task key exists (already checked above)

                    # Update roots if directory specified
                    if new_directory:
                        validated_dirs = validate_working_directory(new_directory)
                        if isinstance(validated_dirs, str):
                            validated_dirs = [validated_dirs]

                        print(f"[Task {i+1}] Updating roots to: {validated_dirs}")
                        await session.update_roots(validated_dirs)

                    # Discover tools (may have changed if roots updated)
                    tools = await session.discover_tools()
                    openai_tools = SchemaConverter.mcp_tools_to_openai(tools)

                    # Execute autonomous task
                    print(f"[Task {i+1}] Executing: {task}")

                    messages = [{"role": "user", "content": task}]

                    for round_num in range(max_rounds):
                        # Call local LLM
                        response = self.llm.chat_completion(
                            messages=messages,
                            tools=openai_tools,
                            tool_choice="auto",
                            max_tokens=actual_max_tokens
                        )

                        message = response["choices"][0]["message"]

                        # Check for tool calls
                        if message.get("tool_calls"):
                            messages.append(message)

                            # Execute tools
                            for tool_call in message["tool_calls"]:
                                tool_name = tool_call["function"]["name"]
                                tool_args = json.loads(tool_call["function"]["arguments"])

                                result = await session.execute_tool(tool_name, tool_args)
                                content = ToolExecutor.extract_text_content(result)

                                messages.append({
                                    "role": "tool",
                                    "tool_call_id": tool_call["id"],
                                    "content": content
                                })
                        else:
                            # Task complete
                            result = self._format_response_with_reasoning(message)
                            results.append(result)
                            print(f"[Task {i+1}] Complete")
                            break
                    else:
                        # Max rounds reached
                        results.append(f"Max rounds ({max_rounds}) reached")

            return results

        except Exception as e:
            import traceback
            return [f"Error during persistent session: {str(e)}\n\n{traceback.format_exc()}"]

    async def autonomous_memory_full(
        self,
        task: str,
        max_rounds: int = DEFAULT_MAX_ROUNDS,
        max_tokens: Union[int, str] = "auto",
        model: Optional[str] = None
    ) -> str:
        """
        Full autonomous execution with memory MCP (knowledge graph) tools.

        Now optimized to use stateful /v1/responses API (98% token savings!).
        This function has been internally optimized while maintaining the same
        external interface.

        Provides local LLM access to knowledge graph operations:
        - create_entities - Create knowledge entities with observations
        - create_relations - Link entities together
        - add_observations - Add facts to existing entities
        - delete_entities, delete_observations, delete_relations
        - read_graph - View entire knowledge graph
        - search_nodes - Search by query
        - open_nodes - Get specific entities

        Args:
            task: The task for the local LLM
            max_rounds: Maximum rounds for autonomous loop (default: 100)
            max_tokens: Maximum tokens per response ("auto" or integer)

        Returns:
            Local LLM's final answer after autonomous tool usage

        Examples:
            # Create knowledge graph
            "Create entities for Python, FastMCP, and MCP, then link them with 'uses' relations"

            # Search knowledge
            "Search for all entities related to 'MCP development'"

            # Update knowledge
            "Add observation to Python entity: 'supports async/await'"
        """
        try:
            # Determine max_tokens
            if max_tokens == "auto":
                actual_max_tokens = self.llm.get_default_max_tokens()
            else:
                actual_max_tokens = max_tokens

            # Connect to memory MCP
            connection = MCPConnection(
                command=DEFAULT_MCP_NPX_COMMAND,
                args=DEFAULT_MCP_NPX_ARGS + [MCP_PACKAGES["memory"]]
            )

            async with connection.connect() as session:
                # Discover ALL memory tools
                discovery = ToolDiscovery(session)
                all_tools = await discovery.discover_tools()
                openai_tools = SchemaConverter.mcp_tools_to_openai(all_tools)
                executor = ToolExecutor(session)

                # Uses chat_completion API with explicit tool result passing
                # See Option 4A implementation: OPTION_4A_IMPLEMENTATION_PLAN.md
                return await self._execute_autonomous_with_tools(
                    task=task,
                    session=session,
                    openai_tools=openai_tools,
                    executor=executor,
                    max_rounds=max_rounds,
                    max_tokens=actual_max_tokens,
                    model=model
                )

        except Exception as e:
            import traceback
            return f"Error during memory execution: {str(e)}\n\n{traceback.format_exc()}"

    async def autonomous_fetch_full(
        self,
        task: str,
        max_rounds: int = DEFAULT_MAX_ROUNDS,
        max_tokens: Union[int, str] = "auto",
        model: Optional[str] = None
    ) -> str:
        """
        Full autonomous execution with fetch MCP (web content) tools.

        Now optimized to use stateful /v1/responses API (99% token savings!).
        This function has been internally optimized while maintaining the same
        external interface.

        Provides local LLM access to web content fetching:
        - fetch - Retrieve web content and convert to markdown

        Args:
            task: The task for the local LLM
            max_rounds: Maximum rounds for autonomous loop (default: 100)
            max_tokens: Maximum tokens per response ("auto" or integer)

        Returns:
            Local LLM's final answer after autonomous tool usage

        Examples:
            # Fetch and analyze web content
            "Fetch https://modelcontextprotocol.io and summarize the main concepts"

            # Multiple fetches
            "Compare documentation from FastMCP and official MCP sites"

            # Extract specific info
            "Fetch Python docs for asyncio and extract key features"
        """
        try:
            # Determine max_tokens
            if max_tokens == "auto":
                actual_max_tokens = self.llm.get_default_max_tokens()
            else:
                actual_max_tokens = max_tokens

            # Connect to fetch MCP
            connection = MCPConnection(
                command="uvx",
                args=["mcp-server-fetch"]
            )

            async with connection.connect() as session:
                # Discover ALL fetch tools
                discovery = ToolDiscovery(session)
                all_tools = await discovery.discover_tools()
                openai_tools = SchemaConverter.mcp_tools_to_openai(all_tools)
                executor = ToolExecutor(session)

                # Uses chat_completion API with explicit tool result passing
                # See Option 4A implementation: OPTION_4A_IMPLEMENTATION_PLAN.md
                return await self._execute_autonomous_with_tools(
                    task=task,
                    session=session,
                    openai_tools=openai_tools,
                    executor=executor,
                    max_rounds=max_rounds,
                    max_tokens=actual_max_tokens,
                    model=model
                )

        except Exception as e:
            import traceback
            return f"Error during fetch execution: {str(e)}\n\n{traceback.format_exc()}"

    async def autonomous_github_full(
        self,
        task: str,
        github_token: Optional[str] = None,
        max_rounds: int = DEFAULT_MAX_ROUNDS,
        max_tokens: Union[int, str] = "auto",
        model: Optional[str] = None
    ) -> str:
        """
        Full autonomous execution with GitHub MCP tools.

        Now optimized to use stateful /v1/responses API (94% token savings!).
        This function has been internally optimized while maintaining the same
        external interface.

        Provides local LLM access to GitHub operations:
        - Repository management (create, fork, search)
        - File operations (read, create, update, push)
        - Issue management (create, list, update, comment)
        - Pull request management (create, list, review, merge)
        - Search (code, issues, repositories, users)

        Args:
            task: The task for the local LLM
            github_token: GitHub personal access token (optional, uses GITHUB_PERSONAL_ACCESS_TOKEN env var if not provided)
            max_rounds: Maximum rounds for autonomous loop (default: 100)
            max_tokens: Maximum tokens per response ("auto" or integer)

        Returns:
            Local LLM's final answer after autonomous tool usage

        Examples:
            # Search and analyze
            "Search for MCP server repositories and list the top 5"

            # Create issues
            "Create an issue in my-org/my-repo about adding tests"

            # PR operations
            "List all open PRs in my-org/my-repo and summarize their status"
        """
        try:
            # Determine max_tokens
            if max_tokens == "auto":
                actual_max_tokens = self.llm.get_default_max_tokens()
            else:
                actual_max_tokens = max_tokens

            # Get GitHub token
            token = github_token or os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN", "")

            # Connect to GitHub MCP
            connection = MCPConnection(
                command=DEFAULT_MCP_NPX_COMMAND,
                args=DEFAULT_MCP_NPX_ARGS + [MCP_PACKAGES["github"]],
                env={"GITHUB_PERSONAL_ACCESS_TOKEN": token}
            )

            async with connection.connect() as session:
                # Discover ALL GitHub tools
                discovery = ToolDiscovery(session)
                all_tools = await discovery.discover_tools()

                # Convert to OpenAI format
                openai_tools = SchemaConverter.mcp_tools_to_openai(all_tools)
                executor = ToolExecutor(session)

                # Uses chat_completion API with explicit tool result passing
                # See Option 4A implementation: OPTION_4A_IMPLEMENTATION_PLAN.md
                return await self._execute_autonomous_with_tools(
                    task=task,
                    session=session,
                    openai_tools=openai_tools,
                    executor=executor,
                    max_rounds=max_rounds,
                    max_tokens=actual_max_tokens,
                    model=model
                )

        except Exception as e:
            import traceback
            return f"Error during GitHub execution: {str(e)}\n\n{traceback.format_exc()}"

    async def vision_analyze(
        self,
        task: str,
        images: Union[str, List[str]],
        model: Optional[str] = None,
        max_tokens: Union[int, str] = "auto",
        detail: str = "auto"
    ) -> str:
        """
        Analyze images with a vision-capable local LLM.

        This tool sends images along with a task to a vision-capable model
        (like Qwen2-VL, LLaVA, or similar) for analysis.

        Unlike other autonomous tools, this doesn't use MCP tool execution -
        it directly uses the LLM's vision capabilities for image analysis.

        Args:
            task: The analysis task or question about the image(s)
            images: Single image or list of images. Each can be:
                - File path: "/path/to/image.png"
                - URL: "https://example.com/image.jpg"
                - Base64: "data:image/png;base64,..." or raw base64 string
            model: Model to use (must be vision-capable). If None, uses configured default.
            max_tokens: Maximum tokens for response ("auto" or integer)
            detail: Vision detail level ("auto", "low", "high")

        Returns:
            LLM's analysis of the image(s)

        Examples:
            # Analyze a local image
            result = await vision_analyze(
                task="Describe what you see in this image",
                images="/path/to/photo.jpg"
            )

            # Compare multiple images
            result = await vision_analyze(
                task="What are the differences between these images?",
                images=["image1.png", "image2.png"]
            )

            # Use specific vision model
            result = await vision_analyze(
                task="Extract text from this screenshot",
                images="screenshot.png",
                model="qwen2-vl-7b"
            )
        """
        try:
            # Determine max_tokens
            if max_tokens == "auto":
                actual_max_tokens = self.llm.get_default_max_tokens()
            else:
                actual_max_tokens = max_tokens

            # Use vision_completion method
            response = self.llm.vision_completion(
                prompt=task,
                images=images,
                temperature=0.7,
                max_tokens=actual_max_tokens,
                detail=detail,
                model=model
            )

            message = response["choices"][0]["message"]
            return self._format_response_with_reasoning(message)

        except Exception as e:
            import traceback
            return f"Error during vision analysis: {str(e)}\n\n{traceback.format_exc()}"


# Register tools with FastMCP
def register_autonomous_tools(mcp, llm_client: Optional[LLMClient] = None):
    """Register autonomous execution tools with FastMCP server.

    Args:
        mcp: FastMCP server instance
        llm_client: Optional LLM client
    """
    tools = AutonomousExecutionTools(llm_client)

    @mcp.tool()
    async def autonomous_filesystem_full(
        task: Annotated[str, Field(
            min_length=1,
            max_length=10000,
            description="Task for the local LLM to execute autonomously"
        )],
        working_directory: Annotated[
            Optional[Union[str, List[str]]],
            Field(
                description="Directory or list of directories for filesystem operations (default: current Claude Code project)"
            )
        ] = None,
        max_rounds: Annotated[int, Field(
            ge=1,
            description="Maximum rounds for autonomous loop (default: 10000, no artificial limit - local LLM works until task complete)"
        )] = 10000,
        max_tokens: Annotated[
            Union[int, str],
            Field(
                description="Maximum tokens per LLM response ('auto' for default 8192 based on Claude Code limits, or integer to override)"
            )
        ] = "auto",
        model: Annotated[
            Optional[str],
            Field(
                description="Model to use for this task (e.g., 'qwen2.5-coder-14b'). If not specified, uses configured default."
            )
        ] = None
    ) -> str:
        """
        Full autonomous execution with ALL 14 filesystem MCP tools.

        Provides local LLM access to complete filesystem operations:
        - read_text_file, read_media_file, read_multiple_files
        - write_file, edit_file
        - create_directory, list_directory, directory_tree
        - move_file, search_files, get_file_info
        - list_allowed_directories

        The local LLM can autonomously:
        - Search for files by pattern across multiple directories
        - Read multiple files from different projects
        - Create and edit files
        - Organize directory structures
        - Get file metadata
        - And more!

        Args:
            task: The task for the local LLM
            working_directory: Directory or list of directories for filesystem operations (default: current Claude Code project)
            max_rounds: Maximum rounds for autonomous loop (default: 10000, no artificial limit - lets local LLM work until task complete)
            max_tokens: Maximum tokens per LLM response ("auto" for default 8192 based on Claude Code limits, or integer to override)

        Returns:
            Local LLM's final answer after autonomous tool usage

        Examples:
            # Simple tasks (uses current project directory and auto token limit)
            - "Search for all Python files and list them"
            - "Read setup.py and README.md, then create a summary.txt file"
            - "Find all markdown files, count them, and tell me the total"

            # Different project directory
            - autonomous_filesystem_full("Read README.md", working_directory="/path/to/other/project")

            # Multiple directories (work across multiple projects!)
            - autonomous_filesystem_full(
                "Find all TODO comments",
                working_directory=["/project1", "/project2"]
              )

            # Complex tasks requiring more rounds and tokens
            - autonomous_filesystem_full("Analyze entire codebase", max_rounds=500, max_tokens=8192)

        Note on max_tokens:
            - "auto" uses 4096 (safe default for most models)
            - LM Studio's API doesn't expose model's actual max_context_length
            - If your model supports more (e.g., 32K, 128K), manually specify (e.g., max_tokens=8192)
        """
        return await tools.autonomous_filesystem_full(task, working_directory, max_rounds, max_tokens, model)

    @mcp.tool()
    async def autonomous_persistent_session(
        tasks: Annotated[List[Union[str, Dict[str, Any]]], Field(
            min_length=1,
            description="List of tasks to execute. Each can be a simple string or dict with 'task' and optional 'working_directory'"
        )],
        initial_directory: Annotated[
            Optional[Union[str, List[str]]],
            Field(
                description="Initial working directory or directories for the session"
            )
        ] = None,
        max_rounds: Annotated[int, Field(
            ge=1,
            description="Maximum rounds per task (default: 10000, no artificial limit - local LLM works until task complete)"
        )] = 10000,
        max_tokens: Annotated[
            Union[int, str],
            Field(
                description="Maximum tokens per response ('auto' for default 8192 based on Claude Code limits, or integer to override)"
            )
        ] = "auto"
    ) -> List[str]:
        """
        Advanced: Execute multiple tasks in a persistent session with dynamic directory updates.

        This implements the MCP Roots Protocol, allowing you to:
        - Run multiple tasks in ONE session (no reconnect overhead)
        - Change working directories DYNAMICALLY between tasks
        - Add/remove directories mid-session

        Perfect for workflows that need to work across multiple projects or
        change context frequently.

        Args:
            tasks: List of tasks. Each can be:
                   - Simple string: "Read README.md"
                   - Dict with working_directory: {"task": "...", "working_directory": "/path"}
            initial_directory: Initial working directory/directories
            max_rounds: Maximum rounds per task (default: 10000, no artificial limit - lets local LLM work until task complete)
            max_tokens: Maximum tokens per response ("auto" for default 8192, or integer to override)

        Returns:
            List of results, one per task

        Examples:
            # Simple: Multiple tasks in same directory
            autonomous_persistent_session([
                "Read README.md",
                "Find all Python files",
                "Create summary.txt"
            ])

            # Advanced: Change directories between tasks
            autonomous_persistent_session([
                {"task": "Read config.json"},
                {
                    "task": "Find all TODO comments",
                    "working_directory": "/other/project"  # Switch!
                },
                {
                    "task": "Compare implementations",
                    "working_directory": ["/proj1", "/proj2"]  # Multiple!
                }
            ])

            # Performance: 3 tasks in one session vs 3 separate calls
            # Persistent session: 1 connection, 3 tasks
            # Separate calls: 3 connections, 3 tasks (slower!)

        Benefits over autonomous_filesystem_full:
            - Faster: No reconnection overhead between tasks
            - Flexible: Change directories mid-session
            - Efficient: Reuse same MCP connection
            - Advanced: True Roots Protocol implementation
        """
        return await tools.autonomous_persistent_session(tasks, initial_directory, max_rounds, max_tokens)

    @mcp.tool()
    async def autonomous_memory_full(
        task: Annotated[str, Field(
            min_length=1,
            max_length=10000,
            description="Task for the local LLM to execute autonomously with memory/knowledge graph tools"
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
        ] = "auto",
        model: Annotated[
            Optional[str],
            Field(
                description="Model to use for this task (e.g., 'qwen2.5-coder-14b'). If not specified, uses configured default."
            )
        ] = None
    ) -> str:
        """
        Full autonomous execution with memory MCP (knowledge graph) tools.

        Provides local LLM access to knowledge graph operations:
        - create_entities - Create knowledge entities with observations
        - create_relations - Link entities together
        - add_observations - Add facts to existing entities
        - delete_entities, delete_observations, delete_relations
        - read_graph - View entire knowledge graph
        - search_nodes - Search by query
        - open_nodes - Get specific entities

        The local LLM can autonomously:
        - Build knowledge graphs from information
        - Create and link entities
        - Query and search knowledge
        - Maintain project context
        - Track relationships between concepts

        Args:
            task: The task for the local LLM
            max_rounds: Maximum rounds for autonomous loop (default: 100)
            max_tokens: Maximum tokens per response ("auto" or integer)

        Returns:
            Local LLM's final answer after autonomous tool usage

        Examples:
            # Create knowledge graph
            "Create entities for Python, FastMCP, and MCP, then link them with 'uses' relations"

            # Search knowledge
            "Search for all entities related to 'MCP development'"

            # Update knowledge
            "Add observation to Python entity: 'supports async/await'"
        """
        return await tools.autonomous_memory_full(task, max_rounds, max_tokens, model)

    @mcp.tool()
    async def autonomous_fetch_full(
        task: Annotated[str, Field(
            min_length=1,
            max_length=10000,
            description="Task for the local LLM to execute autonomously with web content fetching tools"
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
        ] = "auto",
        model: Annotated[
            Optional[str],
            Field(
                description="Model to use for this task (e.g., 'qwen2.5-coder-14b'). If not specified, uses configured default."
            )
        ] = None
    ) -> str:
        """
        Full autonomous execution with fetch MCP (web content) tools.

        Provides local LLM access to web content fetching:
        - fetch - Retrieve web content and convert to markdown

        The local LLM can autonomously:
        - Fetch and analyze web pages
        - Retrieve documentation from URLs
        - Download and process online content
        - Compare content from multiple sites
        - Extract information from web resources

        Args:
            task: The task for the local LLM
            max_rounds: Maximum rounds for autonomous loop (default: 100)
            max_tokens: Maximum tokens per response ("auto" or integer)

        Returns:
            Local LLM's final answer after autonomous tool usage

        Examples:
            # Fetch and analyze web content
            "Fetch https://modelcontextprotocol.io and summarize the main concepts"

            # Multiple fetches
            "Compare documentation from FastMCP and official MCP sites"

            # Extract specific info
            "Fetch Python docs for asyncio and extract key features"
        """
        return await tools.autonomous_fetch_full(task, max_rounds, max_tokens, model)

    @mcp.tool()
    async def autonomous_github_full(
        task: Annotated[str, Field(
            min_length=1,
            max_length=10000,
            description="Task for the local LLM to execute autonomously with GitHub tools"
        )],
        github_token: Annotated[
            Optional[str],
            Field(
                description="GitHub personal access token (optional, uses GITHUB_PERSONAL_ACCESS_TOKEN env var if not provided)"
            )
        ] = None,
        max_rounds: Annotated[int, Field(
            ge=1,
            description="Maximum rounds for autonomous loop (default: 100)"
        )] = 100,
        max_tokens: Annotated[
            Union[int, str],
            Field(
                description="Maximum tokens per LLM response ('auto' for default, or integer to override)"
            )
        ] = "auto",
        model: Annotated[
            Optional[str],
            Field(
                description="Model to use for this task (e.g., 'qwen2.5-coder-14b'). If not specified, uses configured default."
            )
        ] = None
    ) -> str:
        """
        Full autonomous execution with GitHub MCP tools.

        Provides local LLM access to GitHub operations:
        - Repository management (create, fork, search)
        - File operations (read, create, update, push)
        - Issue management (create, list, update, comment)
        - Pull request management (create, list, review, merge)
        - Search (code, issues, repositories, users)

        The local LLM can autonomously:
        - Search and analyze GitHub repositories
        - Create and manage issues
        - Work with pull requests
        - Read and modify repository files
        - Search code and repositories

        Args:
            task: The task for the local LLM
            github_token: GitHub personal access token (optional)
            max_rounds: Maximum rounds for autonomous loop (default: 100)
            max_tokens: Maximum tokens per response ("auto" or integer)

        Returns:
            Local LLM's final answer after autonomous tool usage

        Examples:
            # Search and analyze
            "Search for MCP server repositories and list the top 5"

            # Create issues
            "Create an issue in my-org/my-repo about adding tests"

            # PR operations
            "List all open PRs in my-org/my-repo and summarize their status"
        """
        return await tools.autonomous_github_full(task, github_token, max_rounds, max_tokens, model)

    @mcp.tool()
    async def vision_analyze(
        task: Annotated[str, Field(
            min_length=1,
            max_length=10000,
            description="The analysis task or question about the image(s)"
        )],
        images: Annotated[
            Union[str, List[str]],
            Field(
                description="Single image or list of images. Each can be: file path (/path/to/image.png), URL (https://example.com/image.jpg), or base64 data URI"
            )
        ],
        model: Annotated[
            Optional[str],
            Field(
                description="Vision-capable model to use (e.g., 'qwen2-vl-7b', 'llava-1.5'). If not specified, uses configured default."
            )
        ] = None,
        max_tokens: Annotated[
            Union[int, str],
            Field(
                description="Maximum tokens for response ('auto' for default, or integer to override)"
            )
        ] = "auto",
        detail: Annotated[
            str,
            Field(
                description="Vision detail level: 'auto' (recommended), 'low' (faster), or 'high' (more detailed)"
            )
        ] = "auto"
    ) -> str:
        """
        Analyze images with a vision-capable local LLM.

        **REQUIRES VISION-CAPABLE MODEL** (e.g., Qwen2-VL, LLaVA, MiniCPM-V)

        This tool sends images along with a task to a vision-capable model
        for analysis. Unlike other autonomous tools, this directly uses the
        LLM's vision capabilities without MCP tool execution.

        Supports multiple input formats:
        - File paths: "/path/to/image.png"
        - URLs: "https://example.com/image.jpg" (auto-fetched and converted to base64)
        - Base64: "data:image/png;base64,..." or raw base64 strings

        ## Use Cases
        - Image description and analysis
        - Object identification
        - Text extraction (OCR)
        - Image comparison
        - Chart/diagram interpretation
        - Screenshot analysis

        ## Example Tasks
        - "Describe what you see in this image"
        - "Extract all text from this screenshot"
        - "What objects are in this photo?"
        - "Compare these two images and list differences"
        - "What is the sentiment/mood of this image?"

        Args:
            task: The analysis task or question about the image(s)
            images: Single image or list of images (file path, URL, or base64)
            model: Vision-capable model name (optional, uses default if not specified)
            max_tokens: Maximum tokens for response ("auto" or integer)
            detail: Vision detail level ("auto", "low", "high")

        Returns:
            LLM's analysis/response about the image(s)

        Note:
            - Make sure a vision-capable model is loaded in LM Studio
            - Large images may be slow to process; use detail="low" for faster results
            - URLs are automatically fetched and converted to base64
        """
        return await tools.vision_analyze(task, images, model, max_tokens, detail)


__all__ = [
    "AutonomousExecutionTools",
    "register_autonomous_tools"
]
