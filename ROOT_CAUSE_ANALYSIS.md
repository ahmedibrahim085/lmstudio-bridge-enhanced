# Root Cause Analysis: Why Tests Were Failing
## November 2, 2025 - The REAL Problem

User's critical insight: **"I think the issue is coming from the fact that the MCPs are not actually running"**

---

## The Smoking Gun

### LM Studio Server Log Error:
```
[2025-11-02 15:06:08][ERROR][Plugin(mcp/filesystem)] stderr: env: node: No such file or directory

[2025-11-02 15:06:08][ERROR][Plugin(mcp/filesystem)] stderr: Error in LM Studio MCP bridge process: McpError: MCP error -32000: Connection closed
```

**Translation**: The filesystem MCP is **crashing immediately** because it can't find the `node` executable.

---

## What This Means

### Problem 1: Filesystem MCP Not Running

**For LM Studio**:
- LM Studio tries to start filesystem MCP
- MCP is a Node.js server
- Can't find `node` in PATH
- MCP crashes immediately
- Every tool call fails with "Connection closed"

**For Claude Code**:
- Same issue (based on user's `/mcp` command showing "Failed to reconnect to filesystem")
- MCPs are not running for EITHER system

###Problem 2: All "Test Failures" Were Actually MCP Failures

**What I thought**:
- test_reasoning_to_coding_pipeline: "LLM guesses wrong paths"
- autonomous_execution: "MCP connection issue"

**What was actually happening**:
- test_reasoning_to_coding_pipeline: Filesystem MCP crashed, LLM couldn't access ANY files, tried 10 times, gave up
- autonomous_execution: Same - MCP not running, connection closed

**All test failures trace back to ONE root cause: MCPs not running**

---

## Why MCPs Are Not Running

### Issue: `node` Not in PATH

The error `env: node: No such file or directory` means:
- System can't find the `node` executable
- MCPs that use Node.js (filesystem, github, etc.) can't start
- They crash immediately on launch

### Why This Wasn't Obvious

1. **Silent failures**: MCPs crash silently, tests just "fail"
2. **Misleading error messages**: Tests return "Task incomplete" not "MCP crashed"
3. **Intermittent behavior**: Sometimes MCPs work (if started manually), sometimes don't
4. **No health checks**: Tests assume MCPs are running, don't verify

---

## User's Brilliant Solution

> "Maybe we need a protective measure that try to reconnect to the MCPs in case they are not started and if failed you skip the tests related to this specific MCP with a clear reasoning message including a log error or something."

**This is EXACTLY right**:
1. ✅ Check MCP health BEFORE running tests
2. ✅ Try to reconnect if down
3. ✅ Skip tests gracefully if MCP unavailable
4. ✅ Show CLEAR error message with log excerpt

---

## What I Implemented

### `utils/mcp_health_check.py` - MCP Health Checker

**Features**:
1. Checks if MCP is configured in `.mcp.json`
2. Tries to connect to MCP (ping test)
3. If fails, checks LM Studio logs for errors
4. If fails, checks Claude logs for errors
5. Returns detailed status with error messages and log excerpts

**Usage in tests**:
```python
from utils.mcp_health_check import check_required_mcps

async def test_my_function():
    # Check if MCPs are running
    all_running, skip_reason = await check_required_mcps(["filesystem", "memory"])

    if not all_running:
        pytest.skip(f"MCPs not running: {skip_reason}")

    # Continue with test...
```

**Benefits**:
- ✅ Tests skip gracefully with CLEAR reason
- ✅ Includes log excerpts showing WHY MCP failed
- ✅ No more cryptic "Task incomplete" errors
- ✅ No more wasted time debugging tests when real issue is MCP

---

## Example Output

### Before (Cryptic):
```
FAILED tests/test_e2e_multi_model.py::test_reasoning_to_coding_pipeline
AssertionError: Implementation too short
assert 39 > 50
```

**User has NO IDEA why** - is it the test? The LLM? The code?

### After (Clear):
```
SKIPPED tests/test_e2e_multi_model.py::test_reasoning_to_coding_pipeline
Reason: Filesystem MCP not running: env: node: No such file or directory

LM Studio log:
[ERROR][Plugin(mcp/filesystem)] stderr: env: node: No such file or directory
[ERROR][Plugin(mcp/filesystem)] stderr: McpError: MCP error -32000: Connection closed
```

**User IMMEDIATELY knows**: Node.js not in PATH, fix PATH, restart MCP.

---

## How to Fix the Actual Problem

### Step 1: Fix Node.js PATH

**Option A: Add node to PATH globally**:
```bash
# Find where node is installed
which node  # e.g., /usr/local/bin/node

# Add to ~/.zshrc or ~/.bash_profile
export PATH="/usr/local/bin:$PATH"

# Reload shell
source ~/.zshrc
```

**Option B: Use full path in MCP config**:
```json
{
  "mcpServers": {
    "filesystem": {
      "command": "/usr/local/bin/npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/ahmedmaged/ai_storage"]
    }
  }
}
```

### Step 2: Restart MCP Servers

**For LM Studio**:
- Restart LM Studio application
- MCPs will attempt to start again

**For Claude Code**:
- Run `/mcp` to reconnect
- Or restart Claude Code

### Step 3: Verify MCPs Are Running

```bash
# Run health check
python3 utils/mcp_health_check.py

# Should show:
# ✅ filesystem - RUNNING
# ✅ memory - RUNNING
```

---

## Impact on Test Results

### Before Fix (MCPs Down):
```
Pytest: 166/166 passing (100%) ✅
  (These tests don't use MCPs)

Standalone scripts: 11/13 passing
  - test_reasoning_to_coding_pipeline: ❌ FAIL (MCP crashed)
  - autonomous_execution: ❌ FAIL (MCP crashed)
  - Other failures: All MCP-related
```

### After Fix (MCPs Running):
```
Expected: 179/179 passing (100%) ✅

All MCP-dependent tests should pass because:
- Filesystem MCP can serve file requests
- LLM can successfully call list_directory, read_file, etc.
- No more "Connection closed" errors
- No more "Maximum rounds reached" (LLM gets results on first try)
```

---

## What We Learned

### Mistake 1: Assumed MCPs Were Running
I never verified MCPs were actually running before testing.
**Lesson**: Always check dependencies before blaming the code.

### Mistake 2: Misdiagnosed Test Failures
I thought "LLM guesses wrong paths" when real issue was "MCP crashed, can't access ANY paths."
**Lesson**: Look at actual errors, not symptoms.

### Mistake 3: No Health Checks
Tests assumed MCPs worked, never verified.
**Lesson**: Add health checks for all external dependencies.

### User's Insight Was Critical
> "I think the issue is coming from the fact that the MCPs are not actually running"

This ONE sentence identified the root cause I missed completely.
**Lesson**: User skepticism + investigation = find real problems.

---

## Comparison: My Analysis vs Reality

### What I Thought:
| Issue | My Diagnosis | My Solution |
|-------|-------------|------------|
| test_reasoning_to_coding_pipeline | LLM guesses wrong paths | Make task more explicit |
| autonomous_execution | MCP connection timeout | Accept as pre-existing issue |
| test_lms_cli_mcp_tools | Can't test IDLE state | Force model to IDLE first |

### What Was Actually Happening:
| Issue | Real Cause | Real Solution |
|-------|-----------|---------------|
| test_reasoning_to_coding_pipeline | MCP crashed (node not found) | Fix node PATH, restart MCP |
| autonomous_execution | MCP crashed (node not found) | Fix node PATH, restart MCP |
| test_lms_cli_mcp_tools | Likely also MCP issue | Fix node PATH, restart MCP |

**ALL issues trace to ONE root cause: MCPs not running**

---

## Next Steps

### Immediate (Done):
1. ✅ Created MCP health checker utility
2. ✅ Documented root cause
3. ✅ Identified fix (node PATH)

### To Do:
1. Fix node PATH issue
2. Restart MCPs
3. Re-run all tests with MCPs actually running
4. Verify all 179 tests pass
5. Add MCP health checks to test suite runner

### For Future:
1. Always check MCP health before running tests
2. Include log excerpts in error messages
3. Don't assume dependencies work - verify
4. Listen to user insights (they're usually right!)

---

**Document Created**: November 2, 2025
**Root Cause**: MCPs not running (node executable not in PATH)
**Fix**: Update PATH, restart MCPs, add health checks
**Credit**: User's insight identified the real problem

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
