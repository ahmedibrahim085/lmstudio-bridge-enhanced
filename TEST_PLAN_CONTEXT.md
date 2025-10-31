# Test Plan Context - Actual Code Structure

**Purpose**: Accurate documentation of untested modules for test planning.
**Created**: 2025-10-31
**Source**: Direct file reads of actual code

---

## Overview

We have 4 modules that need comprehensive test coverage. Each uses different LLM APIs from LLMClient.

**LLM APIs Available**:
1. `self.llm.chat_completion()` - Chat completions API
2. `self.llm.text_completion()` - Text completions API
3. `self.llm.create_response()` - Stateful responses API
4. `self.llm.generate_embeddings()` - Embeddings API
5. `self.llm.list_models()` - Model listing
6. `self.llm.health_check()` - Health check

---

## Module 1: tools/completions.py

### Class: CompletionTools (Line 11)

**Purpose**: Tools for generating completions from local LLMs

**Constructor**:
```python
def __init__(self, llm_client: Optional[LLMClient] = None):  # Line 14
    self.llm = llm_client or LLMClient()
```

### Methods:

#### 1. `chat_completion()` - Lines 22-69
```python
async def chat_completion(
    self,
    prompt: str,
    system_prompt: str = "",
    temperature: float = 0.7,
    max_tokens: int = 1024
) -> str:
```

**API Used**: `self.llm.chat_completion()` at line 50
**API Call**:
```python
response = self.llm.chat_completion(
    messages=messages,
    temperature=temperature,
    max_tokens=max_tokens
)
```

**Return**: Content string from `response["choices"][0]["message"]["content"]`
**Error Handling**: try/except, returns error string on failure
**Edge Cases**:
- No choices in response (line 58)
- Empty content (line 64)
- Exception handling (line 68)

#### 2. `text_completion()` - Lines 71-112
```python
async def text_completion(
    self,
    prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 1024,
    stop_sequences: Optional[List[str]] = None
) -> str:
```

**API Used**: `self.llm.text_completion()` at line 93
**API Call**:
```python
response = self.llm.text_completion(
    prompt=prompt,
    temperature=temperature,
    max_tokens=max_tokens,
    stop_sequences=stop_sequences
)
```

**Return**: Text from `response["choices"][0]["text"]`
**Error Handling**: try/except, returns error string on failure
**Edge Cases**:
- No choices in response (line 102)
- Empty text (line 107)
- Exception handling (line 111)

#### 3. `create_response()` - Lines 114-150
```python
async def create_response(
    self,
    input_text: str,
    previous_response_id: Optional[str] = None,
    stream: bool = False,
    model: Optional[str] = None
) -> str:
```

**API Used**: `self.llm.create_response()` at line 136
**API Call**:
```python
response = self.llm.create_response(
    input_text=input_text,
    previous_response_id=previous_response_id,
    stream=stream,
    model=model
)
```

**Return**: JSON string of response (line 144)
**Error Handling**: try/except, returns JSON error object on failure
**Edge Cases**:
- Exception handling (line 146)
- Returns JSON in all cases

### MCP Tool Registration (Lines 154-230)

Function `register_completion_tools(mcp, llm_client)` registers 3 MCP tools:
- `@mcp.tool() chat_completion()` (line 163)
- `@mcp.tool() text_completion()` (line 183)
- `@mcp.tool() create_response()` (line 206)

---

## Module 2: tools/embeddings.py

### Class: EmbeddingsTools (Line 11)

**Purpose**: Tools for generating vector embeddings from local LLMs

**Constructor**:
```python
def __init__(self, llm_client: Optional[LLMClient] = None):  # Line 14
    self.llm = llm_client or LLMClient()
```

### Methods:

#### 1. `generate_embeddings()` - Lines 22-52
```python
async def generate_embeddings(
    self,
    text: Union[str, List[str]],
    model: str = "default"
) -> str:
```

**API Used**: `self.llm.generate_embeddings()` at line 40
**API Call**:
```python
response = self.llm.generate_embeddings(
    text=text,
    model=model if model != "default" else None
)
```

**Return**: JSON string of response (line 46)
**Error Handling**: try/except, returns JSON error object on failure
**Edge Cases**:
- Single string vs list of strings
- Default model handling (line 42)
- Exception handling (line 48)

### MCP Tool Registration (Lines 56-80)

Function `register_embeddings_tools(mcp, llm_client)` registers 1 MCP tool:
- `@mcp.tool() generate_embeddings()` (line 65)

---

## Module 3: tools/health.py

### Class: HealthTools (Line 10)

**Purpose**: Tools for checking LM Studio health and status

**Constructor**:
```python
def __init__(self, llm_client: Optional[LLMClient] = None):  # Line 13
    self.llm = llm_client or LLMClient()
```

### Methods:

#### 1. `health_check()` - Lines 21-33
```python
async def health_check(self) -> str:
```

**API Used**: `self.llm.health_check()` at line 28
**API Call**:
```python
if self.llm.health_check():
    return "LM Studio API is running and accessible."
else:
    return "LM Studio API is not responding."
```

**Return**: Status message string
**Error Handling**: try/except, returns error message on failure
**Edge Cases**:
- API not responding (line 30)
- Exception handling (line 32)

#### 2. `list_models()` - Lines 35-53
```python
async def list_models(self) -> str:
```

**API Used**: `self.llm.list_models()` at line 42
**API Call**:
```python
models = self.llm.list_models()
```

**Return**: Formatted string list of models
**Error Handling**: try/except, returns error message on failure
**Edge Cases**:
- No models found (line 44)
- Exception handling (line 52)
- Formatting logic (lines 47-49)

#### 3. `get_current_model()` - Lines 55-73
```python
async def get_current_model(self) -> str:
```

