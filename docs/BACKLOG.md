# LM Studio Bridge Enhanced — Execution Backlog

> Updated: 2026-03-02 | Post-v5.0.0 + Log Analysis (4 rounds) | Baseline: ~1969 tests passing, 91% coverage

---

## Current State (Verified 2026-03-02)

| Metric | Value |
|--------|-------|
| Branch | `feat/arch-2-constants-split` |
| Tests | ~1969 passed, 0 failures |
| Coverage | **91%+** |
| Coverage target | **80% minimum / 89% goal (exceeded)** |
| VERSION | 5.0.0 (in config/constants/version.py) |
| Completed rounds | Phase 1, 1.5, Round A-D, Error Audit, Code Quality, v5.0.0 (Pre-flight + Phase A + Phase B + Phase C), Log Analysis (4 rounds) |
| Next | Round G Phase 3a: OPP-33+44 (pre-dispatch + circuit breaker) |

---

## Phase 0 — Housekeeping (DONE)

| # | Item | Status | Notes |
|---|------|--------|-------|
| H-01 | Git pull origin main | DONE | Fast-forwarded 22 commits |
| H-02 | Verify Round A tests | DONE | 709 passed, 2 infra failures (expected) |
| H-03 | Commit PLANNING_GUIDELINES.md | DONE | Committed to main |
| H-04 | Update ROADMAP.md Round A status | DONE | Updated |
| H-05 | Fix DEFAULT_MAX_RETRIES 3-way collision | DONE | Single source in constants.py |
| H-06 | Clean stale worktrees | DONE | Removed `suva-wt-opp05` and `suva-wt-opp11` |
| H-07 | Create safety tag | DONE | `v3.3.0-pre-round-b` |
| H-08 | Record coverage baseline | DONE | 69% overall |

---

## Dependency Chains (ALL SATISFIED)

### Chain A: Anthropic Stack
```
OPP-01 DONE → OPP-11 DONE → OPP-13 DONE → OPP-17 DONE
                         ↘
                          OPP-10 DONE
```

### Chain B: Autonomous Loop Stack
```
OPP-02 DONE → OPP-06 DONE → OPP-07 DONE → OPP-08 DONE
OPP-02 DONE → OPP-14 DONE
```

### Chain C: Streaming & Branching
```
OPP-03 DONE → OPP-12 DONE → OPP-15 DONE
```

### Chain D: Multi-Modal
```
OPP-10 DONE → OPP-09 DONE
```

### Independent
```
OPP-04 DONE → OPP-18 DONE
```

---

## Completed OPPs (All 18)

| OPP | Name | Round | RICE | PR |
|-----|------|-------|------|----|
| OPP-01 | Capabilities API | Phase 1 | 100 | PR #3 |
| OPP-02 | Self-Correcting Loops | Phase 1 | 45 | PR #3 |
| OPP-03 | JIT Loading | Phase 1 | 36 | PR #3 |
| OPP-04 | Model Lifecycle REST | Phase 1 | 31.5 | PR #3 |
| OPP-05 | Speculative Decoding | Round A | 42 | PR #7 |
| OPP-06 | Parallel Tool Execution | Round A | 43.2 | PR #7 |
| OPP-07 | Loop Observability | Round A | 25.6 | PR #7 |
| OPP-11 | Anthropic Endpoint | Round A | 81 | PR #7 |
| OPP-13 | Anthropic Tool Use | Round A | 54 | PR #7 |
| OPP-16 | Native MCP via API | Round A | 63.8 | PR #7 |
| OPP-08 | Smart Model Selection | Round B | 18 | v3.4.0 |
| OPP-18 | Headless Deployment | Round B | 16 | v3.4.0 |
| OPP-12 | Streaming | Round B | 21.3 | v3.4.0 |
| OPP-14 | Extended Thinking | Round B | 14.7 | v3.4.0 |
| OPP-10 | Format Adapter (3-way) | Round B | 16 | v3.4.0 |
| OPP-17 | Dual-Format Autonomous | Round C | 14 | v3.5.0 |
| OPP-09 | Multi-Modal Loops | Round C | 12 | v3.5.0 |
| OPP-15 | Conversation Branching | Round C | 4 | v3.5.0 |

