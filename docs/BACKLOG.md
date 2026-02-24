# LM Studio Bridge Enhanced — Execution Backlog

> Updated: 2026-02-24 | Post-error-audit | Baseline: ~1455 tests passing, 91% coverage

---

## Current State (Verified 2026-02-23)

| Metric | Value |
|--------|-------|
| Branch | `fix/server-error-audit` at `275c243` |
| Tests | ~1455 passed, 0 failures, 4 skipped |
| Coverage | **91%** |
| Coverage target | **80% minimum / 89% goal (exceeded)** |
| VERSION | 4.0.0 (in constants.py) |
| Completed rounds | Phase 1, Phase 1.5, Round A, Round B, Round C, Polish, Error Audit |

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

## Completed OPPs (All 14)

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
| OPP-17 | Dual-Format Autonomous | Round C | 14 | v4.0.0 |
| OPP-09 | Multi-Modal Loops | Round C | 12 | v4.0.0 |
| OPP-15 | Conversation Branching | Round C | 4 | v4.0.0 |

Phase 1.5 code quality (OPP-05-10 code quality items): PR #4 + PR #5

---

## Round B — Phase 4 (DONE — v3.4.0)

All 5 OPPs implemented, tested, and merged. Coverage reached ~80%.

---

## Round C — Phase 5 (DONE — v4.0.0)

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
- [x] VERSION bumped to **v4.0.0**
- [x] README updated with final feature list

### Polish Gate ✅
- [x] Coverage push toward **89%** goal (achieved 89%)
- [x] Test infrastructure overhaul complete (12 commits)
- [x] Comprehensive OPP review complete (12 fix commits)
- [ ] All documentation current (in progress)
- [ ] Release tag created
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
Round C ────────────────┘ DONE (v4.0.0)
  C-Step 1: OPP-17 ═══╗ parallel
            OPP-15 ═══╝
  C-Step 2: OPP-09 ────→
  [Gate: coverage ≥ 80% ✅, VERSION → v4.0.0 ✅]
                        │
Polish ─────────────────┘ IN PROGRESS
  - Coverage push → 89% ✅
  - Test infra overhaul ✅ (12 commits)
  - OPP review ✅ (12 fix commits)
  - Docs update (in progress)
  - Release tag (pending)
```

---

## Round D — Quick Wins (PROPOSED — v4.1.0)

Low-effort, high-value additive improvements. All backward compatible.

| Step | OPP | Name | Type | Evolves | Backward Compat | Effort | Depends On |
|------|-----|------|------|---------|-----------------|--------|------------|
| D-1 | OPP-21 | Native Reasoning Parameter | EVOLUTION | OPP-14 (Extended Thinking) | No — replaces `thinking_budget` | LOW | OPP-14 ✅ |
| D-2 | OPP-22 | Single-Model Lookup | EVOLUTION | OPP-04 (Model Lifecycle) | Yes — additive | LOW | OPP-04 ✅ |
| D-3 | OPP-23 | Streaming Usage Tracking | EVOLUTION | OPP-12 (Streaming) | Yes — additive | LOW | OPP-12 ✅ |
| D-4 | OPP-26 | Advanced Sampling (min_p, top_k) | NEW | None | Yes — additive | LOW | None |
| D-5 | OPP-30 | Echo Load Config | EVOLUTION | OPP-04 (Model Lifecycle) | Yes — additive | LOW | OPP-04 ✅ |

**Parallelization**: All 5 OPPs are independent — execute ALL in parallel.

**Gate**: Coverage >= 91%, all tests pass, VERSION → v4.1.0

---

## Round E — Medium Lift (PROPOSED — v4.2.0)

Medium-effort improvements that extend existing infrastructure.

| Step | OPP | Name | Type | Evolves | Backward Compat | Effort | Depends On |
|------|-----|------|------|---------|-----------------|--------|------------|
| E-1 | OPP-24 | Model Auto-Download (REST API) | EVOLUTION | OPP-04 (Model Lifecycle) | Yes — additive | MEDIUM | OPP-04 ✅ |
| E-2 | OPP-27 | Advanced Model Load Params | EVOLUTION | OPP-04 (Model Lifecycle) | Yes — additive | LOW | OPP-04 ✅ |
| E-3 | OPP-28 | API Authentication | NEW | None | Yes — additive header | LOW | None |
| E-4 | OPP-29 | Log-Probabilities | NEW | None | Yes — additive | LOW | None |

**Parallelization**: OPP-24 + OPP-27 share `lms_helper.py` — execute sequentially. OPP-28 + OPP-29 are independent.

```
E-Step 1: OPP-27 (advanced load) → OPP-24 (auto-download, builds on load)
E-Step 2: OPP-28 ═══╗ parallel (zero file overlap)
          OPP-29 ═══╝
