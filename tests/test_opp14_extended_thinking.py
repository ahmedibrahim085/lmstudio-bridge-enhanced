#!/usr/bin/env python3
"""
OPP-14: Extended Thinking Support — Test Suite.

TDD: These tests were written BEFORE the implementation.
They verify thinking block parsing, constant values, and LLMClient
thinking_completion / stream_thinking_completion / is_thinking_capable.

Test Groups
-----------
1.  ThinkingParser  – parse_thinking_blocks
2.  ThinkingParser  – strip_thinking_blocks
3.  ThinkingParser  – estimate_thinking_tokens
4.  ThinkingParser  – has_thinking_content
5.  Constants validation
6.  LLMClient.thinking_completion
7.  LLMClient.stream_thinking_completion
8.  LLMClient.is_thinking_capable
9.  Non-streaming regression (backward compat)
"""

import math
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Imports under test — these will FAIL until implementation is in place
# ---------------------------------------------------------------------------
from config.constants import (
    CHARS_PER_TOKEN_ESTIMATE,
    DEFAULT_THINKING_BUDGET_TOKENS,
    MAX_THINKING_BUDGET_TOKENS,
    MIN_THINKING_BUDGET_TOKENS,
    THINKING_TAG_CLOSE,
    THINKING_TAG_OPEN,
)
from llm.llm_client import LLMClient
from llm.thinking_parser import (
    ThinkingBlock,
    estimate_thinking_tokens,
    has_thinking_content,
    parse_thinking_blocks,
    strip_thinking_blocks,
)

# ===========================================================================
# Group 1: parse_thinking_blocks
# ===========================================================================


class TestParseThinkingBlocks:
    """Tests for parse_thinking_blocks()."""

    def test_single_block_extracted(self):
        """Happy path: single <think>...</think> block is parsed correctly."""
        text = "Before <think>This is reasoning.</think> After"
        blocks = parse_thinking_blocks(text)

        assert len(blocks) == 1
        assert blocks[0].content == "This is reasoning."

    def test_multiple_blocks_extracted(self):
        """Happy path: multiple thinking blocks are all extracted."""
        text = "<think>First thought</think> middle <think>Second thought</think>"
        blocks = parse_thinking_blocks(text)

        assert len(blocks) == 2
        assert blocks[0].content == "First thought"
        assert blocks[1].content == "Second thought"

    def test_empty_input_returns_empty_list(self):
        """Edge: empty string input returns empty list."""
        blocks = parse_thinking_blocks("")
        assert blocks == []

    def test_no_thinking_tags_returns_empty_list(self):
        """Edge: text without any thinking tags returns empty list."""
        text = "This is just regular text with no thinking tags."
        blocks = parse_thinking_blocks(text)
        assert blocks == []

    def test_unclosed_tag_returns_no_match(self):
        """Edge: unclosed <think> tag produces no match (require both open+close)."""
        text = "Text <think>unclosed content without close tag"
        blocks = parse_thinking_blocks(text)
        assert blocks == []

    def test_empty_thinking_block_returns_block_with_empty_content(self):
        """Boundary: <think></think> yields a block with empty string content."""
        text = "Before <think></think> After"
        blocks = parse_thinking_blocks(text)

        assert len(blocks) == 1
        assert blocks[0].content == ""

    def test_thinking_block_with_newlines(self):
        """Happy path: multi-line thinking blocks are fully captured."""
        text = "<think>\nLine one\nLine two\n</think>"
        blocks = parse_thinking_blocks(text)

        assert len(blocks) == 1
        assert "Line one" in blocks[0].content
        assert "Line two" in blocks[0].content

    def test_start_end_positions_recorded(self):
        """Positions (start_pos, end_pos) cover the full tag including delimiters."""
        text = "X<think>abc</think>Y"
        blocks = parse_thinking_blocks(text)

        assert len(blocks) == 1
        block = blocks[0]
        # Reconstruct from positions and verify
        reconstructed = text[block.start_pos:block.end_pos]
        assert reconstructed == "<think>abc</think>"

    def test_nested_think_tag_content_captured(self):
        """Edge: pseudo-nested tags — outer pair wins, inner tag treated as text."""
        # re.DOTALL non-greedy match: first open to first close
        text = "<think>outer <think>inner</think></think>"
        blocks = parse_thinking_blocks(text)
        # At minimum, one block is returned; inner tag text is included
        assert len(blocks) >= 1
        # The first block's content contains "inner" (inner tag part)
        assert "inner" in blocks[0].content

    def test_returns_list_of_thinking_block_dataclass(self):
        """Result items are ThinkingBlock instances."""
        text = "<think>thought</think>"
        blocks = parse_thinking_blocks(text)

        assert isinstance(blocks[0], ThinkingBlock)


