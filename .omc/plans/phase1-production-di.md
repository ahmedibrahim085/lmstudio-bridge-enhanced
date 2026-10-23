# Phase 1: Production Code DI — Implementation Plan

> Date: 2026-02-24 | Branch: `fix/server-error-audit` at `405a48a`
> Baseline: ~1405 tests, 89% coverage
> Prerequisite: `docs/TEST_SUITE_FINDINGS.md` Round 2 analysis complete

---

## Problem / Intent

**WHY**: Production code creates real HTTP clients internally with no injection points
(Dependency Inversion Principle violation). This forces 18 of 23 test files to reach
into implementation details to mock, which is fragile and incomplete.

**WHAT WE SOLVE**: The ROOT architectural problem identified in Round 2 — not symptoms.

**THREE FIXES**:
- R-1: `LLMClient.__init__` — accept optional `session` parameter
- R-2: `get_config()` — skip HTTP auto-detection in test context
- R-3: `discover_models()` — accept optional `rest_client` parameter

---

## File Overlap Matrix

| Fix | Files Modified | Overlaps With |
|-----|---------------|---------------|
| R-1 | `llm/llm_client.py`, `tests/test_llm_client_di.py` (new) | **NONE** |
| R-2 | `config_main.py`, `config/constants.py`, `tests/test_config_testing_mode.py` (new) | **NONE** |
| R-3 | `tests/fixtures/model_discovery.py`, `tests/test_constants.py`, `tests/test_model_discovery.py` | **NONE** |

**Decision: ALL THREE CAN RUN IN PARALLEL.** Zero file overlap between any pair.

---

## R-1: Add `session` Parameter to `LLMClient.__init__`

### Problem (with evidence)

`LLMClient.__init__` at `llm/llm_client.py:134-153` creates a real `requests.Session()`
with connection pooling on every instantiation. There is no way to inject a mock session:

```python
# llm/llm_client.py:134-153 (current)
def __init__(self, api_base: Optional[str] = None, model: Optional[str] = None):
    config = get_config()
    self.api_base = api_base or config.lmstudio.api_base
    self.model = model or config.lmstudio.default_model

    # HTTP connection pooling — ALWAYS creates a REAL session
    self.session = requests.Session()
    adapter = HTTPAdapter(pool_connections=10, pool_maxsize=20, ...)
    self.session.mount('http://', adapter)
    self.session.mount('https://', adapter)
```

**Callers in production code** (5 fallback patterns, backward compat critical):
- `main.py:48` — `llm_client = LLMClient()` (composition root)
- `tools/completions.py:57` — `self.llm = llm_client or LLMClient()`
- `tools/vision.py:31` — `self.llm = llm_client or LLMClient()`
- `tools/health.py:81` — `self.llm = llm_client or LLMClient()`
- `tools/embeddings.py:20` — `self.llm = llm_client or LLMClient()`
- `tools/dynamic_autonomous.py:114` — `self.llm = llm_client or LLMClient()`

**Callers in test code** (23 files create `LLMClient()` — all will benefit):
- `tests/test_http_pooling.py` — 8 instances (most exposed)
- `tests/test_resource_cleanup.py` — 6 instances
- `tests/test_opp12_streaming.py`, `test_opp16_native_mcp.py`, etc.

**Current test workaround** (fragile pattern):
```python
# tests/test_opp05_speculative.py:13 — must mock get_config to avoid real URLs
with patch("llm.llm_client.get_config") as mock_config:
    mock_config.return_value.lmstudio.api_base = "http://localhost:1234/v1"
    mock_config.return_value.lmstudio.default_model = "test-model"
    c = LLMClient()
```

### Approach

Add optional `session` parameter to `__init__`. When provided, skip adapter setup.
Track ownership with `_owns_session` flag — only close session if we created it.
Default `session=None` preserves 100% backward compatibility.

```python
# llm/llm_client.py:134 (proposed)
def __init__(self, api_base=None, model=None, session=None):
    config = get_config()
    self.api_base = api_base or config.lmstudio.api_base
    self.model = model or config.lmstudio.default_model

    if session is not None:
        self.session = session
        self._owns_session = False  # Caller owns lifecycle
    else:
        self.session = requests.Session()
        self._owns_session = True   # We own lifecycle
        adapter = HTTPAdapter(pool_connections=10, pool_maxsize=20, ...)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
```

