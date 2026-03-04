# Architecture

Deep dive into how LM Studio Bridge Enhanced enables TRUE dynamic MCP support with hot reload.

---

## Why Do We Need This Bridge?

### The Core Problem

**LM Studio only exposes HTTP APIs** - it does NOT natively support the MCP protocol!

**LM Studio's HTTP APIs** (4 API surfaces):
1. `GET /v1/models` - List available models (OpenAI-compatible)
2. `POST /v1/chat/completions` - Chat completions (OpenAI-compatible)
3. `POST /v1/completions` - Text completions (OpenAI-compatible)
4. `POST /v1/embeddings` - Generate embeddings (OpenAI-compatible)
5. `POST /v1/responses` - Stateful conversations (LM Studio-specific)
6. `POST /v1/messages` - Anthropic-compatible messages
7. `POST /api/v1/chat` - Native LM Studio chat with 19 event types (v5.0.0)

**What's Missing**:
- ❌ No MCP protocol support
- ❌ No way to expose tools to local LLMs
- ❌ No integration with MCP ecosystem (filesystem, memory, github, etc.)
- ❌ Local LLMs cannot use external tools autonomously

### Why This Matters

**Without this bridge**:
```
Claude Code → Can use MCP tools (filesystem, memory, etc.)
     ↓
  But...
     ↓
Local LLMs in LM Studio → CANNOT use MCP tools
                          (only HTTP chat/completion APIs available)
```

**Result**: Local LLMs are isolated from the rich MCP ecosystem!

### The Solution: This Bridge

This bridge acts as a **translator and orchestrator** between three worlds:

```
┌─────────────────────────────────────────────────────────┐
│ 1. MCP World (Protocol-based Tool Integration)         │
│    - Claude Code speaks MCP                             │
│    - Other MCP servers (filesystem, memory, etc.)       │
└────────────┬────────────────────────────────────────────┘
             │
             │ Bridge translates between worlds
             ▼
┌─────────────────────────────────────────────────────────┐
│ 2. Bridge (lmstudio-bridge-enhanced)                    │
│    - Acts as MCP Server to Claude Code                  │
│    - Acts as MCP Client to other MCPs                   │
│    - Acts as HTTP Client to LM Studio                   │
│    - Orchestrates autonomous tool usage                 │
└────────────┬────────────────────────────────────────────┘
             │
             │ HTTP API calls
             ▼
┌─────────────────────────────────────────────────────────┐
│ 3. LM Studio World (HTTP APIs only)                     │
│    - Local LLMs via HTTP endpoints                      │
│    - No native MCP support                              │
└─────────────────────────────────────────────────────────┘
```

### What The Bridge Enables

**Before bridge** (impossible):
```python
# ❌ This doesn't work - LM Studio has no MCP support
local_llm.use_mcp_tool("filesystem", "read_file", {"path": "README.md"})
```

**After bridge** (now possible):
```python
# ✅ Bridge enables this!
autonomous_with_mcp(
    mcp_name="filesystem",
    task="Read README.md and summarize it",
    model="qwen/qwen3-coder-30b"  # Local LLM in LM Studio
)

# Behind the scenes:
# 1. Bridge connects to filesystem MCP (as MCP client)
# 2. Bridge discovers tools from filesystem MCP
# 3. Bridge passes tools to local LLM via HTTP API (/v1/chat/completions)
# 4. Local LLM decides which tools to use
# 5. Bridge executes tools via filesystem MCP
# 6. Bridge passes results back to local LLM
# 7. Local LLM completes task autonomously!
```

### The Three Roles of This Bridge

1. **MCP Server** (to Claude Code)
   - Exposes 37 tools that Claude can use
   - Appears as a standard MCP server
   - Integrates seamlessly with Claude Code

2. **MCP Client** (to other MCPs)
   - Connects to filesystem, memory, github, etc.
   - Discovers their tools dynamically
   - Executes tool calls on behalf of local LLM

3. **LLM Orchestrator** (to LM Studio)
   - Translates MCP tools → OpenAI tool format
   - Calls local LLM via HTTP APIs
   - Manages autonomous execution loop
   - Handles tool results and multi-step workflows

### Key Innovation

**Most MCP bridges** do ONE thing: expose a specific service's API as MCP tools.

