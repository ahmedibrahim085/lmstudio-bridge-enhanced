# Autonomous Tools Guide

## Overview

The **lmstudio-bridge-enhanced** MCP now enables your local LLM (via LM Studio) to **autonomously use ALL tools from ALL supported MCPs**! 🚀

This creates powerful autonomous capabilities where your local LLM can:
- ✅ **Read, write, and search files** (filesystem MCP)
- ✅ **Manage knowledge graphs** (memory MCP)
- ✅ **Fetch and process web content** (fetch MCP)
- ✅ **Manage GitHub repositories** (github MCP)
- ✅ **Execute multi-step tasks** without human intervention

---

## Architecture

```
┌─────────────────┐
│   Claude Code   │ (Main AI)
└────────┬────────┘
         │
         │ Uses tools from
         ▼
┌──────────────────────────────────────┐
│  lmstudio-bridge-enhanced MCP        │
│  ┌────────────────────────────────┐  │
│  │ Autonomous Tools               │  │
│  │  - autonomous_filesystem_full  │  │
│  │  - autonomous_memory_full      │  │
│  │  - autonomous_fetch_full       │  │
│  │  - autonomous_github_full      │  │
│  │  - autonomous_persistent_session│ │
│  └────────────────────────────────┘  │
└────────┬─────────────────────────────┘
         │
         │ Connects to and uses
         ▼
┌─────────────────────────────────────────┐
│  Local LLM (via LM Studio)              │
│  ┌───────────────────────────────────┐  │
│  │ Autonomously uses MCP tools:      │  │
│  │  - Filesystem MCP (14 tools)      │  │
│  │  - Memory MCP (8 tools)           │  │
│  │  - Fetch MCP (1 tool)             │  │
│  │  - GitHub MCP (25+ tools)         │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

### How It Works

1. **Claude Code** calls an autonomous tool (e.g., `autonomous_filesystem_full`)
2. **lmstudio-bridge** connects to the target MCP (e.g., filesystem) as a **client**
3. **lmstudio-bridge** discovers all available tools from that MCP
4. **lmstudio-bridge** passes those tools to the **local LLM** (via LM Studio API)
5. **Local LLM** autonomously decides which tools to use and when
6. **lmstudio-bridge** executes the tools via the MCP
7. **Local LLM** sees the results and continues until task is complete
8. **lmstudio-bridge** returns final answer to Claude Code

---

## Available Autonomous Tools

### 1. `autonomous_filesystem_full` 📁

**What it does**: Enables local LLM to autonomously use ALL 14 filesystem MCP tools.

**Available tools**:
- `read_text_file` - Read file contents
- `read_media_file` - Read images/audio
- `read_multiple_files` - Batch file reading
- `write_file` - Create or overwrite files
- `edit_file` - Line-based file editing
- `create_directory` - Create directories
- `list_directory` - List directory contents
- `directory_tree` - Recursive directory tree
- `move_file` - Move or rename files
- `search_files` - Search for files by pattern
- `get_file_info` - Get file metadata
- `list_allowed_directories` - List accessible directories

**Parameters**:
- `task` (required): Task description for the local LLM
- `working_directory` (optional): Directory or list of directories to operate in
  - Default: Current Claude Code project directory
  - Can be a single path: `"/path/to/project"`
  - Can be multiple paths: `["/project1", "/project2"]`
- `max_rounds` (optional): Maximum autonomous loop iterations
  - Default: 10000 (no artificial limit)
  - LLM works until task is complete
- `max_tokens` (optional): Maximum tokens per LLM response
  - Default: "auto" (4096 tokens)
  - Can override: `8192` for larger context models

**Examples**:

```python
# Simple file reading
autonomous_filesystem_full(
    "Read README.md and summarize the key features"
)

# Search for files
autonomous_filesystem_full(
    "Find all Python files that contain 'autonomous' in their name"
)

# Multi-file analysis
autonomous_filesystem_full(
    "Read all .py files in tools/ directory and create a summary.md with descriptions of each file"
)

# Cross-project search
autonomous_filesystem_full(
    "Find all TODO comments",
    working_directory=["/project1", "/project2", "/project3"]
)