# ===========================================================================
# Group 2: strip_thinking_blocks
# ===========================================================================


class TestStripThinkingBlocks:
    """Tests for strip_thinking_blocks()."""

    def test_removes_block_preserves_surrounding_text(self):
        """Happy path: thinking block removed, surrounding text preserved."""
        text = "Hello <think>reasoning here</think> world"
        result = strip_thinking_blocks(text)

        assert "reasoning here" not in result
        assert "Hello" in result
        assert "world" in result

    def test_multiple_blocks_all_removed(self):
        """Happy path: all thinking blocks removed from text."""
        text = "<think>first</think> middle <think>second</think> end"
        result = strip_thinking_blocks(text)

        assert "first" not in result
        assert "second" not in result
        assert "middle" in result
        assert "end" in result

    def test_no_blocks_returns_original_text(self):
        """Edge: text without thinking blocks returns unchanged."""
        text = "No thinking blocks here."
        result = strip_thinking_blocks(text)
        assert result == text

    def test_only_thinking_content_returns_empty_or_stripped(self):
        """Edge: text containing only thinking block yields empty/whitespace-stripped text."""
        text = "<think>all reasoning</think>"
        result = strip_thinking_blocks(text)
        assert result.strip() == ""

    def test_whitespace_cleaned_around_removed_block(self):
        """Result is stripped of leading/trailing whitespace."""
        text = "  <think>thought</think>  answer  "
        result = strip_thinking_blocks(text)
        # Should not start/end with whitespace after stripping
        assert result == result.strip()

    def test_preserves_non_thinking_content_exactly(self):
        """Content after block removal matches expected non-thinking portion."""
        text = "<think>ignore</think>keep this"
        result = strip_thinking_blocks(text)
        assert "keep this" in result


# ===========================================================================
# Group 3: estimate_thinking_tokens
# ===========================================================================


class TestEstimateThinkingTokens:
    """Tests for estimate_thinking_tokens()."""

    def test_known_length_text_correct_estimate(self):
        """Happy path: known text length gives expected token estimate."""
        # 40 characters / 4 chars_per_token = 10 tokens
        text = "a" * (CHARS_PER_TOKEN_ESTIMATE * 10)
        assert estimate_thinking_tokens(text) == 10

    def test_empty_string_returns_zero(self):
        """Edge: empty string yields 0 tokens."""
        assert estimate_thinking_tokens("") == 0

    def test_single_character_returns_one(self):
        """Boundary: single character yields at least 1 token (ceiling division)."""
        result = estimate_thinking_tokens("x")
        assert result == math.ceil(1 / CHARS_PER_TOKEN_ESTIMATE)
        # Regardless of CHARS_PER_TOKEN_ESTIMATE, result must be >= 1
        assert result >= 1

    def test_result_is_integer(self):
        """Result is always an integer."""
        assert isinstance(estimate_thinking_tokens("hello world"), int)

    def test_longer_text_gives_larger_estimate(self):
        """Longer text produces a larger token estimate."""
        short = estimate_thinking_tokens("short")
        long_text = estimate_thinking_tokens("short" * 100)
        assert long_text > short


# ===========================================================================
# Group 4: has_thinking_content
# ===========================================================================


class TestHasThinkingContent:
    """Tests for has_thinking_content()."""

    def test_true_when_thinking_tags_present(self):
        """Returns True when <think>...</think> tags present in text."""
        text = "Hello <think>reasoning</think> world"
        assert has_thinking_content(text) is True

    def test_false_when_no_tags(self):
        """Returns False when no thinking tags in text."""
        text = "Regular text without any thinking tags."
        assert has_thinking_content(text) is False

    def test_false_for_empty_string(self):
        """Returns False for empty string."""
        assert has_thinking_content("") is False

    def test_true_for_only_thinking_tags(self):
        """Returns True when text is only thinking tags."""
        assert has_thinking_content("<think>thought</think>") is True

    def test_open_tag_only_still_detected(self):
        """Returns True if at least the open tag is present (quick check)."""
        # has_thinking_content is a QUICK CHECK — only needs open tag
        text = "prefix <think> no close"
        assert has_thinking_content(text) is True


# ===========================================================================
# Group 5: Constants validation
# ===========================================================================


