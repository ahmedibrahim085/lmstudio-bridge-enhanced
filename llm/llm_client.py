#!/usr/bin/env python3
"""Generic LLM client for LM Studio — thin Facade over sub-clients.

This module provides a backward-compatible interface to interact with ANY
local LLM running in LM Studio. All method implementations are delegated
to specialized sub-clients; this class exists only for API compatibility.
"""

import logging
import time
from collections.abc import Generator
from typing import Any, Dict, List, NoReturn, Optional, Union

import requests

from config.constants import (
    DEFAULT_ANTHROPIC_MAX_TOKENS,
    DEFAULT_LLM_TIMEOUT,
    DEFAULT_MAX_TOKENS,
    HEALTH_CHECK_TIMEOUT,
    JIT_TTL_EMBEDDING,
    STREAM_READ_TIMEOUT,
)
from llm.anthropic_client import AnthropicClient
from llm.chat_client import ChatClient
from llm.exceptions import LLMResponseError
from llm.format_adapter import FormatAdapter
from llm.http_transport import HTTPTransport, handle_request_exception
from llm.jit_loader import ensure_model_loaded
from llm.model_info_client import ModelInfoClient
from llm.native_chat_client import NativeChatClient
from llm.protocols import (
    AnthropicProvider,
    ChatProvider,
    ModelInfoProvider,
    NativeChatProvider,
    ResponseProvider,
    StreamProvider,
    ThinkingProvider,
)
from llm.responses_client import ResponsesClient
from llm.streaming_client import StreamingClient
from llm.thinking_client import ThinkingClient
from mcp_client.ephemeral import EphemeralIntegration

logger = logging.getLogger(__name__)


# Keep the module-level helper for backward compatibility — existing code may
# import it directly as ``from llm.llm_client import _handle_request_exception``.
def _handle_request_exception(e: Exception, operation: str = "LLM request") -> NoReturn:
    """Backward-compat shim — delegates to http_transport.handle_request_exception."""
    handle_request_exception(e, operation)


