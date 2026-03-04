# LM Studio Bridge Enhanced — OPP Roadmap

> Updated: 2026-03-02 | LM Studio target: 0.4.4+ | Baseline: ~1969 tests passing, 91% coverage | Log Analysis: 4 rounds

---

## Phase Completion Status

| Phase | OPPs | Status | PR/Version | Tests Added |
|-------|------|--------|------------|-------------|
| Phase 1 (Foundation) | OPP-01, 02, 03, 04 | **DONE** | PR #3 | 72 |
| Phase 1.5 (Code Quality) | OPP-05, 06, 07, 08, 09, 10 | **DONE** | PR #4 + #5 | 86 |
| Round A (Phases 2+3 parallel) | OPP-11, 16, 13, 05, 06, 07 | **DONE** | PR #6 + #7 | 107 |
| Round B (Phase 4) | OPP-12, 10, 08, 14, 18 | **DONE** | v3.4.0 | ~80 |
| Round C (Phase 5) | OPP-17, 09, 15 | **DONE** | v3.5.0 | ~30 |
| Error Audit | 10 bug fixes | **DONE** | v3.5.1-error-audit | ~50 |
| Code Quality Audit | 12 findings fixed | **DONE** | v4.0.0 | ~75 |
| Round D (Quick Wins) | OPP-22, 23, 26, 30 | **DONE** | v4.0.0 | ~90 |
| v5.0.0 Pre-flight | v4.1.0 bridge, CI enforcement | **DONE** | v4.1.0 | ~10 |
| v5.0.0 Phase A (Architecture) | ARCH-1..5 | **DONE** | v5.0.0 | ~30 |
| v5.0.0 Phase B (Features) | OPP-21, 24, 27, 28, 29, 31 | **DONE** | v5.0.0 | ~100 |
| v5.0.0 Phase C (Major) | OPP-19, 25 | **DONE** | v5.0.0 | ~60 |
| Log Analysis | 31 issues (4 rounds), 19 raw → 10 active OPPs | **ANALYSIS DONE** | — | — |
| Round G (Log Analysis OPPs) | 10 active + 1 experiment + 1 deferred | **PROPOSED** | v5.1.0 | ~TBD |

---

## 3 New LM Studio Features (discovered during validation, 2026-02-20)

### NEW-01: `/v1/responses` Endpoint (OpenAI Responses API)

**Since**: LM Studio 0.3.29
**Impact**: OPP-10 (Format Adapter) must route across **3** API surfaces, not 2.

Our `create_response()` already uses this endpoint. OPP-10's format adapter should be aware of it as a first-class routing target alongside `/v1/chat/completions` (OpenAI) and `/v1/messages` (Anthropic).

**Action**: Expand OPP-10 scope. No new OPP needed.

**Updated OPP-10 routing targets**:
1. `POST /v1/chat/completions` — OpenAI chat format (tool_calls in messages)
2. `POST /v1/messages` — Anthropic format (tool_use content blocks)
3. `POST /v1/responses` — OpenAI Responses format (function_call items, stateful)

### NEW-02: `llmster` Daemon (Headless Mode)

**Since**: LM Studio 0.4.x
**Impact**: Enables CI/CD and server deployments without LM Studio GUI.

The bridge already works with headless LM Studio (connects to `localhost:1234` regardless of GUI). However, documenting headless deployment and adding health checks against `llmster` would improve operational reliability.

**Action**: New OPP-18 — Headless Deployment Support.

| Field | Value |
|-------|-------|
| Name | Headless Deployment (`llmster`) |
| Reach | 4 |
| Impact | 5 |
| Confidence | 0.8 |
| Effort | 1 |
| RICE | 16 |
| Phase | Round B (Phase 4) |
| Depends on | OPP-04 (REST client) — **SATISFIED** |

**Scope**:
- Health check endpoint that detects `llmster` vs GUI LM Studio
- Deployment documentation for `llmster` daemon setup
- CI integration example (start `llmster`, run tests, stop)
- Graceful degradation when neither GUI nor daemon is running

### NEW-03: Parallel Inference with Continuous Batching

