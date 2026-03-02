"""Tests for OPP-25 Part 1: Ephemeral MCP Server Lifecycle.

Covers:
  - EphemeralIntegration frozen dataclass construction
  - validate_integration() — non-empty server_id, supported type
  - build_integrations_payload() — converts to API dict format, deduplicates

Test categories (Req 07):
- Happy: Tests 1-4  -- single integration, allowed_tools, multiple, valid validate
- Negative: Tests 5-8 -- empty server_id, unsupported type, whitespace id, build with invalid
- Edge: Tests 9-11 -- empty list, deduplication, allowed_tools=None excluded
- Boundary: Tests 12-13 -- constants exist with correct values, frozen dataclass
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# D-1: Activate testing mode BEFORE any production imports that could trigger
# get_config() -> LMStudioConfig.from_env() -> HTTP auto-detection.
from config.constants import LMSTUDIO_TESTING_ENV_VAR  # noqa: I001
os.environ.setdefault(LMSTUDIO_TESTING_ENV_VAR, "1")

from mcp_client.ephemeral import (  # noqa: E402
    EphemeralIntegration,
    build_integrations_payload,
    validate_integration,
)


# ---------------------------------------------------------------------------
# Happy Path Tests (1-4)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_build_single_integration():
    """Happy-1: Single integration without allowed_tools -> correct API dict."""
    integration = EphemeralIntegration(server_id="server-1")
    result = build_integrations_payload([integration])

    assert result == [{"type": "mcp", "id": "server-1"}]


@pytest.mark.unit
def test_build_integration_with_allowed_tools():
    """Happy-2: Integration with allowed_tools tuple -> 'allowed_tools' key in output."""
    integration = EphemeralIntegration(
        server_id="filesystem-server",
        allowed_tools=("read_file", "write_file"),
    )
    result = build_integrations_payload([integration])

    assert len(result) == 1
    assert result[0]["id"] == "filesystem-server"
    assert result[0]["type"] == "mcp"
    assert "allowed_tools" in result[0]
    assert result[0]["allowed_tools"] == ["read_file", "write_file"]


@pytest.mark.unit
def test_build_multiple_integrations():
    """Happy-3: Two integrations -> list of 2 dicts in the correct order."""
    integrations = [
        EphemeralIntegration(server_id="filesystem-server"),
        EphemeralIntegration(server_id="memory-server"),
    ]
    result = build_integrations_payload(integrations)

    assert len(result) == 2
    assert result[0]["id"] == "filesystem-server"
    assert result[1]["id"] == "memory-server"


@pytest.mark.unit
def test_validate_passes_for_valid_config():
    """Happy-4: Valid EphemeralIntegration does not raise."""
    integration = EphemeralIntegration(server_id="test")
    validate_integration(integration)  # Must not raise


# ---------------------------------------------------------------------------
# Negative Tests (5-8)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_validate_empty_server_id_raises():
    """Negative-5: Empty server_id -> ValueError raised."""
    integration = EphemeralIntegration(server_id="")
    with pytest.raises(ValueError):
        validate_integration(integration)


@pytest.mark.unit
def test_validate_unsupported_type_raises():
    """Negative-6: Unsupported type 'unknown' -> ValueError raised."""
    integration = EphemeralIntegration(server_id="some-server", type="unknown")
    with pytest.raises(ValueError):
        validate_integration(integration)


@pytest.mark.unit
def test_validate_whitespace_server_id_raises():
    """Negative-7: Whitespace-only server_id -> ValueError raised."""
    integration = EphemeralIntegration(server_id="   ")
    with pytest.raises(ValueError):
        validate_integration(integration)


@pytest.mark.unit
def test_build_with_invalid_integration_raises():
    """Negative-8: build_integrations_payload with empty server_id -> ValueError."""
    invalid = EphemeralIntegration(server_id="")
    with pytest.raises(ValueError):
        build_integrations_payload([invalid])


# ---------------------------------------------------------------------------
# Edge Tests (9-11)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_build_empty_list_returns_empty():
    """Edge-9: Empty integrations list -> empty list returned."""
    result = build_integrations_payload([])
    assert result == []


@pytest.mark.unit
def test_build_deduplicates_by_server_id():
    """Edge-10: Two integrations with same server_id -> only last one kept."""
    integrations = [
        EphemeralIntegration(server_id="dup-server"),
        EphemeralIntegration(
            server_id="dup-server", allowed_tools=("read_file",)
        ),
    ]
    result = build_integrations_payload(integrations)

    assert len(result) == 1
    # Last one wins — must include allowed_tools from the second entry
    assert "allowed_tools" in result[0]


@pytest.mark.unit
def test_allowed_tools_none_excluded_from_payload():
    """Edge-11: allowed_tools=None -> 'allowed_tools' key absent from output dict."""
    integration = EphemeralIntegration(server_id="memory-server", allowed_tools=None)
    result = build_integrations_payload([integration])

    assert len(result) == 1
    assert "allowed_tools" not in result[0]


# ---------------------------------------------------------------------------
# Boundary Tests (12-13)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_integration_constants_exist():
    """Boundary-12: INTEGRATION_TYPE_MCP, SUPPORTED_INTEGRATION_TYPES, MAX_INTEGRATIONS_PER_REQUEST importable with correct values."""
    from config.constants import (
        INTEGRATION_TYPE_MCP,
        MAX_INTEGRATIONS_PER_REQUEST,
        SUPPORTED_INTEGRATION_TYPES,
    )

    assert INTEGRATION_TYPE_MCP == "mcp"
    assert "mcp" in SUPPORTED_INTEGRATION_TYPES
    assert MAX_INTEGRATIONS_PER_REQUEST == 20


@pytest.mark.unit
def test_ephemeral_integration_is_frozen():
    """Boundary-13: EphemeralIntegration is frozen (immutable) — assignment raises."""
    integration = EphemeralIntegration(server_id="immutable-server")
    with pytest.raises((AttributeError, TypeError)):
        integration.server_id = "modified"  # type: ignore[misc]
