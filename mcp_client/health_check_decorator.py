#!/usr/bin/env python3
"""
MCP Health Check Decorators for Production Code

Use these decorators to add MCP health checks to production code,
ensuring graceful degradation when MCPs are unavailable.

Per user's insight: Handle MCP availability in BOTH code and tests.
"""

import asyncio
from functools import wraps
from typing import Optional, Callable, Any
import logging

logger = logging.getLogger(__name__)


class MCPUnavailableError(Exception):
    """Raised when an MCP is not available and operation cannot proceed."""

    def __init__(self, mcp_name: str, reason: str, log_excerpt: Optional[str] = None):
        self.mcp_name = mcp_name
        self.reason = reason
        self.log_excerpt = log_excerpt

        message = f"MCP '{mcp_name}' is not available: {reason}"
        if log_excerpt:
            message += f"\n\nLog excerpt:\n{log_excerpt[:500]}"

        super().__init__(message)


def require_mcp(mcp_name: str, return_error_message: bool = True):
    """Decorator to check if MCP is available before executing function.

    This is for PRODUCTION CODE (not tests).

    Args:
        mcp_name: Name of required MCP (e.g., "filesystem", "memory")
        return_error_message: If True, return error message instead of raising
                             If False, raise MCPUnavailableError

    Usage in production code:
        @require_mcp("filesystem", return_error_message=True)
        async def autonomous_with_mcp(mcp_name, task, ...):
            # This will check filesystem MCP before executing
            # If MCP down, returns error message instead of crashing
            ...

    Example output when MCP down:
        "Error: Filesystem MCP is not available.
         Reason: env: node: No such file or directory

         This MCP is required to access files. Please:
         1. Check that node is in your PATH
         2. Restart the MCP server
         3. Check logs at: ~/.lmstudio/server-logs/..."
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            # Import here to avoid circular dependency
            from utils.mcp_health_check import check_required_mcps

            # Check MCP health
            is_running, skip_reason = await check_required_mcps([mcp_name])

            if not is_running:
                error_msg = (
                    f"Error: {mcp_name.capitalize()} MCP is not available.\n\n"
                    f"Reason: {skip_reason}\n\n"
                    f"This MCP is required for this operation. Please:\n"
                    f"1. Check that required dependencies are installed\n"
                    f"2. Verify MCP is configured in .mcp.json\n"
                    f"3. Restart the MCP server\n"
                    f"4. Check logs for details:\n"
                    f"   - LM Studio: ~/.lmstudio/server-logs/\n"
                    f"   - Claude: ~/Library/Logs/Claude/main.log\n"
                )

                if return_error_message:
                    # Return error message (graceful degradation)
                    logger.error(f"MCP {mcp_name} unavailable: {skip_reason}")
                    return error_msg
                else:
                    # Raise exception
                    raise MCPUnavailableError(mcp_name, skip_reason)

            # MCP is available, proceed with function
            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            # For sync functions, run async check in event loop
            from utils.mcp_health_check import check_required_mcps

            loop = asyncio.get_event_loop()
            is_running, skip_reason = loop.run_until_complete(
                check_required_mcps([mcp_name])
            )

            if not is_running:
                error_msg = (
                    f"Error: {mcp_name.capitalize()} MCP is not available.\n\n"
                    f"Reason: {skip_reason}\n\n"
                    f"This MCP is required for this operation. Please:\n"
                    f"1. Check that required dependencies are installed\n"
                    f"2. Verify MCP is configured in .mcp.json\n"
                    f"3. Restart the MCP server\n"
                    f"4. Check logs for details"
                )

                if return_error_message:
                    logger.error(f"MCP {mcp_name} unavailable: {skip_reason}")
                    return error_msg
                else:
                    raise MCPUnavailableError(mcp_name, skip_reason)

            return func(*args, **kwargs)

        # Return appropriate wrapper based on whether function is async
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def require_any_mcp(mcp_names: list[str], return_error_message: bool = True):
    """Decorator to check if ANY of the required MCPs is available.

    Use when function can work with any one of multiple MCPs.

    Args:
        mcp_names: List of MCP names (e.g., ["filesystem", "memory"])
        return_error_message: If True, return error instead of raising

    Usage:
        @require_any_mcp(["filesystem", "memory"])
        async def discover_and_execute(task):
            # Needs at least one MCP to work
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            from utils.mcp_health_check import MCPHealthChecker

            checker = MCPHealthChecker()
            statuses = await checker.check_all_mcps(mcp_names)

            # Check if ANY MCP is running
            any_running = any(status.running for status in statuses.values())

            if not any_running:
                all_errors = [
                    f"{name}: {status.error}"
                    for name, status in statuses.items()
                    if not status.running
                ]

                error_msg = (
                    f"Error: None of the required MCPs are available.\n\n"
                    f"Required (any one of): {', '.join(mcp_names)}\n\n"
                    f"Status:\n" + "\n".join(f"  - {err}" for err in all_errors) + "\n\n"
                    f"Please check MCP configuration and logs."
                )

                if return_error_message:
                    logger.error(f"No MCPs available from: {mcp_names}")
                    return error_msg
                else:
                    raise MCPUnavailableError(
                        mcp_names[0],
                        f"None of {mcp_names} available"
                    )

            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            from utils.mcp_health_check import MCPHealthChecker

            checker = MCPHealthChecker()
            loop = asyncio.get_event_loop()
            statuses = loop.run_until_complete(checker.check_all_mcps(mcp_names))

            any_running = any(status.running for status in statuses.values())

            if not any_running:
                all_errors = [
                    f"{name}: {status.error}"
                    for name, status in statuses.items()
                    if not status.running
                ]

                error_msg = (
                    f"Error: None of the required MCPs are available.\n\n"
                    f"Required (any one of): {', '.join(mcp_names)}\n\n"
                    f"Status:\n" + "\n".join(f"  - {err}" for err in all_errors)
                )

                if return_error_message:
                    logger.error(f"No MCPs available from: {mcp_names}")
                    return error_msg
                else:
                    raise MCPUnavailableError(
                        mcp_names[0],
                        f"None of {mcp_names} available"
                    )

            return func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# Convenience decorators for specific MCPs

def require_filesystem(return_error_message: bool = True):
    """Decorator for functions that require filesystem MCP."""
    return require_mcp("filesystem", return_error_message)


def require_memory(return_error_message: bool = True):
    """Decorator for functions that require memory MCP."""
    return require_mcp("memory", return_error_message)


def require_github(return_error_message: bool = True):
    """Decorator for functions that require github MCP."""
    return require_mcp("github", return_error_message)


# Example usage in production code:

"""
# In tools/dynamic_autonomous.py:

from mcp_client.health_check_decorator import require_filesystem

class DynamicAutonomousAgent:

    @require_filesystem(return_error_message=True)
    async def autonomous_with_mcp(self, mcp_name: str, task: str, ...):
        '''
        If filesystem MCP is down, this will return:

        "Error: Filesystem MCP is not available.

         Reason: env: node: No such file or directory

         This MCP is required for this operation. Please:
         1. Check that required dependencies are installed
         2. Verify MCP is configured in .mcp.json
         3. Restart the MCP server
         4. Check logs for details..."

        Instead of crashing with cryptic error.
        '''
        # Function continues normally if MCP is available
        ...
"""