Phase 1.5 code quality (OPP-05-10 code quality items): PR #4 + PR #5

---

## Round B — Phase 4 (DONE — v3.4.0)

All 5 OPPs implemented, tested, and merged. Coverage reached ~80%.

---

## Round C — Phase 5 (DONE — v3.5.0)

All 3 OPPs implemented, tested, and merged. Coverage reached ~90%.

---

## Quality Gates (ALL PASSED)

### Round B Gate ✅
- [x] All 5 Round B OPPs implemented and tested
- [x] Coverage >= **75%** (achieved ~80%)
- [x] All existing tests still pass
- [x] Integration tests pass for OPP-12 (streaming) and OPP-10 (format adapter)
- [x] Architecture guard tests pass
- [x] VERSION bumped to **v3.4.0**
- [x] Safety tag created

### Round C Gate ✅
- [x] All 3 Round C OPPs implemented and tested
- [x] Coverage >= **80%** (achieved ~90%)
- [x] All tests pass (~1405 total)
- [x] Full integration test suite passes
- [x] Architecture guard tests pass
- [x] VERSION bumped to **v3.5.0**
- [x] README updated with final feature list

### Polish Gate ✅
- [x] Coverage push toward **89%** goal (achieved 89%)
- [x] Test infrastructure overhaul complete (12 commits)
- [x] Comprehensive OPP review complete (12 fix commits)
- [x] All documentation current (v4.0.0)
- [x] Release tag created (v4.0.0)
- [ ] CI/CD pipeline green

---

## Timeline View

```
Phase 0 (Housekeeping) ──── DONE
  H-03 → H-04 → H-05 → H-07
                              │
Round B ──────────────────────┘ DONE (v3.4.0)
  B-Step 1: OPP-08 ═══╗ parallel
            OPP-18 ═══╝
  B-Step 2: OPP-12 ────→
  B-Step 3: OPP-14 ────→
  B-Step 4: OPP-10 ────→
  [Gate: coverage ≥ 75% ✅, VERSION → v3.4.0 ✅]
                        │
Round C ────────────────┘ DONE (v3.5.0)
  C-Step 1: OPP-17 ═══╗ parallel
            OPP-15 ═══╝
  C-Step 2: OPP-09 ────→
  [Gate: coverage ≥ 80% ✅, VERSION → v3.5.0 ✅]
                        │
Polish ─────────────────┘ DONE
  - Coverage push → 89% ✅
  - Test infra overhaul ✅ (12 commits)
  - OPP review ✅ (12 fix commits)
  - Docs update ✅
  - Release tag ✅ (v4.0.0)
                        │
Round D ────────────────┘ DONE (v4.0.0)
  D-Step 1: OPP-22 ═══╗ parallel
            OPP-23 ═══╣
            OPP-26 ═══╣
            OPP-30 ═══╝
  [Gate: coverage ≥ 91% ✅, VERSION → v4.0.0 ✅]
                        │
v5.0.0 Phase A ────────┘ DONE (Architecture)
  ARCH-2 ═══╗
  ARCH-3 ═══╣ parallel (independent)
  ARCH-4 ═══╣
  ARCH-5 ═══╝
  ARCH-1 ────→ (after ARCH-2..5)
                        │
v5.0.0 Phase B ────────┘ DONE (Features)
  OPP-21 ═══╗
  OPP-28 ═══╣ parallel (independent)
  OPP-29 ═══╣
  OPP-31 ═══╝
  OPP-27 → OPP-24 (sequential)
                        │
v5.0.0 Phase C ────────┘ DONE (Major)
  OPP-19 → OPP-25 (sequential)
  [Gate: coverage ≥ 91% ✅, VERSION → v5.0.0 ✅]
                        │
Log Analysis ──────────┘ DONE (4-round deep analysis)
  Source: 188K-line LM Studio server log
  31 issues → 19 OPPs proposed (OPP-32 to OPP-50)
                        │
Round G ───────────────┘ PROPOSED (10 active OPPs after root cause analysis)
  Phase 1: OPP-38 ────→ kill "default" cascade (highest ROI)
  Phase 2: OPP-39 ═══╗ foundations (parallel)
           OPP-32 ═══╣
           OPP-43 ═══╝
  Phase 3: OPP-33+44 ═╗ build ToolCallContext
           OPP-37+40 ═╝
  Phase 4: OPP-45 ────→ model intelligence
  Phase 5: OPP-46 ────→ adaptive timeout (streaming refactor)
  Phase 6: OPP-50 ────→ schema dedup experiment
  [Gate: coverage ≥ 91%, VERSION → v5.1.0]
```

