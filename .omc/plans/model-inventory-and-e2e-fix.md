# Plan: Model Loading Inventory + E2E Test Fix (Rev 2)

**Branch**: `fix/server-error-audit`
**Date**: 2026-02-24
**Safety tag**: `v3.5.1-inventory-pre`
**Revision**: 2 — Addresses Architect (8/10) and Critic (7.2/10) feedback

---

## Revision Changelog

| Rev | Changes | Reason |
|-----|---------|--------|
| 1 | Initial plan | — |
| 2 | Expanded Fix A to ALL e2e methods (GAP 2); kept `_snapshot_loaded_models`/`_unload_new_models` as defense-in-depth (GAP 1); reuse `LONG_TEST_TIMEOUT` instead of new `E2E_TEST_TIMEOUT` (GAP 5); added idempotent unload + double-unload-scope tests (GAP 3); made test #2 behavior-based (GAP 3); clarified test_session_cleanup.py is ADDITIVE (GAP 4); added TOCTOU risk mitigation | Architect Concern 1-5, Critic GAP 1-5 |

---

## Problem Statement

### Problem A: E2E Test Hangs (NOT Missing POST Timeouts)

**Root cause analysis**: All `session.post()` calls in `llm/llm_client.py` already have `timeout=timeout` (default `DEFAULT_LLM_TIMEOUT=58s` at `constants.py:239`). The 9 POST calls (lines 354, 421, 556, 671, 849, 920, 1001, 1078, 1169) all pass timeout correctly.

The real issue: E2E test methods call autonomous functions with excessive `max_rounds` that exceed the 120s pytest timeout:

| Line | Method | max_rounds | Worst case (× 58s) |
|------|--------|------------|---------------------|
| 288 | `test_multi_mcp_with_model` | 30 (hardcoded) | 1,740s |
| 354 | `test_backward_compatibility_no_model` | **no param** → `DEFAULT_MAX_ROUNDS=10000` | **580,000s** |
| 493 | `test_complete_analysis_implementation_workflow` | 20 (hardcoded) | 1,160s |
| 512 | same method, second call | 15 (hardcoded) | 870s |

**Evidence**:
- Stack trace shows hang at `llm_client.py:671` → `session.post()` with `timeout=timeout` (58s) — timeout IS present
- `DEFAULT_MAX_ROUNDS = 10000` at `config/constants.py:262`
- `dynamic_autonomous.py:308`: `max_rounds: int = DEFAULT_MAX_ROUNDS` — production default
- `LONG_TEST_TIMEOUT = 300` exists at `constants.py:286` but is NOT used by any e2e test
- No e2e test has `@pytest.mark.timeout()` override

### Problem B: No Model Loading Inventory

**Root cause**: `ModelLifecycleManager._loaded_by_us` (`model_lifecycle.py:28`) is a bare `set[str]` — no metadata, no timestamps, no test context, no scope tracking. Cleanup is imprecise: either "preserve initial" (missed models) or "unload everything" (too aggressive). No audit trail for debugging VRAM leaks.

**Evidence**:
- `model_lifecycle.py:28`: `self._loaded_by_us: set[str] = set()`
- `model_lifecycle.py:134`: `self._loaded_by_us.add(model_name)` — just a name, no context
- `conftest.py:318-330`: `_unload_new_models()` filters by initial snapshot — preserves pre-existing models
- No JSON persistence for post-mortem debugging

---

## Fix A: E2E Test Configuration — ALL Methods (Sequential — 2 commits)

### A-1: Add E2E_TEST_MAX_ROUNDS constant + apply to ALL e2e methods

**Problem/Intent**: E2E tests hang because `max_rounds` values (30, 20, 15, and default 10000) far exceed the 120s pytest timeout when combined with 58s per-round POST timeout.

