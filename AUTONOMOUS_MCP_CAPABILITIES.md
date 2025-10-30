# Autonomous MCP Capabilities

## Overview

The lmstudio-bridge-enhanced MCP server now provides **dedicated autonomous functions for each MCP**, allowing your local LLM to autonomously use tools from multiple battle-tested MCP servers.

### Architecture

Each MCP gets its own autonomous function:
- **`autonomous_filesystem_full`** - File system operations
- **`autonomous_memory_full`** - Knowledge graph operations (NEW)
- **`autonomous_fetch_full`** - Web content fetching (NEW)
- **`autonomous_github_full`** - GitHub operations (NEW)
- **`autonomous_persistent_session`** - Multi-task filesystem sessions

This architecture keeps functions focused and maintainable while giving Claude the flexibility to choose the right tool for each task.

---

## Available Autonomous Functions

### 1. autonomous_filesystem_full

**Purpose**: File system operations across single or multiple directories

**MCP Tools Exposed** (14 tools):
- `read_text_file`, `read_media_file`, `read_multiple_files`
- `write_file`, `edit_file`
- `create_directory`, `list_directory`, `directory_tree`
- `move_file`, `search_files`, `get_file_info`
- `list_allowed_directories`

**Parameters**:
- `task` (required): Task description for local LLM
- `working_directory` (optional): Single directory or list of directories (default: current project)
- `max_rounds` (optional): Maximum autonomous loop rounds (default: 10000)
- `max_tokens` (optional): Maximum tokens per LLM response (default: "auto")

**Use Cases**:
- Search for files across projects
- Read and analyze code
- Create/edit files and directories
- Organize project structures
- Extract information from multiple files

**Examples**:
```python
# Simple file search
autonomous_filesystem_full("Search for all Python files and list them")

# Multi-directory analysis
autonomous_filesystem_full(
    "Find all TODO comments across both projects",
    working_directory=["/project1", "/project2"]
)

# Complex task with custom limits
autonomous_filesystem_full(
    "Analyze entire codebase and create documentation",
    max_rounds=500,
    max_tokens=8192
)
```

---

### 2. autonomous_memory_full ⭐ NEW

**Purpose**: Knowledge graph operations for building and querying persistent memory

**MCP Tools Exposed** (9 tools):
- `create_entities` - Create knowledge entities with observations
- `create_relations` - Link entities together
- `add_observations` - Add facts to existing entities
- `delete_entities`, `delete_observations`, `delete_relations`
- `read_graph` - View entire knowledge graph
- `search_nodes` - Search by query
- `open_nodes` - Get specific entities

**Parameters**:
- `task` (required): Task description for local LLM
- `max_rounds` (optional): Maximum autonomous loop rounds (default: 100)
- `max_tokens` (optional): Maximum tokens per LLM response (default: "auto")

**Use Cases**:
- Build knowledge graphs from documentation
- Track relationships between concepts
- Create project context databases
- Search and query knowledge
- Maintain learning and research notes

**Examples**:
```python
# Create knowledge graph
autonomous_memory_full(
    "Create entities for Python, FastMCP, and MCP, then link them with 'uses' relations"
)

# Search knowledge
autonomous_memory_full(
    "Search for all entities related to 'MCP development'"
)

# Update knowledge
autonomous_memory_full(
    "Add observation to Python entity: 'supports async/await'"
)

# Build project knowledge
autonomous_memory_full(
    "Read the README and create entities for all mentioned technologies, linking them appropriately"
)
```

---

### 3. autonomous_fetch_full ⭐ NEW

**Purpose**: Web content fetching and analysis

**MCP Tools Exposed** (1 tool):
- `fetch` - Retrieve web content and convert to markdown

**Parameters**:
- `task` (required): Task description for local LLM
- `max_rounds` (optional): Maximum autonomous loop rounds (default: 100)
- `max_tokens` (optional): Maximum tokens per LLM response (default: "auto")

**Use Cases**:
- Fetch and analyze web documentation
- Compare content from multiple sites
- Extract information from online resources
- Download and process web content
- Research online documentation

**Examples**:
```python
# Fetch and analyze
autonomous_fetch_full(
    "Fetch https://modelcontextprotocol.io and summarize the main concepts"
)

# Compare documentation
autonomous_fetch_full(
    "Fetch documentation from both FastMCP and official MCP sites, then compare their features"
)

# Extract specific info
autonomous_fetch_full(
    "Fetch Python asyncio docs and extract the key concepts for async/await"
)

# Research and summarize
autonomous_fetch_full(
    "Fetch the top 3 MCP server examples from GitHub and summarize their implementations"
)
```