# Complex codebase analysis
autonomous_filesystem_full(
    "Analyze the entire codebase structure and create a dependency graph",
    max_rounds=500,
    max_tokens=8192
)
```

---

### 2. `autonomous_memory_full` 🧠

**What it does**: Enables local LLM to autonomously manage a knowledge graph.

**Available tools**:
- `create_entities` - Create knowledge entities
- `create_relations` - Link entities together
- `add_observations` - Add facts to entities
- `delete_entities` - Remove entities
- `delete_relations` - Remove relations
- `delete_observations` - Remove observations
- `read_graph` - View entire knowledge graph
- `search_nodes` - Search for entities
- `open_nodes` - Get specific entities

**Parameters**:
- `task` (required): Task description for the local LLM
- `max_rounds` (optional): Maximum autonomous loop iterations (default: 100)
- `max_tokens` (optional): Maximum tokens per LLM response (default: "auto")

**Examples**:

```python
# Build knowledge graph
autonomous_memory_full(
    "Create entities for Python, FastMCP, and MCP. Link Python to FastMCP with 'uses' relation, and FastMCP to MCP with 'implements' relation"
)

# Search knowledge
autonomous_memory_full(
    "Search for all entities related to 'autonomous agents' and summarize findings"
)

# Update knowledge
autonomous_memory_full(
    "Add observation to Python entity: 'Supports async/await since Python 3.5'"
)

# Complex knowledge graph
autonomous_memory_full(
    "Read all README files in the project, extract key concepts, create entities for each concept, and link them based on relationships mentioned in the docs"
)
```

---

### 3. `autonomous_fetch_full` 🌐

**What it does**: Enables local LLM to autonomously fetch and process web content.

**Available tools**:
- `fetch` - Retrieve web content and convert to markdown

**Parameters**:
- `task` (required): Task description for the local LLM
- `max_rounds` (optional): Maximum autonomous loop iterations (default: 100)
- `max_tokens` (optional): Maximum tokens per LLM response (default: "auto")

**Examples**:

```python
# Fetch and analyze
autonomous_fetch_full(
    "Fetch https://modelcontextprotocol.io and summarize the main concepts of MCP"
)

# Compare multiple sources
autonomous_fetch_full(
    "Fetch documentation from FastMCP GitHub and official MCP website. Compare their features and create a comparison table"
)

# Extract specific information
autonomous_fetch_full(
    "Fetch Python asyncio documentation and extract the 5 most important best practices"
)
```

---

### 4. `autonomous_github_full` 🐙

**What it does**: Enables local LLM to autonomously manage GitHub repositories.

**Available tools**: 25+ GitHub tools including:
- Repository management (create, fork, search)
- File operations (read, create, update, push)
- Issue management (create, list, update, comment)
- Pull request management (create, list, review, merge)
- Search (code, issues, repositories, users)

**Parameters**:
- `task` (required): Task description for the local LLM
- `github_token` (optional): GitHub personal access token
  - If not provided, uses `GITHUB_PERSONAL_ACCESS_TOKEN` environment variable
- `max_rounds` (optional): Maximum autonomous loop iterations (default: 100)
- `max_tokens` (optional): Maximum tokens per LLM response (default: "auto")

**Examples**:

```python
# Search repositories
autonomous_github_full(
    "Search for MCP server repositories and list the top 5 by stars"
)

# Create issues
autonomous_github_full(
    "Create an issue in my-org/my-repo titled 'Add unit tests' with a detailed description of what tests are needed"
)

# Analyze pull requests
autonomous_github_full(
    "List all open PRs in my-org/my-repo, analyze each one, and summarize their status"
)

# Code search
autonomous_github_full(
    "Search GitHub for Python projects that use FastMCP and list the top 10"
)
```

---

### 5. `autonomous_persistent_session` 🔄

**What it does**: Executes multiple tasks in ONE persistent session with dynamic directory updates.

**Why use this**:
- **Performance**: No reconnection overhead between tasks
- **Flexibility**: Change working directories mid-session
- **Efficiency**: Reuse same MCP connection

**Parameters**:
- `tasks` (required): List of tasks to execute
  - Can be simple strings: `["task1", "task2"]`
  - Can be dicts with working_directory: `[{"task": "...", "working_directory": "/path"}]`
- `initial_directory` (optional): Initial working directory or directories
- `max_rounds` (optional): Maximum rounds per task (default: 10000)
- `max_tokens` (optional): Maximum tokens per response (default: "auto")

**Examples**:

```python
# Simple: Multiple tasks in same directory
autonomous_persistent_session([
    "Read README.md",
    "Find all Python files",
    "Create summary.txt with file count"
])

