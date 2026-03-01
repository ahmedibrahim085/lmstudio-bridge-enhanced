# Round D Implementation Plan (v4.0.0)

## Context

All 18 OPPs complete (v3.5.0), test infrastructure overhauled (1509 tests, ~91% coverage). Round D adds 4 independent, backward-compatible quick wins. Combined RICE: 138.1, all LOW effort.

**Branch**: `fix/server-error-audit` → new branch `feat/round-d-v4`

---

## Pre-flight

```bash
git tag v3.5.0-round-d-pre -m "Checkpoint before Round D"
```

---

## OPP-22: Single-Model Lookup (RICE: 56)

**Problem**: Every model lookup fetches ALL models then filters. No single-model query.

**Files to modify**:
- `utils/lms_helper.py` — Add `LMSRestClient.get_model(key)` after L123, refactor `is_model_loaded()` at L114-123
- `llm/llm_client.py` — Refactor `get_model_info()` at L1245+ to use enriched cache

**Approach**: Cache-first lookup — search `_models_cache` by key, fetch only on miss/expired.

```python
# New method in LMSRestClient (after L123)
def get_model(self, model_key: str) -> Optional[Dict[str, Any]]:
    """Get single model by key. Cache-first, fetch on miss."""
    if self._models_cache is not None:
        now = time.time()
        if (now - self._models_cache_time) < LMS_REST_MODELS_CACHE_TTL:
            for m in self._models_cache:
                if m.get("key") == model_key:
                    return m
            return None
    models = self.list_all_models()
    if models is None:
        return None
    for m in models:
        if m.get("key") == model_key:
            return m
    return None
```

**Refactor `is_model_loaded()`** to delegate:
```python
def is_model_loaded(self, model_key: str) -> Optional[bool]:
    model = self.get_model(model_key)
    if model is None:
        return None if self.list_all_models() is None else False
    return len(model.get("loaded_instances", [])) > 0
```

**RED tests** (`tests/test_opp22_single_model_lookup.py`):

| Test | Asserts |
|------|---------|
| `test_get_model_cache_hit` | Found in cache, no HTTP |
| `test_get_model_cache_miss_fetches` | Cache empty → fetches → finds |
| `test_get_model_not_found` | Not in cache or API → None |
| `test_get_model_cache_expired` | Stale cache → re-fetches |
| `test_get_model_key_matching` | Exact key match, not substring |
| `test_is_model_loaded_uses_get_model` | Delegates internally |
| `test_is_model_loaded_loaded_true` | `loaded_instances` non-empty → True |
| `test_is_model_loaded_unloaded_false` | `loaded_instances` empty → False |
| `test_is_model_loaded_not_found` | Model not in list → False |
| `test_is_model_loaded_api_unavailable` | API error → None |

**Commits**: `test(OPP-22): RED` → `feat(OPP-22): GREEN` → `refactor(OPP-22): REFACTOR`

---

## OPP-23: Streaming Usage Tracking (RICE: 44)

**Problem**: Streaming methods yield chunks but discard token usage stats. Non-streaming returns usage.

**Files to modify**:
- `llm/sse_parser.py` — Add `StreamUsage` dataclass + `parse_sse_stream_with_usage()` generator
- `config/constants.py` — Add `SSE_USAGE_KEY = "usage"`

**Approach**: LM Studio includes `usage` in the final data chunk before `[DONE]`. Add a new generator that wraps `parse_sse_stream()`, detects usage in chunks, and returns it as the generator's return value (via `StopIteration.value`). Keep existing `parse_sse_stream()` unchanged.

```python
# New in sse_parser.py
@dataclass(frozen=True)
class StreamUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    @classmethod
    def from_dict(cls, data: dict) -> "StreamUsage":
        return cls(
            prompt_tokens=data.get("prompt_tokens", 0),
            completion_tokens=data.get("completion_tokens", 0),
            total_tokens=data.get("total_tokens", 0),
        )

def parse_sse_stream_with_usage(
    response: requests.Response,
) -> Generator[dict[str, Any], None, StreamUsage | None]:
    """Wraps parse_sse_stream, captures usage from final chunk."""
    usage: StreamUsage | None = None
    for chunk in parse_sse_stream(response):
        if SSE_USAGE_KEY in chunk and chunk.get(SSE_USAGE_KEY) is not None:
            usage = StreamUsage.from_dict(chunk[SSE_USAGE_KEY])
        yield chunk
    return usage
```

