# Test Infrastructure Overhaul — Discussion Log & Decisions

> Date: 2026-02-23
> Status: DISCUSSION COMPLETE — ready for implementation planning
> Context: LM Studio hammered with ~14K model polls and ~1,118 "not found" errors per test session

---

## Root Causes Identified

| # | Root Cause | Evidence | Severity |
|---|-----------|----------|----------|
| RC-1 | **Leaky mocks** — tests patch `subprocess.run` but NOT `_get_rest_client()`. Code tries REST API FIRST at `lms_helper.py:384`, bypassing subprocess mock → real HTTP to LM Studio with fake model names | 486 "not found" lines in 10s from `test_performance_benchmarks.py` | CRITICAL |
| RC-2 | **conftest.py cache reset** — `conftest.py:48-64` autouse fixture resets `ModelValidator._class_cache` before AND after EVERY test, making 30s TTL cache completely useless | Cache reset 1348x per session | CRITICAL |
| RC-3 | **LMSRestClient zero cache** — `list_all_models()` makes a fresh HTTP GET on every call. No caching at all | 14,345 "Returning N models" polls in log | HIGH |
| RC-4 | **_ensure_model_loaded() amplification** — JIT guard in `llm_client.py:170-208` calls `is_model_loaded()` + optionally `ensure_model_loaded_with_verification()` → up to 4 GET `/api/v1/models` per single invocation | 4x amplification per LLM API call | HIGH |
| RC-5 | **Hardcoded model names** — 24 test files with ~175 references to fake/non-existent model names (`test-model`, `qwen/qwen3-coder-30b`, etc.) | 924 "test-model not found", 42 "qwen/qwen3-coder-30b not found" | HIGH |

---

## Native API Metadata (from `/api/v1/models`)

### Available Fields (per model, loaded AND unloaded)

| Field | Type | Example | Use For |
|-------|------|---------|---------|
| `type` | string | `"llm"`, `"embedding"` | Filter LLMs vs embeddings |
| `key` | string | `"mistralai/ministral-3-3b"` | Unique model identifier |
| `publisher` | string | `"mistralai"` | Grouping |
| `display_name` | string | `"Ministral 3 3B"` | Human display |
| `architecture` | string | `"qwen3"`, `"glm4v"` | Model family |
| `params_string` | string/null | `"3B"`, `"80B"`, `null` | Size selection |
| `size_bytes` | int | `2986817071` | VRAM budget, prefer smallest |
| `max_context_length` | int | `262144` | Context requirements |
| `format` | string | `"gguf"`, `"mlx"` | Load compatibility |
| `quantization.name` | string | `"Q4_K_M"`, `"4bit"` | Quality/size trade-off |
| `capabilities.vision` | bool | `true`/`false` | Vision test requirements |
| `capabilities.trained_for_tool_use` | bool | `true`/`false` | Tool-use test requirements |
| `loaded_instances` | array | `[{id, config}]` | Check if loaded + count duplicates |
| `loaded_instances[].config.context_length` | int | `131072` | Actual loaded context |
| `variants` | array | `["model@4bit"]` | Available quantizations |

### NOT Available in API

| Missing Capability | Workaround |
|-------------------|------------|
| Idle/active status | 1-token wake-up ping (`POST /v1/chat/completions`, `max_tokens=1`) |
| `capabilities.reasoning` | Does not exist — name-matching on `key` field |
| `capabilities.thinking` | Does not exist — name-matching on `key` field |
| `capabilities.coding` | Does not exist — name-matching on `key` field |
| Load time estimate | Not available, track empirically |

### Capability Keys (exhaustive — all 33 models checked)

Only **two** capability keys exist across the entire model library:
- `vision`
- `trained_for_tool_use`

No other capability keys exist. Confirmed by scanning all models.

---

## Decisions (D-1 through D-18)

### D-1: Root Causes — Fix All Five
**Question**: Which root causes to fix?
**Decision**: All 5 (leaky mocks, cache reset, zero cache, amplification, hardcoded names). No partial fixes.

### D-2: Hardcoded Models — Zero Tolerance
**Question**: Should we keep any hardcoded model names?
**Decision**: **NO HARD CODED MODELS.** Not in tests, not in mocks, nowhere. All model references from dynamic discovery at runtime.

### D-3: Model Discovery Timing — Once Per Session
**Question**: When do we discover available models?
**Decision**: Once per pytest session (session-scoped fixture). Call `/api/v1/models`, build full inventory, cache for entire session.

### D-4: Model Selection Strategy — Prefer Smallest
**Question**: How to choose which model to use for a test?
**Decision**: Prefer smallest model that fits. Priority:
1. Already loaded (zero load cost)
2. Smallest `size_bytes` from downloaded models with required capabilities

### D-5: Idle Detection — Wake-Up Ping
**Question**: How to verify a model is actually active, not idle?
**Decision**: Send a 1-token wake-up ping (`POST /v1/chat/completions`, `max_tokens=1`) to verify model is responsive before declaring it "loaded and active". Native API does NOT expose idle/active status.

### D-6: Mock Behavior — No Invented Models
**Question**: Should mocks use fake model names?
**Decision**: Mocks follow the same discovery pattern. Use realistic model structures (matching API response schema) but NEVER leak real HTTP requests to LM Studio. No invented model names like `test-model`.

