# Actual Code Structure - For Test Planning

**Purpose**: This document contains ACTUAL code structure from reading the files.
This will be used by local LLMs to understand what needs testing.

---

## tools/autonomous.py

### Overview
Autonomous execution tool allowing local LLMs to use MCP tools autonomously.

### Class: AutonomousExecutionTools (Line 28)

#### Methods:

**`__init__(self, llm_client: Optional[LLMClient] = None)`** - Line 31
- Initialize autonomous execution tools
- Creates default LLM client if none provided

**`_execute_autonomous_stateful(...)`** - Line 41-124
- Core implementation using stateful `/v1/responses` API
- **API Used**: `self.llm.create_response()` at line 81
- Parameters: task, session, openai_tools, executor, max_rounds, max_tokens
- Returns: Final answer string
- Error handling: Returns error messages for unexpected output

**`autonomous_filesystem_full(...)`** - Line 126-278
- Full autonomous execution with filesystem MCP tools
- **API Used**: `self.llm.create_response()` (via _execute_autonomous_stateful)
- Parameters: task, working_directory, max_rounds, max_tokens
- Returns: Final answer string
- Error handling: ValidationError, Exception

**NOTE**: Line 404 mentioned in grep results - need to check if there's `chat_completion` usage later in file

### MCP Tool Functions
Need to check if there are @mcp.tool() decorated functions

---

## tools/completions.py

### From grep results:
- Uses 3 APIs:
  - `chat_completion` (line 50)
  - `text_completion` (line 93)
  - `create_response` (line 136)

Need to read full file to document structure.

---

## tools/embeddings.py

### From grep results:
- Class has `generate_embeddings` method
- Uses `self.llm.generate_embeddings()` at line 40
- MCP tool function at line 66 calls tools.generate_embeddings at line 79

Need to read full file to document structure.

---

## tools/health.py

### From grep results:
- Uses 2 APIs:
  - `list_models` (line 42)
  - `chat_completion` (line 64)
- Has async functions at lines 35, 96

Need to read full file to document structure.

---

## tools/dynamic_autonomous.py (TESTED - for reference)

### Key patterns to learn from:
- Uses ONLY `create_response` API (lines 519, 619)
- Has model validation with ModelNotFoundError
- Returns error strings instead of raising
- Test file: tests/test_multi_model_integration.py

---

## Next Steps for Local LLM

1. Read each file completely
2. Document exact structure
3. Compare with dynamic_autonomous.py
4. Review test_multi_model_integration.py patterns
5. Propose test structure based on actual code