---

## Round D — Quick Wins (DONE — v4.0.0)

Low-effort, high-value additive improvements. All backward compatible.

| Step | OPP | Name | Type | Evolves | Backward Compat | Effort | Depends On |
|------|-----|------|------|---------|-----------------|--------|------------|
| D-1 | OPP-22 | Single-Model Lookup | EVOLUTION | OPP-04 (Model Lifecycle) | Yes — additive | LOW | OPP-04 ✅ |
| D-2 | OPP-23 | Streaming Usage Tracking | EVOLUTION | OPP-12 (Streaming) | Yes — additive | LOW | OPP-12 ✅ |
| D-3 | OPP-26 | Advanced Sampling (min_p, top_k) | NEW | None | Yes — additive | LOW | None |
| D-4 | OPP-30 | Echo Load Config | EVOLUTION | OPP-04 (Model Lifecycle) | Yes — additive | LOW | OPP-04 ✅ |

**Parallelization**: All 4 OPPs are independent — execute ALL in parallel.

**Gate**: Coverage >= 91%, all tests pass, VERSION → v4.0.0

---

## v5.0.0 — Architecture + Features (DONE)

Major version combining architecture refactoring, medium-lift features, and breaking changes.
All breaking changes bundled into one upgrade — v4.x stays a "safe upgrade" guarantee.

### Phase A: Architecture Refactoring

Addresses top findings from `docs/ARCHITECTURE_REVIEW.md` (score: 62/100).

| Step | Item | Name | Effort | Impact | Source |
|------|------|------|--------|--------|--------|
| A-1 | ARCH-1 | Split `LLMClient` into Facade + Protocol | HIGH | HIGH | God class: 1503 lines, 30 methods, 5+ responsibilities |
| A-2 | ARCH-2 | Break `config/constants.py` into domain packages | LOW | MEDIUM | 172 constants in one flat 762-line file |
| A-3 | ARCH-3 | Extract metrics helper from `_autonomous_loop` | LOW | MEDIUM | Same 15-line block copy-pasted 4 times |
| A-4 | ARCH-4 | Fix upward dependency: utils → llm | LOW | MEDIUM | Utils should be leaf-level, imports from llm.exceptions |
| A-5 | ARCH-5 | Platform-abstract MCP process spawning | LOW | MEDIUM | 85 lines of macOS-only Homebrew paths |

**Execution**: A-2 through A-5 in parallel (independent). A-1 after (touches many files).

### Phase B: Round E — Medium-Lift Features (DONE)

| Step | OPP | Name | Type | Status |
|------|-----|------|------|--------|
| B-1 | OPP-21 | Native Reasoning Parameter | EVOLUTION | ✅ DONE |
| B-2 | OPP-24 | Model Auto-Download (REST API) | EVOLUTION | ✅ DONE |
| B-3 | OPP-27 | Advanced Model Load Params | EVOLUTION | ✅ DONE |
| B-4 | OPP-28 | API Authentication | NEW | ✅ DONE |
| B-5 | OPP-29 | Log-Probabilities | NEW | ✅ DONE |
| B-6 | OPP-31 | Model Profiles | NEW | ✅ DONE |

