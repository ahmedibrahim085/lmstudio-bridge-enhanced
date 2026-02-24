# Test Suite Infrastructure — Root Cause Analysis

> Date: 2026-02-24 | Status: **ROOT CAUSE IDENTIFIED**
>
> Trigger: Running `pytest tests/ --ignore=tests/standalone --ignore=tests/integration` caused
> 3x `zai-org/glm-4.6v-flash` and 2x `mistralai/ministral-3-3b` instances loaded in LM Studio.
> No models were reused. No models were unloaded after tests finished.

---

## CORRECTION (IMPORTANT)

**Initial speculation that duplicate glm instances came from "nano-agent MCP tools" was WRONG.**
nano-agent was NOT working during this session. All model instances are caused by
OUR test suite and OUR infrastructure. Root cause tracing below proves this.

---

## Executive Summary

**One root architectural problem causes ALL observed symptoms**: the test infrastructure
has no enforced boundary between test categories (unit / integration / e2e).

There is no structural mechanism preventing unit tests from making real HTTP calls,
triggering model discovery (with wake-up pings that send real inference), or loading
models into LM Studio. The `@pytest.mark.unit` marker exists but is advisory only —
it doesn't enforce HTTP isolation.

---

## Evidence Collected (from LM Studio server log)

**Log file**: `~/.lmstudio/server-logs/2026-02/2026-02-24.1.log`
**Log size**: 21,685 lines generated during ~8.5 min test run (08:57 → 09:06 UTC)

### Raw Numbers

| Metric | Count | Source |
|--------|-------|--------|
| `listLoaded` API calls | ~60 | Tests checking model status |
| `listDownloadedModels` API calls | ~39 | Tests checking model availability |
| "Model not found" errors | 61 | Tests trying fake model names |
| Real inference calls (ministral) | ~11 | chat completion + v1/responses |
| Real inference calls (glm-4.6v) | ~15+ | v1/responses with tool calls |
| Model unload events | **0** | Nothing cleaned up |
| Total API calls to LM Studio | ~173 | During "unit" test run |

### Fake Models Hitting Real API (61 errors)

These model names appeared in "not found in downloaded models" errors:
- `test-model` — most frequent (~30+ times)
- `qwen/qwen3-coder-30b` — ~9 times (stale constant reference)
- `nonexistent-model` — ~2 times
- `huge-model-70b` — 1 time
- `large-model` — 1 time
- `other-model` — 1 time

### Real Inference Timeline

```
08:58:05  ministralai/ministral-3-3b  — chat completion (1 msg)  ← WAKE-UP PING
08:58:07  massive listLoaded/listDownloadedModels burst starts
08:59:05  ministral-3-3b — v1/responses (10 calls in 8 seconds)  ← E2E TEST
08:59:44  zai-org/glm-4.6v-flash — v1/responses starts           ← E2E TEST
09:00:02  glm-4.6v-flash — generates filesystem__list_directory tool call
09:00:03  glm-4.6v-flash — more v1/responses calls
...continues through 09:05:00
```

---

## Root Cause Chain (5 linked causes, 1 root)

### ROOT: No enforced test category boundary

The test suite has ONE `tests/conftest.py` serving ALL test types. There is no
structural enforcement that:
- Unit tests NEVER make real HTTP calls
- E2E test imports don't trigger side effects during pytest collection
- Model discovery/lifecycle fixtures only activate for appropriate test categories

### RC-1: `test_e2e_multi_model.py` triggers discovery at COLLECTION TIME

**The smoking gun.** `test_e2e_multi_model.py:28-29` imports dynamic model constants:

```python
from tests.test_constants import (
    REASONING_MODEL,    # ← DYNAMIC (PEP 562 __getattr__)
    CODING_MODEL,       # ← DYNAMIC
    SMALL_MODEL,        # ← DYNAMIC
    VISION_MODEL,       # ← DYNAMIC
    ...
)
```

These are PEP 562 lazy-resolved attributes in `test_constants.py:98-167`. On first
access, `__getattr__` calls `_ensure_discovery()` → `discover_models()` →
`_wake_up_loaded_role_models()`:

