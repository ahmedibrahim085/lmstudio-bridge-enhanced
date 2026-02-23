# Planning & Execution Guidelines v2.0

> *Updated: 2026-02-23 | Based on: Original guidelines + evidence from Round A execution + coverage data*

---

## 1. Planning Process

### 1.1 Creating Detailed, Honest Planning — Revised Until Verified

- **MUST enter plan mode** for all non-trivial work
- Plan is revised **until all line references are verified against actual code** (not an arbitrary revision count — Round A needed 5 revisions)
- Every revision documents: what changed, why, and who reviewed it

### 1.2 Parallel vs Sequential Identification

- The plan MUST identify which items can execute in **parallel** (zero file overlap, independent modules) vs **sequential** (shared files, dependency chains)
- Use a **file overlap matrix** to justify parallelism decisions (proven in Round A: OPP-11 + OPP-05 parallelized safely, OPP-06/07 serialized due to shared `dynamic_autonomous.py`)
- Structure agent work so no agent is idle-waiting — when one agent is blocked on a dependency, it works on the next unblocked item

### 1.3 Agent Assignment

- The plan MUST specify **who works on what**: which agents/teammates handle which OPPs or tasks
- Assignment respects technical dependencies and maximizes parallel throughput
- Launch parallel agents — each focusing on a **different critical dimension** (architecture, TDD, security, integration)

### 1.4 External Model Review (Push-Back)

- Launch **Nano-agent Z.ai GLM-5** (`mcp__nano-agent__prompt_nano_agent` with `provider: "zai"`) to push back against planning
- Evaluate findings **independently with evidence**. Never blindly accept — discard false positives with documented reasoning
- If a provider produces invalid results for the project (e.g., codebase confusion), **document it in MEMORY.md** and switch providers
- Fallback: Qwen Cloud via nano-agent (`provider: "lmstudio"`, model: `qwen/qwen3-coder-next`) if primary unavailable

---

## 2. Requirements for Every Change Point

**Every point/change in the plan MUST satisfy ALL of the following:**

### 01 — Backed by Actual Code Tracing and Evidence

- Every claim includes **file path, line number, and code snippet**
- "We know what we will break and what we will wire" — trace callers, callees, and side effects
- No assumptions — if you haven't read the code, you don't know it

### 02 — Atomic: Leaves Codebase in a Working State

- After each atomic change: **all existing tests pass + no import errors + server starts via `python3 main.py`**
- Verify with: `python3 -m pytest tests/ --ignore=tests/standalone -x -q`
- If a change breaks something else, it's not atomic enough — split further

### 03 — Atomic: Testable in Real Life

- Each change must be testable at **two levels**:
  - **Unit tests** (mocks) — minimum for every change
  - **Integration tests** (live LM Studio) — **MANDATORY** for any change touching API surface methods (`chat_completion`, `create_response`, `anthropic_messages`, `list_models_enriched`)
- It is OK to have as many phases as it takes to achieve testable atomicity

### 04 — Problem/Intent Documented

- WHY this change exists — the problem being solved or feature being added
- Not "what files changed" but "what user/system problem this solves"

### 05 — Approach Documented

- Concept of the solution — the design decision and rationale
- List of files to be created/modified with expected line count changes
- Alternative approaches considered and why they were rejected

### 06 — Follow TDD: RED → GREEN → REFACTOR

| Phase | What Happens | Rule |
|-------|-------------|------|
| **RED** | Write failing test(s) first | Test MUST fail. If it passes, your test is wrong. |
| **GREEN** | Write ONLY enough production code to pass | No extras. No "while I'm here." |
| **REFACTOR** | Clean up code quality | All tests must stay green after every refactor step. |

- **Commit order**: RED test commit MUST precede GREEN implementation commit. Never reverse.
- **If code is written before a test**: DELETE IT. Start over. No exceptions.

### 07 — Happy Scenario, Negative Scenario, Edge Cases, and Boundary Cases

Every change covers:
- **Happy path**: Normal expected input/output
- **Negative path**: Invalid input, error conditions, exceptions
- **Edge cases**: Empty lists, null/None, zero values, single-element collections
- **Boundary cases**: Exactly at limits (e.g., `max_rounds` at exact cap, VRAM at exact budget)

### 08 — Top-to-Bottom Code Review

- Check the code top to bottom — zoom out, go wide, dig deep
- Specifically hunt for:
  - **Race conditions** (e.g., cache TTL checks without locks)
  - **Resource leaks** (unclosed connections, sessions, file handles)
  - **Error swallowing** (bare `except:`, silent failures)
  - **State mutation** (singletons modified across calls, shared mutable state)
- Ask: **"Are we solving symptoms, or ROOT problems in the architecture design/decision?"**

### 09 — No Hardcoding

- **NO hardcoded strings, variables, queries, URLs, timeouts, or magic numbers**
- All values go in `config/constants.py` with descriptive names and usage comments
- Use parameters for maximum reusability and flexibility
- Known violations to fix: `chat_completion()` hardcodes `"chat/completions"` instead of `CHAT_COMPLETIONS_ENDPOINT`; `DEFAULT_MAX_RETRIES` collision between `llm_client.py` (=2) and `constants.py` (=3)

### 10 — Test Coverage Requirements

| Metric | Minimum | Target |
|--------|---------|--------|
| **Overall coverage** | **80%** | **89%** |
| **New code coverage** | **90%** | **95%** |
| **Critical path coverage** | **95%** | **100%** |

