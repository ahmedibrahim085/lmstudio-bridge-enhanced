# LM Studio Bridge Enhanced v5.0.0

An autonomous middleware agent that lets any MCP client delegate tasks to local LLMs, which can then use any MCP tool — translating between all 4 API formats in real-time.

**Based on**: [LMStudio-MCP](https://github.com/infinitimeless/LMStudio-MCP) by infinitimeless

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![LM Studio](https://img.shields.io/badge/LM%20Studio-0.4.4+-green.svg)](https://lmstudio.ai/)
[![Tests](https://img.shields.io/badge/tests-1969%20passing-brightgreen.svg)](#testing)
[![Coverage](https://img.shields.io/badge/coverage-91%25-brightgreen.svg)](#testing)

---

## The 5 Pillars

This project is not just a bridge — it's a **3-way autonomous middleware agent** built on 5 pillars:

```
     Claude Code                         Other MCPs
     (any MCP client)                    (filesystem, memory, git, fetch...)
          |                                   ^
          | MCP Protocol                      | MCP Protocol
          v                                   |
    +---------------------------------------------+
    |          PILLAR 1: MCP SERVER                |
    |          (FastMCP, 37 tools)                 |
    |                                              |
    |    +--------------------------------------+  |
    |    |   PILLAR 4: AUTONOMOUS AGENT         |  |
    |    |   (self-correcting loops, parallel   |  |
    |    |    tool exec, metrics, branching)    |  |
    |    +--------+-----------------+-----------+  |
    |             |                 |               |
    |    +--------v------+  +------v-----------+   |
    |    | PILLAR 2:     |  | PILLAR 3:        |   |
    |    | LLM CLIENT    |  | MCP CLIENT       |   |
    |    | (Facade +     |  | (dynamic         |   |
    |    |  7 sub-clients|  |  discovery,      |   |
    |    |  4 API surfs) |  |  hot reload)     |   |
    |    +--------+------+  +------+-----------+   |
    |             |                 |               |
    |    +--------v-----------------v-----------+   |
    |    |     PILLAR 5: FORMAT TRANSLATOR      |   |
    |    |     (OpenAI <-> Anthropic <->        |   |
    |    |      Responses, bidirectional)       |   |
    |    +--------------------------------------+   |
    +---------------------------------------------+
          |                                   |
          | HTTP (3 API surfaces)             | stdio/SSE
          v                                   v
     LM Studio                           MCP Servers
     (local LLMs)                        (any from .mcp.json)
```

| Pillar | Role | What Sees It As |
|--------|------|-----------------|
| **1. MCP Server** | Serves 37 tools via FastMCP | Claude Code sees an MCP with tools |
| **2. LLM Client** | Facade + 7 sub-clients across 4 API surfaces | LM Studio sees an HTTP client |
| **3. MCP Client** | Connects to other MCPs dynamically from `.mcp.json` | Other MCPs see an MCP client |
| **4. Autonomous Agent** | Runs LLM-tool loops independently — multi-round, self-correcting, parallel | The orchestrator that ties everything together |
| **5. Format Translator** | Bidirectional 3-way translation: OpenAI, Anthropic, Responses | The universal glue between competing standards |

## What Makes It Different

| # | Differentiation | Description |
|---|----------------|-------------|
| **D-1** | 3-way MCP topology | Acts as MCP Server AND MCP Client AND LLM Client simultaneously — a 3-way node in the MCP graph |
| **D-2** | Autonomous agent loops | Claude delegates a task, the bridge runs a full LLM-tool loop and returns only the result |
| **D-3** | Universal format translation | OpenAI, Anthropic, Responses, Native — all 4 formats, bidirectional, for tools + messages + streaming |
| **D-4** | Dynamic MCP discovery | Hot-reload from `.mcp.json` — add a new MCP, it's instantly available. Zero code changes |
| **D-5** | Smart model routing | Scores all loaded models by capability and picks the best one for each task |
| **D-6** | JIT model lifecycle | Model not loaded? Bridge loads it. Wrong model? Bridge swaps it. All transparent |
| **D-7** | Conversation branching | Fork conversations at any point, explore alternatives, merge results — tree-based history |

---

## Quick Start

### 1. Prerequisites

- Python 3.9+
- [LM Studio](https://lmstudio.ai/) v0.4.4+ with a model loaded
- MCP-compatible client (e.g., Claude Code)

### 2. Install

```bash
git clone https://github.com/ahmedibrahim085/lmstudio-bridge-enhanced.git
cd lmstudio-bridge-enhanced
pip install -r requirements.txt
```

### 3. Configure

#### Option A: Automated Setup (Recommended)

Run the setup script to automatically configure the correct paths:

```bash
./setup-config.sh
```

The script will:
- Detect your project root automatically
- Create configuration for Claude Code and/or LM Studio
- Set correct `PYTHONPATH` for Python module imports
- Backup existing configurations

#### Option B: Manual Configuration

##### For Claude Code

Add to your project's `.mcp.json`:

```json
{
  "mcpServers": {
    "lmstudio-bridge": {
      "command": "python3",
      "args": [
        "/absolute/path/to/lmstudio-bridge-enhanced/main.py"
      ],
      "env": {
        "PYTHONPATH": "/absolute/path/to/lmstudio-bridge-enhanced",
        "LMSTUDIO_HOST": "localhost",
        "LMSTUDIO_PORT": "1234"
      }
    }
  }
}
```

##### For LM Studio

Add to `~/.lmstudio/mcp.json`:

```json
{
  "mcpServers": {
    "lmstudio-bridge-enhanced": {
      "command": "python3",
      "args": [
        "/absolute/path/to/lmstudio-bridge-enhanced/main.py"
      ],
      "env": {
        "PYTHONPATH": "/absolute/path/to/lmstudio-bridge-enhanced",
        "LMSTUDIO_HOST": "localhost",
        "LMSTUDIO_PORT": "1234"
      }
    }
  }
}
```

**Required Setup:**
1. Replace `/absolute/path/to/lmstudio-bridge-enhanced` with your actual installation path
   - Example (macOS/Linux): `/Users/yourname/projects/lmstudio-bridge-enhanced`
   - Example (Windows): `C:\Users\yourname\projects\lmstudio-bridge-enhanced`
2. **Important**: Set `PYTHONPATH` to the same directory as `main.py` (the project root)

**Optional Environment Variables:**
- `DEFAULT_MODEL`: Pin a specific model (e.g., `"qwen/qwen3-coder-30b"`)
- `LMSTUDIO_HOST`: Change if LM Studio runs on different host (default: `localhost`)
- `LMSTUDIO_PORT`: Change if LM Studio uses different port (default: `1234`)

**Example Configuration:**
See `.mcp.json.example` for a template configuration file with placeholders.

### 4. Use

In Claude Code or your MCP client:

```
Use the autonomous_with_mcp tool with the filesystem MCP to list all Python files
```

---

## Key Features

### Agent Profiles & Model Slots (v5.0.0)

Define task-specific agent roles and assign models dynamically:

```python
# Create a role template
create_role(
    name="coder",
    description="Code generation and refactoring",
    config={"temperature": 0.2, "max_tokens": 4096}
)

# Create an agent with a model assigned to a role
create_agent(
    name="my-coder",
    role="coder",
    model="qwen/qwen3-coder-30b"
)

# List active agents
list_agents()

# Remove when done
remove_agent(name="my-coder")
```

**Features**:
- User-defined roles via YAML templates — create, modify, delete
- Any model can play any role with auto-resolved configuration
- Multiple agent slots run concurrently (coder + tester + reviewer)
- 6-param config: temperature, top_p, top_k, max_tokens, system_prompt, context_length
- Model family knowledge base: 6 families x 6 task types with vendor-researched overlays
- Critical constraints auto-enforced per model family

### Native Chat API (v5.0.0)

Direct access to LM Studio's native `/api/v1/chat` endpoint with 19-event SSE streaming:

**19 Event Types**: `chat.start`, `model_load.start/progress/end`, `prompt_processing.start/progress/end`, `reasoning.start/delta/end`, `tool_call.start/arguments/success/failure`, `message.start/delta/end`, `error`, `chat.end`

**Features**:
- Rich streaming with model loading progress, reasoning tokens, tool execution status
- Native reasoning parameter (`reasoning_effort`: low/medium/high) replacing `thinking_budget`
- Log-probabilities support for confidence scoring
- Ephemeral MCP servers via `integrations` parameter
- API authentication via `Authorization` header

### Model Auto-Download (v5.0.0)

Download models directly via REST API without manual LM Studio interaction:

```python
lms_download_model(model_key="qwen/qwen3-coder-30b")
```

### Multi-Model Support (v3.1.0)

Choose different models for different tasks:

```python
# Reasoning model for analysis
autonomous_with_mcp(
    mcp_name="filesystem",
    task="Analyze codebase architecture",
    model="mistralai/magistral-small-2509"
)

# Coding model for implementation
autonomous_with_mcp(
    mcp_name="filesystem",
    task="Generate unit tests",
    model="qwen/qwen3-coder-30b"
)

# Default model (omit parameter)
autonomous_with_mcp(
    mcp_name="filesystem",
    task="List files"
)
```

**Features**:
- Async model validation with caching
- Clear error messages listing available models
- Backward compatible (model parameter is optional)
- Handles IDLE state (models auto-activate)

### Structured Output (v3.2.0) - JSON Schema

Force the LLM to output valid JSON conforming to a schema (LM Studio v0.3.32+):

```python
# Get structured JSON output
chat_completion(
    prompt="List 3 programming languages with their use cases",
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "languages",
            "schema": {
                "type": "object",
                "properties": {
                    "languages": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "use_case": {"type": "string"}
                            }
                        }
                    }
                },
                "required": ["languages"]
            }
        }
    }
)
# Returns: {"languages": [{"name": "Python", "use_case": "Data science"}, ...]}
```

**Features**:
- JSON schema validation with `validate_json_schema` tool
- Schema depth and complexity limits (max 10 levels, 100 properties)
- `json_object` mode for unstructured but valid JSON
- Backward compatible (response_format is optional)

**Note**: Models < 7B parameters may produce invalid JSON. Recommended: Qwen 7B+, Llama 3 8B+, or Mistral 7B+.

### Vision/Image Analysis (v3.2.0)

Analyze images using multimodal models (LM Studio v0.3.30+):

```python
# Analyze any image (auto-detects input format)
analyze_image(image="/path/to/photo.jpg")
analyze_image(image="https://example.com/image.png")
analyze_image(image="data:image/png;base64,...")

# Generate descriptions with different styles
describe_image(image="/path/to/image.jpg", style="detailed")  # or "brief", "creative", "technical"

# Compare multiple images
compare_images(
    images=["design_v1.png", "design_v2.png"],
    comparison_type="differences"  # or "similarities", "both"
)

# Extract text (OCR-like)
extract_text_from_image(image="/path/to/document.png")

# Ask specific questions
answer_about_image(
    image="/path/to/chart.png",
    question="What is the value shown for Q3 2024?"
)
```

**Supported Input Formats** (auto-detected):
- File paths: `/path/to/image.png`, `./relative/path.jpg`
- URLs: `https://example.com/image.jpg`
- Base64: `data:image/png;base64,...` or raw base64 strings

**Note**: Requires a vision-capable model (LLaVA, Qwen-VL, GPT-4V compatible). Text-only models will return an error.

### Model Capability Registry (v3.2.0)

Query model capabilities, VRAM requirements, and find the best model for your task:

```python
# List all downloaded models with metadata
lms_list_downloaded_models()
# Returns: [{"model_key": "qwen/qwen3-coder-30b", "size_bytes": 19000000000, ...}]

# Get detailed capabilities with BFCL benchmark scores
get_model_capabilities(model="qwen/qwen3-coder-30b")
# Returns: {
#   "model_key": "qwen/qwen3-coder-30b",
#   "tool_use_score": 0.933,  # BFCL benchmark
#   "estimated_vram_gb": 18.5,
#   "is_thinking_model": false,
#   "max_context_length": 32768
# }

# Intelligent model resolution with fallback
lms_resolve_model(
    requested_model="large-model-not-downloaded",
    task_type="coding"
)
# Returns: Alternative model suggestion if requested not available

# Download a model
lms_download_model(model_key="huggingface/model-name")
```

**Features**:
- VRAM estimation (accounts for quantization, KV cache, context length)
- Thinking model detection (QwQ, DeepSeek-R1, o1 patterns)
- BFCL benchmark scores for tool calling capability
- Intelligent fallback suggestions
- Persistent cache with delta updates

**VRAM Estimation Formula**:
```
VRAM = (file_size × quant_multiplier + kv_cache) × 1.1 overhead
```

### Dynamic MCP Discovery

No hardcoded configurations. Works with any MCP in your `.mcp.json`:

```python
autonomous_with_mcp("filesystem", "task")
autonomous_with_mcp("memory", "task")
autonomous_with_mcp("postgres", "task")
# Works with ANY MCP
```

### Reasoning Display

For reasoning-capable models (DeepSeek R1, Magistral, Qwen3-thinking), see the model's thinking process before the final answer.

### Autonomous Execution

LLM uses MCP tools autonomously:

```python
# Single MCP
autonomous_with_mcp("filesystem", "Analyze codebase")

# Multiple MCPs
autonomous_with_multiple_mcps(
    ["filesystem", "memory"],
    "Analyze code and build knowledge graph"
)

# Auto-discover all MCPs
autonomous_discover_and_execute("Complete this task")
```

---

## Available Tools (37 total)

### Core Completions (5 tools)
1. `chat_completion` - Chat completions (with reasoning_effort, logprobs, response_format)
2. `text_completion` - Text/code completion
3. `create_response` - Stateful conversations
4. `generate_embeddings` - Vector embeddings
5. `validate_json_schema` - Validate JSON schema before use with structured output

### Health & Discovery (5 tools)
6. `health_check` - Check LM Studio connection
7. `check_server_health` - Detailed server health with diagnostics
8. `check_server_type` - Detect GUI vs headless (llmster)
9. `get_current_model` - Get loaded model info
10. `list_models` - List available models

### Vision Tools (6 tools)
11. `analyze_image` - Comprehensive image analysis
12. `describe_image` - Generate descriptions (detailed/brief/creative/technical)
13. `compare_images` - Compare multiple images
14. `extract_text_from_image` - OCR-like text extraction
15. `identify_objects` - Identify objects with locations
16. `answer_about_image` - Answer specific questions about images

### Autonomous MCP (5 tools)
17. `autonomous_with_mcp` - Use any MCP by name
18. `autonomous_with_multiple_mcps` - Use multiple MCPs
19. `autonomous_discover_and_execute` - Auto-discover all MCPs
20. `autonomous_with_images` - Autonomous with vision input
21. `list_available_mcps` - List discovered MCPs

### Agent Profiles (5 tools) — NEW in v5.0.0
22. `create_agent` - Create an agent slot with model + role
23. `list_agents` - List active agent slots
24. `remove_agent` - Remove an agent slot
25. `create_role` - Create a role template
26. `list_roles` - List available role templates

### Smart Model Selection (1 tool)
27. `select_best_model` - Capability-scored model routing

### LMS CLI Tools (9 tools, optional)
28. `lms_list_loaded_models` - List loaded models with details
29. `lms_list_downloaded_models` - List all downloaded models with metadata
30. `lms_load_model` - Load a specific model
31. `lms_unload_model` - Unload a model to free memory
32. `lms_ensure_model_loaded` - Idempotent model preloading (recommended)
33. `lms_search_models` - Search model catalog
34. `lms_download_model` - Download models from Hugging Face
35. `lms_resolve_model` - Intelligent model resolution with fallback
36. `lms_server_status` - Server health and diagnostics

---

## Architecture

The bridge occupies a unique position in the MCP ecosystem — it's simultaneously a server, client, and autonomous agent:

```
Claude Code ──MCP──> [MCP Server] ──> [Autonomous Agent] ──> [LLM Client] ──HTTP──> LM Studio
                                            |
                                            +──> [MCP Client] ──MCP──> filesystem, memory, git...
                                            |
                                      [Format Translator]
                                    OpenAI <-> Anthropic <-> Responses
```

**API Surfaces** (4 simultaneous):
- OpenAI-compatible: `/v1/chat/completions`, `/v1/completions`, `/v1/models`, `/v1/embeddings`, `/v1/responses`
- Anthropic-compatible: `/v1/messages`
- Native LM Studio REST: `/api/v1/models`, `/api/v1/models/load`, `/api/v1/models/unload`, `/api/v1/diagnostics`
- Native LM Studio Chat: `/api/v1/chat` — 19-event SSE streaming with reasoning, tool calls, model loading progress

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LMSTUDIO_HOST` | `localhost` | LM Studio host |
| `LMSTUDIO_PORT` | `1234` | LM Studio API port |
| `MCP_JSON_PATH` | (auto-detect) | Custom `.mcp.json` path |
| `DEFAULT_MODEL` | (auto-detect) | Default model to use (e.g., `qwen/qwen3-coder-30b`) |
| `LMS_MAX_RETRIES` | `3` | Max retry attempts for LMS CLI operations |
| `LMS_RETRY_BASE_DELAY` | `1.0` | Base delay between retries (seconds) |
| `LMS_RETRY_MAX_DELAY` | `10.0` | Maximum delay cap (seconds) |
| `LMS_EXTRA_NUMERIC_PARAMS` | `""` | Additional numeric params for type coercion (comma-separated) |

### System Prompt (Recommended)

To give your local LLM proper identity and tool usage guidance, configure a system prompt in LM Studio:

**How to Configure**:
1. Open LM Studio
2. Go to Settings → System Prompt (or Chat Settings)
3. Paste the following prompt:

```
You are a local language model running via LM Studio on the user's machine.

## Your Identity
- Model: Running locally (not a cloud service)
- Capabilities: You have access to MCP tools for extended functionality
- Purpose: Assist users with tasks requiring external data/tools

## When to Use Tools
✅ Use tools ONLY when:
- Reading/writing files → use autonomous_with_mcp(mcp_name="filesystem")
- Fetching web content → use autonomous_with_mcp(mcp_name="fetch")
- Storing/retrieving knowledge → use autonomous_with_mcp(mcp_name="memory")
- GitHub operations → use autonomous_with_mcp(mcp_name="github")

❌ Do NOT use tools for:
- Conversational responses (greetings, small talk)
- Identity questions ("Who are you?" - answer: "I am a local LLM...")
- General knowledge ("What is X?" - answer from training)
- Explanations, definitions, tutorials

## Decision Process
Before calling ANY tool, ask:
1. Do I need external data I don't have? → If NO, answer directly
2. Is this a conversational response? → If YES, answer directly
3. Am I delegating to another LLM when I should answer? → If YES, answer directly

When in doubt, answer directly without tools.
```

**Testing Your Configuration**:
```
User: "Hello, who are you?"
Expected: LLM responds directly (no tools) - "I am a local language model..."

User: "Read my README file"
Expected: LLM uses autonomous_with_mcp(mcp_name="filesystem", ...)
```

### MCP Discovery Priority

1. `$MCP_JSON_PATH` (if set)
2. `~/.lmstudio/mcp.json`
3. `$(pwd)/.mcp.json`
4. `~/.mcp.json`

---

## Testing

Run comprehensive tests:

```bash
cd lmstudio-bridge-enhanced
python3 -m pytest tests/ -v
```

**Test Results**: ~1969 tests passing, 91% coverage

Test coverage includes:
- Format adapter 3-way translation (200+ tests)
- Autonomous agent loops — OpenAI and Anthropic formats (100+ tests)
- Streaming — SSE parser, native SSE parser, thinking parser (100+ tests)
- Structured output and JSON schema (51 tests)
- Vision/multimodal (50+ tests)
- Model registry, selection, discovery (150+ tests)
- Model lifecycle — load, unload, JIT, download, validation (120+ tests)
- Agent profiles — slots, roles, resolver, knowledge base (200+ tests)
- Native chat client — 19 event types, ephemeral MCP (80+ tests)
- Reasoning, logprobs, authentication (80+ tests)
- Conversation branching (50+ tests)
- Thread safety, resource cleanup, error handling (80+ tests)
- Architecture guards, constants split, version consistency (30+ tests)

---

## Documentation

- [Quick Start](docs/QUICKSTART.md) - Step-by-step tutorial
- [API Reference](docs/API_REFERENCE.md) - Complete tool documentation
- [Architecture](docs/ARCHITECTURE.md) - How dynamic discovery works
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues
- [Multi-Model Guide](docs/MULTI_MODEL_GUIDE.md) - Model selection guide
- [Contributing](CONTRIBUTING.md) - Development guidelines

---

## Troubleshooting

### Connection Issues

```bash
# Verify LM Studio is running
curl http://localhost:1234/v1/models

# Check MCP configuration
python3 -c "from mcp_client.discovery import get_mcp_discovery; \
            d = get_mcp_discovery(); print(d.mcp_json_path)"
```

### MCP Not Discovered

```bash
# List available MCPs
python3 -c "from mcp_client.discovery import get_mcp_discovery; \
            d = get_mcp_discovery(); print(d.list_available_mcps())"
```

See [Troubleshooting Guide](docs/TROUBLESHOOTING.md) for more.

---

## Version History

### v5.0.0 (March 2026) - Current

**Architecture Refactoring (Phase A)**:
- **ARCH-1**: LLMClient Facade pattern — split 1500-line god class into 7 Protocol-based sub-clients (chat, responses, anthropic, streaming, thinking, model_info, native_chat)
- **ARCH-2**: Constants package — split 854-line flat file into 15 domain modules with backward-compatible re-exports
- **ARCH-3**: Metrics helper extraction — deduplicated 4x copy-pasted 15-line blocks
- **ARCH-4**: Exception hierarchy — `core/exceptions.py` with proper upward dependency fix
- **ARCH-5**: Platform-abstract npx spawning — removed 85 lines of macOS-only Homebrew paths

**New Features (Phase B)**:
- **OPP-21**: Native reasoning parameter (`reasoning_effort`: low/medium/high) — replaces `thinking_budget`
- **OPP-28**: API authentication — `Authorization` header support for secured LM Studio instances
- **OPP-29**: Log-probabilities — per-token confidence scoring
- **OPP-31**: Agent profiles & model slots — user-defined roles, any model to any role, concurrent agents, 6-family knowledge base
- **OPP-27**: Advanced model load params — GPU offloading, context length, flash attention
- **OPP-24**: Model auto-download via REST API

**Major Features (Phase C)**:
- **OPP-19**: Native chat API (`/api/v1/chat`) — 19-event SSE parser with model loading, reasoning, tool calls
- **OPP-25**: Ephemeral MCP servers — `integrations` parameter for per-request MCP configuration

**Stats**: 1969 tests, 91% coverage, 57 commits, +9541/-2560 lines

### v4.1.0 (March 2026)
- **DeprecationWarning for thinking_budget** — migration bridge to v5.0.0 reasoning API
- **CI enforcement** — coverage gate (89%), ruff lint, architecture guard
- **Python 3.12 in CI matrix** — matches pyproject.toml classifiers

### v4.0.0 (March 2026)
- **Code quality audit** — 12-agent, 3-wave deep review with TDD fixes
- **Hardcoded value extraction** — all magic numbers moved to config/constants.py
- **Silent error catch elimination** — logging added to all 16 catch blocks
- **Vision helper deduplication** — 6 duplicated try/except blocks consolidated
- **Unused import cleanup** — ruff --fix across all tool modules
- **Public API test coverage** — register_*_tools() functions now tested
- **Thread safety** — threading.Lock on shared caches
- **Error contracts** — standardized tool error return format
- **Monotonic timers** — time.monotonic() for TTL caches
- **1684 tests, 91% coverage**

### v3.5.0 (February 2026)
- **18 OPPs implemented** across 5 rounds (Phase 1 through Round C)
- **3-way format adapter** — OpenAI, Anthropic, Responses (bidirectional)
- **Dual-format autonomous loops** — OpenAI and Anthropic tool-calling
- **Streaming infrastructure** — SSE parser for all 3 API surfaces
- **Extended thinking** — reasoning budget control for thinking models
- **Multi-modal loops** — vision support in autonomous agent
- **Conversation branching** — fork/merge tree navigation
- **Smart model selection** — capability-scored model routing
- **Native MCP via API** — MCP servers configured in API requests
- **Test infrastructure overhaul** — 1455 tests, 91% coverage
- **10 server bug fixes** — resource leaks, thread safety, silent failures

### v3.4.0 (February 2026)
- Streaming (OPP-12), Extended Thinking (OPP-14), Format Adapter 3-way (OPP-10)
- Smart Model Selection (OPP-08), Headless Deployment (OPP-18)
- ~80% coverage, ~1100 tests

### v3.2.0 (November 2025)
- Structured JSON Output, Vision/Multimodal, Model Capability Registry
- 331 tests, 44 commits, 10 new MCP tools

### v3.1.0 (November 2025)
- Multi-model support, model validation, 7 exception classes

### v3.0.0 (October 2025)
- Reasoning display, evidence-based safety, type safety

See [docs/release-notes/](docs/release-notes/) for complete details.

---

## License

MIT License - See [LICENSE](LICENSE)

---

## Credits

**Original**: [LMStudio-MCP](https://github.com/infinitimeless/LMStudio-MCP) by infinitimeless
**Enhanced by**: Ahmed Maged

**Development Team**:
- Ahmed Maged - Lead Developer
- Claude (Anthropic) - Architecture, documentation, best practices
- Qwen3-Coder 30B - Code generation and implementation
- Qwen3-Think - Deep analysis and strategic planning

See [CONTRIBUTING.md](CONTRIBUTING.md) for development collaboration details.

---

## Support

- **Issues**: [GitHub Issues](https://github.com/ahmedibrahim085/lmstudio-bridge-enhanced/issues)
- **Documentation**: [docs/](docs/)

For quick help, see [QUICKSTART.md](docs/QUICKSTART.md).
