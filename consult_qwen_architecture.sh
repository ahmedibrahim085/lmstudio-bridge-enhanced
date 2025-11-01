#!/bin/bash
# Consultation script for Qwen models on autonomous logger architecture

PROMPT='You are an expert software architect reviewing a production-grade autonomous execution logger implementation.

## CONTEXT:
We are building an auto-logging system for autonomous LLM execution loops that:
- Automatically saves LLM responses + reasoning to files
- Runs on a separate async task (non-blocking)
- Has graceful fallback: Filesystem MCP → Native Python I/O → Disabled
- Saves logs to USER'\''s project directory (not developer'\''s directory)
- Configurable via environment variables

## KEY ARCHITECTURAL DECISIONS:

### 1. Log Location Strategy (Community-First Design):
```python
Priority order:
1. AUTONOMOUS_LOG_DIR env var (explicit user override)
2. Current working directory + /logs/autonomous_sessions (user'\''s project - DEFAULT)
3. ~/.cache/lmstudio-mcp-logs (fallback if project not writable)
```

**Question:** Is this the right priority order for community adoption? Should we change defaults?

### 2. Fallback Hierarchy:
```
Filesystem MCP (if available in .mcp.json)
  ↓ (if fails)
Native Python async I/O
  ↓ (if fails)
Disabled (with warning, never crash)
```

**Question:** Is this fallback order correct? Should we skip filesystem MCP entirely and just use native I/O?

### 3. Pure Async Architecture (NO threads):
```python
- asyncio.Queue (not threading.Queue)
- asyncio.create_task for worker (not threading.Thread)
- asyncio.to_thread for file I/O (not blocking writes)
- Never calls asyncio.run() (prevents RuntimeError)
```

**Question:** Is pure async the right choice? Or should we use threads with proper event loop handling?

### 4. Granular Log Modes:
```
- "full" → Complete response JSON (debugging)
- "reasoning" → Only reasoning field (analysis)
- "response" → Only content field (output review)
- "both" → Reasoning + response (DEFAULT)
- "off" → No logging (privacy)
```

**Question:** Are these the right modes? Missing any important use cases?

### 5. Security Measures:
```python
- Session ID sanitization (prevent path traversal)
- Log directory validation (prevent writing to /etc, /sys, etc.)
- Queue size limit (prevent memory exhaustion)
- Non-blocking put_nowait (never block autonomous loop)
```

**Question:** Are we missing any critical security considerations?

### 6. Truncation Strategy:
```python
- Default: NO truncation (show full reasoning in terminal)
- Opt-in: REASONING_MAX_LENGTH env var (e.g., 2000)
- Logs ALWAYS contain full reasoning (never truncated)
```

**Question:** Should we flip this? Default to truncated terminal output, opt-in to full?

## CORNER CASES IDENTIFIED (57+):
1. Filesystem MCP not in .mcp.json → Fallback to native I/O
2. Disk full → Catch OSError, log warning, disable logging
3. Path traversal attack (../../etc/passwd) → Session ID sanitization
4. Queue overflow → maxsize=1000, drop old entries
5. Non-JSON serializable objects → json.dumps(default=str)
6. MCP connection drops mid-session → Graceful degradation
7. Multiple concurrent sessions → Separate log directories per session
8. Windows vs Unix paths → Use pathlib.Path everywhere
... (50 more corner cases handled)

## YOUR TASK:

**Please provide ULTRA-DEEP analysis on:**

1. **Log Location Strategy:** Is current working directory + /logs/ the right default for community users? Or should we default to ~/.cache/?

2. **Fallback Hierarchy:** Should we even bother with filesystem MCP? Is the complexity worth it, or just use native I/O always?

3. **Pure Async vs Threads:** Is pure async architecture over-engineering? Would threads be simpler and just as good?

4. **Default Truncation:** Should terminal output be truncated by default (better UX) or full by default (more information)?

5. **Security:** What critical security issues are we missing? Path traversal prevention enough?

6. **Performance:** Will asyncio.Queue + asyncio.create_task actually prevent blocking? Or will file I/O still cause issues?

7. **Community Adoption:** From a user'\''s perspective, is this design intuitive? What would confuse users?

**Think ultra-deeply about trade-offs, edge cases, and production deployment scenarios. Challenge every assumption.**'

echo "========================================================================"
echo "CONSULTING: qwen/qwen3-4b-thinking-2507 (Deep Thinking)"
echo "========================================================================"
echo ""

curl -s http://localhost:1234/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"qwen/qwen3-4b-thinking-2507\",
    \"messages\": [{\"role\": \"user\", \"content\": $(echo "$PROMPT" | jq -Rs .)}],
    \"max_tokens\": 8000,
    \"temperature\": 0.7
  }" | jq -r '.choices[0].message |
    if .reasoning_content then
      "=== REASONING PROCESS ===\n" + .reasoning_content + "\n\n=== FINAL ANALYSIS ===\n" + .content
    else
      .content
    end'

echo ""
echo ""
echo "========================================================================"
echo "CONSULTING: qwen/qwen3-coder-30b (Code Review)"
echo "========================================================================"
echo ""

curl -s http://localhost:1234/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"qwen/qwen3-coder-30b\",
    \"messages\": [{\"role\": \"user\", \"content\": $(echo "$PROMPT" | jq -Rs .)}],
    \"max_tokens\": 8000,
    \"temperature\": 0.7
  }" | jq -r '.choices[0].message.content'

echo ""
echo "========================================================================"
echo "CONSULTATION COMPLETE"
echo "========================================================================"
