#!/usr/bin/env python3
"""
OPP-18: Headless Deployment (llmster) — TDD Tests.

Tests for:
1. ServerType enum — GUI, HEADLESS, UNKNOWN, UNAVAILABLE
2. Server type detection — detect whether connected to llmster vs GUI LM Studio
3. Enhanced health checks — comprehensive status including server type, models, VRAM
4. Graceful degradation — clear errors and suggestions when server is unavailable
5. MCP tool registration — check_server_type and check_server_health exposed as tools

TDD: Tests written FIRST (RED phase). Implementation follows.
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config.constants import (
    DIAGNOSTICS_ENDPOINT,
    HEALTH_CHECK_INTERVAL,
    HEALTH_CHECK_TIMEOUT,
    LLMSTER_PROCESS_NAME,
    SERVER_TYPE_HEADER,
    SYSTEM_STATUS_ENDPOINT,
)
from tools.health import (
    HealthTools,
    ServerType,
    register_health_tools,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def health_tools():
    """HealthTools with a mocked LLMClient."""
    with patch("tools.health.LLMClient") as mock_cls:
        mock_llm = MagicMock()
        mock_cls.return_value = mock_llm
        tools = HealthTools()
    return tools


@pytest.fixture
def mock_http_200_gui():
    """Simulates a GUI LM Studio /api/v1/diagnostics response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 200
    resp.headers = {"x-lmstudio-server-type": "gui"}
    resp.json.return_value = {
        "serverType": "gui",
        "version": "0.4.1",
        "uptime": 3600,
    }
    return resp


@pytest.fixture
def mock_http_200_headless():
    """Simulates a headless llmster /api/v1/diagnostics response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 200
    resp.headers = {"x-lmstudio-server-type": "headless"}
    resp.json.return_value = {
        "serverType": "headless",
        "version": "0.4.2",
        "uptime": 120,
    }
    return resp


@pytest.fixture
def mock_http_200_no_type():
    """Simulates a server that responds 200 but gives no type hint."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 200
    resp.headers = {}
    resp.json.return_value = {"version": "0.3.9"}
    return resp


