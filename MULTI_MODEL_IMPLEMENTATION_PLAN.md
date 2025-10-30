# Multi-Model Support Implementation Plan

**Goal**: Enable autonomous tools to use different LLM models simultaneously for specialized tasks (e.g., RAG exploration with reasoning model + code generation with coding model).

---

## Overview

### Current State
- ✅ LM Studio supports multiple loaded models
- ✅ LLMClient supports model selection via `model` parameter
- ❌ Autonomous tools don't expose model parameter to users

### Target State
- ✅ All 4 autonomous tools accept optional `model` parameter
- ✅ Users can specify different models for different tasks
- ✅ Parallel multi-model workflows enabled
- ✅ Backward compatible (optional parameter)

---

## Files to Modify

### 1. Core Implementation
- **`tools/dynamic_autonomous.py`** (658 lines)
  - Modify `DynamicAutonomousAgent.__init__()` to accept model
  - Update 3 autonomous methods to pass model to LLMClient
  - Lines to modify: ~50-80, ~200-250, ~400-450, ~600-650

### 2. Tool Registration
- **`tools/dynamic_autonomous_register.py`** (270 lines)
  - Add `model` parameter to 4 tool signatures
  - Update docstrings with model examples
  - Lines to modify: ~27-95, ~97-160, ~162-217, ~219-266

### 3. Documentation
- **`docs/API_REFERENCE.md`** (~600 lines)
  - Add model parameter to all 4 autonomous tools
  - Add multi-model workflow examples
  - Document model naming conventions
  - Section: "Dynamic Autonomous Tools" (~line 200-500)

- **`docs/QUICKSTART.md`** (~300 lines)
  - Add "Multi-Model Workflows" section
  - Provide 2-3 concrete examples
  - Section: After "Common Use Cases" (~line 150)

- **`README.md`** (~425 lines)
  - Add multi-model capability to features list
  - Brief example in Quick Start section
  - Lines: ~20-30 (features), ~60-70 (example)

### 4. Testing
- **Create: `test_multi_model.py`** (new file)
  - Test single model workflows (existing behavior)
  - Test multi-model parallel workflows
  - Test model parameter validation
  - Test fallback to default model

---

## Implementation Steps

### Step 1: Code Review & Analysis (15 min)
**Status**: Pending

**Tasks**:
- Read `tools/dynamic_autonomous.py` thoroughly
- Identify where LLMClient is instantiated
- Understand how model parameter flows
- Map out all modification points

**Deliverable**: Clear understanding of code structure

---

### Step 2: Modify DynamicAutonomousAgent (30 min)
**Status**: Pending

**Changes in `tools/dynamic_autonomous.py`**:

```python
class DynamicAutonomousAgent:
    def __init__(self, llm_client=None, mcp_discovery=None):
        """Initialize agent with optional LLM client."""
        # HOT RELOAD: Store path only, not instance
        if mcp_discovery:
            self.mcp_json_path = mcp_discovery.mcp_json_path
        else:
            temp_discovery = MCPDiscovery()
            self.mcp_json_path = temp_discovery.mcp_json_path

        # Store default LLM client
        self.llm = llm_client or LLMClient()

    async def autonomous_with_mcp(
        self,
        mcp_name: str,
        task: str,
        max_rounds: int = DEFAULT_MAX_ROUNDS,
        max_tokens: Union[int, str] = "auto",
        model: Optional[str] = None  # ✅ NEW PARAMETER
    ) -> str:
        """Execute task with specific model."""

        # ✅ NEW: Use specified model or default
        llm = LLMClient(model=model) if model else self.llm

        # Rest of implementation uses `llm` instead of `self.llm`
        ...
```

**Apply to 3 methods**:
1. `autonomous_with_mcp()`
2. `autonomous_with_multiple_mcps()`
3. `autonomous_discover_and_execute()`

**Testing**: Verify each method compiles and accepts model parameter

---

### Step 3: Update Tool Registration (30 min)
**Status**: Pending

**Changes in `tools/dynamic_autonomous_register.py`**:

```python
@mcp.tool()
async def autonomous_with_mcp(
    mcp_name: Annotated[str, Field(...)],
    task: Annotated[str, Field(...)],
    max_rounds: Annotated[int, Field(...)] = DEFAULT_MAX_ROUNDS,
    max_tokens: Annotated[Union[int, str], Field(...)] = "auto",
    model: Annotated[Optional[str], Field(  # ✅ NEW PARAMETER
        description="Optional model name (default: currently loaded model). "
                    "Examples: 'qwen/qwen-2.5-coder-32b-instruct', "
                    "'mistralai/magistral-small-2509', 'nomic-ai/nomic-embed-text-v1.5'"
    )] = None
) -> str:
    """
    Execute task autonomously using tools from a SINGLE MCP.

    ... existing docstring ...

    Args:
        mcp_name: Name of the MCP to use
        task: Task description
        max_rounds: Maximum iterations (default: 10000)
        max_tokens: Max tokens per response (default: "auto")
        model: Optional model name for task-specific model selection.  # ✅ NEW
               Use different models for different tasks:
               - Coding: "qwen/qwen-2.5-coder-32b-instruct"
               - Reasoning: "mistralai/magistral-small-2509"
               - Embeddings: "nomic-ai/nomic-embed-text-v1.5"

    ... rest of docstring ...

    Examples:
        # Use specific model
        autonomous_with_mcp(
            mcp_name="filesystem",
            task="Generate unit tests",
            model="qwen/qwen-2.5-coder-32b-instruct"
        )

        # Default model (current behavior)
        autonomous_with_mcp(
            mcp_name="filesystem",
            task="Read files"
        )
    """
    return await agent.autonomous_with_mcp(
        mcp_name=mcp_name,
        task=task,
        max_rounds=max_rounds,
        max_tokens=max_tokens,
        model=model  # ✅ NEW: Pass model parameter
    )
```

**Apply to 3 tools**:
1. `autonomous_with_mcp()`
2. `autonomous_with_multiple_mcps()`
3. `autonomous_discover_and_execute()`

**Note**: `list_available_mcps()` doesn't need model parameter (it's just listing MCPs)

**Testing**: Verify tools register correctly with FastMCP

---

### Step 4: Update API Documentation (45 min)
**Status**: Pending

**Changes in `docs/API_REFERENCE.md`**:

#### Add to each autonomous tool section:

```markdown
### Parameters

... existing parameters ...

- `model` (str, optional): Model name for task-specific selection
  - **Default**: Currently loaded model in LM Studio
  - **Format**: Use exact model identifier from LM Studio
  - **Examples**:
    - `"qwen/qwen-2.5-coder-32b-instruct"` - Coding tasks
    - `"mistralai/magistral-small-2509"` - Reasoning/analysis
    - `"nomic-ai/nomic-embed-text-v1.5"` - Embeddings
  - **Note**: Model must be loaded in LM Studio first (`lms load <model>`)
```

#### Add new section: "Multi-Model Workflows"

```markdown
## Multi-Model Workflows

### Overview

Use different models simultaneously for specialized tasks.

### Prerequisites

1. Load multiple models in LM Studio:
   ```bash
   lms load qwen/qwen-2.5-coder-32b-instruct
   lms load mistralai/magistral-small-2509
   lms ps  # Verify both loaded
   ```

2. Use model parameter in autonomous tools

### Example 1: Parallel RAG + Coding

```python
# In Claude Code, run both tasks in parallel
"Run these two tasks in parallel:
1. Use autonomous_with_mcp with filesystem MCP and magistral model to analyze
   all Python files and build a knowledge graph
2. Use autonomous_with_mcp with filesystem MCP and qwen-coder model to
   generate unit tests for all functions"
```

Claude Code will execute:
```python
import asyncio

results = await asyncio.gather(
    # RAG analysis with reasoning model
    autonomous_with_mcp(
        mcp_name="filesystem",
        task="Analyze all Python files, find patterns, build knowledge graph",
        model="mistralai/magistral-small-2509"
    ),

    # Code generation with coding model
    autonomous_with_mcp(
        mcp_name="filesystem",
        task="Generate unit tests for all functions in tools/",
        model="qwen/qwen-2.5-coder-32b-instruct"
    )
)
```

### Example 2: Task-Specific Model Selection

```python
# Use reasoning model for architecture analysis
autonomous_with_mcp(
    "memory",
    "Analyze codebase architecture and create knowledge graph",
    model="mistralai/magistral-small-2509"
)

# Use coding model for implementation
autonomous_with_mcp(
    "filesystem",
    "Implement the proposed architecture changes",
    model="qwen/qwen-2.5-coder-32b-instruct"
)
```

### Example 3: Embeddings for RAG

```python
# Generate embeddings with embedding model
autonomous_with_mcp(
    "filesystem",
    "Read all markdown docs and generate vector embeddings",
    model="nomic-ai/nomic-embed-text-v1.5"
)
```

### Best Practices

1. **Load models first**: Use `lms load` before autonomous execution
2. **Choose appropriately**:
   - Coding tasks → Qwen Coder
   - Reasoning/analysis → Magistral
   - Embeddings → Nomic Embed
3. **Check memory**: Multiple 32B models need significant RAM
4. **Use exact names**: Model name must match `lms ps` output
```