**Approach**:
1. Add `E2E_TEST_MAX_ROUNDS = 5` to `config/constants.py` — enough to prove autonomous loop works without exhausting timeout. 5 rounds × 58s = 290s (within `LONG_TEST_TIMEOUT=300`)
2. Reuse existing `LONG_TEST_TIMEOUT = 300` (at `constants.py:286`) — NO new duplicate constant
3. Apply `@pytest.mark.timeout(LONG_TEST_TIMEOUT)` to ALL `@pytest.mark.e2e` test methods
4. Replace all hardcoded `max_rounds` in e2e tests with `E2E_TEST_MAX_ROUNDS`

**Files**:
| File | Change | Lines |
|------|--------|-------|
| `config/constants.py` | Add `E2E_TEST_MAX_ROUNDS=5` + `__all__` entry | ~3 lines |
| `tests/test_e2e_multi_model.py` | Import constants; add `@pytest.mark.timeout(LONG_TEST_TIMEOUT)` to ALL e2e methods; replace all `max_rounds=N` with `E2E_TEST_MAX_ROUNDS` | ~20 lines changed |

**Specific changes in `test_e2e_multi_model.py`**:

| Line | Before | After |
|------|--------|-------|
| 105 | `max_rounds=SHORT_MAX_ROUNDS` | `max_rounds=E2E_TEST_MAX_ROUNDS` |
| 145 | `max_rounds=SHORT_MAX_ROUNDS` | `max_rounds=E2E_TEST_MAX_ROUNDS` |
| 196 | `max_rounds=10` | `max_rounds=E2E_TEST_MAX_ROUNDS` |
| 208 | `max_rounds=15` | `max_rounds=E2E_TEST_MAX_ROUNDS` |
| 222 | `max_rounds=10` | `max_rounds=E2E_TEST_MAX_ROUNDS` |
| 288 | `max_rounds=30` | `max_rounds=E2E_TEST_MAX_ROUNDS` |
| 354 | (no max_rounds → default 10000) | `max_rounds=E2E_TEST_MAX_ROUNDS` |
| 493 | `max_rounds=20` | `max_rounds=E2E_TEST_MAX_ROUNDS` |
| 512 | `max_rounds=15` | `max_rounds=E2E_TEST_MAX_ROUNDS` |

Plus add `@pytest.mark.timeout(LONG_TEST_TIMEOUT)` to every method decorated with `@pytest.mark.e2e`.

**Alternatives rejected**:
- "Add new `E2E_TEST_TIMEOUT=300`" — duplicates existing `LONG_TEST_TIMEOUT=300` (Critic GAP 5)
- "Just increase pytest --timeout globally" — masks the problem, slows all tests
- "Reduce DEFAULT_MAX_ROUNDS globally" — changes production behavior for a test-only issue

---

## Fix B: Model Loading Inventory (Sequential — 4 commits)

### B-1: Constants for inventory configuration

**Problem/Intent**: Inventory needs configurable paths and settings, all in `config/constants.py` per rule 09.

**Approach**: Add constants for inventory file path pattern, scope names, and reason strings.

**File**: `config/constants.py`

```python
# Model Loading Inventory — tracks every model load/unload with audit trail
# Used in: tests/fixtures/model_inventory.py
MODEL_INVENTORY_DIR = ".omc/model-inventory"
MODEL_INVENTORY_SCOPE_SESSION = "session"
MODEL_INVENTORY_SCOPE_MODULE = "module"
MODEL_INVENTORY_SCOPE_CLASS = "class"
MODEL_INVENTORY_SCOPE_FUNCTION = "function"
MODEL_INVENTORY_REASON_FIXTURE = "fixture"
MODEL_INVENTORY_REASON_LIFECYCLE = "ensure_model_for_phase"
MODEL_INVENTORY_REASON_DIRECT = "direct"
```

### B-2: ModelLoadInventory class with JSON persistence

**Problem/Intent**: Need a structured inventory that tracks every model load with metadata and persists to JSON per session for debugging.

**Approach**: New module `tests/fixtures/model_inventory.py` with:

1. `ModelLoadRecord` dataclass:
   - `model_name: str` — model identifier
   - `loaded_at: str` — ISO 8601 timestamp
   - `reason: str` — why loaded (fixture, lifecycle, direct)
   - `test_id: str` — pytest node ID (e.g., `tests/test_foo.py::TestBar::test_baz`)
   - `scope: str` — pytest scope (function, class, module, session)
   - `phase: str` — test phase (unit, integration, e2e)
   - `metadata: dict` — extensible: VRAM estimate, model size, etc.
   - `unloaded: bool` — whether model has been unloaded
   - `unloaded_at: str | None` — when unloaded

2. `ModelLoadInventory` class:
   - `_records: list[ModelLoadRecord]` — full audit trail
   - `_active: dict[str, ModelLoadRecord]` — currently loaded models (keyed by model_name)
   - `_session_id: str` — unique session identifier (timestamp-based)
   - `_inventory_dir: Path` — from `MODEL_INVENTORY_DIR` constant

   Methods:
   - `record_load(model_name, reason, test_id, scope, phase, **meta) -> None`
   - `record_unload(model_name) -> None` — marks record as unloaded with timestamp. **IDEMPOTENT**: if model already marked as unloaded, no-op (no LMSHelper call).
   - `get_active_for_scope(scope, test_id=None) -> list[str]` — models loaded at given scope
   - `unload_scope(scope, test_id=None) -> int` — unload models loaded at that scope, returns count. **IDEMPOTENT**: skips already-unloaded models.
   - `unload_all() -> int` — final sweep, unloads everything active. **IDEMPOTENT**.
   - `save() -> None` — persist full audit trail to JSON file. Creates directory on demand.
   - `summary() -> dict` — for logging: total loads, active, unloaded, by scope

   JSON file: `{MODEL_INVENTORY_DIR}/{session_id}.json` — one file per test session.

**File**: `tests/fixtures/model_inventory.py` (NEW)

**Dependencies**:
- `config/constants.py` (inventory constants)
- `utils/lms_helper.py` (LMSHelper.unload_model for actual unloading)

### B-3: Wire ModelLifecycleManager through inventory

**Problem/Intent**: `ensure_model_for_phase()` at `model_lifecycle.py:90-139` loads models but records only to a bare set. It should record to the inventory with full metadata.

**Approach**:
1. `ModelLifecycleManager.__init__` accepts optional `inventory: ModelLoadInventory` parameter (DI)
2. `ensure_model_for_phase()` accepts optional `test_id` and `scope` params, calls `inventory.record_load()` after successful load
3. `unload_models_we_loaded()` calls `inventory.record_unload()` for each model
4. Backward compatible: if no inventory passed, falls back to current `_loaded_by_us` set behavior

**File**: `tests/fixtures/model_lifecycle.py`

| Line | Before | After |
|------|--------|-------|
| 27 | `def __init__(self) -> None:` | `def __init__(self, inventory: ModelLoadInventory | None = None) -> None:` |
| 28 | `self._loaded_by_us: set[str] = set()` | + `self._inventory = inventory` |
| 90 | `def ensure_model_for_phase(self, model_name, ttl=None)` | + optional `test_id=""`, `scope="session"`, `phase="unit"` params |
| 134 | `self._loaded_by_us.add(model_name)` | + `if self._inventory: self._inventory.record_load(...)` |
| 153 | `LMSHelper.unload_model(model_name)` | + `if self._inventory: self._inventory.record_unload(model_name)` |

### B-4: Wire conftest.py fixtures with scoped inventory cleanup

**Problem/Intent**: Fixtures need to create the inventory at session start, pass it through the lifecycle manager, clean up at scope boundaries (class/module), and save the JSON at session end.

**Approach**:
1. Session-scoped fixture `model_inventory` — creates `ModelLoadInventory`, yields it, saves JSON at teardown
2. Wire `model_lifecycle` fixture to receive and pass `model_inventory` to `ModelLifecycleManager`
3. Update `_session_model_cleanup` to ALSO call `inventory.unload_all()` — layered ON TOP of existing `_snapshot_loaded_models` / `_unload_new_models` defense-in-depth (Architect Concern 2)
4. Add module-scoped fixture `_module_model_cleanup` that calls `inventory.unload_scope("module")` at teardown
5. Fixture `require_any_model` passes test context (test ID, scope) when loading through lifecycle