**Session ownership semantics** (`_owns_session` flag):
- `close()` at `llm/llm_client.py:163-172` currently calls `self.session.close()` unconditionally
- With injected sessions, this would close the CALLER's session — a dangerous side effect
- Fix: `close()` only calls `self.session.close()` when `self._owns_session is True`
- `__del__` and `__exit__` delegate to `close()` — inherit the guard automatically

**Alternatives considered and rejected**:
- Factory pattern (`LLMClient.create_for_testing()`): Adds complexity. Optional param is simpler.
- Subclass (`TestLLMClient`): Violates Liskov. Tests should use same class.
- Global "testing mode" flag: Mutable global state. Violates thread safety.

### TDD Plan

**RED** — `tests/test_llm_client_di.py` (new file):

| # | Test | Category | Assertion |
|---|------|----------|-----------|
| 1 | `test_default_creates_real_session` | Happy | `isinstance(client.session, requests.Session)` and `client._owns_session is True` |
| 2 | `test_injected_session_used` | Happy | `client.session is mock_session` and `client._owns_session is False` |
| 3 | `test_injected_session_no_adapter_setup` | Happy | `HTTPAdapter` NOT called when session provided |
| 4 | `test_none_session_creates_real` | Edge | `LLMClient(session=None)` → `_owns_session is True`, creates real session |
| 5 | `test_injected_session_routes_http` | Happy | Call `client.chat_completion(...)`, assert `mock_session.post.called` (verifies injected session is used for actual HTTP, not just stored) |
| 6 | `test_close_skips_injected_session` | Boundary | `client.close()` does NOT call `mock_session.close()` when `_owns_session is False` |
| 7 | `test_close_closes_owned_session` | Happy | `client.close()` DOES call `session.close()` when `_owns_session is True` |
| 8 | `test_context_manager_respects_ownership` | Happy | `with LLMClient(session=mock) as c:` does NOT close injected session on exit |

All tests mock `get_config()` to avoid real URL resolution.

**Key clarification (Architect + Critic feedback)**:
- Test #5 verifies the injected session is actually USED for HTTP traffic (not just identity check like #2)
- Tests #6-8 verify the `_owns_session` guard — injected sessions are NEVER closed by LLMClient

**GREEN** — Edit `llm/llm_client.py`:
- Line 134: Add `session: Optional[requests.Session] = None` parameter
- Line 146-153: Branch — if provided, use it + set `_owns_session = False`; else create real session + set `_owns_session = True`
- Line 163-172 (`close()`): Guard with `if self._owns_session:` before calling `self.session.close()`
- Line 174-179 (`__del__`): Already delegates to `close()` — inherits guard automatically

**REFACTOR** — None expected (minimal change).

### Commits (2)

1. `test(R-1): add DI tests for LLMClient session injection`
2. `feat(R-1): add optional session parameter to LLMClient.__init__`

### Backward Compatibility

- `session=None` default means ALL existing callers work unchanged
- No signature change for positional args (`api_base`, `model` remain positions 1-2)
- `session` is keyword-only in practice (3rd positional, but no caller uses positional)

### NOT an API Surface Method

`LLMClient.__init__` is not in the MANDATORY integration test list
(§5.1 of PLANNING_GUIDELINES.md). Unit tests sufficient.

---

## R-2: Add `LMSTUDIO_TESTING` Env Var to Skip HTTP Auto-Detection

### Problem (with evidence)

`LMStudioConfig.from_env()` at `config_main.py:52-94` calls `_get_first_available_model()`
at line 80 when `DEFAULT_MODEL` env var is not set. This method makes REAL HTTP calls:

```python
# config_main.py:78-81 (current)
if not default_model:
    # Auto-detect: fetch available models and use first non-embedding one
    default_model = cls._get_first_available_model(api_base)
    logger.info(f"Auto-detected default model: {default_model}")
```

`_get_first_available_model()` at `config_main.py:97-134`:
- Line 117-118: `LMSHelper.is_installed()` + `LMSHelper.list_loaded_models()` → real CLI/REST
- If no loaded model found, falls through to HTTP API call

**This means**: Every `get_config()` call in test context (when `DEFAULT_MODEL` is unset)
triggers real HTTP to LM Studio. Called from:
- `llm/llm_client.py:141` — every `LLMClient()` creation
- `llm/model_validator.py:57` — every `ModelValidator()` creation
- `main.py:40` — server startup

