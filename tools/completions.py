#!/usr/bin/env python3
"""
Completion tools for LM Studio (chat and text completions).
"""

from typing import Optional, List
from llm.llm_client import LLMClient
import json


class CompletionTools:
    """Tools for generating completions from local LLMs."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """Initialize completion tools.

        Args:
            llm_client: Optional LLM client (creates default if None)
        """
        self.llm = llm_client or LLMClient()

    async def chat_completion(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> str:
        """Generate a completion from the current LM Studio model.

        Args:
            prompt: The user's prompt to send to the model
            system_prompt: Optional system instructions for the model
            temperature: Controls randomness (0.0 to 1.0)
            max_tokens: Maximum number of tokens to generate

        Returns:
            The model's response to the prompt
        """
        try:
            messages = []

            # Add system message if provided
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            # Add user message
            messages.append({"role": "user", "content": prompt})

            response = self.llm.chat_completion(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )

            # Extract the assistant's message
            choices = response.get("choices", [])
            if not choices:
                return "Error: No response generated"

            message = choices[0].get("message", {})
            content = message.get("content", "")

            if not content:
                return "Error: Empty response from model"

            return content
        except Exception as e:
            return f"Error generating completion: {str(e)}"

    async def text_completion(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        stop_sequences: Optional[List[str]] = None
    ) -> str:
        """Generate a raw text completion (non-chat format) from LM Studio.

        This endpoint is simpler and faster than chat completions for single-turn tasks
        like code completion, text continuation, or simple Q&A.

        Args:
            prompt: The text prompt to complete
            temperature: Controls randomness (0.0 to 2.0, default 0.7)
            max_tokens: Maximum number of tokens to generate (default 1024)
            stop_sequences: Optional list of sequences where generation will stop

        Returns:
            The completed text from the model
        """
        try:
            response = self.llm.text_completion(
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                stop_sequences=stop_sequences
            )

            # Extract the completion text
            choices = response.get("choices", [])
            if not choices:
                return "Error: No completion generated"

            text = choices[0].get("text", "")

            if not text:
                return "Error: Empty completion from model"

            return text
        except Exception as e:
            return f"Error generating text completion: {str(e)}"

    async def create_response(
        self,
        input_text: str,
        previous_response_id: Optional[str] = None,
        stream: bool = False,
        model: Optional[str] = None
    ) -> str:
        """Create a response using LM Studio's stateful /v1/responses endpoint.

        This endpoint provides stateful conversations where you can reference previous
        responses without managing message history manually.

        Args:
            input_text: The user's input text
            previous_response_id: Optional ID from a previous response to continue conversation
            stream: Whether to stream the response (default False)
            model: Model to use (default: uses currently loaded model)

        Returns:
            JSON string with response including ID for future reference
        """
        try:
            response = self.llm.create_response(
                input_text=input_text,
                previous_response_id=previous_response_id,
                stream=stream,
                model=model
            )

            # Return as JSON string
            return json.dumps(response)

        except Exception as e:
            error_response = {
                "error": f"Failed to create response: {str(e)}"
            }
            return json.dumps(error_response)


# Register tools with FastMCP
def register_completion_tools(mcp, llm_client: Optional[LLMClient] = None):
    """Register completion tools with FastMCP server.

    Args:
        mcp: FastMCP server instance
        llm_client: Optional LLM client
    """
    tools = CompletionTools(llm_client)

    @mcp.tool()
    async def chat_completion(
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> str:
        """Generate a completion from the current LM Studio model.

        Args:
            prompt: The user's prompt to send to the model
            system_prompt: Optional system instructions for the model
            temperature: Controls randomness (0.0 to 1.0)
            max_tokens: Maximum number of tokens to generate

        Returns:
            The model's response to the prompt
        """
        return await tools.chat_completion(prompt, system_prompt, temperature, max_tokens)

    @mcp.tool()
    async def text_completion(
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        stop_sequences: Optional[List[str]] = None
    ) -> str:
        """Generate a raw text completion (non-chat format) from LM Studio.

        This endpoint is simpler and faster than chat completions for single-turn tasks
        like code completion, text continuation, or simple Q&A.

        Args:
            prompt: The text prompt to complete
            temperature: Controls randomness (0.0 to 2.0, default 0.7)
            max_tokens: Maximum number of tokens to generate (default 1024)
            stop_sequences: Optional list of sequences where generation will stop

        Returns:
            The completed text from the model
        """
        return await tools.text_completion(prompt, temperature, max_tokens, stop_sequences)

    @mcp.tool()
    async def create_response(
        input_text: str,
        previous_response_id: Optional[str] = None,
        stream: bool = False,
        model: Optional[str] = None
    ) -> str:
        """Create a response using LM Studio's stateful /v1/responses endpoint.

        This endpoint provides stateful conversations where you can reference previous
        responses without managing message history manually.

        Args:
            input_text: The user's input text
            previous_response_id: Optional ID from a previous response to continue conversation
            stream: Whether to stream the response (default False)
            model: Model to use (default: uses currently loaded model)

        Returns:
            JSON string with response including ID for future reference
        """
        return await tools.create_response(
            input_text, previous_response_id, stream, model
        )


__all__ = [
    "CompletionTools",
    "register_completion_tools"
]