**Note**: Requires `mcp-server-fetch` to be installed and configured in `.mcp.json`

---

### 4. autonomous_github_full ⭐ NEW

**Purpose**: GitHub operations for repository management, issues, and PRs

**MCP Tools Exposed** (20+ tools):
- Repository management (create, fork, search)
- File operations (read, create, update, push)
- Branch operations (create, list)
- Issue management (create, list, update, comment)
- Pull request management (create, list, review, merge)
- Search (code, issues, repositories, users)

**Parameters**:
- `task` (required): Task description for local LLM
- `github_token` (optional): GitHub PAT (uses `GITHUB_PERSONAL_ACCESS_TOKEN` env var if not provided)
- `max_rounds` (optional): Maximum autonomous loop rounds (default: 100)
- `max_tokens` (optional): Maximum tokens per LLM response (default: "auto")

**Use Cases**:
- Search and analyze repositories
- Create and manage issues
- Work with pull requests
- Read and modify repository files
- Automate GitHub workflows

**Examples**:
```python
# Search repositories
autonomous_github_full(
    "Search for MCP server repositories and list the top 5 with descriptions"
)

# Create issue
autonomous_github_full(
    "Create an issue in ahmedmaged/my-repo about adding comprehensive tests"
)

# PR analysis
autonomous_github_full(
    "List all open PRs in ahmedmaged/my-repo and summarize their status"
)

# File operations
autonomous_github_full(
    "Read the README.md from ahmedmaged/my-repo and create a summary"
)

# Research
autonomous_github_full(
    "Search for Python MCP servers, analyze the top 3, and compare their features"
)
```

**Note**: Requires `GITHUB_PERSONAL_ACCESS_TOKEN` environment variable to be set

---

### 5. autonomous_persistent_session

**Purpose**: Multi-task execution in a single filesystem session with dynamic directory updates

**Features**:
- Run multiple tasks in ONE session (no reconnect overhead)
- Change working directories DYNAMICALLY between tasks
- Add/remove directories mid-session
- Implements MCP Roots Protocol

**Parameters**:
- `tasks` (required): List of task strings or dicts with optional `working_directory`
- `initial_directory` (optional): Initial working directory/directories
- `max_rounds` (optional): Maximum rounds per task (default: 10000)
- `max_tokens` (optional): Maximum tokens per response (default: "auto")

**Use Cases**:
- Multi-step workflows across projects
- Complex analysis requiring directory changes
- Batch processing of multiple tasks
- Performance-critical operations (avoids reconnection overhead)

**Examples**:
```python
# Simple multi-task
autonomous_persistent_session([
    "Read README.md",
    "Find all Python files",
    "Create summary.txt"
])

# Dynamic directory changes
autonomous_persistent_session([
    {"task": "Read config.json"},
    {
        "task": "Find all TODO comments",
        "working_directory": "/other/project"  # Switch directory!
    },
    {
        "task": "Compare implementations",
        "working_directory": ["/proj1", "/proj2"]  # Multiple directories!
    }
])
```

---

## Configuration Requirements

### 1. LM Studio Running

All autonomous functions require LM Studio to be running with a loaded model:

```bash
# Check if LM Studio is accessible
curl http://localhost:1234/v1/models
```

### 2. MCP Server Configuration

Add required MCPs to your `.mcp.json`:

```json
{
  "mcpServers": {
    "memory": {
      "disabled": false,
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"]
    },
    "fetch": {
      "disabled": false,
      "command": "uvx",
      "args": ["mcp-server-fetch"]
    },
    "lmstudio-bridge-enhanced_v2": {
      "disabled": false,
      "command": "python3",
      "args": ["/path/to/lmstudio-bridge-enhanced/main.py"],
      "env": {
        "LMSTUDIO_HOST": "localhost",
        "LMSTUDIO_PORT": "1234"
      }
    }
  }
}
```

### 3. GitHub Token (for GitHub functions)

Set environment variable for GitHub operations:

```bash
export GITHUB_PERSONAL_ACCESS_TOKEN="your_token_here"
```

Or pass directly to the function:

```python
autonomous_github_full(
    "Search repositories",
    github_token="your_token_here"
)
```

---

## Performance Considerations

### Token Limits

