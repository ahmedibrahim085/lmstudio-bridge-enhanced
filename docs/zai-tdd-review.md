# Z.ai TDD Review — Phase 2 Plan

**Date:** 2026-02-21  
**Reviewer:** Senior TDD Specialist (TDD Discipline Review)  
**Scope:** Round A OPPs (OPP-11, 13, 16, 05, 06, 07) — NOT Phase 1.5 OPPs

---

## Executive Summary

**VERDICT:** **CONDITIONAL APPROVAL** — The plan demonstrates strong TDD awareness with proper RED-GREEN-REFACTOR sequencing and comprehensive test coverage planning. However, there are **6 CRITICAL gaps** and **3 TDD violations** that MUST be addressed before implementation begins. The test infrastructure requirements from OPP-02 are well-documented, which is encouraging. Mock pattern understanding is solid but needs explicit documentation for `asyncio.to_thread` wrapping.

**Risk Level:** MEDIUM (6 critical gaps, mostly around edge cases and integration scenarios)

**Recommendation:** Address the 6 CRITICAL gaps before starting Phase A1 parallel work. The plan is otherwise well-structured with realistic test counts and proper architectural guards.

---

## CRITICAL — Missing Test Scenarios

### CRIT-01: OPP-11 — Anthropic System Prompt Conflict Resolution NOT Fully Tested

**Location:** OPP-11 Test #16 (`test_anthropic_messages_system_conflict_prefers_param`)

**Risk Level:** HIGH

**Evidence:** Plan states test #16 covers "BOTH `system` param AND role=system message → param wins, message filtered". However, the Anthropic API spec allows `system` param at top level AND `role=system` in messages array simultaneously. The test only checks which one "wins" — it does NOT verify:

1. What happens when BOTH are set with DIFFERENT values (e.g., `system="A"` and messages contain `{"role": "system", "content": "B"}`)
2. Whether the system message is properly filtered from the messages array
3. Whether the resulting payload structure matches Anthropic's expected format

**Bug it lets through:** A malformed payload that could cause silent failures or unexpected behavior on the Anthropic endpoint. If both system prompts exist and we don't filter correctly, we might send duplicate/conflicting system prompts to LM Studio, causing confusing LLM behavior.

**Missing Test Name:** `test_anthropic_messages_duplicate_system_different_values`
**Missing Test Description:**
```python
def test_anthropic_messages_duplicate_system_different_values(self):
    """
    When BOTH system param AND role=system message exist with DIFFERENT values:
    1. system param value should be used
    2. role=system message should be REMOVED from messages array
    3. Only ONE system prompt appears in final payload
    
    This guards against duplicate/conflicting system prompts reaching LM Studio.
    """
    # Mock anthropic_messages call with:
    # - system="System A"
    # - messages=[{"role": "system", "content": "System B"}, {"role": "user", "content": "Hi"}]
    # Verify payload contains: {"system": "System A", "messages": [{"role": "user", "content": "Hi"}]}
```

---

### CRIT-02: OPP-13 — Anthropic Tool Use ID Validation Missing

**Location:** OPP-13 Tests #8-9 (extract tool calls)

**Risk Level:** HIGH

**Evidence:** Tests #8-9 verify tool_use blocks are extracted, but there is NO test for malformed or missing `tool_use_id` fields. Anthropic's API requires `id` field in tool_use blocks. If LM Studio returns malformed responses (missing `id`, empty `id`, or wrong format), the extraction logic could crash or produce invalid tool result messages.

**Bug it lets through:** `KeyError` crash when `tool_use_id` is missing, or invalid `tool_result` messages that fail LM Studio's validation. This would cause autonomous loops to abort prematurely.

**Missing Test Name:** `test_extract_tool_use_missing_id_raises_error`
**Missing Test Description:**
```python
def test_extract_tool_use_missing_id_raises_error(self):
    """
    Anthropic tool_use blocks MUST have an 'id' field.
    When id is missing or empty, extraction should raise ValueError.
    This prevents building invalid tool_result messages.
    """
    # Response with: {"type": "tool_use", "name": "test_tool", "input": {...}, "id": ""}
    # Should raise ValueError or skip the tool_use block
```

