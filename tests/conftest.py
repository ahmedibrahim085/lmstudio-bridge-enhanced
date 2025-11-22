#!/usr/bin/env python3
"""
Pytest configuration and fixtures for MCP-dependent tests.

Per user's insight: Handle MCP availability in BOTH code and tests.

This provides pytest fixtures and decorators to:
1. Check MCP health before running tests
2. Skip tests gracefully if MCPs unavailable
3. Show clear error messages with log excerpts
"""

import pytest
import pytest_asyncio
import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.mcp_health_check import (
    MCPHealthChecker,
    check_required_mcps,
    check_filesystem_mcp,
    check_memory_mcp,
)


# ============================================================================
# Pytest Fixtures for MCP Health Checks
# ============================================================================

@pytest_asyncio.fixture(scope="session")
async def mcp_health_checker():
    """Provide MCP health checker instance for entire test session."""
    return MCPHealthChecker()


@pytest_asyncio.fixture(scope="session")
async def check_filesystem_available():
    """Check if filesystem MCP is available (session-scoped).

    Usage in test:
        async def test_my_function(check_filesystem_available):
            is_running, skip_reason = check_filesystem_available
            if not is_running:
                pytest.skip(skip_reason)
            # Continue with test...
    """
    return await check_filesystem_mcp()


@pytest_asyncio.fixture(scope="session")
async def check_memory_available():
    """Check if memory MCP is available (session-scoped)."""
    return await check_memory_mcp()


@pytest_asyncio.fixture(scope="function")
async def require_filesystem():
    """Skip test if filesystem MCP is not available.

    Usage in test:
        async def test_my_function(require_filesystem):
            # Test automatically skipped if filesystem MCP down
            # Continue with test knowing MCP is available
            ...
    """
    is_running, skip_reason = await check_filesystem_mcp()
    if not is_running:
        pytest.skip(f"Filesystem MCP not available: {skip_reason}")


@pytest_asyncio.fixture(scope="function")
async def require_memory():
    """Skip test if memory MCP is not available."""
    is_running, skip_reason = await check_memory_mcp()
    if not is_running:
        pytest.skip(f"Memory MCP not available: {skip_reason}")


@pytest_asyncio.fixture(scope="function")
async def require_mcps():
    """Factory fixture to require specific MCPs.

    Usage in test:
        async def test_my_function(require_mcps):
            # Require filesystem and memory
            await require_mcps(["filesystem", "memory"])
            # Test automatically skipped if any MCP down
            ...
    """
    async def _require_mcps(mcp_names: list[str]):
        is_running, skip_reason = await check_required_mcps(mcp_names)
        if not is_running:
            pytest.skip(f"Required MCPs not available: {skip_reason}")

    return _require_mcps


# ============================================================================
# Pytest Markers for MCP Requirements
# ============================================================================

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "requires_filesystem: mark test as requiring filesystem MCP"
    )
    config.addinivalue_line(
        "markers",
        "requires_memory: mark test as requiring memory MCP"
    )
    config.addinivalue_line(
        "markers",
        "requires_github: mark test as requiring github MCP"
    )
    config.addinivalue_line(
        "markers",
        "requires_mcps: mark test as requiring specific MCPs (list in marker)"
    )


def _check_lmstudio_available():
    """Check if LM Studio is running and available."""
    import requests
    try:
        response = requests.get("http://localhost:1234/v1/models", timeout=2)
        return response.status_code == 200
    except Exception:
        return False


def pytest_runtest_setup(item):
    """Check MCP requirements before running test.

    This automatically skips tests based on markers:

    Usage in tests:
        @pytest.mark.requires_filesystem
        async def test_my_function():
            # Automatically skipped if filesystem MCP not available
            ...

        @pytest.mark.requires_mcps(["filesystem", "memory"])
        async def test_multi_mcp():
            # Automatically skipped if either MCP not available
            ...

        @pytest.mark.e2e
        async def test_end_to_end():
            # Automatically skipped if LM Studio not running
            ...
    """
    # Get all markers
    markers = {marker.name: marker for marker in item.iter_markers()}

    # Auto-skip E2E tests if LM Studio is not available
    if "e2e" in markers:
        if not _check_lmstudio_available():
            pytest.skip(
                "LM Studio not available - E2E test requires running LM Studio.\n"
                "Start LM Studio and load a model to run E2E tests."
            )

    # Check for MCP requirement markers
    required_mcps = []

    if "requires_filesystem" in markers:
        required_mcps.append("filesystem")

    if "requires_memory" in markers:
        required_mcps.append("memory")

    if "requires_github" in markers:
        required_mcps.append("github")

    if "requires_mcps" in markers:
        # Get MCP list from marker args
        marker = markers["requires_mcps"]
        if marker.args:
            required_mcps.extend(marker.args[0])

    # If no MCP requirements, continue
    if not required_mcps:
        return

    # Check if required MCPs are available
    loop = asyncio.get_event_loop()
    is_running, skip_reason = loop.run_until_complete(
        check_required_mcps(required_mcps)
    )

    if not is_running:
        pytest.skip(
            f"Required MCPs not available: {skip_reason}\n\n"
            f"To run this test:\n"
            f"1. Ensure MCPs are configured in .mcp.json\n"
            f"2. Check that dependencies (e.g., node) are in PATH\n"
            f"3. Restart MCP servers\n"
            f"4. Run: python3 utils/mcp_health_check.py to verify"
        )


# ============================================================================
# Example Test Usage
# ============================================================================

"""
# Option 1: Use fixture
async def test_with_fixture(require_filesystem):
    # Automatically skipped if filesystem MCP not available
    # Test code here...
    pass


# Option 2: Use marker
@pytest.mark.requires_filesystem
async def test_with_marker():
    # Automatically skipped if filesystem MCP not available
    # Test code here...
    pass


# Option 3: Use multiple MCPs
@pytest.mark.requires_mcps(["filesystem", "memory"])
async def test_multi_mcp():
    # Automatically skipped if either MCP not available
    # Test code here...
    pass


# Option 4: Manual check
async def test_manual_check(require_mcps):
    # Check specific MCPs at runtime
    await require_mcps(["filesystem", "github"])
    # Test code here...
    pass


# Option 5: Check without skipping (for conditional logic)
async def test_conditional(check_filesystem_available):
    is_running, skip_reason = check_filesystem_available

    if is_running:
        # Run MCP-dependent code
        result = await some_mcp_function()
    else:
        # Run alternative code or mock
        result = mock_result()

    assert result is not None
"""
