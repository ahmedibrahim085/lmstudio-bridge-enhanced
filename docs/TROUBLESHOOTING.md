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

## Multi-Model Issues ✨ NEW

### Issue: "Model not found"

**Symptoms**:
```
Error: Model 'qwen/qwen3-coder' not found.
Available models: mistralai/magistral-small-2509, deepseek/deepseek-coder-33b
```

**Causes**:
1. Model not loaded in LM Studio
2. Typo in model name
3. Wrong model ID format

**Solutions**:

1. **Load model in LM Studio**:
   - Open LM Studio
   - Go to "My Models" or search for model
   - Click "Load" button
   - Wait for loading to complete (progress bar reaches 100%)
   - Verify with: `list_models()`

2. **Use exact model name**:
   ```python
   # Check available models first
   list_models()
   # Returns: Available models (2):
   #   1. qwen/qwen3-coder-30b
   #   2. mistralai/magistral-small-2509

   # Copy exact name from output
   autonomous_with_mcp(
       "filesystem",
       "task",
       model="qwen/qwen3-coder-30b"  # Must match exactly!
   )
   ```

3. **Verify model ID format**:
   ```python
   # Correct format: organization/model-name
   ✅ "qwen/qwen3-coder-30b"
   ✅ "mistralai/magistral-small-2509"
   ✅ "deepseek/deepseek-coder-33b"

   # Wrong format:
   ❌ "qwen3-coder"           # Missing organization
   ❌ "Qwen/Qwen3-Coder-30B"  # Wrong capitalization
   ❌ "qwen-coder"            # Incomplete name
   ```

---

### Issue: "Model parameter ignored"

**Symptoms**: Task uses default model instead of specified model

**Causes**:
1. Using old version of lmstudio-bridge-enhanced (< v2.0.0)
2. Model parameter not specified correctly
3. Positional argument instead of named parameter

**Solutions**:

1. **Update to v2.0.0+**:
   ```bash
   cd lmstudio-bridge-enhanced
   git pull
   pip install -r requirements.txt --upgrade
   ```

2. **Use named parameter**:
   ```python
   ✅ Correct:
   autonomous_with_mcp(
       mcp_name="filesystem",
       task="task description",
       model="qwen/qwen3-coder-30b"  # Named parameter
   )

   ❌ Wrong:
   autonomous_with_mcp(
       "filesystem",
       "task description",
       "qwen/qwen3-coder-30b"  # Positional won't work
   )
   ```

3. **Check version**:
   ```python
   # In Python
   import lmstudio_bridge
   print(lmstudio_bridge.__version__)  # Should be >= 2.0.0
   ```

---

### Issue: "Wrong model used in task"

**Symptoms**: Different model used than specified

**Debugging steps**:

1. **Enable logging**:
   ```python
   import logging
   logging.basicConfig(level=logging.INFO)

   autonomous_with_mcp(
       "filesystem",
       "task",
       model="qwen/qwen3-coder-30b"
   )
   # Check logs for: "Using model: qwen/qwen3-coder-30b"
   ```

2. **Verify model loaded**:
   ```python
   # Check LM Studio has model loaded
   list_models()
   # Should include your specified model
   ```

3. **Test model directly**:
   ```python
   # Test model with chat_completion
   chat_completion(
       prompt="Test",
       model="qwen/qwen3-coder-30b"
   )
   # Should work without error
   ```

**Solutions**:
- Restart LM Studio
- Unload and reload model
- Check LM Studio logs for model switching issues
- Verify model name spelling

---

### Issue: "Model validation slow"

**Symptoms**: Noticeable delay before task starts

**Explanation**: First validation call fetches model list from LM Studio (~100-200ms)

**Solutions**:

1. **Normal behavior**: First call is slower, subsequent calls are cached (< 0.1ms)
   ```python
   # First call: ~100ms validation
   result1 = autonomous_with_mcp("filesystem", "task1", model="...")

   # Subsequent calls: < 0.1ms (cached for 60 seconds)
   result2 = autonomous_with_mcp("filesystem", "task2", model="...")
   ```

2. **If consistently slow**:
   - Check LM Studio API response time: `curl http://localhost:1234/v1/models`
   - Restart LM Studio
   - Reduce number of loaded models

3. **Bypass validation** (not recommended):
   ```python
   # Use default model (no validation)
   autonomous_with_mcp("filesystem", "task")  # No model parameter
   ```

---

### Issue: "Which model should I use?"

**Quick Decision Tree**:

```
What type of task?
├─ Code generation/refactoring/testing
│  └─ Use: qwen/qwen3-coder-30b or deepseek/deepseek-coder-33b
├─ Complex analysis/planning/reasoning
│  └─ Use: mistralai/magistral-small-2509 or qwen/qwen3-thinking-small-2509
├─ Simple file operations/documentation
│  └─ Use: Default (omit model parameter)
└─ Mixed task
   └─ Use: Default or try both and compare
```

**Model Selection Guide**:

| Task Type | Model | Why |
|-----------|-------|-----|
| Generate functions/classes | Qwen-Coder, DeepSeek-Coder | Specialized for code |
| Write unit tests | Qwen-Coder | Understands test patterns |
| Refactor code | Qwen-Coder | Code-aware refactoring |
| Analyze architecture | Magistral, Qwen-Thinking | Better reasoning |
| Identify design patterns | Magistral | Pattern recognition |
| Code review | Magistral | Comprehensive analysis |
| Simple file operations | Default | Sufficient for basic tasks |
| Documentation | Default | General capability |

**Still unsure?**
- Start with default (omit model parameter)
- If quality insufficient, try specialized model
- See [Multi-Model Guide](MULTI_MODEL_GUIDE.md) for detailed selection strategy

---

### Issue: "Can I use multiple models in one call?"

**Answer**: No, one model per tool call.

**Workaround**: Chain multiple calls with different models

```python
# Step 1: Analysis with reasoning model
analysis = autonomous_with_mcp(
    "filesystem",
    "Analyze codebase structure",
    model="mistralai/magistral-small-2509"
)

# Step 2: Implementation with coding model
implementation = autonomous_with_mcp(
    "filesystem",
    f"Implement based on analysis: {analysis}",
    model="qwen/qwen3-coder-30b"
)
```

See [Multi-Model Guide](MULTI_MODEL_GUIDE.md) for workflow patterns.

---

### Issue: "Model keeps unloading in LM Studio"

**Symptoms**: Model works initially, then fails with "model not found"

**Causes**:
1. LM Studio auto-unload settings
2. Memory pressure
3. Multiple models fighting for memory

**Solutions**:

1. **Disable auto-unload**:
   - LM Studio Settings → Memory Management
   - Disable "Auto-unload models"
   - Or increase unload timeout

2. **Monitor memory**:
   ```bash
   # Check available RAM
   free -h  # Linux
   vm_stat  # macOS
   ```

3. **Use one model at a time**:
   - Unload unused models before loading new one
   - Keep only actively used models loaded

4. **Use smaller models**:
   - Try 7B or 13B parameter models
   - Use quantized versions (Q4, Q5)

---

## Getting Help

If issues persist:

1. **Check documentation**:
   - [Quick Start](QUICKSTART.md)
   - [Architecture](ARCHITECTURE.md)
   - [API Reference](API_REFERENCE.md)
   - [Multi-Model Guide](MULTI_MODEL_GUIDE.md) ✨ NEW

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
