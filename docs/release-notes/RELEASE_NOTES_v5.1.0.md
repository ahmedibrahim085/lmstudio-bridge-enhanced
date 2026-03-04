# Release Notes — v5.1.0

**Release Date**: 2026-03-04
**Branch**: `feat/v5.1.0-round-g-complete` → merged to `main`
**Tag**: `v5.1.0`
**PR**: #12

---

## Summary

Round G delivers 11 OPPs focused on **reliability and efficiency**, all derived from a 3-round analysis of 188K-line LM Studio server logs. The release adds 5 new modules to the autonomous agent loop, implements a 6-round code review process, and fixes all CRITICAL and HIGH findings.

**Stats**: 2167 tests, 81% coverage (CI), +5,476/-131 lines, 38 files changed, 18 new files

---

## New Features

### Tool Execution Pipeline

| OPP | Feature | Problem Solved |
|-----|---------|---------------|
| OPP-33 | Pre-dispatch validation | 2 WARNs from missing required params |
| OPP-44 | Per-tool circuit breaker | 7 consecutive failures with no limit |
| OPP-37 | Orphan detection | 24% of tool calls started but never finished |
| OPP-40 | Tool result caching | 42% duplicate tool calls (list_directory x15) |
| OPP-45 | Per-model error budget | glm-4.6v-flash: 80% resources, 100% errors |
| OPP-46 | Adaptive timeout | 58s hardcoded timeout, 9 client disconnects |
| OPP-50 | Schema dedup experiment | 3,810 repeated tool definitions per session |

### Bug Fixes

| OPP | Fix | Impact |
|-----|-----|--------|
| OPP-38 | Fix "model: default" sentinel escape | Eliminated 167 ERRORs/session |
| OPP-39 | Context window guard (cumulative tracking) | Prevented 282K wasted tokens |
| OPP-43 | JIT poll rate limiter (60s memoization) | Eliminated 11,613 redundant polls |
| OPP-32 | Schema-aware type coercion | Fixed string→array/object for LM Studio |

---

## New Modules

| Module | Purpose | Lines |
|--------|---------|-------|
| `tools/tool_call_guard.py` | Pre-dispatch validation + circuit breaker | 137 |
| `tools/tool_call_tracker.py` | Orphan detection with timeout tracking | 110 |
| `tools/tool_result_cache.py` | Allowlist-based caching with TTL + LRU | 178 |
| `tools/model_health.py` | Per-model error budget + health states | 236 |
| `tools/adaptive_timeout.py` | Response-time observation + p95 adaptation | 76 |
| `config/constants/tool_config.py` | 15 new constants (thresholds, TTLs, flags) | 57 |

---

## Review Process

6-round review with specialized agents:

| Round | Focus | Result |
|-------|-------|--------|
| R1 | 6-agent parallel review (code, race, TDD, arch, security, semantic) | 5C + 6H + 4M found |
| R2 | Fix implementation | All 11 C+H fixed (7 commits) |
| R3 | Post-fix verification (3 agents) | All 11 VERIFIED |
| R4 | Gap analysis + synthesis | 5 additional findings (G-1 to G-4) |
| R5 | Regression + coverage | 2167 pass, 0 fail |
| R6 | Final report | READY TO MERGE |

---

## Breaking Changes

None. All changes are backward compatible.

---

## Migration

No migration required. Upgrade from v5.0.0 by pulling latest main.

New features are enabled by default with conservative thresholds:
- Circuit breaker: 5 failures, 60s reset
- Result cache: allowlist-only, 120s TTL
- Health tracker: 300s window, 30% error threshold
- Adaptive timeout: 10 min observations, 1.5x p95 multiplier

All features can be disabled via constants in `config/constants/tool_config.py`.

---

## Known Issues

- OPP-42 (Token Budget Monitoring) deferred — re-measure after OPP-39
- `_MAX_OBSERVATIONS` in adaptive_timeout.py hardcoded (move to tool_config.py later)

---

## Dependency on Previous Releases

Requires v5.0.0 architecture (LLMClient facade, constants package, exception hierarchy).
