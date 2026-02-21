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
import time
from typing import List, Dict, Any, Optional, Union
from contextlib import AsyncExitStack
from pathlib import Path

from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp import ClientSession
from mcp_client.discovery import MCPDiscovery, get_mcp_discovery
from llm.llm_client import LLMClient
from llm.model_validator import ModelValidator
from llm.exceptions import ModelNotFoundError
from utils.lms_helper import LMSHelper
from utils.custom_logging import log_info, log_error
from config.constants import DEFAULT_MAX_ROUNDS, MAX_CONSECUTIVE_ERRORS, DEFAULT_TEMPERATURE

# Import centralized safe_call_tool wrapper from mcp_client
# This ensures ALL code paths use the same coercion logic via single entry point
from mcp_client.type_coercion import safe_call_tool
from mcp_client.executor import ToolExecutor
from tools.loop_metrics import LoopMetrics, RoundMetrics


class _SingleSessionDispatcher:
    """Dispatches tools to a single MCP session."""

    def __init__(self, session: ClientSession):
        self._session = session

    async def dispatch(self, fc_name: str, tool_args: dict) -> tuple:
        """Execute tool on the single session. Returns (display_name, result_text)."""
        result = await safe_call_tool(self._session, fc_name, tool_args)
        return fc_name, ToolExecutor.extract_text_content(result)


class _MultiSessionDispatcher:
    """Dispatches tools across multiple MCP sessions using namespace resolution."""

    def __init__(self, tool_to_session: Dict[str, tuple]):
        self._tool_to_session = tool_to_session

    async def dispatch(self, fc_name: str, tool_args: dict) -> tuple:
        """Resolve namespaced tool and execute. Returns (display_name, result_text).

        Raises:
            KeyError: If tool name not found in any session.
        """
        if fc_name not in self._tool_to_session:
            raise KeyError(f"Unknown tool {fc_name}")
        original_name, session = self._tool_to_session[fc_name]
        log_info(f"Executing {fc_name} (original: {original_name})")
        result = await safe_call_tool(session, original_name, tool_args)
        return fc_name, ToolExecutor.extract_text_content(result)


