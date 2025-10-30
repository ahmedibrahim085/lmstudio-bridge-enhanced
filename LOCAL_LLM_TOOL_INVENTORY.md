# Local LLM Tool Inventory

## Overview

Your **local LLM** (running via LM Studio) has access to **50 tools** across **4 MCPs** when running autonomously through the lmstudio-bridge-enhanced orchestrator.

**Important Distinction:**
- **Claude (You)** - Main AI assistant, calls autonomous functions
- **Local LLM** - Secondary AI (via LM Studio), uses the tools below autonomously

---

## Tool Breakdown by MCP

### 1. Filesystem MCP - 14 Tools ✅

**Autonomous Function**: `autonomous_filesystem_full`

**Available Tools:**

1. **read_text_file** - Read complete file contents as text
2. **read_file** - Read file (deprecated, use read_text_file)
3. **read_media_file** - Read images/audio files (base64 encoded)
4. **read_multiple_files** - Read multiple files simultaneously
5. **write_file** - Create new or overwrite existing files
6. **edit_file** - Make line-based edits with diff output
7. **create_directory** - Create directories (nested supported)
8. **list_directory** - List files and directories with [FILE]/[DIR] prefixes
9. **list_directory_with_sizes** - List files with size information
10. **directory_tree** - Recursive tree view as JSON
11. **move_file** - Move or rename files and directories
12. **search_files** - Recursive file search by pattern
13. **get_file_info** - Get file metadata (size, dates, permissions)
14. **list_allowed_directories** - Show accessible directory list

**What Local LLM Can Do:**
- ✅ Search for files across multiple directories
- ✅ Read and analyze code files
- ✅ Create and edit files
- ✅ Organize directory structures
- ✅ Get file metadata and statistics
- ✅ Compare files across projects

**Security:**
- Only works within allowed directories
- System directories blocked (/etc, /bin, /sbin, etc.)
- Symlink bypass protection enabled

---

### 2. Memory MCP - 9 Tools ✅

**Autonomous Function**: `autonomous_memory_full`

**Available Tools:**

1. **create_entities** - Create multiple knowledge entities
2. **create_relations** - Link entities with relations (active voice)
3. **add_observations** - Add facts to existing entities
4. **delete_entities** - Remove entities and their relations
5. **delete_observations** - Remove specific facts from entities
6. **delete_relations** - Remove relationships between entities
7. **read_graph** - View entire knowledge graph
8. **search_nodes** - Search knowledge graph by query
9. **open_nodes** - Get specific entities by name

**What Local LLM Can Do:**
- ✅ Build knowledge graphs from information
- ✅ Create and link entities
- ✅ Store observations and facts
- ✅ Search and query knowledge
- ✅ Maintain project context
- ✅ Track relationships between concepts

**Use Cases:**
- Building project documentation knowledge base
- Tracking technology relationships
- Creating learning notes
- Research organization

---

### 3. Fetch MCP - 1 Tool ✅

**Autonomous Function**: `autonomous_fetch_full`

**Available Tools:**

1. **fetch** - Fetch web content and convert to markdown
   - **Parameters:**
     - `url` (required): URL to fetch
     - `max_length` (optional): Max characters to return
     - `start_index` (optional): Start position for truncated content
     - `raw` (optional): Return raw HTML instead of markdown

**What Local LLM Can Do:**
- ✅ Fetch web pages and documentation
- ✅ Download online content
- ✅ Convert HTML to markdown automatically
- ✅ Handle pagination with start_index
- ✅ Get raw HTML when needed

**Use Cases:**
- Researching online documentation
- Fetching API specifications
- Downloading code examples
- Comparing content from multiple sites

**Note:** Grants internet access to local LLM!

---

### 4. GitHub MCP - 26 Tools ✅

**Autonomous Function**: `autonomous_github_full`

**Available Tools:**

#### Repository Operations (3 tools)
1. **search_repositories** - Search for repositories
2. **create_repository** - Create new repository
3. **fork_repository** - Fork repositories

#### File Operations (4 tools)
4. **create_or_update_file** - Create/update single file
5. **get_file_contents** - Read file or directory contents
6. **push_files** - Push multiple files in single commit
7. **get_pull_request_files** - List PR changed files

#### Branch Operations (2 tools)
8. **create_branch** - Create new branch
9. **update_pull_request_branch** - Update PR branch

#### Issue Operations (6 tools)
10. **create_issue** - Create new issue
11. **list_issues** - List/filter issues
12. **update_issue** - Update existing issue
13. **add_issue_comment** - Add comment to issue
14. **search_issues** - Search issues and PRs
15. **get_issue** - Get specific issue details