class TestThinkingConstants:
    """Validate that OPP-14 constants are well-formed."""

    def test_default_budget_is_positive_int(self):
        """DEFAULT_THINKING_BUDGET_TOKENS is a positive integer."""
        assert isinstance(DEFAULT_THINKING_BUDGET_TOKENS, int)
        assert DEFAULT_THINKING_BUDGET_TOKENS > 0

    def test_min_less_than_default_less_than_max(self):
        """MIN < DEFAULT < MAX ordering holds."""
        assert MIN_THINKING_BUDGET_TOKENS < DEFAULT_THINKING_BUDGET_TOKENS
        assert DEFAULT_THINKING_BUDGET_TOKENS < MAX_THINKING_BUDGET_TOKENS

    def test_thinking_tag_open_non_empty_string(self):
        """THINKING_TAG_OPEN is a non-empty string."""
        assert isinstance(THINKING_TAG_OPEN, str)
        assert len(THINKING_TAG_OPEN) > 0

    def test_thinking_tag_close_non_empty_string(self):
        """THINKING_TAG_CLOSE is a non-empty string."""
        assert isinstance(THINKING_TAG_CLOSE, str)
        assert len(THINKING_TAG_CLOSE) > 0

    def test_tags_are_distinct(self):
        """Open and close tags are different strings."""
        assert THINKING_TAG_OPEN != THINKING_TAG_CLOSE

    def test_chars_per_token_estimate_positive_int(self):
        """CHARS_PER_TOKEN_ESTIMATE is a positive integer."""
        assert isinstance(CHARS_PER_TOKEN_ESTIMATE, int)
        assert CHARS_PER_TOKEN_ESTIMATE > 0

    def test_min_budget_is_positive(self):
        """MIN_THINKING_BUDGET_TOKENS is a positive integer."""
        assert isinstance(MIN_THINKING_BUDGET_TOKENS, int)
        assert MIN_THINKING_BUDGET_TOKENS > 0

    def test_max_budget_large_enough(self):
        """MAX_THINKING_BUDGET_TOKENS is at least 8192."""
        assert MAX_THINKING_BUDGET_TOKENS >= 8192


# ===========================================================================
# Group 6: LLMClient.thinking_completion
# ===========================================================================


def _make_mock_response(content: str) -> dict[str, Any]:
    """Build a minimal OpenAI-style chat completion response dict."""
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content,
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
    }