### Phase C: Round F — Major Features (DONE)

| Step | OPP | Name | Type | Status |
|------|-----|------|------|--------|
| C-1 | OPP-19 | Native Chat API (`/api/v1/chat`) | EVOLUTION | ✅ DONE |
| C-2 | OPP-25 | Ephemeral MCP Servers | EVOLUTION | ✅ DONE |

### v5.0.0 Execution Order

```
Phase A: Architecture (unblocks cleaner Phase B/C implementation)
  A-2 ═══╗
  A-3 ═══╣ parallel (independent)
  A-4 ═══╣
  A-5 ═══╝
  A-1 ────→ (after A-2..A-5, touches many files)
              │
              ▼
Phase B: Medium-Lift Features
  OPP-21 ═══╗
  OPP-28 ═══╣ parallel (independent)
  OPP-29 ═══╣
  OPP-31 ═══╝
  OPP-27 → OPP-24  (sequential, shared files)
              │
              ▼
Phase C: Major Features
  OPP-19 → OPP-25  (sequential, dependency)
```

**Gate**: Coverage >= 90%, all tests pass, architecture score >= 75/100, VERSION → v5.0.0

### v5.0.0 Gate ✅
- [x] All 8 v5 OPPs + 5 ARCH items implemented and tested
- [x] Coverage >= 91% (maintained)
- [x] All tests pass (~1969 total)
- [x] Architect verification passed (APPROVED)
- [x] VERSION bumped to v5.0.0
- [x] Ruff + pyright clean on all new files

---

## New Dependency Chains (v4.0.0 / v5.0.0)

### Chain E: Streaming Evolution (ALL DONE)
```
OPP-12 DONE → OPP-23 DONE → OPP-19 DONE
```

### Chain F: Model Lifecycle Evolution (ALL DONE)
```
OPP-04 DONE → OPP-22 DONE
OPP-04 DONE → OPP-27 DONE → OPP-24 DONE
OPP-04 DONE → OPP-30 DONE
```

### Chain G: Reasoning Evolution (ALL DONE)
```
OPP-14 DONE → OPP-21 DONE
```

### Chain H: MCP Evolution (ALL DONE)
```
OPP-16 DONE → OPP-19 DONE → OPP-25 DONE
```

### Chain I: Model Profiles (ALL DONE)
```
OPP-04 DONE → OPP-22 DONE → OPP-31 DONE
OPP-26 DONE ──────────────↗
```

### Independent (ALL DONE)
```
OPP-26 DONE (sampling params)
OPP-28 DONE (auth)
OPP-29 DONE (logprobs)
```

---

## OPP Classification Summary

### By Type

| Type | Count | OPPs |
|------|-------|------|
| EVOLUTION (extends existing) | 8 | OPP-19, 21, 22, 23, 24, 25, 27, 30 |
| NEW (greenfield) | 4 | OPP-26, 28, 29, 31 |
| ALREADY EXISTS (removed) | 1 | ~~OPP-20~~ (structured output — already in v3.2.0) |

### By Backward Compatibility

| Compat | Count | OPPs |
|--------|-------|------|
| Yes (additive) | 9 | OPP-22, 23, 24, 26, 27, 28, 29, 30, 31 |
| No (breaking) | 3 | OPP-19, 21, 25 |

---

## API Combination Opportunities (COMBO)

These are not individual OPPs — they are **synergy effects** from combining multiple OPPs.

### COMBO-A: Intelligent Streaming (OPP-19 + OPP-23 + OPP-21)

**What**: Unified streaming pipeline showing model loading progress, reasoning tokens as they stream, tool call results, AND token usage — all in one stream.

**Why it matters**: Currently our streaming is a "dumb pipe" — we get text chunks and `[DONE]`. With native chat's 19 event types + usage tracking + reasoning, every streaming call becomes an observable, debuggable pipeline.

**Evolves**: OPP-12 (Streaming) from "text chunks" to "rich event stream"

