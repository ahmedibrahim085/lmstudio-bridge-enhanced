"""Streaming sub-client for all SSE-based endpoints."""

import logging
from collections.abc import Generator
from typing import Any, Dict, List, Optional

from config.constants import (
    ANTHROPIC_MESSAGES_ENDPOINT,
    DEFAULT_ANTHROPIC_API_VERSION,
    DEFAULT_ANTHROPIC_MAX_TOKENS,
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL_KEYWORD,
    JIT_TTL_DEFAULT,
    STREAM_READ_TIMEOUT,
    is_model_sentinel,
)
from llm.format_adapter import FormatAdapter
from llm.http_transport import HTTPTransport, handle_request_exception
from llm.jit_loader import ensure_model_loaded
from llm.sse_parser import parse_sse_stream

logger = logging.getLogger(__name__)


class StreamingClient:
    """Handles all streaming (SSE) endpoints."""

    def __init__(self, transport: HTTPTransport) -> None:
        self._transport = transport

    @staticmethod
    def _ensure_model_loaded(target_model: Optional[str], ttl: int) -> None:
        ensure_model_loaded(target_model, ttl=ttl)

    def stream_chat_completion(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto",
        timeout: float = STREAM_READ_TIMEOUT,
        response_format: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        min_p: Optional[float] = None,
        top_k: Optional[int] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """Stream a chat completion via SSE."""
        target_model = model if model is not None else self._transport.model
        self._ensure_model_loaded(target_model, ttl=JIT_TTL_DEFAULT)

        payload: Dict[str, Any] = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if target_model and target_model != "default":
            payload["model"] = target_model
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice
        if response_format is not None:
            payload["response_format"] = response_format
        if min_p is not None:
            payload["min_p"] = min_p
        if top_k is not None:
            payload["top_k"] = top_k

        try:
            response = self._transport.session.post(
                self._transport.get_endpoint("chat/completions"),
                json=payload,
                stream=True,
                timeout=timeout,
            )
            response.raise_for_status()
        except Exception as e:
            handle_request_exception(e, "Stream chat completion")

        yield from parse_sse_stream(response)

    def stream_create_response(
        self,
        input_text: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        previous_response_id: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        tool_choice: Optional[str] = None,
        temperature: Optional[float] = None,
        ttl: Optional[int] = None,
        timeout: float = STREAM_READ_TIMEOUT,
        draft_model: Optional[str] = None,
        min_p: Optional[float] = None,
        top_k: Optional[int] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """Stream a stateful response via SSE."""
        model_to_use = (
            self._transport.model
            if model == DEFAULT_MODEL_KEYWORD or model is None
            else model
        )
        resolved_ttl = ttl if ttl is not None else JIT_TTL_DEFAULT
        self._ensure_model_loaded(model_to_use, ttl=resolved_ttl)

        payload: Dict[str, Any] = {
            "input": input_text,
            "stream": True,
            "ttl": resolved_ttl,
        }
        if not is_model_sentinel(model_to_use):
            payload["model"] = model_to_use
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if previous_response_id:
            payload["previous_response_id"] = previous_response_id
        if tools:
            payload["tools"] = FormatAdapter.openai_tools_to_responses(tools)
            if tool_choice:
                payload["tool_choice"] = tool_choice
        if temperature is not None:
            payload["temperature"] = temperature
        if draft_model is not None:
            payload["draft_model"] = draft_model
        if min_p is not None:
            payload["min_p"] = min_p
        if top_k is not None:
            payload["top_k"] = top_k

        try:
            response = self._transport.session.post(
                self._transport.get_endpoint("responses"),
                json=payload,
                stream=True,
                timeout=timeout,
            )
            response.raise_for_status()
        except Exception as e:
            handle_request_exception(e, "Stream create response")

        yield from parse_sse_stream(response)

    def stream_anthropic_messages(
        self,
        messages: List[Dict[str, Any]],
        system: str = "",
        max_tokens: int = DEFAULT_ANTHROPIC_MAX_TOKENS,
        temperature: float = 0.7,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        timeout: float = STREAM_READ_TIMEOUT,
        min_p: Optional[float] = None,
        top_k: Optional[int] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """Stream an Anthropic-compatible messages response via SSE."""
        target_model = model if model is not None else self._transport.model
        self._ensure_model_loaded(target_model, ttl=JIT_TTL_DEFAULT)

        filtered_messages = [m for m in messages if m.get("role") != "system"]

        payload: Dict[str, Any] = {
            "messages": filtered_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
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
                stream=True,
                timeout=timeout,
            )
            response.raise_for_status()
        except Exception as e:
            handle_request_exception(e, "Stream anthropic messages")

        yield from parse_sse_stream(response)


__all__ = ["StreamingClient"]
