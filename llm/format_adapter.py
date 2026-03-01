#!/usr/bin/env python3
"""
Format Adapter — 3-way API format routing for LM Studio Bridge.

Centralizes all format translation between the three supported API surfaces:
  - OpenAI  (chat completions endpoint)
  - Anthropic (messages endpoint)
  - Responses (LM Studio flattened format)

Usage:
    from llm.format_adapter import APIFormat, FormatAdapter

    # Convert tools from OpenAI to Anthropic format
    anthropic_tools = FormatAdapter.openai_tools_to_anthropic(openai_tools)

    # Use master router for dynamic dispatch
    result = FormatAdapter.adapt_tools(tools, APIFormat.OPENAI, APIFormat.ANTHROPIC)
"""

import json
from enum import Enum
from typing import Any, Union

from config.constants import FORMAT_ANTHROPIC, FORMAT_OPENAI, FORMAT_RESPONSES


class APIFormat(str, Enum):
    """Canonical format identifiers for 3-way routing."""

    OPENAI = FORMAT_OPENAI        # /v1/chat/completions
    ANTHROPIC = FORMAT_ANTHROPIC  # Anthropic messages endpoint
    RESPONSES = FORMAT_RESPONSES  # /v1/responses (LM Studio flattened)


class FormatAdapter:
    """Centralized format translation between OpenAI, Anthropic, and Responses APIs.

    All methods are static — no instance state required.
    """

    # ------------------------------------------------------------------
    # Tool format conversions — direct paths
    # ------------------------------------------------------------------

    @staticmethod
    def openai_tools_to_responses(
        tools: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Convert OpenAI tool format to LM Studio /v1/responses (flattened) format.

        OpenAI:    {"type": "function", "function": {"name": "...", ...}}
        Responses: {"type": "function", "name": "...", ...}  (no nested "function" key)

        Args:
            tools: List of tools in OpenAI format.

        Returns:
            List of tools in LM Studio flattened format.
        """
        flattened = []
        for tool in tools:
            if tool.get("type") == "function" and "function" in tool:
                flattened.append({"type": "function", **tool["function"]})
            else:
                flattened.append(tool)
        return flattened

    @staticmethod
    def openai_tools_to_anthropic(
        tools: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Convert OpenAI tool format to Anthropic tool format.

        OpenAI:    {"type": "function", "function": {"name": "...", "parameters": {...}}}
        Anthropic: {"name": "...", "description": "...", "input_schema": {...}}

        Args:
            tools: List of tools in OpenAI format.

        Returns:
            List of tools in Anthropic format.
        """
        converted = []
        for tool in tools:
            if tool.get("type") == "function" and "function" in tool:
                func = tool["function"]
                anthropic_tool: dict[str, Any] = {
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
    def anthropic_tools_to_openai(
        tools: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Convert Anthropic tool format to OpenAI tool format.

        Anthropic: {"name": "...", "description": "...", "input_schema": {...}}
        OpenAI:    {"type": "function", "function": {"name": "...", "parameters": {...}}}

        Args:
            tools: List of tools in Anthropic format.

        Returns:
            List of tools in OpenAI format.
        """
        converted = []
        for tool in tools:
            func: dict[str, Any] = {
                "name": tool["name"],
                "description": tool.get("description", ""),
            }
            if "input_schema" in tool:
                func["parameters"] = tool["input_schema"]
            converted.append({"type": "function", "function": func})
        return converted

    @staticmethod
    def responses_tools_to_openai(
        tools: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Convert LM Studio /v1/responses (flattened) format back to OpenAI format.

        Responses: {"type": "function", "name": "...", "description": "...", ...}
        OpenAI:    {"type": "function", "function": {"name": "...", "description": "...", ...}}

        Args:
            tools: List of tools in LM Studio flattened format.

        Returns:
            List of tools in OpenAI nested format.
        """
        converted = []
        for tool in tools:
            if tool.get("type") == "function":
                # Extract everything except "type" into the nested function dict
                func = {k: v for k, v in tool.items() if k != "type"}
                converted.append({"type": "function", "function": func})
            else:
                converted.append(tool)
        return converted

    @staticmethod
    def anthropic_tools_to_responses(
        tools: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Convert Anthropic tool format to LM Studio Responses format.

        Chains: anthropic -> openai -> responses

        Args:
            tools: List of tools in Anthropic format.

        Returns:
            List of tools in LM Studio flattened format.
        """
        openai_tools = FormatAdapter.anthropic_tools_to_openai(tools)
        return FormatAdapter.openai_tools_to_responses(openai_tools)

    @staticmethod
    def responses_tools_to_anthropic(
        tools: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Convert LM Studio Responses format to Anthropic tool format.

        Chains: responses -> openai -> anthropic

        Args:
            tools: List of tools in LM Studio flattened format.

        Returns:
            List of tools in Anthropic format.
        """
        openai_tools = FormatAdapter.responses_tools_to_openai(tools)
        return FormatAdapter.openai_tools_to_anthropic(openai_tools)

    # ------------------------------------------------------------------
    # Tool format master router
    # ------------------------------------------------------------------

    @staticmethod
    def adapt_tools(
        tools: list[dict[str, Any]],
        source_format: APIFormat,
        target_format: APIFormat,
    ) -> list[dict[str, Any]]:
        """Route tool conversion based on source and target format.

        Returns tools unchanged when source == target.

        Args:
            tools: List of tool dicts.
            source_format: Format of the input tools.
            target_format: Desired output format.

        Returns:
            Tools converted to target_format.

        Raises:
            ValueError: When an unsupported source/target pair is requested.
        """
        # Normalise to enum values so string args work too
        try:
            src = APIFormat(source_format)
            tgt = APIFormat(target_format)
        except ValueError:
            raise ValueError(
                f"Unsupported format pair: {source_format!r} -> {target_format!r}. "
                f"Supported formats: {[f.value for f in APIFormat]}"
            ) from None

        if src == tgt:
            return tools

        dispatch: dict[tuple[APIFormat, APIFormat], Any] = {
            (APIFormat.OPENAI, APIFormat.ANTHROPIC): FormatAdapter.openai_tools_to_anthropic,
            (APIFormat.OPENAI, APIFormat.RESPONSES): FormatAdapter.openai_tools_to_responses,
            (APIFormat.ANTHROPIC, APIFormat.OPENAI): FormatAdapter.anthropic_tools_to_openai,
            (APIFormat.ANTHROPIC, APIFormat.RESPONSES): FormatAdapter.anthropic_tools_to_responses,
            (APIFormat.RESPONSES, APIFormat.OPENAI): FormatAdapter.responses_tools_to_openai,
            (APIFormat.RESPONSES, APIFormat.ANTHROPIC): FormatAdapter.responses_tools_to_anthropic,
        }

        converter = dispatch.get((src, tgt))
        if converter is None:
            raise ValueError(
                f"No converter registered for {src.value!r} -> {tgt.value!r}"
            )
        return converter(tools)

    # ------------------------------------------------------------------
    # Message format conversions
    # ------------------------------------------------------------------

    @staticmethod
    def openai_messages_to_anthropic(
        messages: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], str]:
        """Extract system messages from an OpenAI messages array.

        Anthropic requires the system prompt at the top level (not in messages).
        Multiple system messages are concatenated with a newline separator.

        Args:
            messages: List of OpenAI message dicts.

        Returns:
            Tuple of (filtered_messages, system_prompt_str) where
            filtered_messages has all system-role messages removed and
            system_prompt_str is their concatenated content.
        """
        system_parts: list[str] = []
        filtered: list[dict[str, Any]] = []

        for msg in messages:
            if msg.get("role") == "system":
                system_parts.append(msg.get("content", ""))
            else:
                filtered.append(msg)

        system_str = "\n".join(system_parts)
        return filtered, system_str

    @staticmethod
    def anthropic_messages_to_openai(
        messages: list[dict[str, Any]],
        system: str = "",
    ) -> list[dict[str, Any]]:
        """Prepend a system message to an Anthropic messages array.

        Args:
            messages: List of Anthropic message dicts (no system role).
            system: Top-level system prompt to prepend (skipped if empty).

        Returns:
            Messages array with system message prepended (if non-empty).
        """
        if not system:
            return list(messages)
        return [{"role": "system", "content": system}] + list(messages)

    @staticmethod
    def adapt_messages(
        messages: list[dict[str, Any]],
        source_format: APIFormat,
        target_format: APIFormat,
        system: str = "",
    ) -> Union[list[dict[str, Any]], tuple[list[dict[str, Any]], str]]:
        """Route message conversion based on source and target format.

        Args:
            messages: List of message dicts.
            source_format: Format of the input messages.
            target_format: Desired output format.
            system: System prompt (used when converting Anthropic to OpenAI).

        Returns:
            For OpenAI->Anthropic: Tuple (filtered_messages, system_str).
            For Anthropic->OpenAI: List of messages with system prepended.
            Same format: original messages list unchanged.
        """
        try:
            src = APIFormat(source_format)
            tgt = APIFormat(target_format)
        except ValueError:
            raise ValueError(
                f"Unsupported format pair: {source_format!r} -> {target_format!r}"
            ) from None

        if src == tgt:
            return messages

        if src == APIFormat.OPENAI and tgt == APIFormat.ANTHROPIC:
            return FormatAdapter.openai_messages_to_anthropic(messages)

        if src == APIFormat.ANTHROPIC and tgt == APIFormat.OPENAI:
            return FormatAdapter.anthropic_messages_to_openai(messages, system=system)

        raise ValueError(
            f"Message conversion not implemented for {src.value!r} -> {tgt.value!r}"
        )

    # ------------------------------------------------------------------
    # Response parsing helpers (extracted from LLMClient)
    # ------------------------------------------------------------------

    @staticmethod
    def extract_anthropic_tool_calls(
        response: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Extract tool_use blocks from an Anthropic response.

        Args:
            response: Anthropic API response dict.

        Returns:
            List of dicts with id, name, input for each tool_use block.
        """
        calls: list[dict[str, Any]] = []
        for block in response.get("content", []):
            if block.get("type") == "tool_use":
                calls.append(
                    {
                        "id": block.get("id"),
                        "name": block.get("name"),
                        "input": block.get("input", {}),
                    }
                )
        return calls

    @staticmethod
    def build_anthropic_tool_result(
        tool_use_id: str,
        content: Union[str, dict, None],
        is_error: bool = False,
    ) -> dict[str, Any]:
        """Build an Anthropic tool_result message.

        Args:
            tool_use_id: The id from the tool_use block.
            content: Result content (str, dict auto-serialized to JSON, None becomes "").
            is_error: Whether this is an error result.

        Returns:
            Message dict with role=user and a tool_result content block.
        """
        if content is None:
            content_str = ""
        elif isinstance(content, dict):
            content_str = json.dumps(content)
        else:
            content_str = str(content)

        block: dict[str, Any] = {
            "type": "tool_result",
            "tool_use_id": tool_use_id,
            "content": content_str,
        }
        if is_error:
            block["is_error"] = True

        return {"role": "user", "content": [block]}

    # ------------------------------------------------------------------
    # Response format conversions
    # ------------------------------------------------------------------

    @staticmethod
    def openai_response_to_anthropic(
        response: dict[str, Any],
    ) -> dict[str, Any]:
        """Convert an OpenAI chat completion response to Anthropic format.

        Args:
            response: OpenAI chat completion response dict.

        Returns:
            Response dict in Anthropic format with a 'content' list.
        """
        content: list[dict[str, Any]] = []

        try:
            choices = response.get("choices", [])
            if not choices:
                return {"content": content}

            message = choices[0].get("message", {})
            finish_reason = choices[0].get("finish_reason", "stop")

            # Handle tool calls
            tool_calls: list[dict[str, Any]] | None = message.get("tool_calls")
            if tool_calls:
                for tc in tool_calls:
                    func = tc.get("function", {})
                    raw_args = func.get("arguments", "{}")
                    try:
                        input_data = json.loads(raw_args)
                    except (json.JSONDecodeError, TypeError):
                        input_data = {}
                    content.append(
                        {
                            "type": "tool_use",
                            "id": tc.get("id", ""),
                            "name": func.get("name", ""),
                            "input": input_data,
                        }
                    )

            # Handle text content
            text: str | None = message.get("content")
            if text:
                content.append({"type": "text", "text": text})

            stop_reason = "tool_use" if finish_reason == "tool_calls" else "end_turn"
            return {"content": content, "stop_reason": stop_reason}

        except (KeyError, IndexError, TypeError):
            return {"content": content}

    @staticmethod
    def anthropic_response_to_openai(
        response: dict[str, Any],
    ) -> dict[str, Any]:
        """Convert an Anthropic response to OpenAI chat completion format.

        Args:
            response: Anthropic API response dict.

        Returns:
            Response dict in OpenAI chat completion format.
        """
        message: dict[str, Any] = {"role": "assistant", "content": None}
        finish_reason = "stop"

        try:
            content_blocks = response.get("content", [])
            stop_reason = response.get("stop_reason", "end_turn")

            tool_calls: list[dict[str, Any]] = []
            text_parts: list[str] = []

            for block in content_blocks:
                block_type = block.get("type")
                if block_type == "tool_use":
                    tool_calls.append(
                        {
                            "id": block.get("id", ""),
                            "type": "function",
                            "function": {
                                "name": block.get("name", ""),
                                "arguments": json.dumps(block.get("input", {})),
                            },
                        }
                    )
                elif block_type == "text":
                    text_parts.append(block.get("text", ""))

            if tool_calls:
                message["tool_calls"] = tool_calls
                finish_reason = "tool_calls"
            if text_parts:
                message["content"] = "\n".join(text_parts)

            if stop_reason == "tool_use":
                finish_reason = "tool_calls"

        except (KeyError, TypeError):
            pass

        return {
            "choices": [
                {
                    "message": message,
                    "finish_reason": finish_reason,
                    "index": 0,
                }
            ]
        }


__all__ = ["APIFormat", "FormatAdapter"]
