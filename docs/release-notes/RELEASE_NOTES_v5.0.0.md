# Release Notes - v5.0.0

**Release Date**: March 2, 2026
**Version**: 5.0.0
**Previous Version**: 4.0.0
**Status**: **PRODUCTION READY**
**Commits**: 57 commits since v4.0.0

---

## Release Summary

This is a **major architecture + feature release** that restructures the codebase for long-term maintainability while adding 8 new OPPs and 5 architecture improvements. The monolithic LLMClient is split into a Facade + 7 sub-clients, constants are domain-organized, and the tool count grows from 22 to 37.

**Key Improvements**:
1. **Architecture Phase A** — Facade pattern, domain-split constants, metrics extraction, dependency fix, platform abstraction
2. **Features Phase B** — Agent profiles, reasoning effort, logprobs, API auth, model auto-download, advanced load params
3. **Features Phase C** — Native LM Studio chat API (19 SSE event types), ephemeral MCP servers
4. **4 API surfaces** — OpenAI-compat, Anthropic-compat, Responses, Native Chat
5. **37 MCP tools** — Up from 22 in v4.0.0

---

## What's New

### Phase A: Architecture Refactoring

| Step | Item | Description |
|------|------|-------------|
| A-1 | **ARCH-1: Facade Pattern** | Split `LLMClient` (1503 lines) into Facade + 7 Protocol-based sub-clients: `ChatClient`, `AnthropicClient`, `ResponsesClient`, `StreamingClient`, `ThinkingClient`, `ModelInfoClient`, `NativeChatClient` |
| A-2 | **ARCH-2: Constants Package** | Split `config/constants.py` (854 lines, 205 constants) into `config/constants/` package with 15 domain files. All existing imports preserved via `__init__.py` re-exports |
| A-3 | **ARCH-3: Metrics Extraction** | Extracted `_record_round_metrics()` helper — replaced 4 copy-pasted 15-line blocks in autonomous loop |
| A-4 | **ARCH-4: Dependency Fix** | Moved `exceptions.py` from `llm/` to `core/` — utils no longer imports from llm (leaf-level package) |
| A-5 | **ARCH-5: Platform Abstraction** | Platform-abstract `node`/`npx` resolution — removed 85 lines of macOS-only Homebrew paths |

### Phase B: Medium-Lift Features (Round E)

| OPP | Name | Description |
|-----|------|-------------|
| OPP-21 | **Reasoning Effort** | Native `reasoning_effort` parameter (low/medium/high) replaces deprecated `thinking_budget` |
| OPP-24 | **Model Auto-Download** | `lms_download_model` tool — download models via REST API with progress tracking |
| OPP-27 | **Advanced Load Params** | GPU offload layers, context length, keep-alive TTL, draft model, max concurrent config |
| OPP-28 | **API Authentication** | `api_key` parameter on all completion endpoints — enables shared LM Studio servers |
| OPP-29 | **Log-Probabilities** | `logprobs` and `top_logprobs` parameters — token confidence scores for quality gating |
| OPP-31 | **Agent Profiles** | User-defined agent slots with role templates, 6-family knowledge base, auto-tuned parameters. 5 MCP tools: `create_agent`, `list_agents`, `remove_agent`, `list_roles`, `create_role` |

### Phase C: Major Features (Round F)

| OPP | Name | Description |
|-----|------|-------------|
| OPP-19 | **Native Chat API** | `/api/v1/chat` endpoint with 19 SSE event types (model loading progress, reasoning deltas, tool calls, streaming). New `NativeChatClient` sub-client + `NativeSSEEvent` parser |
| OPP-25 | **Ephemeral MCP** | Spawn temporary MCP servers per-session with automatic lifecycle management |

---

## Tool Inventory (37 total)

### Core Completions & Health (11 tools)
`health_check`, `list_models`, `get_current_model`, `check_server_type`, `check_server_health`, `chat_completion`, `text_completion`, `create_response`, `validate_json_schema`, `anthropic_messages`, `generate_embeddings`

### Vision (6 tools)
`analyze_image`, `describe_image`, `compare_images`, `extract_text_from_image`, `identify_objects`, `answer_about_image`

### Dynamic Autonomous MCP (5 tools)
`autonomous_with_mcp`, `autonomous_with_multiple_mcps`, `autonomous_discover_and_execute`, `list_available_mcps`, `autonomous_with_images`

### Agent Profiles (5 tools) — NEW
`create_agent`, `list_agents`, `remove_agent`, `list_roles`, `create_role`

### Smart Model Selection (1 tool)
`select_best_model`

### LMS CLI (9 tools)
`lms_list_loaded_models`, `lms_list_downloaded_models`, `lms_load_model`, `lms_unload_model`, `lms_ensure_model_loaded`, `lms_search_models`, `lms_download_model`, `lms_resolve_model`, `lms_server_status`

---

## New Files