**Since**: LM Studio 0.4.x
**Impact**: Server natively handles concurrent requests without queueing.

This makes OPP-06 (Parallel Tool Execution) more valuable than originally scored. The server side is already optimized — OPP-06 only needs client-side `asyncio.gather` to exploit it.

**Action**: Bump OPP-06 confidence from 0.75 to 0.9. RICE increases from 36 to 43.2.

---

## Updated RICE Scoring Matrix

Changes from original:
- OPP-05 (Speculative Decoding): Confidence 1.0 → 0.7 (llama.cpp only, no MLX)
- OPP-06 (Parallel Tools): Confidence 0.75 → 0.9 (server continuous batching confirmed)
- OPP-10 (Format Adapter): Effort 2 → 2.5 (expanded to 3 API surfaces)
- OPP-14 (Extended Thinking): Confidence 0.8 → 0.7 (model-dependent)
- OPP-15 (Conversation Branching): Confidence 1.0 → 0.8 (native API only, not OpenAI-compat)
- OPP-18 (NEW): Headless Deployment

| Rank | OPP | Name | R | I | C | E | RICE | Round | Status |
|------|-----|------|---|---|---|---|------|-------|--------|
| — | OPP-01 | Capabilities API | 10 | 10 | 1.0 | 1 | 100 | — | DONE |
| — | OPP-02 | Self-Correcting Loops | 10 | 9 | 1.0 | 2 | 45 | — | DONE |
| — | OPP-03 | JIT Loading | 9 | 8 | 1.0 | 2 | 36 | — | DONE |
| — | OPP-04 | Model Lifecycle REST | 9 | 7 | 1.0 | 2 | 31.5 | — | DONE |
| — | OPP-11 | Anthropic Endpoint | 9 | 9 | 1.0 | 1 | 81 | A | DONE |
| — | OPP-16 | Native MCP via API | 7 | 10 | 0.91 | 1 | 63.8 | A | DONE |
| — | OPP-13 | Anthropic Tool Use | 9 | 8 | 1.0 | 1.33 | 54 | A | DONE |
| — | OPP-06 | Parallel Tool Execution | 6 | 8 | **0.9** | 1 | **43.2** | A | DONE |
| — | OPP-05 | Speculative Decoding | 10 | 8 | **0.7** | 1.33 | **42** | A | DONE |
| — | OPP-07 | Loop Observability | 8 | 8 | 0.8 | 2 | 25.6 | A | DONE |
| — | OPP-12 | Streaming | 5 | 8 | 0.8 | 1.5 | 21.3 | B | DONE |
| — | OPP-08 | Smart Model Selection | 6 | 6 | 1.0 | 2 | 18 | B | DONE |
| — | OPP-10 | Format Adapter (3-way) | 5 | 8 | 1.0 | **2.5** | **16** | B | DONE |
| — | OPP-18 | Headless Deployment | 4 | 5 | 0.8 | 1 | **16** | B | DONE |
| — | OPP-14 | Extended Thinking | 7 | 6 | **0.7** | 2 | **14.7** | B | DONE |
| — | OPP-17 | Dual-Format Autonomous | 7 | 6 | 1.0 | 3 | 14 | C | DONE |
| — | OPP-09 | Multi-Modal Loops | 6 | 6 | 1.0 | 3 | 12 | C | DONE |
| — | OPP-15 | Conversation Branching | 5 | 5 | **0.8** | 5 | **4** | C | DONE |
| — | OPP-19 | Native Chat API (`/api/v1/chat`) | 8 | 10 | 0.8 | 4 | **16** | v5-C | DONE |
| — | OPP-22 | Single-Model Lookup | 8 | 7 | 1.0 | 1 | **56** | D | DONE |
| — | OPP-23 | Streaming Usage Tracking | 7 | 7 | 0.9 | 1 | **44.1** | D | DONE |
| — | OPP-26 | Advanced Sampling (min_p, top_k) | 4 | 5 | 1.0 | 1 | **20** | D | DONE |
| — | OPP-30 | Echo Load Config | 4 | 5 | 0.9 | 1 | **18** | D | DONE |
| — | OPP-21 | Native Reasoning Parameter | 9 | 8 | 0.9 | 1 | **64.8** | v5-B | DONE |
| — | OPP-27 | Advanced Model Load Params | 5 | 6 | 0.9 | 1 | **27** | v5-B | DONE |
| — | OPP-29 | Log-Probabilities | 5 | 6 | 0.8 | 1 | **24** | v5-B | DONE |
| — | OPP-28 | API Authentication | 4 | 6 | 0.8 | 1 | **19.2** | v5-B | DONE |
| — | OPP-24 | Model Auto-Download (REST) | 6 | 7 | 0.8 | 2 | **16.8** | v5-B | DONE |
| — | OPP-25 | Ephemeral MCP Servers | 5 | 9 | 0.7 | 4 | **7.9** | v5-C | DONE |
| — | OPP-31 | Model Profiles | 9 | 9 | 0.9 | 3 | **24.3** | v5-B | DONE |

