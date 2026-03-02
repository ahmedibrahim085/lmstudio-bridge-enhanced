"""Stateful /v1/responses sub-client."""

import logging
from typing import Any, Dict, List, Optional

from config.constants import (
    DEFAULT_LLM_TIMEOUT,
    DEFAULT_MAX_RETRIES,
    DEFAULT_MODEL_KEYWORD,
    DEFAULT_RETRY_BASE_DELAY,
    JIT_TTL_DEFAULT,
    is_model_sentinel,
)
from llm.exceptions import LLMResponseError, LLMTimeoutError
from llm.format_adapter import FormatAdapter
from llm.http_transport import HTTPTransport, handle_request_exception
from llm.jit_loader import ensure_model_loaded
from utils.error_handling import retry_with_backoff

logger = logging.getLogger(__name__)


class ResponsesClient:
    """Handles /v1/responses endpoint."""

    def __init__(self, transport: HTTPTransport) -> None:
        self._transport = transport

    @retry_with_backoff(
        max_retries=DEFAULT_MAX_RETRIES,
        base_delay=DEFAULT_RETRY_BASE_DELAY,
        exceptions=(LLMResponseError, LLMTimeoutError),
    )
    def create_response(
        self,
        input_text: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        previous_response_id: Optional[str] = None,
        stream: bool = False,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        tool_choice: Optional[str] = None,
        temperature: Optional[float] = None,
        ttl: Optional[int] = None,
        timeout: int = DEFAULT_LLM_TIMEOUT,
        draft_model: Optional[str] = None,
        min_p: Optional[float] = None,
        top_k: Optional[int] = None,
        logprobs: bool = False,
        top_logprobs: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Create a stateful response with optional function calling."""
        model_to_use = (
            self._transport.model
            if model == DEFAULT_MODEL_KEYWORD or model is None
            else model
        )
        resolved_ttl = ttl if ttl is not None else JIT_TTL_DEFAULT

        ensure_model_loaded(model_to_use, ttl=resolved_ttl)

        payload: Dict[str, Any] = {
            "input": input_text,
            "stream": stream,
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
        payload["ttl"] = resolved_ttl
        if min_p is not None:
            payload["min_p"] = min_p
        if top_k is not None:
            payload["top_k"] = top_k
        if logprobs:
            payload["logprobs"] = True
            if top_logprobs is not None:
                payload["top_logprobs"] = top_logprobs

        try:
            response = self._transport.session.post(
                self._transport.get_endpoint("responses"),
                json=payload,
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            handle_request_exception(e, "Create response")


__all__ = ["ResponsesClient"]
