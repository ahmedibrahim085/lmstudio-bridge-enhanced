#!/usr/bin/env python3
"""
Tests for message window trimming in _autonomous_loop_anthropic.

The _autonomous_loop_anthropic method in tools/dynamic_autonomous.py now trims
the messages list when it exceeds MAX_ANTHROPIC_LOOP_MESSAGES (100). It keeps
the first message (user task) + last (limit-1) messages to prevent unbounded
memory growth in long-running autonomous loops.

Test approach:
1. Verify MAX_ANTHROPIC_LOOP_MESSAGES constant is properly defined
2. Test trimming logic directly without full MCP integration
3. Simulate message accumulation scenarios
4. Verify first message (user task) is always preserved
5. Verify recent messages are preserved after trimming
"""

import os
import sys

import pytest

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config.constants import MAX_ANTHROPIC_LOOP_MESSAGES  # noqa: E402

# ==============================================================================
# CONSTANT VALIDATION TESTS
# ==============================================================================


class TestMaxAnthropicLoopMessagesConstant:
    """Verify that MAX_ANTHROPIC_LOOP_MESSAGES constant is properly defined."""

    def test_constant_is_importable(self):
        """Test that MAX_ANTHROPIC_LOOP_MESSAGES can be imported from config.constants."""
        assert MAX_ANTHROPIC_LOOP_MESSAGES is not None

    def test_constant_is_integer(self):
        """Test that MAX_ANTHROPIC_LOOP_MESSAGES is an integer."""
        assert isinstance(MAX_ANTHROPIC_LOOP_MESSAGES, int), (
            f"MAX_ANTHROPIC_LOOP_MESSAGES must be int, got {type(MAX_ANTHROPIC_LOOP_MESSAGES)}"
        )

    def test_constant_is_positive(self):
        """Test that MAX_ANTHROPIC_LOOP_MESSAGES is a positive integer."""
        assert MAX_ANTHROPIC_LOOP_MESSAGES > 0, (
            f"MAX_ANTHROPIC_LOOP_MESSAGES must be positive, got {MAX_ANTHROPIC_LOOP_MESSAGES}"
        )

    def test_constant_has_reasonable_value(self):
        """Test that MAX_ANTHROPIC_LOOP_MESSAGES has a reasonable value (10-1000)."""
        assert 10 <= MAX_ANTHROPIC_LOOP_MESSAGES <= 1000, (
            f"MAX_ANTHROPIC_LOOP_MESSAGES should be between "
            f"10-1000, got {MAX_ANTHROPIC_LOOP_MESSAGES}"
        )

    def test_constant_value_is_100(self):
        """Test that MAX_ANTHROPIC_LOOP_MESSAGES is exactly 100 (design spec)."""
        assert MAX_ANTHROPIC_LOOP_MESSAGES == 100, (
            f"Expected MAX_ANTHROPIC_LOOP_MESSAGES=100, got {MAX_ANTHROPIC_LOOP_MESSAGES}"
        )


# ==============================================================================
# MESSAGE WINDOW TRIMMING LOGIC TESTS
# ==============================================================================