@pytest.fixture
def mock_http_404():
    """Simulates diagnostics endpoint not found (older server)."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 404
    resp.headers = {}
    resp.json.return_value = {}
    return resp


# ---------------------------------------------------------------------------
# Tests: ServerType enum
# ---------------------------------------------------------------------------


class TestServerTypeEnum:
    """ServerType enum must have all four members."""

    def test_gui_member_exists(self):
        assert ServerType.GUI is not None

    def test_headless_member_exists(self):
        assert ServerType.HEADLESS is not None

    def test_unknown_member_exists(self):
        assert ServerType.UNKNOWN is not None

    def test_unavailable_member_exists(self):
        assert ServerType.UNAVAILABLE is not None

    def test_members_are_distinct(self):
        members = {ServerType.GUI, ServerType.HEADLESS, ServerType.UNKNOWN, ServerType.UNAVAILABLE}
        assert len(members) == 4

    def test_string_representation(self):
        """Each member should have a readable string value."""
        for member in ServerType:
            assert isinstance(member.value, str)
            assert len(member.value) > 0


# ---------------------------------------------------------------------------
# Tests: check_server_type — happy path GUI
# ---------------------------------------------------------------------------


class TestCheckServerTypeGUI:
    """Detect GUI LM Studio server from diagnostics endpoint."""

    @pytest.mark.asyncio
    async def test_returns_gui_when_header_says_gui(self, health_tools, mock_http_200_gui):
        with patch("tools.health.httpx.get", return_value=mock_http_200_gui):
            result = await health_tools.check_server_type()
        assert result == ServerType.GUI

    @pytest.mark.asyncio
    async def test_returns_gui_when_body_says_gui(self, health_tools):
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 200
        resp.headers = {}  # No header hint
        resp.json.return_value = {"serverType": "gui"}
        with patch("tools.health.httpx.get", return_value=resp):
            result = await health_tools.check_server_type()
        assert result == ServerType.GUI


# ---------------------------------------------------------------------------
# Tests: check_server_type — happy path headless
# ---------------------------------------------------------------------------


class TestCheckServerTypeHeadless:
    """Detect llmster (headless) server from diagnostics endpoint."""

    @pytest.mark.asyncio
    async def test_returns_headless_when_header_says_headless(
        self, health_tools, mock_http_200_headless,
    ):
        with patch("tools.health.httpx.get", return_value=mock_http_200_headless):
            result = await health_tools.check_server_type()
        assert result == ServerType.HEADLESS

    @pytest.mark.asyncio
    async def test_returns_headless_when_body_says_headless(self, health_tools):
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 200
        resp.headers = {}
        resp.json.return_value = {"serverType": "headless"}
        with patch("tools.health.httpx.get", return_value=resp):
            result = await health_tools.check_server_type()
        assert result == ServerType.HEADLESS

    @pytest.mark.asyncio
    async def test_header_takes_priority_over_body(self, health_tools):
        """When header says headless but body says gui, trust the header."""
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 200
        resp.headers = {"x-lmstudio-server-type": "headless"}
        resp.json.return_value = {"serverType": "gui"}
        with patch("tools.health.httpx.get", return_value=resp):
            result = await health_tools.check_server_type()
        assert result == ServerType.HEADLESS


# ---------------------------------------------------------------------------
# Tests: check_server_type — UNKNOWN (server up, no type info)
# ---------------------------------------------------------------------------


class TestCheckServerTypeUnknown:
    """Server responds 200 but gives no type information."""

    @pytest.mark.asyncio
    async def test_returns_unknown_when_no_type_hint(self, health_tools, mock_http_200_no_type):
        with patch("tools.health.httpx.get", return_value=mock_http_200_no_type):
            result = await health_tools.check_server_type()
        assert result == ServerType.UNKNOWN

    @pytest.mark.asyncio
    async def test_returns_unknown_when_diagnostics_404_but_models_ok(
        self, health_tools, mock_http_404,
    ):
        """Diagnostics endpoint missing (older server) but /v1/models works."""
        models_resp = MagicMock(spec=httpx.Response)
        models_resp.status_code = 200

        def side_effect(url, **kwargs):
            if "diagnostics" in url or "system/status" in url:
                return mock_http_404
            return models_resp

        with patch("tools.health.httpx.get", side_effect=side_effect):
            result = await health_tools.check_server_type()
        assert result == ServerType.UNKNOWN


# ---------------------------------------------------------------------------
# Tests: check_server_type — UNAVAILABLE (server not running)
# ---------------------------------------------------------------------------


class TestCheckServerTypeUnavailable:
    """Server not running — connection errors must return UNAVAILABLE."""

    @pytest.mark.asyncio
    async def test_returns_unavailable_on_connection_error(self, health_tools):
        with patch("tools.health.httpx.get", side_effect=httpx.ConnectError("refused")):
            result = await health_tools.check_server_type()
        assert result == ServerType.UNAVAILABLE

    @pytest.mark.asyncio
    async def test_returns_unavailable_on_timeout(self, health_tools):
        with patch("tools.health.httpx.get", side_effect=httpx.TimeoutException("timed out")):
            result = await health_tools.check_server_type()
        assert result == ServerType.UNAVAILABLE

    @pytest.mark.asyncio
    async def test_returns_unavailable_on_read_error(self, health_tools):
        with patch("tools.health.httpx.get", side_effect=httpx.ReadError("connection reset")):
            result = await health_tools.check_server_type()
        assert result == ServerType.UNAVAILABLE

    @pytest.mark.asyncio
    async def test_does_not_crash_on_unexpected_exception(self, health_tools):
        """Any unexpected exception must still return UNAVAILABLE, never raise."""
        with patch("tools.health.httpx.get", side_effect=RuntimeError("unexpected")):
            result = await health_tools.check_server_type()
        assert result == ServerType.UNAVAILABLE


# ---------------------------------------------------------------------------
# Tests: check_server_health — comprehensive health status
# ---------------------------------------------------------------------------


class TestCheckServerHealth:
    """check_server_health returns rich dict with server_type, models, VRAM."""

    @pytest.mark.asyncio
    async def test_health_includes_server_type(self, health_tools):
        with patch.object(health_tools, "check_server_type", new_callable=AsyncMock) as mock_type:
            mock_type.return_value = ServerType.GUI
            health_tools.llm.health_check.return_value = True
            health_tools.llm.list_models.return_value = ["model-a"]
            result = await health_tools.check_server_health()
        assert "server_type" in result
        assert result["server_type"] == ServerType.GUI.value

    @pytest.mark.asyncio
    async def test_health_includes_available_flag(self, health_tools):
        with patch.object(health_tools, "check_server_type", new_callable=AsyncMock) as mock_type:
            mock_type.return_value = ServerType.GUI
            health_tools.llm.health_check.return_value = True
            health_tools.llm.list_models.return_value = []
            result = await health_tools.check_server_health()
        assert "available" in result
        assert result["available"] is True

    @pytest.mark.asyncio
    async def test_health_includes_loaded_models(self, health_tools):
        with patch.object(health_tools, "check_server_type", new_callable=AsyncMock) as mock_type:
            mock_type.return_value = ServerType.HEADLESS
            health_tools.llm.health_check.return_value = True
            health_tools.llm.list_models.return_value = ["llama-3", "qwen-3"]
            result = await health_tools.check_server_health()
        assert "loaded_models" in result
        assert result["loaded_models"] == ["llama-3", "qwen-3"]

    @pytest.mark.asyncio
    async def test_health_includes_model_count(self, health_tools):
        with patch.object(health_tools, "check_server_type", new_callable=AsyncMock) as mock_type:
            mock_type.return_value = ServerType.GUI
            health_tools.llm.health_check.return_value = True
            health_tools.llm.list_models.return_value = ["m1", "m2", "m3"]
            result = await health_tools.check_server_health()
        assert "model_count" in result
        assert result["model_count"] == 3

    @pytest.mark.asyncio
    async def test_health_unavailable_when_server_down(self, health_tools):
        with patch.object(health_tools, "check_server_type", new_callable=AsyncMock) as mock_type:
            mock_type.return_value = ServerType.UNAVAILABLE
            result = await health_tools.check_server_health()
        assert result["available"] is False
        assert result["server_type"] == ServerType.UNAVAILABLE.value

    @pytest.mark.asyncio
    async def test_health_includes_suggestions_when_unavailable(self, health_tools):
        """When server is down, response must include actionable suggestions."""
        with patch.object(health_tools, "check_server_type", new_callable=AsyncMock) as mock_type:
            mock_type.return_value = ServerType.UNAVAILABLE
            result = await health_tools.check_server_health()
        assert "suggestions" in result
        assert len(result["suggestions"]) > 0

    @pytest.mark.asyncio
    async def test_health_suggestions_mention_llmster(self, health_tools):
        """Suggestions for starting the server must mention llmster."""
        with patch.object(health_tools, "check_server_type", new_callable=AsyncMock) as mock_type:
            mock_type.return_value = ServerType.UNAVAILABLE
            result = await health_tools.check_server_health()
        suggestions_text = " ".join(result["suggestions"]).lower()
        assert "llmster" in suggestions_text

    @pytest.mark.asyncio
    async def test_health_never_raises(self, health_tools):
        """check_server_health must never raise — always returns a dict."""
        with patch.object(health_tools, "check_server_type", new_callable=AsyncMock) as mock_type:
            mock_type.side_effect = RuntimeError("catastrophic failure")
            result = await health_tools.check_server_health()
        assert isinstance(result, dict)
        assert result["available"] is False


# ---------------------------------------------------------------------------
# Tests: graceful degradation — clear error messages
# ---------------------------------------------------------------------------


class TestGracefulDegradation:
    """When server is unavailable, errors must be clear and helpful."""

    @pytest.mark.asyncio
    async def test_health_check_returns_string_not_exception(self, health_tools):
        health_tools.llm.health_check.side_effect = ConnectionError("refused")
        result = await health_tools.health_check()
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_list_models_returns_string_not_exception(self, health_tools):
        health_tools.llm.list_models.side_effect = ConnectionError("refused")
        result = await health_tools.list_models()
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_check_server_type_returns_enum_not_exception(self, health_tools):
        with patch("tools.health.httpx.get", side_effect=OSError("network down")):
            result = await health_tools.check_server_type()
        assert isinstance(result, ServerType)

    @pytest.mark.asyncio
    async def test_health_check_unavailable_message_is_helpful(self, health_tools):
        """Error message must not be a bare traceback — must be user-friendly."""
        health_tools.llm.health_check.return_value = False
        result = await health_tools.health_check()
        # Should not contain traceback indicators
        assert "Traceback" not in result
        assert "File " not in result


# ---------------------------------------------------------------------------
# Tests: edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge cases for server type detection and health checks."""

    @pytest.mark.asyncio
    async def test_unexpected_server_type_value_returns_unknown(self, health_tools):
        """Server reports a type string we don't recognise."""
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 200
        resp.headers = {"x-lmstudio-server-type": "cluster-edition-3000"}
        resp.json.return_value = {"serverType": "cluster-edition-3000"}
        with patch("tools.health.httpx.get", return_value=resp):
            result = await health_tools.check_server_type()
        assert result == ServerType.UNKNOWN

    @pytest.mark.asyncio
    async def test_server_type_with_malformed_json(self, health_tools):
        """JSON decode error on diagnostics — falls back gracefully."""
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 200
        resp.headers = {}
        resp.json.side_effect = ValueError("not valid json")
        with patch("tools.health.httpx.get", return_value=resp):
            result = await health_tools.check_server_type()
        # Should not raise; must return a valid ServerType
        assert isinstance(result, ServerType)

    @pytest.mark.asyncio
    async def test_health_with_empty_models_list(self, health_tools):
        """No models loaded is valid — model_count should be 0."""
        with patch.object(health_tools, "check_server_type", new_callable=AsyncMock) as mock_type:
            mock_type.return_value = ServerType.HEADLESS
            health_tools.llm.health_check.return_value = True
            health_tools.llm.list_models.return_value = []
            result = await health_tools.check_server_health()
        assert result["model_count"] == 0
        assert result["loaded_models"] == []

    @pytest.mark.asyncio
    async def test_health_with_models_list_failure(self, health_tools):
        """If listing models fails, health check still returns valid structure."""
        with patch.object(health_tools, "check_server_type", new_callable=AsyncMock) as mock_type:
            mock_type.return_value = ServerType.GUI
            health_tools.llm.health_check.return_value = True
            health_tools.llm.list_models.side_effect = Exception("list failed")
            result = await health_tools.check_server_health()
        assert isinstance(result, dict)
        assert "server_type" in result
        assert "available" in result

    @pytest.mark.asyncio
    async def test_server_type_check_uses_configured_timeout(self, health_tools):
        """httpx.get call must pass the configured HEALTH_CHECK_TIMEOUT."""
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 200
        resp.headers = {}
        resp.json.return_value = {}
        with patch("tools.health.httpx.get", return_value=resp) as mock_get:
            await health_tools.check_server_type()
        # Verify timeout was passed in the call
        call_kwargs = mock_get.call_args[1] if mock_get.call_args else {}
        call_args_positional = mock_get.call_args[0] if mock_get.call_args else ()
        # timeout could be positional or keyword
        assert (
            "timeout" in call_kwargs
            or any("timeout" in str(a) for a in call_args_positional)
        ), "httpx.get must be called with a timeout parameter"