- Measure with: `pytest --cov=llm --cov=tools --cov=config --cov=model_registry --cov=mcp_client --cov=utils --cov-report=term-missing`
- **Current baseline**: 67% overall (verified 2026-02-23)
- Coverage debt modules (below 50%):

  | Module | Current | Action |
  |--------|---------|--------|
  | `tools/dynamic_autonomous_register.py` | 0% | Add registration tests |
  | `tools/health.py` | 21% | Add health check tests |
  | `tools/completions.py` | 36% | Add completion MCP tool tests |
  | `model_registry/tools.py` | 37% | Add registry MCP tool tests |
  | `tools/lms_cli_tools.py` | 36% | Add CLI tool tests |
  | `model_registry/registry.py` | 42% | Add registry logic tests |
  | `tools/embeddings.py` | 42% | Add embedding tests |
  | `tools/vision.py` | 43% | Add vision tool tests |

- **Every PR must not decrease overall coverage.** New code must meet 90% minimum.

---

## 3. Git & Safety Protocol

### 3.1 Tag Before Starting

```bash
git tag <version>-pre-<round> -m "Checkpoint before <round> — <N> tests, <coverage>% coverage"
```

Create a safety tag so we can return to this point if anything goes wrong.

### 3.2 Rollback Strategy

- **If tests fail after a merge**: `git revert --no-commit HEAD` and investigate
- **If a worktree merge has conflicts**: `git merge --abort`, fix in worktree, re-attempt
- **Pre-merge dry-run is mandatory**: `git merge --no-commit --no-ff <branch> && git merge --abort` before every real merge
- **If rollback needed to tag**: `git reset --hard <tag>` (only after confirming with user)

### 3.3 Atomic Commit Instructions

Every atomic commit MUST:

| # | Requirement |
|---|-------------|
| 01 | Break changes into **granular, ultra-detailed** multiple atomic commits |
| 02 | Leave the codebase in a **working state** (all tests pass) |
| 03 | Document the **problem/intent**: why this change exists |
| 04 | Document the **approach**: concept of the solution (not list of file changes) |
| 05 | Follow **TDD commit order**: RED commit before GREEN commit |

**Commit message format**:
```
<type>(<scope>): <description>

<type> = feat|fix|test|refactor|style|docs|ci
<scope> = OPP-XX or module name
```

### 3.4 Version Bump Strategy

| Event | Version Action |
|-------|---------------|
| Round completed (multiple OPPs merged) | Minor bump (e.g., 3.3.0 → 3.4.0) |
| New API surface added | Minor bump |
| Breaking change to existing tool signatures | Major bump |
| Bug fix or minor improvement | Patch bump |
| Update `config/constants.py:VERSION` | In the same commit as the feature |

---

## 4. Review Gates

### 4.1 Before Implementation Starts

- [ ] Plan verified against actual code (all line references checked)
- [ ] External model review completed (GLM-5 via nano-agent)
- [ ] File overlap matrix computed for parallel work
- [ ] Git tag created at current state
- [ ] Coverage baseline recorded

### 4.2 After RED Phase (Tests Written)

- [ ] All new tests fail for the right reasons (not ImportError)
- [ ] Happy, negative, edge, and boundary cases all present
- [ ] Test file follows naming convention: `test_opp{N}_{description}.py`

### 4.3 After GREEN Phase (Implementation Done)

- [ ] All tests pass: `pytest -x -q`
- [ ] Coverage for new code >= 90%
- [ ] No hardcoded values introduced
- [ ] Integration tests pass against live LM Studio (for API surface changes)

### 4.4 After REFACTOR Phase

- [ ] All tests still pass
- [ ] No dead code introduced
- [ ] Constants extracted to `config/constants.py`
- [ ] Commit messages follow format

### 4.5 Before PR/Merge

- [ ] Overall coverage >= 80% (target 89%)
- [ ] Architecture guard tests pass: `pytest tests/test_architecture.py`
- [ ] README/docs updated with current test count and features
- [ ] VERSION bumped appropriately
- [ ] Plan documentation updated with actual outcomes

---

## 5. Integration Testing Requirements

### 5.1 When Integration Tests Are MANDATORY

Any change touching these methods requires a live LM Studio integration test:
- `chat_completion()` — `/v1/chat/completions`
- `create_response()` — `/v1/responses`
- `anthropic_messages()` — `/v1/messages`
- `list_models_enriched()` — `/api/v1/models`
- `_autonomous_loop()` — full autonomous execution
- `_execute_tools_parallel()` — parallel tool dispatch

### 5.2 Integration Test Structure

```python
@pytest.mark.integration
@pytest.mark.skipif(not is_lmstudio_running(), reason="LM Studio not available")
def test_<feature>_integration():
    """Integration test against live LM Studio."""
    ...
```

### 5.3 Integration Test Location

- `tests/standalone/test_integration_<feature>.py`
- Separate from unit tests — can be excluded from CI but MUST pass locally before PR

---

## 6. Plan Documentation Maintenance

- **Amend/update TODOs and plan documentation** after every phase completion
- Record: what was planned vs what actually happened vs deviations and why
- Plan is a **living document** — stale plans are worse than no plan

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| v1.0 | Pre-2026-02-23 | Original guidelines |
| v2.0 | 2026-02-23 | Fixed TDD terminology (RED/BLUE/GREEN → RED/GREEN/REFACTOR); Removed dashboard point (no dashboard in project); Added test coverage requirements (80% min / 89% target); Updated external review to GLM-5 via nano-agent; Added integration test requirements (MANDATORY); Added rollback strategy; Added review gates; Added version bump strategy; Added documentation update requirements; Added coverage debt table with baselines; Added commit ordering rule; Added boundary cases to testing requirements |