### Sub-clients (ARCH-1)
- `llm/chat_client.py` — ChatClient for `/v1/chat/completions`
- `llm/anthropic_client.py` — AnthropicClient for `/v1/messages`
- `llm/responses_client.py` — ResponsesClient for `/v1/responses`
- `llm/streaming_client.py` — StreamingClient for SSE
- `llm/thinking_client.py` — ThinkingClient for reasoning
- `llm/model_info_client.py` — ModelInfoClient for model discovery
- `llm/native_chat_client.py` — NativeChatClient for `/api/v1/chat`
- `llm/protocols.py` — Protocol contracts for all sub-clients
- `llm/jit_loader.py` — JIT model loading helper

### Native Chat (OPP-19)
- `llm/native_sse_parser.py` — 19 event type SSE parser

### Agent Profiles (OPP-31)
- `tools/profiles.py` — MCP tool registration (5 tools)
- `model_registry/profiles.py` — AgentSlotManager, DynamicResolver
- `model_registry/knowledge_base.py` — 6-family model knowledge base
- `model_registry/role_templates/` — YAML role template directory

### Constants Package (ARCH-2)
- `config/constants/__init__.py` + 15 domain files (version, server, api, timeouts, models, errors, limits, sampling, streaming, thinking, security, images, mcp, selection, testing)

### Dependency Fix (ARCH-4)
- `core/__init__.py`, `core/exceptions.py` — moved exceptions to leaf-level package

---

## Breaking Changes

### Deprecation: `thinking_budget` parameter
- **Old**: `thinking_budget=1024` (raw token count)
- **New**: `reasoning_effort="medium"` (semantic level: low/medium/high)
- **Migration**: `DeprecationWarning` emitted when `thinking_budget` is used; auto-maps to `reasoning_effort`
- **Removal**: `thinking_budget` parameter removed in this release after deprecation period

### Internal: Exception import paths
- **Old**: `from llm.exceptions import LLMError`
- **New**: `from core.exceptions import LLMError` (canonical) or `from llm.exceptions import LLMError` (shim, still works)

### Internal: Constants module structure
- **Old**: `config/constants.py` (single file)
- **New**: `config/constants/` (package with 15 domain files)
- **Migration**: No action needed — `from config.constants import X` still works via `__init__.py` re-exports

---

## Testing & Quality

### Test Suite Status

**Total**: ~1969 passed, 4 skipped, 0 failures
**Coverage**: 91%+

| Metric | v4.0.0 | v5.0.0 | Delta |
|--------|--------|--------|-------|
| Tests | ~1684 | ~1969 | +285 |
| Coverage | 91% | 91% | maintained |
| Tool count | 22 | 37 | +15 |
| Sub-clients | 0 | 7 | +7 |
| Constant domains | 1 file | 15 files | organized |

### TDD Discipline

All features implemented with strict RED → GREEN → REFACTOR:
- Every OPP has a `test(OPP-XX): RED` commit followed by `feat(OPP-XX): GREEN` commit
- Architecture changes verified with characterization tests before refactoring
- Two review rounds per phase with findings fixed

---

## Migration Guide

### From v4.0.0 to v5.0.0

```bash
cd /path/to/lmstudio-bridge-enhanced
git pull
git checkout v5.0.0

# Clear stale Python cache (important for constants package change)
find . -type d -name __pycache__ -exec rm -rf {} +

# Restart Claude Code to load updated MCP
```

**What you get automatically**:
- 15 new MCP tools (agent profiles, smart selection, model download, etc.)
- Native LM Studio chat with rich streaming events
- `reasoning_effort` parameter for thinking models
- `logprobs` for token confidence scoring
- `api_key` for shared server deployments
- Cleaner, more maintainable codebase (Facade pattern)

**Action required**:
- Replace `thinking_budget=N` with `reasoning_effort="low"|"medium"|"high"` (if used)
- Clear `__pycache__/` directories after upgrade

---

## Statistics

| Metric | Value |
|--------|-------|
| **Commits** | 57 |
| **Architecture Items** | 5 (ARCH-1 through ARCH-5) |
| **New OPPs** | 8 (OPP-19, 21, 24, 25, 27, 28, 29, 31) |
| **New Files** | ~35 |
| **Files Changed** | 124 |
| **Lines Added** | 11,960 |
| **Lines Removed** | 2,722 |
| **Net Change** | +9,238 lines |
| **New Tests** | ~285 |
| **Total Tests** | ~1,969 |
| **Coverage** | 91% |

---

## Commit Log

<details>
<summary>Click to expand full commit history (57 commits)</summary>