# ---------------------------------------------------------------------------
# Tests: MCP tool registration
# ---------------------------------------------------------------------------


class TestMCPToolRegistration:
    """check_server_type and check_server_health must be registered as MCP tools."""

    def test_register_health_tools_registers_check_server_type(self):
        """register_health_tools must register check_server_type."""
        mock_mcp = MagicMock()
        tool_decorator = MagicMock(return_value=lambda f: f)
        mock_mcp.tool.return_value = tool_decorator

        register_health_tools(mock_mcp)

        # Collect all function names passed through @mcp.tool()
        registered_names = [
            call_args[0][0].__name__
            for call_args in tool_decorator.call_args_list
            if call_args[0]
        ]
        assert "check_server_type" in registered_names, (
            "check_server_type must be registered as an MCP tool"
        )

    def test_register_health_tools_registers_check_server_health(self):
        """register_health_tools must register check_server_health."""
        mock_mcp = MagicMock()
        tool_decorator = MagicMock(return_value=lambda f: f)
        mock_mcp.tool.return_value = tool_decorator

        register_health_tools(mock_mcp)

        registered_names = [
            call_args[0][0].__name__
            for call_args in tool_decorator.call_args_list
            if call_args[0]
        ]
        assert "check_server_health" in registered_names, (
            "check_server_health must be registered as an MCP tool"
        )

    def test_existing_tools_still_registered(self):
        """Adding new tools must not remove existing health_check / list_models."""
        mock_mcp = MagicMock()
        tool_decorator = MagicMock(return_value=lambda f: f)
        mock_mcp.tool.return_value = tool_decorator

        register_health_tools(mock_mcp)

        registered_names = [
            call_args[0][0].__name__
            for call_args in tool_decorator.call_args_list
            if call_args[0]
        ]
        assert "health_check" in registered_names
        assert "list_models" in registered_names


