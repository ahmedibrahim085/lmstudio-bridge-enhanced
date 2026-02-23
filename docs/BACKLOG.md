# LM Studio Bridge Enhanced — Execution Backlog

> Generated: 2026-02-23 | Post-Round A sync | Baseline: 69% coverage, 709 tests passing

---

## Current State (Verified 2026-02-23)

| Metric | Value |
|--------|-------|
| Branch | `main` at `065d165` |
| Tests | 709 passed, 2 infra failures, 4 skipped, 3 xpassed |
| Coverage | **69%** (4435 statements, 1366 missed) |
| Coverage target | **80% minimum / 89% goal** |
| VERSION | 3.2.2 (in constants.py) |
| Completed rounds | Phase 1, Phase 1.5, Round A |

---

## Phase 0 — Housekeeping (BEFORE Round B)

| # | Item | Status | Notes |
|---|------|--------|-------|
| H-01 | Git pull origin main | DONE | Fast-forwarded 22 commits |
| H-02 | Verify Round A tests | DONE | 709 passed, 2 infra failures (expected) |
| H-03 | Commit PLANNING_GUIDELINES.md | TODO | Untracked at `docs/PLANNING_GUIDELINES.md` |
| H-04 | Update ROADMAP.md Round A status | TODO | Shows "Not started" — should be "DONE (PR #7)" |
| H-05 | Fix DEFAULT_MAX_RETRIES 3-way collision | TODO | `config/constants.py` (=3), `llm/llm_client.py` (=2), `utils/retry.py` (=3 env) |
| H-06 | Clean stale worktrees | DONE | Removed `suva-wt-opp05` and `suva-wt-opp11` |
| H-07 | Create safety tag | TODO | `git tag v3.3.0-pre-round-b` |
| H-08 | Record coverage baseline | DONE | 69% overall |

---

## Dependency Chains

### Chain A: Anthropic Stack
```
OPP-01 DONE → OPP-11 DONE → OPP-13 DONE → OPP-17 (Round C)
                         ↘
                          OPP-10 (Round B)
```

### Chain B: Autonomous Loop Stack
```
OPP-02 DONE → OPP-06 DONE → OPP-07 DONE → OPP-08 (Round B)
OPP-02 DONE → OPP-14 (Round B)
```

### Chain C: Streaming & Branching
```
OPP-03 DONE → OPP-12 (Round B) → OPP-15 (Round C)
```

### Chain D: Multi-Modal
```
OPP-10 (Round B) → OPP-09 (Round C)
```

### Independent
```
OPP-04 DONE → OPP-18 (Round B)
```

---

## Completed OPPs (Reference)

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

Phase 1.5 code quality (OPP-05-10 code quality items): PR #4 + PR #5

---

## Round B — Phase 4 (5 OPPs, RICE total: 85.9)

### File Overlap Matrix

| OPP | Primary Files | Conflicts With |
|-----|--------------|----------------|
| OPP-08 | `model_registry/registry.py`, `model_registry/schemas.py`, `model_registry/tools.py` | None |
| OPP-18 | `tools/health.py`, new deployment module | None |
| OPP-12 | `llm/llm_client.py` (streaming generator), `tools/completions.py` | OPP-14 (llm_client.py) |
| OPP-14 | `llm/llm_client.py` (thinking tokens), `config/constants.py` | OPP-12 (llm_client.py) |
| OPP-10 | New `llm/format_adapter.py`, `config/constants.py` | OPP-14 (constants.py) |

### Execution Order

| Step | OPP(s) | Parallel? | RICE | Dependencies Satisfied |
|------|--------|-----------|------|----------------------|
| **B-Step 1** | **OPP-08** + **OPP-18** | YES (parallel) | 18 + 16 | OPP-07 DONE, OPP-04 DONE |
| **B-Step 2** | **OPP-12** | Sequential | 21.3 | OPP-03 DONE |
| **B-Step 3** | **OPP-14** | Sequential after B-2 | 14.7 | OPP-02 DONE |
| **B-Step 4** | **OPP-10** | Sequential last | 16 | OPP-11 DONE |

