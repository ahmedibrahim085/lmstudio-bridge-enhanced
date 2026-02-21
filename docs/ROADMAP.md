# LM Studio Bridge Enhanced — OPP Roadmap

> Updated: 2026-02-20 | LM Studio target: 0.4.3+ | Baseline: 561 tests passing

---

## Phase Completion Status

| Phase | OPPs | Status | PR | Tests Added |
|-------|------|--------|-----|-------------|
| Phase 1 (Foundation) | OPP-01, 02, 03, 04 | **DONE** | PR #3 | 72 |
| Phase 1.5 (Code Quality) | OPP-05, 06, 07, 08, 09, 10 | **DONE** | PR #4 + #5 | 86 |
| Round A (Phases 2+3 parallel) | OPP-11, 16, 13, 05, 06, 07 | Not started | — | — |
| Round B (Phase 4) | OPP-12, 10, 08, 14, 18 | Not started | — | — |
| Round C (Phase 5) | OPP-17, 09, 15 | Not started | — | — |

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
| 1 | OPP-11 | Anthropic Endpoint | 9 | 9 | 1.0 | 1 | 81 | A | Ready |
| 2 | OPP-16 | Native MCP via API | 7 | 10 | 0.91 | 1 | 63.8 | A | Ready |
| 3 | OPP-13 | Anthropic Tool Use | 9 | 8 | 1.0 | 1.33 | 54 | A | Ready (after OPP-11) |
| 4 | OPP-06 | Parallel Tool Execution | 6 | 8 | **0.9** | 1 | **43.2** | A | Ready |
| 5 | OPP-05 | Speculative Decoding | 10 | 8 | **0.7** | 1.33 | **42** | A | Ready (llama.cpp only) |
| 6 | OPP-07 | Loop Observability | 8 | 8 | 0.8 | 2 | 25.6 | A | Ready |
| 7 | OPP-12 | Streaming | 5 | 8 | 0.8 | 1.5 | 21.3 | B | Ready |
| 8 | OPP-08 | Smart Model Selection | 6 | 6 | 1.0 | 2 | 18 | B | Ready (after OPP-07) |
| 9 | OPP-10 | Format Adapter (3-way) | 5 | 8 | 1.0 | **2.5** | **16** | B | Ready (after OPP-11) |
| 10 | OPP-18 | Headless Deployment | 4 | 5 | 0.8 | 1 | **16** | B | **NEW** |
| 11 | OPP-14 | Extended Thinking | 7 | 6 | **0.7** | 2 | **14.7** | B | Ready (model-dependent) |
| 12 | OPP-17 | Dual-Format Autonomous | 7 | 6 | 1.0 | 3 | 14 | C | Ready (after OPP-11+13) |
| 13 | OPP-09 | Multi-Modal Loops | 6 | 6 | 1.0 | 3 | 12 | C | Ready (MLX vision pending) |
| 14 | OPP-15 | Conversation Branching | 5 | 5 | **0.8** | 5 | **4** | C | Ready (native API only) |

**Round totals**:
- Round A (Phases 2+3 parallel): **309.6** — 6 OPPs
- Round B (Phase 4): **85.9** — 5 OPPs
- Round C (Phase 5): **30** — 3 OPPs

---

## Revised Parallelization Strategy

### Key Insight

Phase 3 (OPP-05, 06, 07) depends ONLY on Phase 1 — which is DONE. It does NOT depend on Phase 2. Therefore Phase 2 and Phase 3 execute **in parallel**, collapsing 4 sequential phases into 3 implementation rounds.

### Execution Diagram

```
                    ┌─ Track 1: OPP-11 (Anthropic endpoint) ← OPP-01 ✅
                    │    └─→ OPP-13 (Anthropic tool use) ← OPP-11
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
               Round B — Phase 4
               ┌─ OPP-12 (Streaming) ← OPP-03 ✅
               ├─ OPP-10 (Format adapter 3-way) ← OPP-01 ✅, OPP-11
               ├─ OPP-08 (Smart selection) ← OPP-01 ✅, OPP-07
               ├─ OPP-14 (Extended thinking) ← OPP-02 ✅
               └─ OPP-18 (Headless deploy) ← OPP-04 ✅
                         │
                         ▼
               Round C — Phase 5
               ├─ OPP-17 (Dual-format) ← OPP-11, OPP-13
               ├─ OPP-09 (Multi-modal) ← OPP-10
               └─ OPP-15 (Branching) ← OPP-03 ✅, OPP-12
```

### Round A — Detailed Execution Order

Within Round A, file overlap analysis determines serialization constraints:

| Step | OPP | Files Modified | Parallel With |
|------|-----|---------------|---------------|
| A1 | OPP-11 + OPP-16 + OPP-05 | llm_client.py (non-overlapping sections), lms_helper.py, config/constants.py | All 3 parallel |
| A2 | OPP-06 | tools/dynamic_autonomous.py (tool execution) | After A1 |
| A3 | OPP-07 | tools/dynamic_autonomous.py (logging/metrics) | After A2 |
| A4 | OPP-13 | llm/anthropic_adapter.py (new) | After OPP-11 (A1) |

**Rationale**: OPP-06 and OPP-07 both modify `tools/dynamic_autonomous.py`, so they serialize. OPP-13 depends on OPP-11's Anthropic endpoint.

### Round B — All 5 OPPs Parallel

All Round B OPPs have satisfied dependencies after Round A. Minimal file overlap expected (each touches different modules).

### Round C — All 3 OPPs Parallel

All Round C OPPs have satisfied dependencies after Round B.

---

## Updated Dependency Matrix

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

Round A — Phases 2+3 (parallel):
  Track 1: OPP-11 ← OPP-01 ✅
  Track 2: OPP-16 ← OPP-04 ✅
  Track 3: OPP-05* ← OPP-01 ✅  [*Speculative Decoding — llama.cpp only, add MLX guard]
  Track 4: OPP-06* ← OPP-02 ✅  [*Parallel Tools — boosted by continuous batching]
  Track 5: OPP-07* ← OPP-02 ✅, OPP-03 ✅  [*Loop Observability + /v1/models/{id}/stats]
  Sequential: OPP-13 ← OPP-11 (waits for Track 1)

Round B — Phase 4:
  OPP-12 ← OPP-03 ✅
  OPP-10* ← OPP-01 ✅, OPP-11  [*Expanded: 3-way format routing incl /v1/responses]
  OPP-08* ← OPP-01 ✅, OPP-07*
  OPP-14 ← OPP-02 ✅  [*Model-dependent: needs reasoning-capable models]
  OPP-18 ← OPP-04 ✅  [*NEW: llmster daemon headless deployment]

Round C — Phase 5:
  OPP-17 ← OPP-11, OPP-13
  OPP-09 ← OPP-10*  [*MLX parallel vision pending]
  OPP-15 ← OPP-03 ✅, OPP-12  [*Native API only, not OpenAI-compat]
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

## Remaining Work Summary

| Round | OPPs | RICE Total | Estimated Tests |
|-------|------|-----------|-----------------|
| Round A (Phase 2+3) | OPP-11, 16, 13, 05, 06, 07 | 309.6 | ~80 |
| Round B (Phase 4) | OPP-12, 10, 08, 14, 18 | 85.9 | ~50 |
| Round C (Phase 5) | OPP-17, 09, 15 | 30 | ~30 |
| **TOTAL** | **14 OPPs** | **425.5** | **~160** |

Target: 561 (current) + ~160 = **~720 tests** at project completion.
