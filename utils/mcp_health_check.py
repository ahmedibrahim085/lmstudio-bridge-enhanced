#!/usr/bin/env python3
"""
MCP Health Check Utility

Per user's brilliant suggestion: Check if MCPs are actually running
before executing tests, and skip tests gracefully with clear error
messages if MCPs are down.

This prevents cryptic test failures when the real issue is MCP
server crashes or connectivity problems.
"""

import asyncio
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class MCPStatus:
    """Status of an MCP server."""
    name: str
    running: bool
    error: Optional[str] = None
    log_excerpt: Optional[str] = None


class MCPHealthChecker:
    """Check health of MCP servers before running tests."""

    def __init__(self):
        self.mcp_config_path = Path.home() / ".mcp.json"
        self.lms_log_dir = Path.home() / ".lmstudio" / "server-logs"
        self.claude_log_dir = Path.home() / "Library" / "Logs" / "Claude"

    def check_mcp_config(self) -> Dict:
        """Load MCP configuration."""
        if not self.mcp_config_path.exists():
            return {}

        try:
            with open(self.mcp_config_path) as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  Warning: Could not load .mcp.json: {e}")
            return {}

    def get_latest_lms_log(self) -> Optional[Path]:
        """Get the latest LM Studio server log file."""
        if not self.lms_log_dir.exists():
            return None

        # Find all log files
        log_files = list(self.lms_log_dir.glob("**/*.log"))
        if not log_files:
            return None

        # Return the most recent
        return max(log_files, key=lambda p: p.stat().st_mtime)

    def check_lms_log_for_mcp_errors(self, mcp_name: str) -> Tuple[bool, Optional[str]]:
        """Check LM Studio logs for MCP errors.

        Returns:
            (has_errors, error_excerpt)
        """
        log_file = self.get_latest_lms_log()
        if not log_file:
            return False, "No LM Studio logs found"

        try:
            with open(log_file) as f:
                # Read last 200 lines
                lines = f.readlines()[-200:]

            # Look for errors related to this MCP
            errors = []
            for i, line in enumerate(lines):
                if mcp_name in line.lower() and "error" in line.lower():
                    # Include context (2 lines before and after)
                    start = max(0, i - 2)
                    end = min(len(lines), i + 3)
                    context = ''.join(lines[start:end])
                    errors.append(context)

            if errors:
                # Return first error with context
                return True, errors[0]

            return False, None

        except Exception as e:
            return False, f"Could not read log: {e}"

    def check_claude_log_for_mcp_errors(self, mcp_name: str) -> Tuple[bool, Optional[str]]:
        """Check Claude Code logs for MCP errors.

        Returns:
            (has_errors, error_excerpt)
        """
        main_log = self.claude_log_dir / "main.log"
        if not main_log.exists():
            return False, "No Claude logs found"

        try:
            with open(main_log) as f:
                lines = f.readlines()[-200:]

            errors = []
            for i, line in enumerate(lines):
                if mcp_name in line.lower() and ("error" in line.lower() or "fail" in line.lower()):
                    start = max(0, i - 2)
                    end = min(len(lines), i + 3)
                    context = ''.join(lines[start:end])
                    errors.append(context)

            if errors:
                return True, errors[0]

            return False, None

        except Exception as e:
            return False, f"Could not read log: {e}"

    async def ping_mcp(self, mcp_name: str, mcp_config: Dict) -> bool:
        """Try to connect to an MCP server.

        Returns:
            True if MCP responds, False otherwise
        """
        try:
            # Try to import MCP client
            from mcp_client.connection import MCPConnection

            # Create a connection
            conn = MCPConnection(mcp_name, mcp_config)

            # Try to connect with short timeout
            try:
                async with asyncio.timeout(5.0):
                    await conn.connect()
                    # If we get here, connection succeeded
                    await conn.disconnect()
                    return True
            except asyncio.TimeoutError:
                return False
            except Exception:
                return False

        except Exception:
            # Import failed or other issue
            return False

    async def check_mcp_health(self, mcp_name: str) -> MCPStatus:
        """Check health of a specific MCP.

        Args:
            mcp_name: Name of the MCP (e.g., "filesystem", "memory")

        Returns:
            MCPStatus with details about the MCP's health
        """
        # Load MCP configuration
        config = self.check_mcp_config()
        mcp_servers = config.get("mcpServers", {})

        if mcp_name not in mcp_servers:
            return MCPStatus(
                name=mcp_name,
                running=False,
                error=f"MCP '{mcp_name}' not configured in .mcp.json"
            )

        mcp_config = mcp_servers[mcp_name]

        # Check if disabled
        if mcp_config.get("disabled", False):
            return MCPStatus(
                name=mcp_name,
                running=False,
                error=f"MCP '{mcp_name}' is disabled in .mcp.json"
            )

        # Try to ping the MCP
        can_connect = await self.ping_mcp(mcp_name, mcp_config)

        if can_connect:
            return MCPStatus(name=mcp_name, running=True)

        # MCP is not responding - check logs for why
        # Check LM Studio logs (if testing with LM Studio)
        has_lms_errors, lms_error = self.check_lms_log_for_mcp_errors(mcp_name)

        # Check Claude logs
        has_claude_errors, claude_error = self.check_claude_log_for_mcp_errors(mcp_name)

        # Compile error information
        error_msg = f"MCP '{mcp_name}' not responding"
        log_excerpt = None

        if has_lms_errors and lms_error:
            error_msg += " (LM Studio log shows errors)"
            log_excerpt = f"LM Studio log:\n{lms_error}"
        elif has_claude_errors and claude_error:
            error_msg += " (Claude log shows errors)"
            log_excerpt = f"Claude log:\n{claude_error}"

        return MCPStatus(
            name=mcp_name,
            running=False,
            error=error_msg,
            log_excerpt=log_excerpt
        )

    async def check_all_mcps(self, required_mcps: List[str]) -> Dict[str, MCPStatus]:
        """Check health of all required MCPs.

        Args:
            required_mcps: List of MCP names to check

        Returns:
            Dictionary mapping MCP name to MCPStatus
        """
        results = {}

        for mcp_name in required_mcps:
            status = await self.check_mcp_health(mcp_name)
            results[mcp_name] = status

        return results

    def print_mcp_status_report(self, statuses: Dict[str, MCPStatus]):
        """Print a formatted report of MCP statuses."""
        print("\n" + "="*80)
        print("MCP HEALTH CHECK REPORT")
        print("="*80)

        for mcp_name, status in statuses.items():
            if status.running:
                print(f"✅ {mcp_name:20s} - RUNNING")
            else:
                print(f"❌ {mcp_name:20s} - NOT RUNNING")
                print(f"   Error: {status.error}")
                if status.log_excerpt:
                    print(f"   Log excerpt:")
                    for line in status.log_excerpt.split('\n')[:5]:
                        print(f"      {line}")

        print("="*80)

    def should_skip_tests(self, statuses: Dict[str, MCPStatus], required_mcps: List[str]) -> Tuple[bool, str]:
        """Determine if tests should be skipped based on MCP health.

        Args:
            statuses: MCP status results
            required_mcps: List of MCPs required for tests

        Returns:
            (should_skip, reason)
        """
        down_mcps = [
            name for name, status in statuses.items()
            if not status.running and name in required_mcps
        ]

        if not down_mcps:
            return False, ""

        reasons = []
        for mcp_name in down_mcps:
            status = statuses[mcp_name]
            reason = f"{mcp_name}: {status.error}"
            if status.log_excerpt:
                # Include first line of log excerpt
                first_log_line = status.log_excerpt.split('\n')[0]
                reason += f" ({first_log_line[:100]}...)"
            reasons.append(reason)

        return True, "; ".join(reasons)


