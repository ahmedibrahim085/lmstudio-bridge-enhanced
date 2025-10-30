# Quick Start Guide

Get started with LM Studio Bridge Enhanced in under 5 minutes!

---

## Prerequisites

- **Python 3.9+** installed
- **LM Studio v0.3.29+** running with a model loaded
- **MCP servers** you want to use (optional, filesystem works out of the box)

---

## Installation (2 minutes)

### Step 1: Clone Repository

```bash
git clone https://github.com/your-username/lmstudio-bridge-enhanced.git
cd lmstudio-bridge-enhanced
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Add to Claude Code Configuration

Add this to your project's `.mcp.json` or `~/.lmstudio/mcp.json`:

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

### Step 4: Restart Claude Code

Restart Claude Code to load the MCP server. This is a **one-time step** - after this, you can add new MCPs without restarting!

---

## First Example (1 minute)

### List Files with Local LLM

In Claude Code, say:

```
Use autonomous_with_mcp with the filesystem MCP to list all Python files in the current directory
```

The local LLM will autonomously:
1. Connect to the filesystem MCP
2. Discover available tools
3. Use `search_files` to find Python files
4. Return the list to you

**No API costs, runs locally, instant results!**

---

## Core Concepts

### 1. Dynamic MCP Discovery

Add any MCP to `.mcp.json` → use it immediately:

```json
{
  "mcpServers": {
    "my-custom-mcp": {
      "command": "uvx",
      "args": ["my-mcp-server"]
    }
  }
}
```

Done! No restart needed (after initial setup).

### 2. Autonomous Execution

The local LLM decides which tools to use and when:

```python
autonomous_with_mcp(
    mcp_name="filesystem",
    task="Find all TODO comments and create a summary.txt"
)
```

The local LLM will autonomously:
- Search for files
- Read files with TODO comments
- Create summary.txt
- Return completion status

### 3. Hot Reload

**Performance**: 0.011ms overhead (essentially free!)

**Result**: Add MCPs to `.mcp.json` and use them IMMEDIATELY - no restart!

---

## Common Use Cases

### 1. File Operations

```python
# Read and analyze
autonomous_with_mcp(
    "filesystem",
    "Read README.md and count how many features are listed"
)

# Search across multiple files
autonomous_with_mcp(
    "filesystem",
    "Find all Python files that import 'asyncio' and list them"
)

# Create documentation
autonomous_with_mcp(
    "filesystem",
    "Read all .py files in tools/ and create API_DOCS.md"
)
```

### 2. Knowledge Graph

```python
# Build knowledge graph
autonomous_with_mcp(
    "memory",
    "Create entities for Python, FastMCP, and MCP with 'uses' and 'implements' relations"
)

# Search knowledge
autonomous_with_mcp(
    "memory",
    "Search for all entities related to 'autonomous agents'"
)
```

### 3. Web Content

```python
# Fetch and summarize
autonomous_with_mcp(
    "fetch",
    "Fetch https://modelcontextprotocol.io and explain MCP in 3 sentences"
)
```

### 4. GitHub Operations

```python
# Search repositories
autonomous_with_mcp(
    "github",
    "Search for MCP server repositories and list top 5 by stars"
)
```

### 5. Multiple MCPs Simultaneously

```python
# Use tools from multiple MCPs in one session
autonomous_with_multiple_mcps(
    ["filesystem", "memory"],
    "Read all Python files and create a knowledge graph of the codebase structure"
)
```

---

## Configuration

### Environment Variables

Set these in `.mcp.json` or as system environment variables:

```json
{
  "env": {
    "LMSTUDIO_HOST": "localhost",
    "LMSTUDIO_PORT": "1234",
    "MCP_JSON_PATH": "/custom/path/.mcp.json"
  }
}
```

### MCP Discovery Priority

The system looks for `.mcp.json` in this order:
1. `$MCP_JSON_PATH` (environment variable)
2. `~/.lmstudio/mcp.json` (LM Studio)
3. `$(pwd)/.mcp.json` (current directory)
4. `~/.mcp.json` (home directory)
5. Parent directory

**No hardcoded paths!** Works for any user, any project, any system.

---

## Adding New MCPs

### Step 1: Add to .mcp.json

```json
{
  "mcpServers": {
    "postgres": {
      "command": "uvx",
      "args": ["mcp-server-postgres", "--db-url", "postgresql://..."]
    }
  }
}
```

### Step 2: Use Immediately!

```python
autonomous_with_mcp(
    "postgres",
    "List all tables and count rows in each"
)
```

**No restart needed!** (After initial setup)

---

## Troubleshooting

### LM Studio Not Responding

```bash
# Check LM Studio is running
curl http://localhost:1234/v1/models

# Expected: List of models
# If error: Start LM Studio and load a model
```

### MCP Not Found

```bash
# List available MCPs
python3 -c "from mcp_client.discovery import MCPDiscovery; print(MCPDiscovery().list_available_mcps())"

# Verify MCP is in .mcp.json
cat ~/.lmstudio/mcp.json
```

### Connection Timeout

- Increase timeout in LM Studio settings
- Try a smaller, faster model
- Check firewall/network settings

---

## What's Next?

### Learn More

- **[Architecture](ARCHITECTURE.md)** - How dynamic discovery works
- **[API Reference](API_REFERENCE.md)** - All tools documented
- **[Troubleshooting](TROUBLESHOOTING.md)** - Common issues solved

### Advanced Features

- **Multi-directory operations**: Work across multiple projects
- **Persistent sessions**: Multiple tasks in one session
- **Custom MCPs**: Add your own MCPs dynamically

### Contributing

See **[CONTRIBUTING.md](../CONTRIBUTING.md)** to join the project!

---

## Example Session

```
You: Use autonomous_with_mcp with filesystem to analyze my project structure

Claude Code calls:
autonomous_with_mcp(
    mcp_name="filesystem",
    task="Analyze project structure: list all directories, count files by type, identify main entry points"
)

Local LLM autonomously:
1. Lists directories → 15 directories found
2. Searches files by extension → 45 .py, 12 .md, 3 .json files
3. Reads setup.py and main.py → Entry points identified
4. Returns comprehensive analysis

Total time: 3 seconds
Cost: $0.00 (local!)
Privacy: 100% (never left your machine!)
```

---

**Ready to start?** Try the examples above and explore the full [documentation](ARCHITECTURE.md)!

**Questions?** Check [Troubleshooting](TROUBLESHOOTING.md) or [open an issue](https://github.com/your-username/lmstudio-bridge-enhanced/issues).
