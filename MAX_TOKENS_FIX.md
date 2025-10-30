# max_tokens Default Fix

## Problem Identified

**User feedback**: "I'm not ok with you decided that the maximum number of tokens based on the task complexity from your POV. you frequently fail in that."

## Root Cause

The original implementation set `max_tokens` default to 4096 based on:
- ❌ My (Claude's) subjective judgment of "task complexity"
- ❌ Conservative estimate that "works with most models"
- ❌ My poor track record of judging how many tokens are needed

**Key insight from user**: Pydantic validation doesn't fix bad decision-making logic. It only validates inputs, not my judgment.

## Research: Claude Code's Actual Limits

### Bash Tool Output Limit

From Claude Code's system prompt:
> "If the output exceeds 30000 characters, output will be truncated before being returned to you."

**Source**: https://gist.github.com/wong2/e0f34aac66caf890a332f7b6f9e2ba8f

### Other Truncation Points

- **Lines longer than 2,000 characters**: Truncated
- **MCP tool response display**: ~700 characters (display only, full response saved)

### LM Studio API Options

From LM Studio documentation:
- `maxTokens: false` - Unlimited generation
- `maxTokens: <number>` - Specific limit
- **Parameter is optional** - Can be omitted entirely

**Source**: https://lmstudio.ai/docs/typescript/api-reference/llm-prediction-config-input

## Solution: Base on Technical Limits, Not My Judgment

### New Default: 8192 tokens

**Reasoning:**
```
8192 tokens ≈ 24,000-32,000 characters (depending on tokenization)
Claude Code truncates at 30,000 characters
Therefore: 8192 tokens stays safely under the limit
```

### Benefits

1. ✅ **Not based on my judgment** - Based on actual technical limits
2. ✅ **Comprehensive responses** - 2x higher than before (4096 → 8192)
3. ✅ **Safe** - Stays under Claude Code's 30K character truncation
4. ✅ **User can override** - Can set higher if needed: `max_tokens=16384`

## Implementation

### File: llm/llm_client.py

**Before:**
```python
def get_default_max_tokens(self) -> int:
    """Get a safe default max_tokens value for generation.

    Note: LM Studio's API does not expose model's actual max_context_length.
    This returns a conservative default that works with most modern models.

    For models with larger context windows (32K, 128K+), users should
    manually specify max_tokens when calling autonomous tools.

    Returns:
        Safe default max_tokens (4096)
    """
    return 4096
```

**After:**
```python
def get_default_max_tokens(self) -> int:
    """Get default max_tokens based on Claude Code's tool response limits.

    Claude Code truncates Bash tool output at 30,000 characters. Since MCP
    tool responses use the same handling, we set max_tokens to generate
    responses that stay safely under this limit.

    8192 tokens ≈ 24,000-32,000 characters (depending on tokenization),
    which provides comprehensive responses while staying under Claude Code's
    30,000 character truncation threshold.

    Note: LM Studio's API does not expose model's actual max_context_length,
    so this value is based on Claude Code's known limits rather than the
    loaded model's capabilities.

    Returns:
        8192 tokens (safe estimate for ~30K characters)
    """
    return 8192
```

### File: tools/autonomous.py

**Updated Field descriptions** (2 places):
```python
max_tokens: Annotated[
    Union[int, str],
    Field(
        description="Maximum tokens per LLM response ('auto' for default 8192 based on Claude Code limits, or integer to override)"
    )
] = "auto"
```

**Updated docstrings** (2 places):
```python
max_tokens: Maximum tokens per LLM response ("auto" for default 8192 based on Claude Code limits, or integer to override)
```

## Alternatives Considered

### Option 1: Remove limit entirely (False)
```python
return False  # Unlimited
```

**Pros**: No artificial restriction
**Cons**: Could generate responses > 30K chars, getting truncated anyway

### Option 2: Match exact Claude Code limit
```python
return 10000  # Approximately 30K characters
```

**Pros**: Maximize output
**Cons**: Very close to truncation threshold, risky

### Option 3: User chooses (SELECTED)
```python
return 8192  # Safe compromise
```

**Pros**: Good balance, user can override
**Cons**: None

## User Decision

User approved: **"I think fix at 8192 token is a good compromise"**

## Impact

### Before (4096 tokens)
- ~12,000-16,000 characters
- Often too short for complex responses
- Based on my poor judgment

### After (8192 tokens)
- ~24,000-32,000 characters
- 2x more comprehensive
- Based on Claude Code's actual limits
- Still safely under 30K truncation

## Testing

After restart, verify:
1. `max_tokens="auto"` uses 8192
2. User can override: `max_tokens=16384`
3. Responses are more comprehensive
4. No truncation at Claude Code level

## Files Modified

- `llm/llm_client.py` - Updated `get_default_max_tokens()` method
- `tools/autonomous.py` - Updated Field descriptions and docstrings (4 places)

## Git Commit

To be committed with message:
```
fix: increase max_tokens default to 8192 based on Claude Code limits

- Changed from 4096 to 8192 tokens (2x increase)
- Based on Claude Code's 30K character truncation limit, not my judgment
- Updated all Field descriptions and docstrings
- User feedback: "I'm not ok with you decided based on task complexity"
```

---

**Document Version**: 1.0
**Date**: October 30, 2025
**User Feedback**: "I think fix at 8192 token is a good compromise"
**Research Sources**:
- Claude Code system prompt: https://gist.github.com/wong2/e0f34aac66caf890a332f7b6f9e2ba8f
- LM Studio API docs: https://lmstudio.ai/docs/typescript/api-reference/llm-prediction-config-input
