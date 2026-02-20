"""OPP-08: Unit tests for llm/message_manager.py (previously 0 coverage)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from llm.message_manager import (
    ConversationHistory,
    Message,
    MessageFormatter,
)


class TestMessage:
    """Unit tests for the Message dataclass."""

    def test_to_dict_basic(self):
        """Message.to_dict() returns role and content keys only."""
        msg = Message(role="user", content="hello")
        result = msg.to_dict()
        assert result == {"role": "user", "content": "hello"}

    def test_to_dict_with_tool_call_id(self):
        """Message.to_dict() includes tool_call_id when set."""
        msg = Message(role="tool", content="result", tool_call_id="tc1")
        result = msg.to_dict()
        assert "tool_call_id" in result
        assert result["tool_call_id"] == "tc1"

    def test_to_dict_with_tool_calls(self):
        """Message.to_dict() includes tool_calls when set."""
        tool_calls = [{"id": "1", "function": {"name": "test"}}]
        msg = Message(role="assistant", content="", tool_calls=tool_calls)
        result = msg.to_dict()
        assert "tool_calls" in result
        assert result["tool_calls"] == tool_calls

    def test_to_dict_with_name(self):
        """Message.to_dict() includes name when set."""
        msg = Message(role="assistant", content="hi", name="bot")
        result = msg.to_dict()
        assert "name" in result
        assert result["name"] == "bot"


class TestConversationHistory:
    """Unit tests for ConversationHistory message management methods."""

    def test_add_message_returns_message(self):
        """add_message() returns a Message instance."""
        history = ConversationHistory()
        result = history.add_message("user", "hi")
        assert isinstance(result, Message)
        assert result.role == "user"
        assert result.content == "hi"

    def test_add_user_message(self):
        """add_user_message() adds a message with role 'user'."""
        history = ConversationHistory()
        history.add_user_message("hi")
        assert history.count_messages() == 1
        assert history.messages[0].role == "user"
        assert history.messages[0].content == "hi"

    def test_add_assistant_message_with_tool_calls(self):
        """add_assistant_message() stores tool_calls on the created Message."""
        history = ConversationHistory()
        tool_calls = [{"id": "c1", "function": {"name": "lookup"}}]
        msg = history.add_assistant_message("ok", tool_calls=tool_calls)
        assert msg.tool_calls == tool_calls
        assert history.messages[0].tool_calls == tool_calls

    def test_add_system_message(self):
        """add_system_message() adds a message with role 'system'."""
        history = ConversationHistory()
        history.add_system_message("You are a helpful assistant.")
        assert history.count_messages() == 1
        assert history.messages[0].role == "system"

    def test_add_tool_message(self):
        """add_tool_message() adds a message with role 'tool' and tool_call_id."""
        history = ConversationHistory()
        history.add_tool_message("result", tool_call_id="tc1")
        assert history.count_messages() == 1
        assert history.messages[0].role == "tool"
        assert history.messages[0].tool_call_id == "tc1"

    def test_clear(self):
        """clear() removes all messages from history."""
        history = ConversationHistory()
        history.add_user_message("one")
        history.add_user_message("two")
        history.add_user_message("three")
        assert history.count_messages() == 3
        history.clear()
        assert history.count_messages() == 0


class TestTrimming:
    """Unit tests for message trimming behaviour in ConversationHistory."""

    def test_no_trimming_under_limit(self):
        """Messages below max_messages are all retained."""
        history = ConversationHistory(max_messages=10)
        history.add_user_message("one")
        history.add_user_message("two")
        history.add_user_message("three")
        assert history.count_messages() == 3

    def test_trimming_no_system(self):
        """When no system message, only the last max_messages messages are kept."""
        history = ConversationHistory(max_messages=3)
        for i in range(5):
            history.add_user_message(f"msg{i}")
        assert history.count_messages() == 3
        # The last three should be msg2, msg3, msg4
        contents = [m.content for m in history.messages]
        assert contents == ["msg2", "msg3", "msg4"]

    def test_trimming_preserves_system(self):
        """System message is always kept; last N-1 non-system messages fill the rest."""
        history = ConversationHistory(max_messages=3)
        history.add_system_message("Be helpful.")
        for i in range(4):
            history.add_user_message(f"user{i}")
        # max=3: system + last 2 user messages
        assert history.count_messages() == 3
        assert history.messages[0].role == "system"
        contents = [m.content for m in history.messages[1:]]
        assert contents == ["user2", "user3"]

    def test_trimming_max_one_with_system(self):
        """BUG FIX: max_messages=1 with system message must keep only system message.

        Before the fix, messages[-(1-1):] == messages[-0:] == messages[0:] (ALL),
        which caused [system] + [system, user] = 3 messages with duplicates.
        After the fix, only the system message is retained.
        """
        history = ConversationHistory(max_messages=1)
        history.add_system_message("System prompt.")
        history.add_user_message("User question.")
        assert len(history.messages) == 1, (
            f"Expected 1 message, got {len(history.messages)}: "
            f"{[m.role for m in history.messages]}"
        )
        assert history.messages[0].role == "system"


class TestQueries:
    """Unit tests for ConversationHistory query methods."""

    def test_get_last_message(self):
        """get_last_message() returns the most recently added message."""
        history = ConversationHistory()
        history.add_user_message("first")
        history.add_user_message("second")
        history.add_user_message("third")
        last = history.get_last_message()
        assert last is not None
        assert last.content == "third"

    def test_get_last_message_empty(self):
        """get_last_message() returns None when history is empty."""
        history = ConversationHistory()
        assert history.get_last_message() is None

    def test_get_messages_by_role(self):
        """get_messages_by_role() filters messages by the given role."""
        history = ConversationHistory()
        history.add_system_message("Be helpful.")
        history.add_user_message("hello")
        history.add_assistant_message("hi there")
        history.add_user_message("how are you?")
        user_messages = history.get_messages_by_role("user")
        assert len(user_messages) == 2
        assert all(m.role == "user" for m in user_messages)


class TestSerialization:
    """Unit tests for ConversationHistory serialization methods."""

    def test_to_json_from_json_roundtrip(self):
        """to_json() + from_json() preserves roles and content."""
        history = ConversationHistory()
        history.add_system_message("You are helpful.")
        history.add_user_message("Hello!")
        history.add_assistant_message("Hi, how can I help?")

        json_str = history.to_json()
        restored = ConversationHistory.from_json(json_str)

        assert restored.count_messages() == 3
        assert restored.messages[0].role == "system"
        assert restored.messages[0].content == "You are helpful."
        assert restored.messages[1].role == "user"
        assert restored.messages[1].content == "Hello!"
        assert restored.messages[2].role == "assistant"
        assert restored.messages[2].content == "Hi, how can I help?"

    def test_to_list(self):
        """to_list() returns a list of dicts each containing 'role' and 'content'."""
        history = ConversationHistory()
        history.add_user_message("ping")
        history.add_assistant_message("pong")
        result = history.to_list()
        assert isinstance(result, list)
        assert len(result) == 2
        for item in result:
            assert "role" in item
            assert "content" in item


class TestMessageFormatter:
    """Unit tests for MessageFormatter static methods."""

    def test_format_message(self):
        """format_message() returns a string containing 'USER:' and the content."""
        msg = Message(role="user", content="hello world")
        formatted = MessageFormatter.format_message(msg, include_timestamp=False)
        assert "USER:" in formatted
        assert "hello world" in formatted

    def test_format_conversation(self):
        """format_conversation() joins messages separated by double newlines."""
        history = ConversationHistory()
        history.add_user_message("first")
        history.add_assistant_message("second")
        formatted = MessageFormatter.format_conversation(history, include_timestamps=False)
        assert "\n\n" in formatted
        assert "first" in formatted
        assert "second" in formatted


class TestExports:
    """Documents the public API surface of llm.message_manager."""

    def test_all_contains_stale_toolcalltracker(self):
        """__all__ contains 'ToolCallTracker' which is not yet defined (stale export).

        This test documents the stale export for OPP-09 to address.
        """
        import llm.message_manager  # noqa: PLC0415

        assert "ToolCallTracker" in llm.message_manager.__all__, (
            "Expected ToolCallTracker in __all__ (stale export documented for OPP-09)"
        )
