"""Native chat sub-client for LM Studio /api/v1/chat endpoint.

Streams responses using the native SSE format (19 event types) via
parse_native_sse_stream().
"""

import logging
from typing import Any, Dict, Generator, List, Optional

from config.constants import (
    DEFAULT_MAX_TOKENS,
    JIT_TTL_DEFAULT,
    NATIVE_CHAT_ENDPOINT,
    STREAM_READ_TIMEOUT,
)
from llm.http_transport import HTTPTransport, handle_request_exception
from llm.jit_loader import ensure_model_loaded
from llm.native_sse_parser import NativeSSEEvent, parse_native_sse_stream
from mcp_client.ephemeral import EphemeralIntegration, build_integrations_payload

logger = logging.getLogger(__name__)

__all__ = [
    "NativeChatClient",
]


class NativeChatClient:
    """Native /api/v1/chat streaming client for LM Studio.

    Uses the native SSE format with 19 event types (chat.start,
    message.delta, reasoning.delta, etc.) instead of the OpenAI-compat
    format that only has 3 event types.
    """

    def __init__(self, transport: HTTPTransport) -> None:
        self._transport = transport

    @staticmethod
    def _ensure_model_loaded(
        target_model: Optional[str],
        ttl: int,
    ) -> None:
        """JIT model loading guard."""
        ensure_model_loaded(target_model, ttl=ttl)

    def native_chat(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        stream: bool = True,
        timeout: float = STREAM_READ_TIMEOUT,
        integrations: Optional[List[EphemeralIntegration]] = None,
    ) -> Generator[NativeSSEEvent, None, None]:
        """Stream a native chat via /api/v1/chat.

        Args:
            messages: Chat messages in standard format.
            model: Model identifier. Uses transport.model if None.
            temperature: Sampling temperature.
            max_tokens: Maximum output tokens.
            stream: Always True for native streaming.
            timeout: Request timeout in seconds.
            integrations: Optional per-request MCP server integrations.

        Yields:
            NativeSSEEvent for each SSE block from the server.

        Raises:
            LLMConnectionError: Connection to LM Studio failed.
            LLMTimeoutError: Request timed out.
            LLMResponseError: Server returned an error status.
            ValueError: If any integration has an invalid configuration.
        """
        target_model = model if model is not None else self._transport.model
        self._ensure_model_loaded(target_model, ttl=JIT_TTL_DEFAULT)

        payload: Dict[str, Any] = {
            "messages": messages,
            "model": target_model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }

        if integrations:
            payload["integrations"] = build_integrations_payload(integrations)

        base_url = self._transport.api_base.rsplit("/v1", 1)[0]
        url = f"{base_url}{NATIVE_CHAT_ENDPOINT}"

        try:
            response = self._transport.session.post(
                url,
                json=payload,
                stream=True,
                timeout=timeout,
            )
            response.raise_for_status()
        except Exception as e:
            handle_request_exception(e, "Native chat completion")
            return  # unreachable — handle_request_exception is NoReturn

        try:
            yield from parse_native_sse_stream(response)
        finally:
            response.close()
