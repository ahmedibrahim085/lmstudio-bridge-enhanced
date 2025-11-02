# API Reference

Complete reference for all tools provided by LM Studio Bridge Enhanced.

---

## Tool Categories

- **[Core LM Studio Tools](#core-lm-studio-tools)** (7 tools) - Direct LM Studio HTTP API access
- **[LMS CLI Tools](#lms-cli-tools-optional)** (5 tools) - Advanced model management (optional)
- **[Dynamic Autonomous Tools](#dynamic-autonomous-tools)** (4 tools) - Dynamic MCP integration

**Total**: 16 tools (11 core + 5 optional LMS CLI)

---

## Core LM Studio Tools

Direct access to LM Studio API functions.

### 1. health_check

Check if LM Studio API is accessible.

**Parameters**: None

**Returns**: `str` - Status message

**Example**:
```
health_check()
# Returns: "LM Studio API is running at http://localhost:1234"
```

**Use case**: Verify LM Studio connection before attempting operations.

---

### 2. list_models

List all available models in LM Studio.

**Parameters**: None

**Returns**: `str` - Formatted list of models

**Example**:
```
list_models()
# Returns:
# Available models (3):
# 1. qwen/qwen-2.5-coder-32b-instruct
# 2. mistralai/magistral-small-2509
# 3. nomic-ai/nomic-embed-text-v1.5
```

**Use case**: Check which models are available before making completions.

---

### 3. get_current_model

Get the currently loaded model in LM Studio.

**Parameters**: None

**Returns**: `str` - Model name

**Example**:
```
get_current_model()
# Returns: "qwen/qwen-2.5-coder-32b-instruct"
```

**Use case**: Confirm which model will handle requests.

---

### 4. chat_completion

Generate a chat completion from the current LM Studio model.

**Parameters**:
- `prompt` (str, required): User's prompt
- `system_prompt` (str, optional): System instructions (default: "")
- `temperature` (float, optional): Randomness (0.0-1.0, default: 0.7)
- `max_tokens` (int, optional): Max tokens to generate (default: 1024)

**Returns**: `str` - Model's response

**Example**:
```
chat_completion(
    prompt="Explain async/await in Python",
    system_prompt="You are a Python expert",
    temperature=0.5,
    max_tokens=500
)
# Returns: Detailed explanation of async/await...
```

**Use case**: Simple chat completions without autonomous tool use.

---

### 5. text_completion

Generate raw text completion (non-chat format).

**Parameters**:
- `prompt` (str, required): Text prompt to complete
- `temperature` (float, optional): Randomness (0.0-2.0, default: 0.7)
- `max_tokens` (int, optional): Max tokens (default: 1024)
- `stop_sequences` (list[str], optional): Stop generation at these sequences

**Returns**: `str` - Completed text

**Example**:
```
text_completion(
    prompt="def fibonacci(n):\n    ",
    temperature=0.2,
    max_tokens=200,
    stop_sequences=["\n\n", "def "]
)
# Returns: Completed function code...
```

**Use case**: Code completion, text continuation, or simple Q&A without chat structure.

---

### 6. create_response

Create a stateful response using LM Studio's `/v1/responses` endpoint.

**Parameters**:
- `input_text` (str, required): User's input
- `previous_response_id` (str, optional): ID from previous response to continue conversation
- `stream` (bool, optional): Stream response (default: False)
- `model` (str, optional): Model to use (default: currently loaded model)

**Returns**: `str` - JSON response including `id` for future reference

**Example**:
```
# First message
create_response("Hi, my name is Ahmed")
# Returns: {"id": "resp_123", "content": "Hello Ahmed!", ...}

# Continue conversation
create_response(
    "What's my name?",
    previous_response_id="resp_123"
)
# Returns: {"id": "resp_124", "content": "Your name is Ahmed.", ...}
```

**Use case**: Multi-turn conversations without manually managing history.

---

### 7. generate_embeddings

Generate vector embeddings for text.

**Parameters**:
- `text` (str | list[str], required): Text or list of texts to embed
- `model` (str, optional): Embedding model (default: "default")

**Returns**: `str` - JSON with embeddings and usage info

**Example**:
```
# Single text
generate_embeddings("Python is a programming language")
# Returns: {"embeddings": [[0.123, -0.456, ...]], "usage": {...}}

# Batch
generate_embeddings([
    "Python programming",
    "JavaScript framework",
    "Database query"
])
# Returns: {"embeddings": [[...], [...], [...]], ...}
```

**Use case**: RAG systems, semantic search, text similarity, clustering.

---

## LMS CLI Tools (Optional)

**IMPORTANT**: These tools require LM Studio CLI (`lms`) to be installed.

### Why Use LMS CLI Tools?

**Problem Without LMS CLI**:
- Intermittent HTTP 404 errors when models auto-unload
- No control over model lifecycle
- Limited diagnostics when issues occur
- Models may unload during critical operations

**Solution With LMS CLI**:
- ✅ Prevents 404 errors by ensuring models stay loaded
- ✅ Proactive model management (load before operations)
- ✅ Better diagnostics (detailed model status)
- ✅ Production-grade reliability
- ✅ Self-healing capabilities (auto-load failed models)

**System works WITHOUT LMS CLI**, but these tools provide better reliability for production use!

### Installation

```bash
# Option 1: Homebrew (macOS/Linux - RECOMMENDED)
brew install lmstudio-ai/lms/lms

# Option 2: npm (All platforms)
npm install -g @lmstudio/lms

# Verify installation
lms --version
```

**Documentation**: https://github.com/lmstudio-ai/lms

---

### 1. lms_list_loaded_models

List all currently loaded models with detailed information.

**Parameters**: None

**Returns**: `dict` with:
- `success` (bool): Whether operation succeeded
- `models` (list): List of model details (if successful)
  - `identifier` (str): Model ID (e.g., "qwen/qwen3-coder-30b")
  - `status` (str): Model status ("loaded", "idle", or "loading")
  - `sizeBytes` (int): Model size in bytes
  - `memoryUsageBytes` (int): Current memory usage
- `count` (int): Number of loaded models
- `totalMemoryBytes` (int): Total memory used by all models
- `totalMemoryGB` (float): Total memory in GB
- `error` (str): Error message (if failed)
- `installInstructions` (str): How to install LMS CLI (if not installed)

**Example**:
```python
lms_list_loaded_models()
# Returns:
# {
#   "success": true,
#   "models": [
#     {
#       "identifier": "qwen/qwen3-coder-30b",
#       "status": "loaded",
#       "sizeBytes": 19874906112,
#       "memoryUsageBytes": 19874906112
#     }
#   ],
#   "count": 1,
#   "totalMemoryGB": 18.5,
#   "summary": "Found 1 loaded models using 18.5GB memory"
# }
```

**Use cases**:
- Check which models are available before operations
- Monitor total memory usage
- Optimize model selection based on what's already loaded
- Decide whether to load a new model or use existing one

---

### 2. lms_load_model

Load a specific model in LM Studio.

**Parameters**:
- `model_name` (str, required): Model identifier (e.g., "qwen/qwen3-coder-30b")
- `keep_loaded` (bool, optional): If True, prevents auto-unloading (default: True)

**Returns**: `dict` with:
- `success` (bool): Whether model loaded successfully
- `model` (str): Model identifier
- `keepLoaded` (bool): Whether model will be kept loaded
- `message` (str): Success/failure message
- `error` (str): Error details (if failed)

**Example**:
```python
# Load coder model and keep it loaded for workflow
lms_load_model("qwen/qwen3-coder-30b", keep_loaded=True)
# Returns:
# {
#   "success": true,
#   "model": "qwen/qwen3-coder-30b",
#   "keepLoaded": true,
#   "message": "Model 'qwen/qwen3-coder-30b' loaded successfully and kept loaded (will not auto-unload)"
# }
```

**Use cases**:
- Preload models before intensive operations
- Switch to different model for specific tasks
- Ensure model stays loaded during long workflows
- Prepare for multi-model workflows

---

### 3. lms_unload_model

Unload a model to free memory.

**Parameters**:
- `model_name` (str, required): Model identifier to unload

**Returns**: `dict` with:
- `success` (bool): Whether model unloaded successfully
- `model` (str): Model identifier
- `message` (str): Success/failure message
- `error` (str): Error details (if failed)

**Example**:
```python
# Free memory by unloading unused model
lms_unload_model("qwen/qwen3-4b-thinking-2507")
# Returns:
# {
#   "success": true,
#   "model": "qwen/qwen3-4b-thinking-2507",
#   "message": "Model 'qwen/qwen3-4b-thinking-2507' unloaded successfully"
# }
```

**Use cases**:
- Free memory after completing tasks
- Make room for larger models
- Clean up after multi-model workflows
- Optimize memory usage

---

### 4. lms_ensure_model_loaded ⭐ RECOMMENDED

Ensure a model is loaded, load if necessary (idempotent).

**This is the RECOMMENDED way to prevent 404 errors!**

Safe to call multiple times - only loads if needed.

**Parameters**:
- `model_name` (str, required): Model identifier to ensure is loaded

**Returns**: `dict` with:
- `success` (bool): Whether model is loaded (or was loaded)
- `model` (str): Model identifier
- `wasAlreadyLoaded` (bool): True if model was already loaded
- `message` (str): Status message
- `error` (str): Error details (if failed)

**Example**:
```python
# BEST PRACTICE: Ensure model loaded before operation
lms_ensure_model_loaded("qwen/qwen3-coder-30b")
# Returns (if already loaded):
# {
#   "success": true,
#   "model": "qwen/qwen3-coder-30b",
#   "wasAlreadyLoaded": true,
#   "message": "Model 'qwen/qwen3-coder-30b' is already loaded and ready"
# }

# Returns (if not loaded):
# {
#   "success": true,
#   "model": "qwen/qwen3-coder-30b",
#   "wasAlreadyLoaded": false,
#   "message": "Model 'qwen/qwen3-coder-30b' loaded successfully and kept loaded"
# }
```

**Use cases**:
- **PRIMARY**: Prevent 404 errors before operations
- Guarantee model availability
- Idempotent preloading (safe to call multiple times)
- Fail-safe pattern before autonomous execution

**Best practice workflow**:
```python
# 1. Ensure model loaded first
result = lms_ensure_model_loaded("qwen/qwen3-coder-30b")

if result["success"]:
    # 2. Now safe to run autonomous task
    autonomous_with_mcp(
        "filesystem",
        "analyze codebase",
        model="qwen/qwen3-coder-30b"
    )
```

---

### 5. lms_server_status

Get LM Studio server status and diagnostics.

**Parameters**: None

**Returns**: `dict` with:
- `success` (bool): Whether status retrieved successfully
- `serverRunning` (bool): Whether LM Studio server is running
- `status` (dict): Server status details (if available)
- `error` (str): Error message (if failed)

**Example**:
```python
# Check server health before running tasks
lms_server_status()
# Returns:
# {
#   "success": true,
#   "serverRunning": true,
#   "status": {...},
#   "message": "LM Studio server is running"
# }
```

**Use cases**:
- Check server health before operations
- Diagnose issues when failures occur
- Monitor server state
- Verify LM Studio is running properly

---

### LMS CLI Tools: When to Use

| Scenario | Recommended Tool | Why |
|----------|-----------------|-----|
| Before autonomous execution | `lms_ensure_model_loaded` | Prevents 404 errors |
| Check available models | `lms_list_loaded_models` | See what's already loaded |
| Preload for workflow | `lms_load_model` | Ensure model stays loaded |
| Free memory | `lms_unload_model` | Clean up after tasks |
| Diagnose issues | `lms_server_status` | Server health check |

### LMS CLI vs HTTP API Tools

| Feature | HTTP API Tools | LMS CLI Tools |
|---------|---------------|---------------|
| Model listing | `list_models` (basic) | `lms_list_loaded_models` (detailed) |
| Model loading | Auto (on first use) | `lms_load_model` (explicit) |
| Model status | Not available | `lms_list_loaded_models` (status field) |
| 404 prevention | Not available | `lms_ensure_model_loaded` |
| Memory management | Not available | `lms_unload_model` |
| Installation | None required | Requires `lms` CLI |
| Reliability | Good | Excellent |

**Recommendation**: Use LMS CLI tools for production deployments!

---

## Dynamic Autonomous Tools

Enable local LLM to autonomously use tools from ANY MCP.

### 1. autonomous_with_mcp

Execute task autonomously using tools from a SINGLE MCP.

**Parameters**:
- `mcp_name` (str, required): Name of MCP to use (from `.mcp.json`)
- `task` (str, required): Task description (1-10000 chars)
- `max_rounds` (int, optional): Max autonomous loop iterations (default: 10000)
- `max_tokens` (int | str, optional): Max tokens per LLM response (default: "auto" = 4096)
- `model` (str, optional): ✨ **NEW** - Specific model to use (default: None = use default model)

**Returns**: `str` - Final answer from local LLM

**Example**:
```
# Use default model
autonomous_with_mcp(
    mcp_name="filesystem",
    task="Find all Python files in tools/ and count lines of code",
    max_rounds=50,
    max_tokens=8192
)
# Returns: "Found 15 Python files with 3,456 total lines of code."

# Use specific model (multi-model support)
autonomous_with_mcp(
    mcp_name="filesystem",
    task="Analyze code structure and identify patterns",
    model="mistralai/magistral-small-2509"  # Use reasoning model
)

# Use coding model for implementation
autonomous_with_mcp(
    mcp_name="filesystem",
    task="Generate helper functions based on analysis",
    model="qwen/qwen3-coder-30b"  # Use coding model
)
```

**Available MCPs** (from your `.mcp.json`):
- `filesystem` - File operations
- `memory` - Knowledge graph
- `fetch` - Web content
- `github` - GitHub operations
- `sqlite` - Database operations
- ANY custom MCP you add!

**How it works**:
1. Connects to specified MCP
2. Discovers all available tools from that MCP
3. Passes tools to local LLM
4. Local LLM decides which tools to use and when
5. Executes tools autonomously
6. Returns final answer

---

### 2. autonomous_with_multiple_mcps

Execute task autonomously using tools from MULTIPLE MCPs simultaneously.

**Parameters**:
- `mcp_names` (list[str], required): List of MCP names to use
- `task` (str, required): Task description
- `max_rounds` (int, optional): Max iterations (default: 10000)
- `max_tokens` (int | str, optional): Max tokens (default: "auto")
- `model` (str, optional): ✨ **NEW** - Specific model to use (default: None = use default model)

**Returns**: `str` - Final answer from local LLM

**Example**:
```
# Use default model
autonomous_with_multiple_mcps(
    mcp_names=["filesystem", "memory"],
    task="Read all Python files in tools/ and create a knowledge graph of the codebase structure"
)
# Returns: "Created knowledge graph with 15 files, 47 classes, and 183 functions."

# Use specific model for multi-MCP task
autonomous_with_multiple_mcps(
    mcp_names=["filesystem", "fetch", "memory"],
    task="Read local docs, fetch online docs, compare and build knowledge graph",
    model="mistralai/magistral-small-2509"  # Reasoning model for complex analysis
)
```

**Multi-MCP examples**:
```python
# Filesystem + Memory
autonomous_with_multiple_mcps(
    ["filesystem", "memory"],
    "Analyze code and build knowledge graph"
)

# Filesystem + Fetch + Memory
autonomous_with_multiple_mcps(
    ["filesystem", "fetch", "memory"],
    "Read local docs, fetch online docs, compare them, and build knowledge graph"
)

# Filesystem + GitHub + Memory
autonomous_with_multiple_mcps(
    ["filesystem", "github", "memory"],
    "Analyze local repo, search GitHub for similar projects, create comparison graph"
)
```

**Tool namespacing**: Tools are prefixed with MCP name to avoid collisions:
- `filesystem__read_file`
- `filesystem__write_file`
- `memory__create_entities`
- `memory__read_graph`

---

### 3. autonomous_discover_and_execute

Execute task with ALL available MCPs discovered from `.mcp.json`.

**Parameters**:
- `task` (str, required): Task description
- `max_rounds` (int, optional): Max iterations (default: 10000)
- `max_tokens` (int | str, optional): Max tokens (default: "auto")
- `model` (str, optional): ✨ **NEW** - Specific model to use (default: None = use default model)

**Returns**: `str` - Final answer from local LLM

**Example**:
```
# Use default model with all MCPs
autonomous_discover_and_execute(
    task="Analyze my codebase, fetch relevant docs online, build a knowledge graph, and create comprehensive documentation"
)
# Local LLM automatically uses filesystem, fetch, and memory MCPs!

# Use specific model with all MCPs
autonomous_discover_and_execute(
    task="Comprehensive codebase analysis and documentation",
    model="qwen/qwen3-coder-30b"  # Use powerful coding model
)
```

**What it does**:
1. Discovers ALL enabled MCPs from `.mcp.json`
2. Connects to ALL of them
3. Discovers ALL tools from ALL MCPs
4. Gives local LLM access to EVERYTHING
5. Local LLM autonomously uses any tools needed

**Power**: Most flexible tool - LLM has access to all available tools!

**Note**: May attempt to connect to lmstudio-bridge itself (recursive connection). Prefer `autonomous_with_multiple_mcps` with specific MCP names if this is an issue.

---

### 4. list_available_mcps

List all MCPs discovered from `.mcp.json`.

**Parameters**: None

**Returns**: `str` - Formatted list of MCPs with details

**Example**:
```
list_available_mcps()
# Returns:
# Available MCPs (5):
#
# 1. filesystem
#    Command: npx -y @modelcontextprotocol/server-filesystem
#    Description: MCP server: @modelcontextprotocol/server-filesystem
#    Env vars: ALLOWED_DIRECTORIES
#
# 2. memory
#    Command: npx -y @modelcontextprotocol/server-memory
#    Description: MCP server: @modelcontextprotocol/server-memory
#
# 3. fetch
#    Command: npx -y mcp-server-fetch
#    Description: MCP server: mcp-server-fetch
#
# ...
#
# To use any of these MCPs, call:
#   autonomous_with_mcp(mcp_name='<name>', task='<task>')
#   autonomous_with_multiple_mcps(mcp_names=['<name1>', '<name2>'], task='<task>')
#   autonomous_discover_and_execute(task='<task>')  # Uses ALL MCPs!
```

**Use case**: Check which MCPs are available before calling autonomous tools.

---

## Parameter Details

### max_rounds

Controls how many autonomous loop iterations are allowed.

**Default**: 10000 (no artificial limit - let LLM work until done)

**Range**: 1 - unlimited

**Guidelines**:
- **Simple tasks**: Usually complete in 3-10 rounds
- **Medium tasks**: 20-50 rounds
- **Complex tasks**: 50-500 rounds
- **Very complex**: May need 500+ rounds

**Example usage**:
```python
# Default (recommended)
autonomous_with_mcp("filesystem", "task")  # max_rounds=10000

# Custom limit for simple task
autonomous_with_mcp("filesystem", "quick task", max_rounds=20)

# Higher limit for very complex task
autonomous_with_mcp("filesystem", "analyze entire codebase", max_rounds=5000)
```

**Philosophy**: No artificial limits - let the LLM work until the task is complete!

---

### max_tokens

Controls maximum tokens per LLM response.

**Default**: "auto" (uses 4096 tokens)

**Options**:
- `"auto"` - Uses default 4096 (safe for most models)
- `<integer>` - Manual override (e.g., 8192, 16384)

**Guidelines**:
- **4096**: Safe default for most models
- **8192**: For larger context models (32K+)
- **16384+**: For very large context models (128K+)

**Note**: LM Studio's API doesn't expose model's actual max_context_length, so you must manually specify if your model supports more than 4096.

**Example usage**:
```python
# Default (4096)
autonomous_with_mcp("filesystem", "task")

# Override for larger context model
autonomous_with_mcp("filesystem", "complex task", max_tokens=8192)

# Very large context
autonomous_with_mcp("filesystem", "analyze entire codebase", max_tokens=16384)
```

---

### model ✨ NEW

**Optional parameter for multi-model support** - Select specific LM Studio model for the task.

**Type**: `str | None`

**Default**: `None` (uses default model from config)

**Purpose**: Different models excel at different tasks:
- **Reasoning models** (Magistral, Qwen-Thinking) → Analysis, planning, complex problem-solving
- **Coding models** (Qwen-Coder, DeepSeek-Coder) → Code generation, refactoring, debugging
- **General models** → Balanced performance for mixed tasks

**How to use**:

1. **Check available models**:
```python
list_models()
# Returns: Available models (3):
# 1. qwen/qwen3-coder-30b
# 2. mistralai/magistral-small-2509
# 3. deepseek/deepseek-coder-33b
```

2. **Use specific model**:
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
    task="Generate unit tests for all functions in utils/",
    model="qwen/qwen3-coder-30b"
)

# Default model (omit parameter)
autonomous_with_mcp(
    mcp_name="filesystem",
    task="List Python files"
    # Uses default model - backward compatible!
)
```

3. **Error handling**:
```python
# Invalid model name
autonomous_with_mcp(
    mcp_name="filesystem",
    task="task",
    model="nonexistent-model"
)
# Returns: "Error: Model 'nonexistent-model' not found. Available: qwen/qwen3-coder-30b, mistralai/magistral-small-2509"
```

**Best practices**:
- ✅ Use model names exactly as shown by `list_models()`
- ✅ Match model to task type (reasoning vs coding vs general)
- ✅ Omit parameter for simple tasks (uses default)
- ✅ Load model in LM Studio before use
- ❌ Don't guess model names (they must be exact)
- ❌ Don't use for every task (default often sufficient)

**Model selection guide**:

| Task Type | Recommended Model | Why |
|-----------|------------------|-----|
| Code analysis, architecture review | Magistral, Qwen-Thinking | Better reasoning |
| Code generation, refactoring | Qwen-Coder, DeepSeek-Coder | Specialized for code |
| Testing, debugging | Qwen-Coder | Understands test patterns |
| Documentation | General models | Balanced capability |
| File operations | Default model | Simple tasks |

**Workflow example** (Multi-model pipeline):
```python
# Step 1: Reasoning model analyzes
analysis = autonomous_with_mcp(
    "filesystem",
    "Analyze project structure and identify missing tests",
    model="mistralai/magistral-small-2509"  # Reasoning
)

# Step 2: Coding model generates tests
tests = autonomous_with_mcp(
    "filesystem",
    f"Based on this analysis: {analysis}, generate missing unit tests",
    model="qwen/qwen3-coder-30b"  # Coding
)
```

**Backward compatibility**: Existing code without `model` parameter continues to work unchanged!

---

### task

Description of what the local LLM should do.

**Guidelines for effective task descriptions**:

✅ **DO**:
- Be specific: "Read setup.py and create requirements.txt with all dependencies"
- Include context: "Find Python files in tools/ directory (not tests/)"
- State expected output: "Create summary.md with descriptions of each file"
- Break complex tasks into steps: "First read files, then analyze, then create report"

❌ **DON'T**:
- Be vague: "Do something with files"
- Omit context: "Read files" (which files?)
- Assume knowledge: "Fix the bug" (what bug?)
- Use ambiguous terms: "Check the code" (check for what?)

**Examples**:

```python
# Good task descriptions
"Read README.md and summarize the key features in 3 bullet points"
"Find all TODO comments in Python files and create TODO.md with file locations"
"Count lines of code in tools/ directory, excluding comments and blank lines"
"Search for all imports of 'asyncio' and list which files use it"

# Bad task descriptions
"Check files"  # Too vague
"Read stuff"  # What stuff?
"Fix issues"  # What issues?
"Analyze"  # Analyze what?
```

---

## Error Handling

All tools return error messages as strings when errors occur:

```
"Error: MCP 'nonexistent' not found in .mcp.json. Available MCPs: filesystem, memory, fetch"

"Error: Could not connect to MCP server: Connection refused"

"Error: No tools available from MCP 'filesystem'. Check MCP server logs."

"Error: Max rounds (100) reached without final answer. Task may be too complex."

"Error executing tool 'read_file': File not found: /nonexistent/file.txt"
```

**Best practice**: Check for error messages starting with "Error:" in returned strings.

---

## Usage from Claude Code

### Method 1: Natural Language

```
Can you use autonomous_with_mcp with the filesystem MCP to find all Python files?
```

Claude will call:
```python
autonomous_with_mcp(
    mcp_name="filesystem",
    task="Find all Python files in the current directory and list them"
)
```

### Method 2: Explicit Tool Call

```
Call autonomous_with_mcp with mcp_name="memory" and task="Create entity for Python with observations about features"
```

### Method 3: Multiple Tools

```
Use these tools:
1. autonomous_with_mcp("filesystem", "Count Python files")
2. autonomous_with_mcp("memory", "Create entity 'ProjectStats' with file count")
```

---

## Environment Variables

Configure LM Studio connection:

```json
{
  "env": {
    "LMSTUDIO_HOST": "localhost",
    "LMSTUDIO_PORT": "1234",
    "MCP_JSON_PATH": "/custom/path/.mcp.json"
  }
}
```

**Variables**:
- `LMSTUDIO_HOST` - LM Studio host (default: "localhost")
- `LMSTUDIO_PORT` - LM Studio API port (default: "1234")
- `MCP_JSON_PATH` - Custom path to .mcp.json (optional)

---

## Rate Limits

**None!** Everything runs locally:
- Unlimited requests
- No API costs
- No rate limiting
- Full privacy

---

## Best Practices

### 1. Use Specific MCP Names

```python
# Good - explicit
autonomous_with_mcp("filesystem", "task")

# Less ideal - may connect to unnecessary MCPs
autonomous_discover_and_execute("task")
```

### 2. Set Appropriate max_rounds

```python
# Simple task
autonomous_with_mcp("filesystem", "read one file", max_rounds=10)

# Complex task
autonomous_with_mcp("filesystem", "analyze codebase", max_rounds=500)
```

### 3. Provide Clear Task Descriptions

```python
# Good
"Read README.md, extract the list of features, and count them"

# Bad
"Read and count"  # Count what?
```

### 4. Use Multi-MCP for Related Operations

```python
# Efficient - one session, multiple MCPs
autonomous_with_multiple_mcps(
    ["filesystem", "memory"],
    "Read files and build knowledge graph"
)

# Less efficient - two separate sessions
autonomous_with_mcp("filesystem", "read files")
autonomous_with_mcp("memory", "build graph")
```

---

## See Also

- **[Quick Start Guide](QUICKSTART.md)** - Get started quickly
- **[Architecture](ARCHITECTURE.md)** - How it works internally
- **[Troubleshooting](TROUBLESHOOTING.md)** - Common issues and solutions