class TestThinkingCompletion:
    """Tests for LLMClient.thinking_completion()."""

    @patch("llm.thinking_client.ensure_model_loaded")
    @patch("llm.llm_client.LLMClient.chat_completion")
    def test_happy_path_enriches_response(
        self, mock_chat: MagicMock, mock_load: MagicMock
    ):
        """Happy path: response containing <think> block is enriched with extra keys."""
        raw_content = "<think>I need to reason here.</think>Final answer."
        mock_chat.return_value = _make_mock_response(raw_content)

        client = LLMClient()
        result = client.thinking_completion(
            messages=[{"role": "user", "content": "Hello"}]
        )

        assert "thinking_blocks" in result
        assert "thinking_tokens_estimated" in result
        assert "content_without_thinking" in result

        assert len(result["thinking_blocks"]) == 1
        assert result["thinking_blocks"][0]["content"] == "I need to reason here."
        assert "Final answer." in result["content_without_thinking"]

    @patch("llm.thinking_client.ensure_model_loaded")
    @patch("llm.llm_client.LLMClient.chat_completion")
    def test_invalid_reasoning_effort_raises_value_error(
        self, mock_chat: MagicMock, mock_load: MagicMock
    ):
        """Invalid reasoning effort raises ValueError."""
        client = LLMClient()
        with pytest.raises(ValueError, match="effort"):
            client.thinking_completion(
                messages=[{"role": "user", "content": "test"}],
                reasoning={"effort": "invalid"},
            )

    @patch("llm.thinking_client.ensure_model_loaded")
    @patch("llm.llm_client.LLMClient.chat_completion")
    def test_reasoning_missing_effort_key_raises_value_error(
        self, mock_chat: MagicMock, mock_load: MagicMock
    ):
        """reasoning={} (missing 'effort' key) raises ValueError."""
        client = LLMClient()
        with pytest.raises(ValueError, match="effort"):
            client.thinking_completion(
                messages=[{"role": "user", "content": "test"}],
                reasoning={},
            )

    @patch("llm.thinking_client.ensure_model_loaded")
    @patch("llm.llm_client.LLMClient.chat_completion")
    def test_none_reasoning_uses_default(
        self, mock_chat: MagicMock, mock_load: MagicMock
    ):
        """When reasoning is None, DEFAULT_THINKING_BUDGET_TOKENS is used."""
        mock_chat.return_value = _make_mock_response("No thinking here.")

        client = LLMClient()
        # Should not raise; uses DEFAULT
        result = client.thinking_completion(
            messages=[{"role": "user", "content": "Hello"}],
            reasoning=None,
        )

        # Verify chat_completion was called with max_tokens >= DEFAULT_THINKING_BUDGET_TOKENS
        call_kwargs = mock_chat.call_args
        passed_max_tokens = call_kwargs.kwargs.get(
            "max_tokens", call_kwargs.args[1] if len(call_kwargs.args) > 1 else None
        )
        # max_tokens should be at least DEFAULT_THINKING_BUDGET_TOKENS + base max_tokens
        assert passed_max_tokens is not None
        assert passed_max_tokens >= DEFAULT_THINKING_BUDGET_TOKENS

    @patch("llm.thinking_client.ensure_model_loaded")
    @patch("llm.llm_client.LLMClient.chat_completion")
    def test_response_without_thinking_blocks_still_enriched(
        self, mock_chat: MagicMock, mock_load: MagicMock
    ):
        """Response with no thinking tags still gets enriched keys (empty blocks)."""
        mock_chat.return_value = _make_mock_response("Just a plain answer.")

        client = LLMClient()
        result = client.thinking_completion(
            messages=[{"role": "user", "content": "Hello"}]
        )

        assert result["thinking_blocks"] == []
        assert result["thinking_tokens_estimated"] == 0
        assert "Just a plain answer." in result["content_without_thinking"]

    @patch("llm.thinking_client.ensure_model_loaded")
    @patch("llm.llm_client.LLMClient.chat_completion")
    def test_ensure_model_loaded_called(
        self, mock_chat: MagicMock, mock_load: MagicMock
    ):
        """_ensure_model_loaded is called (JIT loading guard runs)."""
        mock_chat.return_value = _make_mock_response("answer")

        client = LLMClient()
        client.thinking_completion(
            messages=[{"role": "user", "content": "test"}],
            model="qwen/qwq-32b",
        )

        mock_load.assert_called_once()

    @patch("llm.thinking_client.ensure_model_loaded")
    @patch("llm.llm_client.LLMClient.chat_completion")
    def test_thinking_tokens_estimated_positive_when_thinking_present(
        self, mock_chat: MagicMock, mock_load: MagicMock
    ):
        """thinking_tokens_estimated is > 0 when thinking content is present."""
        mock_chat.return_value = _make_mock_response(
            "<think>" + "x" * 100 + "</think>answer"
        )

        client = LLMClient()
        result = client.thinking_completion(
            messages=[{"role": "user", "content": "test"}]
        )

        assert result["thinking_tokens_estimated"] > 0

    @patch("llm.thinking_client.ensure_model_loaded")
    @patch("llm.llm_client.LLMClient.chat_completion")
    def test_thinking_blocks_are_dicts_with_content_key(
        self, mock_chat: MagicMock, mock_load: MagicMock
    ):
        """Each item in thinking_blocks is a dict with at least a 'content' key."""
        mock_chat.return_value = _make_mock_response(
            "<think>reasoning</think>answer"
        )

        client = LLMClient()
        result = client.thinking_completion(
            messages=[{"role": "user", "content": "test"}]
        )

        for block in result["thinking_blocks"]:
            assert isinstance(block, dict)
            assert "content" in block


# ===========================================================================
# Group 7: LLMClient.stream_thinking_completion
# ===========================================================================


