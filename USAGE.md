# Usage Guide - LMStudio Bridge Enhanced

## Quick Start

### 1. Installation
The MCP is already installed at:
```
/Users/ahmedmaged/ai_storage/MyMCPs/lmstudio-bridge-enhanced/
```

### 2. Add to Any Project

Copy this configuration to your project's `.mcp.json`:

```json
{
  "mcpServers": {
    "lmstudio-bridge-enhanced": {
      "disabled": false,
      "command": "python3",
      "args": [
        "/Users/ahmedmaged/ai_storage/MyMCPs/lmstudio-bridge-enhanced/lmstudio_bridge.py"
      ],
      "env": {
        "LMSTUDIO_HOST": "localhost",
        "LMSTUDIO_PORT": "1234"
      }
    }
  }
}
```

**Note:** Adjust the path in `args` if your MyMCPs folder is in a different location.

### 3. Restart Claude Code
After adding the configuration, restart Claude Code to load the MCP.

### 4. Approve MCP
On first use, Claude Code will ask you to approve the MCP server. Click "Approve".

## Using Across Multiple Projects

This MCP is stored in a central location (`/Users/ahmedmaged/ai_storage/MyMCPs/`), so you can:

1. **Add to any project** by copying the `.mcp.json` configuration above
2. **One installation** serves all your projects
3. **Updates** in the central location affect all projects

## Environment Variables

Customize connection to LM Studio:

```json
{
  "env": {
    "LMSTUDIO_HOST": "192.168.1.100",  // Remote LM Studio
    "LMSTUDIO_PORT": "5678"             // Custom port
  }
}
```

## Available Tools

Once configured, you'll have access to 7 tools:

### Original (4 tools)
1. **health_check** - Check LM Studio connectivity
2. **list_models** - List available models
3. **get_current_model** - Get loaded model
4. **chat_completion** - Traditional chat

### Enhanced (3 tools)
5. **text_completion** - Code/text completion
6. **generate_embeddings** - Vector embeddings (requires embedding model)
7. **create_response** - Stateful conversations with response IDs

## Stateful Conversations

The `create_response` tool is the most powerful feature:

**First message:**
```
Input: "Hi, my name is Ahmed"
Output: Response + response_id
```

**Continue conversation:**
```
Input: "What's my name?" + previous_response_id
Output: "Ahmed" (remembered from previous message!)
```

This eliminates the need to manage conversation history manually!

## Troubleshooting

### MCP Not Loading
1. Check path in `.mcp.json` is correct
2. Restart Claude Code
3. Ensure Python 3.9+ is installed

### Connection Errors
1. Verify LM Studio is running: `curl http://localhost:1234/v1/models`
2. Check LMSTUDIO_PORT matches LM Studio settings
3. Try `127.0.0.1` instead of `localhost` in LMSTUDIO_HOST

### Embeddings 404 Error
- You must specify an embedding model
- Use `list_models` to find available embedding models
- Example: `text-embedding-nomic-embed-text-v1.5`

## Example: Using in a New Project

```bash
# 1. Navigate to your project
cd /path/to/your/project

# 2. Create or edit .mcp.json
cat > .mcp.json << 'EOF'
{
  "mcpServers": {
    "lmstudio-bridge-enhanced": {
      "disabled": false,
      "command": "python3",
      "args": [
        "/Users/ahmedmaged/ai_storage/MyMCPs/lmstudio-bridge-enhanced/lmstudio_bridge.py"
      ],
      "env": {
        "LMSTUDIO_HOST": "localhost",
        "LMSTUDIO_PORT": "1234"
      }
    }
  }
}
EOF

# 3. Restart Claude Code
# 4. Start using the 7 tools!
```

## Next Steps

See [README.md](README.md) for complete documentation and feature details.
