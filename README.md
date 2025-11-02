# LM Studio Bridge Enhanced v3.1.0

MCP server that connects Claude Code (or any MCP client) to local LLMs via LM Studio.

**Based on**: [LMStudio-MCP](https://github.com/infinitimeless/LMStudio-MCP) by infinitimeless

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![LM Studio](https://img.shields.io/badge/LM%20Studio-0.3.29+-green.svg)](https://lmstudio.ai/)
[![Tests](https://img.shields.io/badge/tests-171%2F172%20passing-brightgreen.svg)](#testing)

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

Add to your `.mcp.json` (Claude Code) or `~/.lmstudio/mcp.json`:

```json
{
  "mcpServers": {
    "lmstudio-bridge": {
      "command": "python3",
      "args": [
        "/absolute/path/to/lmstudio-bridge-enhanced/main.py"
      ],
      "env": {
        "LMSTUDIO_HOST": "localhost",
        "LMSTUDIO_PORT": "1234"
      }
    }
  }
}
```

**Optional**: Add `"DEFAULT_MODEL": "model/name"` to `env` to pin a specific model.

**Important**: Replace `/absolute/path/to/` with the actual path to your clone.

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

### Core LM Studio (7 tools)
1. `health_check` - Check LM Studio connection
2. `list_models` - List available models
3. `get_current_model` - Get loaded model info
4. `chat_completion` - Chat completions
5. `text_completion` - Text/code completion
6. `generate_embeddings` - Vector embeddings
7. `create_response` - Stateful conversations

### Autonomous MCP (4 tools)
8. `autonomous_with_mcp` - Use any MCP by name
9. `autonomous_with_multiple_mcps` - Use multiple MCPs
10. `autonomous_discover_and_execute` - Auto-discover all MCPs
11. `list_available_mcps` - List discovered MCPs

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

**Test Results**: 171/172 tests passing (99.4%)

The single failing test is for LM Studio's `/v1/responses` endpoint which is not yet implemented by LM Studio. Use `chat_completion()` instead.

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

### v3.1.0 (November 2, 2025) - Current
- Multi-model support with validation
- Model validation layer (async, cached)
- 7 custom exception classes
- Critical IDLE state bug fix
- 99.4% test coverage
- 100% backward compatible

### v3.0.0 (October 2025)
- Reasoning display enhancements
- Evidence-based safety features
- Type safety improvements

See [RELEASE_NOTES_v3.1.0.md](RELEASE_NOTES_v3.1.0.md) for complete details.

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