- **"auto" mode**: Uses 4096 tokens (safe default for most models)
- **Custom limits**: Specify manually if your model supports more (e.g., `max_tokens=8192`)
- LM Studio API doesn't expose model's max context length, so manual tuning may be needed

### Round Limits

- **Filesystem operations**: Default 10000 rounds (essentially unlimited for most tasks)
- **Other MCPs**: Default 100 rounds (sufficient for most operations)
- Increase for complex multi-step tasks

### Connection Overhead

- **Single tasks**: Use dedicated functions (`autonomous_filesystem_full`, etc.)
- **Multiple tasks**: Use `autonomous_persistent_session` to avoid reconnection overhead

---

## Error Handling

All autonomous functions include comprehensive error handling:

1. **Validation Errors**: Invalid parameters are caught and reported clearly
2. **Connection Errors**: MCP connection failures are logged with details
3. **Tool Execution Errors**: Individual tool failures don't crash the entire session
4. **Timeout Handling**: Long-running operations have configurable timeouts
5. **Round Limits**: Prevents infinite loops with max_rounds parameter

Example error output:
```
Error during memory execution: Connection to memory MCP failed
Traceback:
  File "tools/autonomous.py", line 403, in autonomous_memory_full
    connection = MCPConnection(command="npx", args=["-y", "@modelcontextprotocol/server-memory"])
  ...
ConnectionError: Failed to connect to MCP server
```

---

## Best Practices

### 1. Choose the Right Function

- **File operations** → `autonomous_filesystem_full`
- **Knowledge graphs** → `autonomous_memory_full`
- **Web content** → `autonomous_fetch_full`
- **GitHub operations** → `autonomous_github_full`
- **Multi-task workflows** → `autonomous_persistent_session`

### 2. Set Appropriate Limits

```python
# Simple tasks - use defaults
autonomous_memory_full("Create entity for Python")

# Complex tasks - increase limits
autonomous_filesystem_full(
    "Analyze entire codebase",
    max_rounds=500,
    max_tokens=8192
)
```

### 3. Use Persistent Sessions for Performance

```python
# ❌ Slow - 3 separate connections
autonomous_filesystem_full("Task 1")
autonomous_filesystem_full("Task 2")
autonomous_filesystem_full("Task 3")

# ✅ Fast - 1 connection, 3 tasks
autonomous_persistent_session([
    "Task 1",
    "Task 2",
    "Task 3"
])
```

### 4. Provide Clear Task Descriptions

```python
# ❌ Vague
autonomous_memory_full("Do something with Python")

# ✅ Clear
autonomous_memory_full(
    "Create an entity named 'Python' with entity type 'programming_language' "
    "and add observations: 'supports async/await', 'dynamic typing', 'interpreted'"
)
```

---

## Troubleshooting

### Function Not Available

**Problem**: Function not showing in Claude Code

**Solutions**:
1. Restart Claude Code to reload MCP configuration
2. Check MCP server logs for initialization errors
3. Verify function is registered in `tools/autonomous.py`

### Connection Failures

**Problem**: "Failed to connect to MCP server"

**Solutions**:
1. Verify MCP server package is installed (`uvx mcp-server-fetch`, `npx -y @modelcontextprotocol/server-memory`)
2. Check MCP configuration in `.mcp.json`
3. Ensure no conflicting MCP servers running
4. Check system logs for detailed error messages

### LM Studio Issues

**Problem**: "Connection refused to localhost:1234"

**Solutions**:
1. Start LM Studio and load a model
2. Verify LM Studio is listening on port 1234
3. Check firewall settings
4. Test with `curl http://localhost:1234/v1/models`

### GitHub Authentication

**Problem**: "GitHub API authentication failed"

**Solutions**:
1. Set `GITHUB_PERSONAL_ACCESS_TOKEN` environment variable
2. Verify token has required permissions (repo, issues, etc.)
3. Pass token directly to function if environment variable not available
4. Check token hasn't expired

### Performance Issues

**Problem**: Slow execution or timeouts

**Solutions**:
1. Reduce `max_tokens` for faster responses
2. Use persistent sessions for multiple tasks
3. Increase timeout in LLM client configuration
4. Check network connectivity for fetch/GitHub operations

---

## Examples: Real-World Workflows

### Workflow 1: Research and Document