**This bridge** does something unique: it gives **local LLMs autonomous access to the ENTIRE MCP ecosystem!**

**Result**:
- ✅ Local LLMs can now use 100+ existing MCP servers
- ✅ Works with ANY LLM in LM Studio (Qwen, Llama, Mistral, etc.)
- ✅ No code changes needed to add new MCPs
- ✅ True autonomous execution (LLM decides which tools to use)
- ✅ Privacy-first (everything runs locally)
- ✅ No API costs (local LLMs are free)

---

## Core Innovation

**Problem**: Traditional MCP bridges hardcode configurations. Adding new MCPs requires code changes.

**Solution**: Dynamic MCP discovery + hot reload. Add any MCP to `.mcp.json` → use immediately. **Zero code changes, zero restart** (after initial setup).

---

## System Architecture

```
┌──────────────────────────────────────────────────────────┐
│ Claude Code (or any MCP client)                         │
└──────────────┬───────────────────────────────────────────┘
               │
               │ Uses tools from
               ▼
┌──────────────────────────────────────────────────────────┐
│ lmstudio-bridge-enhanced (MCP Server + Orchestrator)     │
│  ┌────────────────────────────────────────────────────┐  │
│  │ FastMCP Server                                     │  │
│  │  - Exposes 37 tools to Claude Code               │  │
│  │  - 11 core (completions, health, embeddings)      │  │
│  │  - 6 vision tools + 5 autonomous MCP tools        │  │
│  │  - 5 agent profile + 1 smart selection            │  │
│  │  - 9 LMS CLI tools (optional)                     │  │
│  └────────────────────────────────────────────────────┘  │
│                                                           │
│  ┌────────────────────────────────────────────────────┐  │
│  │ Dynamic Autonomous Agent                           │  │
│  │  - Reads .mcp.json dynamically (hot reload)       │  │
│  │  - Connects to MCPs as client                     │  │
│  │  - Discovers tools from MCPs                      │  │
│  │  - Passes tools to local LLM                      │  │
│  └────────────────────────────────────────────────────┘  │
│               │                           │               │
│               ▼                           ▼               │
│  ┌────────────────────┐     ┌─────────────────────────┐ │
│  │ LM Studio API      │     │ MCP Client             │ │
│  │ (localhost:1234)   │     │ (stdio connection)     │ │
│  └────────────────────┘     └─────────────────────────┘ │
└──────────────┬───────────────────────┬───────────────────┘
               │                       │
               ▼                       ▼
      ┌────────────────┐      ┌──────────────────────┐
      │ Local LLM      │      │ Other MCP Servers    │
      │ (Qwen, Llama,  │      │  - filesystem        │
      │  Mistral, etc.)│      │  - memory            │
      └────────────────┘      │  - fetch             │
                              │  - github            │
                              │  - ANY custom MCP    │
                              └──────────────────────┘
```

**Key Insight**: The bridge acts as BOTH:
- **MCP Server** to Claude Code (exposes tools)
- **MCP Client** to other MCPs (uses their tools)

This orchestrator pattern enables local LLM to use tools from ANY MCP dynamically!

---

## Dynamic MCP Discovery

### The Challenge

Traditional approach requires hardcoded MCP configurations:

```python
# ❌ OLD: Hardcoded
async def use_filesystem():
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem"]  # Hardcoded!
    )
```

**Problem**: Every new MCP needs code changes!

### The Solution

Dynamic discovery from `.mcp.json`:

```python
# ✅ NEW: Dynamic
async def use_any_mcp(mcp_name):
    # Discover from .mcp.json
    params = discovery.get_connection_params(mcp_name)

    server_params = StdioServerParameters(
        command=params["command"],      # Dynamic!
        args=params["args"],           # Dynamic!
        env=params["env"]              # Dynamic!
    )
```

**Result**: ONE function works with ANY MCP!

### Discovery Flow

```
1. User calls: autonomous_with_mcp("postgres", "task")
                     │
                     ▼
2. Read .mcp.json (hot reload: 0.011ms)
                     │
                     ▼
3. Find "postgres" MCP configuration
   {
     "command": "uvx",
     "args": ["mcp-server-postgres", "--db-url", "..."],
     "env": {"DB_PASSWORD": "..."}
   }
                     │
                     ▼
4. Connect to postgres MCP server
                     │
                     ▼
5. Discover postgres tools dynamically
   ["read_query", "write_query", "create_table", ...]
                     │
                     ▼
6. Pass tools to local LLM
                     │
                     ▼
7. Local LLM uses tools autonomously
                     │
                     ▼
8. Return final answer
```