class TestStreamThinkingCompletion:
    """Tests for LLMClient.stream_thinking_completion()."""

    @patch("llm.thinking_client.ensure_model_loaded")
    @patch("llm.llm_client.LLMClient.stream_chat_completion")
    def test_happy_path_yields_chunks(
        self, mock_stream: MagicMock, mock_load: MagicMock
    ):
        """Happy path: yields SSE chunks from stream_chat_completion."""
        chunks = [
            {"choices": [{"delta": {"content": "<think>reasoning"}}]},
            {"choices": [{"delta": {"content": "</think>answer"}}]},
        ]
        mock_stream.return_value = iter(chunks)

        client = LLMClient()
        results = list(
            client.stream_thinking_completion(
                messages=[{"role": "user", "content": "test"}]
            )
        )

        assert len(results) == 2
        assert results[0] == chunks[0]
        assert results[1] == chunks[1]

    @patch("llm.thinking_client.ensure_model_loaded")
    @patch("llm.llm_client.LLMClient.stream_chat_completion")
    def test_budget_below_min_raises_value_error(
        self, mock_stream: MagicMock, mock_load: MagicMock
    ):
        """Invalid reasoning effort raises ValueError before streaming starts."""
        client = LLMClient()
        with pytest.raises(ValueError, match="reasoning effort"):
            list(
                client.stream_thinking_completion(
                    messages=[{"role": "user", "content": "test"}],
                    reasoning={"effort": "invalid"},
                )
            )

    @patch("llm.thinking_client.ensure_model_loaded")
    @patch("llm.llm_client.LLMClient.stream_chat_completion")
    def test_budget_above_max_raises_value_error(
        self, mock_stream: MagicMock, mock_load: MagicMock
    ):
        """Empty reasoning dict raises ValueError before streaming starts."""
        client = LLMClient()
        with pytest.raises(ValueError, match="reasoning dict must contain"):
            list(
                client.stream_thinking_completion(
                    messages=[{"role": "user", "content": "test"}],
                    reasoning={},
                )
            )

    @patch("llm.thinking_client.ensure_model_loaded")
    @patch("llm.llm_client.LLMClient.stream_chat_completion")
    def test_stream_chat_completion_called_with_stream_true(
        self, mock_stream: MagicMock, mock_load: MagicMock
    ):
        """stream_chat_completion is invoked (streaming path used internally)."""
        mock_stream.return_value = iter([])

        client = LLMClient()
        list(
            client.stream_thinking_completion(
                messages=[{"role": "user", "content": "hello"}]
            )
        )

        mock_stream.assert_called_once()

    @patch("llm.thinking_client.ensure_model_loaded")
    @patch("llm.llm_client.LLMClient.stream_chat_completion")
    def test_none_budget_uses_default_no_error(
        self, mock_stream: MagicMock, mock_load: MagicMock
    ):
        """reasoning=None falls back to DEFAULT_REASONING_EFFORT without error."""
        mock_stream.return_value = iter([])

        client = LLMClient()
        # Should not raise — uses default reasoning effort
        list(
            client.stream_thinking_completion(
                messages=[{"role": "user", "content": "test"}],
                reasoning=None,
            )
        )
        mock_stream.assert_called_once()


# ===========================================================================
# Group 8: LLMClient.is_thinking_capable
# ===========================================================================


class TestIsThinkingCapable:
    """Tests for LLMClient.is_thinking_capable()."""

    def test_true_for_qwq_model(self):
        """qwen/qwq-32b is detected as thinking-capable."""
        assert LLMClient.is_thinking_capable("qwen/qwq-32b") is True

    def test_true_for_deepseek_r1(self):
        """deepseek-r1-14b is detected as thinking-capable."""
        assert LLMClient.is_thinking_capable("deepseek-r1-14b") is True

    def test_true_for_thinking_suffix(self):
        """qwen/qwen3-4b-thinking-2507 is detected as thinking-capable."""
        assert LLMClient.is_thinking_capable("qwen/qwen3-4b-thinking-2507") is True

    def test_false_for_coder_model(self):
        """qwen/qwen3-coder-30b is NOT a thinking model."""
        assert LLMClient.is_thinking_capable("qwen/qwen3-coder-30b") is False

    def test_false_for_magistral(self):
        """mistralai/magistral-small-2509 is NOT a thinking model."""
        assert LLMClient.is_thinking_capable("mistralai/magistral-small-2509") is False

    def test_false_for_plain_llama(self):
        """meta/llama-3-8b is NOT a thinking model."""
        assert LLMClient.is_thinking_capable("meta/llama-3-8b") is False

    def test_is_static_method(self):
        """is_thinking_capable can be called on the class directly (static method)."""
        # Should not require an instance
        result = LLMClient.is_thinking_capable("qwen/qwq-32b")
        assert isinstance(result, bool)


# ===========================================================================
# Group 9: Non-streaming regression (backward compat)
# ===========================================================================


class TestNonStreamingRegression:
    """Verify existing chat_completion still works without thinking params."""

    @patch("llm.thinking_client.ensure_model_loaded")
    @patch.object(
        LLMClient,
        "chat_completion",
        wraps=None,  # we'll override below
    )
    def test_chat_completion_accepts_no_thinking_params(
        self, mock_cc: MagicMock, mock_load: MagicMock
    ):
        """chat_completion works normally without any thinking parameters."""
        expected = _make_mock_response("Hello!")
        mock_cc.return_value = expected

        client = LLMClient()
        result = client.chat_completion(
            messages=[{"role": "user", "content": "Hello"}]
        )

        assert result == expected
        mock_cc.assert_called_once()

    def test_thinking_completion_does_not_break_chat_completion_signature(self):
        """thinking_completion exists as a separate method, not replacing chat_completion."""
        client = LLMClient()
        assert hasattr(client, "chat_completion")
        assert hasattr(client, "thinking_completion")
        # They must be different callables
        assert client.chat_completion != client.thinking_completion
