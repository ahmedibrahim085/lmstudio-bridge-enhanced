# OPP-51: Refactor `dynamic_autonomous.py` God Module

**Status**: SPEC COMPLETE — Ready for implementation
**Priority**: P1 (tech debt — blocks future feature velocity)
**RICE Score**: 18.0 (Reach: 8, Impact: 3, Confidence: 75%, Effort: 1 sprint)
**Version**: v5.2.0
**Author**: Investigation 2026-03-04 (2 rounds, grepai + code-search + manual tracing)

---

## Problem Statement

`tools/dynamic_autonomous.py` is a 1,515-line god module containing a single 1,417-line class (`DynamicAutonomousAgent`) with **6 mixed concerns**. Two autonomous loop methods (`_autonomous_loop` and `_autonomous_loop_anthropic`) are 95% identical (262-266 lines each), differing only in LLM call, response parsing, and state management. Every Round G OPP (33, 37, 40, 44, 45, 46) had to wire into this file, adding ~95 lines of integration code to an already bloated module.

### Evidence

| Metric | Value | Problem |
|--------|-------|---------|
| File lines | 1,515 | 2× the 800-line max (coding style rule) |
| Class lines | 1,417 (93%) | Single class owns everything |
| `self.` references | 78 | High coupling surface |
| `LoopMetrics(` constructions | 7 | Duplicated across both loops |
| `_record_round_metrics` calls | 9 | Duplicated across both loops |
| Duplicate loop code | ~260 lines | Two loops share identical init, guard, metrics, error handling, finally blocks |
| Imports | 22 modules | Too many concerns in one file |
| Test files depending on module | 21 | High blast radius for any change |
| Log calls | 77 | Spread across all concerns |

### Root Cause

The module grew organically: OPP-02 (self-correction), OPP-06 (parallel tools), OPP-07 (metrics), OPP-17 (Anthropic format), OPP-39 (context guard), and Round G (5 pipeline modules) all wired into the same file because there was no separation of concerns. The Anthropic loop was copy-pasted from the responses loop rather than abstracted.

---

## Six Concern Domains

| # | Concern | Lines | Methods | Extraction Target |
|---|---------|-------|---------|-------------------|
| 1 | MCP Connection | ~180 | `autonomous_with_mcp`, `autonomous_with_multiple_mcps`, `autonomous_discover_and_execute`, `autonomous_with_images` | Phase 3: `MCPConnectionManager` |
| 2 | Model Init | ~48 | `_preload_and_validate_model` | Stays in facade (too small to extract) |
| 3 | Tool Dispatchers | ~115 | `_SingleSessionDispatcher`, `_MultiSessionDispatcher` | Phase 1: Move with executor |
| 4 | Tool Execution Pipeline | ~215 | `_execute_tools_sequential`, `_execute_tools_parallel` | **Phase 1: `GuardedToolExecutor`** |
| 5 | Loop Orchestration | ~530 | `_autonomous_loop`, `_autonomous_loop_anthropic`, `_run_autonomous_dispatch` | **Phase 2: Strategy pattern merge** |
| 6 | Metrics | ~31 | `_record_round_metrics`, `_estimate_tokens`, `last_loop_metrics` | Phase 4: `TokenBudgetManager` |

---

## Shared Mutable State

| State | Scope | Mutated By | Thread-Safe? | Extraction Impact |
|-------|-------|------------|-------------|-------------------|
| `self.consecutive_error_count` | Instance | `_execute_tools_sequential`, `_execute_tools_parallel`, both loops | **NO** | Moves into `GuardedToolExecutor` (Phase 1) |
| `self.last_loop_metrics` | Instance | Both loops (set in `finally`) | **NO** (acceptable) | Stays on facade, set by loop return value |
| `self.llm` | Instance | Read-only in loops | Yes | Passed as param to strategy |
| `self.model_validator` | Instance | Read-only | Yes | Stays on facade |
| `self.mcp_json_path` | Instance | Read-only | Yes | Moves to `MCPConnectionManager` (Phase 3) |

