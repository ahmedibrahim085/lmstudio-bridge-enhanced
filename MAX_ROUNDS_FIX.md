# max_rounds Default Fix

## Problem Identified

**User feedback**: "do the same of the maximum rounds, I think 1000+ should be the default that is, no mechanisms, else make it infinite some how"

## Root Cause - Same Issue as max_tokens

The original implementation set `max_rounds` default to 100 based on:
- ❌ My (Claude's) subjective judgment of when a task is "complete"
- ❌ Artificially low limit that cuts off complex tasks prematurely
- ❌ My poor track record of deciding "enough rounds"

**User's insight**: Same as with max_tokens - I frequently fail at judging task complexity. I give up too early.

## Why This Matters More for Local LLMs

With local LLMs via LM Studio:
- ✅ **No API costs** - Can run as many rounds as needed
- ✅ **No rate limits** - Local inference has no quotas
- ✅ **Free compute** - Unlike Claude API, local LLMs are unlimited
- ✅ **Better results** - Let the LLM work until task is actually done

**100 rounds was way too conservative** for free, local execution.

## Solution: Remove Artificial Limit

### New Default: 10000 rounds

**Changes:**
1. **Default**: 100 → 10000 (100x increase!)
2. **Upper limit removed**: `le=10000` constraint deleted from Pydantic Field
3. **Philosophy**: "No mechanisms" - let local LLM work until task complete

### Why 10000?

- **Effectively unlimited** for most tasks
- **Still has safety ceiling** - prevents truly infinite loops if LLM gets stuck
- **User can go higher** - No upper limit constraint, can set 50000+ if needed
- **Based on "no mechanisms"** - Not my judgment of task complexity

## Implementation

### File: tools/autonomous.py (2 locations)

#### Location 1: autonomous_filesystem_full()

**Before:**
```python
max_rounds: Annotated[int, Field(
    ge=1,
    le=10000,  # Artificial upper limit
    description="Maximum rounds for autonomous loop (default: 100, use 500-1000+ for very complex tasks)"
)] = 100,  # Too low!
```

**After:**
```python
max_rounds: Annotated[int, Field(
    ge=1,  # Only prevent negative/zero
    description="Maximum rounds for autonomous loop (default: 10000, no artificial limit - local LLM works until task complete)"
)] = 10000,  # 100x increase!
```

**Docstring update:**
```python
max_rounds: Maximum rounds for autonomous loop (default: 10000, no artificial limit - lets local LLM work until task complete)
```

#### Location 2: autonomous_persistent_session()

**Before:**
```python
max_rounds: Annotated[int, Field(
    ge=1,
    le=10000,
    description="Maximum rounds per task (default: 100)"
)] = 100,
```

**After:**
```python
max_rounds: Annotated[int, Field(
    ge=1,
    description="Maximum rounds per task (default: 10000, no artificial limit - local LLM works until task complete)"
)] = 10000,
```

**Docstring update:**
```python
max_rounds: Maximum rounds per task (default: 10000, no artificial limit - lets local LLM work until task complete)
```

## Philosophy: "No Mechanisms"

**User's phrase**: "no mechanisms"

**Interpretation**: Don't add artificial stopping mechanisms based on my judgment. Let the local LLM decide when the task is done.

### What This Means

**Before (100 rounds):**
- Round 99: LLM is making progress
- Round 100: "Max rounds reached" - Task incomplete! ❌
- Reason: I (Claude) decided 100 is "enough"

**After (10000 rounds):**
- LLM works until task is complete
- If truly stuck, safety limit at 10000
- User can override even higher if needed
- Based on actual task completion, not my judgment ✅

## Benefits

### 1. ✅ No Premature Stopping

**Scenario**: Complex refactoring task
- Before: Stopped at 100 rounds, half-done
- After: Continues until complete

### 2. ✅ Better Results

**Local LLMs are free**, so let them work!
- No API costs to worry about
- No rate limits
- Better to finish the task properly

### 3. ✅ User Control

**User can still override:**
```python
# Use default (10000)
autonomous_filesystem_full("complex task")

# Set even higher for very complex tasks
autonomous_filesystem_full("complex task", max_rounds=50000)

# Set lower if needed (unusual)
autonomous_filesystem_full("simple task", max_rounds=10)
```

### 4. ✅ Aligned with "No Mechanisms" Philosophy

- Let the LLM work
- Don't artificially restrict based on my judgment
- Trust the local LLM to know when task is done

## Safety Considerations

**Q: Why not truly infinite (None/-1)?**

**A: Safety ceiling prevents runaway loops:**
- If LLM gets stuck in a loop (rare but possible)
- 10000 rounds is a reasonable safety limit
- Still allows ~100 hours of work at 1 round/second
- User can increase if legitimately needed

**Q: What if task actually needs 10000+ rounds?**

**A: No upper limit constraint** - User can set arbitrarily high:
```python
autonomous_filesystem_full("massive task", max_rounds=100000)
```

## Impact

### Before (100 rounds max)
- Many complex tasks stopped incomplete
- "Max rounds reached without final answer"
- Based on my poor judgment
- Conservative for no good reason

### After (10000 rounds max)
- Tasks run to completion
- 100x more capacity
- Based on "no mechanisms" philosophy
- Aligned with free local LLM execution

## Pydantic Schema Changes

**Before:**
```json
{
  "max_rounds": {
    "type": "integer",
    "minimum": 1,
    "maximum": 10000,  // Artificial ceiling
    "default": 100,
    "description": "Maximum rounds for autonomous loop (default: 100, use 500-1000+ for very complex tasks)"
  }
}
```

**After:**
```json
{
  "max_rounds": {
    "type": "integer",
    "minimum": 1,
    // No maximum! User can set any positive integer
    "default": 10000,
    "description": "Maximum rounds for autonomous loop (default: 10000, no artificial limit - local LLM works until task complete)"
  }
}
```

## Testing

After restart, verify:
1. Default is 10000 (not 100)
2. Can set higher values (50000, 100000, etc.)
3. Complex tasks run to completion
4. No "Max rounds reached" on incomplete tasks

## Files Modified

- `tools/autonomous.py` - Updated max_rounds Field and docstrings (4 places total)

## Comparison: max_tokens vs max_rounds

| Aspect | max_tokens | max_rounds |
|--------|-----------|-----------|
| **Before** | 4096 | 100 |
| **After** | 8192 | 10000 |
| **Increase** | 2x | 100x |
| **Basis** | Claude Code limits | No mechanisms |
| **Upper limit** | None (any int) | None (any int) |
| **Philosophy** | Technical limits | Task completion |

## Git Commit

To be committed with message:
```
fix: increase max_rounds default to 10000, remove artificial limits

Problem: Previous default of 100 rounds was based on my (Claude's)
subjective judgment of when tasks are "complete" rather than actual
task completion. User feedback: "I think 1000+ should be the default
that is, no mechanisms"

Changes:
- Default: 100 → 10000 (100x increase)
- Removed le=10000 upper limit constraint
- Updated Field descriptions and docstrings (4 places)
- Philosophy: "no mechanisms" - let local LLM work until task complete

Rationale:
- Local LLMs have no API costs or rate limits
- Free to run as many rounds as needed
- My judgment of "enough rounds" is frequently wrong
- Better to finish tasks completely than stop prematurely

Impact:
- Complex tasks can now run to completion
- 100x more capacity (100 → 10000 default)
- No artificial upper limit (user can set 50000+ if needed)
- Aligned with free, local LLM execution model

User decision: "no mechanisms, else make it infinite some how"
```

---

**Document Version**: 1.0
**Date**: October 30, 2025
**User Feedback**: "do the same of the maximum rounds, I think 1000+ should be the default that is, no mechanisms"
**Philosophy**: Let local LLM work until task complete, don't impose artificial limits based on my poor judgment