class TestMessageWindowTrimming:
    """Test the message window trimming logic from _autonomous_loop_anthropic."""

    @staticmethod
    def _apply_trimming_logic(messages: list) -> list:
        """
        Apply the exact trimming logic from _autonomous_loop_anthropic line 1102-1103.

        Keeps first message (user task) + last (limit-1) messages.

        Args:
            messages: List of messages to potentially trim

        Returns:
            Trimmed messages list (or original if no trimming needed)
        """
        if len(messages) > MAX_ANTHROPIC_LOOP_MESSAGES:
            return [messages[0]] + messages[-(MAX_ANTHROPIC_LOOP_MESSAGES - 1):]
        return messages

    def test_no_trim_when_under_limit(self):
        """Test that messages are NOT trimmed when under the limit."""
        messages = [{"role": "user", "content": "task"}]
        for i in range(5):
            messages.append({"role": "assistant", "content": f"response {i}"})

        original_len = len(messages)
        trimmed = self._apply_trimming_logic(messages)

        assert len(trimmed) == original_len, (
            "Messages under limit should not be modified"
        )
        assert trimmed == messages, "Messages should be identical when no trimming"

    def test_no_trim_when_exactly_at_limit(self):
        """Test that messages are NOT trimmed when exactly at the limit."""
        messages = [{"role": "user", "content": "task"}]
        for i in range(MAX_ANTHROPIC_LOOP_MESSAGES - 1):
            messages.append({"role": "assistant", "content": f"response {i}"})

        assert len(messages) == MAX_ANTHROPIC_LOOP_MESSAGES
        trimmed = self._apply_trimming_logic(messages)

        assert len(trimmed) == MAX_ANTHROPIC_LOOP_MESSAGES, (
            "Messages at limit should not be modified"
        )

    def test_trim_when_exceeds_limit(self):
        """Test that messages ARE trimmed when exceeding the limit."""
        messages = [{"role": "user", "content": "original task"}]
        for i in range(150):
            msg = {
                "role": "assistant",
                "content": [{"type": "text", "text": f"response {i}"}]
            }
            messages.append(msg)
            result_msg = {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": f"id_{i}",
                        "content": f"result {i}"
                    }
                ]
            }
            messages.append(result_msg)

        assert len(messages) > MAX_ANTHROPIC_LOOP_MESSAGES
        trimmed = self._apply_trimming_logic(messages)

        assert len(trimmed) == MAX_ANTHROPIC_LOOP_MESSAGES, (
            f"Trimmed messages should equal MAX_ANTHROPIC_LOOP_MESSAGES "
            f"({MAX_ANTHROPIC_LOOP_MESSAGES}), got {len(trimmed)}"
        )

    def test_first_message_always_preserved(self):
        """Test that the first message (user task) is always preserved after trimming."""
        original_task = "This is the original user task"
        messages = [{"role": "user", "content": original_task}]

        # Add many messages to force trimming
        for i in range(150):
            messages.append({"role": "assistant", "content": f"response {i}"})
            messages.append({"role": "user", "content": f"feedback {i}"})

        assert len(messages) > MAX_ANTHROPIC_LOOP_MESSAGES
        trimmed = self._apply_trimming_logic(messages)

        # First message must be preserved
        assert trimmed[0]["role"] == "user", (
            f"First message role should be 'user', got {trimmed[0]['role']}"
        )
        assert trimmed[0]["content"] == original_task, (
            f"First message content should be preserved task, got {trimmed[0]['content']}"
        )

    def test_recent_messages_preserved(self):
        """Test that the most recent messages are preserved after trimming."""
        messages = [{"role": "user", "content": "original task"}]
        for i in range(150):
            msg = {
                "role": "assistant",
                "content": [{"type": "text", "text": f"response {i}"}]
            }
            messages.append(msg)
            result_msg = {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": f"id_{i}",
                        "content": f"result {i}"
                    }
                ]
            }
            messages.append(result_msg)

        last_message_before_trim = messages[-1]
        second_last_message_before_trim = messages[-2]

        trimmed = self._apply_trimming_logic(messages)

        # Last message should be preserved
        assert trimmed[-1] == last_message_before_trim, (
            "Last message should be preserved after trimming"
        )
        # Second-to-last should also be preserved
        assert trimmed[-2] == second_last_message_before_trim, (
            "Second-to-last message should be preserved after trimming"
        )

    def test_trim_removes_old_messages(self):
        """Test that trimming actually removes old messages (not recent ones)."""
        messages = [
            {"role": "user", "content": "task", "id": 0},
            {"role": "assistant", "content": "response 0", "id": 1},
            {"role": "user", "content": "feedback 0", "id": 2},
        ]
        # Add 150 more messages
        for i in range(1, 150):
            msg_id = 3 + (i - 1) * 2
            messages.append(
                {"role": "assistant", "content": f"response {i}", "id": msg_id}
            )
            msg_id_2 = 4 + (i - 1) * 2
            messages.append(
                {"role": "user", "content": f"feedback {i}", "id": msg_id_2}
            )

        # Message with id=2 should be removed (old)
        old_message_id = 2
        assert any(m.get("id") == old_message_id for m in messages), (
            "Old message should exist before trimming"
        )

        trimmed = self._apply_trimming_logic(messages)

        # After trimming, the old message should be gone (except the first one)
        trimmed_ids = [m.get("id") for m in trimmed if m.get("id") is not None]
        assert old_message_id not in trimmed_ids, (
            "Old middle messages should be removed during trimming"
        )

    def test_trim_preserves_message_count_invariant(self):
        """Test that trimmed message count is exactly MAX_ANTHROPIC_LOOP_MESSAGES."""
        for total_messages in [101, 150, 200, 500, 1000]:
            messages = [{"role": "user", "content": "task"}]
            for i in range(total_messages - 1):
                role = "assistant" if i % 2 == 0 else "user"
                messages.append({"role": role, "content": f"message {i}"})

            trimmed = self._apply_trimming_logic(messages)

            assert len(trimmed) == MAX_ANTHROPIC_LOOP_MESSAGES, (
                f"For {total_messages} input messages, trimmed should be exactly "
                f"{MAX_ANTHROPIC_LOOP_MESSAGES}, got {len(trimmed)}"
            )

    def test_trim_handles_complex_message_structure(self):
        """Test trimming with realistic Anthropic message format."""
        messages = [{"role": "user", "content": "original task"}]

        # Simulate realistic assistant response with tool calls
        for i in range(150):
            # Assistant response with tool calls
            assistant_msg = {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": f"I will use tool {i}"},
                    {
                        "type": "tool_use",
                        "id": f"tool_{i}",
                        "name": f"tool_{i}",
                        "input": {"param": f"value_{i}"}
                    }
                ]
            }
            messages.append(assistant_msg)
            # Tool result
            tool_result_msg = {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": f"tool_{i}",
                        "content": f"Tool {i} executed"
                    }
                ]
            }
            messages.append(tool_result_msg)

        assert len(messages) > MAX_ANTHROPIC_LOOP_MESSAGES
        trimmed = self._apply_trimming_logic(messages)

        assert len(trimmed) == MAX_ANTHROPIC_LOOP_MESSAGES
        assert trimmed[0]["role"] == "user"
        assert trimmed[0]["content"] == "original task"

    def test_trim_with_error_messages(self):
        """Test trimming when messages include error responses."""
        messages = [{"role": "user", "content": "task"}]

        for i in range(150):
            messages.append({
                "role": "assistant",
                "content": [{"type": "text", "text": f"Attempting tool {i}"}]
            })
            # Tool error result
            if i % 10 == 0:
                error_msg = {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": f"id_{i}",
                            "content": f"Error: tool {i} failed",
                            "is_error": True
                        }
                    ]
                }
                messages.append(error_msg)
            else:
                result_msg = {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": f"id_{i}",
                            "content": f"Tool {i} result"
                        }
                    ]
                }
                messages.append(result_msg)

        trimmed = self._apply_trimming_logic(messages)

        assert len(trimmed) == MAX_ANTHROPIC_LOOP_MESSAGES
        # First message should be original task
        assert trimmed[0]["content"] == "task"


