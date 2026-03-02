"""Thinking/reasoning sub-client."""

import logging
from collections.abc import Generator
from typing import Any, Dict, List, Optional, Tuple

from config.constants import (
    DEFAULT_LLM_TIMEOUT,
    DEFAULT_MAX_TOKENS,
    DEFAULT_REASONING_EFFORT,
    JIT_TTL_DEFAULT,
    MAX_THINKING_BUDGET_TOKENS,
    MIN_THINKING_BUDGET_TOKENS,
    REASONING_EFFORT_TOKEN_MAP,
    STREAM_READ_TIMEOUT,
    VALID_REASONING_EFFORTS,
)
from llm.http_transport import HTTPTransport
from llm.jit_loader import ensure_model_loaded
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

    def _resolve_reasoning(
        self,
        reasoning: Optional[Dict[str, str]],
    ) -> Tuple[str, int]:
        """Resolve reasoning config to (effort_string, token_budget).

        Args:
            reasoning: Optional dict with 'effort' key ('low'|'medium'|'high').
                       If None, uses DEFAULT_REASONING_EFFORT.

        Returns:
            Tuple of (effort_string, token_budget_int).

        Raises:
            TypeError: If reasoning is not a dict.
            ValueError: If 'effort' key is missing or has an invalid value.
        """
        if reasoning is not None:
            if not isinstance(reasoning, dict):
                raise TypeError(
                    f"reasoning must be a dict, e.g. {{'effort': 'medium'}}, "
                    f"got {type(reasoning).__name__!r}"
                )
            effort = reasoning.get("effort")
            if effort is None:
                raise ValueError(
                    "reasoning dict must contain 'effort' key; "
                    f"valid efforts: {VALID_REASONING_EFFORTS}"
                )
            if effort not in VALID_REASONING_EFFORTS:
                raise ValueError(
                    f"reasoning effort must be one of {VALID_REASONING_EFFORTS}, "
                    f"got {effort!r}"
                )
            return effort, REASONING_EFFORT_TOKEN_MAP[effort]

        # Default: medium effort
        return DEFAULT_REASONING_EFFORT, REASONING_EFFORT_TOKEN_MAP[DEFAULT_REASONING_EFFORT]

    def thinking_completion(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        reasoning: Optional[Dict[str, str]] = None,
        timeout: int = DEFAULT_LLM_TIMEOUT,
        response_format: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        *,
        _chat_fn=None,
    ) -> Dict[str, Any]:
        """Generate a chat completion with extended thinking support.

        Args:
            reasoning: Optional dict e.g. {'effort': 'medium'} (OPP-21).
            _chat_fn: Injectable chat_completion callable (used by Facade).
        """
        _effort, budget = self._resolve_reasoning(reasoning)

        if budget < MIN_THINKING_BUDGET_TOKENS or budget > MAX_THINKING_BUDGET_TOKENS:
            raise ValueError(
                f"Resolved reasoning budget must be between {MIN_THINKING_BUDGET_TOKENS} and "
                f"{MAX_THINKING_BUDGET_TOKENS}, got {budget}."
            )

        effective_max_tokens = budget + max_tokens

        target_model = model if model is not None else self._transport.model
        ensure_model_loaded(target_model, ttl=JIT_TTL_DEFAULT)

        # Use injected chat function or create a ChatClient
        if _chat_fn is None:
            from llm.chat_client import ChatClient

            _chat_fn = ChatClient(self._transport).chat_completion

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
        reasoning: Optional[Dict[str, str]] = None,
        timeout: float = STREAM_READ_TIMEOUT,
        response_format: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        *,
        _stream_fn=None,
    ) -> Generator[Dict[str, Any], None, None]:
        """Stream a chat completion for a thinking-capable model.

        Args:
            reasoning: Optional dict e.g. {'effort': 'medium'} (OPP-21).
            _stream_fn: Injectable stream_chat_completion callable (used by Facade).
        """
        _effort, budget = self._resolve_reasoning(reasoning)

        if budget < MIN_THINKING_BUDGET_TOKENS or budget > MAX_THINKING_BUDGET_TOKENS:
            raise ValueError(
                f"Resolved reasoning budget must be between {MIN_THINKING_BUDGET_TOKENS} and "
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