# ---------------------------------------------------------------------------
# Tests: boundary — timeout at exact limit
# ---------------------------------------------------------------------------


class TestTimeoutBoundary:
    """Health check timeout boundary conditions."""

    @pytest.mark.asyncio
    async def test_timeout_exactly_at_limit_returns_unavailable(self, health_tools):
        """httpx.TimeoutException (not just connect) maps to UNAVAILABLE."""
        with patch("tools.health.httpx.get", side_effect=httpx.TimeoutException("timeout")):
            result = await health_tools.check_server_type()
        assert result == ServerType.UNAVAILABLE

    @pytest.mark.asyncio
    async def test_connect_timeout_returns_unavailable(self, health_tools):
        with patch("tools.health.httpx.get", side_effect=httpx.ConnectTimeout("connect timeout")):
            result = await health_tools.check_server_type()
        assert result == ServerType.UNAVAILABLE

    @pytest.mark.asyncio
    async def test_read_timeout_returns_unavailable(self, health_tools):
        with patch("tools.health.httpx.get", side_effect=httpx.ReadTimeout("read timeout")):
            result = await health_tools.check_server_type()
        assert result == ServerType.UNAVAILABLE


# ---------------------------------------------------------------------------
# Tests: constants presence
# ---------------------------------------------------------------------------


