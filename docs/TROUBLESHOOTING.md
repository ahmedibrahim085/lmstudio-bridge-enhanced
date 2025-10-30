# Troubleshooting Guide

Common issues and solutions for LM Studio Bridge Enhanced.

---

## Quick Diagnostics

Run these commands first to identify issues:

```bash
# 1. Check LM Studio is running
curl http://localhost:1234/v1/models

# 2. Check .mcp.json location
python3 -c "from mcp_client.discovery import MCPDiscovery; print(MCPDiscovery().mcp_json_path)"

# 3. List available MCPs
python3 -c "from mcp_client.discovery import MCPDiscovery; print(MCPDiscovery().list_available_mcps())"

# 4. Test MCP connection
python3 test_dynamic_mcp_discovery.py
```

---

## Connection Issues

### Issue: "Could not connect to LM Studio"

**Symptoms**:
```
Error: Could not connect to LM Studio API at http://localhost:1234
Connection refused
```

**Causes**:
1. LM Studio not running
2. Wrong port
3. Model not loaded
4. Firewall blocking connection

**Solutions**:

1. **Verify LM Studio is running**:
   ```bash
   curl http://localhost:1234/v1/models
   ```
   Expected: JSON with model list

   If connection refused:
   - Start LM Studio
   - Ensure "Start Server" is enabled in LM Studio
   - Check port in LM Studio settings

2. **Check port configuration**:
   ```json
   {
     "env": {
       "LMSTUDIO_PORT": "1234"  // Match LM Studio's port!
     }
   }
   ```

3. **Load a model**:
   - Open LM Studio
   - Load a model from the model library
   - Wait for model to finish loading

4. **Try localhost alternatives**:
   ```json
   {
     "env": {
       "LMSTUDIO_HOST": "127.0.0.1"  // Instead of "localhost"
     }
   }
   ```

---

### Issue: "No tools available from MCP"

**Symptoms**:
```
Error: No tools available from MCP 'filesystem'. Check MCP server logs.
```

**Causes**:
1. MCP server failed to start
2. MCP server crashed
3. Wrong command/args in .mcp.json
4. Missing dependencies

**Solutions**:

1. **Test MCP server directly**:
   ```bash
   # Filesystem MCP
   npx -y @modelcontextprotocol/server-filesystem --help

   # Memory MCP
   npx -y @modelcontextprotocol/server-memory --help
   ```

2. **Check .mcp.json syntax**:
   ```json
   {
     "mcpServers": {
       "filesystem": {
         "command": "npx",
         "args": ["-y", "@modelcontextprotocol/server-filesystem"],
         "env": {}
       }
     }
   }
   ```

3. **Check stderr logs** in Claude Code output for MCP error messages

4. **Verify Node.js is installed** (required for `npx`):
   ```bash
   node --version
   npx --version
   ```

---

## MCP Discovery Issues

### Issue: "MCP not found in .mcp.json"

**Symptoms**:
```
Error: MCP 'postgres' not found in .mcp.json
Available MCPs: filesystem, memory, fetch
```

**Causes**:
1. MCP name typo
2. MCP not added to .mcp.json
3. Using wrong .mcp.json file

**Solutions**:

1. **List available MCPs**:
   ```python
   list_available_mcps()
   ```

2. **Check .mcp.json location**:
   ```bash
   python3 -c "from mcp_client.discovery import MCPDiscovery; print(MCPDiscovery().mcp_json_path)"
   ```

3. **Verify MCP is in file**:
   ```bash
   cat ~/.lmstudio/mcp.json
   # OR
   cat $(pwd)/.mcp.json
   ```

4. **Use exact name from .mcp.json**:
   ```json
   {
     "mcpServers": {
       "my-postgres": {  // Use "my-postgres", not "postgres"!
         ...
       }
     }
   }
   ```

---

### Issue: "MCP disabled"

**Symptoms**:
```
Error: MCP 'filesystem' is disabled
```