**IMPORTANT (Rev 2)**: `_snapshot_loaded_models()` and `_unload_new_models()` are PRESERVED as defense-in-depth. They catch models loaded OUTSIDE the inventory system (direct `LMSHelper.load_model()` calls, standalone `ModelLifecycleManager` instances). The inventory is the primary mechanism; the snapshot is the safety net.

**File**: `tests/conftest.py`

Changes:
- Add `model_inventory` session fixture (creates inventory, saves at teardown)
- Modify `model_lifecycle` fixture: `mgr = ModelLifecycleManager(inventory=model_inventory)`
- Update `_session_model_cleanup`: add `inventory.unload_all()` BEFORE existing `_unload_new_models()` call
- Add `_module_model_cleanup` autouse module fixture: `inventory.unload_scope("module")`
- **KEEP** `_snapshot_loaded_models()` and `_unload_new_models()` as safety net

**File**: `tests/fixtures/model_management.py`

Changes:
- `require_any_model` passes `request.node.nodeid` and scope context to lifecycle manager

---

## TDD Plan

### RED Tests

#### `tests/test_e2e_timeout_config.py` (2 tests)

| # | Test | Asserts |
|---|------|---------|
| 1 | `test_all_e2e_methods_have_timeout_marker` | ALL methods with `@pytest.mark.e2e` in `test_e2e_multi_model.py` also have `@pytest.mark.timeout` |
| 2 | `test_no_e2e_method_uses_excessive_max_rounds` | **Behavior-based** (Architect Rec #4): No e2e test method passes `max_rounds` > `E2E_TEST_MAX_ROUNDS` to autonomous functions. Inspects source for literal values. |

#### `tests/test_model_inventory.py` (15 tests)

| # | Test | Asserts |
|---|------|---------|
| 1 | `test_record_load_adds_to_active` | After `record_load()`, model is in `_active` dict |
| 2 | `test_record_load_stores_metadata` | Record has correct timestamp, reason, test_id, scope, phase |
| 3 | `test_record_unload_marks_inactive` | After `record_unload()`, model removed from `_active`, `unloaded=True`, `unloaded_at` set |
| 4 | `test_get_active_for_scope_filters_correctly` | Returns only models loaded at the given scope |
| 5 | `test_unload_scope_unloads_only_that_scope` | `unload_scope("class")` unloads class-scoped models, preserves session-scoped |
| 6 | `test_unload_scope_returns_count` | Returns correct count of models unloaded |
| 7 | `test_unload_all_clears_everything` | All active models get `unload_model()` called |
| 8 | `test_save_creates_json_file` | JSON file created at expected path with correct structure |
| 9 | `test_save_includes_all_records` | JSON contains both load and unload records with all metadata fields |
| 10 | `test_summary_returns_correct_counts` | Summary dict has total, active, unloaded, by-scope breakdowns |
| 11 | `test_duplicate_load_updates_record` | Loading same model twice updates existing record (no duplicates in active) |
| 12 | `test_unload_scope_handles_failure_gracefully` | Continues unloading if one model fails, logs warning |
| 13 | `test_record_unload_idempotent` | Calling `record_unload()` on already-unloaded model is a no-op — no `LMSHelper.unload_model()` call (Architect Rec #3) |
| 14 | `test_unload_scope_idempotent` | Calling `unload_scope("class")` twice does not double-unload — second call returns 0 (Architect Rec #5) |
| 15 | `test_save_creates_directory_on_demand` | `save()` works even if `MODEL_INVENTORY_DIR` doesn't exist yet |

#### `tests/test_session_cleanup.py` — ADDITIVE tests (3 new, 7 existing PRESERVED)

Existing 7 tests remain unchanged (they test `_snapshot_loaded_models` and `_unload_all_models` defense-in-depth). 3 new tests added:

| # | Test | Asserts |
|---|------|---------|
| NEW-1 | `test_inventory_cleanup_unloads_all_at_session_end` | `inventory.unload_all()` is called at session teardown |
| NEW-2 | `test_module_cleanup_unloads_module_scope` | Module-scoped fixture calls `inventory.unload_scope("module")` |
| NEW-3 | `test_lifecycle_records_to_inventory` | `ensure_model_for_phase()` calls `inventory.record_load()` with correct metadata |

---

## Commit Plan (7 commits)

| # | Type | Message | Fix |
|---|------|---------|-----|
| 1 | test | `test(e2e-timeout): RED tests for e2e timeout and max_rounds configuration` | A RED |
| 2 | fix | `fix(e2e): use E2E_TEST_MAX_ROUNDS and LONG_TEST_TIMEOUT for all e2e tests` | A GREEN |
| 3 | test | `test(inventory): RED tests for model loading inventory system (15 tests)` | B RED |
| 4 | feat | `feat(inventory): add ModelLoadInventory with JSON persistence per session` | B-1 + B-2 GREEN |
| 5 | feat | `feat(lifecycle): wire ModelLifecycleManager through inventory with DI` | B-3 GREEN |
| 6 | feat | `feat(conftest): add scoped inventory cleanup fixtures (preserves defense-in-depth)` | B-4 GREEN |
| 7 | style | `style: fix lint warnings in new inventory code` | cleanup |

---

## File Overlap Matrix (Parallelism Analysis)

| File | Fix A | Fix B-1 | Fix B-2 | Fix B-3 | Fix B-4 |
|------|-------|---------|---------|---------|---------|
| `config/constants.py` | ✓ | ✓ | | | |
| `tests/test_e2e_multi_model.py` | ✓ | | | | |
| `tests/fixtures/model_inventory.py` | | | ✓ (NEW) | | |
| `tests/fixtures/model_lifecycle.py` | | | | ✓ | |
| `tests/conftest.py` | | | | | ✓ |
| `tests/fixtures/model_management.py` | | | | | ✓ |

**Verdict**: Fix A and Fix B share `config/constants.py` → **SEQUENTIAL**. Within Fix B, B-2→B-3→B-4 are sequential (dependency chain). Fix A goes first (smaller, unblocks e2e testing).

---

## Verification

```bash
# Safety tag
git tag v3.5.1-inventory-pre -m "Checkpoint before inventory + e2e fix"

# After all commits — unit tests
pytest tests/ --ignore=tests/standalone -q --tb=short --timeout=120

# New tests specifically
pytest tests/test_model_inventory.py tests/test_e2e_timeout_config.py tests/test_session_cleanup.py -v --timeout=60

# E2E with live LM Studio (now uses LONG_TEST_TIMEOUT=300)
pytest tests/test_e2e_multi_model.py -v -s --timeout=300

# Lint
ruff check config/constants.py tests/fixtures/model_inventory.py tests/fixtures/model_lifecycle.py tests/conftest.py tests/fixtures/model_management.py tests/test_e2e_multi_model.py tests/test_model_inventory.py tests/test_e2e_timeout_config.py tests/test_session_cleanup.py

# Coverage — new code must be >= 90%
pytest --cov=tests/fixtures --cov-report=term-missing tests/test_model_inventory.py tests/test_session_cleanup.py tests/test_lifecycle_wiring.py --timeout=60
```

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Inventory adds overhead to each model load | Minimal — just appending to a list and dict update |
| JSON file grows large with many sessions | One file per session, old files can be pruned |
| Scope tracking complexity | Scope passed explicitly by fixtures, not inferred |
| Backward compat — tests not using inventory | `ModelLifecycleManager` falls back to bare set if no inventory |
| Module-scoped fixture may conflict with session-scoped | All unload methods are IDEMPOTENT — double-unload is a no-op |
| TOCTOU between record_load and actual LMSHelper.load_model | record_load called AFTER successful LMSHelper.load_model (line 134 in model_lifecycle.py is after line 132 success check) |
| Removing snapshot functions breaks existing tests | **MITIGATED (Rev 2)**: snapshot functions are PRESERVED as defense-in-depth |
| E2E tests still too slow with max_rounds=5 | Budget: 5 × 58s = 290s < LONG_TEST_TIMEOUT (300s). If LM Studio is faster, test completes sooner. |