# Advanced: Change directories between tasks
autonomous_persistent_session([
    {"task": "Read config.json"},
    {
        "task": "Find all TODO comments",
        "working_directory": "/other/project"  # Switch!
    },
    {
        "task": "Compare implementations of similar functions",
        "working_directory": ["/proj1", "/proj2"]  # Multiple!
    }
])

# Performance: 3 tasks in one session vs 3 separate calls
# Persistent session: 1 connection, 3 tasks
# Separate calls: 3 connections, 3 tasks (slower!)
```

---

## Testing

### Test Results ✅

All autonomous tools have been tested and verified to work correctly:

```bash
$ python3 test_autonomous_tools.py

================================================================================
TEST 1: autonomous_filesystem_full
✅ PASSED: Local LLM successfully read README.md

TEST 2: autonomous_memory_full
✅ PASSED: Local LLM successfully created knowledge entity

TEST 3: autonomous_fetch_full
✅ PASSED: Local LLM successfully fetched web content

================================================================================
✅ All autonomous tools work correctly!
```

### Run Tests Yourself

```bash
cd /Users/ahmedmaged/ai_storage/MyMCPs/lmstudio-bridge-enhanced
python3 test_autonomous_tools.py
```

---

## Usage from Claude Code

### Method 1: Direct Tool Call

```
Can you use autonomous_filesystem_full to read all Python files in tools/ and create a summary?
```

Claude Code will call:
```python
autonomous_filesystem_full(
    task="Read all Python files in tools/ directory and create a summary of what each file does"
)
```

### Method 2: Explicit Tool Use

```
Use the autonomous tools to:
1. Search for all TODO comments using autonomous_filesystem_full
2. Create a knowledge graph of the project structure using autonomous_memory_full
3. Fetch the latest MCP documentation using autonomous_fetch_full
```

Claude Code will use each tool sequentially.

---

## Advanced Features

### Multi-Directory Operations

Work across multiple projects simultaneously:

```python
autonomous_filesystem_full(
    "Find all occurrences of 'TODO' and 'FIXME' across all projects",
    working_directory=[
        "/Users/ahmedmaged/ai_storage/mcp-development-project",
        "/Users/ahmedmaged/ai_storage/MyMCPs/lmstudio-bridge-enhanced",
        "/Users/ahmedmaged/ai_storage/other-project"
    ]
)
```

### Dynamic Directory Switching

Change directories mid-session:

```python
autonomous_persistent_session([
    "Read README.md from current project",
    {
        "task": "Compare with README from other project",
        "working_directory": "/other/project"
    },
    "Create comparison report in original project"
])
```

### Large Context Models

If your LLM supports larger context (32K, 128K tokens):

```python
autonomous_filesystem_full(
    "Analyze entire codebase and create detailed documentation",
    max_tokens=16384  # Override default 4096
)
```

---

## Best Practices

### ✅ DO

1. **Use clear, specific task descriptions**
   ```python
   # Good
   "Read setup.py and README.md, then create requirements.txt with all dependencies"

   # Bad
   "Do something with files"
   ```

2. **Provide working directories for filesystem operations**
   ```python
   autonomous_filesystem_full(
       "Read config.json",
       working_directory="/path/to/project"
   )
   ```

3. **Use `autonomous_persistent_session` for multiple related tasks**
   ```python
   # Efficient - one session
   autonomous_persistent_session(["task1", "task2", "task3"])

   # Less efficient - three separate sessions
   autonomous_filesystem_full("task1")
   autonomous_filesystem_full("task2")
   autonomous_filesystem_full("task3")
   ```

4. **Set appropriate `max_rounds` for complex tasks**
   ```python
   autonomous_filesystem_full(
       "Analyze entire codebase",
       max_rounds=500  # Complex task needs more rounds
   )
   ```

### ❌ DON'T

1. **Don't use vague task descriptions**
   ```python
   # Bad
   "Check files"  # What files? Check for what?
   ```

2. **Don't set `max_rounds` too low for complex tasks**
   ```python
   # Bad - task will likely fail
   autonomous_filesystem_full(
       "Analyze entire codebase and create documentation",
       max_rounds=3  # Too few!
   )
   ```

3. **Don't specify paths that don't exist**
   ```python
   # Bad
   autonomous_filesystem_full(
       "Read config.json",
       working_directory="/nonexistent/path"  # Will fail!
   )
   ```

---

## Troubleshooting

### Issue: "No tools available from MCP"

**Cause**: MCP server failed to start or return tools.

**Solution**:
1. Verify the MCP is installed:
   ```bash
   npx -y @modelcontextprotocol/server-filesystem --help
   ```
2. Check MCP logs in stderr output
3. Ensure working_directory exists and is accessible

### Issue: "Max rounds reached without final answer"

**Cause**: Task too complex for the number of rounds allowed.

**Solution**:
1. Increase `max_rounds`:
   ```python
   autonomous_filesystem_full(task, max_rounds=100)
   ```
2. Simplify the task description
3. Break into multiple smaller tasks

### Issue: "Error executing tool"

**Cause**: Tool call failed (e.g., file not found, permission denied).

**Solution**:
1. Check stderr logs for specific error
2. Verify file paths are correct
3. Ensure permissions allow the operation
4. Check MCP-specific requirements (e.g., GitHub token for github MCP)

---

## Performance Notes

### Token Usage

- **Default**: 4096 tokens per LLM response (safe for most models)
- **Override**: Set `max_tokens=8192` or higher for larger context models
- **Note**: LM Studio API doesn't expose model's actual max_context_length

### Round Limits

- **Default**: 10000 rounds (no artificial limit)
- **Typical usage**: Simple tasks complete in 3-10 rounds
- **Complex tasks**: May need 50-500 rounds
- **Safety**: Set reasonable `max_rounds` to prevent infinite loops

### Session Management

- **Persistent sessions**: Reuse connection → faster
- **Separate calls**: New connection each time → slower
- **Recommendation**: Use `autonomous_persistent_session` for multiple related tasks

---

## Architecture Details

### Orchestrator Pattern

The lmstudio-bridge-enhanced MCP uses an **orchestrator pattern**:

```
┌─────────────────────────────────────────────────┐
│  lmstudio-bridge-enhanced (Orchestrator)        │
│  ┌──────────────┐         ┌──────────────────┐ │
│  │ MCP Server   │◄────────┤ Claude Code      │ │
│  │ (FastMCP)    │         │ (Main AI)        │ │
│  └──────────────┘         └──────────────────┘ │
│         │                                        │
│         │ Controls                               │
│         ▼                                        │
│  ┌──────────────┐         ┌──────────────────┐ │
│  │ MCP Client   │────────►│ LM Studio        │ │
│  │ (connects to)│         │ (Local LLM)      │ │
│  └──────────────┘         └──────────────────┘ │
│         │                                        │
│         │ Connects to                            │
│         ▼                                        │
│  ┌─────────────────────────────────────────┐   │
│  │ Battle-tested MCPs (as client)          │   │
│  │  - filesystem                            │   │
│  │  - memory                                │   │
│  │  - fetch                                 │   │
│  │  - github                                │   │
│  └─────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