**Completed round totals**:
- Round A (Phases 2+3 parallel): **309.6** — 6 OPPs — **DONE**
- Round B (Phase 4): **85.9** — 5 OPPs — **DONE**
- Round C (Phase 5): **30** — 3 OPPs — **DONE**
- Round D (Quick Wins): **138.1** — 4 OPPs — **DONE**

**Proposed round totals**:
- Round D (v4.0.0 — Quick Wins): **138.1** — 4 OPPs — OPP-22, 23, 26, 30
- v5.0.0 Phase A (Architecture): 5 refactoring items (ARCH-1..5) — no RICE score
- v5.0.0 Phase B (Features): **176.1** — 6 OPPs — OPP-21, 24, 27, 28, 29, 31
- v5.0.0 Phase C (Major): **23.9** — 2 OPPs — OPP-19, 25

**Note**: ~~OPP-20~~ (Structured Output / JSON Schema) removed — already implemented in v3.2.0.

---

## Revised Parallelization Strategy

### Key Insight

Phase 3 (OPP-05, 06, 07) depends ONLY on Phase 1 — which is DONE. It does NOT depend on Phase 2. Therefore Phase 2 and Phase 3 execute **in parallel**, collapsing 4 sequential phases into 3 implementation rounds.

### Execution Diagram

```
                    ┌─ Track 1: OPP-11 (Anthropic endpoint) ← OPP-01 ✅
                    │    └─→ OPP-13 (Anthropic tool use) ← OPP-11 ✅
                    │
                    ├─ Track 2: OPP-16 (Native MCP) ← OPP-04 ✅
Phase 1 (DONE) ────┤
                    ├─ Track 3: OPP-05 (Speculative decoding) ← OPP-01 ✅
                    │
                    ├─ Track 4: OPP-06 (Parallel tools) ← OPP-02 ✅
                    │    └─→ OPP-07 (Observability) ← OPP-02 ✅, OPP-03 ✅
                    └─                      │
                         ┌──────────────────┘
                         ▼
               Round B — Phase 4 ✅
               ┌─ OPP-12 (Streaming) ← OPP-03 ✅
               ├─ OPP-10 (Format adapter 3-way) ← OPP-01 ✅, OPP-11 ✅
               ├─ OPP-08 (Smart selection) ← OPP-01 ✅, OPP-07 ✅
               ├─ OPP-14 (Extended thinking) ← OPP-02 ✅
               └─ OPP-18 (Headless deploy) ← OPP-04 ✅
                         │
                         ▼
               Round C — Phase 5 ✅
               ├─ OPP-17 (Dual-format) ← OPP-11 ✅, OPP-13 ✅
               ├─ OPP-09 (Multi-modal) ← OPP-10 ✅
               └─ OPP-15 (Branching) ← OPP-03 ✅, OPP-12 ✅
```

---

## Updated Dependency Matrix (ALL SATISFIED)