---

## Two Loops: Diff Analysis

### What's Identical (copy-paste duplication)

```
INIT BLOCK (16 lines):
  consecutive_error_count = 0
  tool_schemas = {build from openai_tools}
  guard = ToolCallGuard(tool_schemas)
  tracker = ToolCallTracker()
  cache = ToolResultCache()
  health_tracker = ModelHealthTracker()
  timeout_mgr = AdaptiveTimeoutManager()
  cumulative_tokens = 0
  last_loop_metrics = None
  loop_start_time, total_error_count, completed_rounds, round_metrics_list, final_status

PER-ROUND (identical pattern):
  round_start_time, round_tool_calls, round_errors
  context guard check (cumulative_tokens > threshold)
  health check (advisory)
  adaptive timeout computation
  error handling (consecutive_error_count, total_error_count, health_tracker.record_llm_call)
  tool execution → _execute_tools_sequential/parallel
  tracker.check_orphans()
  tool metrics collection (is_error check, round_tool_calls append)
  _record_round_metrics()
  abort threshold check
  final answer extraction + return

FINALLY BLOCK (6 lines):
  try: self.last_loop_metrics = LoopMetrics(...)
  except: pass
```

### What Differs (only 3 things)

| Aspect | `_autonomous_loop` (responses) | `_autonomous_loop_anthropic` (messages) |
|--------|-------------------------------|----------------------------------------|
| **LLM call** | `self.llm.create_response(input_text, tools, previous_response_id, ...)` | `self.llm.anthropic_messages(messages, system, tools, ...)` |
| **Response parsing** | `output[]` array → `function_call` items, `message.content.output_text` | `content[]` array → `tool_use` items, `text` blocks |
| **State mgmt** | `previous_response_id` (server-side state) + `pending_tool_results` injection | `messages[]` array (client-side) + `FormatAdapter.build_anthropic_tool_result()` + trimming |

---

## Extraction Plan

### Phase 1: `GuardedToolExecutor` (HIGH priority)

**Goal**: Extract tool execution pipeline into standalone, independently testable class.

**New file**: `tools/guarded_tool_executor.py` (~250 lines)

```python
class GuardedToolExecutor:
    """Executes tool calls with guard, cache, tracker, and health integration."""

    def __init__(
        self,
        guard: ToolCallGuard,
        tracker: ToolCallTracker,
        cache: ToolResultCache,
        health_tracker: ModelHealthTracker,
        model: str = "",
    ) -> None:
        self._guard = guard
        self._tracker = tracker
        self._cache = cache
        self._health_tracker = health_tracker
        self._model = model
        self.consecutive_error_count: int = 0  # Moved from DynamicAutonomousAgent

    async def execute_sequential(
        self, dispatcher, fc_list: list[dict]
    ) -> list[tuple[str, str]]:
        """Execute tools sequentially with guard/cache/tracker integration."""
        ...

    async def execute_parallel(
        self, dispatcher, fc_list: list[dict]
    ) -> list[tuple[str, str]]:
        """Execute tools in parallel with batch error semantics."""
        ...
```

**Changes to `dynamic_autonomous.py`**:
- Remove `_execute_tools_sequential` and `_execute_tools_parallel` (~215 lines)
- Both loops create `GuardedToolExecutor` instance, call `executor.execute_sequential()` / `executor.execute_parallel()`
- Read `executor.consecutive_error_count` for abort threshold checks