```
pytest collection
  → imports test_e2e_multi_model.py (module-level import)
  → from tests.test_constants import REASONING_MODEL
  → test_constants.__getattr__("REASONING_MODEL")
  → _ensure_discovery()                           [test_constants.py:116]
  → discover_models()                              [model_discovery.py:219]
  → LMSRestClient().is_server_available()          [REAL HTTP GET]
  → rest_client.list_all_models()                  [REAL HTTP GET]
  → _wake_up_loaded_role_models()                  [model_discovery.py:184]
  → httpx.post("/v1/chat/completions", ...)        [REAL INFERENCE to every loaded model]
```

**This happens BEFORE any `@pytest.mark.e2e` skip markers are evaluated**, because
module imports happen during collection, not during test execution.

**Evidence**: ministral-3-3b chat completion at 08:58:05 (the very first inference in
the log, ~1 minute into test run) — this is the wake-up ping sending `"content": "hi"`
to ministral because it was already loaded and assigned to a role.

### RC-2: E2E tests run with real inference (not skipped)

`test_e2e_multi_model.py` tests use `DynamicAutonomousAgent` which calls
`LLMClient.create_response()` → `/v1/responses` endpoint with real models.
The `conftest.py:211-216` `pytest_runtest_setup` auto-skips e2e tests only
if LM Studio is NOT available. During the observed run, LM Studio WAS running,
so these tests executed with real inference.

**Evidence**: glm-4.6v-flash `/v1/responses` calls with `filesystem__list_directory`
tool calls starting at 08:59:44 — this is `DynamicAutonomousAgent` exercising the
full MCP tool dispatch pipeline with a real model.

### RC-3: Tests mock CLI path but not REST path

After the test infra overhaul, `LMSHelper.load_model()` now tries **REST first**,
then falls back to CLI. But several test files only mock `subprocess.run` (the CLI path):

| File | Mocks | Missing |
|------|-------|---------|
| `test_memory_pressure.py` | `subprocess.run` | `_get_rest_client` |
| `test_concurrent_loading.py:56` | `subprocess.run` + `_get_rest_client` | **OK** |
| `test_failure_scenarios.py` | `_get_rest_client` (autouse) + `subprocess.run` | **OK** |

`test_memory_pressure.py` calls `LMSHelper.load_model("huge-model-70b")` with only
`subprocess.run` mocked. The REST path escapes → real HTTP POST to LM Studio →
"not found" error for the fake model name.

**Evidence**: "huge-model-70b" and "large-model" in the 61 "not found" errors match
the fake model names in `test_memory_pressure.py:39,71`.

### RC-4: No global HTTP safety net

No `@pytest.fixture(autouse=True)` blocks outbound HTTP during unit tests.
Each test file is responsible for its own mocking. Some do it properly
(`test_failure_scenarios.py` has `_prevent_rest_api_leaks` autouse fixture),
most don't.

Without a global safety net, any test that creates `LLMClient()` without mocking
`get_config()` gets a real LM Studio URL, and any HTTP method call escapes.

### RC-5: `model_lifecycle` not autouse → zero cleanup

`conftest.py:280`:
```python
@pytest.fixture(scope="session")
def model_lifecycle(discovered_models):  # NOT autouse=True
```

No test in the suite requests this fixture. The `unload_models_we_loaded()` teardown
is dead code. Models loaded during tests are never cleaned up.

**Evidence**: Zero `unloadModel` events in the entire 21,685-line log.

---

## Causal Dependency Graph

```
No enforced test category boundary (ROOT)
  │
  ├── test_constants.py PEP 562 triggers discover_models() at collection (RC-1)
  │     └── _wake_up_loaded_role_models() sends REAL inference (ministral chat completion)
  │
  ├── E2E tests not isolated from unit test runs (RC-2)
  │     └── DynamicAutonomousAgent calls create_response() → glm v1/responses + tool calls
  │           └── LM Studio auto-loads or uses existing model instances → 3x glm
  │
  ├── Tests mock CLI but not REST path (RC-3)
  │     └── LMSHelper.load_model() REST path escapes → 61 "not found" errors
  │
  ├── No HTTP safety net for unit tests (RC-4)
  │     └── Any unmocked LLMClient() or LMSHelper call reaches real LM Studio
  │
  └── model_lifecycle not autouse (RC-5)
        └── Loaded models NEVER cleaned up → accumulation (0 unload events)
```

