# LM Studio Bridge Enhanced v3.2.0

MCP server that connects Claude Code (or any MCP client) to local LLMs via LM Studio.

**Based on**: [LMStudio-MCP](https://github.com/infinitimeless/LMStudio-MCP) by infinitimeless

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![LM Studio](https://img.shields.io/badge/LM%20Studio-0.3.32+-green.svg)](https://lmstudio.ai/)
[![Tests](https://img.shields.io/badge/tests-331%20passing-brightgreen.svg)](#testing)

---

## What It Does

Bridges LM Studio (local LLMs) to MCP servers so your local models can:

- Use MCP tools (filesystem, database, web, git, etc.)
- Switch models per task with validation
- Display reasoning process (for supported models)
- Work with any MCP server via dynamic discovery

---

## Quick Start

### 1. Prerequisites

- Python 3.9+
- [LM Studio](https://lmstudio.ai/) v0.3.29+ with a model loaded
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

## Available Tools

### Core LM Studio (8 tools)
1. `health_check` - Check LM Studio connection
2. `list_models` - List available models
3. `get_current_model` - Get loaded model info
4. `chat_completion` - Chat completions (with optional `response_format` for structured output)
5. `text_completion` - Text/code completion
6. `generate_embeddings` - Vector embeddings
7. `create_response` - Stateful conversations
8. `validate_json_schema` - Validate JSON schema before use with structured output

### Vision Tools (6 tools)
9. `analyze_image` - Comprehensive image analysis
10. `describe_image` - Generate descriptions (detailed/brief/creative/technical)
11. `compare_images` - Compare multiple images
12. `extract_text_from_image` - OCR-like text extraction
13. `identify_objects` - Identify objects with locations
14. `answer_about_image` - Answer specific questions about images

### Model Registry Tools (4 tools)
15. `lms_list_downloaded_models` - List all downloaded models with metadata
16. `lms_download_model` - Download models from Hugging Face
17. `lms_resolve_model` - Intelligent model resolution with fallback
18. `get_model_capabilities` - Get capabilities with BFCL benchmark scores

### Autonomous MCP (4 tools)
19. `autonomous_with_mcp` - Use any MCP by name
20. `autonomous_with_multiple_mcps` - Use multiple MCPs
21. `autonomous_discover_and_execute` - Auto-discover all MCPs
22. `list_available_mcps` - List discovered MCPs

---

## Architecture

```
Claude Code (MCP Client)
    ↓
lmstudio-bridge (MCP Server)
    ↓
LM Studio API (localhost:1234)
    ↓
Local LLM
    ↓
Other MCP Servers (filesystem, memory, etc.)
```

The bridge acts as both:
- MCP server to Claude Code
- MCP client to other MCPs

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

**Test Results**: 331 tests passing (100%)

Test coverage includes:
- Structured output (51 tests)
- Vision/multimodal (50 tests)
- Type coercion (16 tests)
- Model registry (18 tests)
- Retry logic (8 tests)
- E2E multi-model workflows

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

### v3.2.0 (November 23, 2025) - Current
- **Structured JSON Output** - Force valid JSON with schema validation
- **Vision/Multimodal Support** - 6 new tools for image analysis
- **Model Capability Registry** - BFCL scores, VRAM estimation, fallback
- **Autonomous Agent Improvements** - Type coercion, tool_choice=required
- **Resilience** - Retry logic with exponential backoff, API timeouts
- 331 tests (up from 171), 100% pass rate
- 44 commits, 10 new MCP tools

### v3.1.1 (November 4, 2025)
- Ultra-prominent model parameter documentation
- MCP selection decision tree
- Anti-patterns documentation

### v3.1.0 (November 2, 2025)
- Multi-model support with validation
- Model validation layer (async, cached)
- 7 custom exception classes
- Critical IDLE state bug fix

### v3.0.0 (October 2025)
- Reasoning display enhancements
- Evidence-based safety features
- Type safety improvements

See [RELEASE_NOTES_v3.2.0.md](RELEASE_NOTES_v3.2.0.md) for complete details.

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
