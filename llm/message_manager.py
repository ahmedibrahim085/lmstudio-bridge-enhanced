#!/usr/bin/env python3
"""
Message and conversation history management for LLM interactions.

This module handles maintaining conversation context, formatting messages,
and managing tool calling history.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json


@dataclass
class Message:
    """Represents a single message in a conversation."""

    role: str  # 'system', 'user', 'assistant', 'tool'
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary format.

        Returns:
            Dictionary representation suitable for LLM API
        """
        msg = {
            "role": self.role,
            "content": self.content
        }

        if self.tool_call_id:
            msg["tool_call_id"] = self.tool_call_id

        if self.tool_calls:
            msg["tool_calls"] = self.tool_calls

        if self.name:
            msg["name"] = self.name

        return msg


class ConversationHistory:
    """Manages conversation history and context."""

    def __init__(self, max_messages: Optional[int] = None):
        """Initialize conversation history.

        Args:
            max_messages: Optional maximum number of messages to retain
        """
        self.messages: List[Message] = []
        self.max_messages = max_messages

    def add_message(
        self,
        role: str,
        content: str,
        tool_call_id: Optional[str] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        name: Optional[str] = None
    ) -> Message:
        """Add a message to conversation history.

        Args:
            role: Message role
            content: Message content
            tool_call_id: Optional tool call ID for tool responses
            tool_calls: Optional tool calls from assistant
            name: Optional name for the message

        Returns:
            Created Message object
        """
        message = Message(
            role=role,
            content=content,
            tool_call_id=tool_call_id,
            tool_calls=tool_calls,
            name=name
        )

        self.messages.append(message)

        # Trim if exceeds max_messages
        if self.max_messages and len(self.messages) > self.max_messages:
            # Keep system message if present, trim from the middle
            if self.messages[0].role == "system":
                # Keep first (system) and last N-1 messages
                self.messages = [self.messages[0]] + self.messages[-(self.max_messages - 1):]
            else:
                # Keep last N messages
                self.messages = self.messages[-self.max_messages:]

        return message

    def add_user_message(self, content: str) -> Message:
        """Add a user message.

        Args:
            content: Message content

        Returns:
            Created Message object
        """
        return self.add_message(role="user", content=content)

    def add_assistant_message(
        self,
        content: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None
    ) -> Message:
        """Add an assistant message.

        Args:
            content: Message content
            tool_calls: Optional tool calls

        Returns:
            Created Message object
        """
        return self.add_message(role="assistant", content=content, tool_calls=tool_calls)

    def add_system_message(self, content: str) -> Message:
        """Add a system message.

        Args:
            content: System instructions

        Returns:
            Created Message object
        """
        return self.add_message(role="system", content=content)

    def add_tool_message(self, content: str, tool_call_id: str) -> Message:
        """Add a tool response message.

        Args:
            content: Tool response content
            tool_call_id: ID of the tool call this responds to

        Returns:
            Created Message object
        """
        return self.add_message(role="tool", content=content, tool_call_id=tool_call_id)

    def to_list(self) -> List[Dict[str, Any]]:
        """Convert conversation to list of dictionaries.

        Returns:
            List of message dictionaries for LLM API
        """
        return [msg.to_dict() for msg in self.messages]

    def clear(self) -> None:
        """Clear all messages."""
        self.messages.clear()

    def get_last_message(self) -> Optional[Message]:
        """Get the last message in conversation.

        Returns:
            Last Message or None if empty
        """
        return self.messages[-1] if self.messages else None

    def get_messages_by_role(self, role: str) -> List[Message]:
        """Get all messages with a specific role.

        Args:
            role: Message role to filter by

        Returns:
            List of matching messages
        """
        return [msg for msg in self.messages if msg.role == role]

    def count_messages(self) -> int:
        """Get total number of messages.

        Returns:
            Message count
        """
        return len(self.messages)

    def to_json(self) -> str:
        """Export conversation to JSON.

        Returns:
            JSON string of conversation
        """
        data = {
            "messages": [
                {
                    **msg.to_dict(),
                    "timestamp": msg.timestamp.isoformat()
                }
                for msg in self.messages
            ]
        }
        return json.dumps(data, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "ConversationHistory":
        """Load conversation from JSON.

        Args:
            json_str: JSON string of conversation

        Returns:
            ConversationHistory instance
        """
        data = json.loads(json_str)
        history = cls()

        for msg_data in data.get("messages", []):
            history.add_message(
                role=msg_data["role"],
                content=msg_data["content"],
                tool_call_id=msg_data.get("tool_call_id"),
                tool_calls=msg_data.get("tool_calls"),
                name=msg_data.get("name")
            )

        return history


class ToolCallTracker:
    """Tracks tool calls and their results in a conversation."""

    def __init__(self):
        """Initialize tool call tracker."""
        self.tool_calls: List[Dict[str, Any]] = []

    def record_tool_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        result: Optional[str] = None,
        error: Optional[str] = None
    ) -> None:
        """Record a tool call and its result.

        Args:
            tool_name: Name of the tool
            arguments: Tool arguments
            result: Tool result if successful
            error: Error message if failed
        """
        record = {
            "tool_name": tool_name,
            "arguments": arguments,
            "result": result,
            "error": error,
            "timestamp": datetime.now().isoformat(),
            "success": error is None
        }

        self.tool_calls.append(record)

    def get_tool_calls(
        self,
        tool_name: Optional[str] = None,
        successful_only: bool = False
    ) -> List[Dict[str, Any]]:
        """Get recorded tool calls.

        Args:
            tool_name: Optional filter by tool name
            successful_only: Only return successful calls

        Returns:
            List of tool call records
        """
        calls = self.tool_calls

        if tool_name:
            calls = [c for c in calls if c["tool_name"] == tool_name]

        if successful_only:
            calls = [c for c in calls if c["success"]]

        return calls

    def get_call_count(self, tool_name: Optional[str] = None) -> int:
        """Get number of tool calls.

        Args:
            tool_name: Optional filter by tool name

        Returns:
            Count of tool calls
        """
        if tool_name:
            return len([c for c in self.tool_calls if c["tool_name"] == tool_name])
        return len(self.tool_calls)

    def clear(self) -> None:
        """Clear all recorded tool calls."""
        self.tool_calls.clear()


class MessageFormatter:
    """Formats messages for display and logging."""

    @staticmethod
    def format_message(message: Message, include_timestamp: bool = True) -> str:
        """Format a message for display.

        Args:
            message: Message to format
            include_timestamp: Whether to include timestamp

        Returns:
            Formatted message string
        """
        parts = []

        if include_timestamp:
            parts.append(f"[{message.timestamp.strftime('%H:%M:%S')}]")

        parts.append(f"{message.role.upper()}:")

        if message.tool_calls:
            parts.append(f"\n  Tool Calls: {len(message.tool_calls)}")
            for tc in message.tool_calls:
                parts.append(f"\n    - {tc['function']['name']}")

        if message.content:
            parts.append(f"\n  {message.content}")

        return " ".join(parts)

    @staticmethod
    def format_conversation(
        history: ConversationHistory,
        include_timestamps: bool = True
    ) -> str:
        """Format entire conversation for display.

        Args:
            history: Conversation history
            include_timestamps: Whether to include timestamps

        Returns:
            Formatted conversation string
        """
        return "\n\n".join([
            MessageFormatter.format_message(msg, include_timestamps)
            for msg in history.messages
        ])


__all__ = [
    "Message",
    "ConversationHistory",
    "ToolCallTracker",
    "MessageFormatter"
]