```

**Gate**: Coverage >= 91%, all tests pass, VERSION → v4.2.0

---

## Round F — Major Features (PROPOSED — v5.0.0)

High-effort features that significantly restructure existing systems. Breaking changes expected.

| Step | OPP | Name | Type | Evolves | Backward Compat | Effort | Depends On |
|------|-----|------|------|---------|-----------------|--------|------------|
| F-1 | OPP-19 | Native Chat API (`/api/v1/chat`) | EVOLUTION | OPP-12 (Streaming) + OPP-16 (Native MCP) | No — new streaming parser | HIGH | OPP-12 ✅, OPP-16 ✅ |
| F-2 | OPP-25 | Ephemeral MCP Servers | EVOLUTION | OPP-16 (Native MCP via API) | No — restructures `mcp_servers` | HIGH | OPP-16 ✅, OPP-19 |

**Execution**: Sequential — OPP-19 must land first (OPP-25 uses native chat API).

**Gate**: Coverage >= 90%, all tests pass, VERSION → v5.0.0

---

## New Dependency Chains (Round D/E/F)

### Chain E: Streaming Evolution
```
OPP-12 DONE → OPP-23 (usage tracking) → OPP-19 (native chat)
```

### Chain F: Model Lifecycle Evolution
```
OPP-04 DONE → OPP-22 (single lookup)
OPP-04 DONE → OPP-27 (advanced load) → OPP-24 (auto-download)
OPP-04 DONE → OPP-30 (echo config)
```

### Chain G: Reasoning Evolution
```
OPP-14 DONE → OPP-21 (native reasoning)
```

### Chain H: MCP Evolution
```
OPP-16 DONE → OPP-19 (native chat) → OPP-25 (ephemeral MCP)
```

### Independent
```
OPP-26 (sampling params) — no dependencies
OPP-28 (auth) — no dependencies
OPP-29 (logprobs) — no dependencies
```

---

## OPP Classification Summary

### By Type

| Type | Count | OPPs |
|------|-------|------|
| EVOLUTION (extends existing) | 8 | OPP-19, 21, 22, 23, 24, 25, 27, 30 |
| NEW (greenfield) | 3 | OPP-26, 28, 29 |
| ALREADY EXISTS (removed) | 1 | ~~OPP-20~~ (structured output — already in v3.2.0) |

### By Backward Compatibility

| Compat | Count | OPPs |
|--------|-------|------|
| Yes (additive) | 7 | OPP-22, 23, 24, 26, 27, 28, 29, 30 |
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

## Changelog

| Date | Change |
|------|--------|
| 2026-02-23 | Initial backlog created from ROADMAP.md + evidence-based analysis |
| 2026-02-23 | Phase 0: H-01 (git pull), H-02 (tests verified), H-06 (worktrees cleaned), H-08 (coverage: 69%) |
| 2026-02-23 | Round B complete: 5 OPPs, v3.4.0, ~80% coverage |
| 2026-02-23 | Round C complete: 3 OPPs, v4.0.0, ~90% coverage |
| 2026-02-23 | Comprehensive OPP review: 12 fix commits (3 CRITICAL, 8 HIGH, 4 MEDIUM) |
| 2026-02-23 | Test infrastructure overhaul: 12 commits, coverage 76% → 89%, tests 1355 → ~1405 |
| 2026-02-23 | Updated backlog to reflect v4.0.0 completion state |
| 2026-02-24 | Server error audit: 10 bugs fixed (5 commits), tests 1405 → ~1455, coverage 89% → 91% |
| 2026-02-24 | API gap analysis: 11 new OPPs (OPP-19 to OPP-30, minus OPP-20 already exists) |
| 2026-02-24 | Added Round D (quick wins), Round E (medium lift), Round F (major features) |
| 2026-02-24 | Added 6 API combination opportunities (COMBO-A through COMBO-F) |
