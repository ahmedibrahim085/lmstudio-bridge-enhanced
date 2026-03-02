"""Anthropic-compatible Anthropic messages sub-client."""

import logging
from typing import Any, Dict, List, Optional

from config.constants import (
    ANTHROPIC_MESSAGES_ENDPOINT,
    DEFAULT_ANTHROPIC_API_VERSION,
    DEFAULT_ANTHROPIC_MAX_TOKENS,
    DEFAULT_LLM_TIMEOUT,
    DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_BASE_DELAY,
    JIT_TTL_DEFAULT,
)
from llm.exceptions import LLMResponseError, LLMTimeoutError
from llm.http_transport import HTTPTransport, handle_request_exception
from utils.error_handling import retry_with_backoff

logger = logging.getLogger(__name__)


class AnthropicClient:
    """Handles Anthropic messages endpoint (Anthropic-compatible)."""

    def __init__(self, transport: HTTPTransport) -> None:
        self._transport = transport

    @retry_with_backoff(
        max_retries=DEFAULT_MAX_RETRIES,
        base_delay=DEFAULT_RETRY_BASE_DELAY,
        exceptions=(LLMResponseError, LLMTimeoutError),
    )
    def anthropic_messages(
        self,
        messages: List[Dict[str, Any]],
        system: str = "",
        max_tokens: int = DEFAULT_ANTHROPIC_MAX_TOKENS,
        temperature: float = 0.7,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        timeout: int = DEFAULT_LLM_TIMEOUT,
        min_p: Optional[float] = None,
        top_k: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Send a request to LM Studio's Anthropic-compatible Anthropic messages endpoint."""
        target_model = model if model is not None else self._transport.model

        from llm.chat_client import ChatClient

        ChatClient(self._transport)._ensure_model_loaded(target_model, ttl=JIT_TTL_DEFAULT)

        filtered_messages = [m for m in messages if m.get("role") != "system"]

        payload: Dict[str, Any] = {
            "messages": filtered_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if target_model and target_model != "default":
            payload["model"] = target_model
        if system:
            payload["system"] = system
        if tools:
            payload["tools"] = tools
        if tool_choice is not None:
            payload["tool_choice"] = tool_choice
        if min_p is not None:
            payload["min_p"] = min_p
        if top_k is not None:
            payload["top_k"] = top_k

        headers = {"anthropic-version": DEFAULT_ANTHROPIC_API_VERSION}

        try:
            response = self._transport.session.post(
                self._transport.get_endpoint(ANTHROPIC_MESSAGES_ENDPOINT),
                json=payload,
                headers=headers,
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            handle_request_exception(e, "Anthropic messages")


__all__ = ["AnthropicClient"]