### D-7: Load Tracking — Unload Only Ours
**Question**: Who manages loading/unloading?
**Decision**: Session-level `ModelLifecycleManager` tracks every model loaded by the test session. At teardown, unload ONLY those models. Never unload pre-existing models.

### D-8: Between-Test Reuse — Keep Loaded
**Question**: Should we unload between individual tests?
**Decision**: Keep models loaded within a session if upcoming tests need them. Only unload at session end (or if different model needed and VRAM is full).

### D-9: Test Organization — Layers AND Phases
**Question**: How to organize tests?
**Decision**: Two dimensions:
- **Layers**: unit (mocked, no LM Studio), integration (real API calls), e2e (full workflows)
- **Phases**: Unit first, integration second, e2e last
- Via `pytest_collection_modifyitems` hook for ordering
- Markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.e2e`

### D-10: Capabilities — Structured API First
**Question**: How to determine model capabilities?
**Decision**: Use structured metadata from API wherever possible. Three reliability tiers:
- **Tier 1 (100%)**: `type`, `capabilities.vision`, `capabilities.trained_for_tool_use`
- **Tier 2 (100%)**: `params_string`, `size_bytes`, `max_context_length`
- **Tier 3 (best-effort)**: Name-matching on `key` for thinking/coding roles

### D-11: Thinking/Reasoning Detection — Hybrid
**Question**: API has no `capabilities.reasoning`. How to detect?
**Decision**: **Hybrid approach:**
- Default: Name-match on `key` field
- Override: Env vars take priority when set
- Resolution: env var → already-loaded match → name-match smallest → skip tests

### D-12: Role Keywords
**Question**: Which keywords map to which roles?
**Decision**:

| Role | Detection Method | Keywords (if name-based) |
|------|-----------------|-------------------------|
| chat | Any LLM not matching other roles | N/A — default fallback |
| vision | `capabilities.vision == true` | None — structured API |
| tool-use | `capabilities.trained_for_tool_use == true` | None — structured API |
| thinking | Name-match on `key` | `thinking`, `r1`, `think`, `reasoning` |
| coding | Name-match on `key` | `coder`, `devstral`, `codestral` |
| embedding | `type == "embedding"` | None — structured API |

### D-13: Env Var Override Names
**Question**: What env vars for explicit model override?
**Decision**:
```
LMS_TEST_THINKING_MODEL=<model-key>
LMS_TEST_CODING_MODEL=<model-key>
LMS_TEST_CHAT_MODEL=<model-key>
LMS_TEST_VISION_MODEL=<model-key>
LMS_TEST_EMBEDDING_MODEL=<model-key>
```

### D-14: Duplicate Cleanup — At Session Start
**Question**: Clean up duplicate instances (e.g., 59 nomic-embed copies)?
**Decision**: Yes. Run `cleanup_duplicates()` once at session start. Detect `:N` suffixed instances, unload all duplicates keeping only the first.

### D-15: Global Reruns — Remove
**Question**: `pytest.ini` has `--reruns 2 --reruns-delay 5` globally.
**Decision**: Remove global reruns. Replace with targeted `@pytest.mark.flaky(reruns=N)` only on genuinely flaky tests.

### D-16: Cache Reset — Stop Per-Test Reset
**Question**: conftest.py resets ModelValidator cache between every test.
**Decision**: Stop resetting between every test. Only reset at session boundaries or when explicitly needed.

### D-17: File Scope — 32 Files
**Question**: Which files will be modified?
**Decision**: 32 files total:
- 7 infrastructure (conftest.py, pytest.ini, pyproject.toml, config/constants.py, model_validator.py, fixtures/model_discovery.py [new], fixtures/model_lifecycle.py [new])
- 24 test files (all containing hardcoded model names)
- 1 production file (llm/model_validator.py for cache fix)

### D-18: API Completeness Confirmed
**Question**: Does the native API have reasoning/thinking capability fields?
**Decision**: No. Only `vision` and `trained_for_tool_use` exist. Full metadata available for both loaded AND unloaded models. Confirms D-11 hybrid approach.

---

## Decision Summary Table

| # | Topic | Decision |
|---|-------|----------|
| D-1 | Root causes | Fix all 5 |
| D-2 | Hardcoded models | Zero tolerance — all dynamic |
| D-3 | Discovery timing | Once per pytest session |
| D-4 | Model selection | Prefer loaded, then smallest that fits |
| D-5 | Idle detection | 1-token wake-up ping |
| D-6 | Mock behavior | No invented models, no leaked HTTP |
| D-7 | Load tracking | Track what we load, unload only ours |
| D-8 | Between-test reuse | Keep loaded within session |
| D-9 | Test organization | Layers (unit/integration/e2e) AND phases (ordered) |
| D-10 | Capabilities | Structured API metadata first |
| D-11 | Thinking detection | Hybrid: name-match + env var override |
| D-12 | Role keywords | thinking/coding = name-match; vision/tools/embedding = API |
| D-13 | Env var names | `LMS_TEST_{ROLE}_MODEL` |
| D-14 | Duplicate cleanup | At session start, keep first instance only |
| D-15 | Global reruns | Remove, use targeted @flaky |
| D-16 | Cache reset | Stop per-test reset |
| D-17 | File scope | 32 files (7 infra + 24 test + 1 production) |
| D-18 | API completeness | Only vision + tools structured; rest = name-match |