```
Phase 1 (Layer 0 - DONE):
  OPP-01 ✅ ──┐
  OPP-02 ✅ ──┤ (all complete)
  OPP-04 ✅ ──┤
  OPP-03 ✅ ──┘

Phase 1.5 (Code Quality - DONE):
  OPP-05 ✅ (loop dedup)
  OPP-06 ✅ (retry consolidation)
  OPP-07 ✅ (registry tests)
  OPP-08 ✅ (message manager tests + bug fix)
  OPP-09 ✅ (JIT guard dedup + stale export)
  OPP-10 ✅ (architecture guards)

Round A — Phases 2+3 (parallel) — DONE:
  Track 1: OPP-11 ✅ ← OPP-01 ✅
  Track 2: OPP-16 ✅ ← OPP-04 ✅
  Track 3: OPP-05 ✅ ← OPP-01 ✅
  Track 4: OPP-06 ✅ ← OPP-02 ✅
  Track 5: OPP-07 ✅ ← OPP-02 ✅, OPP-03 ✅
  Sequential: OPP-13 ✅ ← OPP-11 ✅

Round B — Phase 4 — DONE:
  OPP-12 ✅ ← OPP-03 ✅
  OPP-10 ✅ ← OPP-01 ✅, OPP-11 ✅
  OPP-08 ✅ ← OPP-01 ✅, OPP-07 ✅
  OPP-14 ✅ ← OPP-02 ✅
  OPP-18 ✅ ← OPP-04 ✅

Round C — Phase 5 — DONE:
  OPP-17 ✅ ← OPP-11 ✅, OPP-13 ✅
  OPP-09 ✅ ← OPP-10 ✅
  OPP-15 ✅ ← OPP-03 ✅, OPP-12 ✅
```

---

## Scope Adjustments Summary

| OPP | Change | Reason |
|-----|--------|--------|
| OPP-05 | Add MLX backend guard | Speculative decoding is llama.cpp only |
| OPP-06 | Bump confidence 0.75 → 0.9 | Server continuous batching confirmed |
| OPP-10 | Expand to 3-way routing | `/v1/responses` endpoint (since 0.3.29) |
| OPP-14 | Lower confidence 0.8 → 0.7 | Model-dependent (needs reasoning models) |
| OPP-15 | Lower confidence 1.0 → 0.8 | Native API only, not OpenAI-compat |
| OPP-18 | **NEW OPP** | `llmster` daemon headless deployment |

---

## OPP Type Classification (Round D/E/F)

| OPP | Name | Type | Evolves From | Backward Compat |
|-----|------|------|-------------|-----------------|
| OPP-19 | Native Chat API | EVOLUTION | OPP-12 + OPP-16 | No — replaces OpenAI-compat streaming |
| OPP-21 | Native Reasoning | EVOLUTION | OPP-14 | No — replaces `thinking_budget` |
| OPP-22 | Single-Model Lookup | EVOLUTION | OPP-04 | Yes — additive endpoint |
| OPP-23 | Streaming Usage | EVOLUTION | OPP-12 | Yes — additive parameter |
| OPP-24 | Model Auto-Download | EVOLUTION | OPP-04 | Yes — REST replaces CLI |
| OPP-25 | Ephemeral MCP | EVOLUTION | OPP-16 | No — restructures MCP config |
| OPP-26 | Advanced Sampling | NEW | None | Yes — new parameters |
| OPP-27 | Advanced Load Params | EVOLUTION | OPP-04 | Yes — additive parameters |
| OPP-28 | API Authentication | NEW | None | Yes — additive header |
| OPP-29 | Log-Probabilities | NEW | None | Yes — additive parameter |
| OPP-30 | Echo Load Config | EVOLUTION | OPP-04 | Yes — additive response field |
| OPP-31 | Model Profiles | NEW | None | Yes — additive module + MCP tools |

**Summary**: 8 evolutions, 4 new features, 1 removed (OPP-20 already exists). 9 backward compatible, 3 breaking.

---

## Proposed Execution Diagram (Round D/E/F)

