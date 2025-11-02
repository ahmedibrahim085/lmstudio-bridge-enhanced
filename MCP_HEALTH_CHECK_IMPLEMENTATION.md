# MCP Health Check Implementation Guide
## Handling MCP Availability in BOTH Code and Tests

Per user's critical insight: **"This is something that needs to be handled in both the code and the tests"**

---

## Why Both Layers?

### Layer 1: Production Code
**Purpose**: Graceful degradation
**Behavior**: Return helpful error messages instead of crashing
**User Experience**: Clear explanation of what's wrong and how to fix it

### Layer 2: Test Code
**Purpose**: Skip tests that can't run
**Behavior**: `pytest.skip("MCP not available: [reason]")`
**Developer Experience**: No false negatives, clear skip reasons

---

## Implementation Overview

### Files Created:

1. **`utils/mcp_health_check.py`** - Core health checker
   - Checks MCP configuration
   - Pings MCP servers
   - Reads logs for errors
   - Returns detailed status

2. **`mcp_client/health_check_decorator.py`** - Production decorators
   - `@require_mcp()` - For production code
   - Returns error messages when MCP down
   - Prevents crashes

3. **`tests/conftest.py`** - Test fixtures
   - Pytest fixtures for MCP checks
   - Automatic test skipping
   - Custom markers

---

## Usage in Production Code

### Example 1: Decorate Function to Check MCP

```python
# In tools/dynamic_autonomous.py

from mcp_client.health_check_decorator import require_filesystem

class DynamicAutonomousAgent:

    @require_filesystem(return_error_message=True)
    async def autonomous_with_mcp(
        self,
        mcp_name: str,
        task: str,
        max_rounds: int = 10,
        model: Optional[str] = None
    ) -> str:
        """
        Execute autonomous task with MCP.

        If filesystem MCP is down, returns helpful error message:

        "Error: Filesystem MCP is not available.

         Reason: env: node: No such file or directory

         This MCP is required for this operation. Please:
         1. Check that node is in your PATH
         2. Verify MCP is configured in .mcp.json
         3. Restart the MCP server
         4. Check logs at: ~/.lmstudio/server-logs/..."

        Instead of crashing with cryptic error.
        """
        # Function continues normally if MCP is available
        ...
```

### Example 2: Check Multiple MCPs

```python
from mcp_client.health_check_decorator import require_any_mcp

class DynamicAutonomousAgent:

    @require_any_mcp(["filesystem", "memory", "github"])
    async def discover_and_execute(self, task: str) -> str:
        """
        Needs at least ONE MCP to work.

        If ALL MCPs are down, returns:

        "Error: None of the required MCPs are available.

         Required (any one of): filesystem, memory, github

         Status:
           - filesystem: env: node: No such file or directory
           - memory: MCP not configured
           - github: Connection timeout

         Please check MCP configuration and logs."
        """
        # Function continues if at least one MCP is available
        ...
```

### Example 3: Custom MCP Check

```python
from mcp_client.health_check_decorator import require_mcp

@require_mcp("github", return_error_message=False)
async def create_github_issue(title: str, body: str):
    """
    If github MCP is down, RAISES MCPUnavailableError
    instead of returning error message.

    Use return_error_message=False when you want to:
    - Catch the exception in calling code
    - Implement custom error handling
    - Retry logic
    """
    # Function code...
```

---

## Usage in Tests

### Option 1: Use Pytest Fixture

```python
# tests/test_e2e_multi_model.py

@pytest.mark.asyncio
async def test_my_function(require_filesystem):
    """
    Fixture automatically checks filesystem MCP.
    Test is SKIPPED if MCP not available.
    """
    agent = DynamicAutonomousAgent()
    result = await agent.autonomous_with_mcp("filesystem", "List files...")
    assert result is not None
```

### Option 2: Use Pytest Marker