### COMBO-B: Self-Provisioning Bridge (OPP-24 + OPP-27 + OPP-22 + OPP-08)

**What**: User requests a capability (e.g., "coding model") → bridge checks loaded models (OPP-22, fast single-lookup) → smart selector picks best (OPP-08, existing) → if none suitable, downloads optimal model (OPP-24) → loads with tuned GPU/memory config (OPP-27). Zero manual model management.

**Why it matters**: Eliminates the #1 UX friction — users currently must manually find, download, and load models. This makes it "just work".

**Evolves**: OPP-04 + OPP-08 from "manage what you have" to "get what you need"

### COMBO-C: Secure Multi-Tenant (OPP-28 + OPP-25 + OPP-19)

**What**: Each API caller gets their own permission scope + ephemeral MCP servers + stateful chat session. Enables shared LM Studio server across multiple users/apps.

**Why it matters**: Opens a new deployment model — team/shared servers instead of single-developer localhost.

**Creates**: NEW capability that doesn't exist in any form today

### COMBO-D: Confidence-Scored Output (OPP-29 + existing structured output + OPP-21)

**What**: Get structured JSON + log-probabilities showing model confidence per token + reasoning trace. Enables "reject if confidence < threshold" for production reliability.

**Why it matters**: Autonomous loops (OPP-02/06/07/17) currently trust LLM output blindly. This adds a quality gate.

**Evolves**: OPP-02 (Self-Correcting Loops) from "retry on error" to "retry on low confidence"

### COMBO-E: Observable Autonomous Loop (OPP-19 + OPP-07 + OPP-23 + OPP-21)

**What**: The autonomous loop streams model thinking in real-time, tool calls as they happen, token budget consumption, and reasoning quality — all observable via the existing observability infrastructure.

**Why it matters**: Debugging autonomous agents goes from "wait and pray" to "watch and steer".

**Evolves**: OPP-07 (Observability) from "post-hoc metrics" to "real-time observability"

### COMBO-F: Zero-Config Model Router (OPP-22 + OPP-30 + OPP-08 + OPP-27)

**What**: Smart selector picks model → loads with optimal config → echo confirms actual params → caches effective config for next time. Self-tuning model management.

**Why it matters**: Removes trial-and-error from model configuration. The bridge learns what works.

**Evolves**: OPP-08 (Smart Selection) from "pick the model" to "pick AND tune the model"

---

## Round G — Log Analysis OPPs (PROPOSED)

> Source: `docs/LOG_ANALYSIS_2026-03-02.md` — 4-round deep analysis of 188K-line LM Studio server log
> 31 issues found (8 CRITICAL, 12 HIGH, 8 MEDIUM, 3 LOW) → 19 raw OPPs → **10 actionable** after root cause analysis
>
> **Root Cause Analysis (2026-03-02)**: 4 parallel architect agents traced every OPP through the codebase.
> Found 2 root causes (missing model lifecycle state machine + `dynamic_autonomous.py` god module),
> leading to 4 mergers, 3 removals, 1 deferral, 1 redefinition. See changelog for details.

### Priority 0 (Critical — Data Loss / Silent Failures)

| Step | OPP | Name | Type | Fixes | Effort | Files |
|------|-----|------|------|-------|--------|-------|
| G-1 | OPP-32 | Schema-Aware Type Coercion | EVOLUTION | 11/13 WARNs, 15 orphans | MEDIUM | ✅ **DONE** — 2 commits, 22 tests |
| G-2 | OPP-38 | Fix "model: default" Fallback | BUGFIX | 167 ERRORs, 135 rejected requests | LOW | ✅ **DONE** — 6 commits, 22 tests |
| G-3 | OPP-39 | Context Window Guard | NEW | 282K wasted tokens (3 × 94K overflow) | MEDIUM | `tools/dynamic_autonomous.py` |
| G-4 | OPP-43 | Poll Rate Limiter (JIT memoization) | DONE | 11,613 polls (85% of events), 789/min peak | MEDIUM | ✅ **DONE** — 2 commits, 21 tests, 60s JIT guard TTL |