**Current test workaround** (repeated 15+ times across test files):
```python
with patch("llm.llm_client.get_config") as mock_config:
    mock_config.return_value.lmstudio.api_base = "http://localhost:1234/v1"
    mock_config.return_value.lmstudio.default_model = "test-model"
```

### Approach

Add `LMSTUDIO_TESTING` env var check in `from_env()`. When set, skip `_get_first_available_model()`
and use `"default"` as the model name. This is safe because LM Studio accepts `"default"` and
routes to whatever model is currently loaded.

**New constant in `config/constants.py`**:
```python
# Testing mode — env var to skip HTTP auto-detection in get_config()
# Used in: config_main.py:from_env() to prevent real HTTP calls during pytest
LMSTUDIO_TESTING_ENV_VAR = "LMSTUDIO_TESTING"
LMSTUDIO_TESTING_DEFAULT_MODEL = "default"
```

**Change in `config_main.py`**:

Note: `os` is already imported at line 2, and `config.constants` imports are at lines 19-22.
Add `LMSTUDIO_TESTING_ENV_VAR, LMSTUDIO_TESTING_DEFAULT_MODEL` to the existing
module-level import from `config.constants` — NO inline imports.

```python
# config_main.py:19-22 (existing, add to this import block)
from config.constants import (
    ...,
    LMSTUDIO_TESTING_ENV_VAR,
    LMSTUDIO_TESTING_DEFAULT_MODEL,
)

# config_main.py:76-81 (modified)
if not default_model:
    # Check testing mode — skip HTTP auto-detection
    if os.environ.get(LMSTUDIO_TESTING_ENV_VAR):
        default_model = LMSTUDIO_TESTING_DEFAULT_MODEL
        logger.debug("Testing mode: using default model (skipped auto-detection)")
    else:
        default_model = cls._get_first_available_model(api_base)
        logger.info(f"Auto-detected default model: {default_model}")
```

**Activation**: Add to `pytest.ini` or `conftest.py`:
```python
# conftest.py (top-level, before any imports that trigger get_config)
import os
os.environ.setdefault("LMSTUDIO_TESTING", "1")
```

**Alternatives considered and rejected**:
- Mock `get_config()` globally: Already done per-test, fragile, duplicated 15+ times
- `reset_config()` in conftest: Doesn't prevent the initial HTTP call
- Config file support: Over-engineered for this problem

### TDD Plan

**RED** — `tests/test_config_testing_mode.py` (new file):

| # | Test | Category | Assertion |
|---|------|----------|-----------|
| 1 | `test_testing_mode_skips_auto_detect` | Happy | With env var set, `_get_first_available_model` NOT called |
| 2 | `test_testing_mode_uses_default_model` | Happy | `config.lmstudio.default_model == "default"` |
| 3 | `test_normal_mode_auto_detects` | Happy | Without env var, `_get_first_available_model` IS called |
| 4 | `test_explicit_model_overrides_testing_mode` | Edge | `DEFAULT_MODEL=foo` + `LMSTUDIO_TESTING=1` → uses `foo` |
| 5 | `test_testing_mode_empty_string` | Edge | `LMSTUDIO_TESTING=""` → treated as falsy, auto-detects |
| 6 | `test_testing_mode_does_not_make_http_calls` | Negative | With env var, zero HTTP calls (mock httpx/requests) |
| 7 | `test_testing_mode_zero_string_is_truthy` | Boundary | `LMSTUDIO_TESTING="0"` → Python truthy, skips auto-detect (document this behavior) |

All tests use `monkeypatch.setenv()` / `monkeypatch.delenv()` for env var isolation.

**GREEN** — Edit `config_main.py:76-81` + `config/constants.py`:
- Add 2 constants to `config/constants.py`
- Add testing mode branch in `from_env()`

**REFACTOR** — None expected.

### Commits (2)

1. `test(R-2): add tests for LMSTUDIO_TESTING config mode`
2. `feat(R-2): skip HTTP auto-detection when LMSTUDIO_TESTING env var set`

### Backward Compatibility

- Without `LMSTUDIO_TESTING` env var: behavior identical to current code
- With `LMSTUDIO_TESTING=1`: returns `"default"` model, no HTTP calls
- `DEFAULT_MODEL` env var still takes priority over both modes

### conftest.py Activation (separate commit in Phase 2)