**Zero hardcoded assumptions!** Works with ANY MCP.

---

## Hot Reload Implementation

### The Innovation

**Problem**: Adding MCPs to `.mcp.json` required restarting the server.

**Solution**: Read `.mcp.json` FRESH on every tool call!

### Implementation

```python
class DynamicAutonomousAgent:
    def __init__(self, llm_client=None, mcp_discovery=None):
        # Store PATH only, not the discovery instance
        self.mcp_json_path = mcp_discovery.mcp_json_path if mcp_discovery else None
        self.llm = llm_client or LLMClient()

    async def autonomous_with_mcp(self, mcp_name: str, task: str, ...):
        # HOT RELOAD: Create FRESH MCPDiscovery on every call
        discovery = MCPDiscovery(self.mcp_json_path)

        # Get fresh connection params from .mcp.json
        params = discovery.get_connection_params(mcp_name)

        # Connect to MCP...
```

**Key**: Don't cache the MCPDiscovery instance - create a fresh one each time!

### Performance

**Benchmark results** (scripts/benchmark_hot_reload.py):

```
Hot reload per call:       0.0110 ms (11 microseconds)
LLM API call:              8.07 ms
Network request:           10-100 ms
LLM inference:             100-5000 ms

Hot reload is 734x faster than LLM API call
```

**Conclusion**: 0.011ms is **essentially FREE**. The overhead is completely dominated by:
- LLM inference (100-5000ms)
- Network requests (10-100ms)
- Actual MCP tool execution (1-100ms)

### User Experience

**Before hot reload**:
1. Add MCP to `.mcp.json`
2. Restart Claude Code (10-30 seconds)
3. Use MCP

**After hot reload**:
1. Add MCP to `.mcp.json`
2. Use MCP ✅ (instant!)

**Initial setup**: Restart Claude Code ONCE to load hot reload code. After that, hot reload works automatically!

---

## Generic MCP Support

### Proof Matrix

| Feature | sqlite | filesystem | memory | fetch | github | ANY MCP |
|---------|--------|------------|--------|-------|---------|---------|
| Discovery from .mcp.json | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Connection to server | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Tool discovery | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Hot reload support | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| No code changes | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

**Verified**: System works with ANY MCP that follows the MCP protocol!

### How Tool Discovery Works

```python
# Connect to MCP server
async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        # Initialize session
        await session.initialize()

        # Discover tools (generic - works for ANY MCP!)
        tools_response = await session.list_tools()

        # Convert to OpenAI format for local LLM
        openai_tools = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema
                }
            }
            for tool in tools_response.tools
        ]

        # Local LLM now has ALL tools from the MCP!
```

**Result**: Works for ANY MCP - filesystem (14 tools), memory (9 tools), sqlite (6 tools), etc.

---

## Autonomous Execution

### The Loop

```python
async def autonomous_loop(session, task, max_rounds=10000):
    messages = [{"role": "user", "content": task}]

    for round in range(max_rounds):
        # 1. LLM decides what to do
        response = await llm.chat_completion(
            messages=messages,
            tools=openai_tools,
            tool_choice="auto"
        )

        # 2. Check if done
        if response.finish_reason == "stop":
            return response.content  # Task complete!

        # 3. Execute tool calls
        if response.tool_calls:
            for tool_call in response.tool_calls:
                # Execute via MCP
                result = await session.call_tool(
                    tool_call.name,
                    tool_call.arguments
                )

                # Add result to messages
                messages.append({
                    "role": "tool",
                    "content": result
                })

        # Continue loop...
```

**Key Features**:
- **max_rounds: 10000** (default) - No artificial limit
- **Autonomous**: LLM decides which tools to use
- **Multi-step**: LLM can chain tool calls
- **Self-correcting**: LLM sees tool results and adjusts

---

## Multi-MCP Support

### Tool Namespacing

When using multiple MCPs, tools are namespaced to avoid collisions:

```python
# Single MCP (no namespace)
- read_file
- write_file

# Multiple MCPs (namespaced)
- filesystem__read_file
- filesystem__write_file
- memory__create_entities
- memory__read_graph
```