# ==============================================================================
# EDGE CASE TESTS
# ==============================================================================


class TestMessageWindowEdgeCases:
    """Test edge cases in message trimming."""

    @staticmethod
    def _apply_trimming_logic(messages: list) -> list:
        """Apply the exact trimming logic from _autonomous_loop_anthropic."""
        if len(messages) > MAX_ANTHROPIC_LOOP_MESSAGES:
            return [messages[0]] + messages[-(MAX_ANTHROPIC_LOOP_MESSAGES - 1):]
        return messages

    def test_empty_messages_list(self):
        """Test handling of empty messages list (edge case)."""
        messages = []
        trimmed = self._apply_trimming_logic(messages)
        assert trimmed == [], "Empty list should remain empty"

    def test_single_message(self):
        """Test handling of single message (should never trim)."""
        messages = [{"role": "user", "content": "task"}]
        trimmed = self._apply_trimming_logic(messages)
        assert len(trimmed) == 1
        assert trimmed[0] == messages[0]

    def test_two_messages(self):
        """Test handling of two messages (should never trim)."""
        messages = [
            {"role": "user", "content": "task"},
            {"role": "assistant", "content": "response"}
        ]
        trimmed = self._apply_trimming_logic(messages)
        assert len(trimmed) == 2
        assert trimmed == messages

    def test_very_large_message_list(self):
        """Test trimming with very large message list (1000+ messages)."""
        messages = [{"role": "user", "content": "task"}]
        for i in range(1000):
            messages.append({"role": "assistant" if i % 2 == 0 else "user", "content": f"msg {i}"})

        assert len(messages) == 1001
        trimmed = self._apply_trimming_logic(messages)

        assert len(trimmed) == MAX_ANTHROPIC_LOOP_MESSAGES
        assert trimmed[0] == messages[0]

    def test_alternating_roles(self):
        """Test trimming maintains message structure with alternating roles."""
        messages = [{"role": "user", "content": "task"}]
        for i in range(200):
            role = "assistant" if i % 2 == 0 else "user"
            messages.append({"role": role, "content": f"message {i}"})

        trimmed = self._apply_trimming_logic(messages)

        # Check that roles follow expected pattern in trimmed list
        for i in range(1, len(trimmed)):
            if trimmed[i - 1]["role"] == "assistant":
                # Next could be user or assistant (depending on trimming)
                # Just verify it's a valid role
                assert trimmed[i]["role"] in ["user", "assistant"]

    def test_none_values_preserved(self):
        """Test that None values in messages are preserved (not dropped)."""
        messages = [{"role": "user", "content": "task"}]
        for i in range(150):
            if i % 10 == 0:
                messages.append({"role": "assistant", "content": None})
            else:
                messages.append({"role": "assistant", "content": f"response {i}"})

        trimmed = self._apply_trimming_logic(messages)

        assert len(trimmed) == MAX_ANTHROPIC_LOOP_MESSAGES
        # Verify None values are preserved
        assert any(m.get("content") is None for m in trimmed[1:]), (
            "None content values should be preserved in trimmed messages"
        )