```
8110b46 chore: remove stale @xfail markers from 3 tests that now pass
4170ee9 fix(v5.0.0): modernize typing imports and update version assertion
255e25e chore(v5.0.0): bump version to 5.0.0, update ROADMAP and BACKLOG
5933f68 fix(review): address Phase C review findings C-1, H-2, M-2, guard
383ea51 refactor(OPP-25): cleanup static/dynamic server configuration
86512fe feat(OPP-25): GREEN — wire ephemeral servers into native chat client
20066ef test(OPP-25): RED — tests for per-request integrations parameter
86c2eaf feat(OPP-25): GREEN — implement ephemeral MCP server management
96896ad test(OPP-25): RED — tests for ephemeral MCP server lifecycle
091861a refactor(OPP-19): integrate native chat into Facade, add native=False fallback
fba718d feat(OPP-19): GREEN — implement native chat client with /api/v1/chat
59143c1 test(OPP-19): RED — tests for native chat client (/api/v1/chat)
7c5b6bd feat(OPP-19): GREEN — implement native SSE parser with 19 event types
4b1ee75 test(OPP-19): RED — tests for native SSE event parser (19 event types)
1d2a2c6 feat(OPP-24): GREEN — REST model download and status tracking
96d0f03 test(OPP-24): RED — tests for REST model download and status tracking
4d1e2a7 feat(OPP-27): GREEN — extend LMSRestClient.load_model with advanced params
1047c73 test(OPP-27): RED — tests for advanced load params
8bf8247 fix(review): address Phase B review findings M-2 and M-3
dbbb131 feat(OPP-31): GREEN — MCP profile tools for agent/role management (Phase 5)
796d37e test(OPP-31): RED — MCP profile tools for agent slot management (Phase 5)
7c15f06 feat(OPP-31): GREEN — AgentSlotManager with thread-safe slot lifecycle (Phase 4)
c4328e0 test(OPP-31): RED — AgentSlotManager concurrent slot lifecycle (Phase 4)
9e3e96a feat(OPP-31): GREEN — DynamicResolver with config layering (Phase 3)
4b7b2b7 test(OPP-31): RED — DynamicResolver and ResolvedConfig tests (Phase 3)
14f0488 feat(OPP-31): GREEN — model knowledge base with family detection (Phase 2)
a2f7667 test(OPP-31): RED — model knowledge base and family detection (Phase 2)
4cd20ce feat(OPP-31): GREEN — user-defined roles with YAML loader (Phase 1)
821e67a test(OPP-31): RED — RoleTemplate and RoleRegistry tests (Phase 1)
ef7cb11 feat(OPP-29): GREEN — add logprobs and top_logprobs to chat/response clients
474cf90 test(OPP-29): RED — tests for logprobs parameter and top_logprobs validation
b612c14 feat(OPP-28): GREEN — implement API authentication in HTTPTransport
df92c95 test(OPP-28): RED — tests for API authentication header injection
4b41da8 refactor(OPP-21): remove thinking_budget, clean up deprecation shim
dc596f5 feat(OPP-21): GREEN — implement reasoning effort in thinking_client
e72728e test(OPP-21): RED — tests for native reasoning parameter and effort levels
6fbe63b fix(review): update version refs to 4.1.0 in README and ARCH-2 test
d0585a1 fix(review): address Round 1 review findings for v4.1.0 pre-flight
499ac4d ci: add coverage gate, ruff lint, and architecture guard to CI
20e47e1 fix(v4.1): update setup.py version to match constants/version.py
3e452ab chore(v4.1): bump to v4.1.0
8cd09ea feat(v4.1): GREEN — add DeprecationWarning for thinking_budget
46f4823 test(v4.1): RED — tests for DeprecationWarning on thinking_budget
f9c5956 fix(review): H-1 extract JIT loader, H-2 wire protocols into Facade
ffb7c5f feat(ARCH-1): GREEN — split LLMClient into Facade + 6 sub-clients
aff7666 test(ARCH-1): RED — 33 golden master characterization tests for LLMClient
bc3ca6c feat(ARCH-5): GREEN — platform-abstract node/npx resolution
cddbf7e test(ARCH-5): RED — tests for platform-abstract node resolution
d0a7f02 feat(ARCH-4): GREEN — move exceptions to core/, shim llm/exceptions
1322f05 test(ARCH-4): RED — tests for core.exceptions import paths and hierarchy
e6ec442 feat(ARCH-3): GREEN — extract _record_round_metrics helper
8f299fe test(ARCH-3): RED — tests for extracted _record_round_metrics helper
77db687 fix(ARCH-2): update stale path in version consistency assertion message
2fe9583 refactor(ARCH-2): clean up __all__ exports and fix version consistency test
7fda864 feat(ARCH-2): GREEN — split constants.py into 15 domain packages
b95075d test(ARCH-2): RED — tests for domain-split constants re-export completeness
07d1fd8 chore: create branch and safety tag for ARCH-2
```

</details>

---

## Contributors

- **Ahmed Maged** - Primary Developer
- **Claude Code** - AI Collaboration Partner

---

**Release**: v5.0.0
**Date**: March 2, 2026
**Status**: **PRODUCTION READY**

**Full Changelog**: v4.0.0...v5.0.0
