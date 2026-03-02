"""Thinking/reasoning sub-client."""

import logging
from typing import Any, Dict, Generator, List, Optional

from config.constants import (
    DEFAULT_LLM_TIMEOUT,
    DEFAULT_MAX_TOKENS,
    DEFAULT_THINKING_BUDGET_TOKENS,
    JIT_TTL_DEFAULT,
    MAX_THINKING_BUDGET_TOKENS,
    MIN_THINKING_BUDGET_TOKENS,
    STREAM_READ_TIMEOUT,
)
from llm.http_transport import HTTPTransport
from llm.thinking_parser import (
    estimate_thinking_tokens,
    parse_thinking_blocks,
    strip_thinking_blocks,
)

logger = logging.getLogger(__name__)


class ThinkingClient:
    """Handles thinking/reasoning completions."""

    def __init__(self, transport: HTTPTransport) -> None:
        self._transport = transport

    def thinking_completion(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        thinking_budget: Optional[int] = None,
        timeout: int = DEFAULT_LLM_TIMEOUT,
        response_format: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        *,
        _chat_fn=None,
    ) -> Dict[str, Any]:
        """Generate a chat completion with extended thinking support.

        Args:
            _chat_fn: Injectable chat_completion callable (used by Facade).
        """
        budget = thinking_budget if thinking_budget is not None else DEFAULT_THINKING_BUDGET_TOKENS

        if budget < MIN_THINKING_BUDGET_TOKENS or budget > MAX_THINKING_BUDGET_TOKENS:
            raise ValueError(
                f"thinking_budget must be between {MIN_THINKING_BUDGET_TOKENS} and "
                f"{MAX_THINKING_BUDGET_TOKENS}, got {budget}."
            )

        effective_max_tokens = budget + max_tokens

        target_model = model if model is not None else self._transport.model
        from llm.chat_client import ChatClient

        ChatClient(self._transport)._ensure_model_loaded(target_model, ttl=JIT_TTL_DEFAULT)

        # Use injected chat function or create a ChatClient
        if _chat_fn is None:
            from llm.chat_client import ChatClient as CC

            _chat_fn = CC(self._transport).chat_completion

        response = _chat_fn(
            messages=messages,
            temperature=temperature,
            max_tokens=effective_max_tokens,
            timeout=timeout,
            response_format=response_format,
            model=model,
        )

        assistant_text: str = ""
        try:
            assistant_text = response["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError):
            assistant_text = ""

        blocks = parse_thinking_blocks(assistant_text)
        thinking_token_total = sum(estimate_thinking_tokens(b.content) for b in blocks)

        response["thinking_blocks"] = [{"content": b.content} for b in blocks]
        response["thinking_tokens_estimated"] = thinking_token_total
        response["content_without_thinking"] = strip_thinking_blocks(assistant_text)

        return response

    def stream_thinking_completion(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        thinking_budget: Optional[int] = None,
        timeout: float = STREAM_READ_TIMEOUT,
        response_format: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        *,
        _stream_fn=None,
    ) -> Generator[Dict[str, Any], None, None]:
        """Stream a chat completion for a thinking-capable model.

        Args:
            _stream_fn: Injectable stream_chat_completion callable (used by Facade).
        """
        budget = thinking_budget if thinking_budget is not None else DEFAULT_THINKING_BUDGET_TOKENS

        if budget < MIN_THINKING_BUDGET_TOKENS or budget > MAX_THINKING_BUDGET_TOKENS:
            raise ValueError(
                f"thinking_budget must be between {MIN_THINKING_BUDGET_TOKENS} and "
                f"{MAX_THINKING_BUDGET_TOKENS}, got {budget}."
            )

        effective_max_tokens = budget + max_tokens

        if _stream_fn is None:
            from llm.streaming_client import StreamingClient

            _stream_fn = StreamingClient(self._transport).stream_chat_completion

        yield from _stream_fn(
            messages=messages,
            temperature=temperature,
            max_tokens=effective_max_tokens,
            timeout=timeout,
            response_format=response_format,
            model=model,
        )

    @staticmethod
    def is_thinking_capable(model_id: str) -> bool:
        """Check whether model_id is a thinking/reasoning model."""
        from model_registry.schemas import ModelMetadata

        return ModelMetadata._is_thinking_model(model_id)


__all__ = ["ThinkingClient"]