### Priority 1 (High — Reliability / Efficiency)

| Step | OPP | Name | Type | Fixes | Effort | Files |
|------|-----|------|------|-------|--------|-------|
| G-5 | OPP-33 | Pre-Dispatch Tool Argument Validation | NEW | 2 WARNs (missing required params), reduces orphans | LOW | `tools/dynamic_autonomous.py` |
| ~~G-6~~ | ~~OPP-34~~ | ~~Model Tool-Calling Error Budget~~ | ~~NEW~~ | **MERGED → OPP-45** (tracking without action is subset of auto-demotion) | — | — |
| G-7 | OPP-37 | Orphan Detection with Fast-Fail | EVOLUTION | 23 orphaned tool calls (24% rate) | MEDIUM | `tools/dynamic_autonomous.py` |
| G-8 | OPP-40 | Tool Result Caching | NEW | 42% duplicate tool calls (~30 redundant). **+OPP-47 merged**: cache key normalization handles namespace differences | MEDIUM | `tools/dynamic_autonomous.py` |
| G-9 | OPP-44 | Tool Call Circuit Breaker | NEW | 7 consecutive failures before self-correct, no max retries. **+OPP-48 merged**: 10 truncated JSON parse failures count as breaker errors | MEDIUM | `tools/dynamic_autonomous.py` |
| G-10 | OPP-45 | Per-Model Error Budget with Auto-Demotion | NEW | glm 80% of events + 100% of errors, no demotion. **+OPP-34 merged**: error tracking + action in one OPP. Integrates `ModelFallbackManager` | MEDIUM | `tools/dynamic_autonomous.py`, `llm/llm_client.py`, `utils/model_fallback.py` |
| G-11 | OPP-46 | Adaptive Timeout (Both Inference Phases) | NEW | 3 × wasted prompt processing (94K tokens → 0 output), 9 disconnects during generation, 126 prompt re-starts (91% re-processing). **+OPP-49 merged**: unified timeout for prompt processing AND generation phases | MEDIUM→HIGH | `llm/llm_client.py`, `llm/responses_client.py`, `tools/dynamic_autonomous.py` |

### Round 4 Additions (Post Root Cause Analysis)

| Step | OPP | Name | Type | Fixes | Effort | Files |
|------|-----|------|------|-------|--------|-------|
| ~~G-17~~ | ~~OPP-48~~ | ~~Truncated Tool Call Recovery~~ | ~~NEW~~ | **MERGED → OPP-44** (parse failures count as circuit breaker errors) | — | — |
| ~~G-18~~ | ~~OPP-49~~ | ~~Generation-Aware Timeout~~ | ~~NEW~~ | **MERGED → OPP-46** (unified adaptive timeout for both inference phases) | — | — |
| G-19 | OPP-50 | Tool Schema Dedup Experiment | EXPERIMENT | Test: omit `tools` from payload after round 0 when `previous_response_id` is set. If LM Studio accepts, saves ~3,810 repeated definitions/session | LOW | `llm/responses_client.py` |

### Priority 2 (Medium — Observability / Optimization)

| Step | OPP | Name | Type | Fixes | Effort | Files |
|------|-----|------|------|-------|--------|-------|
| ~~G-12~~ | ~~OPP-35~~ | ~~LMSAuthenticator getModelInfo Caching~~ | ~~EVOLUTION~~ | **REMOVED**: 6,273 calls are LM Studio INTERNAL (`lms-cli`), not our bridge. Our `list_all_models()` already cached at 30s TTL (`lms_helper.py:92-97`) | — | — |
| ~~G-13~~ | ~~OPP-36~~ | ~~Logprobs Response Bloat Suppression~~ | ~~EVOLUTION~~ | **REMOVED**: Bridge never requests logprobs (default=False). LM Studio sends empty `top_logprobs: []` server-side. Not a bridge code issue | — | — |
| ~~G-14~~ | ~~OPP-41~~ | ~~Conversation Chain Health Monitoring~~ | ~~NEW~~ | **REMOVED**: Short chains (avg 2.4) = efficient task completion, NOT a bug. Already partially captured in `LoopMetrics.total_rounds` | — | — |
| G-15 | OPP-42 | Token Budget Monitoring & Alerting | NEW | **DEFERRED**: Re-measure after OPP-39 bounds context. 27:1 ratio dominated by 3×94K overflow outliers. Also blocked by LM Studio `/v1/responses` not returning token counts | LOW | `tools/dynamic_autonomous.py` |
| ~~G-16~~ | ~~OPP-47~~ | ~~Tool Name Normalization Layer~~ | ~~NEW~~ | **MERGED → OPP-40** (cache key normalization is 5-line implementation detail, not standalone OPP) | — | — |