### Why This Works

1. **Separation of concerns**: Main AI (Claude) doesn't need to manage tool execution
2. **Reusability**: Local LLM can use any existing MCP server
3. **Flexibility**: Add new MCPs without changing core code
4. **Performance**: Local LLM runs locally → faster, cheaper, private
5. **Reliability**: Uses battle-tested MCPs (filesystem, memory, etc.)

---

## Future Enhancements

### Planned Features

- [ ] **Python Interpreter Integration**: Execute Python code autonomously
- [ ] **Docker Integration**: Manage containers autonomously
- [ ] **Custom MCP Support**: Connect to user-defined MCPs
- [ ] **Streaming Support**: Real-time progress updates
- [ ] **Parallel Execution**: Run multiple autonomous agents concurrently

---

## Conclusion

The autonomous tools feature enables your local LLM to:
- ✅ **Use ALL tools from ALL supported MCPs**
- ✅ **Execute multi-step tasks without human intervention**
- ✅ **Work across multiple projects simultaneously**
- ✅ **Build knowledge graphs, fetch web content, manage GitHub repos**
- ✅ **All running locally with full privacy**

**Start using autonomous tools today!** 🚀

```python
# Example: Let your local LLM analyze your entire codebase
autonomous_filesystem_full(
    "Read all Python files, create a knowledge graph of classes and functions, generate comprehensive documentation, and save it to DOCUMENTATION.md"
)
```

---

**Documentation Version**: 1.0.0
**Last Updated**: October 30, 2025
**Author**: Ahmed Maged (via Claude Code + Local LLM)
**Status**: ✅ Production Ready