**Dispatchers**: Move `_SingleSessionDispatcher` and `_MultiSessionDispatcher` to `tools/guarded_tool_executor.py` (they're only used by the executor).

**Test impact**: LOW — Tests call executors through the loop, not directly. Re-export dispatchers from `dynamic_autonomous.py` for backward compat:
```python
from tools.guarded_tool_executor import _SingleSessionDispatcher, _MultiSessionDispatcher
```

**Lines removed from god module**: ~330 (215 executor + 115 dispatchers)
**Lines added**: ~250 (new file) + ~15 (import + instantiation in loops)
**Net reduction**: ~300 lines from god module

### Phase 2: Strategy Pattern for Loop Merge (HIGH priority)

**Goal**: Eliminate 260 lines of copy-paste duplication between the two loops.

**New file**: `tools/loop_strategy.py` (~120 lines)

```python
class LoopStrategy(Protocol):
    """Abstraction over LLM API format differences."""

    def call_llm(self, llm: LLMClient, round_num: int, **kwargs) -> dict:
        """Make the LLM API call. Returns raw response dict."""
        ...

    def parse_tool_calls(self, response: dict) -> list[dict]:
        """Extract tool calls from response in common format [{name, arguments}]."""
        ...

    def parse_text_content(self, response: dict) -> str | None:
        """Extract final text answer from response."""
        ...

    def update_state(self, response: dict, tool_results: list) -> None:
        """Update strategy-specific state (response_id or messages array)."""
        ...

    def get_response_id(self, response: dict) -> str | None:
        """Get response ID for metrics/logging."""
        ...


class ResponsesStrategy:
    """Strategy for /v1/responses API (stateful, previous_response_id)."""

    def __init__(self) -> None:
        self._previous_response_id: str | None = None
        self._pending_tool_results: list = []
    ...


class AnthropicStrategy:
    """Strategy for /v1/messages API (stateless, messages array)."""

    def __init__(self, task: str) -> None:
        self._messages: list[dict] = [{"role": "user", "content": task}]
    ...
```

**Changes to `dynamic_autonomous.py`**:
- Delete `_autonomous_loop_anthropic` entirely (~262 lines)
- Modify `_autonomous_loop` to accept a `LoopStrategy` parameter
- Modify `_run_autonomous_dispatch` to create the appropriate strategy and pass it

**Test impact**: MEDIUM — 20 tests call `_autonomous_loop_anthropic` directly. Options:
1. **(Preferred)** Keep `_autonomous_loop_anthropic` as a thin wrapper that creates `AnthropicStrategy` and calls `_autonomous_loop(strategy=...)`. Zero test breakage.
2. Update tests to call `_autonomous_loop(strategy=AnthropicStrategy(...))`.

**Lines removed**: ~262 (entire Anthropic loop)
**Lines added**: ~120 (strategy file) + ~10 (wrapper method)
**Net reduction**: ~130 lines from god module

### Phase 3: `MCPConnectionManager` (MEDIUM priority)

**Goal**: Extract MCP connection boilerplate shared across 4 public methods.

**New file**: `tools/mcp_connection_manager.py` (~130 lines)

```python
class MCPConnectionManager:
    """Manages MCP discovery, connection, and tool conversion."""

    def __init__(self, mcp_json_path: str) -> None:
        self._mcp_json_path = mcp_json_path

    async def connect_single(self, mcp_name: str) -> tuple[dispatcher, list[dict]]:
        """Connect to single MCP, return dispatcher + openai_tools."""
        ...

    async def connect_multiple(self, mcp_names: list[str]) -> tuple[dispatcher, list[dict]]:
        """Connect to multiple MCPs, return multi-dispatcher + merged tools."""
        ...

    async def discover_and_connect(self) -> tuple[dispatcher, list[dict]]:
        """Auto-discover all MCPs, connect, return dispatcher + all tools."""
        ...
```

**Lines removed from god module**: ~120 (deduplicated connection boilerplate)
**Lines added**: ~130 (new file)
**Net reduction**: ~80 lines (dedup savings + cleaner facade)

### Phase 4: `TokenBudgetManager` (LOW priority)

**Goal**: Extract `_estimate_tokens`, context guard logic, `cumulative_tokens` tracking.

**New file**: `tools/token_budget.py` (~50 lines)

Small utility — only worth doing if Phases 1-3 are complete and the remaining facade is clean enough.

**Lines removed**: ~30
**Net reduction**: ~20 lines

---

## Summary: Expected Outcome

| Metric | Before | Phase 1 | Phase 2 | Phase 3 | Phase 4 |
|--------|--------|---------|---------|---------|---------|
| `dynamic_autonomous.py` | 1,515 | ~1,185 | ~920 | ~840 | ~810 |
| New files | 0 | 1 | 2 | 3 | 4 |
| Max new file size | — | ~250 | ~120 | ~130 | ~50 |
| Duplicate loop code | ~260 | ~260 | **0** | 0 | 0 |
| `LoopMetrics(` copies | 7 | 7 | **2** | 2 | 2 |
| Shared mutable state | 1 (`consecutive_error_count`) | **0** | 0 | 0 | 0 |

**Phase 1 alone delivers 80% of the value.** Phase 2 eliminates the worst duplication. Phases 3-4 are cleanup.

---

## Execution Constraints

1. **TDD discipline**: RED → GREEN → REFACTOR for every extraction
2. **Backward compatibility**: Re-export all public symbols from `dynamic_autonomous.py`
3. **No behavior changes**: Pure structural refactoring — same tests must pass
4. **Atomic commits**: One extraction per commit, full regression between
5. **Safety tag**: Create `v5.1.0-opp51-pre` before starting

---

## Verification Strategy

```bash
# After each phase:
python3 -m pytest tests/ --ignore=tests/standalone -x -q
# Expected: 2167 pass, 0 fail (same as v5.1.0 baseline)

# Architecture guards:
python3 -m pytest tests/test_architecture.py tests/test_arch2_constants_split.py -v

# Coverage must not decrease:
python3 -m pytest tests/ --ignore=tests/standalone \
  --cov=tools --cov-report=term-missing -q
# Expected: tools/ coverage >= 81% (v5.1.0 baseline)
```

---

## Dependencies

| Depends On | Status |
|------------|--------|
| v5.1.0 merged to main | DONE |
| All Round G OPPs complete | DONE |
| 21 test files stable | DONE (2167 pass) |

| Blocks | Why |
|--------|-----|
| Any future OPP touching `dynamic_autonomous.py` | Reduces integration complexity |
| OPP-42 (Token Budget Monitoring) | Phase 4 extracts the seam |
| Performance optimization work | Cleaner modules = easier profiling |

---

## Open Questions

| # | Question | Proposed Answer |
|---|----------|-----------------|
| 1 | Should dispatchers move with executor or stay? | Move — they're only used by executor |
| 2 | Should `_autonomous_loop_anthropic` become a wrapper or be deleted? | Wrapper (zero test breakage) |
| 3 | Should `MCPConnectionManager` use `AsyncExitStack` internally? | Yes — matches current pattern in `autonomous_with_multiple_mcps` |
| 4 | Phase 1 and 2 sequential or parallel? | Sequential — Phase 2 depends on Phase 1's executor extraction |

---

## File Inventory (Post-Refactor)

| File | Purpose | Lines (est) |
|------|---------|-------------|
| `tools/dynamic_autonomous.py` | Facade: public API + `__init__` + routing | ~400 |
| `tools/guarded_tool_executor.py` | Tool execution with guard/cache/tracker/health | ~250 |
| `tools/loop_strategy.py` | `LoopStrategy` protocol + 2 implementations | ~120 |
| `tools/mcp_connection_manager.py` | MCP discovery, connection, tool conversion | ~130 |
| `tools/token_budget.py` | Token estimation + context guard | ~50 |
| `tools/dynamic_autonomous_register.py` | MCP tool registration (unchanged) | 564 |

**Total**: ~1,514 lines across 6 files vs 1,515 in 1 file. Same code, proper SRP.