### Dependency Chains (Post Root Cause Analysis)

```
Root Cause 1: Missing Model Lifecycle State Machine
  OPP-38 (fix "default") → OPP-43 (poll limiter)
  (fixing "default" eliminates error-amplified polling)

Root Cause 2: dynamic_autonomous.py God Module — Missing ToolCallContext
  OPP-32 (schema coercion) ─┐
  OPP-33 (pre-dispatch)     ├─→ ToolCallContext foundation
  OPP-44 (circuit breaker)  ─┘        │
                                       ├→ OPP-37 (orphan detection) + OPP-40 (result cache)
                                       └→ OPP-45 (per-model error budget + auto-demotion)

Context Efficiency:
  OPP-39 (context guard) → OPP-42 (token monitoring, DEFERRED)

Timeout Intelligence:
  OPP-46 (adaptive timeout, both phases — absorbs OPP-49)

Independent:
  OPP-50 (tool schema dedup experiment)
```

### Execution Order (Revised — Root Cause Driven)

```
Phase 1: Kill the Cascade ✅ DONE
  OPP-38 ✅ ──→ fix "default" sentinel escape (6 commits, 22 tests, 1991 pass)

Phase 2: Foundations (parallel)
  OPP-39 ═══╗ context window guard
  OPP-32 ═══╣ schema-aware type coercion
  OPP-43 ═══╝ poll rate limiter (after OPP-38 removes error amplification)

Phase 3: Build ToolCallContext (sequential pair, then parallel)
  OPP-33 + OPP-44 ═══╗ pre-dispatch validation + circuit breaker (shared foundation)
  OPP-37 + OPP-40   ═╝ orphan detection + result cache (extend context)

Phase 4: Model Intelligence
  OPP-45 ────→ per-model error budget + auto-demotion (integrates ModelFallbackManager)

Phase 5: Streaming Refactor (most invasive, do last)
  OPP-46 ────→ adaptive timeout for both inference phases (requires non-streaming → streaming)

Phase 6: Quick Experiment
  OPP-50 ────→ test omitting tools after round 0 with previous_response_id
```

### Consolidated OPP Summary

| Status | Count | OPPs |
|--------|-------|------|
| **Active** | 9 | OPP-32, 33, 37, 39, 40, 43, 44, 45, 46 |
| **Done (Round G)** | 1 | OPP-38 |
| **Experiment** | 1 | OPP-50 |
| **Deferred** | 1 | OPP-42 (re-measure after OPP-39) |
| **Merged** | 4 | OPP-34→45, OPP-47→40, OPP-48→44, OPP-49→46 |
| **Removed** | 3 | OPP-35, 36, 41 |
| **Total original** | 19 | OPP-32 through OPP-50 |

### Gate

- [ ] All P0 OPPs (32, 38, 39, 43) implemented and tested
- [ ] ToolCallContext pattern implemented (enables OPP-33, 37, 40, 44)
- [ ] Coverage >= 91% maintained
- [ ] All existing tests pass
- [ ] Re-run log analysis scenario to confirm fix
- [ ] VERSION → v5.1.0 (or v6.0.0 if breaking)

---

## Changelog

