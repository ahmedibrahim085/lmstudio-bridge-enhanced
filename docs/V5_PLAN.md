# v5.0.0 Comprehensive Implementation Plan

> **Version**: Final (Round 3+ Completeness) | **Date**: 2026-03-01 | **Status**: APPROVED
> **Baseline**: v4.0.0 | 1684 tests | 91% coverage | Branch: `main`
> **Research**: 4 parallel agents + 6 web searches + full codebase scan + OPP-31 synthesis (7 stages, 112 sources)
> **Reviews**: Round 1 (3 parallel architect reviews) → Round 2 (2 verification agents) → Round 3 (2 verification agents) → Round 3+ completeness fixes

---

## Review Round 1 Findings (Addressed in This Revision)

| # | Finding | Severity | Source | Fix |
|---|---------|----------|--------|-----|
| C-1 | No bridge release with DeprecationWarnings before v5.0 | CRITICAL | Review 1 | Added §Bridge Release Strategy |
| C-2 | Quality gates advisory, not CI-enforced | CRITICAL | Review 1 | Added §CI Enforcement |
| C-3 | No Golden Master tests for ARCH-1 | CRITICAL | Review 1 | Added to A-1 |
| C-4 | OPP-27: load_model already has context_length/flash_attention | CRITICAL | Review 2 | Fixed B-4 scope |
| C-5 | load_model line refs wrong (L137-193 vs actual L175-235/L405-507) | CRITICAL | Review 3 | Fixed all line refs |
| C-6 | A-4 scope incomplete — tools/ also imports from llm.exceptions | CRITICAL | Review 3 | Fixed A-4 affected files |
| C-7 | Req 07 missing: no test case categorization | CRITICAL | Review 2 | Added per-item |
| C-8 | Req 08 missing: no code review analysis | CRITICAL | Review 2 | Added per-item |
| I-1 | Long-lived branch vs trunk-based dev | IMPORTANT | Review 1 | Added §Development Strategy |
| I-2 | Cross-phase graph missing ARCH→Phase B edges | IMPORTANT | Review 1 | Expanded graph |
| I-3 | OPP-31 needs inline phasing summary | IMPORTANT | Review 1 | Added to B-6 |
| I-4 | Phase C breaking changes unclear | IMPORTANT | Review 1 | Clarified in C-1/C-2 |
| I-5 | No fallback plan for OPP-31 delay | IMPORTANT | Review 1 | Added to B-6 |
| I-6 | Agent assignment missing (Section 1.3) | IMPORTANT | Review 2 | Added §Agent Assignment |
| I-7 | No alternative approaches (Req 05) | IMPORTANT | Review 2 | Added per major item |
| I-8 | External model review missing (Section 1.4) | IMPORTANT | Review 2 | Added §External Review |
| I-9 | Phase B integration tests incomplete | IMPORTANT | Review 2 | Added MANDATORY markers |
| I-10 | Per-item review gates missing | IMPORTANT | Review 2 | Added to quality gates |
| M-1 | ARCH-3 code sample wrong field names | MINOR | Review 1 | Fixed |
| M-2 | Various line count off-by-2 errors | MINOR | Reviews 1,3 | Fixed all |
| M-3 | "172 constants" — actually 209 definitions | MINOR | Review 1 | Fixed |
| M-4 | Plan doesn't mention httpx transition | MINOR | Review 1 | Noted in A-1 |

---

## Executive Summary