**Testing**: Review documentation for clarity and completeness

---

### Step 5: Update Quick Start Guide (30 min)
**Status**: Pending

**Changes in `docs/QUICKSTART.md`**:

Add after "Common Use Cases" section:

```markdown
## Multi-Model Workflows

### Load Multiple Models

```bash
# Install lms CLI (one-time)
brew install lmstudio-ai/lms/lms

# Load multiple models
lms load qwen/qwen-2.5-coder-32b-instruct
lms load mistralai/magistral-small-2509

# Verify both loaded
lms ps
```

### Use Different Models for Different Tasks

```python
# Reasoning model for analysis
autonomous_with_mcp(
    "filesystem",
    "Analyze project architecture",
    model="mistralai/magistral-small-2509"
)

# Coding model for implementation
autonomous_with_mcp(
    "filesystem",
    "Generate unit tests",
    model="qwen/qwen-2.5-coder-32b-instruct"
)
```

### Parallel Multi-Model Execution

In Claude Code:
```
Run in parallel:
1. Use magistral model to explore and analyze all files
2. Use qwen-coder model to generate tests
```

Both tasks execute simultaneously with different models! ⚡
```

**Testing**: Ensure examples are clear and actionable

---

### Step 6: Update README (15 min)
**Status**: Pending

**Changes in `README.md`**:

Update "Core Features" section:

```markdown
### 1. Dynamic MCP Discovery
... existing content ...

### 2. Hot Reload
... existing content ...

### 3. Multi-Model Support ⚡ NEW!

Use different models for specialized tasks:
- Reasoning model for analysis
- Coding model for implementation
- Embedding model for RAG

```python
# Use specific model
autonomous_with_mcp(
    "filesystem",
    "Generate unit tests",
    model="qwen/qwen-2.5-coder-32b-instruct"
)
```

Run multiple models in parallel for complex workflows!
```

**Testing**: Verify README flows well with new content

---

### Step 7: Create Test Script (45 min)
**Status**: Pending

**Create `test_multi_model.py`**:

```python
#!/usr/bin/env python3
"""
Test multi-model support in autonomous tools.

Prerequisites:
- LM Studio running with API enabled
- At least 2 models loaded (test with available models)

Run: python3 test_multi_model.py
"""

import asyncio
from tools.dynamic_autonomous import DynamicAutonomousAgent, DEFAULT_MAX_ROUNDS

async def test_default_model():
    """Test without model parameter (existing behavior)."""
    print("\n" + "="*80)
    print("TEST 1: Default model (existing behavior)")
    print("="*80)

    agent = DynamicAutonomousAgent()

    result = await agent.autonomous_with_mcp(
        mcp_name="filesystem",
        task="List files in current directory",
        max_rounds=10
    )

    print(f"✅ Result: {result[:200]}...")
    assert len(result) > 0
    print("✅ TEST 1 PASSED: Default model works")


async def test_specific_model():
    """Test with specific model parameter."""
    print("\n" + "="*80)
    print("TEST 2: Specific model parameter")
    print("="*80)

    agent = DynamicAutonomousAgent()

    # Use first available loaded model
    result = await agent.autonomous_with_mcp(
        mcp_name="filesystem",
        task="Count Python files in current directory",
        max_rounds=10,
        model="qwen/qwen-2.5-coder-32b-instruct"  # Change to your loaded model
    )

    print(f"✅ Result: {result[:200]}...")
    assert len(result) > 0
    print("✅ TEST 2 PASSED: Specific model works")


async def test_parallel_models():
    """Test parallel execution with different models."""
    print("\n" + "="*80)
    print("TEST 3: Parallel multi-model execution")
    print("="*80)

    agent = DynamicAutonomousAgent()

    # Run two tasks in parallel with different models
    results = await asyncio.gather(
        agent.autonomous_with_mcp(
            mcp_name="filesystem",
            task="List Python files",
            max_rounds=10,
            model="qwen/qwen-2.5-coder-32b-instruct"
        ),
        agent.autonomous_with_mcp(
            mcp_name="filesystem",
            task="Count total files",
            max_rounds=10,
            model="mistralai/magistral-small-2509"
        )
    )

    print(f"✅ Result 1 (qwen): {results[0][:100]}...")
    print(f"✅ Result 2 (magistral): {results[1][:100]}...")

    assert len(results) == 2
    assert all(len(r) > 0 for r in results)
    print("✅ TEST 3 PASSED: Parallel multi-model works")


async def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("MULTI-MODEL SUPPORT TESTS")
    print("="*80)

    try:
        await test_default_model()
        await test_specific_model()
        await test_parallel_models()

        print("\n" + "="*80)
        print("✅ ALL TESTS PASSED!")
        print("="*80)

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
```