class TestConstants:
    """All new constants must exist in config.constants."""

    def test_health_check_timeout_is_positive_float(self):
        assert isinstance(HEALTH_CHECK_TIMEOUT, float)
        assert HEALTH_CHECK_TIMEOUT > 0

    def test_diagnostics_endpoint_is_string(self):
        assert isinstance(DIAGNOSTICS_ENDPOINT, str)
        assert DIAGNOSTICS_ENDPOINT.startswith("/")

    def test_system_status_endpoint_is_string(self):
        assert isinstance(SYSTEM_STATUS_ENDPOINT, str)
        assert SYSTEM_STATUS_ENDPOINT.startswith("/")

    def test_server_type_header_is_string(self):
        assert isinstance(SERVER_TYPE_HEADER, str)
        assert len(SERVER_TYPE_HEADER) > 0

    def test_llmster_process_name_is_string(self):
        assert isinstance(LLMSTER_PROCESS_NAME, str)
        assert len(LLMSTER_PROCESS_NAME) > 0

    def test_health_check_interval_is_positive(self):
        assert isinstance(HEALTH_CHECK_INTERVAL, (int, float))
        assert HEALTH_CHECK_INTERVAL > 0


# ---------------------------------------------------------------------------
# REFACTOR phase: additional tests to push tools/health.py coverage to 90%+
# Covers: list_models success, get_current_model, v1/models fallback branch,
#         and the inner async wrappers inside register_health_tools.
# ---------------------------------------------------------------------------