```python
@pytest.mark.asyncio
@pytest.mark.requires_filesystem
async def test_my_function():
    """
    Marker automatically checks filesystem MCP.
    Test is SKIPPED if MCP not available.

    Cleaner than fixture if you have many tests.
    """
    agent = DynamicAutonomousAgent()
    result = await agent.autonomous_with_mcp("filesystem", "List files...")
    assert result is not None
```

### Option 3: Multiple MCPs

```python
@pytest.mark.asyncio
@pytest.mark.requires_mcps(["filesystem", "memory"])
async def test_multi_mcp():
    """
    Test requires BOTH filesystem AND memory MCPs.
    Skipped if EITHER is unavailable.
    """
    agent = DynamicAutonomousAgent()
    result = await agent.autonomous_with_multiple_mcps(
        ["filesystem", "memory"],
        "Read files and create knowledge graph"
    )
    assert result is not None
```

### Option 4: Conditional Logic (No Skip)

```python
@pytest.mark.asyncio
async def test_conditional(check_filesystem_available):
    """
    Check MCP but DON'T skip test.
    Use for conditional logic.
    """
    is_running, skip_reason = check_filesystem_available

    if is_running:
        # Run MCP-dependent code
        result = await some_mcp_function()
        assert "real data" in result
    else:
        # Run with mocks
        result = mock_mcp_function()
        assert "mock data" in result
```

---

## Migration Plan

### Step 1: Add Decorators to Production Code

**Files to update**:
- `tools/dynamic_autonomous.py`
- `tools/autonomous.py`
- Any function that uses MCPs

**Example change**:
```python
# BEFORE
async def autonomous_with_mcp(self, mcp_name, task, ...):
    # May crash with "Connection closed" if MCP down
    ...

# AFTER
from mcp_client.health_check_decorator import require_filesystem

@require_filesystem(return_error_message=True)
async def autonomous_with_mcp(self, mcp_name, task, ...):
    # Returns helpful error message if MCP down
    ...
```

### Step 2: Add Markers to Tests

**Files to update**:
- `tests/test_e2e_multi_model.py`
- `tests/test_multi_model_integration.py`
- Any test that uses MCPs

**Example change**:
```python
# BEFORE
@pytest.mark.asyncio
@pytest.mark.e2e
async def test_reasoning_to_coding_pipeline(self):
    # May fail with cryptic error if MCP down
    ...

# AFTER
@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.requires_filesystem
async def test_reasoning_to_coding_pipeline(self):
    # Skipped with clear reason if MCP down
    ...
```

### Step 3: Update Test Suite Runner

```python
# In run_full_test_suite.py

def phase3_e2e_tests(self):
    """Phase 3: E2E Tests."""
    print("\n🔷 PHASE 3: E2E TESTS")

    # NEW: Check MCP health first
    from utils.mcp_health_check import MCPHealthChecker

    checker = MCPHealthChecker()
    statuses = await checker.check_all_mcps(["filesystem", "memory"])

    should_skip, reason = checker.should_skip_tests(statuses, ["filesystem"])

    if should_skip:
        print(f"⚠️  Skipping E2E tests: {reason}")
        return True  # Don't fail, just skip

    # Continue with tests...
```

---

## Expected Behavior

### Scenario 1: MCP Running (Normal)

**Production code**:
```python
result = await autonomous_with_mcp("filesystem", "List files...")
# Returns: "Files: foo.py, bar.py, baz.txt..."
```

**Tests**:
```
test_reasoning_to_coding_pipeline PASSED
test_multi_mcp_integration PASSED
```

### Scenario 2: MCP Down (Graceful Degradation)

**Production code**:
```python
result = await autonomous_with_mcp("filesystem", "List files...")
# Returns: "Error: Filesystem MCP is not available.
#           Reason: env: node: No such file or directory
#           Please check that node is in your PATH..."
```

**Tests**:
```
test_reasoning_to_coding_pipeline SKIPPED
  Reason: Filesystem MCP not available: env: node: No such file or directory

  To run this test:
  1. Ensure node is in your PATH
  2. Verify MCP configured in .mcp.json
  3. Restart MCP server
  4. Run: python3 utils/mcp_health_check.py to verify
```

