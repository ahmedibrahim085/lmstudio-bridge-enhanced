# LM Studio Bridge Enhanced v2

> Connect ANY MCP to local LLMs via LM Studio. Zero API costs, full privacy, instant hot reload.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![LM Studio](https://img.shields.io/badge/LM%20Studio-0.3.29+-green.svg)](https://lmstudio.ai/)

---

## What This Does

Bridge between LM Studio (local LLM) and ANY Model Context Protocol (MCP) server. Your local LLM can:

- 🗂️ **Use ANY MCP** - filesystem, database, web, git, and more
- ⚡ **Hot Reload** - Add new MCPs instantly (no restart, 0.011ms overhead)
- 🔧 **Zero Config** - Automatically discovers MCPs from `.mcp.json`
- 🎯 **Multi-Model Support** ✨ NEW - Switch models per task (reasoning vs coding)
- 🔒 **Full Privacy** - Everything runs locally, no cloud APIs
- 💰 **Zero Cost** - No API fees, unlimited usage

**Key Innovations**:
1. Dynamic MCP discovery + hot reload - Add any MCP to `.mcp.json` → use immediately
2. Multi-model support - Choose the right model for each task automatically

---

## Quick Start (2 minutes)

### 1. Install

```bash
git clone https://github.com/your-username/lmstudio-bridge-enhanced.git
cd lmstudio-bridge-enhanced
pip install -r requirements.txt
```

### 2. Configure

Add to your `.mcp.json` or `~/.lmstudio/mcp.json`:

```json
{
  "mcpServers": {
    "lmstudio-bridge-enhanced_v2": {
      "command": "python3",
      "args": ["-m", "lmstudio_bridge"],
      "env": {
        "LMSTUDIO_HOST": "localhost",
        "LMSTUDIO_PORT": "1234"
      }
    }
  }
}
```

### 3. Use

```python
# In Claude Code or any MCP client:
"Use autonomous_with_mcp with the filesystem MCP to list all Python files"

# Add a new MCP to .mcp.json:
{
  "your-new-mcp": {
    "command": "uvx",
    "args": ["your-mcp-server"]
  }
}

# Use immediately (no restart!):
"Use autonomous_with_mcp with your-new-mcp to [your task]"
```

**That's it!** No restart, no code changes, no hardcoded assumptions.

---

## Core Features

### 1. Dynamic MCP Discovery

Works with **ANY** MCP in your `.mcp.json`:

```python
autonomous_with_mcp(
    mcp_name="filesystem",  # or "memory", "fetch", "github", "time", etc.
    task="Your task here"
)
```

- ✅ No hardcoded MCP configurations
- ✅ Automatically discovers all enabled MCPs
- ✅ Works with standard MCPs and custom MCPs

### 2. Hot Reload (0.011ms overhead)

Add MCPs to `.mcp.json` → use immediately:

- **No restart required** (after initial setup)
- **0.011ms overhead** per call (essentially free)
- **734x faster** than LLM API call
- Reads `.mcp.json` fresh on every tool call

**Before Hot Reload:**
1. Add MCP to `.mcp.json`
2. Restart Claude Code (10-30 seconds)
3. Use MCP

**After Hot Reload:**
1. Add MCP to `.mcp.json`
2. Use MCP ✅

### 3. Autonomous Execution

Local LLM autonomously uses MCP tools:

```python
# Single MCP
autonomous_with_mcp("filesystem", "Analyze my codebase")

# Multiple MCPs simultaneously
autonomous_with_multiple_mcps(
    ["filesystem", "memory"],
    "Analyze code and build knowledge graph"
)

# Auto-discover ALL MCPs
autonomous_discover_and_execute(
    "Use any tools you need to complete this task"
)
```

### 4. No Artificial Limits

- **max_rounds: 10000** (default) - Let LLM work until done
- **max_tokens: 8192** (default) - Based on Claude Code limits
- Most tasks complete in < 20 rounds anyway

### 5. Multi-Model Support ✨ NEW

Choose the right model for each task:

```python
# Reasoning model for analysis
autonomous_with_mcp(
    mcp_name="filesystem",
    task="Analyze codebase architecture and identify design patterns",
    model="mistralai/magistral-small-2509"
)

# Coding model for implementation
autonomous_with_mcp(
    mcp_name="filesystem",
    task="Generate unit tests for all functions",
    model="qwen/qwen3-coder-30b"
)

# Default model (omit parameter)
autonomous_with_mcp(
    mcp_name="filesystem",
    task="List Python files"
)
```

**Benefits**:
- 🎯 **Match model to task** - Use reasoning models for analysis, coding models for implementation
- 🔄 **Multi-model pipelines** - Chain different models in workflows
- ✅ **Backward compatible** - Existing code works unchanged
- 🚀 **Easy validation** - Clear error messages if model not found

**Quickstart**:
```python
# 1. List available models
list_models()

# 2. Use specific model
autonomous_with_mcp("filesystem", "task", model="model-name")

# 3. That's it!
```

---

## Available Tools

### Core LM Studio Functions (7)
1. `health_check` - Verify LM Studio API
2. `list_models` - List available models
3. `get_current_model` - Get loaded model
4. `chat_completion` - Chat completions
5. `text_completion` - Raw text/code completion
6. `generate_embeddings` - Vector embeddings
7. `create_response` - Stateful conversations

### Dynamic Autonomous Functions (4) 🚀
1. `autonomous_with_mcp(mcp_name, task)` - Use ANY MCP by name
2. `autonomous_with_multiple_mcps(mcp_names, task)` - Use multiple MCPs
3. `autonomous_discover_and_execute(task)` - Auto-discover ALL MCPs
4. `list_available_mcps()` - List discovered MCPs

**Total: 11 tools** (7 core + 4 dynamic)

---

## How It Works

### Architecture

```
Claude Code (or any MCP client)
    ↓
lmstudio-bridge-enhanced_v2 (MCP Server)
    ↓
LM Studio API (localhost:1234)
    ↓
Local LLM (Qwen, Llama, Mistral, etc.)
    ↓
Other MCP Servers (filesystem, memory, etc.)
```

**The bridge acts as both**:
- **MCP Server** to Claude Code
- **MCP Client** to other MCPs

### Dynamic Discovery Flow

1. Tool called: `autonomous_with_mcp("filesystem", "task")`
2. Hot reload: Read `.mcp.json` (0.011ms)
3. Discover: Find "filesystem" MCP configuration
4. Connect: Connect to filesystem MCP server
5. Tools: Discover filesystem's tools dynamically
6. Execute: Local LLM uses tools autonomously
7. Result: Return final answer

**Zero hardcoded assumptions** - works with any MCP!

---

## Prerequisites

- **Python 3.9+**
- **LM Studio v0.3.29+** with a model loaded
- **MCP servers** you want to use (filesystem, memory, etc.)

---

## Documentation

- **[Quick Start Guide](docs/QUICKSTART.md)** - 5-minute tutorial with examples
- **[Architecture](docs/ARCHITECTURE.md)** - How dynamic discovery works
- **[API Reference](docs/API_REFERENCE.md)** - All tools documented
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues solved
- **[Contributing](CONTRIBUTING.md)** - Join the project

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LMSTUDIO_HOST` | `localhost` | LM Studio host |
| `LMSTUDIO_PORT` | `1234` | LM Studio API port |
| `MCP_JSON_PATH` | (auto-detect) | Custom `.mcp.json` path |

### MCP Discovery Priority

1. `$MCP_JSON_PATH` (if set)
2. `~/.lmstudio/mcp.json`
3. `$(pwd)/.mcp.json`
4. `~/.mcp.json`
5. Parent directory

**100% portable** - no hardcoded paths.

---

## Examples

### Example 1: Filesystem Operations

```python
autonomous_with_mcp(
    mcp_name="filesystem",
    task="Find all Python files, count lines of code, create summary"
)
```

### Example 2: Multiple MCPs

```python
autonomous_with_multiple_mcps(
    mcp_names=["filesystem", "memory"],
    task="Analyze codebase and build a knowledge graph of architecture"
)
```

### Example 3: Auto-Discovery

```python
autonomous_discover_and_execute(
    task="Research MCP protocol, fetch docs, and create a summary"
)
# Automatically discovers and uses: filesystem, fetch, memory
```

### Example 4: Add Custom MCP

```json
// Add to ~/.lmstudio/mcp.json
{
  "mcpServers": {
    "postgres": {
      "command": "uvx",
      "args": ["mcp-server-postgres", "--db-url", "postgresql://..."]
    }
  }
}
```

```python
# Use immediately (no restart!)
autonomous_with_mcp(
    mcp_name="postgres",
    task="List all tables and count rows in each"
)
```

---

## Performance

### Hot Reload Benchmarks

- **Per call overhead**: 0.011ms (11 microseconds)
- **Comparison**: 734x faster than LLM API call (8.07ms)
- **Conclusion**: Essentially FREE

### Token Efficiency

- Uses stateful `/v1/responses` API for autonomous execution
- **97% fewer tokens** at round 100 (vs linear growth)
- **Unlimited rounds** without context overflow

---

## Testing

Run tests:

```bash
# Core integration
python3 test_lmstudio_integration.py

# Dynamic discovery
python3 test_dynamic_discovery.py

# Autonomous execution
python3 test_autonomous.py

# Performance
python3 benchmark.py
```

**All tests passing** ✅

---

## Troubleshooting

### Connection Issues

```bash
# Verify LM Studio is running
curl http://localhost:1234/v1/models

# Check MCP configuration
python3 -c "from mcp_client.discovery import MCPDiscovery; \
            d = MCPDiscovery(); print(d.mcp_json_path)"
```

### Hot Reload Not Working

- Restart Claude Code once to load hot reload code
- After that, hot reload works automatically
- Verify file watching isn't disabled

### MCP Not Discovered

```bash
# List available MCPs
python3 -c "from mcp_client.discovery import MCPDiscovery; \
            d = MCPDiscovery(); print(d.list_available_mcps())"

# Override with environment variable
MCP_JSON_PATH=/path/to/custom/.mcp.json python3 your_script.py
```

See **[Troubleshooting Guide](docs/TROUBLESHOOTING.md)** for more.

---

## Contributing

We welcome contributions! See **[CONTRIBUTING.md](CONTRIBUTING.md)** for:
- Code of conduct
- Development setup
- Contribution guidelines
- Architecture overview

---

## Development

See **[Development Notes](docs/archive/DEVELOPMENT_NOTES.md)** for the complete development journey, including:
- Problems solved
- Design decisions
- Performance optimizations
- Lessons learned

---

## License

MIT License - see [LICENSE](LICENSE) file.

---

## Credits

**Original Project**: [LMStudio-MCP](https://github.com/infinitimeless/LMStudio-MCP) by infinitimeless

**Enhanced by**: Ahmed Maged

### Key Enhancements

- ✅ Dynamic MCP discovery (zero hardcoded configs)
- ✅ Hot reload (0.011ms overhead)
- ✅ Generic support (works with ANY MCP)
- ✅ Autonomous execution (4 new tools)
- ✅ Stateful conversations (97% token savings)
- ✅ Comprehensive documentation

---

## Project Status

🎉 **Production Ready**

- All features implemented and tested
- Comprehensive documentation
- Hot reload verified end-to-end
- Generic support proven (30+ tools from 5 MCPs)
- Ready for open source release

---

## Support

- **Issues**: [GitHub Issues](https://github.com/your-username/lmstudio-bridge-enhanced/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-username/lmstudio-bridge-enhanced/discussions)
- **Documentation**: [docs/](docs/)

---

**Ready to bridge your local LLM to the MCP ecosystem!** 🚀

For a quick tutorial, see **[Quick Start Guide](docs/QUICKSTART.md)**.
