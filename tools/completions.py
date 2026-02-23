#!/usr/bin/env python3
"""
Completion tools for LM Studio (chat and text completions).
"""

from typing import Optional, List, Dict, Any
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
        max_tokens: int = 1024,
        response_format: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate a completion from the current LM Studio model.

        Args:
            prompt: The user's prompt to send to the model
            system_prompt: Optional system instructions for the model
            temperature: Controls randomness (0.0 to 1.0)
            max_tokens: Maximum number of tokens to generate
            response_format: Optional structured output format (LM Studio v0.3.32+)
                - {"type": "json_object"} for valid JSON output
                - {"type": "json_schema", "json_schema": {...}} for schema-conforming JSON

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
                max_tokens=max_tokens,
                response_format=response_format
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

    async def anthropic_messages(
        self,
        messages: str,
        system: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.7,
        model: Optional[str] = None,
    ) -> str:
        """Send a message using Anthropic format via LM Studio.

        Args:
            messages: JSON string of message array
            system: Top-level system prompt
            max_tokens: Maximum tokens (required by Anthropic protocol)
            temperature: Controls randomness
            model: Optional model override

        Returns:
            JSON string with Anthropic-format response
        """
        try:
            parsed_messages = json.loads(messages) if isinstance(messages, str) else messages
            result = self.llm.anthropic_messages(
                messages=parsed_messages,
                system=system,
                max_tokens=max_tokens,
                temperature=temperature,
                model=model,
            )
            return json.dumps(result, indent=2)

        except Exception as e:
            error_response = {
                "error": f"Failed to send Anthropic message: {str(e)}"
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
        max_tokens: int = 1024,
        response_format: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Delegate a task to the local LLM running in LM Studio.

        ⚠️ CRITICAL: This tool calls ANOTHER LLM (not you!). Only use for task DELEGATION.

        ## When to Use This Tool
        ✅ Use for:
        - Bulk content generation (e.g., "generate 50 product descriptions")
        - Programmatic text/code generation for external systems
        - Offloading repetitive sub-tasks to local models
        - Template-based content creation at scale
        - Delegating computational work to specialized local models

        ❌ Do NOT use for:
        - Answering user questions → Answer directly from your knowledge!
        - Conversational responses → You should respond, not another LLM!
        - Simple Q&A → Inefficient to delegate what you can answer
        - Explaining concepts → You have this knowledge already
        - Identity questions → Never ask another LLM "who are you?"

        ## Switching Models (Multi-Model Support)
        **To delegate a task to a DIFFERENT model:**

        The current implementation uses the DEFAULT model configured in LM Studio.

        ⚠️ **Model switching via `model` parameter is NOT currently supported** in this basic tool.

        **For multi-model workflows**, use the autonomous tools instead:
        ```python
        # Use a specific model for a task
        autonomous_with_mcp(
            mcp_name="filesystem",
            task="your task",
            model="qwen/qwen3-coder-30b"  # Specify model here
        )
        ```

        ❌ **Do NOT use `lms_*` tools for model switching**:
        ```python
        # WRONG - This is for model LIFECYCLE, not task delegation
        lms_ensure_model_loaded("gemma-3")  # ❌ WRONG
        chat_completion("generate photo")    # Still uses default model

        # CORRECT - Use autonomous tools with model parameter
        autonomous_with_mcp(
            mcp_name="filesystem",
            task="generate photo description",
            model="gemma-3"  # ✅ CORRECT
        )
        ```

        ## Multimedia & Content Types 🎨🖼️📹
        **You can request ANY content type** through this tool:
        - ✅ Text, code, markdown (always supported)
        - ✅ Images (PNG, JPG, SVG) - if receiving LLM is multimodal
        - ✅ Audio/Video analysis - if receiving LLM supports it
        - ✅ Documents (PDF, Word) - if receiving LLM can process
        - ✅ Data files (JSON, CSV, XML)

        **Content Handling**: The receiving LLM in LM Studio decides:
        - ✅ Accept & process if it has the capability (e.g., GPT-4V can analyze images)
        - ❌ Reject with error if unsupported (e.g., text-only models cannot process images)

        This tool is content-agnostic - it forwards your request without restriction.
        The receiving model's capabilities determine what's supported.

        ## Examples
        ✅ CORRECT:
        User: "Generate 10 creative coffee shop names"
        Action: chat_completion(prompt="Generate 10 creative coffee shop names")
        Reason: Bulk generation task - appropriate delegation

        ✅ CORRECT:
        User: "Analyze sentiment in this user review dataset"
        Action: chat_completion(prompt="Analyze sentiment: [review data]")
        Reason: Batch processing task - good delegation

        ❌ INCORRECT:
        User: "Hello, who are you?"
        Wrong: chat_completion(prompt="Hello, who are you?")
        Correct: Answer directly - "I am a local language model running via LM Studio..."
        Reason: This is conversation! You should answer yourself, not ask another LLM

        ❌ INCORRECT:
        User: "What is Python?"
        Wrong: chat_completion(prompt="What is Python?")
        Correct: Answer directly - "Python is a high-level programming language..."
        Reason: You have this knowledge! No need to delegate simple Q&A

        ❌ INCORRECT:
        User: "Explain how recursion works"
        Wrong: chat_completion(prompt="Explain recursion")
        Correct: Answer directly with your own explanation
        Reason: Explaining concepts is YOUR job, not another LLM's

        ## Structured Output (JSON Schema) - LM Studio v0.3.32+
        Force the LLM to output valid JSON conforming to a schema:
        ```python
        chat_completion(
            prompt="List 3 programming languages",
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "languages",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "languages": {"type": "array", "items": {"type": "string"}}
                        },
                        "required": ["languages"]
                    }
                }
            }
        )
        # Returns: {"languages": ["Python", "JavaScript", "Rust"]}
        ```

        ⚠️ Not all models support structured output. Models < 7B may produce invalid JSON.

        Args:
            prompt: The specific task to delegate to the local LLM
            system_prompt: Optional system instructions for the local LLM
            temperature: Controls randomness (0.0 = deterministic, 1.0 = creative)
            max_tokens: Maximum response length
            response_format: Optional structured output format:
                - {"type": "json_object"} - Force valid JSON output
                - {"type": "json_schema", "json_schema": {...}} - Force schema-conforming JSON

        Returns:
            The local LLM's response to the delegated task

        Note: This creates a SECOND LLM call. Only use when delegation is truly beneficial.
        """
        return await tools.chat_completion(prompt, system_prompt, temperature, max_tokens, response_format)

    @mcp.tool()
    async def text_completion(
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        stop_sequences: Optional[List[str]] = None
    ) -> str:
        """
        Generate raw text/code completion from local LLM (non-chat format).

        ⚠️ IMPORTANT: This delegates to ANOTHER LLM for programmatic generation.

        ## When to Use This Tool
        ✅ Use for:
        - Code completion for external systems (e.g., IDE integrations)
        - Text continuation for programmatic use
        - Template filling at scale
        - Format-specific generation (completing JSON, YAML, etc.)
        - Single-turn generation tasks without conversation context

        ❌ Do NOT use for:
        - Conversational responses → Use chat_completion or answer directly
        - Questions requiring reasoning → Use chat_completion with system prompt
        - Tasks you can complete yourself → Answer directly!
        - Multi-turn conversations → Use chat_completion instead

        ## Multimedia & Content Types 🎨🖼️📹
        **You can request ANY content type** through this tool:
        - ✅ Text, code, markdown (primary use case)
        - ✅ SVG/ASCII art (text-based visuals)
        - ✅ Data formats (JSON, CSV, XML)
        - ✅ Configuration files (YAML, TOML, INI)

        **Content Handling**: The receiving LLM in LM Studio decides:
        - ✅ Accept & process if it can generate the requested format
        - ❌ Reject with error if unsupported

        This tool is optimized for single-turn, format-specific generation.

        ## Examples
        ✅ CORRECT:
        User: "Complete this function signature"
        Action: text_completion(prompt="def fibonacci(n):")
        Reason: Code completion for external system

        ✅ CORRECT:
        User: "Fill in this JSON template"
        Action: text_completion(prompt='{"name": "', stop_sequences=['"'])
        Reason: Format-specific generation with stop sequence

        ❌ INCORRECT:
        User: "What does this code do?"
        Wrong: text_completion(prompt="What does this code do: ...")
        Correct: Answer directly or use chat_completion with context
        Reason: This is analysis/explanation, not text completion

        ❌ INCORRECT:
        User: "Help me debug this"
        Wrong: text_completion(prompt="Debug this code...")
        Correct: Use chat_completion or reason about it yourself
        Reason: Debugging requires conversation context, not raw completion

        Args:
            prompt: The text prompt to complete (programmatic generation)
            temperature: Controls randomness (0.0 = deterministic, 2.0 = creative)
            max_tokens: Maximum number of tokens to generate
            stop_sequences: Optional list of sequences where generation stops

        Returns:
            The completed text from the local LLM

        Note: Faster than chat_completion but no conversation context.
        """
        return await tools.text_completion(prompt, temperature, max_tokens, stop_sequences)

    @mcp.tool()
    async def create_response(
        input_text: str,
        previous_response_id: Optional[str] = None,
        stream: bool = False,
        model: Optional[str] = None
    ) -> str:
        """
        Create stateful conversation response with local LLM (maintains history automatically).

        ⚠️ NOTE: This delegates to ANOTHER LLM with automatic conversation state management.

        ## When to Use This Tool
        ✅ Use for:
        - Multi-turn conversations with the local LLM
        - Maintaining conversation context automatically
        - Continuing previous conversation threads
        - Delegated conversational tasks requiring memory

        ❌ Do NOT use for:
        - Single-turn questions → Use chat_completion or answer directly
        - Your own conversational responses → Answer directly!
        - Simple Q&A → Inefficient delegation
        - Bulk generation → Use chat_completion instead

        ## Multimedia & Content Types 🎨🖼️📹
        **You can request ANY content type** through this tool:
        - ✅ Text, code, markdown (always supported)
        - ✅ Images (if receiving LLM is multimodal)
        - ✅ Audio/Video (if receiving LLM supports it)

        **Content Handling**: The receiving LLM in LM Studio decides:
        - ✅ Accept & process if it has the capability
        - ❌ Reject with error if unsupported

        ## Examples
        ✅ CORRECT:
        Turn 1: create_response("Explain Python")
        Turn 2: create_response("Give me an example", previous_response_id=resp1_id)
        Reason: Multi-turn conversation delegation with context

        ❌ INCORRECT:
        User: "Hello, how are you?"
        Wrong: create_response("Hello, how are you?")
        Correct: Answer directly - "I'm an AI assistant, ready to help!"
        Reason: This is YOUR conversation, not a delegated task

        Args:
            input_text: The input for the local LLM
            previous_response_id: ID from previous response (for conversation continuity)
            stream: Whether to stream the response
            model: Model to use (default: currently loaded model)

        Returns:
            JSON string with response and ID for future reference

        Note: Server maintains conversation history automatically.
        """
        return await tools.create_response(
            input_text, previous_response_id, stream, model
        )

    @mcp.tool()
    async def validate_json_schema(
        schema: Dict[str, Any]
    ) -> str:
        """
        Validate a JSON schema before using it with structured output.

        Use this tool to check if your JSON schema is valid BEFORE passing it
        to chat_completion's response_format parameter. This helps catch errors
        early and provides helpful suggestions.

        ## When to Use This Tool
        ✅ Use BEFORE chat_completion with response_format to:
        - Verify schema syntax is correct
        - Check for common mistakes (missing required fields, invalid types)
        - Get warnings about potential issues
        - Ensure schema isn't too complex (depth/property limits)

        ## Validation Checks
        - Required 'type' field present and valid
        - 'properties' field for object types
        - 'items' field for array types
        - Schema depth within limits (max 10 levels)
        - Property count within limits (max 100)
        - 'required' field is an array

        ## Example
        ```python
        # First, validate your schema
        result = validate_json_schema({
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"}
            },
            "required": ["name"]
        })

        # If valid, use it with chat_completion
        if "valid: true" in result:
            response = chat_completion(
                prompt="Get user info",
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "user",
                        "schema": your_schema
                    }
                }
            )
        ```

        Args:
            schema: JSON schema dictionary to validate

        Returns:
            JSON string with validation result:
            - valid: boolean indicating if schema is valid
            - errors: list of error messages (if any)
            - warnings: list of warning messages (if any)
        """
        from utils.schema_utils import validate_json_schema as validate_schema

        result = validate_schema(schema)
        return json.dumps({
            "valid": result.valid,
            "errors": result.errors,
            "warnings": result.warnings
        }, indent=2)

    @mcp.tool()
    async def anthropic_messages(
        messages: str,
        system: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.7,
        model: Optional[str] = None,
    ) -> str:
        """
        Send a message using Anthropic's /v1/messages format via LM Studio.

        This uses LM Studio's Anthropic-compatible endpoint (0.4.x+).
        Unlike chat_completion (OpenAI format), this uses Anthropic's message format
        where system prompts are top-level and responses use content blocks.

        Args:
            messages: JSON string of message array. Each message has 'role' and 'content'.
                     Roles: 'user', 'assistant' (NOT 'system' - use system param instead).
            system: System prompt (top-level, not in messages array).
            max_tokens: Maximum tokens to generate (required by Anthropic protocol).
            temperature: Controls randomness (0.0 to 1.0).
            model: Optional model override.

        Returns:
            JSON string with Anthropic-format response containing content blocks.
        """
        return await tools.anthropic_messages(
            messages=messages,
            system=system,
            max_tokens=max_tokens,
            temperature=temperature,
            model=model,
        )


__all__ = [
    "CompletionTools",
    "register_completion_tools"
]