The `os.environ.setdefault("LMSTUDIO_TESTING", "1")` in conftest.py is a Phase 2
defense-in-depth item (D-1). R-2 only adds the CAPABILITY — activation is separate.

---

## R-3: Add `rest_client` Parameter to `discover_models()`

### Problem (with evidence)

`discover_models()` at `tests/fixtures/model_discovery.py:219-267` creates a real
`LMSRestClient()` on every call:

```python
# tests/fixtures/model_discovery.py:227-228 (current)
rest_client = LMSRestClient()
if rest_client.is_server_available():
    # ... makes real HTTP calls including wake-up pings ...
```

This is called from `test_constants.py:133` via PEP 562 `__getattr__`:
```python
# tests/test_constants.py:131-133 (current)
from tests.fixtures.model_discovery import discover_models
discovered = discover_models()  # ← creates REAL LMSRestClient, sends REAL inference
```

At pytest COLLECTION TIME, `test_e2e_multi_model.py:28-29` imports `REASONING_MODEL` etc.,
triggering `__getattr__` → `_ensure_discovery()` → `discover_models()` → REAL HTTP + wake-up pings.

**Existing callers**:
- `tests/test_constants.py:133` — PEP 562 lazy resolution (COLLECTION TIME)
- `tests/conftest.py:268` — `discovered_models()` fixture (SESSION scope)
- `tests/test_model_discovery.py` — 12 test methods (all mock `LMSRestClient` manually)

### Approach

Add optional `rest_client` parameter. When provided, use it instead of creating a new one.
Default `None` preserves existing behavior.

**Change in `tests/fixtures/model_discovery.py:219`**:
```python
def discover_models(rest_client=None) -> DiscoveredModels:
    if rest_client is None:
        rest_client = LMSRestClient()
    if rest_client.is_server_available():
        # ... existing code uses rest_client ...
```

**Change in `tests/test_constants.py:131-133`** (use injected client):
```python
def _ensure_discovery():
    global _discovery_done
    if _discovery_done:
        return
    _discovery_done = True
    try:
        import os
        from tests.fixtures.model_discovery import discover_models
        # In testing mode, pass None to let discover_models handle it
        # (discover_models will check LMSTUDIO_TESTING internally if needed)
        discovered = discover_models()
        # ... rest unchanged ...
```

Actually — for test_constants.py, the change is minimal. The PEP 562 discovery already
works via `discover_models()`. The key improvement is that `discover_models()` can now
be called with a mock client in `conftest.py:268` and `test_model_discovery.py` tests.

**The REAL fix for collection-time inference** is in Phase 2 (D-1: conftest sets
`LMSTUDIO_TESTING=1` env var before any imports → R-2 prevents get_config HTTP →
R-3 allows discover_models to accept mock client).

### TDD Plan

**RED** — Add to existing `tests/test_model_discovery.py`:

| # | Test | Category | Assertion |
|---|------|----------|-----------|
| 1 | `test_discover_models_uses_injected_client` | Happy | Injected mock client's methods called |
| 2 | `test_discover_models_none_creates_default` | Happy | `None` param creates real `LMSRestClient` |
| 3 | `test_discover_models_injected_client_not_available` | Negative | `client.is_server_available() → False` → falls back to CLI |
| 4 | `test_discover_models_injected_client_raises` | Edge | Client raises → falls back to CLI |
| 5 | `test_conftest_discovered_models_accepts_client` | Happy | `discovered_models` fixture works with injected client |

**GREEN** — Edit `tests/fixtures/model_discovery.py:219`:
- Add `rest_client=None` parameter
- Use provided client or create new one

**REFACTOR** — Update `conftest.py:268` to pass-through (no behavior change yet).

### Commits (2)

1. `test(R-3): add tests for discover_models rest_client injection`
2. `feat(R-3): add optional rest_client parameter to discover_models()`

### Backward Compatibility

- Default `rest_client=None` means ALL existing callers work unchanged
- `conftest.py:268` calls `discover_models()` without args → unchanged
- `test_constants.py:133` calls `discover_models()` without args → unchanged
- `test_model_discovery.py` existing tests mock `LMSRestClient` internally → unchanged

---

## Execution Plan

### Parallel Execution (Wave 1)