---

## Answers to Deep Questions

### Q1: Are we solving SYMPTOMS or ROOT PROBLEMS?

**The 5 originally identified problems (P-1 through P-5) are ALL SYMPTOMS of ONE
root architectural problem: no enforced boundary between test categories.**

Fixing individual symptoms would be band-aids:
- Making `model_lifecycle` autouse → band-aid (symptom: RC-5)
- Adding `_prevent_rest_api_leaks` to each test → band-aid (symptom: RC-3/RC-4)
- Mocking REST client in test_memory_pressure.py → band-aid (symptom: RC-3)

**The ROOT fix** is structural:
1. Enforce test category boundaries (separate conftest hierarchy)
2. Block outbound HTTP BY DEFAULT in unit test conftest
3. Only allow real HTTP in explicitly marked integration/e2e tests
4. Prevent module-level imports from triggering side effects during collection

### Q2: Are these bugs related? How? When did coupling happen?

**YES — all 5 root causes are causally linked** (see dependency graph above).

**Timeline of coupling**:
1. **Original design**: Tests assumed LMSHelper used CLI (subprocess) only. Mocking
   `subprocess.run` was sufficient. Tests worked.
2. **Test infra overhaul**: `discover_models()` rewritten to REST-first with wake-up
   pings (D-5). `LMSHelper.load_model()` gained REST-first path. But existing test
   mocks were NOT updated to cover the new REST path.
3. **PEP 562 addition**: `test_constants.py` gained lazy model resolution via
   `__getattr__` calling `discover_models()`. This created a collection-time side
   effect that no one anticipated.
4. **Result**: Tests that previously worked (mocking subprocess only) now leak
   through the REST path. And mere test COLLECTION triggers real inference.

### Q3: Bad coding, architecture, or approach? Does fixing require code changes?

**ARCHITECTURE PROBLEM** — in both test infrastructure AND production code.

**Test infrastructure needs** (MUST fix):
1. Separate conftest hierarchy: `tests/conftest.py` (common), unit-level conftest
   (HTTP blocked), integration conftest (real fixtures)
2. Global autouse fixture that blocks outbound HTTP for non-e2e tests
3. `_wake_up_loaded_role_models()` must NOT run during collection
4. E2E tests should be in a separate directory (e.g., `tests/e2e/`)

**Production code contributes to the problem** (SHOULD fix for testability):
1. `LMSHelper.load_model()` dual-path (REST + CLI) requires mocking at TWO levels —
   tests must know internal implementation details to mock properly
2. `LLMClient.__init__` creates a real `requests.Session` without DI option —
   no way to inject a mock session at construction time
3. `get_config()` returns real LM Studio URLs even in test context —
   no test profile or override mechanism

The production code isn't BROKEN — it works correctly. But its tight coupling to
`requests.Session` and `get_config()` makes proper test isolation harder than
necessary. Fixing the test infrastructure properly benefits from minor production
code changes to improve testability (dependency injection for session/config).

---

---

## ROUND 2: Deeper Root Cause Analysis

> "Are we solving SYMPTOMS, or ROOT PROBLEMS in the architecture design/decision?"

### The First Round Was Still Describing Symptoms

Round 1 identified "no enforced test category boundary" as the root cause. That's **partially correct
but still one level too shallow**. Let me explain why.

"No enforced test category boundary" is an OBSERVATION about test infrastructure. But WHY do
we need enforced boundaries in the first place? Because **production code creates real I/O
internally with no injection points**. If production code accepted injected dependencies, tests
would be naturally safe regardless of category boundaries.

### The TRUE Root: Dependency Inversion Principle Violation in Production Code

Every production class that does I/O creates its own HTTP client internally:

| Class | Constructor/Method | What it creates | DI available? |
|-------|-------------------|-----------------|---------------|
| `LLMClient.__init__` (llm_client.py:134-153) | `get_config()` + `requests.Session()` | Real HTTP session pointing to `http://localhost:1234/v1` | **NO** — `session` is always created internally |
| `LMSHelper._get_rest_client` (lms_helper.py:218-226) | `LMSRestClient()` | Real `httpx.Client()` with connection pooling | **NO** — class-level factory, no override |
| `LMSRestClient.__init__` (lms_helper.py:54) | `httpx.Client()` | Real HTTP client | **NO** — hardcoded in constructor |
| `discover_models` (model_discovery.py:227-228) | `LMSRestClient()` | Real HTTP + real inference pings to every loaded model | **NO** — no parameter to inject mock client |
| `get_config().from_env()._get_first_available_model` (config_main.py:97-134) | `LMSHelper.list_loaded_models()` | Real CLI/REST calls | **NO** — config layer making HTTP calls |

**The pattern is consistent**: every I/O boundary creates concrete implementations internally.
There is ZERO dependency injection for HTTP clients anywhere in the production codebase.

This means the ONLY way to prevent real HTTP in tests is to **reach into implementation details
and mock internal methods** (`_get_rest_client`, `subprocess.run`, etc.). This is fragile by
definition — every new HTTP path in production code requires a corresponding mock in tests.

### Exposure Quantification

| Category | Count | Details |
|----------|-------|---------|
| Test files creating `LLMClient()` | **23** | Across all test directories |
| Test files with REST leak protection | **5** | `test_failure_scenarios`, `test_concurrent_loading`, `test_performance_benchmarks`, `test_lms_rest_client`, `test_model_lifecycle` |
| Unprotected files in main `tests/` | **~8** | `test_memory_pressure`, `test_bug6_bug8`, `test_resource_cleanup`, `test_silent_failure_logging`, `test_opp14_extended_thinking`, `test_opp16_native_mcp`, `test_opp11_anthropic_endpoint`, `test_opp12_streaming` |
| Unprotected files in `tests/standalone/` | **~10** | Excluded with `--ignore=tests/standalone` but still dangerous if run directly |

**18 of 23 test files that create `LLMClient()` have NO REST leak protection.**

### Re-Evaluating Round 1 Fixes Against Root Problem

| Round 1 Fix | What it does | Solves Root? | Why / Why Not |
|-------------|-------------|--------------|---------------|
| F-1: Move e2e files | Hides them from `--ignore` | **NO** — moves the symptom, doesn't fix the design. E2E file still triggers inference if imported. |
| F-2: Lazy imports in test_constants | Delays PEP 562 trigger | **NO** — discovery still runs real HTTP when accessed. Just delays WHEN, not WHETHER. |
| F-3: `_prevent_rest_api_leaks` per-file | Mocks `_get_rest_client` in one file | **NO** — whack-a-mole. Must be added to each of 18+ files individually. Breaks when new HTTP paths added. |
| F-4: Global HTTP blocking fixture | Blocks all outbound HTTP for non-e2e | **COMPENSATORY** — works around the DI gap. Good defense-in-depth but doesn't fix production code. |
| F-5: `tests/e2e/` directory | Separates test categories | **PARTIALLY** — good hygiene but doesn't prevent HTTP leaks in unit tests that create `LLMClient()`. |
| F-6: `model_lifecycle` autouse for e2e | Cleans up after e2e runs | **NO** — fixes cleanup but not prevention. |
| F-7: DI for `LLMClient.session` | Accept optional `session` param | **YES** — removes the need for internal mocking |
| F-8: Test config profile | `get_config()` returns safe URLs in tests | **YES** — prevents real URLs from reaching production code |
| F-9: Unify `load_model` to single path | Remove dual REST/CLI | **PARTIALLY** — simplifies mock surface but doesn't solve the DI problem |

**The original fix plan had the priorities BACKWARDS.** Phase 3 ("optional, production code")
contains the TRUE root fixes. Phases 1-2 are compensatory measures.

### Q1 Revisited: Symptoms or ROOT Problems?

**Round 1 was solving symptoms.** The 5 RCs (RC-1 through RC-5) are all consequences of one
architectural decision: **production code owns its I/O dependencies internally**.

If `LLMClient.__init__` accepted an optional `session` parameter, tests could inject a mock
session at construction time — no need for `_prevent_rest_api_leaks`, no need for global
HTTP blocking, no need for test category separation to prevent leaks.