**RED tests** (`tests/test_opp23_streaming_usage.py`):

| Test | Asserts |
|------|---------|
| `test_stream_usage_fields` | Has prompt/completion/total_tokens |
| `test_stream_usage_from_dict` | Constructs from dict |
| `test_stream_usage_defaults_zero` | Missing keys → 0 |
| `test_stream_usage_frozen` | Immutable dataclass |
| `test_captures_usage_from_final_chunk` | Usage in last chunk → captured |
| `test_yields_all_content_chunks` | Content chunks yielded normally |
| `test_no_usage_returns_none` | No usage in stream → None |
| `test_done_sentinel_consumed` | `[DONE]` never yielded |
| `test_empty_stream_none_usage` | Empty stream → None usage |

**Commits**: `test(OPP-23): RED` → `feat(OPP-23): GREEN` → `refactor(OPP-23): REFACTOR`

---

## OPP-26: Advanced Sampling Parameters (RICE: 20)

**Problem**: Only `temperature`, `top_p`, `max_tokens` supported. Missing `min_p`, `top_k`.

**Files to modify**:
- `config/constants.py` — Add 8 sampling constants
- `tools/completions.py` — Extend `_validate_generation_params()` at L28-45, add params to MCP tools
- `llm/llm_client.py` — Add `min_p`, `top_k` to all 7 methods (L267-1089)