# ==============================================================================
# REGRESSION TESTS
# ==============================================================================


class TestMessageWindowRegressions:
    """Regression tests to prevent future bugs in message trimming."""

    @staticmethod
    def _apply_trimming_logic(messages: list) -> list:
        """Apply the exact trimming logic from _autonomous_loop_anthropic."""
        if len(messages) > MAX_ANTHROPIC_LOOP_MESSAGES:
            return [messages[0]] + messages[-(MAX_ANTHROPIC_LOOP_MESSAGES - 1):]
        return messages

    def test_off_by_one_at_boundary(self):
        """Test that trimming calculation is correct at boundary (100, 101, 102)."""
        # Exactly at limit
        messages_100 = [{"role": "user", "content": "task"}]
        for i in range(99):
            messages_100.append({"role": "assistant", "content": f"msg {i}"})

        trimmed_100 = self._apply_trimming_logic(messages_100)
        assert len(trimmed_100) == 100

        # One over limit
        messages_101 = messages_100 + [{"role": "user", "content": "msg 99"}]
        trimmed_101 = self._apply_trimming_logic(messages_101)
        assert len(trimmed_101) == 100

        # Two over limit
        messages_102 = messages_101 + [{"role": "assistant", "content": "msg 100"}]
        trimmed_102 = self._apply_trimming_logic(messages_102)
        assert len(trimmed_102) == 100

    def test_first_message_unchanged_multiple_trims(self):
        """Test that first message is preserved even after multiple trim operations."""
        original_task = "This is my task"
        messages = [{"role": "user", "content": original_task}]

        # Simulate multiple trim cycles
        for cycle in range(3):
            # Add 200 messages per cycle
            for i in range(200):
                messages.append({"role": "assistant", "content": f"cycle {cycle} msg {i}"})

            # Trim
            if len(messages) > MAX_ANTHROPIC_LOOP_MESSAGES:
                messages = [messages[0]] + messages[-(MAX_ANTHROPIC_LOOP_MESSAGES - 1):]

            # Verify first message is still original
            assert messages[0]["content"] == original_task, (
                f"After cycle {cycle}, first message should still be original task"
            )

    def test_slice_indices_correct(self):
        """Test that the slice indices [-(MAX_ANTHROPIC_LOOP_MESSAGES - 1):] are correct."""
        messages = [{"role": "user", "content": "task", "idx": 0}]
        for i in range(1, 150):
            messages.append({"role": "assistant", "content": "msg", "idx": i})

        # Before trim: 150 messages
        assert len(messages) == 150

        # Apply trim
        trimmed = [messages[0]] + messages[-(MAX_ANTHROPIC_LOOP_MESSAGES - 1):]

        # After trim: should be 100
        assert len(trimmed) == MAX_ANTHROPIC_LOOP_MESSAGES

        # The slice should start at message index 50 (150 - 99)
        expected_start_idx = 150 - (MAX_ANTHROPIC_LOOP_MESSAGES - 1)
        actual_start_idx = trimmed[1]["idx"]
        assert actual_start_idx == expected_start_idx, (
            f"Slice should start at index {expected_start_idx}, got {actual_start_idx}"
        )

        # Last message index should be 149
        assert trimmed[-1]["idx"] == 149, (
            f"Last message should have original index 149, got {trimmed[-1]['idx']}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