**Cause**: MCP has `"disabled": true` in .mcp.json

**Solution**:

```json
{
  "mcpServers": {
    "filesystem": {
      "disabled": false,  // Set to false or remove this line
      ...
    }
  }
}
```

---

## Hot Reload Issues

### Issue: "New MCP not discovered"

**Symptoms**: Added MCP to `.mcp.json` but `list_available_mcps()` doesn't show it

**Causes**:
1. Editing wrong .mcp.json file
2. JSON syntax error
3. Need to restart Claude Code (one-time initial setup)

**Solutions**:

1. **Check which .mcp.json is being read**:
   ```bash
   python3 -c "from mcp_client.discovery import MCPDiscovery; print(MCPDiscovery().mcp_json_path)"
   ```

2. **Validate JSON syntax**:
   ```bash
   python3 -m json.tool < ~/.lmstudio/mcp.json
   ```
   Should output formatted JSON without errors

3. **For initial setup**: Restart Claude Code ONCE to load hot reload code

4. **After initial setup**: No restart needed! Just add MCP to .mcp.json and use immediately

---

## Autonomous Execution Issues

### Issue: "Max rounds reached without final answer"

**Symptoms**:
```
Error: Max rounds (100) reached without final answer. Task may be too complex or LLM needs more rounds.
```

**Causes**:
1. Task too complex for rounds limit
2. LLM getting stuck in loop
3. Task description unclear

**Solutions**:

1. **Increase max_rounds**:
   ```python
   autonomous_with_mcp(
       "filesystem",
       "complex task",
       max_rounds=500  // Increase from default
   )
   ```

2. **Simplify task**:
   ```python
   # Instead of:
   "Analyze entire codebase and create comprehensive docs"

   # Break into smaller tasks:
   "Read all Python files in tools/ directory"
   "For each file, extract function names and descriptions"
   "Create summary.md with the extracted information"
   ```

3. **Make task description more specific**:
   ```python
   # Vague:
   "Check files"

   # Specific:
   "Read README.md and count the number of features listed"
   ```

---

### Issue: "Tool execution failed"

**Symptoms**:
```
Error executing tool 'read_file': File not found: /path/to/file.txt
```

**Causes**:
1. File/path doesn't exist
2. Permission denied
3. Wrong working directory
4. Path contains special characters

**Solutions**:

1. **Verify file exists**:
   ```bash
   ls -la /path/to/file.txt
   ```

2. **Check permissions**:
   ```bash
   ls -l /path/to/file.txt
   # Should show read permissions
   ```

3. **Specify working directory**:
   ```python
   autonomous_with_mcp(
       "filesystem",
       "read config.json",
       working_directory="/absolute/path/to/project"
   )
   ```

4. **Use absolute paths** in task descriptions:
   ```python
   # Good
   "Read /home/user/project/README.md"

   # May fail if working directory is wrong
   "Read README.md"
   ```

---

## Performance Issues

### Issue: "Responses are very slow"

**Causes**:
1. Model too large for hardware
2. LM Studio settings
3. Too many concurrent operations

**Solutions**:

1. **Use faster model**:
   - Try smaller models (7B instead of 32B)
   - Use quantized models (Q4 instead of FP16)

2. **Adjust LM Studio settings**:
   - Increase context length
   - Adjust batch size
   - Enable GPU acceleration

3. **Reduce max_tokens**:
   ```python
   autonomous_with_mcp(
       "filesystem",
       "task",
       max_tokens=2048  // Reduce from default 4096
   )
   ```

---

### Issue: "High memory usage"

**Causes**:
1. Model too large
2. Large context length
3. Multiple concurrent sessions

**Solutions**:

1. **Use smaller model**:
   - 7B or 13B instead of 32B+
   - Quantized versions (Q4, Q5)

2. **Reduce context length** in LM Studio

3. **Close unused models** in LM Studio

---

## Configuration Issues

### Issue: "Environment variables not recognized"

**Symptoms**: Settings in `"env"` section of .mcp.json not applied