# Convenience functions for pytest

async def check_filesystem_mcp() -> Tuple[bool, str]:
    """Check if filesystem MCP is running.

    Returns:
        (is_running, skip_reason)
    """
    checker = MCPHealthChecker()
    status = await checker.check_mcp_health("filesystem")

    if status.running:
        return True, ""

    skip_reason = f"Filesystem MCP not running: {status.error}"
    if status.log_excerpt:
        skip_reason += f"\nLog: {status.log_excerpt[:200]}"

    return False, skip_reason


async def check_memory_mcp() -> Tuple[bool, str]:
    """Check if memory MCP is running."""
    checker = MCPHealthChecker()
    status = await checker.check_mcp_health("memory")

    if status.running:
        return True, ""

    skip_reason = f"Memory MCP not running: {status.error}"
    if status.log_excerpt:
        skip_reason += f"\nLog: {status.log_excerpt[:200]}"

    return False, skip_reason


async def check_required_mcps(mcp_names: List[str]) -> Tuple[bool, str]:
    """Check if all required MCPs are running.

    Args:
        mcp_names: List of required MCP names

    Returns:
        (all_running, skip_reason)
    """
    checker = MCPHealthChecker()
    statuses = await checker.check_all_mcps(mcp_names)

    should_skip, reason = checker.should_skip_tests(statuses, mcp_names)

    if should_skip:
        return False, reason

    return True, ""


# For use in tests
def pytest_skip_if_mcp_down(mcp_names: List[str]):
    """Decorator to skip pytest tests if MCPs are down.

    Usage:
        @pytest_skip_if_mcp_down(["filesystem", "memory"])
        async def test_my_function():
            ...
    """
    import pytest

    def decorator(func):
        async def wrapper(*args, **kwargs):
            all_running, skip_reason = await check_required_mcps(mcp_names)
            if not all_running:
                pytest.skip(f"Required MCPs not running: {skip_reason}")
            return await func(*args, **kwargs)
        return wrapper
    return decorator


if __name__ == "__main__":
    # Test the health checker
    async def main():
        checker = MCPHealthChecker()

        # Check specific MCPs
        print("Checking MCP health...")
        statuses = await checker.check_all_mcps(["filesystem", "memory", "github"])

        checker.print_mcp_status_report(statuses)

        # Check if tests should be skipped
        should_skip, reason = checker.should_skip_tests(
            statuses,
            required_mcps=["filesystem"]
        )

        if should_skip:
            print(f"\n⚠️  Tests should be SKIPPED: {reason}")
        else:
            print("\n✅ All required MCPs are running - tests can proceed")

    asyncio.run(main())