class LLMClient:
    """Backward-compatible facade over extracted sub-clients.

    All public methods delegate to the appropriate sub-client.
    Construction, session lifecycle, and context-manager support
    are preserved exactly as before.
    """

    def __init__(
        self,
        api_base: Optional[str] = None,
        model: Optional[str] = None,
        session: Optional["requests.Session"] = None,
    ):
        """Initialize LLM client.

        Args:
            api_base: Optional API base URL (uses config if None)
            model: Optional model name (uses currently loaded model if None)
            session: Optional pre-configured requests.Session (uses new session if None).
                     When provided, LLMClient does NOT own the session lifecycle.
        """
        self._transport = HTTPTransport(
            api_base=api_base, model=model, session=session,
        )

        # Expose transport attributes for backward compat
        self.api_base = self._transport.api_base
        self.model = self._transport.model
        self.session = self._transport.session
        self._owns_session = self._transport._owns_session

        # Sub-clients (typed via protocols for structural verification)
        self._chat: ChatProvider = ChatClient(self._transport)
        self._responses: ResponseProvider = ResponsesClient(self._transport)
        self._anthropic: AnthropicProvider = AnthropicClient(self._transport)
        self._streaming: StreamProvider = StreamingClient(self._transport)
        self._thinking: ThinkingProvider = ThinkingClient(self._transport)
        self._model_info: ModelInfoProvider = ModelInfoClient(self._transport)
        self._native_chat: NativeChatProvider = NativeChatClient(self._transport)

        # Native MCP support cache (OPP-16)
        self._native_mcp_supported: Optional[bool] = None
        self._native_mcp_checked_at: float = 0.0

    # ------------------------------------------------------------------
    # Resource management
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the HTTP session and release connection pool resources."""
        self._transport.close()
        self.session = self._transport.session  # sync after close (may be None)

    def __del__(self) -> None:
        """Ensure session is closed on garbage collection (safety net)."""
        try:
            self.close()
        except Exception:  # noqa: S110
            pass

    def __enter__(self) -> "LLMClient":
        """Support usage as a context manager."""
        return self

    def __exit__(
        self,
        exc_type: object,
        exc_val: object,
        exc_tb: object,
    ) -> bool:
        """Close session on context manager exit; never suppress exceptions."""
        self.close()
        return False

    # ------------------------------------------------------------------
    # Lazy init (backward compat with __new__() + manual attribute pattern)
    # ------------------------------------------------------------------

    _LAZY_ATTRS = frozenset({
        "_transport", "_chat", "_responses", "_anthropic",
        "_streaming", "_thinking", "_model_info", "_native_chat",
        "_native_mcp_supported", "_native_mcp_checked_at",
    })

    def __getattr__(self, name: str) -> object:
        """Bootstrap sub-clients lazily when created via __new__()."""
        if name in self._LAZY_ATTRS:
            self._init_sub_clients()
            return object.__getattribute__(self, name)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def __setattr__(self, name: str, value: object) -> None:
        """Sync session writes to transport for backward compat."""
        object.__setattr__(self, name, value)
        if name == "session":
            try:
                transport = object.__getattribute__(self, "_transport")
                transport.session = value
            except AttributeError:
                pass  # _transport not yet initialized

    def _init_sub_clients(self) -> None:
        """Create sub-clients from manually-set session/model/api_base attributes."""
        transport = HTTPTransport.__new__(HTTPTransport)
        transport.api_base = getattr(self, "api_base", "")
        transport.model = getattr(self, "model", "")
        transport.session = getattr(self, "session", None)
        transport._owns_session = False
        self._transport = transport
        self._chat = ChatClient(transport)
        self._responses = ResponsesClient(transport)
        self._anthropic = AnthropicClient(transport)
        self._streaming = StreamingClient(transport)
        self._thinking = ThinkingClient(transport)
        self._model_info = ModelInfoClient(transport)
        self._native_chat = NativeChatClient(transport)
        self._native_mcp_supported = None
        self._native_mcp_checked_at = 0.0

    # ------------------------------------------------------------------
    # Internal helpers (kept for backward compat with tests/consumers)
    # ------------------------------------------------------------------

    def _get_endpoint(self, path: str) -> str:
        """Get full URL for an endpoint."""
        return self._transport.get_endpoint(path)

    def _ensure_model_loaded(
        self,
        target_model: Optional[str],
        ttl: int,
        label: str = "Model",
    ) -> None:
        """JIT model loading guard."""
        ensure_model_loaded(target_model, ttl=ttl, label=label)

    # ------------------------------------------------------------------
    # Chat / Text completions
    # ------------------------------------------------------------------

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
        logprobs: bool = False,
        top_logprobs: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Generate a chat completion from the local LLM."""
        return self._chat.chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
            tool_choice=tool_choice,
            timeout=timeout,
            response_format=response_format,
            model=model,
            min_p=min_p,
            top_k=top_k,
            logprobs=logprobs,
            top_logprobs=top_logprobs,
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
        return self._chat.text_completion(
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            stop_sequences=stop_sequences,
            model=model,
            timeout=timeout,
            min_p=min_p,
            top_k=top_k,
        )

    # ------------------------------------------------------------------
    # Static format delegates (Feature Envy — delegate to FormatAdapter)
    # ------------------------------------------------------------------

    @staticmethod
    def convert_tools_to_responses_format(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert OpenAI tool format to LM Studio /v1/responses format."""
        return FormatAdapter.openai_tools_to_responses(tools)

    @staticmethod
    def convert_tools_to_anthropic_format(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert OpenAI tool format to Anthropic tool format."""
        return FormatAdapter.openai_tools_to_anthropic(tools)

    @staticmethod
    def extract_anthropic_tool_calls(response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract tool_use blocks from an Anthropic response."""
        return FormatAdapter.extract_anthropic_tool_calls(response)

    @staticmethod
    def build_anthropic_tool_result(
        tool_use_id: str,
        content: Union[str, dict, None],
        is_error: bool = False,
    ) -> Dict[str, Any]:
        """Build an Anthropic tool_result message."""
        return FormatAdapter.build_anthropic_tool_result(tool_use_id, content, is_error)

    # ------------------------------------------------------------------
    # Embeddings
    # ------------------------------------------------------------------

    def generate_embeddings(
        self,
        text: Union[str, List[str]],
        model: Optional[str] = None,
        ttl: Optional[int] = None,
        timeout: int = DEFAULT_LLM_TIMEOUT,
    ) -> Dict[str, Any]:
        """Generate vector embeddings for text."""
        target_model = model if model and model != "default" else self._transport.model
        resolved_ttl = ttl if ttl is not None else JIT_TTL_EMBEDDING

        self._ensure_model_loaded(target_model, ttl=resolved_ttl, label="Embedding model")

        payload: Dict[str, Any] = {"input": text}
        if model and model != "default":
            payload["model"] = model
        elif self._transport.model and self._transport.model != "default":
            payload["model"] = self._transport.model
        payload["ttl"] = resolved_ttl

        try:
            response = self._transport.session.post(
                self._transport.get_endpoint("embeddings"),
                json=payload,
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            handle_request_exception(e, "Generate embeddings")

    # ------------------------------------------------------------------
    # Responses API
    # ------------------------------------------------------------------

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
        return self._responses.create_response(
            input_text=input_text,
            tools=tools,
            previous_response_id=previous_response_id,
            stream=stream,
            model=model,
            max_tokens=max_tokens,
            tool_choice=tool_choice,
            temperature=temperature,
            ttl=ttl,
            timeout=timeout,
            draft_model=draft_model,
            min_p=min_p,
            top_k=top_k,
            logprobs=logprobs,
            top_logprobs=top_logprobs,
        )

    # ------------------------------------------------------------------
    # Vision
    # ------------------------------------------------------------------

    def vision_completion(
        self,
        prompt: str,
        images: Union[str, List[str]],
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        detail: str = "auto",
        timeout: int = DEFAULT_LLM_TIMEOUT,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate a vision completion from a multimodal LLM."""
        from utils.image_utils import build_vision_content, process_image_input

        if isinstance(images, str):
            images = [images]

        processed_images: List = []
        errors = []
        for i, img in enumerate(images):
            result = process_image_input(img, detail=detail)
            if result.is_valid:
                processed_images.append(result)
            else:
                errors.extend([f"Image {i+1}: {e}" for e in result.errors])

        if errors:
            raise ValueError(f"Invalid image input(s): {'; '.join(errors)}")
        if not processed_images:
            raise ValueError("No valid images provided")

        content = build_vision_content(prompt, processed_images)
        messages: List[Dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": content})

        return self.chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            model=model,
        )

    # ------------------------------------------------------------------
    # Anthropic
    # ------------------------------------------------------------------

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
        """Send a request to LM Studio's Anthropic-compatible messages endpoint."""
        return self._anthropic.anthropic_messages(
            messages=messages,
            system=system,
            max_tokens=max_tokens,
            temperature=temperature,
            tools=tools,
            tool_choice=tool_choice,
            model=model,
            timeout=timeout,
            min_p=min_p,
            top_k=top_k,
        )

    # ------------------------------------------------------------------
    # Streaming
    # ------------------------------------------------------------------

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
        """Stream a chat completion from the local LLM via SSE."""
        yield from self._streaming.stream_chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
            tool_choice=tool_choice,
            timeout=timeout,
            response_format=response_format,
            model=model,
            min_p=min_p,
            top_k=top_k,
        )

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
        """Stream a stateful response via SSE from /v1/responses."""
        yield from self._streaming.stream_create_response(
            input_text=input_text,
            tools=tools,
            previous_response_id=previous_response_id,
            model=model,
            max_tokens=max_tokens,
            tool_choice=tool_choice,
            temperature=temperature,
            ttl=ttl,
            timeout=timeout,
            draft_model=draft_model,
            min_p=min_p,
            top_k=top_k,
        )

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
        yield from self._streaming.stream_anthropic_messages(
            messages=messages,
            system=system,
            max_tokens=max_tokens,
            temperature=temperature,
            tools=tools,
            tool_choice=tool_choice,
            model=model,
            timeout=timeout,
            min_p=min_p,
            top_k=top_k,
        )

    # ------------------------------------------------------------------
    # Native Chat (OPP-19)
    # ------------------------------------------------------------------

    def native_chat(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        stream: bool = True,
        timeout: float = STREAM_READ_TIMEOUT,
        integrations: Optional[List[EphemeralIntegration]] = None,
    ) -> Generator[Any, None, None]:
        """Stream a native chat via LM Studio /api/v1/chat.

        Uses the native SSE format with 19 event types instead of
        OpenAI-compat format. Returns NativeSSEEvent objects.

        Args:
            messages: Chat messages.
            model: Model identifier. Uses default if None.
            temperature: Sampling temperature.
            max_tokens: Maximum output tokens.
            stream: Always True for native streaming.
            timeout: Request timeout.
            integrations: Optional per-request MCP server integrations.

        Yields:
            NativeSSEEvent for each server event.
        """
        yield from self._native_chat.native_chat(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream,
            timeout=timeout,
            integrations=integrations,
        )

    # ------------------------------------------------------------------
    # Native MCP
    # ------------------------------------------------------------------

    def supports_native_mcp(self) -> bool:
        """Check if LM Studio supports native MCP in API requests."""
        now = time.monotonic()
        if self._native_mcp_supported is not None and (now - self._native_mcp_checked_at) < 300:
            return self._native_mcp_supported

        try:
            base_url = self._transport.api_base.rsplit("/v1", 1)[0]
            resp = self._transport.session.get(
                f"{base_url}/api/v1/server/info",
                timeout=HEALTH_CHECK_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            supported = bool(data.get("capabilities", {}).get("mcp", False))
        except Exception:
            logger.warning("Native MCP support check failed", exc_info=True)
            supported = False

        self._native_mcp_supported = supported
        self._native_mcp_checked_at = now
        return supported

    def chat_completion_with_native_mcp(
        self,
        messages: List[Dict[str, Any]],
        mcp_servers: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        timeout: int = DEFAULT_LLM_TIMEOUT,
        require_native: bool = False,
        min_p: Optional[float] = None,
        top_k: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Send chat completion with native MCP server configuration."""
        if not mcp_servers:
            raise ValueError("mcp_servers must not be empty")

        if require_native and not self.supports_native_mcp():
            raise LLMResponseError("Native MCP not supported by this LM Studio version")

        target_model = model if model is not None else self._transport.model

        payload: Dict[str, Any] = {
            "messages": messages,
            "mcp_servers": mcp_servers,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if target_model and target_model != "default":
            payload["model"] = target_model
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
            handle_request_exception(e, "Native MCP chat completion")

    # ------------------------------------------------------------------
    # Model info
    # ------------------------------------------------------------------

    def list_models(self) -> List[str]:
        """List all available models in LM Studio."""
        return self._model_info.list_models()

    def list_models_enriched(self) -> List[Dict[str, Any]]:
        """List all available models with enriched metadata."""
        return self._model_info.list_models_enriched()

    def get_model_info(self, model_id: Optional[str] = None) -> Dict[str, Any]:
        """Get basic model information from LM Studio."""
        return self._model_info.get_model_info(model_id)

    def get_default_max_tokens(self) -> int:
        """Get default max_tokens based on Claude Code's tool response limits."""
        return ModelInfoClient.get_default_max_tokens()

    # ------------------------------------------------------------------
    # Thinking
    # ------------------------------------------------------------------

    def thinking_completion(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        reasoning: Optional[Dict[str, Any]] = None,
        timeout: int = DEFAULT_LLM_TIMEOUT,
        response_format: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate a chat completion with extended thinking support.

        Args:
            reasoning: Optional dict e.g. {'effort': 'medium'} (OPP-21).
        """
        return self._thinking.thinking_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            reasoning=reasoning,
            timeout=timeout,
            response_format=response_format,
            model=model,
            _chat_fn=self.chat_completion,
        )

    def stream_thinking_completion(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        reasoning: Optional[Dict[str, Any]] = None,
        timeout: float = STREAM_READ_TIMEOUT,
        response_format: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """Stream a chat completion for a thinking-capable model.

        Args:
            reasoning: Optional dict e.g. {'effort': 'medium'} (OPP-21).
        """
        yield from self._thinking.stream_thinking_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            reasoning=reasoning,
            timeout=timeout,
            response_format=response_format,
            model=model,
            _stream_fn=self.stream_chat_completion,
        )

    @staticmethod
    def is_thinking_capable(model_id: str) -> bool:
        """Check whether model_id is a thinking/reasoning model."""
        return ThinkingClient.is_thinking_capable(model_id)

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    def health_check(self) -> bool:
        """Check if LM Studio API is accessible."""
        return self._transport.health_check()


__all__ = [
    "LLMClient",
]