**Solutions**:

1. **Verify .mcp.json format**:
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

2. **Restart Claude Code** after changing .mcp.json env vars

3. **Set system environment variables** as fallback:
   ```bash
   export LMSTUDIO_HOST=localhost
   export LMSTUDIO_PORT=1234
   ```

---

## Test Failures

### Issue: "Tests fail with connection errors"

**Solution**:

1. **Ensure LM Studio is running** with model loaded:
   ```bash
   curl http://localhost:1234/v1/models
   ```

2. **Run tests individually** to isolate issues:
   ```bash
   python3 test_lmstudio_integration.py
   python3 test_dynamic_discovery.py
   python3 test_autonomous_tools.py
   ```

3. **Check test logs** for specific error messages

---

## GitHub MCP Issues

### Issue: "GitHub authentication failed"

**Symptoms**:
```
Error: GitHub API authentication failed
```

**Cause**: Missing or invalid GitHub personal access token

**Solutions**:

1. **Set GitHub token**:
   ```json
   {
     "mcpServers": {
       "github": {
         "env": {
           "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_your_token_here"
         }
       }
     }
   }
   ```

2. **Create GitHub token**:
   - Go to GitHub Settings → Developer settings → Personal access tokens
   - Generate new token with appropriate scopes
   - Copy token to .mcp.json

3. **Verify token**:
   ```bash
   curl -H "Authorization: token ghp_your_token" https://api.github.com/user
   ```

---

## SQLite MCP Issues

### Issue: "Database locked"

**Cause**: Multiple connections to SQLite database

**Solution**:

```python
# Use separate database files for testing
autonomous_with_mcp(
    "sqlite",
    "Create table test",
    # SQLite will handle locking automatically
)
```

---

## Common Error Messages

### "Module not found: mcp"

**Cause**: Missing dependencies

**Solution**:
```bash
pip install -r requirements.txt
```

---

### "Python version mismatch"

**Cause**: Python < 3.9

**Solution**:
```bash
python3 --version  # Should be 3.9+
# If not, install Python 3.9 or newer
```

---

### "Port already in use"

**Cause**: Another process using LM Studio port

**Solution**:

1. **Find process using port**:
   ```bash
   lsof -i :1234
   ```

2. **Kill process or change port**:
   ```json
   {
     "env": {
       "LMSTUDIO_PORT": "5678"  // Use different port
     }
   }
   ```

---

## Debug Mode

### Enable verbose logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

This will show:
- MCP connections
- Tool calls
- LLM requests/responses
- Error details

---

## Getting Help

If issues persist:

1. **Check documentation**:
   - [Quick Start](QUICKSTART.md)
   - [Architecture](ARCHITECTURE.md)
   - [API Reference](API_REFERENCE.md)

2. **Search existing issues**: [GitHub Issues](https://github.com/your-username/lmstudio-bridge-enhanced/issues)

3. **Create new issue** with:
   - Error message (full output)
   - Steps to reproduce
   - Environment details (OS, Python version, LM Studio version)
   - .mcp.json configuration (redact sensitive data!)

4. **Community support**: [GitHub Discussions](https://github.com/your-username/lmstudio-bridge-enhanced/discussions)

---

## Useful Commands

```bash
# System information
python3 --version
node --version
npx --version

# LM Studio status
curl http://localhost:1234/v1/models

# MCP discovery
python3 -c "from mcp_client.discovery import MCPDiscovery; print(MCPDiscovery().mcp_json_path)"
python3 -c "from mcp_client.discovery import MCPDiscovery; print(MCPDiscovery().list_available_mcps())"

# Validate JSON
python3 -m json.tool < ~/.lmstudio/mcp.json

# Run tests
python3 test_lmstudio_integration.py
python3 test_dynamic_discovery.py
python3 test_autonomous_tools.py

# Performance benchmark
python3 benchmark_hot_reload.py
```

---

**Still having issues?** Open an issue with detailed information and we'll help you out!
