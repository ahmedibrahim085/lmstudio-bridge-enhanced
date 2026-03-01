#!/usr/bin/env python3
"""Tests for OPP-23: Streaming Usage Tracking."""
from unittest.mock import MagicMock

import pytest

from llm.sse_parser import StreamUsage, parse_sse_stream_with_usage


def _make_response(lines: list[str]) -> MagicMock:
    """Create a mock requests.Response with iter_lines()."""
    resp = MagicMock()
    resp.iter_lines.return_value = iter(lines)
    return resp


class TestStreamUsageDataclass:
    """Tests for the StreamUsage frozen dataclass."""

    def test_stream_usage_fields(self):
        """Has prompt_tokens, completion_tokens, total_tokens."""
        usage = StreamUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30)
        assert usage.prompt_tokens == 10
        assert usage.completion_tokens == 20
        assert usage.total_tokens == 30

    def test_stream_usage_from_dict(self):
        """Constructs from a dict (like API response)."""
        data = {"prompt_tokens": 5, "completion_tokens": 15, "total_tokens": 20}
        usage = StreamUsage.from_dict(data)
        assert usage.prompt_tokens == 5
        assert usage.completion_tokens == 15
        assert usage.total_tokens == 20

    def test_stream_usage_defaults_zero(self):
        """Missing keys default to 0."""
        usage = StreamUsage.from_dict({})
        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0

    def test_stream_usage_frozen(self):
        """Immutable dataclass — can't assign to fields."""
        usage = StreamUsage(prompt_tokens=1, completion_tokens=2, total_tokens=3)
        with pytest.raises(AttributeError):
            usage.prompt_tokens = 99  # type: ignore[misc]


class TestParseSSEStreamWithUsage:
    """Tests for parse_sse_stream_with_usage() generator."""

    def test_captures_usage_from_final_chunk(self):
        """Usage in the last data chunk is captured as return value."""
        lines = [
            'data: {"choices":[{"delta":{"content":"Hello"}}]}',
            'data: {"choices":[],"usage":{"prompt_tokens":10,"completion_tokens":5,"total_tokens":15}}',
            "data: [DONE]",
        ]
        resp = _make_response(lines)

        gen = parse_sse_stream_with_usage(resp)
        chunks = []
        try:
            while True:
                chunks.append(next(gen))
        except StopIteration as e:
            usage = e.value

        assert len(chunks) == 2
        assert usage is not None
        assert usage.prompt_tokens == 10
        assert usage.completion_tokens == 5
        assert usage.total_tokens == 15

    def test_yields_all_content_chunks(self):
        """Content chunks are yielded normally."""
        lines = [
            'data: {"choices":[{"delta":{"content":"A"}}]}',
            'data: {"choices":[{"delta":{"content":"B"}}]}',
            'data: {"choices":[{"delta":{"content":"C"}}]}',
            "data: [DONE]",
        ]
        resp = _make_response(lines)

        chunks = list(parse_sse_stream_with_usage(resp))
        assert len(chunks) == 3

    def test_no_usage_returns_none(self):
        """No usage in stream → None return value."""
        lines = [
            'data: {"choices":[{"delta":{"content":"Hi"}}]}',
            "data: [DONE]",
        ]
        resp = _make_response(lines)

        gen = parse_sse_stream_with_usage(resp)
        chunks = []
        try:
            while True:
                chunks.append(next(gen))
        except StopIteration as e:
            usage = e.value

        assert len(chunks) == 1
        assert usage is None

    def test_done_sentinel_consumed(self):
        """[DONE] sentinel is NOT yielded as a chunk."""
        lines = [
            'data: {"choices":[]}',
            "data: [DONE]",
        ]
        resp = _make_response(lines)

        chunks = list(parse_sse_stream_with_usage(resp))
        assert len(chunks) == 1
        # None of the chunks should be the DONE sentinel
        for chunk in chunks:
            assert chunk != "[DONE]"

    def test_empty_stream_none_usage(self):
        """Empty stream → None usage."""
        resp = _make_response(["data: [DONE]"])

        gen = parse_sse_stream_with_usage(resp)
        chunks = []
        try:
            while True:
                chunks.append(next(gen))
        except StopIteration as e:
            usage = e.value

        assert len(chunks) == 0
        assert usage is None
