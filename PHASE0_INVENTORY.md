# Phase 0: Pre-Flight Checks Inventory

**Date**: October 30, 2025
**Status**: In Progress

---

## 0.1 Code Inventory ✅

### V1 Functions (Implementation)

**File**: `tools/autonomous.py`

1. **autonomous_filesystem_full**
   - Line: 35
   - Parameters: task, working_directory, max_rounds, max_tokens
   - Uses: /v1/chat/completions (stateless)

2. **autonomous_memory_full**
   - Line: 517
   - Parameters: task, max_rounds, max_tokens
   - Uses: /v1/chat/completions (stateless)

3. **autonomous_fetch_full**
   - Line: 751
   - Parameters: task, max_rounds, max_tokens
   - Uses: /v1/chat/completions (stateless)

4. **autonomous_github_full**
   - Line: 977
   - Parameters: task, github_token, max_rounds, max_tokens
   - Uses: /v1/chat/completions (stateless)

### V2 Functions (Implementation)

**File**: `tools/autonomous.py`

1. **autonomous_filesystem_full_v2**
   - Line: 189
   - Parameters: task, working_directory, max_rounds, max_tokens
   - Uses: /v1/responses (stateful)

2. **autonomous_memory_full_v2**
   - Line: 623
   - Parameters: task, max_rounds, max_tokens
   - Uses: /v1/responses (stateful)

3. **autonomous_fetch_full_v2**
   - Line: 851
   - Parameters: task, max_rounds, max_tokens
   - Uses: /v1/responses (stateful)

4. **autonomous_github_full_v2**
   - Line: 1087
   - Parameters: task, github_token, max_rounds, max_tokens
   - Uses: /v1/responses (stateful)

### FastMCP Registrations (V1)

**File**: `tools/autonomous.py`

1. autonomous_filesystem_full - Line: 1237 (decorated with @mcp.tool())
2. autonomous_memory_full - Line: 1467 (decorated with @mcp.tool())
3. autonomous_fetch_full - Line: 1591 (decorated with @mcp.tool())
4. autonomous_github_full - Line: 1702 (decorated with @mcp.tool())

### FastMCP Registrations (V2)

**File**: `tools/autonomous.py`

1. autonomous_filesystem_full_v2 - Line: 1313 (decorated with @mcp.tool())
2. autonomous_memory_full_v2 - Line: 1524 (decorated with @mcp.tool())
3. autonomous_fetch_full_v2 - Line: 1642 (decorated with @mcp.tool())
4. autonomous_github_full_v2 - Line: 1764 (decorated with @mcp.tool())

### Total Count
- **V1 implementations**: 4 functions
- **V2 implementations**: 4 functions
- **V1 FastMCP tools**: 4 registrations
- **V2 FastMCP tools**: 4 registrations
- **Total functions to consolidate**: 8 → 4
- **Total FastMCP tools to consolidate**: 8 → 4

---

## 0.2 Dependency Check

### Shared Dependencies

All autonomous functions depend on:
- `AutonomousExecutionTools` class
- `LLMClient` (llm/llm_client.py)
- `MCPConnection` (mcp_client/connection.py)
- `ToolDiscovery` (mcp_client/tool_discovery.py)
- `ToolExecutor` (mcp_client/executor.py)
- `SchemaConverter` (mcp_client/tool_discovery.py)

### V1-Specific Code

V1 functions use:
- `MessageManager` (llm/message_manager.py) for manual history
- `chat_completion()` method in LLMClient
- Message list construction and management

### V2-Specific Code

V2 functions use:
- `create_response()` method in LLMClient
- `previous_response_id` tracking
- No manual message management

### Private Helpers Needed

To consolidate, we'll need to create:
- `_execute_autonomous_stateful()` - Extract v2 core logic
- `_execute_autonomous_stateless()` - Extract v1 core logic
- `_create_filesystem_connection()` - Connection setup
- `_create_memory_connection()` - Connection setup
- `_create_fetch_connection()` - Connection setup
- `_create_github_connection()` - Connection setup

---

## 0.3 Test Inventory

### Test Files Found

1. **test_autonomous_v2_comparison.py**
   - Tests: V1 vs V2 comparison
   - Uses: Both v1 and v2 functions
   - Purpose: Compare token usage
   - Status: Will need updating

2. **test_phase3_all_v2_functions.py**
   - Tests: All v2 functions
   - Uses: Only v2 functions
   - Purpose: Validate v2 implementations
   - Status: Can be removed after consolidation

