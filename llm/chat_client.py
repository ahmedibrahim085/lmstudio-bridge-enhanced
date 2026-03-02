"""Chat and text completion sub-client."""

import logging
from typing import Any, Dict, List, Optional

from config.constants import (
    DEFAULT_LLM_TIMEOUT,
    DEFAULT_MAX_RETRIES,
    DEFAULT_MAX_TOKENS,
    DEFAULT_RETRY_BASE_DELAY,
    JIT_TTL_DEFAULT,
)
from llm.exceptions import LLMResponseError, LLMTimeoutError
from llm.http_transport import HTTPTransport, handle_request_exception
from llm.jit_loader import ensure_model_loaded
from utils.error_handling import retry_with_backoff

logger = logging.getLogger(__name__)


class ChatClient:
    """Handles /v1/chat/completions and /v1/completions endpoints."""

    def __init__(self, transport: HTTPTransport) -> None:
        self._transport = transport

    @staticmethod
    def _ensure_model_loaded(
        target_model: Optional[str],
        ttl: int,
        label: str = "Model",
    ) -> None:
        """JIT model loading guard — delegates to llm.jit_loader."""
        ensure_model_loaded(target_model, ttl=ttl, label=label)

    @retry_with_backoff(
        max_retries=DEFAULT_MAX_RETRIES,
        base_delay=DEFAULT_RETRY_BASE_DELAY,
        exceptions=(LLMResponseError, LLMTimeoutError),
    )
    def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto",
        timeout: int = DEFAULT_LLM_TIMEOUT,
        response_format: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        min_p: Optional[float] = None,
        top_k: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Generate a chat completion from the local LLM."""
        target_model = model if model is not None else self._transport.model
        self._ensure_model_loaded(target_model, ttl=JIT_TTL_DEFAULT)

        payload: Dict[str, Any] = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
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
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            handle_request_exception(e, "Chat completion")

    @retry_with_backoff(
        max_retries=DEFAULT_MAX_RETRIES,
        base_delay=DEFAULT_RETRY_BASE_DELAY,
        exceptions=(LLMResponseError, LLMTimeoutError),
    )
    def text_completion(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        stop_sequences: Optional[List[str]] = None,
        model: Optional[str] = None,
        timeout: int = DEFAULT_LLM_TIMEOUT,
        min_p: Optional[float] = None,
        top_k: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Generate a raw text completion from the local LLM."""
        target_model = model or self._transport.model
        self._ensure_model_loaded(target_model, ttl=JIT_TTL_DEFAULT)

        payload: Dict[str, Any] = {
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "model": target_model,
        }
        if stop_sequences:
            payload["stop"] = stop_sequences
        if min_p is not None:
            payload["min_p"] = min_p
        if top_k is not None:
            payload["top_k"] = top_k

        try:
            response = self._transport.session.post(
                self._transport.get_endpoint("completions"),
                json=payload,
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            handle_request_exception(e, "Text completion")


__all__ = ["ChatClient"]