```
                    ┌─ OPP-22 (single lookup) ← OPP-04 ✅
Round D (v4.0.0) ──┤  OPP-23 (streaming usage) ← OPP-12 ✅     ALL PARALLEL
                    ├─ OPP-26 (sampling params) ← none
                    └─ OPP-30 (echo config) ← OPP-04 ✅
                         │
                         ▼
v5.0.0 Phase A ────┐
  (Architecture)    ├─ ARCH-2 (break constants) ═══╗
                    ├─ ARCH-3 (extract metrics) ═══╣ PARALLEL
                    ├─ ARCH-4 (fix utils→llm)  ═══╣
                    ├─ ARCH-5 (platform MCP)   ═══╝
                    └─ ARCH-1 (split LLMClient) ────→ (after ARCH-2..5)
                         │
                         ▼
v5.0.0 Phase B ────┐
  (Features)        ├─ OPP-21 (reasoning) ═══╗
                    ├─ OPP-28 (auth)      ═══╣ PARALLEL
                    ├─ OPP-29 (logprobs)  ═══╝
                    └─ OPP-27 (adv load) → OPP-24 (auto-download)  SEQUENTIAL
                         │
                         ▼
v5.0.0 Phase C ────┐
  (Major)           ├─ OPP-19 (native chat) ← OPP-12 ✅, OPP-16 ✅
                    └─ OPP-25 (ephemeral MCP) ← OPP-19
```

---

## API Combination Opportunities

| Combo | Name | APIs Combined | Impact | Evolves |
|-------|------|--------------|--------|---------|
| COMBO-A | Intelligent Streaming | OPP-19 + 23 + 21 | TRANSFORMATIVE | OPP-12 → rich event stream |
| COMBO-B | Self-Provisioning Bridge | OPP-24 + 27 + 22 + 08 | GAME-CHANGER | OPP-04+08 → zero manual model mgmt |
| COMBO-C | Secure Multi-Tenant | OPP-28 + 25 + 19 | NEW MARKET | None → team/shared deployments |
| COMBO-D | Confidence-Scored Output | OPP-29 + structured output + 21 | HIGH VALUE | OPP-02 → confidence-gated loops |
| COMBO-E | Observable Autonomous Loop | OPP-19 + 07 + 23 + 21 | HIGH VALUE | OPP-07 → real-time observability |
| COMBO-F | Zero-Config Model Router | OPP-22 + 30 + 08 + 27 | MEDIUM | OPP-08 → self-tuning selection |

---

## Completed Work Summary

| Round | OPPs | RICE Total | Tests Added |
|-------|------|-----------|-------------|
| Phase 1 (Foundation) | OPP-01, 02, 03, 04 | 212.5 | 72 |
| Phase 1.5 (Code Quality) | 6 items | — | 86 |
| Round A (Phase 2+3) | OPP-11, 16, 13, 05, 06, 07 | 309.6 | ~107 |
| Round B (Phase 4) | OPP-12, 10, 08, 14, 18 | 85.9 | ~80 |
| Round C (Phase 5) | OPP-17, 09, 15 | 30 | ~30 |
| Error Audit | 10 bug fixes | — | ~50 |
| Code Quality Audit | 12 findings fixed | — | ~75 |
| Round D (Quick Wins) | OPP-22, 23, 26, 30 | 138.1 | ~90 |
| Round D (Quick Wins) through v4.0.0 subtotal | **22 OPPs + 22 fixes** | **776.1** | **~590** |
| v5.0.0 Phase A (Architecture) | ARCH-1..5 | — | ~30 |
| v5.0.0 Phase B (Features) | OPP-21, 24, 27, 28, 29, 31 | 176.1 | ~100 |
| v5.0.0 Phase C (Major) | OPP-19, 25 | 23.9 | ~60 |
| **GRAND TOTAL** | **30 OPPs + 5 ARCH + 22 fixes** | **976.1** | **~780** |

Final completed state: ~1969 tests, 91% coverage, VERSION 5.0.0.

---

## Round G — Log Analysis OPPs (PROPOSED)

> Source: 4-round deep analysis of 188K-line LM Studio server log (`docs/LOG_ANALYSIS_2026-03-02.md`)
> 31 issues found → 19 raw OPPs → **10 active** after root cause analysis (4 merged, 3 removed, 1 deferred, 1 experiment)
>
> **Root causes**: (1) Missing model lifecycle state machine — `"default"` sentinel escapes config→API boundary.
> (2) `dynamic_autonomous.py` god module (1,168 lines, 16 methods, 8+ responsibilities) — missing `ToolCallContext` pattern.

