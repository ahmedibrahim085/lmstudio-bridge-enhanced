# Constants Documentation

## Overview

This document describes all configuration constants used throughout the lmstudio-bridge-enhanced MCP server. These constants replace hard-coded values to improve maintainability, clarity, and consistency.

## Location

All constants are defined in: **`llm/llm_client.py`** (lines 14-25)

## Constants Reference

### DEFAULT_LLM_TIMEOUT = 55

**Purpose:** Default timeout for all LLM API calls to LM Studio

**Value:** 55 seconds

**Rationale:**
- Claude Code has a hard 60-second timeout for MCP tool calls
- Cannot be bypassed (GitHub issues #7575, #245)
- 55 seconds provides 5-second safety margin
- Balances between giving LLM time and staying under Claude's limit

**Used By:**
- `LLMClient.chat_completion()` - Chat completions with tools
- `LLMClient.text_completion()` - Raw text completions
- `LLMClient.generate_embeddings()` - Vector embeddings generation
- `LLMClient.create_response()` - Stateful responses

**Research:**
- GitHub Issue #7575: "Claude code does not obey values of MCP_TIMEOUT longer than 60 seconds"
- GitHub Issue #245: "mcp client times out after 60 seconds (ignoring timeout option)"
- See: `TIMEOUT_LIMITATION.md` for complete analysis

**User Override:**
```python
# All methods accept timeout parameter
llm.chat_completion(messages, timeout=120)  # Custom timeout
```

---

### HEALTH_CHECK_TIMEOUT = 5

**Purpose:** Timeout for health check API calls

**Value:** 5 seconds

**Rationale:**
- Health checks should be fast
- If LM Studio not responding in 5s, it's not healthy
- No need for long timeout - this is a binary check (up/down)
- Separates "quick check" from "work timeout" (55s)

**Used By:**
- `LLMClient.health_check()` - Checks if LM Studio API is accessible

**Example:**
```python
if llm.health_check():  # Quick 5-second check
    print("LM Studio is running")
else:
    print("LM Studio is not accessible")
```

**Why Separate Constant:**
- Different timeout philosophy than LLM calls
- Health checks should fail fast
- Makes intent clear in code

---

### DEFAULT_AUTONOMOUS_ROUNDS = 10000

**Purpose:** Default max rounds for AutonomousLLMClient class

**Value:** 10000 rounds

**Rationale:**
- Consistency with main autonomous tools (`autonomous_filesystem_full`)
- "No mechanisms" philosophy - let LLM work until task complete
- Local LLMs are free (no API costs)
- Effectively unlimited for most tasks
- Still has safety ceiling to prevent runaway loops

**Used By:**
- `AutonomousLLMClient.__init__()` - Default max_rounds parameter

**History:**
- Originally: 5 rounds (too low!)
- Session fix: Updated to 10000 for consistency
- Based on user feedback: "no mechanisms, else make it infinite some how"

**Why 10000:**
- 100x increase from previous default (100)
- Effectively unlimited for realistic tasks
- Still prevents truly infinite loops
- User can override if needed

**User Override:**
```python
# Use default (10000)
client = AutonomousLLMClient()

# Or override
client = AutonomousLLMClient(max_rounds=50000)  # Very complex task
```

**Related:**
- See `MAX_ROUNDS_FIX.md` for complete rationale
- Main autonomous tools also use 10000 as default

---

## Design Principles

### 1. Single Source of Truth
All configuration values defined once, used everywhere.

**Bad (hard-coded):**
```python
response = requests.get(url, timeout=5)  # What does 5 mean?
# ... 50 lines later ...
response = requests.get(url2, timeout=5)  # Same value, repeated
```

**Good (constant):**
```python
response = requests.get(url, timeout=HEALTH_CHECK_TIMEOUT)
# ... 50 lines later ...
response = requests.get(url2, timeout=HEALTH_CHECK_TIMEOUT)  # Clear intent
```

### 2. Clear Intent
Constants have descriptive names that explain purpose.

**Comparison:**
- `timeout=5` - What kind of timeout? Why 5?
- `timeout=HEALTH_CHECK_TIMEOUT` - Aha! Health check, should be fast

### 3. Easy to Change
Change once, updates everywhere.

**Example:** If Claude Code fixes the 60-second bug:
```python
# Only one line to change!
DEFAULT_LLM_TIMEOUT = 120  # Can increase now
```

### 4. Documentation at Source
Constants documented where defined, with rationale.

---

## Migration from Hard-Coded Values

### Session History

**Commit: ac1cdef** - Created `DEFAULT_LLM_TIMEOUT`
- Replaced hard-coded `timeout=30` in 4 methods
- Based on Claude Code's 60-second MCP limit

**Commit: cd0ae18** - Created 2 additional constants
- `HEALTH_CHECK_TIMEOUT = 5` - Replaced hard-coded `timeout=5`
- `DEFAULT_AUTONOMOUS_ROUNDS = 10000` - Replaced hard-coded `max_rounds: int = 5`

**Commit: [This one]** - Cleaned up PoC/demo code
- Removed `test_autonomous_poc()` function (replaced by production tools)
- Removed `POC_MAX_ROUNDS = 5` constant (no longer needed)

### Before and After

#### Example 1: Health Check
**Before:**
```python
def health_check(self) -> bool:
    response = requests.get(self._get_endpoint("models"), timeout=5)
    return response.status_code == 200
```

**After:**
```python
def health_check(self) -> bool:
    response = requests.get(self._get_endpoint("models"), timeout=HEALTH_CHECK_TIMEOUT)
    return response.status_code == 200
```

**Benefits:**
- Clear intent: This is a health check timeout
- Easy to change: One constant to update
- Documented: See constant definition for rationale

#### Example 2: AutonomousLLMClient
**Before:**
```python
def __init__(self, llm_client=None, max_rounds: int = 5):
    self.max_rounds = max_rounds
```

**After:**
```python
def __init__(self, llm_client=None, max_rounds: int = DEFAULT_AUTONOMOUS_ROUNDS):
    self.max_rounds = max_rounds  # Default: 10000
```

**Benefits:**
- Consistent with main autonomous tools
- Follows "no mechanisms" philosophy
- 100x increase from 5 to 10000

---

## Related Documentation

### Timeout Constants
- **TIMEOUT_LIMITATION.md** - Complete analysis of Claude Code's 60s limit
- **SESSION_SUMMARY.md** - Overview of all session changes

### Round Constants
- **MAX_ROUNDS_FIX.md** - Why 10000 rounds for autonomous execution
- **SESSION_SUMMARY.md** - "No mechanisms" philosophy

### General
- **MAX_TOKENS_FIX.md** - Why 8192 tokens default
- **PYDANTIC_REFACTORING.md** - Validation best practices

---

## Best Practices

### When to Create a Constant

✅ **Create constant if:**
- Value used in multiple places
- Value has special meaning/rationale
- Value might need to change
- Makes intent clearer

❌ **Don't create constant if:**
- Standard API parameter default (e.g., `temperature=0.7`)
- User-facing parameter meant to be overridden
- Value used only once and self-explanatory

### Naming Conventions

**Pattern:** `[CATEGORY]_[PURPOSE]_[UNIT]`

**Examples:**
- `DEFAULT_LLM_TIMEOUT` - Default for LLM calls, timeout (seconds implied)
- `HEALTH_CHECK_TIMEOUT` - For health checks, timeout (seconds implied)
- `DEFAULT_AUTONOMOUS_ROUNDS` - Default for autonomous execution, rounds

### Documentation Required

For each constant, document:
1. **Purpose** - What is it for?
2. **Value** - What is the value and why?
3. **Rationale** - Why this value specifically?
4. **Used By** - Which functions/classes use it?
5. **Research** (if applicable) - Links to issues, docs, etc.

---

## Future Considerations

### Potential New Constants

**If we find more hard-coded values:**
- Review if they meet "when to create constant" criteria
- Follow naming conventions
- Add to this document
- Update code to use constant

### Configuration File

**Future improvement:** Move constants to config file
```python
# config.py
class TimeoutConfig:
    DEFAULT_LLM = 55
    HEALTH_CHECK = 5

class RoundsConfig:
    AUTONOMOUS_DEFAULT = 10000
```

**Benefits:**
- Centralized configuration
- Could load from JSON/YAML
- Environment variable overrides

**Trade-off:**
- More complex setup
- Might be overkill for 3 constants
- Keep as-is for now, consider if we get 10+ constants

---

## Summary

| Constant | Value | Purpose | Used In |
|----------|-------|---------|---------|
| `DEFAULT_LLM_TIMEOUT` | 55s | Main LLM API timeout | 4 LLM methods |
| `HEALTH_CHECK_TIMEOUT` | 5s | Fast health check | health_check() |
| `DEFAULT_AUTONOMOUS_ROUNDS` | 10000 | Unlimited autonomous rounds | AutonomousLLMClient |

**All constants defined in:** `llm/llm_client.py:14-25`

**Philosophy:**
- Single source of truth
- Clear intent
- Easy to change
- Well-documented

---

**Document Version:** 1.0
**Date:** October 30, 2025
**Related Commits:** ac1cdef (timeout), [current] (health check, rounds)
**Session:** Fixing artificial limits based on technical constraints
