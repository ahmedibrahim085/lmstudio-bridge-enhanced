#!/usr/bin/env python3
"""
Health check and system status tools for LM Studio.

OPP-18: Extended with server type detection (GUI vs headless llmster),
comprehensive health status, and graceful degradation when server is unavailable.
"""

import logging
from enum import Enum
from typing import Any, Optional

import httpx

from config.constants import (
    DEFAULT_LMSTUDIO_BASE_URL,
    DIAGNOSTICS_ENDPOINT,
    HEALTH_CHECK_TIMEOUT,
    LLMSTER_PROCESS_NAME,
    SERVER_TYPE_GUI,
    SERVER_TYPE_HEADER,
    SERVER_TYPE_HEADLESS,
    SYSTEM_STATUS_ENDPOINT,
)
from llm.llm_client import LLMClient

logger = logging.getLogger(__name__)


class ServerType(str, Enum):
    """LM Studio server variant.

    GUI      — desktop application with GUI running the server
    HEADLESS — llmster daemon (headless, no GUI)
    UNKNOWN  — server is reachable but type cannot be determined
    UNAVAILABLE — server is not reachable at all
    """

    GUI = "gui"
    HEADLESS = "headless"
    UNKNOWN = "unknown"
    UNAVAILABLE = "unavailable"


def _detect_type_from_response(resp: httpx.Response) -> Optional[ServerType]:
    """Parse server type from an HTTP response.

    Checks header first, then JSON body.  Returns None when the response
    gives no type information (caller should return UNKNOWN).
    """
    # 1. Header takes priority
    header_value = resp.headers.get(SERVER_TYPE_HEADER, "").lower().strip()
    if header_value == SERVER_TYPE_GUI:
        return ServerType.GUI
    if header_value == SERVER_TYPE_HEADLESS:
        return ServerType.HEADLESS

    # 2. Fall back to JSON body
    try:
        body = resp.json()
        body_type = str(body.get("serverType", "")).lower().strip()
        if body_type == SERVER_TYPE_GUI:
            return ServerType.GUI
        if body_type == SERVER_TYPE_HEADLESS:
            return ServerType.HEADLESS
    except (ValueError, AttributeError):
        pass

    return None