| Rank | OPP | Name | R | I | C | E | RICE | Priority | Status |
|------|-----|------|---|---|---|---|------|----------|--------|
| 1 | OPP-38 | Fix "model: default" Fallback | 10 | 10 | 1.0 | 0.5 | **200** | P0 | **DONE** |
| 2 | OPP-32 | Schema-Aware Type Coercion | 8 | 9 | 0.9 | 2 | **32.4** | P0 | **DONE** |
| 3 | OPP-39 | Context Window Guard | 7 | 9 | 0.8 | 2 | **25.2** | P0 | PROPOSED |
| 4 | OPP-40 | Tool Result Caching (+OPP-47) | 7 | 8 | 0.9 | 2 | **25.2** | P1 | **DONE** |
| 5 | OPP-37 | Orphan Detection with Fast-Fail | 6 | 8 | 0.8 | 2 | **19.2** | P1 | **DONE** |
| 6 | OPP-33 | Pre-Dispatch Tool Argument Validation | 6 | 7 | 0.9 | 1 | **37.8** | P1 | **DONE** |
| ~~7~~ | ~~OPP-34~~ | ~~Model Tool-Calling Error Budget~~ | — | — | — | — | — | — | **MERGED → OPP-45** |
| ~~8~~ | ~~OPP-35~~ | ~~LMSAuthenticator getModelInfo Caching~~ | — | — | — | — | — | — | **REMOVED** (LM Studio internal, our cache already works) |
| ~~9~~ | ~~OPP-36~~ | ~~Logprobs Response Bloat Suppression~~ | — | — | — | — | — | — | **REMOVED** (server-side issue, bridge never requests logprobs) |
| ~~10~~ | ~~OPP-41~~ | ~~Conversation Chain Health Monitoring~~ | — | — | — | — | — | — | **REMOVED** (short chains = efficient, not a bug) |
| 11 | OPP-42 | Token Budget Monitoring & Alerting | 4 | 5 | 0.8 | 1 | **16** | P2 | **DEFERRED** (re-measure after OPP-39) |
| 12 | OPP-43 | Poll Rate Limiter (JIT memoization) | 9 | 9 | 0.9 | 2 | **36.5** | P0 | **DONE** |
| 13 | OPP-44 | Tool Call Circuit Breaker (+OPP-48) | 7 | 8 | 0.8 | 2 | **22.4** | P1 | **DONE** |
| 14 | OPP-45 | Per-Model Error Budget + Auto-Demotion (+OPP-34) | 7 | 8 | 0.8 | 2 | **22.4** | P1 | **DONE** |
| 15 | OPP-46 | Adaptive Timeout — Both Phases (+OPP-49) | 6 | 7 | 0.8 | 2 | **16.8** | P1 | **DONE** |
| ~~16~~ | ~~OPP-47~~ | ~~Tool Name Normalization Layer~~ | — | — | — | — | — | — | **MERGED → OPP-40** |
| ~~17~~ | ~~OPP-48~~ | ~~Truncated Tool Call Recovery~~ | — | — | — | — | — | — | **MERGED → OPP-44** |
| ~~18~~ | ~~OPP-49~~ | ~~Generation-Aware Timeout~~ | — | — | — | — | — | — | **MERGED → OPP-46** |
| 19 | OPP-50 | Tool Schema Dedup Experiment | 8 | 5 | 0.9 | 2 | **18** | P1 | EXPERIMENT |

### Key Findings Driving These OPPs

