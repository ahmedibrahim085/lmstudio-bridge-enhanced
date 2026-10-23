# OPP-31: Dynamic Model Profiles

> **Status**: PROPOSED | **Version**: 3.0 | **Date**: 2026-03-01
> **Research**: 7-stage parallel study + 4 model-family config studies, 126+ sources, cross-validated
> **Architecture**: Agent-slot architecture — user-defined roles, any model to any role, concurrent multi-agent workflows

---

## RICE Score

| Field | Value | Rationale |
|-------|-------|-----------|
| **Reach** | 9 | Every multi-model or multi-persona workflow benefits |
| **Impact** | 9 | Eliminates manual per-request param management; enables agent personas |
| **Confidence** | 0.9 | "Config object as profile" validated across 15/15 industry implementations |
| **Effort** | 3 | New module + knowledge base + resolver + MCP tools |
| **RICE** | **24.3** | `(9 × 9 × 0.9) / 3` |
| **Phase** | v5.0.0-B | |
| **Depends on** | OPP-22 DONE, OPP-04 DONE, OPP-26 DONE |
| **Backward compat** | Yes — purely additive |

---

## 1. Problem Statement

### What's Wrong

1. **No reusable configuration** — every request needs manual `model`, `temperature`, `max_tokens`, `system_prompt`
2. **No dynamic model resolution** — models come and go; hardcoded model IDs break
3. **No vendor-optimized defaults** — each family has different optimal params per task (DeepSeek coding=0.0, Qwen coding=0.2, Gemma coding=0.5) but callers can't know this
4. **No context overflow management** — `contextOverflowPolicy` inaccessible via REST (issue #532)
5. **No multi-agent support** — can't run Qwen as coder + DeepSeek as reviewer + Phi as tester simultaneously
6. **No flexibility** — roles, models, and assignments are all user decisions that the system shouldn't constrain

### Key Insight

**Nothing is hardcoded. Everything is a user decision.**

- Roles are user-defined (not a fixed set of 6)
- Any model can play any role (Qwen as tester, Phi as reviewer, DeepSeek as coder)
- Multiple agents run concurrently (each with its own model + role + config)
- The system provides **knowledge** (vendor-optimal params), not **restrictions**

### Who's Affected

- **MCP tool callers** (Claude Code) that need consistent personas
- **Multi-agent workflows** — coder writes → tester tests → reviewer reviews, all concurrent
- **Developers** who want flexible model-to-role assignments that adapt to installed models

---

## 2. Solution Overview

### Core Concept: Agent Slots

An **Agent Slot** is a runtime binding of:
```
Agent Slot = User-Defined Role + Assigned Model + Auto-Resolved Config
```

Nothing is hardcoded:
- Users **create** roles (or use provided examples)
- Users **assign** models to roles (or let the system pick the best available)
- The system **resolves** optimal params from the knowledge base
- Multiple slots run **concurrently** to form a workflow

### Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     AGENT SLOT MANAGER                        │
│                                                                │
│  Slot 1: "coder"    → Qwen2.5-Coder-7B    → temp=0.20       │
│  Slot 2: "tester"   → Phi-4               → temp=0.10       │
│  Slot 3: "reviewer" → DeepSeek-V3         → temp=0.30       │
│  Slot 4: "writer"   → Llama-3.3-70B       → temp=0.70       │
│                                                                │
│  All loaded simultaneously, each with own resolved config     │
│                                                                │
│  Workflow: Slot 1 output → Slot 2 input → Slot 3 input       │
└──────────────────────────────────────────────────────────────┘
```

### What OPP-31 Delivers

1. **User-defined roles** — create any role with any system prompt + params (examples provided, not mandated)
2. **Provider capabilities** — dynamic tracking of each model's specialties (vision, code, reasoning, tool_use)
3. **Model Knowledge Base** — vendor-researched optimal params per family × task type
4. **Dynamic Resolver** — auto-picks best model for a role OR accepts explicit user assignment
5. **Agent Slot Manager** — multiple concurrent agent slots, each independently configured
6. **Client-side context overflow** — `truncateMiddle` / `stopAtLimit` / `rollingWindow`
7. **MCP tools** — `create_agent`, `list_agents`, `assign_model`, `send_to_agent`, `create_workflow`

### Only 6 Parameters That Matter

Out of LM Studio's 41 parameters, only **6 drive meaningful behavioral differences**:

| Parameter | Why It Matters |
|-----------|---------------|
| `temperature` | Controls determinism vs creativity — the #1 differentiator |
| `top_p` | Nucleus sampling — model-family-specific (Qwen=0.8, Gemma=0.95) |
| `top_k` | Vocabulary breadth — family-specific (Qwen=20, Gemma=64, Phi=50) |
| `max_tokens` | Output length — task-specific (code=4096, docs=8192, chat=2048) |
| `system_prompt` | Behavioral identity — the role definition itself |
| `context_length` | Working memory — task-specific (reasoning=32K, chat=8K) |

---

## 3. User-Defined Roles

### Roles Are Templates, Not Constraints

A role is just a named config template. Users create any role they need:

```python
@dataclass(frozen=True)
class RoleTemplate:
    """A named behavioral template. Fully user-definable."""
    name: str                    # Any name the user chooses
    description: str             # Human-readable purpose
    system_prompt: str           # Behavioral instructions
    temperature: float = 0.7    # Default (overridden by knowledge base + user)
    max_tokens: int = 4096
    context_length: int = 16384
    context_overflow_policy: str = "truncateMiddle"
    preferred_capabilities: tuple[str, ...] = ()  # Hints for auto-resolution
```

### Example Roles (Provided as Starting Points)

These are shipped as YAML files in `roles/examples/`. Users can modify, delete, or add their own.

```yaml
# roles/examples/coder.yaml
name: coder
description: Code generation and debugging
system_prompt: |
  You are an expert software engineer. Write clean, correct code.
  Follow language idioms. Prefer minimal changes over rewrites.
temperature: 0.2
max_tokens: 4096
context_length: 32768
context_overflow_policy: truncateMiddle
preferred_capabilities: [code]

# roles/examples/tester.yaml
name: tester
description: Test generation and QA
system_prompt: |
  You are a senior QA engineer. Write comprehensive unit tests with
  arrange/act/assert. Cover happy path, edge cases, error conditions.
temperature: 0.3
max_tokens: 4096
context_length: 32768
preferred_capabilities: [code]

# roles/examples/reviewer.yaml
name: reviewer
description: Code review and analysis
system_prompt: |
  You are a senior architect conducting a code review. Analyze for
  correctness, security, performance. Use CRITICAL/HIGH/MEDIUM/LOW.
temperature: 0.2
max_tokens: 4096
context_length: 32768
preferred_capabilities: [code]

# roles/examples/writer.yaml
name: writer
description: Documentation and technical writing
system_prompt: |
  You are a technical writer. Clear, concise, well-structured docs.
  Markdown format. Audience: experienced developers.
temperature: 0.7
max_tokens: 8192
context_length: 16384
context_overflow_policy: rollingWindow
preferred_capabilities: [long_context]

# roles/examples/chat.yaml
name: chat
description: General conversation and assistance
system_prompt: |
  You are a helpful assistant. Be concise and accurate.
temperature: 0.7
max_tokens: 2048
context_length: 8192
context_overflow_policy: rollingWindow

# roles/examples/reasoning.yaml
name: reasoning
description: Complex analysis and step-by-step reasoning
system_prompt: |
  Reason step by step. Show your work clearly.
temperature: 0.6
max_tokens: 32768
context_length: 32768
context_overflow_policy: stopAtLimit
preferred_capabilities: [reasoning]
```

### Custom Roles — Create Anything

Users create roles for any purpose:

```yaml
# roles/security-auditor.yaml
name: security-auditor
description: OWASP vulnerability analysis
system_prompt: |
  Analyze code for OWASP Top 10 vulnerabilities, injection risks,
  auth flaws. Rate findings as CRITICAL/HIGH/MEDIUM/LOW with CVE refs.
temperature: 0.1
max_tokens: 8192
preferred_capabilities: [code]

# roles/translator.yaml
name: translator
description: Code-to-docs translator
system_prompt: |
  Read source code and produce comprehensive API documentation.
  Include parameter descriptions, return values, and usage examples.
temperature: 0.5
preferred_capabilities: [code, long_context]

# roles/image-describer.yaml
name: image-describer
description: Image analysis and description
system_prompt: |
  Describe images in detail. Focus on technical content, diagrams,
  and data visualizations. Be precise about text in images.
temperature: 0.3
preferred_capabilities: [vision]
```

### Role Storage

```
roles/
├── examples/           # Shipped with bridge (user can modify)
│   ├── coder.yaml
│   ├── tester.yaml
│   ├── reviewer.yaml
│   ├── writer.yaml
│   ├── chat.yaml
│   └── reasoning.yaml
├── security-auditor.yaml   # User-created
├── translator.yaml         # User-created
└── ...                     # Any number of custom roles
```

Configurable via `LMSTUDIO_ROLES_DIR` environment variable.

---

## 4. Provider Capabilities

### Every Model Has Specialties

Models aren't interchangeable. Each has capabilities the system should track:

| Capability | Models That Excel | Detection |
|-----------|------------------|-----------|
| `code` | Qwen2.5-Coder, Codestral, DeepSeek-Coder, StarCoder | Name pattern + OPP-08 |
| `reasoning` | DeepSeek-R1, Phi-4-reasoning, Qwen3 (thinking mode) | Name pattern + OPP-08 |
| `vision` | Qwen2-VL, GLM-4V, Gemma-3 (4B+), Llava, Phi-3.5-vision | Name pattern + API field |
| `tool_use` | Most instruct models (varies by quality) | API field (`tool_use: true`) |
| `long_context` | Qwen2.5 (128K), Gemma-3 (128K), DeepSeek (128K) | Model metadata |
| `multilingual` | Qwen, GLM, Mistral | Name pattern |
| `embedding` | nomic-embed, all-minilm, BGE | Model type field |

### Dynamic Capability Detection

Builds on OPP-08's existing `ModelMetadata.capabilities`:

```python
@dataclass(frozen=True)
class ProviderCapabilities:
    """What a specific model can do well."""
    code: float = 0.0           # 0.0-1.0 coding capability score
    reasoning: float = 0.0      # 0.0-1.0 reasoning score
    vision: bool = False        # Can process images?
    tool_use: bool = False      # Can call functions/tools?
    long_context: bool = False  # 64K+ context window?
    context_length: int = 4096  # Actual context window size
    family: str = "unknown"     # Detected model family
    specialties: tuple[str, ...] = ()  # Additional tags
```

### Capability Sources (Layered)

```
1. LM Studio API fields       — tool_use, vision (authoritative, confidence 1.0)
2. OPP-08 KNOWN_BENCHMARKS    — coding/reasoning scores (confidence 0.90-0.95)
3. Name-pattern inference      — "coder" in name → code=0.7 (confidence 0.70)
4. User overrides              — manual capability tagging
```

---

## 5. Model Knowledge Base

### Purpose

Each model family has vendor-specific optimal parameters that differ by task. The Knowledge Base stores **overlays** applied when a model family is resolved for a specific role.

### Family Detection

```python
def detect_family(model_key: str) -> str:
    """Detect model family from LM Studio model key."""
    key_lower = model_key.lower()
    families = [
        ("qwen", "qwen"), ("deepseek", "deepseek"), ("llama", "llama"),
        ("mistral", "mistral"), ("codestral", "mistral"), ("magistral", "mistral"),
        ("phi", "phi"), ("gemma", "gemma"), ("glm", "glm"),
        ("starcoder", "starcoder"), ("yi", "yi"),
    ]
    for pattern, family in families:
        if pattern in key_lower:
            # Sub-family detection for critical constraint models
            if family == "deepseek" and "r1" in key_lower:
                return "deepseek-r1"
            if family == "phi" and "reasoning" in key_lower:
                return "phi-reasoning"
            return family
    return "unknown"
```

**Key point**: `detect_family()` is extensible. When new model families appear (GLM-5, Yi-2, etc.), add a pattern here and an overlay dict below. No other code changes needed.

### Per-Family × Per-Task Overlays

Values marked `—` mean "use role template default, no override."

All values sourced from official vendor docs, HuggingFace model cards, and confirmed community practices. See [Appendix B](#appendix-b-research-artifacts) for citations.

#### Qwen Family
*Sources: Qwen2.5 blog, Qwen3 blog, HuggingFace cards, Ollama modelfiles*

| Task Type | temp | top_p | top_k | rep_penalty |
|-----------|------|-------|-------|-------------|
| code | 0.20 | 0.80 | 20 | 1.05 |
| test | 0.30 | 0.85 | 30 | 1.10 |
| write | 0.70 | 0.90 | 40 | 1.10 |
| review | 0.20 | 0.80 | 20 | 1.20 |
| chat | 0.70 | 0.80 | 20 | 1.05 |
| reason | 0.60 | 0.95 | 20 | 1.05 |

**Constraints**: Qwen3 thinking mode — NEVER greedy decode (temp=0 → repetition loops). Strip `<think>...</think>` from multi-turn history.

#### DeepSeek Family
*Sources: DeepSeek API docs, DeepSeek-R1 model card*

| Task Type | temp | top_p |
|-----------|------|-------|
| code | **0.0** | 0.95 |
| test | 0.3 | 0.95 |
| write | 1.0 | 0.95 |
| review | 0.3 | 0.95 |
| chat | **1.3** | 0.95 |
| reason | — | — |

**DeepSeek-R1 family (ALL tasks)**: temp=**0.6** MANDATORY (temp<0.5 → repetition loops). No system prompt — inject into user turn. Force `<think>\n` prefix.

#### Llama Family
*Sources: Llama-4-Scout card, Muxup reference, community*

| Task Type | temp | top_p | top_k |
|-----------|------|-------|-------|
| code | 0.2 | 0.7 | 10 |
| test | 0.3 | 0.8 | 20 |
| write | 0.7 | 0.9 | 40 |
| review | 0.2 | 0.8 | 20 |
| chat | 0.6 | 0.9 | — |
| reason | 0.6 | 0.9 | — |

#### Mistral Family
*Sources: Mistral-Small card, Codestral docs, Magistral card*

| Task Type | temp | top_p |
|-----------|------|-------|
| code | 0.2 | — |
| test | 0.2 | 0.9 |
| write | 0.7 | 0.9 |
| review | 0.2 | 0.9 |
| chat | **0.15** | — |
| reason | **0.7** | 0.95 |

#### Phi Family
*Sources: Phi-4 report, Phi-4-reasoning card*

| Task Type | temp | top_p | top_k |
|-----------|------|-------|-------|
| code | 0.0 | 0.95 | 50 |
| test | 0.1 | 0.95 | 50 |
| write | 0.7 | 0.95 | 50 |
| review | 0.2 | 0.95 | 50 |
| chat | 0.7 | 0.95 | 50 |
| reason | — | — | — |

**Phi-4-reasoning family (ALL tasks)**: temp=**0.8**, top_k=50, top_p=0.95 — MANDATORY per Microsoft.

#### Gemma Family
*Sources: Gemma-3 HF discussions #25, #84; Google Gemma docs*

| Task Type | temp | top_p | top_k |
|-----------|------|-------|-------|
| code | **0.5** | 0.95 | 64 |
| test | 0.4 | 0.95 | 64 |
| write | **1.0** | 0.95 | 64 |
| review | 0.4 | 0.95 | 64 |
| chat | **1.0** | 0.95 | 64 |
| reason | 0.8 | 0.95 | 64 |

**Constraints**: No native system role — inject into first user turn. NEVER top_k=1. Avoid QAT variants (gibberish bug). Use repetition_penalty=1.1 with vLLM.

#### Unknown Family Fallback

When family can't be detected, use role template defaults with no overlay. Safe because role templates have moderate values that work across families.

### Task Type Mapping

Roles map to knowledge base task types through `preferred_capabilities`:

| Role's preferred_capabilities | Knowledge Base Task Type |
|------------------------------|------------------------|
| Contains `"code"` | `code` (for coder), `test` (for tester), `review` (for reviewer) |
| Contains `"reasoning"` | `reason` |
| Contains `"long_context"` | `write` |
| Default / empty | `chat` |

This mapping is flexible — a custom role with `preferred_capabilities: [code]` automatically gets code-optimized params from the knowledge base.

### Adding New Families

When a new model family appears:

1. Add pattern to `detect_family()` (one line)
2. Add overlay dict to `MODEL_KNOWLEDGE` (one dict)
3. Add critical constraints if any (optional)
4. Write tests

No other code changes. The resolver, roles, and MCP tools all adapt automatically.

---

## 6. Dynamic Resolver

### Builds on OPP-08 SmartModelSelector

OPP-31's resolver **composes with** OPP-08's existing `SmartModelSelector`:

```
OPP-08: task_type → best model_id (capability scoring)
OPP-31: role + optional model → ResolvedConfig (model + params + constraints)
        ├── Uses SmartModelSelector when user doesn't specify a model
        ├── Adds knowledge base overlay for family-specific params
        └── Enforces critical constraints (mandatory temps, etc.)
```

### Two Modes of Resolution

**Auto-resolve** (user specifies role only):
```
use_role("coder")
  → SmartModelSelector picks best loaded model with code capability
  → Knowledge base applies family-specific overlay
  → ResolvedConfig returned
```

**Explicit assignment** (user specifies role + model):
```
use_role("tester", model="phi-4")
  → Phi-4 used directly (no scoring needed)
  → Knowledge base applies Phi family overlay for "test" task type
  → ResolvedConfig returned
```

### Config Layering

```
Priority (highest wins):
  1. Critical constraints  — mandatory model-specific (R1 temp>=0.5, Phi-reasoning temp=0.8)
  2. User overrides        — explicit per-request params
  3. Family overlay        — knowledge base per-family per-task
  4. Role template         — user-defined role params
  5. Global defaults       — constants.py fallbacks
```

Critical constraints ALWAYS win — even over user overrides. If a user requests temp=0.0 for DeepSeek-R1, the resolver enforces temp=0.6 and logs a warning.

### Resolved Config (Output)

```python
@dataclass(frozen=True)
class ResolvedConfig:
    """Fully resolved, immutable configuration — ready for LM Studio API."""

    # Assignment
    slot_name: str              # User-chosen name for this agent slot
    role_name: str              # Which role template was used
    model_key: str              # Which model was assigned

    # Resolved parameters
    system_prompt: str
    temperature: float
    max_tokens: int
    top_p: float
    top_k: int | None
    min_p: float | None
    context_length: int
    context_overflow_policy: str
    repetition_penalty: float | None

    # Model-specific flags (from knowledge base)
    supports_system_role: bool      # False for Gemma, DeepSeek-R1
    force_thinking_prefix: bool     # True for DeepSeek-R1
    strip_thinking_tags: bool       # True for Qwen3 thinking mode

    # Metadata
    family: str
    capabilities: ProviderCapabilities
```

---

## 7. Agent Slot Manager

### Multiple Concurrent Agents

The slot manager holds multiple active agent slots simultaneously:

```python
class AgentSlotManager:
    """Manages multiple concurrent agent slots."""

    def __init__(self, role_registry, knowledge_base, resolver):
        self._slots: dict[str, ResolvedConfig] = {}  # name → config
        self._resolver = resolver

    def create_slot(
        self,
        name: str,
        role: str,
        model: str | None = None,
        overrides: dict | None = None,
    ) -> ResolvedConfig:
        """Create a new agent slot.

        Args:
            name: Unique slot name (e.g., "my-coder", "pr-reviewer")
            role: Role template name (e.g., "coder", "security-auditor")
            model: Optional explicit model. None = auto-resolve best available.
            overrides: Optional param overrides (temperature, max_tokens, etc.)
        """

    def remove_slot(self, name: str) -> None:
        """Remove an agent slot. Does NOT unload the model."""

    def get_slot(self, name: str) -> ResolvedConfig:
        """Get a slot's resolved config."""

    def list_slots(self) -> list[dict]:
        """List all active slots with their configs."""

    def send(self, slot_name: str, messages: list[dict]) -> dict:
        """Send messages to a specific agent slot.

        Applies the slot's resolved config (system prompt, overflow,
        params) and forwards to LM Studio.
        """
```

### Example: Multi-Agent Workflow

```python
# User creates a 3-agent workflow
manager.create_slot("my-coder", role="coder", model="qwen2.5-coder-7b")
manager.create_slot("my-tester", role="tester", model="phi-4")
manager.create_slot("my-reviewer", role="reviewer", model="deepseek-v3")

# Each slot has independently resolved config:
#   my-coder:    Qwen coder overlay → temp=0.20, top_p=0.80, top_k=20
#   my-tester:   Phi test overlay → temp=0.10, top_p=0.95, top_k=50
#   my-reviewer: DeepSeek review overlay → temp=0.30, top_p=0.95

# Send work to each agent
code = manager.send("my-coder", [{"role": "user", "content": "Write a parser"}])
tests = manager.send("my-tester", [{"role": "user", "content": f"Test this:\n{code}"}])
review = manager.send("my-reviewer", [{"role": "user", "content": f"Review:\n{code}"}])
```

### Workflow Chains (Optional)

For common patterns, users can define workflow chains:

```yaml
# workflows/code-review.yaml
name: code-review
description: Write code, test it, review it
steps:
  - slot: coder
    role: coder
    # model: auto-resolved
  - slot: tester
    role: tester
    input_from: coder   # Output of coder feeds into tester
  - slot: reviewer
    role: reviewer
    input_from: coder   # Output of coder feeds into reviewer
```

---

## 8. Client-Side Context Overflow (Tier 2)

### Why Client-Side?

LM Studio's `contextOverflowPolicy` is inaccessible via REST API (S1, issue #532).

### Three Policies

**`truncateMiddle`** (default):
- System prompt preserved at position 0, last N messages preserved
- Middle messages removed. Evidence: U-shaped attention — 27pp accuracy drop at middle (Liu et al. TACL 2024)

**`stopAtLimit`** (for reasoning/agentic):
- Reject when messages exceed limit. Prevents silent loss of reasoning chains.

**`rollingWindow`** (for chat):
- FIFO eviction of oldest messages, system prompt always pinned.

### Token Counting

| Aspect | Approach |
|--------|----------|
| Library | `tiktoken` (`cl100k_base` encoding) |
| Accuracy | ±10% vs actual model tokenizer |
| Fallback | `len(text) / 4` heuristic |

---

## 9. System Prompt Protection

### Model-Specific Handling

| Family | System Role? | Handling |
|--------|-------------|----------|
| Qwen | Yes | Standard system message |
| DeepSeek (V3/Coder) | Yes | Standard system message |
| DeepSeek-R1 | **No** | Prepend to first user turn |
| Llama | Yes | Standard system message |
| Mistral | Yes | Standard system message |
| Phi | Yes | Standard system message |
| Gemma | **No** | Inject into first user turn |
| GLM | Yes | Standard system message |

Handled automatically via `ResolvedConfig.supports_system_role`.

### Injection Sanitization

Strip structural tokens (`<|im_start|>`, `[INST]`, `<start_of_turn>`, etc.) from user input to prevent ChatBug-style injection attacks (32-52% ASR).

---

## 10. MCP Tool Integration

### New MCP Tools

```python
@server.tool()
async def create_agent(
    name: str,
    role: str,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> str:
    """Create a named agent slot with a role and optional model assignment.

    If model is not specified, auto-resolves the best available model
    for the role's preferred capabilities.

    Examples:
        create_agent("my-coder", "coder")
        create_agent("my-coder", "coder", model="qwen2.5-coder-7b")
        create_agent("sec-check", "security-auditor", temperature=0.05)
    """

@server.tool()
async def list_agents() -> str:
    """List all active agent slots with their models and configs."""

@server.tool()
async def remove_agent(name: str) -> str:
    """Remove an agent slot. Does not unload the model from LM Studio."""

@server.tool()
async def send_to_agent(name: str, message: str) -> str:
    """Send a message to a specific agent and get the response.

    The agent's role config (system prompt, temperature, etc.) is
    applied automatically.
    """

@server.tool()
async def list_roles() -> str:
    """List all available role templates (built-in + custom)."""

@server.tool()
async def create_role(
    name: str,
    description: str,
    system_prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    preferred_capabilities: list[str] | None = None,
) -> str:
    """Create a new role template at runtime. Saved to roles/ as YAML."""

@server.tool()
async def list_models() -> str:
    """List models in LM Studio with detected families and capabilities."""
```

### Integration with Existing Tools

Existing completion tools gain an optional `agent` parameter:

```python
async def chat_completion(
    prompt: str,
    model: str | None = None,       # Explicit model (existing)
    agent: str | None = None,        # NEW: agent slot name
    ...
) -> str:
```

**Priority**: explicit params > agent slot config > tool defaults

---

## 11. File Impact Matrix

Builds on existing `model_registry/` (OPP-08) infrastructure.

| File | Change Type | Lines (est.) | Description |
|------|------------|-------------|-------------|
| `config/constants.py` | MODIFY | +40 | Role/agent constants, overflow policy names |
| `config/roles.py` | **NEW** | ~100 | `RoleTemplate` dataclass, `RoleRegistry` (YAML loader) |
| `config/model_knowledge.py` | **NEW** | ~220 | Per-family × per-task overlays, critical constraints, `detect_family()` |
| `config/resolver.py` | **NEW** | ~150 | `DynamicResolver` (composes with OPP-08 `SmartModelSelector`) |
| `config/resolved_config.py` | **NEW** | ~60 | `ResolvedConfig` frozen dataclass |
| `config/agent_slots.py` | **NEW** | ~180 | `AgentSlotManager` — concurrent slot management |
| `config/overflow.py` | **NEW** | ~150 | Client-side overflow policies |
| `config/template_detection.py` | **NEW** | ~80 | Template detection, injection sanitization |
| `tools/profiles.py` | **NEW** | ~160 | 7 MCP tools (create/list/remove agent, send, list/create roles, list models) |
| `tools/completions.py` | MODIFY | +15 | Add optional `agent` param |
| `model_registry/selector.py` | MODIFY | +10 | Expose task_type→capability for OPP-31 |
| `llm/llm_client.py` | MODIFY | +20 | Accept resolved config params |
| `utils/token_counter.py` | **NEW** | ~60 | tiktoken wrapper |
| `roles/examples/*.yaml` | **NEW** | ~120 | 6 example role templates |
| **Total** | | **~1365** | 9 new files + 3 modifications + 6 YAML templates |

### Reuse from OPP-08

| OPP-08 Component | OPP-31 Usage |
|-------------------|-------------|
| `SmartModelSelector.select()` | Called by resolver for auto-resolution |
| `TASK_CAPABILITY_MAP` | Role capability → task type mapping |
| `ModelMetadata.capabilities` | Input to `ProviderCapabilities` |
| `_infer_coding_capability()` | Reused for name-pattern capability detection |
| `KNOWN_BENCHMARKS` | Tiebreaking when multiple models match |

---

## 12. Test Plan

| File | Tests | Focus |
|------|-------|-------|
| `tests/test_opp31_roles.py` | ~12 | RoleTemplate, custom role loading, YAML parsing |
| `tests/test_opp31_capabilities.py` | ~10 | ProviderCapabilities, capability detection |
| `tests/test_opp31_knowledge.py` | ~20 | Per-family overlays, critical constraints, family detection |
| `tests/test_opp31_resolver.py` | ~22 | Auto-resolve, explicit assignment, layering, constraint enforcement |
| `tests/test_opp31_agent_slots.py` | ~18 | Create/remove/list slots, concurrent slots, send_to_agent |
| `tests/test_opp31_overflow.py` | ~18 | All 3 overflow policies, system prompt preservation |
| `tests/test_opp31_template.py` | ~12 | Template detection, injection sanitization |
| `tests/test_opp31_token_counter.py` | ~8 | Token counting, fallback |
| `tests/test_opp31_mcp_tools.py` | ~15 | All 7 MCP tools |
| **Total** | **~135** | |

### Key Test Cases

**User-defined roles**:
- Load custom role from YAML
- Role with unknown capabilities → uses defaults
- Create role at runtime via MCP tool → saved to disk
- Delete example role → still works (no hardcoded dependency)

**Any model to any role**:
- Qwen assigned as tester → Qwen test overlay applied
- DeepSeek assigned as reviewer → DeepSeek review overlay applied
- Unknown model assigned to custom role → role defaults only
- DeepSeek-R1 assigned to coder → temp forced to 0.6 (critical constraint wins)

**Multi-agent concurrent**:
- Create 3 slots simultaneously → all active
- Each slot independently configured → different temps
- Remove one slot → others unaffected
- Send to slot → correct config applied

**Provider capabilities**:
- Vision model detected → vision=True
- Coder model detected → code score > 0
- Auto-resolve "coder" role → picks model with highest code score
- Auto-resolve "image-describer" → picks vision-capable model

---

## 13. Implementation Phases (TDD)

### Phase 1: Roles + Config

| Step | Commit |
|------|--------|
| 1a | `test(OPP-31): RED — RoleTemplate and RoleRegistry` |
| 1b | `feat(OPP-31): GREEN — user-defined roles with YAML loader` |
| 1c | `refactor(OPP-31): role constants` |

### Phase 2: Knowledge Base

| Step | Commit |
|------|--------|
| 2a | `test(OPP-31): RED — model knowledge base and family detection` |
| 2b | `feat(OPP-31): GREEN — 6-family knowledge base with constraints` |
| 2c | `refactor(OPP-31): knowledge base cleanup` |

### Phase 3: Resolver

| Step | Commit |
|------|--------|
| 3a | `test(OPP-31): RED — resolver with auto and explicit modes` |
| 3b | `feat(OPP-31): GREEN — DynamicResolver composing with SmartModelSelector` |
| 3c | `refactor(OPP-31): resolver cleanup` |

### Phase 4: Agent Slot Manager

| Step | Commit |
|------|--------|
| 4a | `test(OPP-31): RED — concurrent agent slots` |
| 4b | `feat(OPP-31): GREEN — AgentSlotManager` |
| 4c | `refactor(OPP-31): slot manager cleanup` |

### Phase 5: Token Counting + Overflow

| Step | Commit |
|------|--------|
| 5a | `test(OPP-31): RED — token counter and overflow` |
| 5b | `feat(OPP-31): GREEN — tiktoken + 3 overflow policies` |
| 5c | `refactor(OPP-31): overflow cleanup` |

### Phase 6: Template + Sanitization

| Step | Commit |
|------|--------|
| 6a | `test(OPP-31): RED — template detection and sanitization` |
| 6b | `feat(OPP-31): GREEN — template detection` |
| 6c | `refactor(OPP-31): template cleanup` |

### Phase 7: MCP Tools

| Step | Commit |
|------|--------|
| 7a | `test(OPP-31): RED — 7 MCP tools` |
| 7b | `feat(OPP-31): GREEN — create/list/remove agent, roles, models` |
| 7c | `refactor(OPP-31): MCP tool cleanup` |

### Phase 8: Integration

| Step | Commit |
|------|--------|
| 8a | `feat(OPP-31): wire AgentSlotManager into LLMClient` |

### Total: ~22 commits, ~135 tests, ~1365 lines

---

## 14. Deferred Items

| Item | Reason | Trigger |
|------|--------|---------|
| Workflow YAML chains | Useful but adds complexity; manual `send_to_agent` covers v1 | User demand |
| Internet-fetched knowledge base | Auto-fetch from HuggingFace model cards | Production stability |
| Quantization-aware param adjustment | Unvalidated (Q4→lower temp by 0.05) | Real benchmark evidence |
| Benchmark auto-refresh script | `KNOWN_BENCHMARKS` dated 2025-01 | New model releases |
| Agent-to-agent piping | Direct output routing between slots | Workflow demand |

---

## 15. Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Family detection fails for new model | LOW | Falls back to role defaults — works acceptably |
| Knowledge base becomes stale | MEDIUM | Code-versioned; update with each bridge release |
| Too many concurrent slots exhaust VRAM | HIGH | Document VRAM limits; auto-load respects available memory |
| tiktoken ±10% off actual tokenizer | MEDIUM | Use conservative 90% of context_length |
| LM Studio infinite-loop bug | HIGH | Monitor `stopReason`; abort after max_tokens×0.9 |
| User creates conflicting role names | LOW | Validate uniqueness on create; error on collision |

---

## Appendix A: Complete Temperature Matrix

```
TASK    QWEN   DEEPSEEK  DS-R1   LLAMA  MISTRAL  PHI-4  PHI-REASON  GEMMA
─────── ────── ────────  ──────  ─────  ───────  ─────  ──────────  ─────
code    0.20   0.0       0.6*    0.2    0.2      0.0    0.8*        0.5
test    0.30   0.3       0.6*    0.3    0.2      0.1    0.8*        0.4
write   0.70   1.0       0.6*    0.7    0.7      0.7    0.8*        1.0
review  0.20   0.3       0.6*    0.2    0.2      0.2    0.8*        0.4
chat    0.70   1.3       0.6*    0.6    0.15     0.7    0.8*        1.0
reason  0.60   0.6       0.6     0.6    0.7      0.5    0.8*        0.8

* = mandatory value, constraint-enforced (overrides user input)
```

## Appendix B: Research Artifacts

| Report | File | Sources |
|--------|------|---------|
| Synthesis | `.omc/scientist/reports/20260301_131300_opp31_synthesis_report.md` | 112 |
| Cross-validation | `.omc/scientist/reports/20260301_130953_opp31_cross_validation.md` | All |
| Qwen configs | `.omc/scientist/reports/20260301_model_configs_qwen.md` | 15 |
| DeepSeek/Phi/Gemma | `.omc/scientist/reports/20260301_model_configs_deepseek_phi_gemma.md` | 16 |
| Dynamic patterns | `.omc/scientist/reports/20260301_dynamic_profile_patterns.md` | 18 |
| Stages S1-S7 | 13 files, ~250KB | Various |

### Key Sources

- [Qwen2.5 Blog](https://qwenlm.github.io/blog/qwen2.5/) — [Qwen3 Blog](https://qwenlm.github.io/blog/qwen3/)
- [DeepSeek API Params](https://api-docs.deepseek.com/quick_start/parameter_settings) — [R1 Card](https://huggingface.co/deepseek-ai/DeepSeek-R1)
- [Phi-4-reasoning Card](https://huggingface.co/microsoft/Phi-4-reasoning)
- [Gemma-3 HF #25](https://huggingface.co/google/gemma-3-12b-it/discussions/25)
- [Muxup Vendor Reference](https://muxup.com/2025q2/recommended-llm-parameter-quick-reference)
- [CrewAI LLM Selection](https://docs.crewai.com/en/learn/llm-selection-guide) — [RouteLLM](https://github.com/lm-sys/RouteLLM)
- [Semantic Kernel CustomAIServiceSelector](https://github.com/microsoft/semantic-kernel)

---

*OPP-31 spec v3.0 — Agent-Slot Architecture — 2026-03-01*
