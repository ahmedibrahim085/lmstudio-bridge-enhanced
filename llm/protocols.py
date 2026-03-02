"""Protocol definitions for LLMClient sub-client contracts.

Each protocol defines the public interface for one responsibility domain.
Sub-clients implement these protocols; the Facade delegates to them.
"""

from typing import Any, Dict, Generator, List, Optional, Protocol, Union, runtime_checkable


@runtime_checkable
class ChatProvider(Protocol):
    """Contract for chat and text completion methods."""

    def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = ...,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto",
        timeout: int = ...,
        response_format: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        min_p: Optional[float] = None,
        top_k: Optional[int] = None,
    ) -> Dict[str, Any]: ...

    def text_completion(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = ...,
        stop_sequences: Optional[List[str]] = None,
        model: Optional[str] = None,
        timeout: int = ...,
        min_p: Optional[float] = None,
        top_k: Optional[int] = None,
    ) -> Dict[str, Any]: ...


@runtime_checkable
class ResponseProvider(Protocol):
    """Contract for stateful /v1/responses API."""

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
        timeout: int = ...,
        draft_model: Optional[str] = None,
        min_p: Optional[float] = None,
        top_k: Optional[int] = None,
    ) -> Dict[str, Any]: ...


@runtime_checkable
class AnthropicProvider(Protocol):
    """Contract for Anthropic-compatible messages API."""

    def anthropic_messages(
        self,
        messages: List[Dict[str, Any]],
        system: str = "",
        max_tokens: int = ...,
        temperature: float = 0.7,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        timeout: int = ...,
        min_p: Optional[float] = None,
        top_k: Optional[int] = None,
    ) -> Dict[str, Any]: ...


@runtime_checkable
class StreamProvider(Protocol):
    """Contract for all streaming methods."""

    def stream_chat_completion(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = ...,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto",
        timeout: float = ...,
        response_format: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        min_p: Optional[float] = None,
        top_k: Optional[int] = None,
    ) -> Generator[Dict[str, Any], None, None]: ...

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
        timeout: float = ...,
        draft_model: Optional[str] = None,
        min_p: Optional[float] = None,
        top_k: Optional[int] = None,
    ) -> Generator[Dict[str, Any], None, None]: ...

    def stream_anthropic_messages(
        self,
        messages: List[Dict[str, Any]],
        system: str = "",
        max_tokens: int = ...,
        temperature: float = 0.7,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        timeout: float = ...,
        min_p: Optional[float] = None,
        top_k: Optional[int] = None,
    ) -> Generator[Dict[str, Any], None, None]: ...


@runtime_checkable
class ModelInfoProvider(Protocol):
    """Contract for model listing and info methods."""

    def list_models(self) -> List[str]: ...
    def list_models_enriched(self) -> List[Dict[str, Any]]: ...
    def get_model_info(self, model_id: Optional[str] = None) -> Dict[str, Any]: ...


@runtime_checkable
class ThinkingProvider(Protocol):
    """Contract for thinking/reasoning methods."""

    def thinking_completion(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = ...,
        thinking_budget: Optional[int] = None,
        timeout: int = ...,
        response_format: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
    ) -> Dict[str, Any]: ...

    def stream_thinking_completion(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = ...,
        thinking_budget: Optional[int] = None,
        timeout: float = ...,
        response_format: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
    ) -> Generator[Dict[str, Any], None, None]: ...

    @staticmethod
    def is_thinking_capable(model_id: str) -> bool: ...


__all__ = [
    "ChatProvider",
    "ResponseProvider",
    "AnthropicProvider",
    "StreamProvider",
    "ModelInfoProvider",
    "ThinkingProvider",
]