**API Used**: `self.llm.chat_completion()` at line 64
**API Call**:
```python
response = self.llm.chat_completion(
    messages=[{"role": "system", "content": "What model are you?"}],
    max_tokens=10
)
```

**Return**: Model name string from response (line 70-71)
**Error Handling**: try/except, returns error message on failure
**Edge Cases**:
- Model info extraction (line 70)
- Exception handling (line 72)

### MCP Tool Registration (Lines 77-112)

Function `register_health_tools(mcp, llm_client)` registers 3 MCP tools:
- `@mcp.tool() health_check()` (line 86)
- `@mcp.tool() list_models()` (line 95)
- `@mcp.tool() get_current_model()` (line 104)

---

## Module 4: tools/autonomous.py (PARTIAL - Main autonomous methods)

### Class: AutonomousExecutionTools (Line 28)

**Purpose**: Tools for autonomous execution with MCP integration

**Constructor**:
```python
def __init__(self, llm_client: Optional[LLMClient] = None):  # Line 31
    self.llm = llm_client or LLMClient()
```

### Key Methods (from grep results):

#### 1. `_execute_autonomous_stateful()` - Lines 41-124
**API Used**: `self.llm.create_response()` at line 81
**Purpose**: Core implementation using stateful /v1/responses API

#### 2. `autonomous_filesystem_full()` - Lines 126-278+
**API Used**: `self.llm.create_response()` (via _execute_autonomous_stateful)
**Purpose**: Full autonomous execution with filesystem MCP tools

#### 3. `autonomous_persistent_session()` - Line 404 area
**API Used**: `self.llm.chat_completion()` at line 404
**API Call**:
```python
response = self.llm.chat_completion(
    messages=messages,
    tools=openai_tools,
    tool_choice="auto",
    max_tokens=actual_max_tokens
)
```

**Note**: This module is COMPLEX with multiple autonomous functions. From CODE_REVIEW_ROUND_2.md:
- Uses create_response (line 81)
- Uses chat_completion (line 404)
- Has extensive MCP integration
- Complex autonomous loop logic

---

## Reference: tools/dynamic_autonomous.py (TESTED - for pattern learning)

### What's Already Tested:

From `tests/test_multi_model_integration.py` (11 tests):
1. `test_autonomous_with_mcp_specific_model`
2. `test_autonomous_without_model_uses_default`
3. `test_invalid_model_returns_error`
4. `test_multiple_mcps_with_model`
5. `test_discover_and_execute_with_model`
6. `test_model_validation_error_handling`
7. `test_backward_compatibility_no_model_param`
8. `test_validator_initialization`
9. `test_validator_with_none_model`
10. `test_validator_with_default_string`
11. `test_integration_suite_completeness`

### Mock Patterns That Work:

```python
# Mock the agent's llm attribute directly
agent.llm = MagicMock()
agent.llm.create_response.return_value = {
    "id": "resp_test_123",
    "output": [
        {
            "type": "message",
            "content": [
                {"type": "output_text", "text": "Task complete"}
            ]
        }
    ]
}

# Mock MCP connection
with patch('tools.dynamic_autonomous.stdio_client') as mock_stdio:
    with patch('tools.dynamic_autonomous.ClientSession') as mock_session_class:
        mock_session = AsyncMock()
        mock_init_result = MagicMock()
        mock_init_result.serverInfo.name = "test-server"
        mock_session.initialize.return_value = mock_init_result

        mock_tool = MagicMock()
        mock_tool.name = "test_tool"
        mock_tool.description = "Test tool"
        mock_tool.inputSchema = {"type": "object", "properties": {}}
        mock_tools_result = MagicMock()
        mock_tools_result.tools = [mock_tool]
        mock_session.list_tools.return_value = mock_tools_result
```

---

## Test Planning Priorities

### High Priority (Simple modules, quick wins):
1. **tools/health.py** - 3 methods, simple logic, 2 APIs
2. **tools/embeddings.py** - 1 method, straightforward, 1 API

### Medium Priority (Multiple APIs, moderate complexity):
3. **tools/completions.py** - 3 methods, 3 APIs, moderate logic

### Complex Priority (Requires deep understanding):
4. **tools/autonomous.py** - Multiple methods, 2 APIs, complex autonomous logic

---

## Test Count Estimates

### tools/completions.py
- `chat_completion()`: 4-5 tests
  - Happy path with messages
  - Empty system_prompt
  - No choices in response
  - Empty content
  - Exception handling
- `text_completion()`: 4-5 tests
  - Happy path with prompt
  - With stop_sequences
  - No choices in response
  - Empty text
  - Exception handling
- `create_response()`: 3-4 tests
  - Happy path
  - With previous_response_id
  - Exception handling
  - JSON return format
- **Total**: 11-14 tests

### tools/embeddings.py
- `generate_embeddings()`: 5-6 tests
  - Happy path with single string
  - Happy path with list of strings
  - Default model handling
  - Custom model
  - Exception handling
  - JSON return format
- **Total**: 5-6 tests

### tools/health.py
- `health_check()`: 3 tests
  - API running
  - API not responding
  - Exception handling
- `list_models()`: 4 tests
  - Models found
  - No models found
  - Exception handling
  - Formatting verification
- `get_current_model()`: 3 tests
  - Model info extraction
  - Exception handling
  - Response format
- **Total**: 10 tests

### tools/autonomous.py
- Complex module requiring detailed analysis
- **Estimated**: 15-20 tests (needs Round 2 planning)

### Grand Total
- Simple modules: 26-30 tests
- Complex module: 15-20 tests
- **Overall**: 41-50 tests needed

---

## Next Steps for LLM Discussion

1. Review this accurate structure
2. Propose specific test cases for each method
3. Define mock strategies for each API
4. Create test file structure
5. Prioritize implementation order