class DynamicAutonomousAgent:
    """
    Dynamic autonomous agent that can connect to ANY MCP discovered from .mcp.json.

    This is the TRUE dynamic solution - no hardcoded MCP configurations!
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        mcp_discovery: Optional[MCPDiscovery] = None,
        model_validator: Optional[ModelValidator] = None
    ):
        """
        Initialize dynamic autonomous agent with HOT RELOAD support.

        Hot reload: .mcp.json is read fresh on EVERY tool call, so adding
        new MCPs to .mcp.json makes them available immediately without restart!

        Performance: Only 0.011ms overhead per call (essentially free).

        Args:
            llm_client: Optional LLM client (creates default if None)
            mcp_discovery: Optional MCP discovery instance (only used to get mcp_json_path)
            model_validator: Optional model validator (creates default if None)
        """
        self.llm = llm_client or LLMClient()
        self.model_validator = model_validator or ModelValidator()

        # HOT RELOAD: Don't store discovery instance, only the path
        # This way we create fresh MCPDiscovery on every call (reads file fresh)
        if mcp_discovery:
            self.mcp_json_path = mcp_discovery.mcp_json_path
        else:
            # Find mcp.json path once (this doesn't read the file)
            temp_discovery = MCPDiscovery()
            self.mcp_json_path = temp_discovery.mcp_json_path

    async def _preload_and_validate_model(self, model: Optional[str], verbose: bool = False) -> Optional[str]:
        """Preload model via LMS CLI and validate if specified.

        Args:
            model: Model override (None = use self.llm.model)
            verbose: If True, use emoji-enhanced logging with CLI install warning

        Returns:
            Error message string if validation fails, None on success
        """
        model_to_use = model or self.llm.model
        if LMSHelper.is_installed():
            log_info(f"LMS CLI detected - ensuring model loaded: {model_to_use}")
            try:
                if LMSHelper.ensure_model_loaded(model_to_use):
                    if verbose:
                        log_info(f"✅ Model '{model_to_use}' preloaded and kept loaded (prevents 404)")
                    else:
                        log_info(f"Model '{model_to_use}' preloaded")
                else:
                    if verbose:
                        log_info(f"⚠️  Could not preload model '{model_to_use}' with LMS CLI")
                    else:
                        log_info(f"Could not preload model '{model_to_use}'")
            except Exception as e:
                if verbose:
                    log_info(f"⚠️  Error during model preload: {e}")
                else:
                    log_info(f"Error during model preload: {e}")
        elif verbose:
            log_info(
                "⚠️  LMS CLI not installed - model may auto-unload causing intermittent 404 errors. "
                "Install for better reliability: brew install lmstudio-ai/lms/lms"
            )

        # Validate model if specified
        if model is not None:
            log_info(f"Model: {model}")
            try:
                await self.model_validator.validate_model(model)
                log_info(f"✓ Model validated: {model}")
            except ModelNotFoundError as e:
                log_error(f"Model validation failed: {e}")
                return f"Error: Model '{model}' not found. {e}"
            except Exception as e:
                log_error(f"Model validation error: {e}")
                return f"Error: Model validation failed: {e}"

        return None

    async def autonomous_with_mcp(
        self,
        mcp_name: str,
        task: str,
        max_rounds: int = DEFAULT_MAX_ROUNDS,
        max_tokens: Union[int, str] = "auto",
        model: Optional[str] = None
    ) -> str:
        """
        Execute task autonomously using tools from a SINGLE MCP.

        The MCP is dynamically discovered from .mcp.json - NO hardcoded config!

        Args:
            mcp_name: Name of the MCP to use (e.g., "filesystem", "memory", "fetch")
            task: Task description for the local LLM
            max_rounds: Maximum autonomous loop iterations
            max_tokens: Maximum tokens per LLM response ("auto" or integer)
            model: Optional model name (None = use default from config)

        Returns:
            Final answer from the local LLM

        Raises:
            ValueError: If MCP not found or is disabled
            ModelNotFoundError: If specified model not available in LM Studio

        Examples:
            # Use filesystem MCP with default model
            await agent.autonomous_with_mcp(
                mcp_name="filesystem",
                task="Read README.md and summarize it"
            )

            # Use memory MCP with specific model
            from config.constants import DEFAULT_AUTONOMOUS_MODEL
            await agent.autonomous_with_mcp(
                mcp_name="memory",
                task="Create an entity called 'Python' with observations",
                model=DEFAULT_AUTONOMOUS_MODEL
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

        error = await self._preload_and_validate_model(model)
        if error:
            return error

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
                        dispatcher=_SingleSessionDispatcher(session),
                        openai_tools=openai_tools,
                        task=task,
                        max_rounds=max_rounds,
                        max_tokens=actual_max_tokens,
                        model=model
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
        max_rounds: int = DEFAULT_MAX_ROUNDS,
        max_tokens: Union[int, str] = "auto",
        model: Optional[str] = None
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
            model: Optional model name (None = use default from config)

        Returns:
            Final answer from the local LLM

        Raises:
            ModelNotFoundError: If specified model not available in LM Studio

        Examples:
            # Use filesystem + memory MCPs with default model
            await agent.autonomous_with_multiple_mcps(
                mcp_names=["filesystem", "memory"],
                task="Read all Python files and create a knowledge graph of the codebase structure"
            )

            # Use filesystem + fetch + memory MCPs with specific model
            await agent.autonomous_with_multiple_mcps(
                mcp_names=["filesystem", "fetch", "memory"],
                task="Read local docs, fetch online docs, compare them, and build a knowledge graph",
                model=DEFAULT_AUTONOMOUS_MODEL
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

        error = await self._preload_and_validate_model(model)
        if error:
            return error

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
                return await self._autonomous_loop(
                    dispatcher=_MultiSessionDispatcher(tool_to_session),
                    openai_tools=all_openai_tools,
                    task=task,
                    max_rounds=max_rounds,
                    max_tokens=actual_max_tokens,
                    model=model
                )

        except ValueError as e:
            log_error(f"Configuration error: {e}")
            return f"Error: {e}"
        except Exception as e:
            # Handle Python 3.11+ ExceptionGroups from anyio TaskGroups
            # Extract root cause from nested exception groups for clearer error messages
            import sys
            root_cause = e
            if sys.version_info >= (3, 11) and isinstance(e, BaseExceptionGroup):
                # Unwrap nested ExceptionGroups to find the actual error
                while hasattr(root_cause, 'exceptions') and root_cause.exceptions:
                    root_cause = root_cause.exceptions[0]

            log_error(f"Multi-MCP execution failed: {root_cause}")
            import traceback
            log_error(traceback.format_exc())
            return f"Error during multi-MCP execution: {root_cause}"

    async def autonomous_discover_and_execute(
        self,
        task: str,
        max_rounds: int = DEFAULT_MAX_ROUNDS,
        max_tokens: Union[int, str] = "auto",
        model: Optional[str] = None
    ) -> str:
        """
        Execute task with ALL available MCPs discovered from .mcp.json!

        This is the ULTIMATE dynamic solution - the local LLM automatically gets
        access to EVERY tool from EVERY enabled MCP in .mcp.json!

        Args:
            task: Task description for the local LLM
            max_rounds: Maximum autonomous loop iterations
            max_tokens: Maximum tokens per LLM response ("auto" or integer)
            model: Optional model name (None = use default from config)

        Returns:
            Final answer from the local LLM

        Raises:
            ModelNotFoundError: If specified model not available in LM Studio

        Examples:
            # Let LLM use ANY tool from ANY MCP with default model!
            await agent.autonomous_discover_and_execute(
                task="Read my codebase, fetch relevant docs online, build a knowledge graph, and create comprehensive documentation"
            )

            # LLM has access to EVERYTHING with specific model!
            await agent.autonomous_discover_and_execute(
                task="Analyze this project, compare with GitHub repos, fetch best practices, and suggest improvements",
                model=DEFAULT_AUTONOMOUS_MODEL
            )
        """
        log_info("=== Auto-Discovery Autonomous Execution ===")
        log_info("Discovering ALL available MCPs from .mcp.json...")

        # PROACTIVE MODEL PRELOADING (Fallback mechanism)
        # Ensure model is loaded before starting autonomous execution
        error = await self._preload_and_validate_model(model, verbose=True)
        if error:
            return error

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
            max_tokens=max_tokens,
            model=model
        )

    @staticmethod
    def _build_input_text(
        round_num: int,
        task: str,
        pending_tool_results: list,
        consecutive_error_count: int = 0
    ) -> str:
        """Build input text for the LLM with tool results and self-correction hints."""
        if round_num == 0:
            input_text = task
        else:
            if pending_tool_results:
                results_text = "\n\n".join([
                    f"Tool '{name}' returned:\n{result}"
                    for name, result in pending_tool_results
                ])
                input_text = f"""Tool execution completed. Here are the ACTUAL results:

{results_text}

IMPORTANT: Use ONLY the actual results above. Do NOT make up or hallucinate information.
Continue with the task based on these results."""
            else:
                input_text = "Continue with the task."

        # Self-correction hint when errors are accumulating (not on first round)
        if round_num > 0 and consecutive_error_count >= 2:
            input_text += (
                f"\n\nNOTE: {consecutive_error_count} consecutive errors occurred. "
                "Reconsider your approach: check tool argument formats, try simpler "
                "alternatives, or explain what is going wrong."
            )

        return input_text

    async def _execute_tools_sequential(self, dispatcher, fc_list):
        """Execute tools sequentially. Returns list of (name, result_text) tuples.

        Updates self.consecutive_error_count:
        - Success: resets to 0
        - Failure: increments by 1 per failing tool
        """
        results = []
        for fc in fc_list:
            fc_name = fc["name"]
            tool_args = fc.get("arguments", {})

            # Parse JSON string args
            if isinstance(tool_args, str):
                try:
                    tool_args = json.loads(tool_args)
                except json.JSONDecodeError:
                    error_msg = f"Failed to parse tool arguments for '{fc_name}': {str(tool_args)[:200]}"
                    log_error(error_msg)
                    results.append((fc_name, f"Error: {error_msg}"))
                    self.consecutive_error_count += 1
                    continue

            log_info(f"Executing {fc_name}")

            try:
                display_name, tool_result = await dispatcher.dispatch(fc_name, tool_args)
                self.consecutive_error_count = 0  # Reset on success
                log_info(f"Tool result: {str(tool_result)[:200]}...")
            except KeyError as e:
                tool_result = f"Error: {e}"
                log_error(str(e))
                self.consecutive_error_count += 1
            except Exception as e:
                tool_result = f"Error: {e}"
                log_error(f"Tool execution failed: {e}")
                self.consecutive_error_count += 1

            results.append((fc_name, tool_result))

        return results

    async def _execute_tools_parallel(self, dispatcher, fc_list):
        """Execute tools in parallel using asyncio.gather(). Returns list of (name, result_text) tuples.

        Error counting (batch semantics):
        - ALL succeed: consecutive_error_count = 0
        - ALL fail: consecutive_error_count += 1 (capped at +1 per batch)
        - PARTIAL success: consecutive_error_count UNCHANGED
        """
        async def _run_one(fc):
            fc_name = fc["name"]
            tool_args = fc.get("arguments", {})

            # Parse JSON string args
            if isinstance(tool_args, str):
                try:
                    tool_args = json.loads(tool_args)
                except json.JSONDecodeError:
                    error_msg = f"Failed to parse tool arguments for '{fc_name}': {str(tool_args)[:200]}"
                    log_error(error_msg)
                    return fc_name, f"Error: {error_msg}", False

            try:
                display_name, tool_result = await dispatcher.dispatch(fc_name, tool_args)
                log_info(f"Tool result: {str(tool_result)[:200]}...")
                return fc_name, tool_result, True  # True = success
            except KeyError as e:
                log_error(str(e))
                return fc_name, f"Error: {e}", False
            except Exception as e:
                log_error(f"Tool execution failed: {e}")
                return fc_name, f"Error: {e}", False

        gathered = await asyncio.gather(*[_run_one(fc) for fc in fc_list], return_exceptions=True)

        results = []
        successes = 0
        failures = 0

        for item in gathered:
            if isinstance(item, Exception):
                # Unexpected exception from gather itself
                results.append(("unknown", f"Error: {item}"))
                failures += 1
            else:
                fc_name, result_text, success = item
                results.append((fc_name, result_text))
                if success:
                    successes += 1
                else:
                    failures += 1

        # Batch error counting semantics
        total = successes + failures
        if total > 0 and successes == total:
            # ALL succeed -> reset
            self.consecutive_error_count = 0
        elif total > 0 and failures == total:
            # ALL fail -> +1 (capped per batch)
            self.consecutive_error_count += 1
        # PARTIAL success -> unchanged (no modification)

        return results

    async def _autonomous_loop(
        self,
        dispatcher,
        openai_tools: List[Dict],
        task: str,
        max_rounds: int,
        max_tokens: int,
        model: Optional[str] = None,
        parallel_tools: bool = False
    ) -> str:
        """Core autonomous loop using stateful /v1/responses API with explicit tool result injection.

        HYBRID APPROACH that provides:
        - Stateful conversation management (97% token savings via previous_response_id)
        - Explicit tool result passing (injected into input_text)
        - No context overflow (server handles history)

        Based on LM Studio SDK's .act() internal behavior:
        "run a tool → provide the result to the LLM → wait for the LLM to generate a response"

        See: https://lmstudio.ai/docs/typescript/agent/act

        Args:
            dispatcher: _SingleSessionDispatcher or _MultiSessionDispatcher instance
            openai_tools: List of tools in OpenAI function-calling format
            task: Task description for the LLM
            max_rounds: Maximum number of autonomous loop iterations
            max_tokens: Maximum tokens per LLM response
            model: Optional model name override
            parallel_tools: If True, execute multiple tool calls in parallel via asyncio.gather()
        """
        previous_response_id = None
        pending_tool_results = []  # Track tool results to inject into next round
        self.consecutive_error_count = 0

        # --- OPP-07: Metrics tracking initialisation ---
        self.last_loop_metrics = None
        loop_start_time = time.monotonic()
        total_error_count = 0       # Never resets — cumulative across all rounds
        completed_rounds = 0
        round_metrics_list: list[Any] = []
        final_status = "max_rounds"  # Default if the for-loop exhausts without return

        try:
            for round_num in range(max_rounds):
                log_info(f"\n--- Round {round_num + 1}/{max_rounds} ---")

                # Per-round metrics state
                round_start_time = time.monotonic()
                round_tool_calls: list[dict[str, Any]] = []
                round_errors = 0

                # Build input text with tool results injection and self-correction hints
                input_text = self._build_input_text(
                    round_num, task, pending_tool_results, self.consecutive_error_count
                )
                if round_num > 0:
                    pending_tool_results = []

                # Call /v1/responses with tools (stateful API!)
                # Use tool_choice="required" on first round to FORCE tool usage
                # This prevents LLMs from hallucinating instead of calling tools
                # On subsequent rounds, use "auto" to allow final answers
                current_tool_choice = "required" if round_num == 0 else "auto"

                # CRITICAL: Run sync HTTP call in thread pool to avoid blocking event loop
                # This prevents MCP connection TaskGroup failures during long LLM calls
                try:
                    response = await asyncio.to_thread(
                        self.llm.create_response,
                        input_text=input_text,
                        tools=openai_tools,
                        previous_response_id=previous_response_id,
                        max_tokens=max_tokens,
                        model=model,
                        tool_choice=current_tool_choice,
                        temperature=DEFAULT_TEMPERATURE
                    )
                except Exception as e:
                    self.consecutive_error_count += 1
                    total_error_count += 1
                    round_errors += 1
                    log_error(f"LLM call failed (consecutive: {self.consecutive_error_count}): {e}")
                    if self.consecutive_error_count >= MAX_CONSECUTIVE_ERRORS:
                        final_status = "aborted"
                        # Record round before early return
                        completed_rounds += 1
                        try:
                            llm_call_duration = time.monotonic() - round_start_time
                            rm = RoundMetrics(
                                round_number=completed_rounds,
                                llm_call_duration_seconds=llm_call_duration,
                                tool_calls=round_tool_calls,
                                error_count=round_errors,
                            )
                            if len(round_metrics_list) < 100:
                                round_metrics_list.append(rm)
                            else:
                                round_metrics_list.pop(0)
                                round_metrics_list.append(rm)
                        except Exception:  # noqa: S110 — metrics must never break the autonomous loop
                            pass
                        return f"Task aborted: {self.consecutive_error_count} consecutive errors. Last: {e}"
                    pending_tool_results.append(("_llm_error", f"LLM call failed: {e}"))
                    # Record this round and continue
                    completed_rounds += 1
                    try:
                        llm_call_duration = time.monotonic() - round_start_time
                        rm = RoundMetrics(
                            round_number=completed_rounds,
                            llm_call_duration_seconds=llm_call_duration,
                            tool_calls=round_tool_calls,
                            error_count=round_errors,
                        )
                        if len(round_metrics_list) < 100:
                            round_metrics_list.append(rm)
                        else:
                            round_metrics_list.pop(0)
                            round_metrics_list.append(rm)
                    except Exception:  # noqa: S110 — metrics must never break the autonomous loop
                        pass
                    continue

                llm_call_duration = time.monotonic() - round_start_time

                # Save response ID for next round (maintains conversation state)
                previous_response_id = response["id"]
                log_info(f"Response ID: {previous_response_id}")

                # Check for incomplete response (truncation)
                status = response.get("status")
                if status == "incomplete":
                    incomplete_reason = response.get("incomplete_details", {}).get("reason", "unknown")
                    log_error(f"Response incomplete: {incomplete_reason}")

                # Process output array (not choices - different format!)
                output = response.get("output", [])

                # Find text output (final answer) - it's nested inside "message" type items
                text_content = None
                for item in output:
                    if item.get("type") == "message":
                        content = item.get("content", [])
                        for content_item in content:
                            if content_item.get("type") == "output_text":
                                text_content = content_item.get("text", "")
                                log_info(f"LLM text: {text_content[:100]}...")
                                break
                        if text_content:
                            break
                    elif item.get("type") == "reasoning":
                        reasoning_content = item.get("content", [])
                        for rc in reasoning_content:
                            if rc.get("type") == "reasoning_text":
                                log_info(f"LLM reasoning: {rc.get('text', '')[:200]}...")

                # Check for function calls
                function_calls = [
                    item for item in output
                    if item.get("type") == "function_call"
                ]

                if function_calls:
                    log_info(f"LLM requested {len(function_calls)} tool call(s)")

                    if parallel_tools and len(function_calls) > 1:
                        pending_tool_results = await self._execute_tools_parallel(dispatcher, function_calls)
                    else:
                        pending_tool_results = await self._execute_tools_sequential(dispatcher, function_calls)

                    # Track tool call metrics (after execution)
                    for tc_name, tc_result in pending_tool_results:
                        is_error = "error" in str(tc_result).lower()[:20]
                        round_tool_calls.append({
                            "name": tc_name,
                            "duration_seconds": 0.0,
                            "success": not is_error,
                        })
                        if is_error:
                            round_errors += 1
                            total_error_count += 1

                    # Record completed round metrics
                    completed_rounds += 1
                    try:
                        rm = RoundMetrics(
                            round_number=completed_rounds,
                            llm_call_duration_seconds=llm_call_duration,
                            tool_calls=round_tool_calls,
                            error_count=round_errors,
                        )
                        if len(round_metrics_list) < 100:
                            round_metrics_list.append(rm)
                        else:
                            round_metrics_list.pop(0)
                            round_metrics_list.append(rm)
                    except Exception:  # noqa: S110 — metrics must never break the autonomous loop
                        pass

                    # Check abort threshold after tool execution
                    if self.consecutive_error_count >= MAX_CONSECUTIVE_ERRORS:
                        final_status = "aborted"
                        return f"Task aborted: {self.consecutive_error_count} consecutive errors. Last batch had failures."

                    # Continue loop - tool results will be injected in next iteration
                else:
                    # Final answer - no function calls
                    log_info("LLM provided final answer")

                    # Record completed round metrics (no tool calls this round)
                    completed_rounds += 1
                    try:
                        rm = RoundMetrics(
                            round_number=completed_rounds,
                            llm_call_duration_seconds=llm_call_duration,
                            tool_calls=round_tool_calls,
                            error_count=round_errors,
                        )
                        if len(round_metrics_list) < 100:
                            round_metrics_list.append(rm)
                        else:
                            round_metrics_list.pop(0)
                            round_metrics_list.append(rm)
                    except Exception:  # noqa: S110 — metrics must never break the autonomous loop
                        pass

                    final_status = "completed"
                    if text_content:
                        return text_content
                    else:
                        return "No content in response"

            return "Task incomplete: Maximum rounds reached"

        finally:
            # Always set last_loop_metrics regardless of how the loop exited.
            # Wrap in try/except so a metrics bug can NEVER break the caller.
            try:
                self.last_loop_metrics = LoopMetrics(
                    total_rounds=completed_rounds,
                    total_duration_seconds=time.monotonic() - loop_start_time,
                    total_tool_calls=sum(len(rm.tool_calls) for rm in round_metrics_list),
                    total_errors=total_error_count,
                    final_status=final_status,
                    rounds=round_metrics_list,
                )
            except Exception:
                pass  # Never break the caller for metrics


__all__ = [
    "DynamicAutonomousAgent",
    "_SingleSessionDispatcher",
    "_MultiSessionDispatcher",
]