| Date | Change |
|------|--------|
| 2026-02-23 | Initial backlog created from ROADMAP.md + evidence-based analysis |
| 2026-02-23 | Phase 0: H-01 (git pull), H-02 (tests verified), H-06 (worktrees cleaned), H-08 (coverage: 69%) |
| 2026-02-23 | Round B complete: 5 OPPs, v3.4.0, ~80% coverage |
| 2026-02-23 | Round C complete: 3 OPPs, v3.5.0, ~90% coverage |
| 2026-02-23 | Comprehensive OPP review: 12 fix commits (3 CRITICAL, 8 HIGH, 4 MEDIUM) |
| 2026-02-23 | Test infrastructure overhaul: 12 commits, coverage 76% → 89%, tests 1355 → ~1405 |
| 2026-02-23 | Updated backlog to reflect v3.5.0 completion state |
| 2026-02-24 | Server error audit: 10 bugs fixed (5 commits), tests 1405 → ~1455, coverage 89% → 91% |
| 2026-02-24 | API gap analysis: 11 new OPPs (OPP-19 to OPP-30, minus OPP-20 already exists) |
| 2026-02-24 | Added Round D (quick wins), Round E (medium lift), Round F (major features) |
| 2026-02-24 | Added 6 API combination opportunities (COMBO-A through COMBO-F) |
| 2026-02-24 | Versioning revision: Round C → v3.5.0, Round D → v4.0.0, merged Round E + F + Architecture into v5.0.0 |
| 2026-02-24 | OPP-21 moved from Round D to v5.0.0 Phase B (breaking change bundles with v5) |
| 2026-02-24 | Added Architecture Refactoring phase (ARCH-1..5) from ARCHITECTURE_REVIEW.md findings |
| 2026-03-01 | Code quality audit: 12 findings fixed (threading, error contracts, logging, dedup, imports) |
| 2026-03-01 | VERSION bumped to 4.0.0, docs updated to reflect current state |
| 2026-03-01 | OPP-31 (Model Profiles) spec written — 7-stage research, 112 sources, RICE 24.3, added to v5.0.0 Phase B |
| 2026-03-02 | v5.0.0 complete: 57 commits, Phase A (5 ARCH) + Phase B (6 OPPs) + Phase C (2 OPPs), ~1969 tests, 91% coverage |
| 2026-03-02 | All v5 sections marked DONE, gate checklist verified, documentation updated |
| 2026-03-02 | Log analysis: 2-round deep analysis of 188K-line server log → 17 issues, 11 new OPPs (OPP-32 to OPP-42) |
| 2026-03-02 | Added Round G (Log Analysis OPPs) with 4 batches, 3 dependency chains, gate criteria |
| 2026-03-02 | Round 3 log analysis: 11 additional findings → 5 new OPPs (OPP-43 to OPP-47), total 28 issues, 16 OPPs |
| 2026-03-02 | Round G updated: 16 OPPs across 5 batches, 5 dependency chains (J-M + independent), gate updated |
| 2026-03-02 | Round 4 log analysis: 3 additional findings → 3 new OPPs (OPP-48 to OPP-50), total 31 issues, 19 OPPs |
| 2026-03-02 | Round G updated: 19 OPPs across 6 batches, 7 dependency chains (J-O + independent), evidence updated for OPP-43/45/46 |
| 2026-03-02 | Root cause analysis: 4 parallel architect agents traced every OPP through codebase. Found 2 root causes (missing model lifecycle state machine + `dynamic_autonomous.py` god module). Consolidated 19 raw OPPs → 10 active + 1 experiment + 1 deferred + 4 merged (34→45, 47→40, 48→44, 49→46) + 3 removed (35, 36, 41). Replaced batch execution with 6-phase root-cause-driven plan |
| 2026-03-02 | OPP-38 DONE: 6 atomic TDD commits on `feat/opp-38-default-sentinel-fix`. Added `is_model_sentinel()` helper, fixed 4 vulnerable clients (V1-V4), refactored 8 files to use centralized helper. 22 new tests, 1991 total pass, 0 fail |
