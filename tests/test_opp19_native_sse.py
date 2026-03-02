"""Tests for OPP-19 Part 1: Native SSE Event Parser.

Covers:
  - NativeSSEEvent frozen dataclass (event_type, data fields)
  - parse_native_sse_stream() parses SSE blocks into NativeSSEEvent objects
  - All 19 native event type constants exist with correct string values
  - Error handling: invalid JSON and network errors yield error events (no raise)
  - Unknown event types pass through (not dropped)
  - Missing event: field falls back to a default type

Test categories (Req 07):
- Happy:    Tests 1-5  -- chat.start, message.delta, chat.end, sequence, float progress
- Negative: Tests 6-8  -- invalid JSON, network error, missing event field
- Edge:     Tests 9-11 -- unknown event type, empty data payload, all 19 types
- Boundary: Tests 12-13 -- constant string values, frozen dataclass
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# D-1: Activate testing mode BEFORE any production imports that could trigger
# get_config() -> LMStudioConfig.from_env() -> HTTP auto-detection.
from config.constants import LMSTUDIO_TESTING_ENV_VAR  # noqa: I001
os.environ.setdefault(LMSTUDIO_TESTING_ENV_VAR, "1")

from llm.native_sse_parser import NativeSSEEvent, parse_native_sse_stream  # noqa: E402


# ---------------------------------------------------------------------------
# Mock Helpers
# ---------------------------------------------------------------------------

class MockStreamResponse:
    """Mock HTTP response with iter_lines() for SSE testing."""

    def __init__(self, lines):
        self._lines = lines

    def iter_lines(self):
        return iter(self._lines)

    def close(self):
        pass


class BrokenStreamResponse:
    """Mock HTTP response whose iter_lines() raises an exception."""

    def iter_lines(self):
        raise Exception("Simulated network failure")

    def close(self):
        pass


def _sse_lines(*blocks):
    """Build raw SSE byte lines from (event_type, json_str) pairs.

    Each block is a 2-tuple: (event_type_str, json_data_str).
    Blocks are separated by an empty b"" line (SSE event boundary).
    """
    lines = []
    for event_type, json_str in blocks:
        lines.append(f"event: {event_type}".encode())
        lines.append(f"data: {json_str}".encode())
        lines.append(b"")
    return lines


# ---------------------------------------------------------------------------
# Happy Path Tests (1-5)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_parse_chat_start_event():
    """Happy-1: Single chat.start block yields NativeSSEEvent with correct fields."""
    lines = _sse_lines(("chat.start", '{"model": "test-model"}'))
    response = MockStreamResponse(lines)

    events = list(parse_native_sse_stream(response))

    assert len(events) == 1
    event = events[0]
    assert isinstance(event, NativeSSEEvent)
    assert event.event_type == "chat.start"
    assert event.data == {"model": "test-model"}


@pytest.mark.unit
def test_parse_message_delta_event():
    """Happy-2: message.delta block yields event with content in data dict."""
    lines = _sse_lines(("message.delta", '{"content": "Hello"}'))
    response = MockStreamResponse(lines)

    events = list(parse_native_sse_stream(response))

    assert len(events) == 1
    assert events[0].event_type == "message.delta"
    assert events[0].data["content"] == "Hello"


@pytest.mark.unit
def test_parse_chat_end_event():
    """Happy-3: chat.end block yields final event with nested result in data."""
    lines = _sse_lines(("chat.end", '{"result": {"content": "Full response"}}'))
    response = MockStreamResponse(lines)

    events = list(parse_native_sse_stream(response))

    assert len(events) == 1
    assert events[0].event_type == "chat.end"
    assert events[0].data["result"]["content"] == "Full response"


@pytest.mark.unit
def test_parse_multiple_events():
    """Happy-4: Sequence chat.start -> message.delta -> chat.end parsed in order."""
    lines = _sse_lines(
        ("chat.start", '{"model": "test"}'),
        ("message.delta", '{"content": "Hi"}'),
        ("chat.end", '{"result": {}}'),
    )
    response = MockStreamResponse(lines)

    events = list(parse_native_sse_stream(response))

    assert len(events) == 3
    assert events[0].event_type == "chat.start"
    assert events[1].event_type == "message.delta"
    assert events[2].event_type == "chat.end"


@pytest.mark.unit
def test_parse_model_load_progress():
    """Happy-5: model_load.progress block preserves float progress value."""
    lines = _sse_lines(("model_load.progress", '{"progress": 0.5}'))
    response = MockStreamResponse(lines)

    events = list(parse_native_sse_stream(response))

    assert len(events) == 1
    assert events[0].event_type == "model_load.progress"
    assert events[0].data["progress"] == 0.5


# ---------------------------------------------------------------------------
# Negative Tests (6-8)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_invalid_json_yields_error_event():
    """Negative-6: Invalid JSON in data field yields error event, does not raise."""
    lines = [
        b"event: message.delta",
        b"data: {invalid-json}",
        b"",
    ]
    response = MockStreamResponse(lines)

    events = list(parse_native_sse_stream(response))

    assert len(events) >= 1
    error_events = [e for e in events if e.event_type == "error"]
    assert len(error_events) >= 1, (
        f"Expected at least one error event, got: {[e.event_type for e in events]}"
    )


@pytest.mark.unit
def test_network_error_yields_error_event():
    """Negative-7: iter_lines() raises Exception -> yields error event, does not raise."""
    response = BrokenStreamResponse()

    # Must NOT raise — error is captured as an event
    events = list(parse_native_sse_stream(response))

    assert len(events) >= 1
    error_events = [e for e in events if e.event_type == "error"]
    assert len(error_events) >= 1, (
        f"Expected at least one error event, got: {[e.event_type for e in events]}"
    )


@pytest.mark.unit
def test_missing_event_field_uses_default():
    """Negative-8: data line without preceding event: line yields event with a default type."""
    lines = [
        b'data: {"content": "hi"}',
        b"",
    ]
    response = MockStreamResponse(lines)

    events = list(parse_native_sse_stream(response))

    # Should still yield something (not silently drop)
    assert len(events) >= 1
    # Default event_type must be a non-empty string
    assert events[0].event_type != ""
    assert isinstance(events[0].event_type, str)


# ---------------------------------------------------------------------------
# Edge Tests (9-11)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_unknown_event_type_still_yielded():
    """Edge-9: Unknown event type future.new.type passes through and is not dropped."""
    lines = _sse_lines(("future.new.type", '{}'))
    response = MockStreamResponse(lines)

    events = list(parse_native_sse_stream(response))

    assert len(events) == 1
    assert events[0].event_type == "future.new.type"


@pytest.mark.unit
def test_empty_data_payload():
    """Edge-10: event: chat.start with data: {} yields event with empty dict."""
    lines = _sse_lines(("chat.start", "{}"))
    response = MockStreamResponse(lines)

    events = list(parse_native_sse_stream(response))

    assert len(events) == 1
    assert events[0].event_type == "chat.start"
    assert events[0].data == {}


@pytest.mark.unit
def test_all_19_event_types_recognized():
    """Edge-11: Feed all 19 known event types -> all 19 NativeSSEEvents yielded."""
    from config.constants import (
        NATIVE_EVENT_CHAT_START,
        NATIVE_EVENT_MODEL_LOAD_START,
        NATIVE_EVENT_MODEL_LOAD_PROGRESS,
        NATIVE_EVENT_MODEL_LOAD_END,
        NATIVE_EVENT_PROMPT_PROCESSING_START,
        NATIVE_EVENT_PROMPT_PROCESSING_PROGRESS,
        NATIVE_EVENT_PROMPT_PROCESSING_END,
        NATIVE_EVENT_REASONING_START,
        NATIVE_EVENT_REASONING_DELTA,
        NATIVE_EVENT_REASONING_END,
        NATIVE_EVENT_TOOL_CALL_START,
        NATIVE_EVENT_TOOL_CALL_ARGUMENTS,
        NATIVE_EVENT_TOOL_CALL_SUCCESS,
        NATIVE_EVENT_TOOL_CALL_FAILURE,
        NATIVE_EVENT_MESSAGE_START,
        NATIVE_EVENT_MESSAGE_DELTA,
        NATIVE_EVENT_MESSAGE_END,
        NATIVE_EVENT_ERROR,
        NATIVE_EVENT_CHAT_END,
    )

    all_types = [
        NATIVE_EVENT_CHAT_START,
        NATIVE_EVENT_MODEL_LOAD_START,
        NATIVE_EVENT_MODEL_LOAD_PROGRESS,
        NATIVE_EVENT_MODEL_LOAD_END,
        NATIVE_EVENT_PROMPT_PROCESSING_START,
        NATIVE_EVENT_PROMPT_PROCESSING_PROGRESS,
        NATIVE_EVENT_PROMPT_PROCESSING_END,
        NATIVE_EVENT_REASONING_START,
        NATIVE_EVENT_REASONING_DELTA,
        NATIVE_EVENT_REASONING_END,
        NATIVE_EVENT_TOOL_CALL_START,
        NATIVE_EVENT_TOOL_CALL_ARGUMENTS,
        NATIVE_EVENT_TOOL_CALL_SUCCESS,
        NATIVE_EVENT_TOOL_CALL_FAILURE,
        NATIVE_EVENT_MESSAGE_START,
        NATIVE_EVENT_MESSAGE_DELTA,
        NATIVE_EVENT_MESSAGE_END,
        NATIVE_EVENT_ERROR,
        NATIVE_EVENT_CHAT_END,
    ]

    blocks = [(et, "{}") for et in all_types]
    lines = _sse_lines(*blocks)
    response = MockStreamResponse(lines)

    events = list(parse_native_sse_stream(response))

    assert len(events) == 19, f"Expected 19 events, got {len(events)}"
    yielded_types = [e.event_type for e in events]
    for expected_type in all_types:
        assert expected_type in yielded_types, (
            f"Event type '{expected_type}' was not yielded"
        )


# ---------------------------------------------------------------------------
# Boundary Tests (12-13)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_event_type_constant_values():
    """Boundary-12: All 19 NATIVE_EVENT_* constants match expected string values."""
    from config.constants import (
        NATIVE_EVENT_CHAT_START,
        NATIVE_EVENT_MODEL_LOAD_START,
        NATIVE_EVENT_MODEL_LOAD_PROGRESS,
        NATIVE_EVENT_MODEL_LOAD_END,
        NATIVE_EVENT_PROMPT_PROCESSING_START,
        NATIVE_EVENT_PROMPT_PROCESSING_PROGRESS,
        NATIVE_EVENT_PROMPT_PROCESSING_END,
        NATIVE_EVENT_REASONING_START,
        NATIVE_EVENT_REASONING_DELTA,
        NATIVE_EVENT_REASONING_END,
        NATIVE_EVENT_TOOL_CALL_START,
        NATIVE_EVENT_TOOL_CALL_ARGUMENTS,
        NATIVE_EVENT_TOOL_CALL_SUCCESS,
        NATIVE_EVENT_TOOL_CALL_FAILURE,
        NATIVE_EVENT_MESSAGE_START,
        NATIVE_EVENT_MESSAGE_DELTA,
        NATIVE_EVENT_MESSAGE_END,
        NATIVE_EVENT_ERROR,
        NATIVE_EVENT_CHAT_END,
    )

    assert NATIVE_EVENT_CHAT_START == "chat.start"
    assert NATIVE_EVENT_MODEL_LOAD_START == "model_load.start"
    assert NATIVE_EVENT_MODEL_LOAD_PROGRESS == "model_load.progress"
    assert NATIVE_EVENT_MODEL_LOAD_END == "model_load.end"
    assert NATIVE_EVENT_PROMPT_PROCESSING_START == "prompt_processing.start"
    assert NATIVE_EVENT_PROMPT_PROCESSING_PROGRESS == "prompt_processing.progress"
    assert NATIVE_EVENT_PROMPT_PROCESSING_END == "prompt_processing.end"
    assert NATIVE_EVENT_REASONING_START == "reasoning.start"
    assert NATIVE_EVENT_REASONING_DELTA == "reasoning.delta"
    assert NATIVE_EVENT_REASONING_END == "reasoning.end"
    assert NATIVE_EVENT_TOOL_CALL_START == "tool_call.start"
    assert NATIVE_EVENT_TOOL_CALL_ARGUMENTS == "tool_call.arguments"
    assert NATIVE_EVENT_TOOL_CALL_SUCCESS == "tool_call.success"
    assert NATIVE_EVENT_TOOL_CALL_FAILURE == "tool_call.failure"
    assert NATIVE_EVENT_MESSAGE_START == "message.start"
    assert NATIVE_EVENT_MESSAGE_DELTA == "message.delta"
    assert NATIVE_EVENT_MESSAGE_END == "message.end"
    assert NATIVE_EVENT_ERROR == "error"
    assert NATIVE_EVENT_CHAT_END == "chat.end"


@pytest.mark.unit
def test_native_sse_event_is_frozen():
    """Boundary-13: NativeSSEEvent is frozen — setting any attribute raises FrozenInstanceError."""
    from dataclasses import FrozenInstanceError

    event = NativeSSEEvent(event_type="chat.start", data={"model": "test"})

    with pytest.raises(FrozenInstanceError):
        event.event_type = "chat.end"  # type: ignore[misc]
