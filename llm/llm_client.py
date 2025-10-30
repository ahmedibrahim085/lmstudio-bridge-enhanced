#!/usr/bin/env python3
"""
Generic LLM client for LM Studio.

This module provides a generic interface to interact with ANY local LLM
running in LM Studio, not specific to any particular model.
"""

import requests
import json
import time
import logging
from typing import List, Dict, Any, Optional, Union
from config import get_config

# Configure logging
logger = logging.getLogger(__name__)

# Default timeout for all LLM API calls
# Set to 55 seconds to stay safely under Claude Code's 60-second MCP timeout limit
# See: https://github.com/anthropics/claude-code/issues/7575
DEFAULT_LLM_TIMEOUT = 55

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
DEFAULT_MAX_RETRIES = 2  # Retry up to 2 times (3 total attempts)
DEFAULT_RETRY_DELAY = 1.0  # Initial delay in seconds
DEFAULT_RETRY_BACKOFF = 2.0  # Exponential backoff multiplier


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

    def _get_endpoint(self, path: str) -> str:
        """Get full URL for an endpoint.

        Args:
            path: API path

        Returns:
            Full URL
        """
        return f"{self.api_base}/{path.lstrip('/')}"

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto",
        timeout: int = DEFAULT_LLM_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: float = DEFAULT_RETRY_DELAY,
        retry_backoff: float = DEFAULT_RETRY_BACKOFF
    ) -> Dict[str, Any]:
        """Generate a chat completion from the local LLM.

        Includes automatic retry logic for transient HTTP 500 errors with exponential backoff.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            temperature: Controls randomness (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            tools: Optional list of tools in OpenAI format
            tool_choice: Tool selection strategy ('auto', 'none', or specific tool)
            timeout: Request timeout in seconds (default 55s, safely under Claude Code's 60s MCP timeout)
            max_retries: Maximum number of retries for transient errors (default 2)
            retry_delay: Initial delay between retries in seconds (default 1.0)
            retry_backoff: Exponential backoff multiplier (default 2.0)

        Returns:
            Response dictionary from LLM API

        Raises:
            requests.RequestException: If API call fails after all retries
        """
        payload = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        # Only add model if not using default
        if self.model and self.model != "default":
            payload["model"] = self.model

        # Add tools if provided
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice

        # Retry loop with exponential backoff
        last_exception = None
        current_delay = retry_delay

        for attempt in range(max_retries + 1):  # +1 for initial attempt
            try:
                response = requests.post(
                    self._get_endpoint("chat/completions"),
                    json=payload,
                    timeout=timeout
                )

                response.raise_for_status()

                # Log successful retry if this wasn't the first attempt
                if attempt > 0:
                    logger.info(f"Request succeeded on retry attempt {attempt}")

                return response.json()

            except requests.exceptions.HTTPError as e:
                # Only retry on HTTP 500 (Internal Server Error)
                if e.response.status_code == 500 and attempt < max_retries:
                    logger.warning(
                        f"HTTP 500 error on attempt {attempt + 1}/{max_retries + 1}. "
                        f"Retrying in {current_delay}s... "
                        f"(tools: {len(tools) if tools else 0})"
                    )
                    time.sleep(current_delay)
                    current_delay *= retry_backoff  # Exponential backoff
                    last_exception = e
                    continue
                else:
                    # Don't retry for other status codes or if max retries reached
                    raise

            except requests.exceptions.RequestException as e:
                # Don't retry for non-HTTP errors (connection, timeout, etc.)
                raise

        # If we get here, all retries failed
        logger.error(f"Request failed after {max_retries + 1} attempts")
        raise last_exception

    def text_completion(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        stop_sequences: Optional[List[str]] = None,
        timeout: int = DEFAULT_LLM_TIMEOUT
    ) -> Dict[str, Any]:
        """Generate a raw text completion from the local LLM.

        Args:
            prompt: Text prompt to complete
            temperature: Controls randomness (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            stop_sequences: Optional list of stop sequences
            timeout: Request timeout in seconds (default 55s, safely under Claude Code's 60s MCP timeout)

        Returns:
            Response dictionary from LLM API

        Raises:
            requests.RequestException: If API call fails
        """
        payload = {
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        # Add stop sequences if provided
        if stop_sequences:
            payload["stop"] = stop_sequences

        response = requests.post(
            self._get_endpoint("completions"),
            json=payload,
            timeout=timeout
        )

        response.raise_for_status()
        return response.json()

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

    def generate_embeddings(
        self,
        text: Union[str, List[str]],
        model: Optional[str] = None,
        timeout: int = DEFAULT_LLM_TIMEOUT
    ) -> Dict[str, Any]:
        """Generate vector embeddings for text.

        Args:
            text: Single text or list of texts to embed
            model: Optional specific model for embeddings
            timeout: Request timeout in seconds (default 55s, safely under Claude Code's 60s MCP timeout)

        Returns:
            Response dictionary with embeddings data

        Raises:
            requests.RequestException: If API call fails
        """
        payload = {"input": text}

        # Use specified model or default
        if model and model != "default":
            payload["model"] = model
        elif self.model and self.model != "default":
            payload["model"] = self.model

        response = requests.post(
            self._get_endpoint("embeddings"),
            json=payload,
            timeout=timeout
        )

        response.raise_for_status()
        return response.json()

    def create_response(
        self,
        input_text: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        previous_response_id: Optional[str] = None,
        stream: bool = False,
        model: Optional[str] = None,
        timeout: int = DEFAULT_LLM_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: float = DEFAULT_RETRY_DELAY,
        retry_backoff: float = DEFAULT_RETRY_BACKOFF
    ) -> Dict[str, Any]:
        """Create a stateful response with optional function calling.

        This method uses LM Studio's /v1/responses API, which provides stateful
        conversations and supports function calling with a flattened tool format.

        Includes automatic retry logic for transient HTTP 500 errors with exponential backoff.

        Args:
            input_text: User input text
            tools: Optional list of tools in OpenAI format (will be converted to LM Studio format)
            previous_response_id: Optional ID from previous response for conversation continuity
            stream: Whether to stream response
            model: Optional specific model
            timeout: Request timeout in seconds (default 55s, safely under Claude Code's 60s MCP timeout)
            max_retries: Maximum number of retries for transient errors (default 2)
            retry_delay: Initial delay between retries in seconds (default 1.0)
            retry_backoff: Exponential backoff multiplier (default 2.0)

        Returns:
            Response dictionary with response ID and output array

        Raises:
            requests.RequestException: If API call fails after all retries

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
        payload = {
            "input": input_text,
            "model": model or self.model,
            "stream": stream
        }

        # Add previous response for conversation continuity
        if previous_response_id:
            payload["previous_response_id"] = previous_response_id

        # Add tools in LM Studio's flattened format
        if tools:
            payload["tools"] = self.convert_tools_to_responses_format(tools)

        # Retry loop with exponential backoff
        last_exception = None
        current_delay = retry_delay

        for attempt in range(max_retries + 1):  # +1 for initial attempt
            try:
                response = requests.post(
                    self._get_endpoint("responses"),
                    json=payload,
                    timeout=timeout
                )

                response.raise_for_status()

                # Log successful retry if this wasn't the first attempt
                if attempt > 0:
                    logger.info(f"Request succeeded on retry attempt {attempt}")

                return response.json()

            except requests.exceptions.HTTPError as e:
                # Only retry on HTTP 500 (Internal Server Error)
                if e.response.status_code == 500 and attempt < max_retries:
                    logger.warning(
                        f"HTTP 500 error on attempt {attempt + 1}/{max_retries + 1}. "
                        f"Retrying in {current_delay}s... "
                        f"(tools: {len(tools) if tools else 0})"
                    )
                    time.sleep(current_delay)
                    current_delay *= retry_backoff  # Exponential backoff
                    last_exception = e
                    continue
                else:
                    # Don't retry for other status codes or if max retries reached
                    raise

            except requests.exceptions.RequestException as e:
                # Don't retry for non-HTTP errors (connection, timeout, etc.)
                raise

        # If we get here, all retries failed
        logger.error(f"Request failed after {max_retries + 1} attempts")
        raise last_exception

    def list_models(self) -> List[str]:
        """List all available models in LM Studio.

        Returns:
            List of model IDs

        Raises:
            requests.RequestException: If API call fails
        """
        response = requests.get(self._get_endpoint("models"))
        response.raise_for_status()

        models = response.json().get("data", [])
        return [model["id"] for model in models]

    def get_model_info(self, model_id: Optional[str] = None) -> Dict[str, Any]:
        """Get basic model information from LM Studio.

        Note: LM Studio's OpenAI-compatible API only returns basic info (id, object, owned_by).
        It does NOT include max_context_length or token limits.

        Args:
            model_id: Model ID (uses currently loaded model if None)

        Returns:
            Dictionary with model information

        Raises:
            requests.RequestException: If API call fails
            ValueError: If model not found
        """
        response = requests.get(self._get_endpoint("models"))
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

    def health_check(self) -> bool:
        """Check if LM Studio API is accessible.

        Returns:
            True if API is accessible

        Raises:
            requests.RequestException: If API is not accessible
        """
        try:
            response = requests.get(self._get_endpoint("models"), timeout=HEALTH_CHECK_TIMEOUT)
            return response.status_code == 200
        except requests.RequestException:
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