**Missing Test Name:** `test_extract_tool_use_malformed_id_format`
**Missing Test Description:**
```python
def test_extract_tool_use_malformed_id_format(self):
    """
    Anthropic tool_use IDs should follow format: "toolu_..."
    Test with various malformed IDs: None, integer, empty string.
    Verify graceful handling (skip or error, NOT crash).
    """
```

---

### CRIT-03: OPP-06 — Parallel Tool Execution Deadlock Scenario NOT Tested

**Location:** OPP-06 Tests #6-9 (parallel execution)

**Risk Level:** HIGH

**Evidence:** Tests #6-9 verify basic parallel execution with `asyncio.gather()`, but there is NO test for the **timeout + partial failure** scenario that could cause hangs:

1. What happens when one tool times out (e.g., 60s) while others complete quickly?
2. Does `asyncio.wait_for()` properly cancel pending tasks?
3. Are partial results preserved before timeout?

The plan mentions `test_parallel_timeout_one_of_n` in Rev 4 notes as "already covered by test_partial_success_count_unchanged" — BUT that test does NOT verify timeout behavior specifically. Timeout is a different error path (asyncio.TimeoutError vs. tool execution exception).

**Bug it lets through:** Autonomous loop could hang indefinitely if one tool in a parallel batch never completes. The 60s timeout might not cancel pending `asyncio.gather()` tasks properly, causing resource leaks.

**Missing Test Name:** `test_parallel_timeout_cancels_pending_tasks`
**Missing Test Description:**
```python
def test_parallel_timeout_cancels_pending_tasks(self):
    """
    When one tool in a parallel batch times out (e.g., slow MCP),
    verify that:
    1. asyncio.TimeoutError is caught
    2. Pending tasks are cancelled (not left running)
    3. Completed tool results are preserved
    4. Error count is incremented correctly
    
    Use AsyncMock with side_effect that sleeps 70s for one tool, returns immediately for others.
    Mock asyncio.wait_for to trigger timeout after 1s for test speed.
    """
```

---

### CRIT-04: OPP-07 — Loop Metrics Collection During Early Abort Paths NOT Fully Tested

**Location:** OPP-07 Tests #16-18 (early return metrics)

**Risk Level:** MEDIUM-HIGH

**Evidence:** Tests #16-18 verify `last_loop_metrics` is set on JSON parse error, KeyError, and max_rounds abort. However, the plan states there are "5+ early return paths" in the autonomous loop. Only 3 are tested. MISSING early return paths:

1. **LLM call failure** (ConnectionError, timeout) — line ~635 in `dynamic_autonomous.py`
2. **Max consecutive errors abort** — line ~645 (`if consecutive_error_count >= MAX_CONSECUTIVE_ERRORS`)
3. **Empty content / no text_content** — line ~720 (`else: return "No content in response"`)

**Bug it lets through:** If the loop aborts early due to LLM connection failure or max consecutive errors, `last_loop_metrics` might be `None` or incomplete. Dashboard consumers calling `agent.last_loop_metrics.to_dashboard_format()` would crash with `AttributeError`.

**Missing Test Name:** `test_loop_metrics_set_on_llm_connection_error`
**Missing Test Description:**
```python
def test_loop_metrics_set_on_llm_connection_error(self):
    """
    When LLM raises ConnectionError, loop should abort with error message
    BUT last_loop_metrics must still be populated with:
    - rounds completed so far
    - total_errors count
    - status='aborted'
    
    Guard against AttributeError when dashboard reads metrics after failed loop.
    """
```