**Testing**: Run script with multiple loaded models

---

### Step 8: Integration Testing (30 min)
**Status**: Pending

**Test scenarios**:

1. **Single model (backward compatibility)**
   ```bash
   # Load one model
   lms load qwen/qwen-2.5-coder-32b-instruct

   # Test without model parameter
   python3 test_multi_model.py
   ```

2. **Multiple models (new feature)**
   ```bash
   # Load two models
   lms load qwen/qwen-2.5-coder-32b-instruct
   lms load mistralai/magistral-small-2509

   # Test with model parameter
   python3 test_multi_model.py
   ```

3. **Invalid model name (error handling)**
   ```python
   # Should handle gracefully
   autonomous_with_mcp(
       "filesystem",
       "task",
       model="nonexistent-model"
   )
   # Expected: Clear error message
   ```

4. **Parallel execution (real workflow)**
   ```
   In Claude Code:
   "Run in parallel: use magistral to analyze files, use qwen-coder to generate tests"
   ```

**Success criteria**:
- ✅ Backward compatibility maintained
- ✅ New model parameter works
- ✅ Parallel execution works
- ✅ Error handling is clear

---

### Step 9: Commit Changes (15 min)
**Status**: Pending

**Commit message**:
```
feat: add multi-model support for specialized workflows

Enable autonomous tools to use different LLM models for specialized tasks:
- Reasoning model for analysis and RAG
- Coding model for implementation
- Embedding model for vector operations

Changes:
- Add optional `model` parameter to all 4 autonomous tools
- Update DynamicAutonomousAgent to pass model to LLMClient
- Document multi-model workflows with examples
- Add test_multi_model.py for validation

Benefits:
- Parallel multi-model workflows (e.g., RAG + coding simultaneously)
- Task-specific model selection
- Backward compatible (model optional, defaults to current behavior)
- Enables advanced workflows like agentic RAG

Examples:
  autonomous_with_mcp(
      "filesystem",
      "Generate tests",
      model="qwen/qwen-2.5-coder-32b-instruct"
  )

🎉 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## Timeline Estimate

| Step | Duration | Cumulative |
|------|----------|------------|
| 1. Code Review | 15 min | 15 min |
| 2. Modify Agent | 30 min | 45 min |
| 3. Update Registration | 30 min | 75 min |
| 4. API Docs | 45 min | 120 min |
| 5. Quick Start | 30 min | 150 min |
| 6. README | 15 min | 165 min |
| 7. Test Script | 45 min | 210 min |
| 8. Integration Testing | 30 min | 240 min |
| 9. Commit | 15 min | 255 min |

**Total: ~4.5 hours** (conservative estimate)

---

## Risk Assessment

### Low Risk ✅
- **Backward compatibility**: Optional parameter, defaults to current behavior
- **Simple implementation**: Just parameter passing
- **Well-tested pattern**: LLMClient already supports model selection

### Medium Risk ⚠️
- **User error**: Wrong model name → Clear error message needed
- **Memory limits**: Multiple large models → Document requirements
- **Model not loaded**: Runtime error → Graceful handling needed

### Mitigation
- Add validation for model parameter
- Document memory requirements
- Provide clear error messages
- Test with multiple scenarios

---

## Success Criteria

### Functional
- ✅ All 4 autonomous tools accept optional `model` parameter
- ✅ Model parameter passed correctly to LLMClient
- ✅ Parallel multi-model workflows work
- ✅ Backward compatible (no breaking changes)

### Documentation
- ✅ API Reference updated with model parameter
- ✅ Multi-model workflow examples provided
- ✅ Quick Start guide includes multi-model section
- ✅ README mentions multi-model capability

### Testing
- ✅ Test script passes with single model
- ✅ Test script passes with multiple models
- ✅ Parallel execution test passes
- ✅ Error handling works correctly

### Quality
- ✅ Code follows existing patterns
- ✅ Documentation is clear and actionable
- ✅ Commit message is comprehensive
- ✅ No regressions in existing functionality

---

## Next Actions

**Ready to proceed?**

I will:
1. ✅ Start with Step 1 (Code Review)
2. ✅ Implement changes systematically
3. ✅ Test after each major change
4. ✅ Update todo list as I progress
5. ✅ Commit when all tests pass

**Estimated completion**: 4-5 hours of focused work

Shall I begin implementation?
