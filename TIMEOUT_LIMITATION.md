# Timeout Limitation Documentation

## The Problem: Claude Code's 60-Second Hard Limit

### Technical Constraint

Claude Code has a **hard-coded 60-second timeout** for MCP tool calls that cannot be bypassed, despite configuration options.

**Evidence:**
- GitHub Issue #7575: "Claude code does not obey values of MCP_TIMEOUT longer than 60 seconds"
- GitHub Issue #245: "mcp client times out after 60 seconds (ignoring timeout option)"
- Tested: MCP_TIMEOUT=100000 configured, but fails after ~60,028ms

### Our Architecture

```
Claude Code → [60s hard limit] → Our MCP Server → [55s timeout] → LM Studio API
```

**Why 55 seconds?**
- Claude Code enforces ~60-second hard limit
- We set 55 seconds to stay safely under this limit
- Gives 5-second safety margin for network overhead

## Impact on Our MCP

### With New 8192 Token Default

**Token generation times (approximate):**
- **Small responses** (500 tokens): ~5-10 seconds ✅
- **Medium responses** (2000 tokens): ~20-30 seconds ✅
- **Large responses** (4000 tokens): ~40-50 seconds ✅
- **Very large responses** (8192 tokens): **60-120+ seconds** ❌ TIMEOUT!

### The Tradeoff

**We chose Option 4: Accept the Limitation**

