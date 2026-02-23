#!/usr/bin/env python3
"""
Generic LLM client for LM Studio.

This module provides a generic interface to interact with ANY local LLM
running in LM Studio, not specific to any particular model.
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional, Union

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import get_config
from config.constants import (
    ANTHROPIC_MESSAGES_ENDPOINT,
    DEFAULT_ANTHROPIC_API_VERSION,
    DEFAULT_ANTHROPIC_MAX_TOKENS,
    DEFAULT_MAX_RETRIES,
    DEFAULT_THINKING_BUDGET_TOKENS,
    JIT_TTL_DEFAULT,
    JIT_TTL_EMBEDDING,
    MAX_THINKING_BUDGET_TOKENS,
    MIN_THINKING_BUDGET_TOKENS,
    STREAM_READ_TIMEOUT,
)
from llm.exceptions import (
    LLMConnectionError,
    LLMError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
)
from llm.sse_parser import parse_sse_stream
from llm.thinking_parser import (
    estimate_thinking_tokens,
    parse_thinking_blocks,
    strip_thinking_blocks,
)
from utils.error_handling import retry_with_backoff
from utils.lms_helper import LMSHelper

# Configure logging
logger = logging.getLogger(__name__)

# Default timeout for all LLM API calls
# Set to 58 seconds to accommodate slower models like Magistral (45-46s response time)
# Still safely under Claude Code's 60-second MCP timeout limit
# See: https://github.com/anthropics/claude-code/issues/7575
DEFAULT_LLM_TIMEOUT = 58

# Health check timeout - fast check for API availability
# Health checks should be quick, so we use a shorter timeout
HEALTH_CHECK_TIMEOUT = 5

# Default max rounds for AutonomousLLMClient
# For consistency with main autonomous tools (10000 rounds default)
DEFAULT_AUTONOMOUS_ROUNDS = 10000

# Default max tokens for LLM responses
# Based on Claude Code's 30K character limit for tool responses
# 8192 tokens ≈ 24K-32K chars, safely under the limit
DEFAULT_MAX_TOKENS = 8192

# Retry configuration for transient errors
# Based on investigation findings: HTTP 500 errors are rare and transient
# DEFAULT_MAX_RETRIES is imported from config.constants (value=3 = total attempts for retry_with_backoff)
DEFAULT_RETRY_DELAY = 1.0  # Initial delay in seconds
DEFAULT_RETRY_BACKOFF = 2.0  # Exponential backoff multiplier


def _handle_request_exception(e: Exception, operation: str = "LLM request") -> None:
    """Convert requests exceptions to our custom exception hierarchy.

    Args:
        e: The exception from requests library
        operation: Description of the operation that failed

    Raises:
        LLMTimeoutError: For timeout errors
        LLMConnectionError: For connection errors
        LLMRateLimitError: For rate limit errors (HTTP 429)
        LLMResponseError: For other HTTP errors
        LLMError: For other unexpected errors
    """
    if isinstance(e, requests.exceptions.Timeout):
        raise LLMTimeoutError(
            f"{operation} timed out. LM Studio may be overloaded or unresponsive.",
            original_exception=e
        )

    elif isinstance(e, requests.exceptions.ConnectionError):
        raise LLMConnectionError(
            f"{operation} failed: Could not connect to LM Studio. "
            f"Is LM Studio running?",
            original_exception=e
        )

    elif isinstance(e, requests.exceptions.HTTPError):
        # Note: Use "is not None" instead of truthy check because Response.__bool__
        # returns False for status_code >= 400, which would incorrectly give us None
        status_code = e.response.status_code if e.response is not None else None

        if status_code == 429:
            raise LLMRateLimitError(
                f"{operation} failed: Rate limit exceeded. Please try again later.",
                original_exception=e
            )
        elif status_code == 500:
            raise LLMResponseError(
                f"{operation} failed: LM Studio internal error (HTTP 500). "
                f"This is usually transient - retry may succeed.",
                original_exception=e
            )
        elif status_code == 404:
            raise LLMResponseError(
                f"{operation} failed: Endpoint not found (HTTP 404). "
                f"Check that LM Studio API is running correctly.",
                original_exception=e
            )
        else:
            raise LLMResponseError(
                f"{operation} failed: HTTP {status_code} error.",
                original_exception=e
            )

    elif isinstance(e, requests.exceptions.RequestException):
        raise LLMError(
            f"{operation} failed: {str(e)}",
            original_exception=e
        )

    else:
        # Unexpected error type
        raise LLMError(
            f"{operation} failed with unexpected error: {str(e)}",
            original_exception=e
        )


class LLMClient:
    """Generic client for interacting with local LLMs via LM Studio API.

    This client works with ANY model loaded in LM Studio.
    """

    def __init__(self, api_base: Optional[str] = None, model: Optional[str] = None):
        """Initialize LLM client.

        Args:
            api_base: Optional API base URL (uses config if None)
            model: Optional model name (uses currently loaded model if None)
        """
        config = get_config()
        self.api_base = api_base or config.lmstudio.api_base
        self.model = model or config.lmstudio.default_model

        # HTTP connection pooling for better performance
        self.session = requests.Session()
        adapter = HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=Retry(total=3, backoff_factor=0.3)
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

        # Native MCP support cache (OPP-16)
        self._native_mcp_supported: Optional[bool] = None
        self._native_mcp_checked_at: float = 0.0

    def _get_endpoint(self, path: str) -> str:
        """Get full URL for an endpoint.

        Args:
            path: API path

        Returns:
            Full URL
        """
        return f"{self.api_base}/{path.lstrip('/')}"

    def _ensure_model_loaded(
        self,
        target_model: Optional[str],
        ttl: int,
        label: str = "Model"
    ) -> None:
        """JIT model loading guard. Ensures model is loaded before API call.

        Args:
            target_model: Model identifier to load
            ttl: TTL in seconds for JIT loading
            label: Label for log messages (e.g., "Model", "Embedding model")

        Raises:
            LLMConnectionError: If model not loaded and loading fails
        """
        if not target_model or target_model == "default" or not LMSHelper.is_installed():
            return

        try:
            is_loaded = LMSHelper.is_model_loaded(target_model)

            if is_loaded is False:
                logger.warning(f"{label} '{target_model}' not loaded, attempting to load...")
                load_success = LMSHelper.ensure_model_loaded_with_verification(target_model, ttl=ttl)

                if not load_success:
                    raise LLMConnectionError(
                        f"{label} '{target_model}' is not loaded and failed to load automatically."
                    )

                logger.info(f"{label} '{target_model}' loaded successfully")
            elif is_loaded is True:
                logger.debug(f"{label} '{target_model}' already loaded")

        except LLMConnectionError:
            raise
        except Exception as e:
            logger.warning(f"Could not verify {label.lower()} load state: {e}. Proceeding anyway...")

    @retry_with_backoff(
        max_retries=DEFAULT_MAX_RETRIES,  # +1 for initial attempt = 3 total
        base_delay=DEFAULT_RETRY_DELAY,
        exceptions=(LLMResponseError, LLMTimeoutError)  # Only retry these
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
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a chat completion from the local LLM.

        Automatically retries on transient errors (HTTP 500, timeouts) with exponential backoff.
        Automatically ensures the model is loaded before making the request (if LMS CLI available).

        Args:
            messages: List of message dictionaries with 'role' and 'content'.
                      Content can be a string or a list (for multimodal messages with images).
            temperature: Controls randomness (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            tools: Optional list of tools in OpenAI format
            tool_choice: Tool selection strategy ('auto', 'none', or specific tool)
            timeout: Request timeout in seconds (default 58s, safely under Claude Code's 60s MCP timeout)
            response_format: Optional structured output format. Supported formats:
                - {"type": "json_object"} - Force valid JSON output
                - {"type": "json_schema", "json_schema": {"name": "...", "schema": {...}}}
                  Force output to conform to a specific JSON schema (LM Studio v0.3.32+)
            model: Model to use for this request. If None, uses the client's default model.
                   Use this to override the model for specific requests (e.g., different
                   models for different autonomous tasks).

        Returns:
            Response dictionary from LLM API

        Raises:
            LLMTimeoutError: If request times out
            LLMConnectionError: If cannot connect to LM Studio
            LLMRateLimitError: If rate limit exceeded
            LLMResponseError: If LM Studio returns an error
            LLMError: For other unexpected errors

        Example:
            # Basic chat completion
            response = client.chat_completion(messages=[{"role": "user", "content": "Hello"}])

            # With structured JSON output
            response = client.chat_completion(
                messages=[{"role": "user", "content": "List 3 colors"}],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "colors",
                        "schema": {
                            "type": "object",
                            "properties": {"colors": {"type": "array", "items": {"type": "string"}}},
                            "required": ["colors"]
                        }
                    }
                }
            )
        """
        # Determine which model to use (per-request model overrides default)
        target_model = model if model is not None else self.model

        self._ensure_model_loaded(target_model, ttl=JIT_TTL_DEFAULT)

        payload = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        # Only add model if not using default
        if target_model and target_model != "default":
            payload["model"] = target_model

        # Add tools if provided
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice

        # Add response_format for structured output (LM Studio v0.3.32+)
        if response_format is not None:
            payload["response_format"] = response_format

        try:
            response = self.session.post(
                self._get_endpoint("chat/completions"),
                json=payload,
                timeout=timeout
            )
            response.raise_for_status()
            return response.json()

        except Exception as e:
            _handle_request_exception(e, "Chat completion")

    @retry_with_backoff(
        max_retries=DEFAULT_MAX_RETRIES,
        base_delay=DEFAULT_RETRY_DELAY,
        exceptions=(LLMResponseError, LLMTimeoutError)
    )
    def text_completion(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        stop_sequences: Optional[List[str]] = None,
        model: Optional[str] = None,
        timeout: int = DEFAULT_LLM_TIMEOUT
    ) -> Dict[str, Any]:
        """Generate a raw text completion from the local LLM.

        Automatically retries on transient errors with exponential backoff.
        Automatically ensures the model is loaded before making the request (if LMS CLI available).

        Args:
            prompt: Text prompt to complete
            temperature: Controls randomness (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            stop_sequences: Optional list of stop sequences
            model: Model to use (default: uses self.model, required when multiple models loaded)
            timeout: Request timeout in seconds (default 58s, safely under Claude Code's 60s MCP timeout)

        Returns:
            Response dictionary from LLM API

        Raises:
            LLMTimeoutError: If request times out
            LLMConnectionError: If cannot connect to LM Studio
            LLMRateLimitError: If rate limit exceeded
            LLMResponseError: If LM Studio returns an error
            LLMError: For other unexpected errors
        """
        # Determine which model to use
        target_model = model or self.model

        self._ensure_model_loaded(target_model, ttl=JIT_TTL_DEFAULT)

        payload = {
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        # Add model parameter (required when multiple models loaded)
        payload["model"] = target_model

        # Add stop sequences if provided
        if stop_sequences:
            payload["stop"] = stop_sequences

        try:
            response = self.session.post(
                self._get_endpoint("completions"),
                json=payload,
                timeout=timeout
            )
            response.raise_for_status()
            return response.json()

        except Exception as e:
            _handle_request_exception(e, "Text completion")

    @staticmethod
    def convert_tools_to_responses_format(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert OpenAI tool format to LM Studio /v1/responses format.

        OpenAI format (for /v1/chat/completions):
            {"type": "function", "function": {"name": "...", "description": "...", ...}}

        LM Studio format (for /v1/responses):
            {"type": "function", "name": "...", "description": "...", ...}

        The key difference: LM Studio uses a flattened structure without the nested
        "function" object.

        Args:
            tools: List of tools in OpenAI format

        Returns:
            List of tools in LM Studio flattened format

        Example:
            >>> tools = [{"type": "function", "function": {"name": "test", "description": "..."}}]
            >>> LLMClient.convert_tools_to_responses_format(tools)
            [{"type": "function", "name": "test", "description": "..."}]
        """
        flattened = []
        for tool in tools:
            if tool.get("type") == "function" and "function" in tool:
                # Flatten: move function contents to top level
                flattened.append({
                    "type": "function",
                    **tool["function"]  # Spread name, description, parameters
                })
            else:
                # Already flat or different type
                flattened.append(tool)
        return flattened

    @staticmethod
    def convert_tools_to_anthropic_format(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert OpenAI tool format to Anthropic tool format.

        OpenAI: {"type": "function", "function": {"name": "...", "parameters": {...}}}
        Anthropic: {"name": "...", "description": "...", "input_schema": {...}}

        Args:
            tools: List of tools in OpenAI format

        Returns:
            List of tools in Anthropic format
        """
        converted = []
        for tool in tools:
            if tool.get("type") == "function" and "function" in tool:
                func = tool["function"]
                anthropic_tool = {
                    "name": func["name"],
                    "description": func.get("description", ""),
                }
                if "parameters" in func:
                    anthropic_tool["input_schema"] = func["parameters"]
                converted.append(anthropic_tool)
            else:
                converted.append(tool)
        return converted

    @staticmethod
    def extract_anthropic_tool_calls(response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract tool_use blocks from an Anthropic response.

        Args:
            response: Anthropic API response dict

        Returns:
            List of dicts with id, name, input for each tool call
        """
        calls = []
        for block in response.get("content", []):
            if block.get("type") == "tool_use":
                calls.append({
                    "id": block.get("id"),
                    "name": block.get("name"),
                    "input": block.get("input", {}),
                })
        return calls

    @staticmethod
    def build_anthropic_tool_result(
        tool_use_id: str,
        content: Union[str, dict, None],
        is_error: bool = False,
    ) -> Dict[str, Any]:
        """Build an Anthropic tool_result message.

        Args:
            tool_use_id: The id from the tool_use block
            content: Result content (str, dict auto-serialized, None -> "")
            is_error: Whether this is an error result

        Returns:
            Message dict with role=user and tool_result content block
        """
        if content is None:
            content_str = ""
        elif isinstance(content, dict):
            content_str = json.dumps(content)
        else:
            content_str = str(content)

        block: Dict[str, Any] = {
            "type": "tool_result",
            "tool_use_id": tool_use_id,
            "content": content_str,
        }
        if is_error:
            block["is_error"] = True

        return {"role": "user", "content": [block]}

    # TODO(OPP-10): Extract to anthropic_adapter.py

    @retry_with_backoff(
        max_retries=DEFAULT_MAX_RETRIES,
        base_delay=DEFAULT_RETRY_DELAY,
        exceptions=(LLMResponseError, LLMTimeoutError)
    )
    def generate_embeddings(
        self,
        text: Union[str, List[str]],
        model: Optional[str] = None,
        ttl: Optional[int] = None,
        timeout: int = DEFAULT_LLM_TIMEOUT
    ) -> Dict[str, Any]:
        """Generate vector embeddings for text.

        Automatically retries on transient errors with exponential backoff.
        Automatically ensures the model is loaded before making the request (if LMS CLI available).

        Args:
            text: Single text or list of texts to embed
            model: Optional specific model for embeddings
            ttl: Optional TTL in seconds for JIT model loading. Defaults to JIT_TTL_EMBEDDING.
            timeout: Request timeout in seconds (default 58s, safely under Claude Code's 60s MCP timeout)

        Returns:
            Response dictionary with embeddings data

        Raises:
            LLMTimeoutError: If request times out
            LLMConnectionError: If cannot connect to LM Studio
            LLMRateLimitError: If rate limit exceeded
            LLMResponseError: If LM Studio returns an error
            LLMError: For other unexpected errors
        """
        # Resolve target model
        target_model = model if model and model != "default" else self.model

        # Resolve TTL once for both the load guard and the payload
        resolved_ttl = ttl if ttl is not None else JIT_TTL_EMBEDDING

        self._ensure_model_loaded(target_model, ttl=resolved_ttl, label="Embedding model")

        payload = {"input": text}

        # Use specified model or default
        if model and model != "default":
            payload["model"] = model
        elif self.model and self.model != "default":
            payload["model"] = self.model

        # Always include TTL for JIT model loading
        payload["ttl"] = resolved_ttl

        try:
            response = self.session.post(
                self._get_endpoint("embeddings"),
                json=payload,
                timeout=timeout
            )
            response.raise_for_status()
            return response.json()

        except Exception as e:
            _handle_request_exception(e, "Generate embeddings")

    @retry_with_backoff(
        max_retries=DEFAULT_MAX_RETRIES,
        base_delay=DEFAULT_RETRY_DELAY,
        exceptions=(LLMResponseError, LLMTimeoutError)
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
    ) -> Dict[str, Any]:
        """Create a stateful response with optional function calling.

        This method uses LM Studio's /v1/responses API, which provides stateful
        conversations and supports function calling with a flattened tool format.

        Automatically retries on transient errors (HTTP 500, timeouts) with exponential backoff.

        Args:
            input_text: User input text
            tools: Optional list of tools in OpenAI format (will be converted to LM Studio format)
            previous_response_id: Optional ID from previous response for conversation continuity
            stream: Whether to stream response
            model: Optional specific model
            max_tokens: Maximum tokens to generate
            tool_choice: Tool selection strategy ('auto', 'required', 'none').
                        'required' forces the LLM to call a tool instead of responding with text.
            timeout: Request timeout in seconds (default 58s, safely under Claude Code's 60s MCP timeout)

        Returns:
            Response dictionary with response ID and output array

        Raises:
            LLMTimeoutError: If request times out
            LLMConnectionError: If cannot connect to LM Studio
            LLMRateLimitError: If rate limit exceeded
            LLMResponseError: If LM Studio returns an error
            LLMError: For other unexpected errors

        Example:
            >>> # First call with tools
            >>> response1 = client.create_response(
            ...     "Calculate 2+2",
            ...     tools=[{"type": "function", "function": {"name": "calc", ...}}]
            ... )
            >>> # Follow-up call using previous response
            >>> response2 = client.create_response(
            ...     "Now multiply that by 3",
            ...     tools=tools,
            ...     previous_response_id=response1["id"]
            ... )
        """
        # Resolve "default" to actual model name
        model_to_use = self.model if model == "default" or model is None else model

        # Resolve TTL once for both the load guard and the payload
        resolved_ttl = ttl if ttl is not None else JIT_TTL_DEFAULT

        self._ensure_model_loaded(model_to_use, ttl=resolved_ttl)

        payload = {
            "input": input_text,
            "model": model_to_use,
            # Note: stream=True passes through to LM Studio but response parsing
            # currently expects a complete JSON response, not SSE chunks.
            # Full streaming support would require an async iterator with SSE parsing.
            "stream": stream
        }

        # Add optional parameters
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        # Add previous response for conversation continuity
        if previous_response_id:
            payload["previous_response_id"] = previous_response_id

        # Add tools in LM Studio's flattened format
        if tools:
            payload["tools"] = self.convert_tools_to_responses_format(tools)
            # Add tool_choice if specified (default is 'auto')
            if tool_choice:
                payload["tool_choice"] = tool_choice

        # Add temperature if explicitly set (optional — not auto-added when None)
        if temperature is not None:
            payload["temperature"] = temperature

        # Add draft model for speculative decoding (GGUF only, LM Studio validates)
        if draft_model is not None:
            payload["draft_model"] = draft_model

        # Always include TTL for JIT model loading
        payload["ttl"] = resolved_ttl

        try:
            response = self.session.post(
                self._get_endpoint("responses"),
                json=payload,
                timeout=timeout
            )
            response.raise_for_status()
            return response.json()

        except Exception as e:
            _handle_request_exception(e, "Create response")

    def vision_completion(
        self,
        prompt: str,
        images: Union[str, List[str]],
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        detail: str = "auto",
        timeout: int = DEFAULT_LLM_TIMEOUT,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a vision completion from a multimodal LLM.

        Sends images along with a text prompt to vision-capable models.
        Automatically detects input format (file path, URL, or base64).

        Args:
            prompt: Text prompt describing what to do with the image(s)
            images: Single image or list of images. Each can be:
                - File path: "/path/to/image.png"
                - URL: "https://example.com/image.jpg"
                - Base64: "data:image/png;base64,..." or raw base64 string
            system_prompt: Optional system instructions
            temperature: Controls randomness (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            detail: Vision detail level ("auto", "low", "high")
            timeout: Request timeout in seconds
            model: Model to use for this request. If None, uses the client's default model.
                   Must be a vision-capable model (e.g., Qwen2-VL, LLaVA).

        Returns:
            Response dictionary from LLM API

        Raises:
            LLMTimeoutError: If request times out
            LLMConnectionError: If cannot connect to LM Studio
            LLMResponseError: If LM Studio returns an error or model doesn't support vision
            LLMError: For other unexpected errors
            ValueError: If image input is invalid

        Example:
            # Analyze a local image
            response = client.vision_completion(
                prompt="What's in this image?",
                images="/path/to/photo.jpg"
            )

            # Compare multiple images
            response = client.vision_completion(
                prompt="What are the differences between these images?",
                images=["image1.png", "image2.png"]
            )

            # Use URL
            response = client.vision_completion(
                prompt="Describe this image",
                images="https://example.com/image.jpg"
            )
        """
        from utils.image_utils import ImageInput, build_vision_content, process_image_input

        # Normalize to list
        if isinstance(images, str):
            images = [images]

        # Process all images
        processed_images: List[ImageInput] = []
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

        # Build the vision content
        content = build_vision_content(prompt, processed_images)

        # Build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": content})

        # Use the existing chat_completion method
        return self.chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            model=model
        )

    @retry_with_backoff(
        max_retries=DEFAULT_MAX_RETRIES,
        base_delay=DEFAULT_RETRY_DELAY,
        exceptions=(LLMResponseError, LLMTimeoutError)
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
    ) -> Dict[str, Any]:
        """Send a request to LM Studio's Anthropic-compatible /v1/messages endpoint.

        Args:
            messages: List of message dicts with 'role' and 'content' (NO system role).
            system: Top-level system prompt (Anthropic format: not in messages).
            max_tokens: Maximum tokens to generate (required by Anthropic protocol).
            temperature: Controls randomness (0.0 to 1.0).
            tools: Optional list of tools in Anthropic format.
            tool_choice: Optional tool selection strategy.
            model: Model override for this request.
            timeout: Request timeout in seconds.

        Returns:
            Response dictionary in Anthropic format.

        Raises:
            LLMTimeoutError: If request times out.
            LLMConnectionError: If cannot connect to LM Studio.
            LLMRateLimitError: If rate limit exceeded.
            LLMResponseError: If LM Studio returns an error.
            LLMError: For other unexpected errors.
        """
        target_model = model if model is not None else self.model

        self._ensure_model_loaded(target_model, ttl=JIT_TTL_DEFAULT)

        # Filter system messages from the messages array (Anthropic uses top-level system)
        filtered_messages = [m for m in messages if m.get("role") != "system"]

        payload = {
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

        headers = {
            "anthropic-version": DEFAULT_ANTHROPIC_API_VERSION,
        }

        try:
            response = self.session.post(
                self._get_endpoint(ANTHROPIC_MESSAGES_ENDPOINT),
                json=payload,
                headers=headers,
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json()

        except Exception as e:
            _handle_request_exception(e, "Anthropic messages")

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
    ):
        """Stream a chat completion from the local LLM via SSE.

        This is the streaming counterpart to ``chat_completion()``.  It opens
        a streaming connection to ``/v1/chat/completions`` and yields each
        parsed SSE event as a dict.  The ``[DONE]`` sentinel is consumed
        internally and never yielded.

        Args:
            messages: List of message dicts with ``role`` and ``content``.
            temperature: Controls randomness (0.0 to 1.0).
            max_tokens: Maximum tokens to generate.
            tools: Optional list of tools in OpenAI format.
            tool_choice: Tool selection strategy (``"auto"``, ``"none"``, etc.).
            timeout: Read timeout in seconds (default ``STREAM_READ_TIMEOUT``).
            response_format: Optional structured output format dict.
            model: Optional per-request model override.

        Yields:
            dict: Parsed SSE event payload, or ``{"error": "..."}`` on
            network/parse failures.

        Raises:
            LLMTimeoutError: If the connection times out.
            LLMConnectionError: If LM Studio cannot be reached.
            LLMRateLimitError: If HTTP 429 is returned.
            LLMResponseError: If LM Studio returns another HTTP error.
        """
        target_model = model if model is not None else self.model
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

        try:
            response = self.session.post(
                self._get_endpoint("chat/completions"),
                json=payload,
                stream=True,
                timeout=timeout,
            )
            response.raise_for_status()
        except Exception as e:
            _handle_request_exception(e, "Stream chat completion")

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
    ):
        """Stream a stateful response via SSE from ``/v1/responses``.

        This is the streaming counterpart to ``create_response()``.  It
        always sets ``stream=True`` in the payload and yields each parsed
        SSE event.

        Args:
            input_text: User input text.
            tools: Optional list of tools in OpenAI format.
            previous_response_id: Optional previous response ID for continuity.
            model: Optional per-request model override.
            max_tokens: Maximum tokens to generate.
            tool_choice: Tool selection strategy.
            temperature: Sampling temperature.
            ttl: JIT model loading TTL in seconds.
            timeout: Read timeout in seconds.
            draft_model: Optional draft model for speculative decoding.

        Yields:
            dict: Parsed SSE event payload, or ``{"error": "..."}`` on failure.

        Raises:
            LLMTimeoutError: If the connection times out.
            LLMConnectionError: If LM Studio cannot be reached.
            LLMRateLimitError: If HTTP 429 is returned.
            LLMResponseError: If LM Studio returns another HTTP error.
        """
        model_to_use = self.model if model == "default" or model is None else model
        resolved_ttl = ttl if ttl is not None else JIT_TTL_DEFAULT
        self._ensure_model_loaded(model_to_use, ttl=resolved_ttl)

        payload: Dict[str, Any] = {
            "input": input_text,
            "model": model_to_use,
            "stream": True,
            "ttl": resolved_ttl,
        }

        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        if previous_response_id:
            payload["previous_response_id"] = previous_response_id

        if tools:
            payload["tools"] = self.convert_tools_to_responses_format(tools)
            if tool_choice:
                payload["tool_choice"] = tool_choice

        if temperature is not None:
            payload["temperature"] = temperature

        if draft_model is not None:
            payload["draft_model"] = draft_model

        try:
            response = self.session.post(
                self._get_endpoint("responses"),
                json=payload,
                stream=True,
                timeout=timeout,
            )
            response.raise_for_status()
        except Exception as e:
            _handle_request_exception(e, "Stream create response")

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
    ):
        """Stream an Anthropic-compatible messages response via SSE.

        This is the streaming counterpart to ``anthropic_messages()``.  It
        targets ``/v1/messages`` and always sets ``stream=True``.  System-role
        messages are filtered from the array (same rule as the non-streaming
        method).

        Args:
            messages: List of message dicts (no ``system`` role).
            system: Top-level system prompt in Anthropic format.
            max_tokens: Maximum tokens to generate.
            temperature: Sampling temperature.
            tools: Optional tools in Anthropic format.
            tool_choice: Optional tool selection strategy dict.
            model: Optional per-request model override.
            timeout: Read timeout in seconds.

        Yields:
            dict: Parsed SSE event payload, or ``{"error": "..."}`` on failure.

        Raises:
            LLMTimeoutError: If the connection times out.
            LLMConnectionError: If LM Studio cannot be reached.
            LLMRateLimitError: If HTTP 429 is returned.
            LLMResponseError: If LM Studio returns another HTTP error.
        """
        target_model = model if model is not None else self.model
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

        headers = {
            "anthropic-version": DEFAULT_ANTHROPIC_API_VERSION,
        }

        try:
            response = self.session.post(
                self._get_endpoint(ANTHROPIC_MESSAGES_ENDPOINT),
                json=payload,
                headers=headers,
                stream=True,
                timeout=timeout,
            )
            response.raise_for_status()
        except Exception as e:
            _handle_request_exception(e, "Stream anthropic messages")

        yield from parse_sse_stream(response)

    def supports_native_mcp(self) -> bool:
        """Check if LM Studio supports native MCP in API requests.

        Probes GET /api/v1/server/info, checks for 'mcp' in capabilities.
        Result cached with TTL=300s.
        Returns False on any error (safe default).
        """
        now = time.monotonic()
        if self._native_mcp_supported is not None and (now - self._native_mcp_checked_at) < 300:
            return self._native_mcp_supported

        try:
            resp = self.session.get(
                self._get_endpoint("api/v1/server/info"),
                timeout=HEALTH_CHECK_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            supported = bool(data.get("capabilities", {}).get("mcp", False))
        except Exception:
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
    ) -> Dict[str, Any]:
        """Send chat completion with native MCP server configuration.

        Args:
            messages: Chat messages
            mcp_servers: List of MCP server configs [{name, transport, command, args, env}]
            model: Optional model override
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            timeout: Request timeout in seconds
            require_native: If True, raises LLMResponseError when native MCP unsupported

        Returns:
            Chat completion response dict

        Raises:
            ValueError: If mcp_servers is empty
            LLMResponseError: If native MCP not supported (when require_native=True)
            LLMTimeoutError: On timeout
        """
        if not mcp_servers:
            raise ValueError("mcp_servers must not be empty")

        if require_native and not self.supports_native_mcp():
            raise LLMResponseError("Native MCP not supported by this LM Studio version")

        target_model = model if model is not None else self.model

        payload = {
            "messages": messages,
            "mcp_servers": mcp_servers,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if target_model and target_model != "default":
            payload["model"] = target_model

        try:
            response = self.session.post(
                self._get_endpoint("v1/chat/completions"),
                json=payload,
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            _handle_request_exception(e, "Native MCP chat completion")

    def list_models(self) -> List[str]:
        """List all available models in LM Studio.

        Returns:
            List of model IDs

        Raises:
            LLMTimeoutError: If request times out
            LLMConnectionError: If cannot connect to LM Studio
            LLMResponseError: If LM Studio returns an error
            LLMError: For other unexpected errors
        """
        try:
            response = self.session.get(self._get_endpoint("models"))
            response.raise_for_status()
            models = response.json().get("data", [])
            return [model["id"] for model in models]

        except Exception as e:
            _handle_request_exception(e, "List models")

    def list_models_enriched(self) -> List[Dict[str, Any]]:
        """List all available models with enriched metadata from the native REST API.

        Tries the native /api/v1/models endpoint first (richer data), then falls back
        to the OpenAI-compatible /v1/models endpoint.

        Returns:
            List of dicts with model metadata (model_id, capabilities, context length, etc.)
        """
        base_url = self.api_base.rstrip("/")
        if base_url.endswith("/v1"):
            base_url = base_url[:-3]

        try:
            response = self.session.get(f"{base_url}/api/v1/models")
            response.raise_for_status()
            raw_list = response.json()
            if isinstance(raw_list, list) and raw_list:
                return [
                    {
                        "model_id": entry.get("key", ""),
                        "key": entry.get("key", ""),
                        "type": entry.get("type", "llm"),
                        "publisher": entry.get("publisher", ""),
                        "arch": entry.get("arch", ""),
                        "max_context_length": entry.get("max_context_length"),
                        "capabilities": entry.get("capabilities", {}),
                        "loaded_instances": entry.get("loaded_instances", []),
                        "size_bytes": entry.get("size_bytes"),
                        "quantization": entry.get("quantization"),
                        "compatibility_type": entry.get("compatibility_type"),
                    }
                    for entry in raw_list
                ]
        except Exception:
            logger.debug("Native /api/v1/models unavailable, falling back to /v1/models")

        # Fallback
        return [{"model_id": m} for m in self.list_models()]

    def get_model_info(self, model_id: Optional[str] = None) -> Dict[str, Any]:
        """Get basic model information from LM Studio.

        Note: LM Studio's OpenAI-compatible API only returns basic info (id, object, owned_by).
        It does NOT include max_context_length or token limits.

        Args:
            model_id: Model ID (uses currently loaded model if None)

        Returns:
            Dictionary with model information

        Raises:
            LLMTimeoutError: If request times out
            LLMConnectionError: If cannot connect to LM Studio
            LLMResponseError: If LM Studio returns an error
            LLMError: For other unexpected errors
            ValueError: If model not found
        """
        try:
            response = self.session.get(self._get_endpoint("models"))
            response.raise_for_status()
            models = response.json().get("data", [])

            # If no model_id specified, get the first available (currently loaded)
            if not model_id:
                if models:
                    return models[0]
                else:
                    raise ValueError("No models loaded in LM Studio")

            # Find specific model
            for model in models:
                if model.get("id") == model_id:
                    return model

            raise ValueError(f"Model '{model_id}' not found in LM Studio")

        except (ValueError, KeyError, IndexError):
            # Re-raise data validation errors as-is
            raise
        except Exception as e:
            _handle_request_exception(e, "Get model info")

    def get_default_max_tokens(self) -> int:
        """Get default max_tokens based on Claude Code's tool response limits.

        Claude Code truncates Bash tool output at 30,000 characters. Since MCP
        tool responses use the same handling, we set max_tokens to generate
        responses that stay safely under this limit.

        8192 tokens ≈ 24,000-32,000 characters (depending on tokenization),
        which provides comprehensive responses while staying under Claude Code's
        30,000 character truncation threshold.

        Note: LM Studio's API does not expose model's actual max_context_length,
        so this value is based on Claude Code's known limits rather than the
        loaded model's capabilities.

        Returns:
            8192 tokens (safe estimate for ~30K characters)
        """
        # Based on Claude Code's 30K character limit for tool responses
        # 8192 tokens ≈ 24K-32K chars, safely under the limit
        return 8192

    # ------------------------------------------------------------------
    # OPP-14: Extended Thinking
    # ------------------------------------------------------------------

    def thinking_completion(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        thinking_budget: Optional[int] = None,
        timeout: int = DEFAULT_LLM_TIMEOUT,
        response_format: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate a chat completion with extended thinking support.

        Like :meth:`chat_completion` but reserves a token budget for the
        model's chain-of-thought reasoning and enriches the returned dict with
        parsed thinking blocks.

        Unlike :meth:`chat_completion` this method has **no retry decorator**
        because thinking completions are expensive and retrying them
        automatically could waste significant compute.

        Args:
            messages: List of message dicts with ``role`` and ``content``.
            temperature: Controls randomness (0.0 to 1.0).
            max_tokens: Tokens to allocate for the *visible* response.  The
                actual ``max_tokens`` sent to the API will be
                ``thinking_budget + max_tokens`` so reasoning tokens do not
                eat into the response budget.
            thinking_budget: Tokens to reserve for reasoning.  Must be in
                ``[MIN_THINKING_BUDGET_TOKENS, MAX_THINKING_BUDGET_TOKENS]``.
                Defaults to :data:`~config.constants.DEFAULT_THINKING_BUDGET_TOKENS`
                when ``None``.
            timeout: Request timeout in seconds.
            response_format: Optional structured output format dict.
            model: Optional per-request model override.

        Returns:
            Standard chat completion response dict **plus** three extra keys:

            - ``thinking_blocks`` (list[dict]): Each item has at minimum a
              ``"content"`` key holding the raw thinking text.
            - ``thinking_tokens_estimated`` (int): Rough token count across
              all thinking blocks.
            - ``content_without_thinking`` (str): The assistant reply with all
              thinking blocks stripped and whitespace trimmed.

        Raises:
            ValueError: If *thinking_budget* is outside the allowed range.
            LLMTimeoutError: If request times out.
            LLMConnectionError: If cannot connect to LM Studio.
            LLMRateLimitError: If rate limit exceeded.
            LLMResponseError: If LM Studio returns an error.
            LLMError: For other unexpected errors.
        """
        # Resolve and validate budget
        budget = thinking_budget if thinking_budget is not None else DEFAULT_THINKING_BUDGET_TOKENS

        if budget < MIN_THINKING_BUDGET_TOKENS or budget > MAX_THINKING_BUDGET_TOKENS:
            raise ValueError(
                f"thinking_budget must be between {MIN_THINKING_BUDGET_TOKENS} and "
                f"{MAX_THINKING_BUDGET_TOKENS}, got {budget}."
            )

        # Bump max_tokens so the thinking budget doesn't consume response tokens
        effective_max_tokens = budget + max_tokens

        # Determine target model and JIT-load if needed
        target_model = model if model is not None else self.model
        self._ensure_model_loaded(target_model, ttl=JIT_TTL_DEFAULT)

        # Delegate to chat_completion (single attempt — no retry wrapper)
        response = self.chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=effective_max_tokens,
            timeout=timeout,
            response_format=response_format,
            model=model,
        )

        # Extract the assistant text from the response
        assistant_text: str = ""
        try:
            assistant_text = response["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError):
            assistant_text = ""

        # Parse thinking blocks and build enrichment
        blocks = parse_thinking_blocks(assistant_text)
        thinking_token_total = sum(
            estimate_thinking_tokens(b.content) for b in blocks
        )

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
    ):
        """Stream a chat completion for a thinking-capable model.

        Streaming counterpart to :meth:`thinking_completion`.  Validates the
        thinking budget, then delegates to :meth:`stream_chat_completion` and
        yields SSE chunks as-is.  Callers should accumulate the streamed text
        and call :func:`~llm.thinking_parser.parse_thinking_blocks` post-hoc
        to extract thinking blocks from the full response.

        Args:
            messages: List of message dicts with ``role`` and ``content``.
            temperature: Controls randomness (0.0 to 1.0).
            max_tokens: Tokens for the visible response portion.
            thinking_budget: Tokens reserved for reasoning.  Must be in
                ``[MIN_THINKING_BUDGET_TOKENS, MAX_THINKING_BUDGET_TOKENS]``.
                Defaults to :data:`~config.constants.DEFAULT_THINKING_BUDGET_TOKENS`.
            timeout: Read timeout in seconds.
            response_format: Optional structured output format dict.
            model: Optional per-request model override.

        Yields:
            dict: Parsed SSE event payload from :meth:`stream_chat_completion`.

        Raises:
            ValueError: If *thinking_budget* is outside the allowed range.
            LLMTimeoutError: If the connection times out.
            LLMConnectionError: If LM Studio cannot be reached.
            LLMRateLimitError: If HTTP 429 is returned.
            LLMResponseError: If LM Studio returns another HTTP error.
        """
        # Resolve and validate budget (eager — before any network call)
        budget = thinking_budget if thinking_budget is not None else DEFAULT_THINKING_BUDGET_TOKENS

        if budget < MIN_THINKING_BUDGET_TOKENS or budget > MAX_THINKING_BUDGET_TOKENS:
            raise ValueError(
                f"thinking_budget must be between {MIN_THINKING_BUDGET_TOKENS} and "
                f"{MAX_THINKING_BUDGET_TOKENS}, got {budget}."
            )

        effective_max_tokens = budget + max_tokens

        yield from self.stream_chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=effective_max_tokens,
            timeout=timeout,
            response_format=response_format,
            model=model,
        )

    @staticmethod
    def is_thinking_capable(model_id: str) -> bool:
        """Check whether *model_id* is a thinking / reasoning model.

        Delegates to :meth:`~model_registry.schemas.ModelMetadata._is_thinking_model`
        which matches against known reasoning-model name patterns (qwq, deepseek-r1,
        thinking, o1, r1, …).

        Args:
            model_id: Model identifier string to test.

        Returns:
            ``True`` if the model appears to be a thinking/reasoning model,
            ``False`` otherwise.

        Examples:
            >>> LLMClient.is_thinking_capable("qwen/qwq-32b")
            True
            >>> LLMClient.is_thinking_capable("qwen/qwen3-coder-30b")
            False
        """
        from model_registry.schemas import ModelMetadata

        return ModelMetadata._is_thinking_model(model_id)

    def health_check(self) -> bool:
        """Check if LM Studio API is accessible.

        Returns:
            True if API is accessible, False otherwise

        Note:
            This method returns False on any error instead of raising exceptions,
            making it safe to use for health checks without try/except blocks.
        """
        try:
            response = self.session.get(self._get_endpoint("models"), timeout=HEALTH_CHECK_TIMEOUT)
            return response.status_code == 200
        except Exception:
            # Catch all exceptions and return False - this is a health check
            return False


class AutonomousLLMClient:
    """LLM client with autonomous tool calling capabilities.

    This client manages the autonomous loop where the LLM can make
    multiple tool calls without manual intervention.
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        max_rounds: int = DEFAULT_AUTONOMOUS_ROUNDS
    ):
        """Initialize autonomous LLM client.

        Args:
            llm_client: Optional LLM client (creates default if None)
            max_rounds: Maximum autonomous rounds before stopping (default: 10000)
        """
        self.llm = llm_client or LLMClient()
        self.max_rounds = max_rounds

    async def autonomous_execution(
        self,
        task: str,
        tools: List[Dict[str, Any]],
        tool_executor,  # From mcp_client.executor
        system_prompt: Optional[str] = None
    ) -> str:
        """Execute task autonomously with tool calling.

        Args:
            task: Task description for the LLM
            tools: Available tools in OpenAI format
            tool_executor: Tool executor instance for executing tools
            system_prompt: Optional system instructions

        Returns:
            Final answer from LLM

        Raises:
            Exception: If autonomous execution fails
        """
        # Initialize messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": task})

        # Autonomous loop
        for round_num in range(self.max_rounds):
            # Call LLM with tools
            response = self.llm.chat_completion(
                messages=messages,
                tools=tools,
                tool_choice="auto"
            )

            message = response["choices"][0]["message"]

            # Check for tool calls
            if message.get("tool_calls"):
                # Add assistant message
                messages.append(message)

                # Execute each tool
                for tool_call in message["tool_calls"]:
                    tool_name = tool_call["function"]["name"]
                    tool_args = json.loads(tool_call["function"]["arguments"])

                    # Execute tool via MCP
                    result = await tool_executor.execute_tool(tool_name, tool_args)

                    # Add tool result to messages
                    from mcp_client.executor import ToolExecutor
                    content = ToolExecutor.extract_text_content(result)

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": content
                    })
            else:
                # LLM has final answer
                return message.get("content", "No content in response")

        return "Max rounds reached without final answer"


__all__ = [
    "LLMClient",
    "AutonomousLLMClient"
]