If `discover_models()` accepted an optional `rest_client` parameter, PEP 562 collection-time
discovery would be harmless — it would use the injected mock client.

If `get_config()` had a test profile (e.g., `TESTING=1` env var → returns `api_base="http://test-sentinel:0/v1"`),
no test would ever reach real LM Studio accidentally.

**The compensatory fixes (Phases 1-2) are still VALUABLE as defense-in-depth**, but they should
be SECONDARY to the production code DI fixes, not primary.

### Q2 Revisited: When Did the Coupling Happen?

**Timeline with git evidence:**

```
Nov 2025 (original design):
  LMSHelper.load_model() — CLI only (subprocess.run)
  LLMClient() — creates requests.Session() internally (no DI)
  get_config() — returns real LM Studio URLs (no test profile)
  COUPLING LEVEL: LOW — one mock point (subprocess.run) per test

Feb 23 2026 22:18 (b8ec121):
  LMSRestClient added with TTL cache
  _get_rest_client() introduced as class-level factory
  COUPLING LEVEL: MEDIUM — now TWO mock points needed (subprocess + REST)

Feb 23 2026 22:32 (321c96c):
  discover_models() rewritten to REST-first + wake-up ping
  _wake_up_loaded_role_models() sends httpx.post to every loaded model
  PEP 562 in test_constants.py now triggers REAL INFERENCE at collection time
  COUPLING LEVEL: HIGH — HTTP leaks from test collection, not just execution

Feb 23 2026 (same day, test infra overhaul):
  _prevent_rest_api_leaks pattern added to 5 of 23 files
  18 files left unprotected — REST path escapes silently
  COUPLING LEVEL: HIGH (partially mitigated in 5 files)
```

**The critical amplification was on Feb 23 2026.** The REST-first rewrite (`321c96c`)
doubled the HTTP surface area but only ~22% of test files (5/23) were updated with
corresponding mocks. This is a PROCESS gap: production code changed I/O paths without
a corresponding update to ALL consumers.

**WHY did this happen?** Because the original architecture had no DI. Adding a new I/O
path (REST) required manually updating every test file's mocks. With DI, adding REST
would be transparent to tests — they'd inject a mock regardless of how many paths exist
internally.

### Q3 Revisited: Architecture Problem? Need Code Changes?

**YES — this is an architecture design problem that requires production code changes.**

The test infrastructure fixes are necessary but insufficient alone:

**Production code changes needed (ROOT fixes):**

1. **`LLMClient.__init__` DI** (llm_client.py:134):
   ```python
   def __init__(self, api_base=None, model=None, session=None):
       # ... existing code ...
       if session is not None:
           self.session = session
       else:
           self.session = requests.Session()
           # ... adapter setup ...
   ```
   Impact: Tests inject mock session at construction. No internal mocking needed.
   Backward compat: 100% — default `session=None` preserves current behavior.

2. **`get_config()` test profile** (config_main.py:301):
   ```python
   def get_config() -> Config:
       global _config
       if _config is None:
           with _config_lock:
               if _config is None:
                   _config = Config.from_env()
       return _config
   ```
   The `from_env()` at line 52 reads `LMSTUDIO_HOST` / `LMSTUDIO_PORT` env vars.
   In test context, `_get_first_available_model()` at line 97 makes REAL HTTP calls.
   Fix: Add `LMSTUDIO_TESTING=1` env var check → skip HTTP auto-detection, use "default".

3. **`discover_models()` injectable client** (model_discovery.py:219):
   ```python
   def discover_models(rest_client=None) -> DiscoveredModels:
       if rest_client is None:
           rest_client = LMSRestClient()
       # ... use rest_client instead of creating new one ...
   ```
   Impact: `test_constants.py:_ensure_discovery()` can inject a mock.

**Test infrastructure changes (DEFENSE-IN-DEPTH, still needed):**

4. Global `autouse` HTTP-blocking fixture for non-e2e tests
5. E2E tests in separate `tests/e2e/` directory with own conftest
6. `model_lifecycle` autouse for e2e conftest only

### Revised Fix Plan (Correct Priority Order)

**Phase 1: Fix the ROOT — Production Code DI (3 commits)**