---

## Before vs After

### Before (No Health Checks):

**Production**:
```python
>>> result = await autonomous_with_mcp("filesystem", "List files")
Traceback (most recent call last):
  ...
mcp.shared.exceptions.McpError: MCP error -32000: Connection closed
```
❌ User sees cryptic error, no idea how to fix

**Tests**:
```
FAILED test_reasoning_to_coding_pipeline
AssertionError: Implementation too short
assert 39 > 50
```
❌ Developer wastes hours debugging, real issue is MCP down

### After (With Health Checks):

**Production**:
```python
>>> result = await autonomous_with_mcp("filesystem", "List files")
"Error: Filesystem MCP is not available.

 Reason: env: node: No such file or directory

 This MCP is required for this operation. Please:
 1. Check that node is in your PATH
 2. Verify MCP is configured in .mcp.json
 3. Restart the MCP server
 4. Check logs at: ~/.lmstudio/server-logs/..."
```
✅ User knows EXACTLY what's wrong and how to fix it

**Tests**:
```
SKIPPED test_reasoning_to_coding_pipeline
  Reason: Filesystem MCP not available: env: node: No such file or directory

  LM Studio log:
  [ERROR][Plugin(mcp/filesystem)] stderr: env: node: No such file or directory

  To run this test:
  1. Ensure node is in your PATH
  2. Restart MCP server
```
✅ Developer knows EXACTLY why test skipped, no debugging needed

---

## Testing the Implementation

### Test MCP Health Checker:
```bash
python3 utils/mcp_health_check.py
```

Expected output:
```
================================================================================
MCP HEALTH CHECK REPORT
================================================================================
❌ filesystem           - NOT RUNNING
   Error: MCP 'filesystem' not responding
   Log excerpt:
      [ERROR][Plugin(mcp/filesystem)] stderr: env: node: No such file or directory
✅ memory               - RUNNING
================================================================================
```

### Test Production Decorator:
```python
# Create test script
from mcp_client.health_check_decorator import require_filesystem

@require_filesystem()
async def test_function():
    return "This should return error if MCP down"

result = await test_function()
print(result)
```

### Test Pytest Markers:
```bash
# Run tests with MCP health checks
pytest tests/test_e2e_multi_model.py -v

# Should see:
# SKIPPED test_reasoning_to_coding_pipeline
#   Reason: Filesystem MCP not available...
```

---

## Benefits

### For Production Users:
✅ Clear error messages explaining what's wrong
✅ Step-by-step instructions to fix
✅ Log excerpts showing root cause
✅ No cryptic stack traces

### For Developers:
✅ No wasted time debugging when MCP is down
✅ Tests skip gracefully with clear reasons
✅ Can run subset of tests even if some MCPs down
✅ Health check before running full test suite

### For DevOps:
✅ Can detect MCP issues in CI/CD
✅ Health check script for monitoring
✅ Clear logs showing MCP status
✅ Can automate MCP restarts based on health

---

## Next Steps

1. **Immediate**: Fix node PATH issue
   ```bash
   which node
   echo 'export PATH="/usr/local/bin:$PATH"' >> ~/.zshrc
   source ~/.zshrc
   ```

2. **Restart MCPs**:
   - Restart LM Studio
   - In Claude Code: `/mcp` to reconnect

3. **Verify health**:
   ```bash
   python3 utils/mcp_health_check.py
   # Should show: ✅ filesystem - RUNNING
   ```

4. **Re-run tests**:
   ```bash
   pytest tests/ -v
   # Should see: 179/179 passing (100%)
   ```

5. **Add decorators to production code** (optional but recommended)

6. **Add markers to tests** (optional but recommended)

---

**Document Created**: November 2, 2025
**Purpose**: Implementation guide for MCP health checks in both code and tests
**Credit**: User's insight that this needs both layers

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