class HealthTools:
    """Tools for checking LM Studio health and status."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """Initialize health tools.

        Args:
            llm_client: Optional LLM client (creates default if None)
        """
        self.llm = llm_client or LLMClient()
        self._base_url = DEFAULT_LMSTUDIO_BASE_URL

    async def health_check(self) -> str:
        """Check if LM Studio API is accessible.

        Returns:
            A message indicating whether the LM Studio API is running.
        """
        try:
            if self.llm.health_check():
                return "LM Studio API is running and accessible."
            else:
                return "LM Studio API is not responding."
        except Exception as e:
            return f"Error connecting to LM Studio API: {str(e)}"

    async def list_models(self) -> str:
        """List all available models in LM Studio.

        Returns:
            A formatted list of available models.
        """
        try:
            models = self.llm.list_models()

            if not models:
                return "No models found in LM Studio."

            result = "Available models in LM Studio:\n\n"
            for model in models:
                result += f"- {model}\n"

            return result
        except Exception as e:
            return f"Error listing models: {str(e)}"

    async def get_current_model(self) -> str:
        """Get the currently loaded model in LM Studio.

        Returns:
            The name of the currently loaded model.
        """
        try:
            # LM Studio doesn't have a direct endpoint for currently loaded model
            # We'll check which model responds to a simple completion request
            response = self.llm.chat_completion(
                messages=[{"role": "system", "content": "What model are you?"}],
                max_tokens=10
            )

            # Extract model info from response
            model_info = response.get("model", "Unknown")
            return f"Currently loaded model: {model_info}"
        except Exception as e:
            return f"Error identifying current model: {str(e)}"

    async def check_server_type(self) -> ServerType:
        """Detect whether the server is GUI LM Studio, llmster (headless), or unknown.

        Detection strategy (in priority order):
        1. GET /api/v1/diagnostics — check x-lmstudio-server-type header, then JSON body
        2. GET /api/v1/system/status — same header/body checks as fallback
        3. GET /v1/models — if 200, server is up but type is UNKNOWN
        4. Any network error → UNAVAILABLE

        Returns:
            ServerType enum member.
        """
        endpoints = [
            f"{self._base_url}{DIAGNOSTICS_ENDPOINT}",
            f"{self._base_url}{SYSTEM_STATUS_ENDPOINT}",
        ]

        server_reachable = False

        for url in endpoints:
            try:
                resp = httpx.get(url, timeout=HEALTH_CHECK_TIMEOUT)
                if resp.status_code == 200:
                    server_reachable = True
                    detected = _detect_type_from_response(resp)
                    if detected is not None:
                        return detected
                    # 200 but no type info — keep trying other endpoints
            except (
                httpx.ConnectError,
                httpx.ConnectTimeout,
                httpx.ReadTimeout,
                httpx.ReadError,
                httpx.TimeoutException,
            ):
                # Network-level failure — server is not reachable
                return ServerType.UNAVAILABLE
            except Exception as exc:
                logger.debug("Unexpected error probing %s: %s", url, exc)
                return ServerType.UNAVAILABLE

        if server_reachable:
            return ServerType.UNKNOWN

        # Neither endpoint was reachable — try the OpenAI-compat models endpoint
        try:
            resp = httpx.get(
                f"{self._base_url}/v1/models",
                timeout=HEALTH_CHECK_TIMEOUT,
            )
            if resp.status_code == 200:
                return ServerType.UNKNOWN
        except Exception:
            pass

        return ServerType.UNAVAILABLE

    async def check_server_health(self) -> dict[str, Any]:
        """Return a comprehensive health report including server type and loaded models.

        The returned dict always has at minimum:
            available   (bool)   — whether the server responded
            server_type (str)    — ServerType value
            loaded_models (list) — model names (empty list if unavailable/error)
            model_count (int)    — len(loaded_models)
            suggestions (list)   — actionable strings when server is unavailable

        Additional keys are present when the server is available:
            message (str) — human-readable summary

        This method NEVER raises — it always returns a dict.
        """
        try:
            server_type = await self.check_server_type()
        except Exception as exc:
            logger.error("check_server_type raised unexpectedly: %s", exc)
            server_type = ServerType.UNAVAILABLE

        if server_type is ServerType.UNAVAILABLE:
            return {
                "available": False,
                "server_type": server_type.value,
                "loaded_models": [],
                "model_count": 0,
                "suggestions": [
                    (
                        f"Start {LLMSTER_PROCESS_NAME} (headless daemon): "
                        f"llmster --port 1234"
                    ),
                    "Or launch the LM Studio desktop application and enable the server.",
                    "Verify the server is listening: curl http://localhost:1234/v1/models",
                ],
            }

        # Server is reachable — gather model info
        loaded_models: list[str] = []
        try:
            raw = self.llm.list_models()
            if isinstance(raw, list):
                loaded_models = raw
        except Exception as exc:
            logger.warning("Could not list models during health check: %s", exc)

        return {
            "available": True,
            "server_type": server_type.value,
            "loaded_models": loaded_models,
            "model_count": len(loaded_models),
            "message": (
                f"LM Studio ({server_type.value}) is running. "
                f"{len(loaded_models)} model(s) loaded."
            ),
            "suggestions": [],
        }


# ---------------------------------------------------------------------------
# Register tools with FastMCP
# ---------------------------------------------------------------------------


def register_health_tools(mcp, llm_client: Optional[LLMClient] = None) -> None:
    """Register health tools with FastMCP server.

    Args:
        mcp: FastMCP server instance
        llm_client: Optional LLM client
    """
    tools = HealthTools(llm_client)

    @mcp.tool()
    async def health_check() -> str:
        """Check if LM Studio API is accessible.

        Returns:
            A message indicating whether the LM Studio API is running.
        """
        return await tools.health_check()

    @mcp.tool()
    async def list_models() -> str:
        """List all available models in LM Studio.

        Returns:
            A formatted list of available models.
        """
        return await tools.list_models()

    @mcp.tool()
    async def get_current_model() -> str:
        """Get the currently loaded model in LM Studio.

        Returns:
            The name of the currently loaded model.
        """
        return await tools.get_current_model()

    @mcp.tool()
    async def check_server_type() -> str:
        """Detect whether LM Studio is running as GUI, headless (llmster), or unavailable.

        Returns:
            One of: "gui", "headless", "unknown", "unavailable"
        """
        result = await tools.check_server_type()
        return result.value

    @mcp.tool()
    async def check_server_health() -> dict[str, Any]:
        """Return comprehensive LM Studio health status.

        Includes server type, loaded models, and actionable suggestions
        when the server is unavailable.

        Returns:
            Dict with keys: available, server_type, loaded_models,
            model_count, suggestions, and (when available) message.
        """
        return await tools.check_server_health()


__all__ = [
    "HealthTools",
    "ServerType",
    "register_health_tools",
]
