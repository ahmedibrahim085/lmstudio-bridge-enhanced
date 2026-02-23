#!/usr/bin/env python3
"""
OPP-14: Extended Thinking Parser.

Utilities for extracting and processing <think>...</think> blocks emitted
by reasoning-capable models (QwQ, DeepSeek-R1, o1-style, etc.).

The parser treats thinking blocks as first-class objects so callers can:
- Inspect the model's chain-of-thought reasoning
- Strip it from the visible output
- Estimate how many tokens were spent on reasoning

Usage
-----
    from llm.thinking_parser import (
        parse_thinking_blocks,
        strip_thinking_blocks,
        estimate_thinking_tokens,
        has_thinking_content,
    )

    response_text = "<think>I should reason carefully...</think>Final answer."

    blocks = parse_thinking_blocks(response_text)
    clean  = strip_thinking_blocks(response_text)
    tokens = estimate_thinking_tokens(blocks[0].content)
"""

import math
import re
from dataclasses import dataclass

from config.constants import (
    CHARS_PER_TOKEN_ESTIMATE,
    THINKING_TAG_CLOSE,
    THINKING_TAG_OPEN,
)

# Pre-compiled pattern: matches <think>...</think> with DOTALL (non-greedy)
# Non-greedy (.*?) ensures we get the FIRST close tag, not the last one.
_THINKING_PATTERN = re.compile(
    re.escape(THINKING_TAG_OPEN) + r"(.*?)" + re.escape(THINKING_TAG_CLOSE),
    re.DOTALL,
)


@dataclass
class ThinkingBlock:
    """A single <think>...</think> block extracted from model output.

    Attributes:
        content:   Raw text content between the open and close tags.
        start_pos: Character index in the source text where the open tag begins.
        end_pos:   Character index in the source text immediately after the close tag.
    """

    content: str
    start_pos: int
    end_pos: int


def parse_thinking_blocks(text: str) -> list[ThinkingBlock]:
    """Extract all <think>...</think> blocks from *text*.

    Uses a non-greedy match so that multiple independent blocks are handled
    correctly.  Unclosed tags produce no match.

    Args:
        text: Raw model output (may contain zero or more thinking blocks).

    Returns:
        Ordered list of :class:`ThinkingBlock` instances.  Empty list when
        *text* contains no thinking tags.

    Examples:
        >>> blocks = parse_thinking_blocks("<think>step 1</think>answer")
        >>> blocks[0].content
        'step 1'
    """
    if not text:
        return []

    blocks: list[ThinkingBlock] = []
    for match in _THINKING_PATTERN.finditer(text):
        blocks.append(
            ThinkingBlock(
                content=match.group(1),
                start_pos=match.start(),
                end_pos=match.end(),
            )
        )
    return blocks


def strip_thinking_blocks(text: str) -> str:
    """Remove all <think>...</think> blocks from *text* and strip whitespace.

    Args:
        text: Raw model output possibly containing thinking blocks.

    Returns:
        The text with all thinking blocks removed, stripped of leading/trailing
        whitespace.

    Examples:
        >>> strip_thinking_blocks("<think>reasoning</think>Final answer.")
        'Final answer.'
    """
    if not text:
        return text

    cleaned = _THINKING_PATTERN.sub("", text)
    return cleaned.strip()


def estimate_thinking_tokens(text: str) -> int:
    """Estimate token count for *text* using a characters-per-token heuristic.

    The estimate uses :data:`~config.constants.CHARS_PER_TOKEN_ESTIMATE`
    characters per token (ceiling division so even 1 character returns 1).

    Args:
        text: Text whose token count should be estimated (typically the
              content of one or more thinking blocks).

    Returns:
        Estimated integer token count.  Returns ``0`` for empty strings.

    Examples:
        >>> estimate_thinking_tokens("a" * 40)  # 40 / 4 = 10
        10
    """
    if not text:
        return 0
    return math.ceil(len(text) / CHARS_PER_TOKEN_ESTIMATE)


def has_thinking_content(text: str) -> bool:
    """Quick check: does *text* contain at least one thinking open tag?

    This is intentionally a fast prefix check rather than a full parse —
    suitable for branching logic before calling :func:`parse_thinking_blocks`.

    Args:
        text: Text to inspect.

    Returns:
        ``True`` if :data:`~config.constants.THINKING_TAG_OPEN` appears in
        *text*, ``False`` otherwise.
    """
    return THINKING_TAG_OPEN in text


__all__ = [
    "ThinkingBlock",
    "parse_thinking_blocks",
    "strip_thinking_blocks",
    "estimate_thinking_tokens",
    "has_thinking_content",
]