**Missing Test Name:** `test_loop_metrics_set_on_max_consecutive_errors`
**Missing Test Description:**
```python
def test_loop_metrics_set_on_max_consecutive_errors(self):
    """
    After MAX_CONSECUTIVE_ERRORS consecutive failures, loop aborts.
    Verify last_loop_metrics captures:
    - error count (should be >= MAX_CONSECUTIVE_ERRORS)
    - consecutive_error_count (may be >= MAX)
    - status='aborted'
    """
```

---

### CRIT-05: OPP-16 — Native MCP Feature Detection Race Condition NOT Tested

**Location:** OPP-16 Test #11 (`test_supports_native_mcp_caching`)

**Risk Level:** MEDIUM

**Evidence:** Test #11 verifies caching works (TTL=300s). However, there is NO test for the **concurrent first call** race condition:

1. Two threads/tasks call `supports_native_mcp()` simultaneously when cache is empty
2. Both threads see `_native_mcp_supported is None`
3. Both threads make HTTP GET to `/api/v1/server/info`
4. Both threads write to `_native_mcp_supported` (last writer wins)

The Rev 4 note accepts "double call on first use" as acceptable, BUT it doesn't test the behavior. This could cause unnecessary HTTP load or inconsistent results if the two HTTP calls get different responses (unlikely but possible during LM Studio restart).

**Missing Test Name:** `test_supports_native_mcp_concurrent_first_call`
**Missing Test Description:**
```python
def test_supports_native_mcp_concurrent_first_call(self):
    """
    When multiple callers invoke supports_native_mcp() simultaneously
    with cold cache (None), verify:
    1. Only ONE HTTP request is made (not N concurrent requests)
    2. All callers get the same result
    3. No race condition in cache write
    
    Use asyncio.gather() to simulate 10 concurrent calls with mock HTTP.
    Assert mock HTTP called exactly once.
    """
```

**Note:** This requires implementing a lock or `asyncio.ensure_future()` pattern. If the plan accepts "double call," this test should at least document the expected behavior (e.g., "2 HTTP calls acceptable, all callers converge to same result").

---

### CRIT-06: OPP-05 — Speculative Decoding with Wrong Backend NOT Tested

**Location:** OPP-05 Tests #1-8 (compatibility_type detection)

**Risk Level:** MEDIUM

**Evidence:** Tests verify `supports_speculative_decoding` returns True/False based on `compatibility_type`. However, there is NO integration test that actually calls `create_response()` with `draft_model` param on a NON-GGUF model:

1. What happens when user passes `draft_model="some_draft"` but model is MLX (`compatibility_type="mlx"`)?
2. Does LM Studio reject the request? Or does it silently ignore `draft_model`?
3. Should our bridge validate BEFORE sending to LM Studio?

**Missing Test Name:** `test_create_response_draft_model_rejected_for_mlx`
**Missing Test Description:**
```python
def test_create_response_draft_model_rejected_for_mlx(self):
    """
    When draft_model is specified but model is NOT GGUF (e.g., MLX),
    verify behavior:
    - Option A: Raise ValueError before calling LM Studio (defensive)
    - Option B: Pass through and let LM Studio handle (document in docstring)
    
    Test should call create_response() with draft_model on a model
    with compatibility_type="mlx" and verify the result.
    """
```

---

## TDD VIOLATIONS — RED-GREEN-REFACTOR Broken

### VIOL-01: OPP-07 — Test File Imports Module That Doesn't Exist Yet

**Location:** OPP-07 Atomic Commit #1 (RED tests)

**Evidence:** Plan states: "Tests import from `tools.loop_metrics` (will fail with ImportError = proper RED)."

**Why This is a Violation:**  
In strict TDD, RED tests should fail on **assertions**, not on `ImportError`. If the test file cannot even import the module under test, you're not testing the behavior — you're testing module existence. This makes it harder to distinguish between:

1. Missing module (implementation hasn't started)
2. Wrong implementation (tests run but assertions fail)

**Recommended Fix:**  
Split the RED commit into two:

```bash
# Commit 1a: Add module stub with dataclass signatures
feat(OPP-07): add loop_metrics module stub
- Create tools/loop_metrics.py with empty dataclass definitions
- Passes import but has no real implementation

# Commit 1b: Add RED tests that assert on behavior
test(OPP-07): add RED tests for loop observability (22 tests)
- Tests import successfully
- All assertions fail (not import errors)
```

This ensures proper TDD discipline: tests fail because behavior is missing, not because code structure is missing.

---

### VIOL-02: OPP-13 — Round-Trip Test Has No Explicit Assertion

**Location:** OPP-13 Test #16 (`test_roundtrip_conversion`)

**Evidence:** Plan describes this as "convert tools → call → extract → build result full scenario" but does NOT specify what assertion validates the round-trip. A proper round-trip test should verify:

1. Original tool schema → Anthropic format
2. Mock Anthropic response with tool_use
3. Extract tool_use back to internal format
4. Build tool_result message
5. **ASSERT: tool_result message can be sent back to LM Studio successfully**

**Recommended Fix:**  
Explicitly document the assertion in test description:

```python
def test_roundtrip_conversion(self):
    """
    Full round-trip scenario:
    1. Convert OpenAI tool schema to Anthropic format
    2. Mock LM Studio response with tool_use block
    3. Extract tool_use from response
    4. Build tool_result message
    5. ASSERT: tool_result message has correct structure (role=user, content with tool_result)
    6. ASSERT: tool_use_id matches extracted id
    7. ASSERT: content is properly serialized
    """
```

---

### VIOL-03: OPP-06 — Sequential Test #4 Documents "Known Behavior" But Doesn't Flag as Bug

**Location:** OPP-06 Test #4 (`test_sequential_three_failures_same_round`)

**Evidence:** Plan states: "documents existing sequential behavior — 3 tools fail = count reaches 3 in one round (known behavior, NOT capped in sequential path)"

**Why This is Concerning:**  
The plan acknowledges this is inconsistent with parallel path (capped at +1), but accepts it as "known behavior" and defers fixing. This is a TDD smell — you're testing FOR a bug instead of testing AGAINST it.

**Recommended Fix:**  
Either:

**Option A:** Fix the sequential path in OPP-06 (preferable for consistency):
```python
# In _execute_tools_sequential, also cap at +1 per round
if any(failed for failed in results):
    consecutive_error_count += 1  # NOT +len(failed)
```

**Option B:** Mark the test as `@pytest.mark.xfail` with a clear bug tracker link:
```python
@pytest.mark.xfail(reason="OPP-06-BUG: Sequential path increments per-tool instead of capped. https://github.com/.../issues/...")
def test_sequential_three_failures_same_round(self):
    """
    Documents inconsistent behavior: sequential path increments per-tool,
    parallel path caps at +1. This is a BUG, not intended behavior.
    """
```

**Option B** is safer for Round A timeline, but the bug should be tracked explicitly.

---

## MISSING EDGE CASES

### EDGE-01: OPP-11 — Anthropic API Version Mismatch

**Risk:** LOW  
**Missing Test:** What happens when LM Studio doesn't support the `anthropic-version` header we send? Test with LM Studio returning 400 for unsupported API version.

**Test Name:** `test_anthropic_messages_unsupported_api_version_fallback`

---

### EDGE-02: OPP-11 — Empty Tool Array in Anthropic Format

**Risk:** LOW  
**Missing Test:** Anthropic endpoint with `tools=[]` (empty array, not `None`). Verify this doesn't crash and behaves like no tools provided.

**Test Name:** `test_anthropic_messages_empty_tools_array`

---

### EDGE-03: OPP-13 — Tool Schema with Circular References

**Risk:** LOW-MEDIUM  
**Missing Test:** JSON Schema with `$ref` circular references. `convert_tools_to_anthropic_format` should preserve these as-is (not try to resolve).

**Test Name:** `test_convert_tool_schema_with_ref_preserved`

---

### EDGE-04: OPP-06 — Parallel Execution with Zero Tools

**Risk:** LOW  
**Missing Test:** `parallel_tools=True` but `function_calls=[]` (no tools requested). Should fall back to sequential path gracefully.

**Test Name:** `test_parallel_flag_ignored_with_zero_tools`

---

### EDGE-05: OPP-07 — Metrics Overflow on Long-Running Loops

**Risk:** LOW (addressed in Rev 3 with 100-round cap)  
**Status:** ✅ TESTED — Test #19 `test_loop_metrics_rounds_capped_at_100` covers this.

---

### EDGE-06: OPP-16 — Native MCP with Disabled Server

**Risk:** MEDIUM  
**Missing Test:** LM Studio returns `"mcp": true` in capabilities but MCP server is disabled/stopped. Does `chat_completion_with_native_mcp()` raise a clear error or timeout?

**Test Name:** `test_native_mcp_server_disabled_raises_error`

---

### EDGE-07: OPP-05 — Draft Model Not Loaded

**Risk:** MEDIUM  
**Missing Test:** `draft_model` parameter specifies a model that isn't loaded in LM Studio. Does `_ensure_model_loaded()` get called for the draft model too? Or only for the main model?

**Test Name:** `test_create_response_draft_model_not_loaded`

**Expected Behavior:** Either:
- Automatically load draft model via `_ensure_model_loaded(draft_model, ttl=...)`
- Raise `LLMResponseError("Draft model 'X' not loaded")`

This should be explicitly tested.

---

## SUGGESTIONS — Test Quality Improvements

### SUG-01: Add Property-Based Testing for Tool Schema Conversion

**Location:** OPP-13  
**Suggestion:** Use `hypothesis` library to generate random JSON schemas and verify round-trip conversion preserves structure. This catches edge cases that manual tests miss.

**Benefit:** Catches unexpected schema variations (nested objects, enums, pattern constraints) that hand-written tests might not cover.

---

### SUG-02: Add Fuzz Testing for Anthropic Message Parsing

**Location:** OPP-11  
**Suggestion:** Generate malformed Anthropic responses (missing fields, wrong types, nested structures) and verify parser handles gracefully.

**Benefit:** Hardens parsing logic against unexpected LM Studio responses or API changes.

---

### SUG-03: Add Performance Regression Test for Parallel Execution

**Location:** OPP-06  
**Suggestion:** Add a test that measures wall-clock time for 3 tools in parallel vs sequential. Assert parallel is at least 1.5x faster (not perfect 3x due to overhead).

**Benefit:** Catches performance regressions if asyncio logic is accidentally serialized.

**Test Name:** `test_parallel_execution_faster_than_sequential`

---

### SUG-04: Add Chaos Testing for MCP Failures

**Location:** OPP-06, OPP-16  
**Suggestion:** Use `mcp` library's test utilities to simulate MCP server crashes, timeouts, and malformed responses. Verify autonomous loop recovers gracefully.

**Benefit:** Hardens error handling beyond happy-path mocks.

---

### SUG-05: Document Mock Patterns Explicitly

**Location:** ALL OPPs  
**Suggestion:** The Rev 4 note mentions Qwen provided `asyncio.to_thread` mock template, but it's not in the plan itself. Add a section "Test Infrastructure Patterns" with code examples for:

1. Mocking `llm.create_response` with `MagicMock(side_effect=...)` (NOT `AsyncMock`)
2. Running async tests with `_run_loop()` helper
3. Mocking MCP sessions with `AsyncMock` for `call_tool`

**Benefit:** Ensures all teammates follow consistent mock patterns. Prevents subtle bugs where `AsyncMock` is used incorrectly (causes test flakiness).

---

## VERIFIED — Test Design Decisions That Are Correct

### ✅ VERIFY-01: OPP-02 Helper Pattern Usage

**Evidence:** Plan states OPP-07 tests "MUST use `_make_agent()`/`_run_loop()` helpers from OPP-02 pattern"

**Assessment:** **CORRECT** — These helpers encapsulate the async event loop setup and mock LLM injection. Reusing them ensures consistency and prevents `asyncio` setup bugs.

---

### ✅ VERIFY-02: Retry Decorator Uses Local Constant

**Evidence:** Rev 3 note clarifies `@retry_with_backoff` uses `llm_client.DEFAULT_MAX_RETRIES` (=2), NOT `constants.DEFAULT_MAX_RETRIES` (=3)

**Assessment:** **CORRECT** — Name collision is documented, and plan specifies the correct import. This prevents off-by-one errors in retry logic.

---

### ✅ VERIFY-03: OPP-06 Error Count Three-Branch Logic

**Evidence:** Rev 3 defines three branches for parallel error counting:
1. All succeed → `consecutive_error_count = 0`
2. All fail → `consecutive_error_count += 1` (capped)
3. Partial success → `consecutive_error_count` unchanged

**Assessment:** **CORRECT** — This gives the LLM self-correction opportunity while acknowledging partial progress. The logic is well-tested (#16, #18).

---

### ✅ VERIFY-04: OPP-07 Instance Attribute Instead of Tuple Return

**Evidence:** Rev 2 changed from `(str, LoopMetrics)` return to `self.last_loop_metrics` attribute

**Assessment:** **CORRECT** — Instance attribute is simpler, avoids breaking 3 callers, and is safe given stdio transport serialization. Documented limitation (last-writer-wins) is acceptable.

---

### ✅ VERIFY-05: Architecture Guards Scan Entire Codebase

**Evidence:** Rev 2 test `test_no_hardcoded_anthropic_endpoint` scans "ENTIRE codebase, not just llm_client.py"

**Assessment:** **CORRECT** — Hardcoded strings can creep in anywhere. Whole-codebase scan prevents regressions.

---

## TEST COUNT VERIFICATION

### Plan Claims vs. Reality

| OPP | Plan Claim | Count from Test List | Match? | Notes |
|-----|------------|---------------------|--------|-------|
| OPP-11 | 18 | 18 tests listed | ✅ | Accurate (Rev 3: +3 from Rev 2) |
| OPP-05 | 15 | 15 tests listed | ✅ | Accurate (Rev 3: +2 from Rev 2) |
| OPP-16 | 12 | 12 tests listed | ✅ | Accurate (Rev 3: +2 from Rev 2) |
| OPP-13 | 16 | 16 tests listed | ✅ | Accurate (Rev 3: +2 from Rev 2) |
| OPP-06 | 18 | 18 tests listed | ✅ | Accurate (Rev 3: +4 from Rev 2) |
| OPP-07 | 22 | 22 tests listed | ✅ | Accurate (Rev 3: +6 from Rev 2) |
| **Round A Total** | **111** | **111** | ✅ | **VERIFIED** |
| Guards | 10 | 10 guards listed | ✅ | Accurate |
| **Grand Total** | **121** | **121** | ✅ | **ALL TESTS ACCOUNTED FOR** |

### Realism Assessment

**Verdict:** **REALISTIC** — The test counts are achievable and follow the established pattern from OPP-02 (21 tests for self-correcting loops). 

**Evidence:**
- OPP-02 has 21 tests for similar complexity (autonomous loop behavior)
- OPP-01 has 16 tests for API integration
- Round A adds 111 tests over 6 OPPs (avg 18.5 per OPP)
- This is consistent with historical test density

**Risk:** None — Test counts are realistic and achievable within the 2-week Round A timeline.

---

## FINAL VERDICT

### Overall Assessment

**CONDITIONAL APPROVAL** — The Phase 2 plan demonstrates strong TDD discipline with comprehensive test coverage, proper mock patterns, and realistic test counts. However, **6 CRITICAL gaps** and **3 TDD violations** MUST be addressed before implementation begins.

### Action Items Before Phase A1 Launch

#### MUST-FIX (Blocking)

1. **CRIT-01**: Add `test_anthropic_messages_duplicate_system_different_values` to OPP-11
2. **CRIT-02**: Add `test_extract_tool_use_missing_id_raises_error` and `test_extract_tool_use_malformed_id_format` to OPP-13
3. **CRIT-03**: Add `test_parallel_timeout_cancels_pending_tasks` to OPP-06
4. **CRIT-04**: Add `test_loop_metrics_set_on_llm_connection_error` and `test_loop_metrics_set_on_max_consecutive_errors` to OPP-07
5. **VIOL-01**: Split OPP-07 RED commit into: (1a) module stub, (1b) behavioral tests
6. **VIOL-03**: Mark OPP-06 Test #4 as `@pytest.mark.xfail` with bug tracker link OR fix sequential path consistency

#### SHOULD-FIX (Recommended)

7. **CRIT-05**: Add `test_supports_native_mcp_concurrent_first_call` to OPP-16 (or document double-call behavior explicitly)
8. **CRIT-06**: Add `test_create_response_draft_model_rejected_for_mlx` to OPP-05
9. **VIOL-02**: Add explicit assertion documentation to OPP-13 Test #16

#### NICE-TO-HAVE (Future Sprints)

10. **SUG-01**: Add property-based testing with `hypothesis` for OPP-13
11. **SUG-03**: Add performance regression test for OPP-06 parallel execution
12. **SUG-05**: Add "Test Infrastructure Patterns" section to plan with mock code examples

### Risk Summary

| Risk Category | Count | Severity |
|--------------|-------|----------|
| CRITICAL gaps | 6 | HIGH (3), MEDIUM (3) |
| TDD violations | 3 | MEDIUM |
| Missing edge cases | 4 | LOW (3), MEDIUM (1) |
| Test count accuracy | 0 | NONE (all verified ✅) |
| Mock pattern correctness | 0 | NONE (patterns verified ✅) |

### Confidence Level

**HIGH** — Once the 6 MUST-FIX items are addressed, the plan will have robust TDD coverage with minimal risk of shipping bugs to production. The test infrastructure requirements are well-documented, mock patterns are consistent with OPP-02, and test counts are realistic.

---

## Appendix: Mock Pattern Reference

From OPP-02 and plan documentation, the canonical mock patterns for Round A tests:

### Pattern 1: Mock LLM in Autonomous Loop

```python
from tools.dynamic_autonomous import DynamicAutonomousAgent
from unittest.mock import MagicMock

def _make_agent(mock_llm_create_response=None):
    """Build agent with mocked LLM."""
    mock_llm = MagicMock()
    if mock_llm_create_response is not None:
        mock_llm.create_response = mock_llm_create_response
    else:
        mock_llm.create_response = MagicMock()
    
    agent = DynamicAutonomousAgent.__new__(DynamicAutonomousAgent)
    agent.llm = mock_llm
    agent.model_validator = MagicMock()
    agent.mcp_json_path = "/tmp/fake.mcp.json"
    return agent
```

### Pattern 2: Run Async Tests

```python
import asyncio

def _run_loop(coro):
    """Run async coroutine in fresh event loop."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

# Usage in test:
def test_parallel_execution(self):
    agent = _make_agent(MagicMock(side_effect=mock_response))
    result = _run_loop(
        agent._autonomous_loop(
            dispatcher=mock_dispatcher,
            openai_tools=[],
            task="test task",
            max_rounds=10,
            max_tokens=1024,
        )
    )
    self.assertEqual(result, "expected")
```

### Pattern 3: Mock MCP Session

```python
from unittest.mock import AsyncMock

def _mock_session():
    """Return a mock ClientSession."""
    session = MagicMock()
    session.call_tool = AsyncMock()
    return session

# Usage:
async def fake_safe_call_tool(session, name, args):
    return {"result": "success"}

with patch("tools.dynamic_autonomous.safe_call_tool", side_effect=fake_safe_call_tool):
    result = _run_loop(agent._autonomous_loop(...))
```

---

**Review completed:** 2026-02-21  
**Next review:** After MUST-FIX items addressed (estimated 2-4 hours)