#### Pull Request Operations (8 tools)
16. **create_pull_request** - Create new PR
17. **get_pull_request** - Get PR details
18. **list_pull_requests** - List/filter PRs
19. **create_pull_request_review** - Create PR review
20. **merge_pull_request** - Merge PR
21. **get_pull_request_status** - Get PR check status
22. **get_pull_request_comments** - Get PR comments
23. **get_pull_request_reviews** - Get PR reviews

#### Search Operations (2 tools)
24. **search_code** - Search code across GitHub
25. **search_users** - Search for users

#### Other Operations (1 tool)
26. **list_commits** - Get commit history

**What Local LLM Can Do:**
- ✅ Search and analyze repositories
- ✅ Create and manage issues
- ✅ Work with pull requests
- ✅ Read and modify repository files
- ✅ Create branches
- ✅ Search code and users
- ✅ Manage repository content

**Authentication:**
- Requires `GITHUB_PERSONAL_ACCESS_TOKEN` environment variable
- Or pass token directly to `autonomous_github_full` function

---

## Summary Statistics

```
Total MCPs: 4
Total Tools: 50
  - Filesystem: 14 tools (28%)
  - GitHub: 26 tools (52%)
  - Memory: 9 tools (18%)
  - Fetch: 1 tool (2%)
```

---

## How It Works

### Architecture Flow

```
┌─────────────────────────────────────────────────────────────┐
│ Claude Code (Main AI Assistant)                             │
│ - Receives user requests                                    │
│ - Decides which autonomous function to call                 │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            │ Calls autonomous function
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ lmstudio-bridge-enhanced MCP (Orchestrator)                 │
│ - autonomous_filesystem_full()                              │
│ - autonomous_memory_full()                                  │
│ - autonomous_fetch_full()                                   │
│ - autonomous_github_full()                                  │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            │ Connects to target MCP
                            │ Discovers tools
                            │ Converts to OpenAI format
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Local LM Studio Model (Autonomous Worker)                   │
│ - Receives task + available tools                           │
│ - Calls tools autonomously                                  │
│ - Iterates until task complete                              │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            │ Executes tools via MCP
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Target MCP Server                                            │
│ - Filesystem MCP (file operations)                          │
│ - Memory MCP (knowledge graph)                              │
│ - Fetch MCP (web content)                                   │
│ - GitHub MCP (GitHub API)                                   │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            │ Performs actual operations
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Real Resources                                               │
│ - Local filesystem                                           │
│ - Knowledge graph database                                  │
│ - Web content                                                │
│ - GitHub repositories                                        │
└─────────────────────────────────────────────────────────────┘
```

### Autonomous Loop

```python
# 1. Claude calls autonomous function
result = autonomous_filesystem_full("Search for all Python files")

# 2. Function connects to MCP and discovers tools
connection = MCPConnection(command="npx", args=["..."])
tools = await discovery.discover_tools()  # Gets 14 filesystem tools

# 3. Local LLM runs autonomous loop
for round in range(max_rounds):
    # Local LLM decides which tool to use
    response = llm.chat_completion(
        messages=[{"role": "user", "content": task}],
        tools=tools  # All 14 filesystem tools available
    )

    # If tool call, execute it via MCP
    if response.tool_calls:
        for tool_call in response.tool_calls:
            result = await mcp.execute_tool(tool_call)
            # Feed result back to LLM
    else:
        # LLM has final answer
        return response.content
```

---

## Example Usage

### Example 1: Filesystem Operations

```python
# Claude calls:
autonomous_filesystem_full(
    "Search for all Python files, read their imports, and create a dependency graph"
)

# Local LLM autonomously uses these tools:
# 1. search_files("*.py")
# 2. read_multiple_files([list of Python files])
# 3. write_file("dependency_graph.txt", content)
# Returns: "Created dependency graph with 25 Python files"
```

### Example 2: Knowledge Graph Building

```python
# Claude calls:
autonomous_memory_full(
    "Create entities for Python, FastMCP, and MCP with observations, then link them"
)

# Local LLM autonomously uses these tools:
# 1. create_entities([Python, FastMCP, MCP])
# 2. add_observations("Python", ["supports async/await", "dynamic typing"])
# 3. create_relations(["FastMCP uses Python", "MCP uses Python"])
# Returns: "Created 3 entities with 5 observations and 2 relations"
```

### Example 3: Web Research