v5.0.0 is a **major version** that combines architecture refactoring (ARCH-1..5) with new features (OPP-21,24,27,28,29,31) and breaking changes (OPP-19,25). The plan uses an **architecture-first** strategy: clean up the foundation before adding features, following the industry-standard "Facade-as-Seam" pattern ([refactoring.guru](https://refactoring.guru/design-patterns/facade), [God Class Guide](https://www.metridev.com/metrics/god-class-the-definitive-guide-to-identifying-and-avoiding-it/)).

**Key decisions:**
1. **Bridge release v4.1.0** ships first with DeprecationWarnings (per Django/Pydantic/SQLAlchemy patterns)
2. Architecture refactoring (Phase A) lands next — provides cleaner targets for feature work
3. Breaking changes (OPP-19, 21, 25) bundled in v5.0.0 — one migration for users
4. OPP-31 (Agent Slots) is the flagship feature — depends on OPP-08 (existing) + architecture cleanup
5. Trunk-based development: all phases merge to `main` behind feature flags, no long-lived branches

**Total scope**: 5 ARCH + 8 OPP = 13 work items across 16 commit groups, ~74 TDD commits, ~315-355 new tests, ~4350 new lines

---

## Bridge Release Strategy (v4.1.0)

**Rationale**: Industry standard (Django, Pydantic v1→v2, SQLAlchemy) requires shipping DeprecationWarnings in a minor release before removing APIs in the next major version. Users need time to migrate.

**v4.1.0 ships BEFORE v5.0.0 work begins**, containing:

| Deprecated API | Replacement (v5.0.0) | Warning |
|---------------|----------------------|---------|
| `thinking_budget: int` | `reasoning: {effort: str}` | `DeprecationWarning("thinking_budget is deprecated, use reasoning={'effort': 'medium'}")` |
| `from llm.exceptions import X` | `from core.exceptions import X` | No warning (re-export preserved indefinitely) |
| OpenAI-compat streaming format | Native SSE format | Runtime info log (not warning — both available in v5.0) |

**Implementation** (3 commits):
1. `test(v4.1): RED — tests for DeprecationWarning on thinking_budget`
2. `feat(v4.1): GREEN — add warnings.warn() in thinking_completion()`
3. `chore(v4.1): bump to v4.1.0, update CHANGELOG`

**Timeline**: Ship v4.1.0 → wait minimum 2 weeks → begin v5.0.0 Phase A

---

## Development Strategy

**Trunk-based development** with feature flags (per [Trunk Based Development](https://trunkbaseddevelopment.com/), Google/Meta engineering practices):

- All work merges to `main` in short-lived branches (`feat/arch-2`, `feat/opp-21`, etc.)
- Each branch lives ≤ 3 days before merge
- Feature flags for incomplete work: `FEATURE_NATIVE_CHAT=0` (env var, checked at import time)
- No long-lived `feat/v5.0.0` branch — avoids merge hell
- Safety tags before each phase: `v4.1.0-phase-a-pre`, `v4.1.0-phase-b-pre`

**Alternatives considered**:
- Long-lived feature branch: Rejected — merge conflicts compound with 13 items touching ~30 files
- Git flow: Rejected — overhead without CI/CD pipeline to justify it

---

## Agent Assignment (Section 1.3)

| Item | Agent Type | Model | Rationale |
|------|-----------|-------|-----------|
| A-2 (constants split) | executor | sonnet | Mechanical file splitting, low complexity |
| A-3 (metrics extract) | executor | sonnet | Simple extraction refactor |
| A-4 (exceptions move) | executor | sonnet | Re-export wiring, needs precision |
| A-5 (platform abstract) | executor | sonnet | Strategy pattern implementation |
| A-1 (LLMClient split) | executor-high | opus | Complex refactor, Facade pattern, high risk |
| OPP-21 (reasoning) | executor | sonnet | Parameter replacement, deprecation shim |
| OPP-28 (auth) | executor | sonnet | Header injection, low complexity |
| OPP-29 (logprobs) | executor | sonnet | Parameter passthrough |
| OPP-31 (agent slots) | executor-high | opus | Flagship feature, ~1365 lines, architecture |
| OPP-27 (adv load) | executor | sonnet | Parameter extension |
| OPP-24 (download) | executor | sonnet | REST client addition |
| OPP-19 (native chat) | executor-high | opus | New SSE parser, 19 event types |
| OPP-25 (ephemeral MCP) | executor | sonnet | Lifecycle management |

**Parallel batch assignment**: A-2, A-3, A-4, A-5 run simultaneously (4 agents).
**Parallel batch assignment**: OPP-21, OPP-28, OPP-29, OPP-31 run simultaneously (4 agents).

---

## External Review (Section 1.4)

Per planning guidelines, external model push-back via Nano-agent Z.ai GLM-5 should be requested:
- **When**: After Round 2 revision is approved
- **Focus**: Challenge architecture decisions (Facade vs full rewrite), OPP-31 scope, Phase C breaking changes
- **Evaluate independently**: Discard false positives with documented reasoning

---

## Phase A: Architecture Refactoring

### Rationale

Architecture review scored **62/100** ([docs/ARCHITECTURE_REVIEW.md](../docs/ARCHITECTURE_REVIEW.md)). The top 5 findings all relate to structural issues that make feature development harder. Fixing them first:
- Reduces merge conflicts in Phase B/C (features land on clean targets)
- Provides Protocol-based interfaces for OPP-31 (Agent Slots) to compose with
- Industry best practice: refactor before feature work ([Strangler Fig Pattern](https://martinfowler.com/bliki/StranglerFigApplication.html))

### A-2: Break `config/constants.py` into Domain Packages

**Problem**: 209 constant definitions in 853-line flat file. `__all__` has 205 entries (matching the 205 definitions). Finding anything requires scrolling through 16 different domains mixed together.

**Evidence**:
- `config/constants.py:1-853` — single file, 16 comment-separated sections
- Industry standard: domain-based splitting for >100 config values ([pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/))

**Approach**: Split into domain packages with backward-compatible re-export.

```
config/
  constants/
    __init__.py          # Re-exports everything: from .api import *; from .models import *; etc.
    api.py               # API endpoints, versions, URL patterns
    timeouts.py          # All timeout values
    models.py            # Model names, keywords, role mappings
    errors.py            # Error message templates
    limits.py            # Validation bounds, max values
    sampling.py          # Temperature, top_p, min_p, top_k defaults
    streaming.py         # SSE config, streaming constants
    thinking.py          # Reasoning/thinking config
    security.py          # SSRF, auth config
    server.py            # Host, port, server config
    testing.py           # Test infrastructure constants
    selection.py         # Smart selection weights, task mappings
    images.py            # Image processing constants
    mcp.py               # MCP discovery, connection config
    version.py           # VERSION string only
```

**Backward compat**: `from config.constants import X` still works — `__init__.py` re-exports all.

**Alternative approaches considered**:
- pydantic-settings with typed config classes: Rejected — over-engineering for constants, adds dependency
- Single file with better section headers: Rejected — 853 lines is beyond maintainable for a flat file
- Python dataclass per domain: Rejected — would break all `from config.constants import X` consumers

**Files modified**: `config/constants.py` → split into `config/constants/` (16 files)
**Files affected by imports**: NONE — re-export preserves all import paths
**Estimated lines**: ~853 redistributed + ~50 new `__init__.py` boilerplate
**Tests**: 10-12 tests | **New code coverage**: >= 90% (target 95%)
**Risk**: LOW — pure refactoring, zero behavioral change

**Test case categorization (Req 07)**:
- Happy: `from config.constants import VERSION` works, `from config.constants.api import CHAT_COMPLETIONS_ENDPOINT` works
- Negative: `from config.constants import NONEXISTENT` raises ImportError
- Edge: Empty domain file has empty `__all__`, `__init__.py` re-exports nothing extra
- Boundary: Every single one of 205 `__all__` entries still importable

**Code review notes (Req 08)**:
- No race conditions (constants are module-level, immutable)
- No resource leaks (no I/O)
- Risk: circular import if domain files import each other — enforce NO cross-domain imports

**TDD commits**:
1. `test(ARCH-2): RED — tests for domain-split constants re-export completeness`
2. `feat(ARCH-2): GREEN — split constants.py into domain packages`
3. `refactor(ARCH-2): clean up __all__ exports in new modules`

---

### A-3: Extract Metrics Helper from `_autonomous_loop`

**Problem**: Same 13-line `RoundMetrics` recording block duplicated 4 times at `tools/dynamic_autonomous.py:849,868,945,972`.

**Evidence**:
- `tools/dynamic_autonomous.py` = 1192 lines, `_autonomous_loop` = 250 lines (L760-1009)
- `RoundMetrics` imported from `tools/loop_metrics.py` (L51)
- 4x duplication of identical recording pattern with `round_metrics_list` append logic

**Approach**: Extract `_record_round_metrics()` helper method.

```python
def _record_round_metrics(
    self,
    round_metrics_list: list,
    completed_rounds: int,
    llm_call_duration: float,
    round_tool_calls: list,
    round_errors: int,
) -> None:
    """Record metrics for a single autonomous loop round."""
    rm = RoundMetrics(
        round_number=completed_rounds,
        llm_call_duration_seconds=llm_call_duration,
        tool_calls=round_tool_calls,
        error_count=round_errors,
    )
    if len(round_metrics_list) < 100:
        round_metrics_list.append(rm)
    else:
        round_metrics_list.pop(0)
        round_metrics_list.append(rm)
```

**Alternative approaches considered**:
- Decorator-based metrics: Rejected — the 4 call sites have different control flow (return vs continue vs pass)
- Context manager: Rejected — metrics recording is not a resource lifecycle pattern
- Keep as-is: Rejected — 4x duplication violates DRY, each block is wrapped in try/except

**Files modified**: `tools/dynamic_autonomous.py` (extract helper, replace 4 call sites at L849, L868, L945, L972)
**Estimated lines**: -33 (net reduction from deduplication)
**Tests**: 5-6 tests | **New code coverage**: >= 90% (target 95%)
**Risk**: LOW — behavioral equivalence, function extraction

**Test case categorization (Req 07)**:
- Happy: Helper records metrics with correct field values
- Negative: Exception in helper never propagates (matches existing `except Exception: pass`)
- Edge: Empty tool_calls list → `tool_calls=[]` recorded, zero errors → `error_count=0`
- Boundary: `round_metrics_list` at exactly 100 entries → oldest popped, new appended

**Code review notes (Req 08)**:
- No race conditions (single-threaded within `_autonomous_loop`)
- No resource leaks (pure data operation)
- Existing `except Exception: pass` pattern preserved — metrics must never break the loop

**TDD commits**:
1. `test(ARCH-3): RED — tests for extracted _record_round_metrics helper`
2. `feat(ARCH-3): GREEN — extract metrics helper, replace 4 duplication sites`
3. `refactor(ARCH-3): simplify _autonomous_loop after extraction`

---

### A-4: Fix Upward Dependency: utils -> llm (and tools -> llm.exceptions)

**Problem**: `utils/lms_helper.py:46` imports `from llm.exceptions import LLMError`. Utils should be leaf-level per the 5-pillar architecture. Additionally, `tools/` layer also imports from `llm.exceptions`, creating tight coupling.

**Evidence** (verified — all production files importing from `llm.exceptions` outside `llm/`):
- `utils/lms_helper.py:46` — `from llm.exceptions import LLMError`
- `utils/lms_helper.py:456,495,503` — lazy imports of `ModelMemoryError`
- `tools/dynamic_autonomous.py:41` — `from llm.exceptions import ModelNotFoundError`
- `tools/completions.py:32` — `from llm.exceptions import LLMResponseError`
- `llm/model_validator.py:25` — `from llm.exceptions import LLMConnectionError, ModelNotFoundError` (within `llm/`, OK)

**Approach**: Move shared exception hierarchy to `core/exceptions.py` — both `llm`, `utils`, and `tools` import from there.

```
core/
  __init__.py
  exceptions.py      # LLMError, LLMTimeoutError, etc. (~210 lines, moved from llm/exceptions.py)

llm/
  exceptions.py      # Re-exports from core.exceptions for backward compat

utils/
  lms_helper.py      # Now imports from core.exceptions (downward dependency)

tools/
  dynamic_autonomous.py  # Now imports from core.exceptions
  completions.py         # Now imports from core.exceptions
```

**Alternative approaches considered**:
- Keep in `llm/exceptions.py`, accept the coupling: Rejected — violates architecture layering
- Create `shared/exceptions.py`: Rejected — `core/` is more conventional for foundational types
- Move only `LLMError` base class: Rejected — half-measure, tools still need specific exceptions

**Files modified**:
- NEW: `core/__init__.py`, `core/exceptions.py`
- MODIFIED: `llm/exceptions.py` (re-export shim)
- MODIFIED: `utils/lms_helper.py:46` (change import source)
- MODIFIED: `tools/dynamic_autonomous.py:41` (change import source)
- MODIFIED: `tools/completions.py:32` (change import source)
**Estimated lines**: ~230 new (mostly moved), ~10 changed
**Tests**: 8-10 tests | **New code coverage**: >= 90% (target 95%)
**Risk**: LOW — re-export ensures zero breaking change

**Test case categorization (Req 07)**:
- Happy: `from core.exceptions import LLMError` works, `from llm.exceptions import LLMError` still works
- Negative: `from core.exceptions import NonExistent` raises ImportError
- Edge: Exception hierarchy preserved (`isinstance(LLMTimeoutError(), LLMError)` is True)
- Boundary: Every exception class in `llm/exceptions.py.__all__` still importable from both paths

**Code review notes (Req 08)**:
- No race conditions (module-level imports)
- Risk: circular import if `core.exceptions` imports from `llm` — verify NO reverse imports
- All test files that import `from llm.exceptions` continue working (re-export shim)

**TDD commits**:
1. `test(ARCH-4): RED — tests for core.exceptions import paths and hierarchy`
2. `feat(ARCH-4): GREEN — move exceptions to core/, add re-export shim`
3. `refactor(ARCH-4): update utils/ and tools/ imports to core.exceptions`

---

### A-5: Platform-Abstract MCP Process Spawning

**Problem**: `mcp_client/discovery.py:185-271` — 87 lines of macOS-only Homebrew Cellar path resolution.

**Evidence**:
- `mcp_client/discovery.py:185-271` — hardcoded Homebrew paths starting at L187-188
- `mcp_client/discovery.py:219` — npx-specific Homebrew resolution
- Architecture Review: "Will silently produce wrong results on Linux/Windows"

**Approach**: Replace with `shutil.which()` + platform strategy.

```python
import shutil
import platform

def _resolve_node_path() -> str | None:
    """Find node/npx executable using platform-appropriate resolution."""
    # Strategy 1: shutil.which (works on all platforms)
    npx_path = shutil.which("npx")
    if npx_path:
        return npx_path

    # Strategy 2: Platform-specific fallbacks
    if platform.system() == "Darwin":
        return _resolve_homebrew_node()  # existing 87-line logic, now isolated
    elif platform.system() == "Linux":
        return _resolve_linux_node()     # /usr/bin/node, snap, nvm
    return None  # Windows: rely on PATH
```

**Alternative approaches considered**:
- `nodeenv` package for hermetic Node.js: Rejected — adds dependency, overkill for finding npx
- Docker-based MCP execution: Rejected — not in scope, users expect local execution
- Keep macOS-only: Rejected — limits cross-platform adoption

**Files modified**: `mcp_client/discovery.py` (extract + wrap existing logic)
**Estimated lines**: ~20 new (wrapper + strategy dispatch), ~0 deleted (existing logic preserved)
**Tests**: 8-10 tests | **New code coverage**: >= 90% (target 95%)
**Risk**: LOW — existing macOS logic preserved, new platforms additive

**Test case categorization (Req 07)**:
- Happy: `shutil.which("npx")` returns path → used directly
- Negative: `shutil.which` returns None AND not macOS → returns None
- Edge: `shutil.which` returns empty string → treated as falsy, falls through
- Boundary: macOS with Homebrew but broken symlinks → falls through to None

**Code review notes (Req 08)**:
- No race conditions (`shutil.which` is stateless)
- No resource leaks (no file handles opened)
- Risk: TOCTOU on node path (exists at check time, gone at use time) — acceptable, pre-existing

**TDD commits**:
1. `test(ARCH-5): RED — tests for platform-abstract node resolution`
2. `feat(ARCH-5): GREEN — implement shutil.which + platform strategy`
3. `refactor(ARCH-5): move Homebrew-specific logic into _resolve_homebrew_node`

---

### A-1: Split `LLMClient` into Facade + Protocol (DEPENDS ON A-2..A-5)

**Problem**: `llm/llm_client.py` — 1587 lines, 31 methods, 5+ responsibilities. The "God Class" anti-pattern.

**Evidence**:
- `llm/llm_client.py:1-1587` — 31 `def` statements (30 class methods: 24 public + 6 private, plus 1 module-level helper `_handle_request_exception` at L64)
- Architecture Review: "5+ distinct responsibilities mixed in one class"
- `thinking_completion` at L1385 with `thinking_budget` at L1390

**Approach**: Extract responsibilities into Protocol-based modules. Keep `LLMClient` as thin Facade for backward compat. **Critical: Golden Master tests FIRST** (characterization tests that freeze current behavior before refactoring).

**Step 0 — Golden Master Tests** (before ANY code changes):

Capture exact current behavior of all 24 public methods via snapshot tests. These freeze the API contract:
```python
# tests/test_arch1_golden_master.py
class TestLLMClientGoldenMaster:
    """Characterization tests — capture current behavior before ARCH-1 refactor."""

    def test_chat_completion_signature(self): ...        # params + return type
    def test_chat_completion_payload_shape(self): ...    # exact JSON sent to LM Studio
    def test_text_completion_payload_shape(self): ...
    def test_create_response_payload_shape(self): ...
    def test_anthropic_messages_payload_shape(self): ...
    def test_stream_chat_yields_chunks(self): ...
    def test_thinking_completion_budget_mapping(self): ...
    def test_list_models_enriched_structure(self): ...
    # ... one per public method (24 total)
```

**Step 1 — Define Protocols** (`llm/protocols.py`):

```python
from typing import Protocol, Optional, Any, Generator

class ChatProvider(Protocol):
    def chat_completion(self, model: str, messages: list, **kwargs) -> dict: ...
    def text_completion(self, model: str, prompt: str, **kwargs) -> dict: ...

class ResponseProvider(Protocol):
    def create_response(self, model: str, input: Any, **kwargs) -> dict: ...

class AnthropicProvider(Protocol):
    def anthropic_messages(self, model: str, messages: list, **kwargs) -> dict: ...

class StreamProvider(Protocol):
    def stream_chat_completion(self, model: str, messages: list, **kwargs) -> Generator: ...
    def stream_create_response(self, model: str, input: Any, **kwargs) -> Generator: ...
    def stream_anthropic_messages(self, model: str, messages: list, **kwargs) -> Generator: ...

class ModelInfoProvider(Protocol):
    def list_models(self) -> list: ...
    def list_models_enriched(self) -> list: ...
    def get_model_info(self, model_key: str) -> Optional[dict]: ...

class ThinkingProvider(Protocol):
    def thinking_completion(self, model: str, messages: list, **kwargs) -> dict: ...
    def is_thinking_capable(self, model_name: str) -> bool: ...
```

**Step 2 — Extract Implementations** (new files):

```
llm/
  protocols.py           # Protocol definitions (~80 lines)
  http_transport.py      # Session management, _get_endpoint, health (~200 lines)
  chat_client.py         # chat_completion, text_completion (~250 lines)
  responses_client.py    # create_response, stateful API (~150 lines)
  anthropic_client.py    # anthropic_messages (~200 lines)
  streaming_client.py    # 3x stream_* methods (~250 lines)
  thinking_client.py     # thinking_completion, is_thinking_capable (~180 lines)
  model_info_client.py   # list_models, list_models_enriched, get_model_info (~150 lines)
  llm_client.py          # Thin Facade (~200 lines) — delegates to sub-clients
```

**Step 3 — Facade** (`llm/llm_client.py` becomes thin):

```python
class LLMClient:
    """Backward-compatible facade over extracted sub-clients."""

    def __init__(self, session=None):
        self._transport = HTTPTransport(session=session)
        self._chat = ChatClient(self._transport)
        self._responses = ResponsesClient(self._transport)
        self._anthropic = AnthropicClient(self._transport)
        self._streaming = StreamingClient(self._transport)
        self._thinking = ThinkingClient(self._transport)
        self._model_info = ModelInfoClient(self._transport)

    # Delegate all public methods
    def chat_completion(self, *args, **kwargs):
        return self._chat.chat_completion(*args, **kwargs)
    # ... etc for all 24 public methods
```

**Note on httpx**: Current transport uses `requests`. The transport extraction (Step 2) creates a clean seam for a future `requests → httpx` migration but does NOT include it in this scope. httpx migration would be a separate OPP.

**Alternative approaches considered**:
- Full rewrite (no Facade): Rejected — breaks every consumer, too risky for 31-method class
- Mixin-based decomposition: Rejected — mixins create implicit coupling, hard to test in isolation
- Strangler Fig (proxy + gradual migration): Rejected — Facade IS the simplified version of this
- Keep as-is, just add features: Rejected — 1587 lines is unmaintainable, every feature adds merge conflicts

**Why A-1 depends on A-2..A-5**:
- A-2 (constants split) means A-1 imports from clean domain packages
- A-3 (metrics helper) reduces dynamic_autonomous.py complexity before A-1 changes interface
- A-4 (exceptions) means A-1's sub-clients import from `core.exceptions` not `llm.exceptions`
- A-5 (platform abstraction) is independent but should land first to reduce merge surface

**Files modified**:
- NEW: 8 files (`protocols.py`, `http_transport.py`, `chat_client.py`, `responses_client.py`, `anthropic_client.py`, `streaming_client.py`, `thinking_client.py`, `model_info_client.py`)
- MODIFIED: `llm/llm_client.py` (from 1587 lines → ~200 line Facade)
- MODIFIED: `llm/__init__.py` (new exports)
**Estimated lines**: ~1460 extracted + ~200 facade = ~1660 total (net +73 for protocols/boilerplate)
**Tests**: 24 golden master + 25-30 new = ~50 total | **New code coverage**: >= 90% (target 95%)
**Risk**: MEDIUM — touches core module, but Golden Master + Facade preserves API surface
**Integration test MANDATORY**: `chat_completion`, `create_response`, `anthropic_messages`, `list_models_enriched` — all 4 API surface methods are re-wired through the Facade and MUST be validated against live LM Studio

**Test case categorization (Req 07)**:
- Happy: Each sub-client method produces same output as original LLMClient method
- Negative: Sub-client raises same exceptions as original for invalid inputs
- Edge: `LLMClient(session=None)` creates own transport (backward compat)
- Boundary: All 24 golden master tests pass unchanged after refactor

**Code review notes (Req 08)**:
- **Race condition risk**: `_transport` is shared — verify thread-safety of session reuse (pre-existing, not introduced)
- **Resource leak**: `close()` must propagate to all sub-clients → transport → session.close()
- **State mutation**: Sub-clients must not hold mutable state beyond transport reference
- **Error swallowing**: Facade must NOT catch/swallow exceptions from sub-clients — transparent delegation

**TDD commits**:
1. `test(ARCH-1): RED — 24 golden master characterization tests for LLMClient`
2. `test(ARCH-1): RED — protocol compliance tests for 6 sub-client contracts`
3. `feat(ARCH-1): GREEN — extract protocols and http_transport`
4. `feat(ARCH-1): GREEN — extract chat_client and responses_client`
5. `feat(ARCH-1): GREEN — extract anthropic_client and streaming_client`
6. `feat(ARCH-1): GREEN — extract thinking_client and model_info_client`
7. `feat(ARCH-1): GREEN — convert LLMClient to thin Facade`
8. `test(ARCH-1): verify all golden master + existing tests pass against Facade`
9. `refactor(ARCH-1): remove Feature Envy static methods (4 FormatAdapter delegates)`

---

### Phase A Execution Order

```
A-2 (constants) ═══╗
A-3 (metrics)   ═══╣  PARALLEL (zero file overlap — verified in matrix)
A-4 (exceptions)═══╣
A-5 (platform)  ═══╝
         │
         ▼
A-1 (LLMClient split) ────→ (sequential, depends on A-2..A-5)
```

### Phase A File Overlap Matrix

| File | A-1 | A-2 | A-3 | A-4 | A-5 |
|------|-----|-----|-----|-----|-----|
| `config/constants.py` | — | SPLIT | — | — | — |
| `config/constants/__init__.py` | — | NEW | — | — | — |
| `llm/llm_client.py` | REWRITE | — | — | — | — |
| `llm/protocols.py` | NEW | — | — | — | — |
| `llm/http_transport.py` | NEW | — | — | — | — |
| `llm/chat_client.py` | NEW | — | — | — | — |
| `llm/responses_client.py` | NEW | — | — | — | — |
| `llm/anthropic_client.py` | NEW | — | — | — | — |
| `llm/streaming_client.py` | NEW | — | — | — | — |
| `llm/thinking_client.py` | NEW | — | — | — | — |
| `llm/model_info_client.py` | NEW | — | — | — | — |
| `tools/dynamic_autonomous.py` | — | — | MODIFY | MODIFY (import) | — |
| `tools/completions.py` | — | — | — | MODIFY (import) | — |
| `core/__init__.py` | — | — | — | NEW | — |
| `core/exceptions.py` | — | — | — | NEW | — |
| `llm/exceptions.py` | — | — | — | SHIM | — |
| `utils/lms_helper.py` | — | — | — | MODIFY (import) | — |
| `mcp_client/discovery.py` | — | — | — | — | MODIFY |

**Note**: A-3 and A-4 both touch `tools/dynamic_autonomous.py` but in DIFFERENT ways (A-3: extract method body, A-4: change import line 41). These are safe to parallelize since they touch non-overlapping lines. However, if merge conflicts arise, A-4 (import change) should merge first as it's a 1-line change.

**Verdict**: A-2, A-3, A-4, A-5 have minimal overlap — safe for parallel execution with conflict resolution protocol.

### Phase A Quality Gate

**Per-item gates** (after each ARCH item's GREEN commit):
- [ ] `pytest tests/ --ignore=tests/standalone -x -q` — all pass
- [ ] `ruff check <modified_files>` — 0 errors
- [ ] `python3 main.py --help` — starts successfully

**Phase-level gates** (after all Phase A items):
- [ ] All existing 1684 tests pass unchanged
- [ ] Coverage >= 91% (no regression)
- [ ] Architecture score improves from 62/100 to >= 75/100
- [ ] `from config.constants import X` still works for all X (205 entries)
- [ ] `LLMClient` public API unchanged (24 golden master tests)
- [ ] Zero new import cycles (`python3 -c "import llm; import utils; import tools; import core"`)
- [ ] `python3 main.py` starts successfully

---

## Phase B: Medium-Lift Features

### B-1: OPP-21 — Native Reasoning Parameter (RICE: 64.8)

**Problem**: Current `thinking_budget` (OPP-14) uses a custom parameter. LM Studio 0.4+ supports native `reasoning: {effort: "low"|"medium"|"high"}` per the [LM Studio REST API](https://lmstudio.ai/docs/developer/rest).

**Evidence**:
- `llm/llm_client.py:1385` — `def thinking_completion(` with `thinking_budget` at L1390
- `llm/thinking_parser.py:1-160` — current custom thinking extraction
- LM Studio changelog: "Reasoning content moves out of `message.content`" (v0.3.23)

**Approach**: Replace `thinking_budget: int` with `reasoning: {effort: str}` parameter. Backward compat shim maps `thinking_budget` → `effort` with DeprecationWarning (already shipped in v4.1.0).

**Breaking change**: `thinking_budget` parameter removed in v5.0.0. v4.1.0 shim emits DeprecationWarning.

**Alternative approaches considered**:
- Keep `thinking_budget` as primary, add `reasoning` as alias: Rejected — LM Studio native API uses `reasoning`, keeping non-standard param as primary creates confusion
- Gradual migration (support both indefinitely): Rejected — dual-parameter maintenance burden, v4.1.0 DeprecationWarning already gives migration window

**Files modified**:
- `llm/thinking_client.py` (post-ARCH-1) — new reasoning parameter
- `config/constants/thinking.py` (post-ARCH-2) — reasoning effort constants
- `tools/completions.py` — expose in MCP tools
**Estimated lines**: ~80 new, ~40 removed
**Tests**: 12-14 tests (including **integration test MANDATORY** for thinking_completion) | **New code coverage**: >= 90% (target 95%)

**Test case categorization (Req 07)**:
- Happy: `reasoning={"effort": "medium"}` → correct payload, valid response
- Negative: `reasoning={"effort": "invalid"}` → ValueError, `reasoning={}` → ValueError
- Edge: `reasoning=None` → uses default effort, both `reasoning` and `thinking_budget` → error
- Boundary: `effort="low"` vs `effort="high"` → different token allocations

**Code review notes (Req 08)**:
- **Error swallowing**: Mapping from legacy `thinking_budget` to `effort` must log the mapping, not silently convert
- **State mutation**: Ensure `reasoning` dict is not mutated after validation — freeze or copy before sending
- **Backward compat**: v4.1.0 DeprecationWarning must fire exactly once per call, not once per import

**Depends on**: ARCH-1 (thinking_client extracted), OPP-14 DONE, v4.1.0 shipped

**TDD commits**:
1. `test(OPP-21): RED — tests for native reasoning parameter and effort levels`
2. `feat(OPP-21): GREEN — implement reasoning effort in thinking_client`
3. `refactor(OPP-21): remove thinking_budget, clean up deprecation shim`

---

### B-2: OPP-28 — API Authentication (RICE: 19.2)

**Problem**: No authentication support. LM Studio 0.4+ supports `Authorization: Bearer` tokens.

**Evidence**:
- LM Studio docs: "Require Authentication" toggle, per-token permissions
- `llm/llm_client.py:139` — `__init__` creates `requests.Session()` with no auth headers
- `llm/llm_client.py:161-163` — session headers set (Content-Type, Accept) but no Authorization

**Approach**: Add optional `api_key` parameter to transport.

**Alternative approaches considered**:
- Per-request auth header (not session-level): Rejected — adds overhead on every call, auth is typically session-scoped
- OAuth2/mTLS: Rejected — LM Studio only supports Bearer tokens, over-engineering When set, include `Authorization: Bearer {key}` header.

**Files modified**:
- `llm/http_transport.py` (post-ARCH-1) — add auth header to session
- `config/constants/security.py` (post-ARCH-2) — auth constants
- `config_main.py` — env var `LMS_API_KEY`
**Estimated lines**: ~50 new
**Tests**: 8-10 tests | **New code coverage**: >= 90% (target 95%)

**Test case categorization (Req 07)**:
- Happy: `api_key="sk-test"` → `Authorization: Bearer sk-test` in headers
- Negative: `api_key=""` → no header (empty key treated as absent), 401 response → LLMConnectionError
- Edge: `api_key` with trailing whitespace → stripped, `api_key` set in env var AND constructor → constructor wins
- Boundary: Very long API key (>1000 chars) → accepted (no length validation, LM Studio decides)

**Code review notes (Req 08)**:
- **Secret exposure**: API key must NEVER appear in logs, error messages, or exception tracebacks — mask in `__repr__`
- **Race condition**: If session headers are shared across threads, setting auth header must be thread-safe
- **Error handling**: 401 Unauthorized must raise specific `LLMAuthenticationError`, not generic `LLMConnectionError`

**Depends on**: ARCH-1 (transport extracted)

**TDD commits**:
1. `test(OPP-28): RED — tests for API authentication header injection`
2. `feat(OPP-28): GREEN — add api_key to HTTPTransport`
3. `refactor(OPP-28): extract auth config to security constants`

---

### B-3: OPP-29 — Log-Probabilities (RICE: 24)

**Problem**: No way to get token confidence scores. LM Studio supports `logprobs: true` and `top_logprobs: N` in chat completions.

**Evidence**:
- OpenAI API spec: `logprobs` and `top_logprobs` parameters
- LM Studio OpenAI-compat endpoints support these parameters

**Approach**: Add `logprobs: bool` and `top_logprobs: int` parameters to chat/response methods. Parse logprobs from response.

**Alternative approaches considered**:
- Separate `get_logprobs()` method: Rejected — logprobs are part of the completion response, not a separate endpoint
- Always return logprobs: Rejected — adds response size overhead, most users don't need them

**Files modified**:
- `llm/chat_client.py` (post-ARCH-1) — add logprobs params
- `llm/responses_client.py` — add logprobs params
- `config/constants/sampling.py` (post-ARCH-2) — logprobs constants
**Estimated lines**: ~60 new
**Tests**: 10-12 tests (including **integration test MANDATORY** for `chat_completion` with logprobs) | **New code coverage**: >= 90% (target 95%)

**Test case categorization (Req 07)**:
- Happy: `logprobs=True, top_logprobs=5` → present in payload and parsed from response
- Negative: `top_logprobs=-1` → ValueError, `top_logprobs=25` → ValueError (max 20 per OpenAI spec)
- Edge: `logprobs=True` without `top_logprobs` → defaults to 1, `logprobs=False` → param not in payload
- Boundary: `top_logprobs=0` → invalid (must be ≥1 when logprobs=True), `top_logprobs=20` → max valid

**Code review notes (Req 08)**:
- **Resource leak**: Logprobs parsing must not accumulate unbounded data — cap at `top_logprobs` entries per token
- **Error swallowing**: If LM Studio returns malformed logprobs (missing fields), log warning and return None, don't crash
- **State mutation**: Parsed logprobs should be returned as frozen dataclass or namedtuple, not mutable dict

**Depends on**: ARCH-1 (chat_client extracted)

**TDD commits**:
1. `test(OPP-29): RED — tests for logprobs parameter and response parsing`
2. `feat(OPP-29): GREEN — add logprobs to chat and response clients`
3. `refactor(OPP-29): extract logprobs parsing utility`

---

### B-4: OPP-27 — Advanced Model Load Parameters (RICE: 27)

**Problem**: `LMSRestClient.load_model()` (at `utils/lms_helper.py:175`) already accepts `context_length` and `flash_attention`, but LM Studio supports additional load params: `max_concurrent_predictions`, `ttl`, `draft_model`, `gpu_layers`.

**Evidence** (verified):
- `utils/lms_helper.py:175` — `def load_model(self, model_key: str, context_length=None, flash_attention=None):`
- `utils/lms_helper.py:405` — `LMSHelper.load_model(cls, model_name: str, keep_loaded: bool = True, ttl: Optional[int] = None)`
- LM Studio REST API: POST `/api/v1/models/load` accepts additional parameters beyond what we support
- OPP-30 (DONE): `echo_load_config` already returns actual config after load

**Scope correction** (from Review Round 2 finding C-4): The original plan incorrectly claimed `load_model()` "only accepts model_key and gpu_offload". The actual current signature already has `context_length` and `flash_attention`. There is no `gpu_offload` parameter. OPP-27 adds the REMAINING params only.

**Approach**: Extend `LMSRestClient.load_model()` to accept remaining LM Studio load params.

**New parameters to add**:
- `gpu_layers: Optional[int]` — number of layers to offload to GPU (0 = CPU only, -1 = all)
- `max_concurrent_predictions: Optional[int]` — parallel inference slots
- `ttl: Optional[int]` — seconds before auto-unload (0 = never)
- `draft_model: Optional[str]` — speculative decoding model key

**Alternative approaches considered**:
- `**load_kwargs` passthrough: Rejected — no validation, opaque API
- Typed dataclass `LoadConfig`: Considered for v6.0 — adds overhead now, good future refactor target

**Files modified**:
- `utils/lms_helper.py:175` — extend `LMSRestClient.load_model()` parameter list
- `config/constants/models.py` (post-ARCH-2) — load param validation constants
- `tools/lms_cli_tools.py` — expose new params in MCP tools
**Estimated lines**: ~80 new
**Tests**: 12-14 tests (including **integration test MANDATORY** for load_model) | **New code coverage**: >= 90% (target 95%)

**Test case categorization (Req 07)**:
- Happy: `gpu_layers=35, ttl=300` → present in payload, load succeeds
- Negative: `gpu_layers=-2` → ValueError, `max_concurrent_predictions=0` → ValueError
- Edge: All new params None → payload identical to current (backward compat)
- Boundary: `gpu_layers=-1` → valid (all layers), `gpu_layers=0` → valid (CPU only), `ttl=0` → valid (never unload)

**Code review notes (Req 08)**:
- `load_model` has check-before-load pattern — verify `draft_model` doesn't bypass this
- The `LMSHelper.load_model` at L405 is a CLASS METHOD (CLI-based) — NOT in scope here

**Depends on**: OPP-04 DONE, OPP-30 DONE

**TDD commits**:
1. `test(OPP-27): RED — tests for advanced load params (gpu_layers, ttl, draft_model, max_concurrent)`
2. `feat(OPP-27): GREEN — extend LMSRestClient.load_model with new params`
3. `refactor(OPP-27): consolidate load param validation`

---

### B-5: OPP-24 — Model Auto-Download via REST (RICE: 16.8)

**Problem**: Model download requires CLI. LM Studio 0.4+ has POST `/api/v1/download` REST endpoint.

**Evidence**:
- LM Studio REST API: `POST /api/v1/download`, `GET /api/v1/download-status`
- `utils/lms_helper.py:911` — existing `LMSHelper.download_model()` uses CLI subprocess
- `utils/lms_helper.py:550` — `list_downloaded_models()` for checking existing downloads

**Approach**: Add `download_model()` to `LMSRestClient`, expose as MCP tool. Keep CLI fallback.

**Alternative approaches considered**:
- Replace CLI download entirely: Rejected — CLI fallback needed when REST server is down (model not loaded = no REST)
- WebSocket-based progress tracking: Rejected — REST polling is simpler and matches LM Studio's API design

**Files modified**:
- `utils/lms_helper.py` — add `download_model()`, `get_download_status()`
- `tools/lms_cli_tools.py` — new MCP tool `download_model`
- `config/constants/api.py` — download endpoint constants
**Estimated lines**: ~120 new
**Tests**: 10-12 tests | **New code coverage**: >= 90% (target 95%)

**Test case categorization (Req 07)**:
- Happy: `download_model("org/model-name")` → 200 OK, progress polling works
- Negative: Invalid model key → 404, network error during download → LLMConnectionError
- Edge: Model already downloaded → `{"already_exists": true}`, empty model key → ValueError
- Boundary: Very long model key (HuggingFace paths can be long) → accepted

**Code review notes (Req 08)**:
- **Resource leak**: Download polling must have a timeout — infinite polling if LM Studio hangs
- **Error swallowing**: Partial download failures must be reported, not silently ignored
- **Race condition**: Concurrent download requests for same model — LM Studio may reject duplicates, handle 409 Conflict

**Depends on**: OPP-04 DONE, OPP-27 (shares `lms_helper.py` — SEQUENTIAL after OPP-27)

**TDD commits**:
1. `test(OPP-24): RED — tests for REST model download and status tracking`
2. `feat(OPP-24): GREEN — implement download_model and status tracking`
3. `refactor(OPP-24): add progress callback pattern for download monitoring`

---

### B-6: OPP-31 — Model Profiles / Agent Slots (RICE: 24.3)

**Problem**: No reusable model configuration, no dynamic resolution, no multi-agent support.

**Evidence**:
- Full spec at `docs/OPP-31-MODEL-PROFILES.md` (v3.0, 952 lines, 126+ research sources)
- `model_registry/selector.py:49` — existing `SmartModelSelector` class (OPP-08) that P2 resolver composes with
- `config/constants.py:659-684` — `TASK_CAPABILITY_MAP`, `SELECTION_WEIGHT_CAPABILITY`, `SELECTION_WEIGHT_CONFIDENCE`, `SELECTION_FALLBACK_SORT_KEY` used by SmartModelSelector
- `utils/lms_helper.py:175` — `LMSRestClient.load_model()` that slot manager calls for model lifecycle
- `llm/llm_client.py:139` — `LLMClient.__init__` that agent slots wrap for per-slot configuration

**Approach**: Agent-Slot Architecture per spec v3.0.

**Alternative approaches considered**:
- Simple profile dict (no resolver): Rejected — static profiles can't adapt to available models at runtime, misses the key OPP-08 integration
- Extend LLMClient directly with profile support: Rejected — violates ARCH-1 decomposition, adds more to the God Class
- Third-party config management (Hydra, OmegaConf): Rejected — adds dependency for what is a domain-specific feature, our YAML roles are simpler

**Phasing summary** (condensed from spec's 8 phases into 5 implementation phases):

| Plan Phase | Spec Phases Covered | Scope | Commits | Tests |
|------------|-------------------|-------|---------|-------|
| P1: Roles & Knowledge Base | Spec §1-2 | YAML role defs, vendor-optimal params | 6 | ~35 |
| P2: Dynamic Resolver | Spec §3-4 | Compose with OPP-08 SmartModelSelector | 4 | ~25 |
| P3: Agent Slot Manager | Spec §5-6 | Concurrent slot lifecycle | 6 | ~40 |
| P4: Context Overflow | Spec §7 | Client-side truncation/summarization | 4 | ~25 |
| P5: MCP Integration | Spec §8 | Tools for slot management | 2 | ~10 |

> **Note**: The full OPP-31 spec (`docs/OPP-31-MODEL-PROFILES.md`) has 8 detailed phases. This plan condenses them into 5 implementation phases for commit planning. See spec for granular phase breakdown.

**Files modified** (new module):
- NEW: `agent_slots/` package (7-8 new files)
  - `__init__.py` — public API
  - `roles.py` — YAML-based role definitions
  - `knowledge_base.py` — vendor-optimal params per family
  - `resolver.py` — DynamicResolver (composes with OPP-08 SmartModelSelector)
  - `manager.py` — AgentSlotManager for concurrent slots
  - `capabilities.py` — ProviderCapabilities tracking
  - `overflow.py` — Client-side context overflow enforcement
- MODIFIED: `tools/` — new MCP tools for agent slot management
- MODIFIED: `config/constants/` — agent slot constants
**Estimated lines**: ~1365 new
**Tests**: ~135 tests (per spec, including **integration test MANDATORY** for slot creation/resolution) | **New code coverage**: >= 90% (target 95%)
**Depends on**: OPP-04 DONE, OPP-22 DONE, OPP-26 DONE, OPP-08 DONE

**Test case categorization (Req 07)**:
- Happy: Create role from YAML → resolved to loaded model → slot active with correct params
- Negative: Invalid YAML schema → ValueError, model not found → ModelNotFoundError, slot creation with 0 context → ValueError
- Edge: Role with no system prompt → uses empty string, role referencing unloaded model → triggers auto-load, concurrent slot creation for same role → both succeed (independent instances)
- Boundary: Maximum concurrent slots (stress test with 10+ slots), context overflow at exactly context_length → truncation triggers, YAML with all optional fields omitted → defaults applied

**Code review notes (Req 08)**:
- **Race condition**: Concurrent slot creation/release — `AgentSlotManager` must use threading.Lock for slot registry
- **Resource leak**: Active slots hold model references — MUST release on exception and on explicit cleanup. Use `__del__` or context manager pattern
- **Error swallowing**: Failed model resolution must propagate, never fall back silently to a random model
- **State mutation**: Role definitions loaded from YAML must be frozen (immutable) after parse — prevent runtime modification

**Fallback plan**: If OPP-31 scope proves too large during implementation:
- **Minimum viable**: Ship P1 (roles) + P2 (resolver) + P5 (MCP tools) = ~70 tests, ~600 lines
- **Defer**: P3 (manager) and P4 (overflow) to v5.1.0
- **P5 ships with P1+P2**: P5 (MCP tools) exposes role/resolver APIs — does NOT depend on P3 (slot manager). If P3 is deferred, P5 exposes only `create_role`, `resolve_model`, `list_roles` tools (not `create_slot`, `release_slot`)

**TDD commits**: 22 commits per spec (see `docs/OPP-31-MODEL-PROFILES.md`)

---

### Phase B Execution Order

```
OPP-21 (reasoning) ═══╗
OPP-28 (auth)      ═══╣  PARALLEL (independent files — verified)
OPP-29 (logprobs)  ═══╣
OPP-31 (agent slots)══╝
         │
         ▼ (after parallel batch)
OPP-27 (adv load) → OPP-24 (download)  SEQUENTIAL (shared lms_helper.py + lms_cli_tools.py)
```

### Phase B File Overlap Matrix

| File | OPP-21 | OPP-28 | OPP-29 | OPP-31 | OPP-27 | OPP-24 |
|------|--------|--------|--------|--------|--------|--------|
| `llm/thinking_client.py` | MODIFY | — | — | — | — | — |
| `llm/http_transport.py` | — | MODIFY | — | — | — | — |
| `llm/chat_client.py` | — | — | MODIFY | — | — | — |
| `llm/responses_client.py` | — | — | MODIFY | — | — | — |
| `agent_slots/*` | — | — | — | NEW | — | — |
| `utils/lms_helper.py` | — | — | — | — | MODIFY (L175) | MODIFY (new method) |
| `tools/completions.py` | MODIFY | — | — | — | — | — |
| `tools/lms_cli_tools.py` | — | — | — | — | MODIFY | MODIFY |
| `config/constants/thinking.py` | MODIFY | — | — | — | — | — |
| `config/constants/security.py` | — | MODIFY | — | — | — | — |
| `config/constants/sampling.py` | — | — | MODIFY | — | — | — |
| `config/constants/models.py` | — | — | — | — | MODIFY | — |
| `config/constants/api.py` | — | — | — | — | — | MODIFY |

**Verdict**: OPP-21, 28, 29, 31 touch DIFFERENT files — safe for parallel. OPP-27 and OPP-24 share `lms_helper.py` and `lms_cli_tools.py` — must be sequential.

### Phase B Quality Gate

**Per-item gates** (after each OPP's GREEN commit):
- [ ] `pytest tests/ --ignore=tests/standalone -x -q` — all pass
- [ ] New code coverage >= 90%
- [ ] `ruff check <modified_files>` — 0 errors

**Phase-level gates**:
- [ ] All tests pass (existing + ~190 new)
- [ ] Coverage >= 91% (new code >= 90%)
- [ ] `thinking_budget` deprecation warning emits correctly (OPP-21)
- [ ] Authentication header present when `LMS_API_KEY` set (OPP-28)
- [ ] Logprobs returned when requested (OPP-29)
- [ ] Model download via REST works with progress tracking (OPP-24)
- [ ] OPP-31 agent slots work concurrently (**integration test MANDATORY**)
- [ ] load_model accepts new params without breaking existing usage (OPP-27, **integration test MANDATORY**)

---

## Phase C: Major Features (Breaking Changes)

### What Breaks and Why

Phase C introduces **two breaking changes** that require the v5.0.0 major version bump:

1. **OPP-19**: Default streaming format changes from OpenAI-compat SSE (3 event types) to LM Studio native SSE (19 event types). Existing `for chunk in stream: chunk["choices"][0]["delta"]["content"]` patterns break. **Mitigation**: `native=False` flag falls back to OpenAI-compat.

2. **OPP-25**: MCP server configuration restructures from static (discovered at startup) to dynamic (per-request `integrations` parameter). Existing static configs continue working; new parameter is additive. **Impact**: Lower than OPP-19 — mostly additive.

### C-1: OPP-19 — Native Chat API `/api/v1/chat` (RICE: 16)

**Problem**: Currently using OpenAI-compat `/v1/chat/completions` which lacks LM Studio-specific features: model load streaming, prompt processing events, context length control, integrations.

**Evidence**:
- [LM Studio REST API docs](https://lmstudio.ai/docs/developer/rest/endpoints): `/api/v1/chat` has 19 event types vs 3 in OpenAI-compat
- Current `llm/sse_parser.py:1-156` — parses OpenAI-compat SSE only

**Approach**: New native chat client + streaming parser. Keep OpenAI-compat as fallback.

**Alternative approaches considered**:
- Replace OpenAI-compat entirely: Rejected — breaks all existing users, no fallback for older LM Studio versions
- Adapter pattern (translate native events to OpenAI-compat shape): Rejected — loses information from 19→3 event type reduction, defeats the purpose

**Files modified**:
- NEW: `llm/native_chat_client.py` — native `/api/v1/chat` client
- NEW: `llm/native_sse_parser.py` — parser for 19 event types
- MODIFIED: `llm/http_transport.py` — native endpoint routing
- MODIFIED: `config/constants/api.py` — `NATIVE_CHAT_ENDPOINT = "/api/v1/chat"` and 19 event type constants
- MODIFIED: `llm/llm_client.py` (Facade) — new `native_chat()` method
**Estimated lines**: ~400 new
**Tests**: 20-25 tests (including **integration test MANDATORY** — 19 event types against live LM Studio) | **New code coverage**: >= 90% (target 95%)
**Depends on**: OPP-12 DONE, OPP-16 DONE, ARCH-1 (sub-client architecture)

**Test case categorization (Req 07)**:
- Happy: Standard chat → receives content events, stops cleanly
- Negative: Invalid model → error event, connection refused → LLMConnectionError
- Edge: Empty response (model generates nothing) → done event with no content events
- Boundary: All 19 event types parsed correctly, unknown event type → logged and skipped

**Code review notes (Req 08)**:
- **Resource leak**: Streaming response must be closed even on exception — use context manager
- **State mutation**: Parser must be stateless per-request (no carry-over between calls)
- **Error swallowing**: Error events from LM Studio MUST propagate, never silently consumed

**TDD commits**:
1. `test(OPP-19): RED — tests for native SSE event parser (19 event types)`
2. `feat(OPP-19): GREEN — implement native SSE parser`
3. `test(OPP-19): RED — tests for native chat client`
4. `feat(OPP-19): GREEN — implement native chat client with /api/v1/chat`
5. `refactor(OPP-19): integrate into Facade, add native=False fallback flag`

---

### C-2: OPP-25 — Ephemeral MCP Servers (RICE: 7.9)

**Problem**: MCP server configuration is static. LM Studio 0.4+ supports `integrations` parameter for per-request MCP server attachment.

**Evidence**:
- LM Studio REST API: `integrations` array in `/api/v1/chat` with `type`, `id`, `allowed_tools`
- `mcp_client/discovery.py:1-431` — current static discovery

**Approach**: Per-request MCP server attachment via the native chat API's `integrations` parameter.

**Alternative approaches considered**:
- Static registry with dynamic enable/disable: Rejected — still requires restart for new servers, doesn't match LM Studio's per-request `integrations` design
- Sidecar process per ephemeral server: Rejected — over-engineering, LM Studio manages server lifecycle internally

**Files modified**:
- NEW: `mcp_client/ephemeral.py` — ephemeral server lifecycle management
- MODIFIED: `mcp_client/discovery.py` — support dynamic server registration
- MODIFIED: `llm/native_chat_client.py` (from OPP-19) — pass integrations
- MODIFIED: `config/constants/mcp.py` — `INTEGRATION_TYPE_MCP = "mcp"` and ephemeral server constants
**Estimated lines**: ~250 new
**Tests**: 15-18 tests | **New code coverage**: >= 90% (target 95%)

**Test case categorization (Req 07)**:
- Happy: Ephemeral server attached, tools available in response, server cleaned up
- Negative: Invalid server config → ValueError, server crash mid-request → graceful error
- Edge: Empty `integrations` list → no servers attached, duplicate server IDs → last wins
- Boundary: Maximum number of ephemeral servers (stress test with 10+ servers)

**Code review notes (Req 08)**:
- **Resource leak**: Ephemeral servers MUST be cleaned up on request completion — use try/finally
- **Race condition**: Concurrent requests with same server ID — need per-request isolation
- **Error swallowing**: Failed cleanup must be logged, not swallowed

**Depends on**: OPP-16 DONE, OPP-19 (native chat API needed for integrations parameter)

**TDD commits**:
1. `test(OPP-25): RED — tests for ephemeral MCP server lifecycle`
2. `feat(OPP-25): GREEN — implement ephemeral server management`
3. `test(OPP-25): RED — tests for per-request integrations parameter`
4. `feat(OPP-25): GREEN — wire ephemeral servers into native chat client`
5. `refactor(OPP-25): cleanup static/dynamic server configuration`

---

### Phase C Execution Order

```
OPP-19 (native chat) → OPP-25 (ephemeral MCP)  SEQUENTIAL (dependency)
```

### Phase C Quality Gate

- [ ] All tests pass (existing + ~40 new)
- [ ] Coverage >= 91%
- [ ] Native chat streaming works with all 19 event types (**integration test MANDATORY**)
- [ ] Ephemeral MCP servers auto-cleanup on request completion
- [ ] OpenAI-compat fallback works when `native=False`
- [ ] Migration guide finalized for breaking changes

---

## Cross-Phase Dependency Graph (Expanded)

```
v4.1.0 (Bridge Release: DeprecationWarnings) ──────────────────────────
         │
         ▼
Phase A (Architecture) ─────────────────────────────────────────────────
  A-2 (constants split) ═══╗
  A-3 (metrics extract) ═══╣  PARALLEL
  A-4 (fix utils→llm)  ═══╣
  A-5 (platform abstract)══╝
           │
           ▼
  A-1 (LLMClient split) ──────────────────────────────────────────────
           │
           ├────────────────────────────────────────┐
           │                                        │
           ▼                                        ▼
Phase B (Features) ──────────────────     Phase B (Features) ─────────
  OPP-21 (reasoning) ═══╗                 OPP-27 (adv load)
    needs: thinking_client (A-1)            │
  OPP-28 (auth)      ═══╣                  ▼
    needs: http_transport (A-1)           OPP-24 (download)
  OPP-29 (logprobs)  ═══╣
    needs: chat_client (A-1)
  OPP-31 (agent slots)══╝
    needs: protocols (A-1),
           constants split (A-2)
           │
           ▼
Phase C (Major) ────────────────────────────────────────────────────────
  OPP-19 (native chat)
    needs: http_transport (A-1),
           streaming_client (A-1)
           │
           ▼
  OPP-25 (ephemeral MCP)
    needs: native_chat_client (OPP-19)
```

**Key cross-phase edges** (missed in Round 1):
- A-1 → OPP-21: thinking_client.py must exist before OPP-21 can modify it
- A-1 → OPP-28: http_transport.py must exist before OPP-28 can add auth
- A-1 → OPP-29: chat_client.py must exist before OPP-29 can add logprobs
- A-1 → OPP-19: streaming_client.py must exist before OPP-19 can add native SSE
- A-2 → OPP-31: constants/slots.py needs domain package structure

---

## CI Enforcement

**Current state**: `.github/workflows/tests.yml` runs pytest with `--reruns 2 --reruns-delay 5` but has NO coverage threshold, NO ruff, NO architecture guard tests.

**Required changes** (separate PR, before v5.0.0 work):

```yaml
# .github/workflows/tests.yml additions
- name: Run tests with coverage
  run: |
    pytest tests/ --ignore=tests/standalone --ignore=tests/integration \
      --cov=llm --cov=tools --cov=config --cov=utils --cov=model_registry \
      --cov=mcp_client --cov-report=term-missing --cov-fail-under=89 -x -q

- name: Lint
  run: ruff check llm/ utils/ tools/ config/ model_registry/ mcp_client/

- name: Architecture guard
  run: pytest tests/test_architecture.py -v

- name: Type check (informational)
  run: pyright llm/ utils/ tools/ config/ || true  # warn but don't block
  continue-on-error: true
```

**Gate enforcement**: Coverage floor at 89%. Ruff at 0 errors. Architecture guard mandatory.

---

## Commit Plan Summary

| Phase | Item | Commits | Tests | Lines |
|-------|------|---------|-------|-------|
| pre | v4.1.0 bridge release | 3 | 3-5 | ~30 |
| pre | CI enforcement PR | 1 | 0 | ~20 |
| A | ARCH-2 (constants) | 3 | 10-12 | ~50 new |
| A | ARCH-3 (metrics) | 3 | 5-6 | -33 net |
| A | ARCH-4 (exceptions) | 3 | 8-10 | ~230 |
| A | ARCH-5 (platform) | 3 | 8-10 | ~20 |
| A | ARCH-1 (LLMClient) | 9 | ~50 | ~1660 |
| B | OPP-21 (reasoning) | 3 | 12-14 | ~80 |
| B | OPP-28 (auth) | 3 | 8-10 | ~50 |
| B | OPP-29 (logprobs) | 3 | 10-12 | ~60 |
| B | OPP-31 (agent slots) | 22 | ~135 | ~1365 |
| B | OPP-27 (adv load) | 3 | 12-14 | ~80 |
| B | OPP-24 (download) | 3 | 10-12 | ~120 |
| C | OPP-19 (native chat) | 5 | 20-25 | ~400 |
| C | OPP-25 (ephemeral MCP) | 5 | 15-18 | ~250 |
| — | Version bump + docs | 2 | — | — |
| **TOTAL** | **16 items** | **~74** | **~310-340** | **~4350** |

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| ARCH-1 (LLMClient split) breaks existing tests | MEDIUM | HIGH | Golden Master tests freeze API. Facade preserves interface. Safety tag. |
| OPP-19 (native chat) API instability | LOW | HIGH | Keep OpenAI-compat fallback (`native=False`). Version-detect at startup. |
| OPP-31 (agent slots) scope creep | MEDIUM | MEDIUM | Strict spec v3.0 adherence. Fallback: ship P1+P2 only, defer P3+P4. |
| Coverage regression during ARCH-1 | MEDIUM | MEDIUM | CI gate at 89%. Run coverage after every commit. |
| LM Studio API changes between v0.4.x | LOW | MEDIUM | Abstract behind Protocol. API version detection. |
| Merge conflicts in parallel Phase B | LOW | LOW | File overlap matrix verified — zero overlap in parallel batch. |
| v4.1.0 DeprecationWarning breaks users | LOW | LOW | Warning only, no behavior change. Users have 2+ weeks to migrate. |
| Long review cycle delays Phase A start | MEDIUM | LOW | Trunk-based dev — start A-2..A-5 while A-1 plan finalizes. |

---

## Breaking Change Migration Guide (Draft)

### For v4.x Users Upgrading to v5.0.0

#### 1. `thinking_budget` → `reasoning.effort` (OPP-21)

```python
# v4.x (deprecated in v4.1.0 — DeprecationWarning emitted)
client.thinking_completion(model="...", thinking_budget=1024)

# v5.0.0 (thinking_budget REMOVED)
client.thinking_completion(model="...", reasoning={"effort": "medium"})
```

#### 2. Native streaming format (OPP-19)

```python
# v4.x — OpenAI-compat SSE (still available with native=False)
for chunk in stream:
    text = chunk["choices"][0]["delta"]["content"]

# v5.0.0 — Native SSE (default, richer events)
for event in stream:
    if event["type"] == "content":
        text = event["data"]["text"]
    elif event["type"] == "reasoning":
        thinking = event["data"]["reasoning_content"]
```

#### 3. Imports (NO breaking change)

```python
# Both work in v5.0.0 (re-export preserved)
from llm.exceptions import LLMError      # ← still works
from core.exceptions import LLMError     # ← new canonical path
```

#### 4. MCP server configuration (OPP-25)

```python
# v4.x — Static MCP config (still works in v5.0.0)
# Configured at server startup only

# v5.0.0 — Per-request MCP attachment (new, additive)
response = client.native_chat(
    model="...",
    input="...",
    integrations=[{"type": "mcp", "id": "my-server", "allowed_tools": ["tool1"]}]
)
```

---

## Pre-flight Checklist

- [ ] v4.1.0 bridge release shipped (DeprecationWarnings)
- [ ] CI enforcement PR merged (coverage gate, ruff, architecture guard)
- [ ] Safety tag: `git tag v4.1.0-v5-pre -m "Checkpoint before v5.0.0"`
- [ ] Coverage baseline recorded: 91% / ~1684 tests
- [ ] All existing tests green
- [ ] Architecture review baseline: 62/100
- [ ] External model review (GLM-5 push-back) completed

---

## Post-Merge Gate (v5.0.0 Release)

```bash
# Full regression
pytest tests/ --ignore=tests/standalone --ignore=tests/integration -x -q

# Coverage check (CI-enforced at 89% floor)
pytest --cov=llm --cov=tools --cov=config --cov=utils --cov=model_registry \
       --cov=mcp_client --cov=core --cov=agent_slots --cov-report=term-missing \
       --cov-fail-under=89 tests/ --ignore=tests/standalone -q

# Architecture score
# Target: >= 75/100 (from 62/100)

# Lint (CI-enforced)
ruff check llm/ utils/ tools/ config/ core/ agent_slots/ model_registry/ mcp_client/

# Architecture guard (CI-enforced)
pytest tests/test_architecture.py -v

# Server starts
python3 main.py --help

# Version
grep VERSION config/constants/version.py  # → "5.0.0"
```

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| Round 1 Draft | 2026-03-01 | Initial comprehensive plan from research |
| Round 2 Revision | 2026-03-01 | Fixed 8 critical + 10 important + 5 minor issues from 3-review audit. Added: bridge release strategy, CI enforcement, golden master tests, agent assignment, test categorization (Req 07), code review analysis (Req 08), alternative approaches (Req 05), expanded dependency graph, OPP-31 fallback plan, trunk-based dev strategy. Fixed: OPP-27 scope (load_model already has context_length/flash_attention), A-4 scope (tools/ imports too), ARCH-3 field names, all line references verified against code. |
| Round 3 Revision | 2026-03-01 | Fixed 10 remaining issues from Review Round 2: exec summary numbers (69→74 commits, 15→16 items), `__all__` count (272→205 in 3 locations), method count clarification (30 class + 1 module-level), RoundMetrics block size (11→13 lines), OPP-31 phase mapping table (5 plan phases → 8 spec phases), fallback plan P5 dependency fix (P5 ships with P1+P2, not P3), added Req 08 code review notes to OPP-21/28/29. |
| Round 3+ Completeness | 2026-03-01 | Fixed all Review Round 3 findings: Added Req 10 coverage targets (>= 90%) to all 13 items. Added Req 05 alternatives to OPP-21/28/29/24/19/25. Added Req 07 test categorization + Req 08 code review notes to OPP-31 and OPP-24. Added Req 03 integration MANDATORY to A-1 and OPP-29. Added Req 01 current-code line refs to OPP-28/24/31. Added Req 09 constants routing to OPP-19/25. Fixed exec summary test range (310-340 → 305-335). |