### OPP Details

#### OPP-08: Smart Model Selection (RICE: 18)
- **Problem**: No intelligent model routing based on task requirements
- **Depends on**: OPP-01 (Capabilities API) DONE, OPP-07 (Observability) DONE
- **Key files**: `model_registry/registry.py` (42% coverage), `model_registry/tools.py` (37% coverage), `model_registry/schemas.py`
- **Coverage opportunity**: Fixes registry.py (42% → 80%+) and tools.py (37% → 80%+)
- **Scope**: Task-to-model matching, capability-based filtering, performance-weighted selection

#### OPP-18: Headless Deployment — llmster (RICE: 16)
- **Problem**: No support for headless LM Studio daemon deployments
- **Depends on**: OPP-04 (REST client) DONE
- **Key files**: `tools/health.py` (21% coverage), `tools/lms_cli_tools.py` (36% coverage)
- **Coverage opportunity**: Fixes health.py (21% → 80%+) and lms_cli_tools.py (36% → 60%+)
- **Scope**: Detect llmster vs GUI, health checks, graceful degradation, CI example

#### OPP-12: Streaming (RICE: 21.3)
- **Problem**: No streaming support for long completions
- **Depends on**: OPP-03 (JIT Loading) DONE
- **Key files**: `llm/llm_client.py`, `tools/completions.py` (36% coverage)
- **Coverage opportunity**: Fixes completions.py (36% → 80%+)
- **Scope**: SSE streaming for chat_completion, create_response, and anthropic_messages

#### OPP-14: Extended Thinking (RICE: 14.7)
- **Problem**: No support for reasoning/thinking tokens in model responses
- **Depends on**: OPP-02 (Self-Correcting Loops) DONE
- **Key files**: `llm/llm_client.py`, `config/constants.py`
- **Scope**: Thinking token parameters, budget management, model capability check
- **Note**: Model-dependent — requires reasoning-capable models in LM Studio

#### OPP-10: Format Adapter — 3-way Routing (RICE: 16)
- **Problem**: No unified format translation between OpenAI, Anthropic, and Responses APIs
- **Depends on**: OPP-01 (Capabilities API) DONE, OPP-11 (Anthropic Endpoint) DONE
- **Key files**: New `llm/format_adapter.py`, `config/constants.py`
- **Scope**: Bidirectional translation: OpenAI chat ↔ Anthropic messages ↔ Responses format
- **Routes**: `/v1/chat/completions`, `/v1/messages`, `/v1/responses`

---

## Round C — Phase 5 (3 OPPs, RICE total: 30)

### File Overlap Matrix

| OPP | Primary Files | Conflicts With |
|-----|--------------|----------------|
| OPP-17 | `tools/dynamic_autonomous.py` | None |
| OPP-15 | New branching module | None |
| OPP-09 | `tools/vision.py`, `tools/embeddings.py`, format adapter | None |

### Execution Order

| Step | OPP(s) | Parallel? | RICE | Dependencies Satisfied |
|------|--------|-----------|------|----------------------|
| **C-Step 1** | **OPP-17** + **OPP-15** | YES (parallel) | 14 + 4 | OPP-13 DONE, OPP-12 (Round B) |
| **C-Step 2** | **OPP-09** | Sequential after C-1 | 12 | OPP-10 (Round B) |

### OPP Details

#### OPP-17: Dual-Format Autonomous (RICE: 14)
- **Problem**: Autonomous loop only works with OpenAI format, not Anthropic
- **Depends on**: OPP-11 (Anthropic Endpoint) DONE, OPP-13 (Anthropic Tool Use) DONE
- **Key files**: `tools/dynamic_autonomous.py` (86% coverage)
- **Scope**: Autonomous loop dispatch via Anthropic format, format-agnostic tool execution

