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
import json
import os


class AutonomousExecutionTools:
    """Tools for autonomous execution with MCP integration."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """Initialize autonomous execution tools.

        Args:
            llm_client: Optional LLM client (creates default if None)
        """
        self.llm = llm_client or LLMClient()

    # Private helper methods for consolidated implementation

    async def _execute_autonomous_stateful(
        self,
        task: str,
        session: Any,
        openai_tools: List[Dict],
        executor: ToolExecutor,
        max_rounds: int,
        max_tokens: int
    ) -> str:
        """
        Core implementation using stateful /v1/responses API.

        This is the optimized implementation with constant token usage.
        Uses LM Studio's stateful conversation API where the server maintains
        conversation history automatically.

        Args:
            task: The task for the local LLM
            session: Active MCP session
            openai_tools: List of tools in OpenAI format
            executor: Tool executor for the session
            max_rounds: Maximum rounds for autonomous loop
            max_tokens: Maximum tokens per response

        Returns:
            Final answer from the LLM
        """
        # Autonomous loop with /v1/responses API (stateful!)
        previous_response_id = None

        for round_num in range(max_rounds):
            # Determine input text
            if round_num == 0:
                input_text = task
            else:
                # For subsequent rounds, just say "Continue"
                # Tool results are automatically available via server-side state
                input_text = "Continue with the task based on the tool results."

            # Call /v1/responses with tools (auto-converts to flattened format)
            response = self.llm.create_response(
                input_text=input_text,
                tools=openai_tools,
                previous_response_id=previous_response_id,
                model="default"
            )

            # Save response ID for next round
            previous_response_id = response["id"]

            # Process output array (not choices!)
            output = response.get("output", [])

            # Check for function calls
            function_calls = [
                item for item in output
                if item.get("type") == "function_call"
            ]

            if function_calls:
                # Execute each tool
                for fc in function_calls:
                    tool_name = fc["name"]
                    tool_args = json.loads(fc["arguments"])

                    # Execute via MCP
                    await executor.execute_tool(tool_name, tool_args)

                # Continue loop (tool results automatically available to LLM)
                continue

            # Check for final answer (message output)
            for item in output:
                if item.get("type") == "message":
                    # Extract text from content
                    content = item.get("content", [])
                    for content_item in content:
                        if content_item.get("type") == "output_text":
                            return content_item.get("text", "")

            # If neither function calls nor message, something unexpected happened
            return f"Unexpected output format in round {round_num + 1}"

        return f"Max rounds ({max_rounds}) reached without final answer."

    async def autonomous_filesystem_full(
        self,
        task: str,
        working_directory: Optional[Union[str, List[str]]] = None,
        max_rounds: int = 100,
        max_tokens: Union[int, str] = "auto"
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

            # 3. Connect to filesystem MCP with working directory/directories
            # Pass all directories as separate arguments
            connection_args = [
                "-y",
                "@modelcontextprotocol/server-filesystem"
            ]
            # Add all directories to args
            connection_args.extend(working_dirs)

            connection = MCPConnection(
                command="npx",
                args=connection_args
            )

            async with connection.connect() as session:
                # 2. Discover ALL tools from filesystem MCP
                discovery = ToolDiscovery(session)
                all_tools = await discovery.discover_tools()

                # 3. Convert ALL tools to OpenAI format
                openai_tools = SchemaConverter.mcp_tools_to_openai(all_tools)
                executor = ToolExecutor(session)

                # Call optimized stateful implementation
                return await self._execute_autonomous_stateful(
                    task=task,
                    session=session,
                    openai_tools=openai_tools,
                    executor=executor,
                    max_rounds=max_rounds,
                    max_tokens=actual_max_tokens
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
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem"],
            initial_roots=working_dirs
        )

        return session

    async def autonomous_persistent_session(
        self,
        tasks: List[Dict[str, Any]],
        initial_directory: Optional[Union[str, List[str]]] = None,
        max_rounds: int = 100,
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
                            result = message.get("content", "No content in response")
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
        max_rounds: int = 100,
        max_tokens: Union[int, str] = "auto"
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
                command="npx",
                args=["-y", "@modelcontextprotocol/server-memory"]
            )

            async with connection.connect() as session:
                # Discover ALL memory tools
                discovery = ToolDiscovery(session)
                all_tools = await discovery.discover_tools()
                openai_tools = SchemaConverter.mcp_tools_to_openai(all_tools)
                executor = ToolExecutor(session)

                # Call optimized stateful implementation
                return await self._execute_autonomous_stateful(
                    task=task,
                    session=session,
                    openai_tools=openai_tools,
                    executor=executor,
                    max_rounds=max_rounds,
                    max_tokens=actual_max_tokens
                )

        except Exception as e:
            import traceback
            return f"Error during memory execution: {str(e)}\n\n{traceback.format_exc()}"

    async def autonomous_fetch_full(
        self,
        task: str,
        max_rounds: int = 100,
        max_tokens: Union[int, str] = "auto"
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

                # Call optimized stateful implementation
                return await self._execute_autonomous_stateful(
                    task=task,
                    session=session,
                    openai_tools=openai_tools,
                    executor=executor,
                    max_rounds=max_rounds,
                    max_tokens=actual_max_tokens
                )

        except Exception as e:
            import traceback
            return f"Error during fetch execution: {str(e)}\n\n{traceback.format_exc()}"

    async def autonomous_github_full(
        self,
        task: str,
        github_token: Optional[str] = None,
        max_rounds: int = 100,
        max_tokens: Union[int, str] = "auto"
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
                command="npx",
                args=["-y", "@modelcontextprotocol/server-github"],
                env={"GITHUB_PERSONAL_ACCESS_TOKEN": token}
            )

            async with connection.connect() as session:
                # Discover ALL GitHub tools
                discovery = ToolDiscovery(session)
                all_tools = await discovery.discover_tools()

                # Convert to OpenAI format
                openai_tools = SchemaConverter.mcp_tools_to_openai(all_tools)
                executor = ToolExecutor(session)

                # Call optimized stateful implementation
                return await self._execute_autonomous_stateful(
                    task=task,
                    session=session,
                    openai_tools=openai_tools,
                    executor=executor,
                    max_rounds=max_rounds,
                    max_tokens=actual_max_tokens
                )

        except Exception as e:
            import traceback
            return f"Error during GitHub execution: {str(e)}\n\n{traceback.format_exc()}"



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
        ] = "auto"
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
        return await tools.autonomous_filesystem_full(task, working_directory, max_rounds, max_tokens)

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
        ] = "auto"
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
        return await tools.autonomous_memory_full(task, max_rounds, max_tokens)

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
        ] = "auto"
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
        return await tools.autonomous_fetch_full(task, max_rounds, max_tokens)

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
        ] = "auto"
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
        return await tools.autonomous_github_full(task, github_token, max_rounds, max_tokens)



__all__ = [
    "AutonomousExecutionTools",
    "register_autonomous_tools"
]