| Finding | Severity | Evidence | OPP |
|---------|----------|----------|-----|
| "model: default" sent to LM Studio | CRITICAL | 167 ERRORs, 135 rejected | OPP-38 ✅ |
| Array type coercion gap | CRITICAL | 11/13 WARNs | OPP-32 |
| 94K token context overflow | CRITICAL | 3 × 94K input → 0 output | OPP-39 |
| 24% orphaned tool calls | CRITICAL | 23/95 started never finished | OPP-37 |
| 89% prompt cache miss | HIGH | 113/127 cached_tokens=0 | OPP-40 |
| 42% duplicate tool calls | HIGH | list_directory llm/ ×15 | OPP-40 |
| ~~Conversation fragmentation~~ | ~~HIGH~~ | ~~2.4 avg chain length~~ | ~~OPP-41~~ **REMOVED** (efficient, not a bug) |
| ~~6,273 uncached getModelInfo~~ | ~~HIGH~~ | ~~789 calls/min peak~~ | ~~OPP-35~~ **REMOVED** (LM Studio internal) |
| ~~18,211 logprobs lines~~ | ~~HIGH~~ | ~~9.7% log bloat~~ | ~~OPP-36~~ **REMOVED** (server-side) |
| 27:1 input/output ratio | MEDIUM | 96.5% tokens are overhead | OPP-42 |
| 11,613 lms-cli polls (85% of events) | CRITICAL | 789/min peak, getModelInfo uncached | OPP-43 |
| 10 silently dropped tool calls | CRITICAL | Truncated JSON generation, no circuit breaker | OPP-44 |
| glm 80% events + 100% errors | HIGH | Error density accelerates 1.75→5.33/min | OPP-45 |
| 3× wasted prompt processing | HIGH | 94K tokens processed then 0 output | OPP-46 |
| ~~Tool name inconsistency across models~~ | ~~MEDIUM~~ | ~~qwen: `list_directory`, glm: `filesystem__list_directory`~~ | ~~OPP-47~~ **MERGED → OPP-40** |
| 10 truncated tool call parse failures | HIGH | ALL `read_text_file`, ALL glm-4.6v-flash | OPP-44 (absorbed OPP-48) |
| 9 client disconnects post-100% prompt | HIGH | 37s gap between prompt processing complete and timeout | OPP-46 (absorbed OPP-49) |
| 3,909 repeated tool schema definitions | HIGH | 127 tool arrays × ~30 tools/array, ~50% of log volume | OPP-50 (EXPERIMENT) |
| getModelInfo is 54% of internal calls | CRITICAL (R4 update) | LMSAuthenticator: 6,273 getModelInfo, cache strategy per endpoint | OPP-43 |
| glm 31.1% tool call failure rate | HIGH (R4 update) | 23/74 orphaned vs 0% for qwen/magistral | OPP-45 |
| 126 prompt re-starts (91% re-processing) | HIGH (R4 update) | 9 disconnects during generation phase | OPP-46 |

### Execution Order (Root Cause Driven)

```
Phase 1: Kill the Cascade ✅ DONE
  OPP-38 ✅ ──→ fix "default" sentinel escape (6 commits, 22 tests)

Phase 2: Foundations (parallel)
  OPP-39 ═══╗ context window guard
  OPP-32 ═══╣ schema-aware type coercion
  OPP-43 ═══╝ poll rate limiter (after OPP-38 removes error amplification)

Phase 3: Build ToolCallContext (sequential pair, then parallel)
  OPP-33 + OPP-44 ═══╗ pre-dispatch validation + circuit breaker
  OPP-37 + OPP-40   ═╝ orphan detection + result cache

Phase 4: Model Intelligence
  OPP-45 ────→ per-model error budget + auto-demotion

Phase 5: Streaming Refactor (most invasive, do last)
  OPP-46 ────→ adaptive timeout for both inference phases

Phase 6: Quick Experiment
  OPP-50 ────→ test omitting tools after round 0 with previous_response_id
```

### Consolidated Summary

| Status | Count | OPPs |
|--------|-------|------|
| **Active** | 9 | OPP-32, 33, 37, 39, 40, 43, 44, 45, 46 |
| **Done (Round G)** | 1 | OPP-38 |
| **Experiment** | 1 | OPP-50 |
| **Deferred** | 1 | OPP-42 (re-measure after OPP-39) |
| **Merged** | 4 | OPP-34→45, OPP-47→40, OPP-48→44, OPP-49→46 |
| **Removed** | 3 | OPP-35, 36, 41 |

Target version: **v5.1.0** (all backward compatible, no breaking changes)