#### OPP-15: Conversation Branching (RICE: 4)
- **Problem**: No support for branching/forking conversation histories
- **Depends on**: OPP-03 (JIT Loading) DONE, OPP-12 (Streaming, Round B)
- **Key files**: New `llm/conversation_branch.py`
- **Scope**: Fork/branch conversations, merge branches, tree navigation
- **Note**: Native API only — not OpenAI-compatible

#### OPP-09: Multi-Modal Loops (RICE: 12)
- **Problem**: Autonomous loops cannot process images/vision input
- **Depends on**: OPP-10 (Format Adapter, Round B)
- **Key files**: `tools/vision.py` (43% coverage), `tools/embeddings.py` (42% coverage)
- **Coverage opportunity**: Fixes vision.py (43% → 80%+) and embeddings.py (42% → 80%+)
- **Scope**: Image input in autonomous loops, multi-modal tool results

---

## Coverage Debt Tracker

| Module | Current | Target | Fix In |
|--------|---------|--------|--------|
| `tools/dynamic_autonomous_register.py` | 0% | 80% | Round B, OPP-08 |
| `tools/health.py` | 21% | 80% | Round B, OPP-18 |
| `tools/completions.py` | 36% | 80% | Round B, OPP-12 |
| `tools/lms_cli_tools.py` | 36% | 60% | Round B, OPP-18 |
| `model_registry/tools.py` | 37% | 80% | Round B, OPP-08 |
| `tools/embeddings.py` | 42% | 80% | Round C, OPP-09 |
| `model_registry/registry.py` | 42% | 80% | Round B, OPP-08 |
| `tools/vision.py` | 43% | 80% | Round C, OPP-09 |
| `utils/observability.py` | 0% | 80% | Round B, OPP-08 |

---

## Quality Gates

### Round B Gate (before Round C starts)
- [ ] All 5 Round B OPPs implemented and tested
- [ ] Coverage >= **75%** (from current 69%)
- [ ] All existing tests still pass
- [ ] Integration tests pass for OPP-12 (streaming) and OPP-10 (format adapter)
- [ ] Architecture guard tests pass
- [ ] VERSION bumped to **v3.4.0**
- [ ] Safety tag created

### Round C Gate (before release)
- [ ] All 3 Round C OPPs implemented and tested
- [ ] Coverage >= **80%** (minimum target)
- [ ] All tests pass (estimated ~800+ total)
- [ ] Full integration test suite passes
- [ ] Architecture guard tests pass
- [ ] VERSION bumped to **v4.0.0**
- [ ] README updated with final feature list

### Polish Gate (final)
- [ ] Coverage push toward **89%** goal
- [ ] All documentation current
- [ ] Release tag created
- [ ] CI/CD pipeline green

---

## Timeline View

```
Phase 0 (Housekeeping) ←── WE ARE HERE
  H-03 → H-04 → H-05 → H-07
                              │
Round B ──────────────────────┘
  B-Step 1: OPP-08 ═══╗ parallel
            OPP-18 ═══╝
  B-Step 2: OPP-12 ────→
  B-Step 3: OPP-14 ────→
  B-Step 4: OPP-10 ────→
  [Gate: coverage ≥ 75%, VERSION → v3.4.0]
                        │
Round C ────────────────┘
  C-Step 1: OPP-17 ═══╗ parallel
            OPP-15 ═══╝
  C-Step 2: OPP-09 ────→
  [Gate: coverage ≥ 80%, VERSION → v4.0.0]
                        │
Polish ─────────────────┘
  - Coverage push → 89%
  - Docs update
  - Release tag
```

---

## Changelog

| Date | Change |
|------|--------|
| 2026-02-23 | Initial backlog created from ROADMAP.md + evidence-based analysis |
| 2026-02-23 | Phase 0: H-01 (git pull), H-02 (tests verified), H-06 (worktrees cleaned), H-08 (coverage: 69%) |