```python
# Step 1: Fetch documentation from web
autonomous_fetch_full(
    "Fetch https://modelcontextprotocol.io and extract all key concepts"
)

# Step 2: Store knowledge in memory
autonomous_memory_full(
    "Create entities for MCP, Resources, Tools, and Prompts, "
    "then link them with appropriate relations based on the fetched documentation"
)

# Step 3: Create local documentation
autonomous_filesystem_full(
    "Create a file named 'MCP_SUMMARY.md' with a comprehensive summary "
    "of MCP concepts organized by category"
)
```

### Workflow 2: GitHub Repository Analysis

```python
# Step 1: Search repositories
autonomous_github_full(
    "Search for MCP server repositories and identify the top 5 most starred"
)

# Step 2: Analyze code
autonomous_github_full(
    "For each of the top 5 repositories, read the README.md "
    "and main implementation file, then summarize the features"
)

# Step 3: Create comparison
autonomous_filesystem_full(
    "Create a file 'MCP_SERVER_COMPARISON.md' with a table comparing "
    "the features, stars, and implementation approaches of the 5 servers"
)
```

### Workflow 3: Knowledge Graph Building

```python
# Step 1: Read local documentation
autonomous_filesystem_full(
    "Read all markdown files in the docs/ directory"
)

# Step 2: Build knowledge graph
autonomous_memory_full(
    "Create entities for all technologies, tools, and concepts mentioned "
    "in the documentation, then create relations showing how they connect"
)

# Step 3: Query knowledge
autonomous_memory_full(
    "Search for all entities related to 'async programming' and list "
    "their observations and relationships"
)
```

---

## Architecture Details

### How It Works

1. **Claude calls autonomous function** via MCP
2. **Function connects to target MCP** (memory, fetch, GitHub, etc.)
3. **Discovers available tools** from the target MCP
4. **Converts tools to OpenAI format** for LLM consumption
5. **Starts autonomous loop**:
   - LLM receives task + available tools
   - LLM calls tools as needed
   - Tools execute via real MCP
   - Results feed back to LLM
   - Loop continues until task complete or max_rounds reached
6. **Returns final answer** to Claude

### Connection Flow

```
Claude Code (Main LLM)
    ↓
lmstudio-bridge-enhanced MCP (Orchestrator)
    ↓
Local LM Studio Model (Autonomous Worker)
    ↓
Target MCP (memory/fetch/github/filesystem)
    ↓
Actual Operations (knowledge graph/web/GitHub/files)
```

### Security Model

- **Filesystem**: Directory validation with blocked system paths
- **GitHub**: Token-based authentication (user-provided or env var)
- **Fetch**: No authentication (public web content only)
- **Memory**: Local storage (no external connections)

---

## Future Enhancements

Planned features for future versions:

1. **Multi-MCP Functions**: Execute tasks using multiple MCPs simultaneously
2. **Streaming Responses**: Real-time progress updates during autonomous execution
3. **Tool Prioritization**: Suggest which autonomous function to use for each task
4. **Error Recovery**: Automatic retry and fallback strategies
5. **Session Persistence**: Save and resume autonomous sessions
6. **Performance Metrics**: Track token usage, round counts, and execution times
7. **Custom MCP Support**: Easy registration of user-created MCPs

---

## Version History

### v2.0 (Current)
- ✅ Added `autonomous_memory_full` for knowledge graph operations
- ✅ Added `autonomous_fetch_full` for web content fetching
- ✅ Added `autonomous_github_full` for GitHub operations
- ✅ Comprehensive error handling and logging
- ✅ Documentation and examples

### v1.0
- ✅ Initial `autonomous_filesystem_full` implementation
- ✅ Basic autonomous execution loop
- ✅ MCP connection and tool discovery
- ✅ OpenAI format conversion

---

## Contributing

To add support for additional MCPs:

1. Create new method in `AutonomousExecutionTools` class
2. Follow the pattern of existing functions
3. Register the function in `register_autonomous_tools()`
4. Add documentation and examples
5. Test thoroughly with the target MCP

Example template:
```python
async def autonomous_YOUR_MCP_full(
    self,
    task: str,
    max_rounds: int = 100,
    max_tokens: Union[int, str] = "auto"
) -> str:
    """Your MCP autonomous execution."""
    # Implementation following existing patterns
```

---

## Support

For issues, questions, or contributions:
- GitHub Issues: Create issue in your repository
- Documentation: See main README.md
- MCP Specs: https://modelcontextprotocol.io

---

**Last Updated**: October 30, 2025
**Version**: 2.0
**Author**: Ahmed Maged