1. ✅ **Set timeout to 55 seconds** (under Claude's limit)
2. ✅ **Accept that very large responses might timeout**
3. ✅ **Let users retry with lower max_tokens if needed**
4. ✅ **Document limitation clearly**

## Solution: DEFAULT_LLM_TIMEOUT Constant

### Implementation

```python
# llm/llm_client.py

# Default timeout for all LLM API calls
# Set to 55 seconds to stay safely under Claude Code's 60-second MCP timeout limit
# See: https://github.com/anthropics/claude-code/issues/7575
DEFAULT_LLM_TIMEOUT = 55
```

**Used in:**
- `chat_completion(timeout=DEFAULT_LLM_TIMEOUT)`
- `text_completion(timeout=DEFAULT_LLM_TIMEOUT)`
- `generate_embeddings(timeout=DEFAULT_LLM_TIMEOUT)`
- `create_response(timeout=DEFAULT_LLM_TIMEOUT)`

### Benefits

1. **Single source of truth** - Change once, updates everywhere
2. **Well-documented** - Comments explain the constraint
3. **Easy to adjust** - If Claude Code fixes the bug, change in one place
4. **Practical** - Works within real-world limitations

## User Guidance

### If You Hit Timeouts

**Symptom:**
```
Error: requests.exceptions.ReadTimeout: HTTPConnectionPool(host='localhost', port=1234):
Read timed out. (read timeout=55)
```

**Causes:**
1. Task is too complex (LLM taking >55 seconds)
2. max_tokens is too high (8192 tokens takes 60-120+ seconds)
3. LLM model is slow (larger models take longer)

**Solutions:**

#### Option 1: Reduce max_tokens (Recommended)
```python
# Instead of default 8192
autonomous_filesystem_full("complex task", max_tokens=4000)  # Faster
```

#### Option 2: Break Task Into Smaller Steps
```python
# Instead of one big task
autonomous_persistent_session([
    {"task": "Step 1: Read files"},
    {"task": "Step 2: Analyze data"},
    {"task": "Step 3: Generate report"}
])
```

#### Option 3: Try Configuring Claude Code (May Not Work)

Edit `~/.claude/settings.json`:
```json
{
  "env": {
    "MCP_TIMEOUT": "120000",
    "MCP_TOOL_TIMEOUT": "120000"
  }
}
```

**Note:** Due to bug #7575, this likely won't work, but worth trying.

## Research Sources

### MCP Protocol Specification
**URL:** https://modelcontextprotocol.io/specification/2025-06-18/basic/lifecycle

**Key Points:**
- Implementations SHOULD establish timeouts
- Timeouts SHOULD be configurable per-request
- Progress notifications MAY reset timeout clock
- Implementations SHOULD enforce maximum timeout regardless of progress

### Claude Code Issues

**Issue #7575:** "Claude code does not obey values of MCP_TIMEOUT longer than 60 seconds"
- https://github.com/anthropics/claude-code/issues/7575
- Confirmed: 60-second hard limit
- Configuration ignored

**Issue #245:** "mcp client times out after 60 seconds (ignoring timeout option)"
- https://github.com/modelcontextprotocol/typescript-sdk/issues/245
- TypeScript SDK has hard 60-second limit
- resetTimeoutOnProgress doesn't work

**Issue #470:** "use MCPClient resetTimeoutOnProgress=True to support long MCP tool calls"
- https://github.com/anthropics/claude-code/issues/470
- Proposed solution: progress notifications
- Not yet implemented

**Issue #5615:** "Complete Claude Code Timeout Configuration Guide"
- https://github.com/anthropics/claude-code/issues/5615
- Working configuration for Bash timeouts
- MCP timeouts still broken

## Alternative Approaches Considered

### Approach 1: Increase to 120 Seconds (Rejected)
**Pro:** Would support 8192 token responses
**Con:** Claude Code kills at 60s anyway - pointless

### Approach 2: Dynamic Timeout Based on max_tokens (Rejected)
```python
timeout = max(60, max_tokens // 50)  # Scale with tokens
```
**Pro:** Adapts to response size
**Con:** Still hits Claude's 60s limit

### Approach 3: Implement Progress Reporting (Future)
**Pro:** Could bypass 60s limit (per MCP spec)
**Con:** TypeScript SDK bug makes this not work
**Status:** Wait for upstream fix

### Approach 4: Accept Limitation (SELECTED)
**Pro:** Honest, practical, works today
**Con:** Very large responses (8192 tokens) may timeout
**Decision:** Best option available

## Recommendations

### For Users

1. **Default works well** for most tasks (up to ~4000 tokens)
2. **Reduce max_tokens** if you hit timeouts
3. **Break large tasks** into smaller steps
4. **Be patient** - local LLMs are slower than APIs

### For Developers

1. **Don't increase timeout** above 55 seconds (pointless due to Claude Code limit)
2. **Consider progress reporting** when upstream bug is fixed
3. **Document timeouts** in error messages
4. **Guide users** to reduce max_tokens on timeout

## Future Improvements

### When Claude Code Fixes Bug #7575

```python
# Can increase to support full 8192 token responses
DEFAULT_LLM_TIMEOUT = 120  # 2 minutes
```

### When Progress Reporting Works

```python
# Implement progress notifications to reset timeout
# See: https://github.com/anthropics/claude-code/issues/470
```

### Alternative: Streaming Responses

```python
# Stream responses token-by-token
# Reset timeout on each chunk
# Requires LM Studio streaming support
```

## Summary

**Current State:**
- **Timeout:** 55 seconds (safely under Claude's 60s limit)
- **max_tokens:** 8192 (may timeout on very large responses)
- **max_rounds:** 10000 (no artificial limit)

**Philosophy:**
- Accept technical limitations we cannot control
- Optimize within constraints
- Provide clear user guidance
- Document workarounds

**User Impact:**
- ✅ Most tasks work perfectly (< 4000 tokens)
- ⚠️ Very large responses (8192 tokens) may timeout
- ✅ Users can easily reduce max_tokens if needed
- ✅ Clear error messages and guidance

---

**Document Version:** 1.0
**Date:** October 30, 2025
**Decision:** Option 4 - Accept limitation, set timeout to 55 seconds
**Status:** Implemented in commit (pending)
**Reference:** llm/llm_client.py:17 (DEFAULT_LLM_TIMEOUT constant)
