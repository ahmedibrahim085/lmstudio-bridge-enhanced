#!/usr/bin/env python3
"""
Pytest configuration and fixtures for MCP-dependent tests.

Per user's insight: Handle MCP availability in BOTH code and tests.

This provides pytest fixtures and decorators to:
1. Check MCP health before running tests
2. Skip tests gracefully if MCPs unavailable
3. Show clear error messages with log excerpts

Architecture Boundary — Test Fixtures vs Production Code
=========================================================
Test fixtures (model_discovery, model_lifecycle, model_management) use
LMSHelper exclusively for LM Studio interaction. Production code uses
ModelValidator for model validation with its own class-level cache.

These two worlds MUST NOT cross:
- Test fixtures NEVER call ModelValidator (prevents cache pollution)
- ModelValidator's class cache is reset via opt-in fixture for tests that need isolation
- discover_models() and ModelLifecycleManager delegate to LMSHelper only
"""

import asyncio
import logging
import os
import sys

import pytest
import pytest_asyncio

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from llm.model_validator import ModelValidator
from tests.fixtures.model_discovery import discover_models
from tests.fixtures.model_lifecycle import ModelLifecycleManager
from utils.mcp_health_check import (
    MCPHealthChecker,
    check_filesystem_mcp,
    check_memory_mcp,
    check_required_mcps,
)

logger = logging.getLogger(__name__)


@pytest.fixture
def reset_model_validator_cache():
    """Reset ModelValidator class-level cache. Opt-in only.

    Use this fixture in tests that mock _fetch_models() differently
    and need cache isolation. Most tests should let the cache work
    naturally (30s TTL) to match production behavior.

    Uses reset_cache() classmethod (thread-safe, via _class_cache_lock)
    rather than direct attribute assignment.
    """
    ModelValidator.reset_cache()
    yield
    ModelValidator.reset_cache()


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
    config.addinivalue_line(
        "markers",
        "flaky: mark test as flaky (eligible for targeted reruns)"
    )
    config.addinivalue_line(
        "markers",
        "model_required: mark test as requiring a specific model loaded"
    )
    config.addinivalue_line(
        "markers",
        "unit: mark test as pure unit test (no external dependencies)"
    )


def _check_lmstudio_available():
    """Check if LM Studio is running and available."""
    import httpx

    from config.constants import DEFAULT_LMSTUDIO_BASE_URL, MODELS_ENDPOINT
    try:
        response = httpx.get(
            f"{DEFAULT_LMSTUDIO_BASE_URL}{MODELS_ENDPOINT}", timeout=2.0
        )
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
# Session-Level Model Management Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def discovered_models():
    """Discover available models once at session start.

    Returns DiscoveredModels with loaded_ids, downloaded_ids, roles.
    Safe when LM Studio is unavailable (returns empty DiscoveredModels).
    """
    result = discover_models()
    if result.lmstudio_available:
        logger.info(
            f"Session discovery: {len(result.loaded_ids)} loaded, "
            f"{len(result.roles)} roles"
        )
    else:
        logger.info("Session discovery: LM Studio not available")
    return result


@pytest.fixture(scope="session")
def model_lifecycle(discovered_models):
    """Session-scoped model lifecycle manager.

    Cleans up duplicate model instances at session start.
    Unloads models we loaded at session end.
    """
    mgr = ModelLifecycleManager()

    if discovered_models.lmstudio_available:
        cleaned = mgr.cleanup_duplicates()
        if cleaned:
            logger.info(f"Session start: cleaned {cleaned} duplicate model(s)")

    yield mgr

    if discovered_models.lmstudio_available:
        unloaded = mgr.unload_models_we_loaded()
        if unloaded:
            logger.info(f"Session teardown: unloaded {unloaded} model(s)")


@pytest.fixture(scope="session")
def lmstudio_available(discovered_models):
    """Boolean: whether LM Studio was reachable at session start."""
    return discovered_models.lmstudio_available


# ============================================================================
# Test Requirement Fixtures
# ============================================================================

@pytest.fixture
def require_lmstudio(lmstudio_available):
    """Skip test if LM Studio is not running."""
    if not lmstudio_available:
        pytest.skip("LM Studio not available")


@pytest.fixture
def require_chat_model(discovered_models):
    """Skip if no chat model available. Returns the model name."""
    model = discovered_models.chat_model
    if not model:
        pytest.skip("No chat model available")
    return model


@pytest.fixture
def require_multiple_models(discovered_models):
    """Skip if fewer than 2 models are loaded."""
    if len(discovered_models.loaded_ids) < 2:
        pytest.skip(
            f"Need 2+ loaded models, have {len(discovered_models.loaded_ids)}"
        )
    return discovered_models.loaded_ids


# ============================================================================
# Test Phase Ordering
# ============================================================================

def pytest_collection_modifyitems(config, items):
    """Reorder tests: unit first, integration second, e2e last.

    This ensures fast unit tests run before slower integration/e2e tests,
    giving faster feedback on basic correctness before hitting external deps.
    """
    unit_tests = []
    integration_tests = []
    e2e_tests = []
    other_tests = []

    for item in items:
        markers = {m.name for m in item.iter_markers()}
        if "e2e" in markers:
            e2e_tests.append(item)
        elif "integration" in markers:
            integration_tests.append(item)
        elif "unit" in markers:
            unit_tests.append(item)
        else:
            # Unmarked tests treated as unit-level (fastest first)
            other_tests.append(item)

    # Reorder: unit/unmarked → integration → e2e
    items[:] = unit_tests + other_tests + integration_tests + e2e_tests


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