**Result**: Local LLM can distinguish tools from different MCPs!

### Connection Management

```python
async def autonomous_with_multiple_mcps(mcp_names, task):
    # Connect to ALL MCPs
    connections = []
    all_tools = []

    for mcp_name in mcp_names:
        params = discovery.get_connection_params(mcp_name)

        # Connect to MCP
        read, write = await stdio_client(server_params)
        session = await ClientSession(read, write)

        connections.append((mcp_name, session))

        # Discover tools and namespace them
        tools = await session.list_tools()
        namespaced_tools = [
            f"{mcp_name}__{tool.name}": tool
            for tool in tools
        ]
        all_tools.extend(namespaced_tools)

    # Local LLM now has tools from ALL MCPs!
    await autonomous_loop(connections, all_tools, task)
```

**Result**: Use tools from multiple MCPs in a single autonomous session!

---

## Configuration Discovery

### Search Priority

The system searches for `.mcp.json` in this order:

1. **$MCP_JSON_PATH** (environment variable)
   - Explicit override for testing or custom configs
   - Example: `MCP_JSON_PATH=/tmp/test.mcp.json`

2. **~/.lmstudio/mcp.json**
   - LM Studio's native MCP configuration
   - Most relevant for local LLM usage

3. **$(pwd)/.mcp.json**
   - Project-specific configuration
   - Where Claude Code runs the MCP server

4. **~/.mcp.json**
   - User-wide MCP configuration
   - Fallback for global MCPs

5. **$(dirname $(pwd))/.mcp.json**
   - Parent directory
   - Fallback for nested structures

**100% portable**: No hardcoded paths, works for any user/project/system!

### Implementation

```python
class MCPDiscovery:
    def _find_mcp_json(self) -> Optional[str]:
        possible_paths = [
            os.environ.get("MCP_JSON_PATH"),
            os.path.expanduser("~/.lmstudio/mcp.json"),
            os.path.join(os.getcwd(), ".mcp.json"),
            os.path.expanduser("~/.mcp.json"),
            os.path.join(os.path.dirname(os.getcwd()), ".mcp.json")
        ]

        for path in possible_paths:
            if path and os.path.exists(path):
                return path

        return None
```

**No assumptions**: Discovers configuration dynamically!

---

## LMS CLI Integration (Optional Enhancement)

### What is LMS CLI?

**LMS CLI** (`lms`) is the official command-line tool for LM Studio model management.

**Installation**:
```bash
# Homebrew (recommended)
brew install lmstudio-ai/lms/lms

# npm
npm install -g @lmstudio/lms
```

**Documentation**: https://github.com/lmstudio-ai/lms

### Why Integrate LMS CLI?

**Problem Without LMS CLI**:
```
User runs autonomous task
    ↓
Bridge calls /v1/chat/completions
    ↓
LM Studio auto-unloaded model (memory pressure)
    ↓
HTTP 404 Error! ❌
    ↓
Task fails, user has to manually reload model
```

**Solution With LMS CLI**:
```
User runs autonomous task
    ↓
Bridge checks model status via LMS CLI
    ↓
Model is unloaded or idle? → Auto-load it!
    ↓
Bridge calls /v1/chat/completions
    ↓
Success! ✅
    ↓
Task completes autonomously
```

### How It Works

**Architecture**:

```
┌─────────────────────────────────────────────────────────┐
│ lmstudio-bridge-enhanced                                │
│                                                           │
│  ┌────────────────────────────────────────────────────┐ │
│  │ Model Validation & Loading (utils/lms_helper.py)  │ │
│  │                                                      │ │
│  │ 1. Check if model loaded (via LMS CLI)            │ │
│  │    → lms ps --json                                 │ │
│  │    → Parse model status: loaded/idle/loading       │ │
│  │                                                      │ │
│  │ 2. If not loaded or idle:                          │ │
│  │    → lms load <model> --ttl 600                    │ │
│  │    → Model stays loaded for 10 minutes             │ │
│  │                                                      │ │
│  │ 3. Verify model active                              │ │
│  │    → lms ps --json (check status=loaded)           │ │
│  └────────────────────────────────────────────────────┘ │
│                │                                         │
│                ▼                                         │
│  ┌────────────────────────────────────────────────────┐ │
│  │ LM Studio HTTP API (v1/chat/completions, etc.)    │ │
│  └────────────────────────────────────────────────────┘ │
└──────────────┬──────────────────────────────────────────┘
               │
               ▼
      ┌────────────────┐
      │ Local LLM      │
      └────────────────┘
```