**Approach**: Optional params (None = don't send). Conditional payload inclusion matching existing temperature pattern.

**Constants** (config/constants.py):
```python
DEFAULT_MIN_P = None
DEFAULT_TOP_K = None
MIN_MIN_P = 0.0
MAX_MIN_P = 1.0
MIN_TOP_K = 1
MAX_TOP_K = 1000
ERROR_MIN_P_OUT_OF_RANGE = "min_p must be between {min} and {max}, got {value}"
ERROR_TOP_K_OUT_OF_RANGE = "top_k must be between {min} and {max}, got {value}"
```

**Validation** (tools/completions.py:28-45):
```python
def _validate_generation_params(
    temperature: float, max_tokens: int,
    min_p: Optional[float] = None, top_k: Optional[int] = None,
) -> None:
    # ... existing validation ...
    if min_p is not None and not MIN_MIN_P <= min_p <= MAX_MIN_P:
        raise ValueError(ERROR_MIN_P_OUT_OF_RANGE.format(...))
    if top_k is not None and not MIN_TOP_K <= top_k <= MAX_TOP_K:
        raise ValueError(ERROR_TOP_K_OUT_OF_RANGE.format(...))
```

**Payload pattern** (each of 7 LLMClient methods):
```python
if min_p is not None:
    payload["min_p"] = min_p
if top_k is not None:
    payload["top_k"] = top_k
```

**Methods to update** (all add `min_p: Optional[float] = None, top_k: Optional[int] = None`):
1. `chat_completion()` L267
2. `text_completion()` L370
3. `create_response()` L572
4. `anthropic_messages()` L787
5. `stream_chat_completion()` L861
6. `stream_create_response()` L932
7. `stream_anthropic_messages()` L1013

**RED tests** (`tests/test_opp26_sampling_params.py`):

| Test | Asserts |
|------|---------|
| `test_valid_min_p_accepted` | 0.5 passes |
| `test_min_p_below_zero_rejected` | -0.1 raises ValueError |
| `test_min_p_above_one_rejected` | 1.5 raises ValueError |
| `test_min_p_none_skips` | None → no error |
| `test_valid_top_k_accepted` | 40 passes |
| `test_top_k_below_one_rejected` | 0 raises ValueError |
| `test_top_k_above_max_rejected` | 1001 raises ValueError |
| `test_top_k_none_skips` | None → no error |
| `test_min_p_in_chat_payload` | min_p=0.1 → in payload |
| `test_top_k_in_chat_payload` | top_k=40 → in payload |
| `test_none_not_in_payload` | None → not in payload |
| `test_both_in_payload` | Both set → both present |
| `test_stream_chat_min_p` | Streaming also gets min_p |
| `test_create_response_top_k` | create_response gets top_k |

**Commits**: `test(OPP-26): RED` → `feat(OPP-26): GREEN` → `refactor(OPP-26): REFACTOR`

---

## OPP-30: Echo Load Config (RICE: 18)

**Problem**: `load_model()` returns `{success, instance_id}` but not the actual GPU/memory config.

**Files to modify**:
- `utils/lms_helper.py` — Add `_fetch_model_config()` helper, modify `load_model()` at L137-193

**Approach**: After successful load, invalidate cache, re-fetch, extract `loaded_instances[-1].config`.

```python
# New helper in LMSRestClient
def _fetch_model_config(self, model_key: str) -> Optional[Dict[str, Any]]:
    """Fetch load config from latest loaded instance."""
    self.invalidate_cache()
    models = self.list_all_models()
    if models is None:
        return None
    for m in models:
        if m.get("key") == model_key:
            instances = m.get("loaded_instances", [])
            if instances:
                return instances[-1].get("config", {})
            return None
    return None
```

**Modified `load_model()` returns**: Add `"config": config` to all return dicts (success, already_loaded, and failure paths).

**RED tests** (`tests/test_opp30_echo_load_config.py`):

| Test | Asserts |
|------|---------|
| `test_load_returns_config` | Successful load includes config dict |
| `test_already_loaded_returns_config` | already_loaded=True includes config |
| `test_config_has_expected_fields` | Config has gpu/context_length/etc. |
| `test_config_from_latest_instance` | Uses last `loaded_instances` entry |
| `test_config_none_no_instances` | No instances → config=None |
| `test_config_none_failed_load` | Failed load → config=None |
| `test_config_none_refetch_fails` | Re-fetch fails → config=None |
| `test_cache_invalidated_after_load` | Cache cleared after success |

**Commits**: `test(OPP-30): RED` → `feat(OPP-30): GREEN` → `refactor(OPP-30): REFACTOR`

---

## File Overlap Matrix

| File | OPP-22 | OPP-23 | OPP-26 | OPP-30 |
|------|--------|--------|--------|--------|
| `config/constants.py` | — | add SSE_USAGE_KEY | add 8 sampling constants | — |
| `llm/llm_client.py` | refactor get_model_info (L1245+) | — | add params to 7 methods (L267-1089) | — |
| `llm/sse_parser.py` | — | add StreamUsage + new generator | — | — |
| `utils/lms_helper.py` | add get_model (L123+), refactor is_model_loaded (L114) | — | — | add _fetch_model_config, modify load_model (L137) |
| `tools/completions.py` | — | — | extend validation + MCP tools | — |

**Verdict**: All 4 touch different methods/lines. Safe for sequential execution with clean commits per OPP.

---

## Execution Order

```
1. Pre-flight: safety tag
2. OPP-22 (3 commits) — utils/lms_helper.py + llm/llm_client.py
3. OPP-30 (3 commits) — utils/lms_helper.py (different methods)
4. OPP-23 (3 commits) — llm/sse_parser.py + config/constants.py
5. OPP-26 (3 commits) — llm/llm_client.py + tools/completions.py + config/constants.py
6. Post-merge: full regression, coverage check, VERSION bump to 4.0.0
```

OPP-22 before OPP-30 because OPP-30's `_fetch_model_config()` can optionally reuse `get_model()` from OPP-22.

---

## Post-Merge Gate

```bash
# Full regression
pytest tests/ --ignore=tests/standalone --ignore=tests/integration -x -q

# New OPP tests
pytest tests/test_opp22_single_model_lookup.py tests/test_opp23_streaming_usage.py \
       tests/test_opp26_sampling_params.py tests/test_opp30_echo_load_config.py -v

# Existing regression
pytest tests/test_lms_rest_client.py tests/test_opp12_streaming.py -v

# Coverage >= 91%
pytest --cov=llm --cov=tools --cov=config --cov=utils --cov-report=term-missing \
       tests/ --ignore=tests/standalone -q

# Lint
ruff check llm/ utils/ tools/ config/ tests/test_opp*.py

# Version bump
# config/constants.py: VERSION = "4.0.0"
# pyproject.toml: version = "4.0.0"
# setup.py: version = "4.0.0"
# git tag v4.0.0
```

---

## Commit Plan (14 total)

| # | Message |
|---|---------|
| 0 | `chore: tag v3.5.0-round-d-pre safety checkpoint` |
| 1 | `test(OPP-22): RED — tests for single-model lookup and is_model_loaded refactoring` |
| 2 | `feat(OPP-22): GREEN — add LMSRestClient.get_model() and refactor is_model_loaded()` |
| 3 | `refactor(OPP-22): clean up get_model_info cache-first path` |
| 4 | `test(OPP-30): RED — tests for echo load config` |
| 5 | `feat(OPP-30): GREEN — add config echo to load_model via _fetch_model_config` |
| 6 | `refactor(OPP-30): return dict consistency across success/failure paths` |
| 7 | `test(OPP-23): RED — tests for streaming usage tracking` |
| 8 | `feat(OPP-23): GREEN — add StreamUsage dataclass and parse_sse_stream_with_usage` |
| 9 | `refactor(OPP-23): update __all__ exports` |
| 10 | `test(OPP-26): RED — tests for min_p and top_k sampling parameters` |
| 11 | `feat(OPP-26): GREEN — add min_p/top_k to all LLMClient methods and MCP tools` |
| 12 | `refactor(OPP-26): extract constants, update __all__ exports` |
| 13 | `chore: bump version to v4.0.0 for Round D` |

---

## Actual Outcomes (Post-Audit)

Round D implementation completed, then audited against PLANNING_GUIDELINES.md. 12 findings identified and fixed:

### Audit Findings Fixed

| Finding | Severity | Fix | Commit |
|---------|----------|-----|--------|
| F-5 | CRITICAL | 9 missing OPP-23/OPP-26 constants added to `__all__` in constants.py | `da8712e` |
| F-3 | HIGH | Python 3.9 compat: `StreamUsage \| None` → `Optional[StreamUsage]` in sse_parser.py | `84509a7` |
| F-8 | MEDIUM | Added min_p/top_k to `chat_completion_with_native_mcp()` (8th method missed) | `727c337` |
| F-6 | HIGH | Added min_p/top_k to all 3 MCP tool wrappers + CompletionTools class methods | `60d58ad` |
| F-7 | HIGH | Added 4 missing multi-method payload tests (stream_chat, create_response) | `fd78481` |
| F-9 | HIGH | Added 10 integration test stubs for all 4 OPPs | `5eb531f` |
| F-10 | MEDIUM | This section — plan updated with actual outcomes | — |

### Deviations from Plan

- **OPP-26 methods**: Plan said 7 methods. Actual: 8 (chat_completion_with_native_mcp added in F-8)
- **OPP-26 tests**: Plan said 14. Delivered: 21 (17 original + 4 F-7 additions)
- **OPP-23 REFACTOR**: Plan omitted Python 3.9 compat fix (F-3 added it)
- **MCP wrappers**: Plan listed OPP-26 tools/completions.py changes but missed MCP wrapper functions (F-6 fixed)
- **Integration stubs**: Not in original plan. Added as F-9 per PLANNING_GUIDELINES.md rule 5

### Final Test Counts

| Test File | Count |
|-----------|-------|
| test_opp22_single_model_lookup.py | 10 |
| test_opp23_streaming_usage.py | 9 |
| test_opp26_sampling_params.py | 21 |
| test_opp30_echo_load_config.py | 8 |
| test_f6_mcp_sampling_wrappers.py | 8 |
| test_round_d_integration_stubs.py | 10 (skipped) |
| **Total Round D** | **66** |