3. **test_local_llm_tools.py**
   - Tests: Basic LLM functionality
   - Uses: Core tools, not autonomous
   - Status: No changes needed

4. **test_responses_api_v2.py**
   - Tests: /v1/responses API
   - Uses: Core API, not autonomous functions
   - Status: No changes needed

5. **test_responses_with_tools.py**
   - Tests: Tool format conversion
   - Uses: Core functionality
   - Status: No changes needed

### Test Update Plan

**After Phase 1** (Internal Swap):
- test_autonomous_v2_comparison.py: Update to test stateful vs stateless
- test_phase3_all_v2_functions.py: Keep for now (still testing v2)

**After Phase 4** (Remove V2):
- test_autonomous_v2_comparison.py: Remove v2 references or rename
- test_phase3_all_v2_functions.py: Delete or consolidate into single test

---

## 0.4 Compatibility Verification

### Running Tests

**Status**: Need to run all tests to verify current state

```bash
# Test commands to run:
python3 test_autonomous_v2_comparison.py
python3 test_phase3_all_v2_functions.py
```

### Expected Results

All tests should PASS before proceeding with consolidation.

### Compatibility Matrix

| Function | V1 Works? | V2 Works? | Outputs Match? |
|----------|-----------|-----------|----------------|
| filesystem | ✅ (expected) | ✅ (expected) | ✅ (expected) |
| memory | ✅ (expected) | ✅ (expected) | ✅ (expected) |
| fetch | ✅ (expected) | ✅ (expected) | ✅ (expected) |
| github | ✅ (expected) | ✅ (expected) | ✅ (expected) |

---

## 0.5 Documentation Check

### Documents Referencing V1 or V2

1. **README.md**
   - Sections: Autonomous MCP Functions
   - References: Both v1 (legacy) and v2 (recommended)
   - Update needed: ✅

2. **MIGRATION_GUIDE.md**
   - Entire document about v1 → v2
   - Update needed: ✅ (simplify or archive)

3. **PHASE4A_DOCUMENTATION_UPDATE_COMPLETE.md**
   - Historical record of Phase 4A
   - Update needed: ❌ (keep as history)

4. **MAKING_V2_DEFAULT_ANALYSIS.md**
   - Analysis of making v2 default
   - Update needed: ❌ (keep as history)

5. **PHASE3_IMPLEMENTATION_COMPLETE.md**
   - Phase 3 completion record
   - Update needed: ❌ (keep as history)

6. **IMPLEMENTATION_COMPLETE_ALL_PHASES.md**
   - Complete summary of all phases
   - Update needed: ❌ (keep as history)

### Docstrings to Update

**V1 Functions** (4 total):
- Remove ⚠️ warnings after Phase 1
- Update to show optimization

**V2 Functions** (4 total):
- Will be removed in Phase 4

---

## 0.6 Go/No-Go Decision Criteria

### Required (Must Pass All)

- [ ] All v1 tests passing
- [ ] All v2 tests passing
- [ ] V1 and V2 produce identical outputs
- [ ] No known bugs in either version
- [ ] Clean git state (all changes committed)

### Recommended (Should Pass Most)

- [ ] Test coverage >80%
- [ ] Documentation up to date
- [ ] No pending PRs or issues blocking
- [ ] Backup/branch created

### Risk Assessment

**Technical Risk**: LOW
- V2 is proven to work
- V1 and V2 behavior identical
- Phased approach allows rollback

**User Impact Risk**: NONE (internal project)
- No external users yet
- Can break/change freely
- Aggressive timeline appropriate

**Code Quality Risk**: LOW
- Consolidation improves code quality
- Removes duplication
- Simplifies maintenance

---

## Next Steps After Phase 0

### If GO Decision:

**Phase 1: Internal Swap**
1. Create private helper methods
2. Extract stateful implementation
3. Extract stateless implementation
4. Update v1 to call helpers
5. Update v2 to call helpers
6. Test everything
7. Commit

**Phase 2: Add Fallback**
1. Add `use_stateful_api` parameter
2. Implement conditional logic
3. Update FastMCP registrations
4. Test both modes
5. Document
6. Commit

**Skip Phase 3** (as requested)

**Phase 4: Remove V2**
1. Delete v2 implementations
2. Delete v2 FastMCP registrations
3. Update tests
4. Update documentation
5. Version bump to 3.0.0
6. Commit

### If NO-GO Decision:

Document blockers and address them before proceeding.

---

**Inventory Complete**: Next → Run tests for compatibility verification