```python
# Claude calls:
autonomous_fetch_full(
    "Fetch MCP documentation and summarize key concepts"
)

# Local LLM autonomously uses these tools:
# 1. fetch("https://modelcontextprotocol.io")
# 2. Analyzes content
# Returns: "MCP key concepts: Resources, Tools, Prompts, JSON-RPC..."
```

### Example 4: GitHub Analysis

```python
# Claude calls:
autonomous_github_full(
    "Search for MCP server repos, analyze top 5, create comparison"
)

# Local LLM autonomously uses these tools:
# 1. search_repositories("MCP server")
# 2. get_file_contents("owner/repo", "README.md") x5
# 3. list_issues("owner/repo") x5
# Returns: "Analyzed 5 MCP servers: filesystem (50 stars), memory (30 stars)..."
```

---

## Tool Categories

### By Function Type

**File I/O** (6 tools)
- read_text_file, read_media_file, read_multiple_files
- write_file, edit_file, get_file_info

**Directory Operations** (5 tools)
- create_directory, list_directory, list_directory_with_sizes
- directory_tree, search_files

**File Management** (2 tools)
- move_file, list_allowed_directories

**Knowledge Graph** (9 tools)
- All memory MCP tools

**Web Access** (1 tool)
- fetch

**GitHub API** (26 tools)
- All GitHub MCP tools

---

## Limitations and Constraints

### Security Restrictions

**Filesystem:**
- Only works within allowed directories
- System directories blocked (/etc, /bin, /sbin, /System, /root)
- Symlink bypass protection enabled
- Validation on all paths

**GitHub:**
- Requires valid GitHub token
- Subject to GitHub API rate limits
- Respects repository permissions

**Fetch:**
- No authentication for private content
- Subject to website robots.txt
- Timeout limits apply

### Performance Limits

**Max Rounds:**
- Filesystem: 10,000 rounds (essentially unlimited)
- Memory: 100 rounds
- Fetch: 100 rounds
- GitHub: 100 rounds

**Max Tokens:**
- Default: "auto" (4096 tokens safe for most models)
- Can override manually if model supports more

### Model Requirements

**Required:**
- LM Studio running
- Model loaded in LM Studio
- Model supports function calling (tool use)

**Recommended Models:**
- Qwen 2.5 Coder 7B+
- Llama 3.1 8B+
- Mistral 7B+
- Any model with good tool-calling capabilities

---

## Testing

To test what tools are available, run:

```bash
cd /Users/ahmedmaged/ai_storage/MyMCPs/lmstudio-bridge-enhanced
python3 test_local_llm_tools.py
```

This script:
1. Connects to each MCP
2. Discovers all available tools
3. Shows detailed tool information
4. Provides summary statistics

---

## Configuration

### Required MCP Configuration

Add to `.mcp.json`:

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
      "args": ["/path/to/main.py"],
      "env": {
        "LMSTUDIO_HOST": "localhost",
        "LMSTUDIO_PORT": "1234"
      }
    }
  }
}
```

### Environment Variables

```bash
# For GitHub operations
export GITHUB_PERSONAL_ACCESS_TOKEN="your_token_here"

# For custom working directory (optional)
export WORKING_DIR="/path/to/project"

# For LM Studio (if non-default)
export LMSTUDIO_HOST="localhost"
export LMSTUDIO_PORT="1234"
```

---

## Future Enhancements

Planned tool additions:

1. **Python Interpreter MCP** - Execute Python code
2. **Database MCP** - Query databases (PostgreSQL, SQLite)
3. **Docker MCP** - Manage containers
4. **AWS MCP** - Cloud operations
5. **Slack MCP** - Team communication

---

## Troubleshooting

### Tools Not Available

**Problem:** Local LLM says "Tool not found"

**Solution:**
1. Verify MCP is configured in `.mcp.json`
2. Check MCP server is installed
3. Restart Claude Code to reload configuration
4. Run `test_local_llm_tools.py` to verify connection

### Connection Failures

**Problem:** "Failed to connect to MCP"

**Solution:**
1. Check MCP package installed:
   - `npx -y @modelcontextprotocol/server-memory`
   - `uvx mcp-server-fetch`
2. Verify no other processes using MCP
3. Check system logs for errors

### Authentication Issues

**Problem:** GitHub operations fail with auth error

**Solution:**
1. Set `GITHUB_PERSONAL_ACCESS_TOKEN` environment variable
2. Verify token has required scopes (repo, issues, etc.)
3. Pass token directly to `autonomous_github_full` function

---

**Last Updated:** October 30, 2025
**Total Tools:** 50
**MCPs Supported:** 4
**Autonomous Functions:** 5