### Model State Handling

**Three Model States** (from `lms ps`):
1. **`loaded`** - Active and ready to serve requests ✅
2. **`idle`** - Present in memory, will auto-activate on API request ✅
3. **`loading`** - Currently loading into memory ⏳

**IDLE State Behavior** (from LM Studio docs):
> "Any API request to an idle model automatically reactivates it"

This means both `loaded` and `idle` are **acceptable states**!

**Code Implementation** (utils/lms_helper.py:250-290):
```python
def is_model_loaded(model_name: str) -> Optional[bool]:
    """Check if model is available (loaded or idle)."""
    models = list_loaded_models()

    for m in models:
        if m.get("identifier") == model_name:
            status = m.get("status", "").lower()

            # Both loaded and idle are usable!
            is_available = status in ("loaded", "idle")

            return is_available

    return False  # Not found
```

### Benefits

1. **Prevents 404 Errors**
   - Ensures model is loaded before HTTP API calls
   - Eliminates "model not found" errors
   - Auto-recovers from model unloading

2. **Better Diagnostics**
   - Detailed model status (loaded/idle/loading)
   - Memory usage monitoring
   - Server health checks

3. **TTL Management**
   - Configurable time-to-live for models
   - Prevents premature auto-unloading
   - Optimizes memory vs availability trade-off

4. **Production-Grade Reliability**
   - Proactive model management
   - Self-healing capabilities
   - Health checks and verification

5. **Multi-Model Workflows**
   - Explicit model loading/unloading
   - Memory optimization
   - Workflow orchestration

### Implementation Details

**Core Functions** (in utils/lms_helper.py):

1. `is_model_loaded()` - Check if model is available (loaded or idle)
2. `load_model()` - Load model with TTL (default: 10 minutes)
3. `unload_model()` - Free memory
4. `ensure_model_loaded()` - Idempotent preloading (RECOMMENDED)
5. `verify_model_loaded()` - Health check after loading
6. `list_loaded_models()` - Get all models with details

**MCP Tools** (in tools/lms_cli_tools.py):

Exposes 9 LMS CLI functions as MCP tools:
- `lms_list_loaded_models`
- `lms_list_downloaded_models`
- `lms_load_model`
- `lms_unload_model`
- `lms_ensure_model_loaded` ⭐
- `lms_search_models`
- `lms_download_model`
- `lms_resolve_model`
- `lms_server_status`

