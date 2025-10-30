# API Reference

Complete reference for all tools provided by LM Studio Bridge Enhanced.

---

## Tool Categories

- **[Core LM Studio Tools](#core-lm-studio-tools)** (7 tools) - Direct LM Studio API access
- **[Dynamic Autonomous Tools](#dynamic-autonomous-tools)** (4 tools) - Dynamic MCP integration

**Total**: 11 tools

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

## Dynamic Autonomous Tools

Enable local LLM to autonomously use tools from ANY MCP.

### 1. autonomous_with_mcp

Execute task autonomously using tools from a SINGLE MCP.

**Parameters**:
- `mcp_name` (str, required): Name of MCP to use (from `.mcp.json`)
- `task` (str, required): Task description (1-10000 chars)
- `max_rounds` (int, optional): Max autonomous loop iterations (default: 10000)
- `max_tokens` (int | str, optional): Max tokens per LLM response (default: "auto" = 4096)

**Returns**: `str` - Final answer from local LLM

**Example**:
```
autonomous_with_mcp(
    mcp_name="filesystem",
    task="Find all Python files in tools/ and count lines of code",
    max_rounds=50,
    max_tokens=8192
)
# Returns: "Found 15 Python files with 3,456 total lines of code."
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

**Returns**: `str` - Final answer from local LLM

**Example**:
```
autonomous_with_multiple_mcps(
    mcp_names=["filesystem", "memory"],
    task="Read all Python files in tools/ and create a knowledge graph of the codebase structure"
)
# Returns: "Created knowledge graph with 15 files, 47 classes, and 183 functions."
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

**Returns**: `str` - Final answer from local LLM

**Example**:
```
autonomous_discover_and_execute(
    task="Analyze my codebase, fetch relevant docs online, build a knowledge graph, and create comprehensive documentation"
)
# Local LLM automatically uses filesystem, fetch, and memory MCPs!
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