| # | Fix | File | Impact |
|---|-----|------|--------|
| R-1 | Add `session` parameter to `LLMClient.__init__` | `llm/llm_client.py:134` | Tests inject mock session; eliminates need for transport-level mocking |
| R-2 | Add `LMSTUDIO_TESTING` env var to `get_config()` | `config_main.py:52-94` | Prevents auto-detection HTTP calls in test context |
| R-3 | Add `rest_client` parameter to `discover_models()` | `tests/fixtures/model_discovery.py:219` | PEP 562 discovery can use injected mock |

**Phase 2: Defense-in-Depth — Test Infrastructure (4 commits)**

| # | Fix | File | Impact |
|---|-----|------|--------|
| D-1 | Add global `autouse` HTTP-blocking conftest for unit tests | `tests/conftest.py` | Safety net even if DI is bypassed |
| D-2 | Move e2e tests to `tests/e2e/` with own conftest | `tests/e2e/conftest.py` | Clean category separation |
| D-3 | Make `model_lifecycle` autouse in e2e conftest | `tests/e2e/conftest.py` | Automatic cleanup after e2e runs |
| D-4 | Add `_prevent_rest_api_leaks` to remaining 8 unprotected files | 8 test files | Belt-and-suspenders for existing tests |

**Phase 3: Simplify — Remove Compensatory Complexity (2 commits)**

| # | Fix | File | Impact |
|---|-----|------|--------|
| S-1 | Remove per-file `_prevent_rest_api_leaks` after global fixture exists | 5 test files | Reduce duplication — global fixture handles it |
| S-2 | Simplify PEP 562 in test_constants.py to use injected client | `tests/test_constants.py:131` | No HTTP at collection time even without conftest |

---

## Recommended Fix Plan (Priority Order)

### Phase 1: Fix the ROOT — Production Code DI

| # | Fix | Impact | Effort |
|---|-----|--------|--------|
| R-1 | Add optional `session` param to `LLMClient.__init__` | Eliminates transport-level mocking | 1 hr |
| R-2 | Add `LMSTUDIO_TESTING=1` env var to skip HTTP auto-detection in `get_config()` | Prevents config-time HTTP calls | 30 min |
| R-3 | Add optional `rest_client` param to `discover_models()` | PEP 562 collection-time safe | 30 min |

### Phase 2: Defense-in-Depth — Test Infrastructure

| # | Fix | Impact | Effort |
|---|-----|--------|--------|
| D-1 | Global `autouse` HTTP-blocking fixture in `tests/conftest.py` | Safety net for all non-e2e tests | 1 hr |
| D-2 | Move e2e tests to `tests/e2e/` with own conftest | Clean test category separation | 2 hr |
| D-3 | `model_lifecycle` autouse in e2e conftest only | Automatic cleanup | 30 min |
| D-4 | Add `_prevent_rest_api_leaks` to 8 unprotected test files | Belt-and-suspenders | 30 min |

### Phase 3: Simplify — Remove Compensatory Complexity

| # | Fix | Impact | Effort |
|---|-----|--------|--------|
| S-1 | Remove per-file `_prevent_rest_api_leaks` (global handles it) | Reduce duplication | 15 min |
| S-2 | Simplify `test_constants.py` PEP 562 to use injected client | No HTTP at collection | 30 min |

---

## Changelog

| Date | Change |
|------|--------|
| 2026-02-24 | Initial findings from LM Studio log analysis |
| 2026-02-24 | CORRECTION: removed false nano-agent speculation, all instances are ours |
| 2026-02-24 | ROOT CAUSE IDENTIFIED: PEP 562 collection-time discovery + missing test boundaries |
| 2026-02-24 | Complete causal chain traced with file:line evidence for all 5 root causes |
| 2026-02-24 | Answered user's 3 deep questions (symptoms vs root, coupling timeline, code changes) |
| 2026-02-24 | **ROUND 2**: Deeper analysis — production DI violation identified as TRUE root cause |
| 2026-02-24 | Reversed fix priority order: production DI first, test infra as defense-in-depth |
| 2026-02-24 | Quantified exposure: 18 of 23 LLMClient-creating test files unprotected |
| 2026-02-24 | Traced coupling timeline via git: REST-first rewrite (321c96c) was amplification point |