See [API Reference](API_REFERENCE.md#lms-cli-tools-optional) for details.

### Graceful Degradation

**System works WITHOUT LMS CLI!**

```python
if not LMSHelper.is_installed():
    # Skip LMS CLI-based validation
    # Proceed with HTTP API call
    # May experience intermittent 404 errors
    logger.warning("LMS CLI not installed - using basic mode")
```

**Recommendations**:
- ✅ **Development**: LMS CLI optional but helpful
- ✅ **Testing**: LMS CLI recommended for reliability
- ✅ **Production**: LMS CLI strongly recommended (prevents 404 errors)

---

## Key Components

### 1. MCPDiscovery Class

**File**: `mcp_client/discovery.py`

**Responsibilities**:
- Find `.mcp.json` in multiple locations
- Parse MCP configurations
- Validate MCP names
- Provide connection parameters

**API**:
```python
discovery = MCPDiscovery()

# List available MCPs
mcps = discovery.list_available_mcps()
# ['filesystem', 'memory', 'fetch', ...]

# Get connection params for a specific MCP
params = discovery.get_connection_params("filesystem")
# {'command': 'npx', 'args': [...], 'env': {...}}
```

### 2. DynamicAutonomousAgent Class

**File**: `tools/dynamic_autonomous.py`

**Responsibilities**:
- Connect to MCPs dynamically
- Discover tools from MCPs
- Pass tools to local LLM
- Execute autonomous loops
- Handle multi-MCP sessions

**API**:
```python
agent = DynamicAutonomousAgent(llm_client)

# Single MCP
await agent.autonomous_with_mcp("filesystem", "task")

# Multiple MCPs
await agent.autonomous_with_multiple_mcps(["filesystem", "memory"], "task")

# Auto-discover ALL MCPs
await agent.autonomous_discover_and_execute("task")
```

### 3. Tool Registration

**File**: `tools/dynamic_autonomous_register.py`

**Responsibilities**:
- Register dynamic tools with FastMCP
- Expose tools to Claude Code
- Handle parameter validation
- Provide tool documentation

**API**:
```python
from tools.dynamic_autonomous_register import register_dynamic_autonomous_tools

mcp = FastMCP("lmstudio-bridge")
register_dynamic_autonomous_tools(mcp, llm_client)

# Now tools are available to Claude Code:
# - autonomous_with_mcp
# - autonomous_with_multiple_mcps
# - autonomous_discover_and_execute
# - list_available_mcps
```

---

## Performance Characteristics

### Hot Reload

- **Per call overhead**: 0.011ms
- **Comparison**: 734x faster than LLM API
- **Conclusion**: Essentially FREE

### Autonomous Execution

- **Typical tasks**: 3-10 rounds
- **Complex tasks**: 50-500 rounds
- **Default max**: 10000 rounds (no artificial limit)

### Token Efficiency

Using stateful `/v1/responses` API:
- **Round 10**: ~1000 tokens context
- **Round 100**: ~10000 tokens context (vs 100000 with linear growth)
- **Result**: 97% token savings at scale!

---

## Design Decisions

### 1. Hot Reload vs. File Watcher

**Chose**: Hot reload (re-read on every call)

**Why**:
- 0.011ms cost is negligible
- Simpler implementation
- No dependencies (no watchdog library)
- Instant updates (no polling delay)

**Alternative rejected**: File watcher (overkill for 0.011ms)

### 2. Orchestrator Pattern

**Chose**: Bridge acts as MCP server + MCP client

**Why**:
- Separation of concerns
- Reuses battle-tested MCPs
- Claude doesn't manage tool execution
- Local LLM handles autonomous decisions

**Alternative rejected**: Direct Claude → LM Studio connection (loses MCP ecosystem)

### 3. Tool Namespacing

**Chose**: Prefix tools with MCP name when using multiple MCPs

**Why**:
- Prevents tool name collisions
- Clear which MCP owns each tool
- LLM can distinguish tools easily

**Alternative rejected**: No namespacing (would cause collisions)

### 4. Default max_rounds: 10000

**Chose**: Very high limit (10000 rounds)

**Why**:
- Philosophy: "Let LLM work until done"
- Most tasks finish in < 20 rounds anyway
- Users can override for specific limits
- Prevents artificial constraints

**Alternative rejected**: Low default like 100 (too limiting)

---

## Extensibility

### Adding New MCP Support

```json
// Add to .mcp.json
{
  "mcpServers": {
    "your-new-mcp": {
      "command": "uvx",
      "args": ["your-mcp-server", "--arg", "value"],
      "env": {"API_KEY": "..."}
    }
  }
}
```

**No code changes required!** System discovers and uses it automatically.

### Adding New Tools to Bridge

```python
# In main.py or custom tool module
@mcp.tool()
async def custom_tool(param: str) -> str:
    """Custom tool description."""
    # Implementation
    return result

# Tool is now available to Claude Code!
```

---

## Comparison: Before vs After

### Before (Hardcoded)

```python
# ❌ Separate function for each MCP
async def autonomous_filesystem_full(task):
    # Hardcoded filesystem configuration
    ...

async def autonomous_memory_full(task):
    # Hardcoded memory configuration
    ...

# Adding new MCP: Write new function, update registration, restart
```

**Problems**:
- Code changes for every new MCP
- Duplication across functions
- Restart required
- Doesn't scale

### After (Dynamic)

```python
# ✅ ONE function for ALL MCPs
async def autonomous_with_mcp(mcp_name, task):
    # Dynamic discovery from .mcp.json
    params = discovery.get_connection_params(mcp_name)
    # Connect and execute...

# Adding new MCP: Edit .mcp.json, done!
```

**Benefits**:
- Zero code changes
- No restart (after initial setup)
- Scales to unlimited MCPs
- Future-proof

---

## Security Considerations

### Credential Handling

- **Never hardcode**: All credentials in `.mcp.json` env vars
- **Environment variables**: Can reference system env vars
- **File permissions**: `.mcp.json` should be user-readable only

### MCP Validation

```python
def get_connection_params(self, mcp_name: str):
    if mcp_name not in self.config["mcpServers"]:
        raise ValueError(f"MCP '{mcp_name}' not found")

    config = self.config["mcpServers"][mcp_name]
    if config.get("disabled", False):
        raise ValueError(f"MCP '{mcp_name}' is disabled")

    return config
```

**Result**: Only use MCPs explicitly configured and enabled.

---

## Testing Strategy

### Unit Tests

- `tests/standalone/test_dynamic_mcp_discovery.py` - Discovery system
- `tests/standalone/test_generic_tool_discovery.py` - Tool discovery for any MCP
- `scripts/benchmark_hot_reload.py` - Performance verification

### Integration Tests

- `tests/standalone/test_autonomous_tools.py` - End-to-end autonomous execution
- `tests/standalone/test_local_llm_uses_sqlite.py` - Dynamically added MCP

---

## Future Enhancements

### Planned

- [ ] MCP blacklist for auto-discovery (avoid recursive connection)
- [ ] Parallel multi-MCP connections
- [ ] Streaming progress updates
- [ ] Tool execution caching
- [ ] Enhanced error recovery

---

## v5.0.0 Architecture Changes

### Facade Pattern (ARCH-1)

The monolithic `LLMClient` (1503 lines, 30+ methods) was split into a **Facade + 7 Protocol-based sub-clients**:

```
┌──────────────────────────────────────────────────┐
│                  LLMClient (Facade)               │
│  Delegates to specialized sub-clients             │
│  Backward-compatible: all existing methods work   │
├──────────────────────────────────────────────────┤
│  ChatClient          │ /v1/chat/completions       │
│  AnthropicClient     │ /v1/messages               │
│  ResponsesClient     │ /v1/responses              │
│  StreamingClient     │ SSE streaming              │
│  ThinkingClient      │ Reasoning/extended thinking│
│  ModelInfoClient     │ Model discovery & info     │
│  NativeChatClient    │ /api/v1/chat (19 events)   │
└──────────────────────────────────────────────────┘
```

**Files**: `llm/chat_client.py`, `llm/anthropic_client.py`, `llm/responses_client.py`, `llm/streaming_client.py`, `llm/thinking_client.py`, `llm/model_info_client.py`, `llm/native_chat_client.py`

**Protocol contracts**: `llm/protocols.py` defines `runtime_checkable` Protocol classes.

### Domain-Split Constants (ARCH-2)

`config/constants.py` (854 lines, 205 constants) was converted to a **package with 15 domain files**:

```
config/constants/
├── __init__.py      # Re-exports everything (backward-compatible)
├── version.py       # VERSION, MIN_PYTHON_VERSION
├── server.py        # Host, port, logging, env vars
├── api.py           # Endpoints, HTTP status codes, format constants
├── timeouts.py      # All timeout/retry/TTL constants
├── models.py        # Default model names, role keywords
├── errors.py        # Error message strings
├── limits.py        # Min/max validation bounds
├── sampling.py      # Default sampling parameters
├── streaming.py     # SSE parsing constants
├── thinking.py      # Thinking/reasoning constants
├── security.py      # SSRF protection, blocked IPs
├── images.py        # Vision/image constants
├── mcp.py           # MCP paths and packages
├── selection.py     # Smart model selection weights
└── testing.py       # Test timeouts and markers
```

**Backward-compatible**: `from config.constants import X` still works via `__init__.py` re-exports.

### Native Chat Client (OPP-19)

New sub-client for LM Studio's native `/api/v1/chat` endpoint with **19 SSE event types**:

```
chat.start → model_load.{start,progress,end} → prompt_processing.{start,progress,end}
→ reasoning.{start,delta,end} → tool_call.{start,arguments,success,failure}
→ message.{start,delta,end} → error → chat.end
```

**Parser**: `llm/native_sse_parser.py` — yields `NativeSSEEvent(event_type, data)` frozen dataclasses.

### Agent Profiles (OPP-31)

User-defined agent slots with auto-resolved model configuration:

- **Agent Slot** = user-defined role + assigned model + auto-tuned parameters
- **6-family knowledge base**: Qwen, DeepSeek, Llama, Mistral, Gemma, Phi — vendor-researched overlays
- **Config layering**: critical constraints > user overrides > family overlay > role template > defaults
- **MCP tools**: `create_agent`, `list_agents`, `remove_agent`, `list_roles`, `create_role`

**Files**: `tools/profiles.py`, `model_registry/profiles.py`, `model_registry/knowledge_base.py`

### Additional v5.0.0 Features

| Feature | OPP | Description |
|---------|-----|-------------|
| Reasoning Effort | OPP-21 | `reasoning_effort` parameter (low/medium/high) |
| Model Auto-Download | OPP-24 | `lms_download_model` tool via REST API |
| Advanced Load Params | OPP-27 | GPU offload, context length, keep-alive config |
| API Authentication | OPP-28 | `api_key` parameter on all completions |
| Log-Probabilities | OPP-29 | `logprobs` and `top_logprobs` parameters |
| Ephemeral MCP | OPP-25 | Spawn temporary MCP servers per-session |
| Smart Selection | OPP-08 | `select_best_model` tool with capability matching |

---

## v5.1.0 Round G — Reliability Modules

Round G added 5 new modules to the autonomous agent loop, all wired into `_execute_tools_sequential` and `_execute_tools_parallel`:

```
┌─────────────────────────────────────────────────────────┐
│              Tool Execution Pipeline (v5.1.0)            │
│                                                          │
│  LLM Response → Extract Tool Calls                       │
│       │                                                  │
│       ▼                                                  │
│  ┌─────────────────┐                                     │
│  │ ToolCallGuard    │ Pre-dispatch validation (OPP-33)   │
│  │                  │ Circuit breaker (OPP-44)           │
│  └────────┬────────┘                                     │
│           ▼                                              │
│  ┌─────────────────┐                                     │
│  │ ToolResultCache  │ Allowlist-based, TTL + LRU (OPP-40)│
│  │                  │ Cache hit → skip dispatch           │
│  └────────┬────────┘                                     │
│           ▼                                              │
│  ┌─────────────────┐                                     │
│  │ ToolCallTracker  │ Start/end timestamps (OPP-37)      │
│  │                  │ Orphan detection on timeout         │
│  └────────┬────────┘                                     │
│           ▼                                              │
│      dispatcher.dispatch()                               │
│           │                                              │
│           ▼                                              │
│  ┌─────────────────┐                                     │
│  │ModelHealthTracker│ Per-model error budget (OPP-45)    │
│  │                  │ Advisory degradation states         │
│  └─────────────────┘                                     │
│                                                          │
│  ┌─────────────────┐                                     │
│  │AdaptiveTimeout   │ p95-based timeout adaptation       │
│  │  Manager         │ Per-model, per-endpoint (OPP-46)   │
│  └─────────────────┘                                     │
└─────────────────────────────────────────────────────────┘
```

**Files**: `tools/tool_call_guard.py`, `tools/tool_call_tracker.py`, `tools/tool_result_cache.py`, `tools/model_health.py`, `tools/adaptive_timeout.py`

**Constants**: `config/constants/tool_config.py` — 15 new constants (thresholds, TTLs, feature flags)

**Metrics**: `tools/loop_metrics.py` — `RoundMetrics` extended with `orphan_count`, `cache_hits`, `cache_misses`

---

## Conclusion

The architecture enables:

✅ **Dynamic MCP support** - Works with ANY MCP
✅ **Hot reload** - Add MCPs instantly (0.011ms overhead)
✅ **Generic tool discovery** - No hardcoded assumptions
✅ **Autonomous execution** - Local LLM uses tools independently
✅ **Multi-MCP sessions** - Use tools from multiple MCPs simultaneously
✅ **Facade + sub-clients** - Clean separation of concerns (v5.0.0)
✅ **Agent profiles** - Role-based model routing with auto-tuned params (v5.0.0)
✅ **4 API surfaces** - OpenAI, Anthropic, Responses, Native Chat (v5.0.0)
✅ **Future-proof** - Works with MCPs that don't exist yet!

**The result**: A truly dynamic, scalable, and maintainable MCP bridge!

---

**See Also**:
- [Quick Start Guide](QUICKSTART.md) - Get started in 5 minutes
- [API Reference](API_REFERENCE.md) - All tools documented
- [Troubleshooting](TROUBLESHOOTING.md) - Common issues solved
