#!/usr/bin/env python3
"""
OPP-18: Integration tests for headless deployment detection.

These tests require a live LM Studio instance (GUI or llmster daemon)
running on localhost:1234.  They are automatically skipped when no
server is detected, so they never block the regular test suite.

Run manually:
    # Start LM Studio (GUI or llmster) then:
    python3 -m pytest tests/standalone/test_integration_headless.py -v

Or as part of CI that has LM Studio available:
    python3 -m pytest tests/standalone/test_integration_headless.py \
        -m integration -v
"""

import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from config.constants import DEFAULT_LMSTUDIO_BASE_URL
from tools.health import HealthTools, ServerType


# ---------------------------------------------------------------------------
# Helper: check whether LM Studio is reachable at all
# ---------------------------------------------------------------------------


def is_lmstudio_running() -> bool:
    """Return True if LM Studio server is reachable on localhost:1234."""
    try:
        import httpx
        resp = httpx.get(f"{DEFAULT_LMSTUDIO_BASE_URL}/v1/models", timeout=2.0)
        return resp.status_code == 200
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.flaky(reruns=1, reruns_delay=3)
@pytest.mark.asyncio
@pytest.mark.skipif(not is_lmstudio_running(), reason="LM Studio not available")
async def test_headless_detection_integration():
    """Integration test for server type detection against a real server.

    When LM Studio is running, check_server_type() must return a valid
    ServerType that is NOT UNAVAILABLE.
    """
    tools = HealthTools()
    server_type = await tools.check_server_type()

    assert server_type in (
        ServerType.GUI,
        ServerType.HEADLESS,
        ServerType.UNKNOWN,
    ), (
        f"Expected GUI, HEADLESS, or UNKNOWN when server is running; "
        f"got {server_type}"
    )


@pytest.mark.integration
@pytest.mark.flaky(reruns=1, reruns_delay=3)
@pytest.mark.asyncio
@pytest.mark.skipif(not is_lmstudio_running(), reason="LM Studio not available")
async def test_health_report_is_complete_integration():
    """check_server_health() returns a complete dict against a real server."""
    tools = HealthTools()
    report = await tools.check_server_health()

    # Structural checks
    assert isinstance(report, dict)
    assert "available" in report
    assert "server_type" in report
    assert "loaded_models" in report
    assert "model_count" in report
    assert "suggestions" in report

    # When server is running, available must be True
    assert report["available"] is True

    # model_count must match actual list length
    assert report["model_count"] == len(report["loaded_models"])

    # server_type must be a known value
    assert report["server_type"] in {st.value for st in ServerType}


@pytest.mark.integration
@pytest.mark.flaky(reruns=1, reruns_delay=3)
@pytest.mark.asyncio
@pytest.mark.skipif(not is_lmstudio_running(), reason="LM Studio not available")
async def test_server_type_is_consistent_across_calls_integration():
    """Two consecutive calls must return the same server type.

    Guards against flapping (e.g. type changes mid-check).
    """
    tools = HealthTools()
    type_first = await tools.check_server_type()
    type_second = await tools.check_server_type()

    assert type_first == type_second, (
        f"Server type changed between calls: {type_first} -> {type_second}"
    )


@pytest.mark.integration
@pytest.mark.flaky(reruns=1, reruns_delay=3)
@pytest.mark.asyncio
async def test_unavailable_detection_integration():
    """When no server is running, check_server_type returns UNAVAILABLE.

    This test uses a non-existent port so it always runs regardless of
    whether LM Studio is available on :1234.
    """
    tools = HealthTools()
    # Point at a port nothing listens on
    tools._base_url = "http://localhost:19999"

    server_type = await tools.check_server_type()
    assert server_type == ServerType.UNAVAILABLE


@pytest.mark.integration
@pytest.mark.flaky(reruns=1, reruns_delay=3)
@pytest.mark.asyncio
async def test_graceful_health_report_when_unavailable_integration():
    """check_server_health returns structured error when server is down."""
    tools = HealthTools()
    tools._base_url = "http://localhost:19999"

    report = await tools.check_server_health()

    assert report["available"] is False
    assert report["server_type"] == ServerType.UNAVAILABLE.value
    assert report["model_count"] == 0
    assert len(report["suggestions"]) > 0

    # Suggestions must mention llmster
    combined = " ".join(report["suggestions"]).lower()
    assert "llmster" in combined