| Track | Fix | Agent | Commits | Files |
|-------|-----|-------|---------|-------|
| A | R-1 (LLMClient session DI) | `python-engineer` | 2 | `llm/llm_client.py`, new test |
| B | R-2 (LMSTUDIO_TESTING env var) | `python-engineer` | 2 | `config_main.py`, `config/constants.py`, new test |
| C | R-3 (discover_models client DI) | `python-engineer` | 2 | `tests/fixtures/model_discovery.py`, `tests/test_model_discovery.py` |

**Total: 6 atomic commits (3 RED + 3 GREEN)**

### Post-Parallel Verification

After all 3 tracks complete:

```bash
# Full test suite — all must pass
pytest tests/ --ignore=tests/standalone -q --tb=short --timeout=120

# Coverage — must not decrease from 89%
pytest --cov=llm --cov=tools --cov=config --cov=model_registry --cov=mcp_client --cov=utils \
  --cov-report=term-missing tests/ --ignore=tests/standalone --timeout=120

# Lint — zero errors
ruff check config/ utils/ llm/ tools/ model_registry/ mcp_client/ tests/

# Import check — server starts
python3 -c "from llm.llm_client import LLMClient; print('OK')"
```

---

## Acceptance Criteria (Testable)

| # | Criterion | How to Verify |
|---|-----------|---------------|
| AC-1 | `LLMClient(session=mock_session)` uses injected session | `assert client.session is mock_session` |
| AC-2 | `LLMClient()` still creates real session (backward compat) | `assert isinstance(client.session, requests.Session)` |
| AC-3 | `LMSTUDIO_TESTING=1` env var prevents HTTP auto-detection | Mock `_get_first_available_model`, assert NOT called |
| AC-4 | Without `LMSTUDIO_TESTING`, auto-detection works normally | Assert `_get_first_available_model` IS called |
| AC-5 | `discover_models(rest_client=mock)` uses injected client | Assert mock client methods called |
| AC-6 | `discover_models()` still creates real client (backward compat) | Existing test_model_discovery tests pass unchanged |
| AC-7 | Full test suite passes after all changes | `pytest` exit code 0 |
| AC-8 | Coverage >= 89% (not decreased) | `pytest --cov` report |
| AC-9 | Zero ruff errors | `ruff check` exit code 0 |
| AC-10 | All new code has >= 90% coverage | `--cov-report=term-missing` shows no significant gaps |

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| R-1 breaks `close()`/`__del__` for injected sessions | LOW | MEDIUM | `_owns_session` flag guards close(); Tests #6-8 verify ownership semantics |
| R-2 conftest activation causes side effects | LOW | HIGH | R-2 only adds capability; activation is Phase 2 |
| R-3 changes break existing test_model_discovery tests | LOW | MEDIUM | Default `None` preserves behavior; run existing tests |
| Parallel agents create merge conflicts | NONE | — | Zero file overlap verified via matrix |
| `DEFAULT_MODEL` env var interaction with testing mode | LOW | LOW | Test #4 explicitly verifies priority |

---

## Verification Steps

1. After RED commits: `pytest tests/test_llm_client_di.py tests/test_config_testing_mode.py -v` → all FAIL
2. After GREEN commits: same command → all PASS
3. Full suite: `pytest tests/ --ignore=tests/standalone -q --tb=short --timeout=120`
4. Coverage: `pytest --cov=llm --cov=config --cov-report=term-missing tests/ --ignore=tests/standalone`
5. Lint: `ruff check llm/ config/ config_main.py tests/fixtures/ tests/test_model_discovery.py`

---

## Changelog

| Date | Change |
|------|--------|
| 2026-02-24 | Initial plan created from TEST_SUITE_FINDINGS.md Round 2 analysis |
| 2026-02-24 | **Architect + Critic review improvements applied**: |
| | [HIGH] R-1: Added `_owns_session` flag — `close()` only closes sessions LLMClient created (prevents caller session destruction) |
| | [MEDIUM] R-2: Changed to module-level imports (`os` at line 2, constants at lines 19-22) — removed inline `import os as _os` |
| | [MEDIUM] R-1: Clarified test #5 to verify `mock_session.post.called` after `chat_completion()` (HTTP routing, not just identity) |
| | [MEDIUM] R-1: Added test #8 for context manager ownership semantics; split test #6/#7 into owns vs. doesn't-own |
| | [ADVISORY] R-2: Added test #7 for `LMSTUDIO_TESTING="0"` truthy edge case (Python `os.environ.get()` returns `"0"` which is truthy) |