class TestListModelsExistingBehaviour:
    """Cover list_models success paths that were uncovered (lines 92, 107-114)."""

    @pytest.mark.asyncio
    async def test_list_models_returns_formatted_string(self, health_tools):
        """list_models with actual models returns a formatted list string."""
        health_tools.llm.list_models.return_value = ["model-a", "model-b"]
        result = await health_tools.list_models()
        assert "model-a" in result
        assert "model-b" in result

    @pytest.mark.asyncio
    async def test_list_models_empty_returns_no_models_message(self, health_tools):
        """list_models with empty list returns 'No models found'."""
        health_tools.llm.list_models.return_value = []
        result = await health_tools.list_models()
        assert "No models" in result

    @pytest.mark.asyncio
    async def test_health_check_success_returns_running_message(self, health_tools):
        """health_check() True path returns running message."""
        health_tools.llm.health_check.return_value = True
        result = await health_tools.health_check()
        assert "running" in result.lower()


class TestGetCurrentModel:
    """Cover get_current_model (lines 124-136)."""

    @pytest.mark.asyncio
    async def test_get_current_model_returns_model_name(self, health_tools):
        health_tools.llm.chat_completion.return_value = {"model": "qwen3-coder"}
        result = await health_tools.get_current_model()
        assert "qwen3-coder" in result

    @pytest.mark.asyncio
    async def test_get_current_model_unknown_when_missing_key(self, health_tools):
        """Response with no 'model' key returns Unknown."""
        health_tools.llm.chat_completion.return_value = {}
        result = await health_tools.get_current_model()
        assert "Unknown" in result

    @pytest.mark.asyncio
    async def test_get_current_model_error_returns_string(self, health_tools):
        health_tools.llm.chat_completion.side_effect = RuntimeError("no model loaded")
        result = await health_tools.get_current_model()
        assert isinstance(result, str)
        assert "Error" in result


class TestCheckServerTypeFallbackBranch:
    """Cover the /v1/models fallback in check_server_type (lines 182-193)."""

    @pytest.mark.asyncio
    async def test_returns_unknown_via_v1_models_fallback(self, health_tools):
        """Both diagnostic endpoints return 404 but /v1/models returns 200 -> UNKNOWN."""
        not_found = MagicMock(spec=httpx.Response)
        not_found.status_code = 404
        not_found.headers = {}
        not_found.json.return_value = {}

        models_ok = MagicMock(spec=httpx.Response)
        models_ok.status_code = 200
        models_ok.headers = {}
        models_ok.json.return_value = {"data": []}

        call_count = {"n": 0}

        def side_effect(url, **kwargs):
            call_count["n"] += 1
            if "/v1/models" in url and "api" not in url:
                return models_ok
            return not_found

        with patch("tools.health.httpx.get", side_effect=side_effect):
            result = await health_tools.check_server_type()
        assert result == ServerType.UNKNOWN

    @pytest.mark.asyncio
    async def test_returns_unavailable_when_all_endpoints_fail(self, health_tools):
        """All three endpoints fail -> UNAVAILABLE."""
        not_found = MagicMock(spec=httpx.Response)
        not_found.status_code = 404
        not_found.headers = {}
        not_found.json.return_value = {}

        with patch("tools.health.httpx.get", return_value=not_found):
            result = await health_tools.check_server_type()
        assert result == ServerType.UNAVAILABLE

    @pytest.mark.asyncio
    async def test_fallback_v1_models_exception_returns_unavailable(self, health_tools):
        """If /v1/models also throws, return UNAVAILABLE without crash."""
        not_found = MagicMock(spec=httpx.Response)
        not_found.status_code = 404
        not_found.headers = {}
        not_found.json.return_value = {}

        call_urls: list[str] = []

        def side_effect(url, **kwargs):
            call_urls.append(url)
            # Third call (v1/models) raises
            if len(call_urls) >= 3:
                raise httpx.ConnectError("no route")
            return not_found

        with patch("tools.health.httpx.get", side_effect=side_effect):
            result = await health_tools.check_server_type()
        assert result == ServerType.UNAVAILABLE


class TestRegisterHealthToolsWrappers:
    """Cover the inner async wrappers in register_health_tools (lines 275, 284, etc.)."""

    @pytest.mark.asyncio
    async def test_health_check_wrapper_delegates_to_tools(self):
        """The registered health_check wrapper calls HealthTools.health_check."""
        captured: dict = {}

        mock_mcp = MagicMock()

        def tool_decorator_factory():
            def decorator(fn):
                captured[fn.__name__] = fn
                return fn
            return decorator

        mock_mcp.tool.side_effect = tool_decorator_factory

        with patch("tools.health.LLMClient") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.health_check.return_value = True
            mock_cls.return_value = mock_llm
            register_health_tools(mock_mcp)

        assert "health_check" in captured
        result = await captured["health_check"]()
        assert "running" in result.lower()

    @pytest.mark.asyncio
    async def test_list_models_wrapper_delegates_to_tools(self):
        """The registered list_models wrapper calls HealthTools.list_models."""
        captured: dict = {}

        mock_mcp = MagicMock()

        def tool_decorator_factory():
            def decorator(fn):
                captured[fn.__name__] = fn
                return fn
            return decorator

        mock_mcp.tool.side_effect = tool_decorator_factory

        with patch("tools.health.LLMClient") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.list_models.return_value = ["model-x"]
            mock_cls.return_value = mock_llm
            register_health_tools(mock_mcp)

        assert "list_models" in captured
        result = await captured["list_models"]()
        assert "model-x" in result

    @pytest.mark.asyncio
    async def test_get_current_model_wrapper_delegates_to_tools(self):
        """The registered get_current_model wrapper calls HealthTools.get_current_model."""
        captured: dict = {}

        mock_mcp = MagicMock()

        def tool_decorator_factory():
            def decorator(fn):
                captured[fn.__name__] = fn
                return fn
            return decorator

        mock_mcp.tool.side_effect = tool_decorator_factory

        with patch("tools.health.LLMClient") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.chat_completion.return_value = {"model": "llama-3"}
            mock_cls.return_value = mock_llm
            register_health_tools(mock_mcp)

        assert "get_current_model" in captured
        result = await captured["get_current_model"]()
        assert "llama-3" in result

    @pytest.mark.asyncio
    async def test_check_server_type_wrapper_returns_string_value(self):
        """The registered check_server_type wrapper returns the enum .value string."""
        captured: dict = {}

        mock_mcp = MagicMock()

        def tool_decorator_factory():
            def decorator(fn):
                captured[fn.__name__] = fn
                return fn
            return decorator

        mock_mcp.tool.side_effect = tool_decorator_factory

        with patch("tools.health.LLMClient"):
            with patch("tools.health.httpx.get", side_effect=httpx.ConnectError("refused")):
                register_health_tools(mock_mcp)
                result = await captured["check_server_type"]()

        assert result == ServerType.UNAVAILABLE.value

    @pytest.mark.asyncio
    async def test_check_server_health_wrapper_returns_dict(self):
        """The registered check_server_health wrapper returns a dict."""
        captured: dict = {}

        mock_mcp = MagicMock()

        def tool_decorator_factory():
            def decorator(fn):
                captured[fn.__name__] = fn
                return fn
            return decorator

        mock_mcp.tool.side_effect = tool_decorator_factory

        with patch("tools.health.LLMClient"):
            with patch("tools.health.httpx.get", side_effect=httpx.ConnectError("refused")):
                register_health_tools(mock_mcp)
                result = await captured["check_server_health"]()

        assert isinstance(result, dict)
        assert result["available"] is False
