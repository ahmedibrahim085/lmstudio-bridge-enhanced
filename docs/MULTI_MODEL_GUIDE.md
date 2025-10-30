# Multi-Model Support Guide

**LM Studio Bridge Enhanced v2 - Multi-Model Feature**

Use different models for different tasks to maximize quality and performance.

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Model Selection Strategy](#model-selection-strategy)
4. [Common Workflows](#common-workflows)
5. [Best Practices](#best-practices)
6. [Performance Considerations](#performance-considerations)
7. [Troubleshooting](#troubleshooting)

---

## Overview

### What is Multi-Model Support?

Multi-model support allows you to specify which LM Studio model to use for each autonomous task. Different models excel at different things:

- **Reasoning models** (Magistral, Qwen-Thinking) → Analysis, planning, problem-solving
- **Coding models** (Qwen-Coder, DeepSeek-Coder) → Code generation, refactoring, testing
- **General models** (Llama, Mixtral) → Balanced performance for mixed tasks

### Why Use It?

**Better Results**: Match the model's strengths to the task requirements
**Flexibility**: Chain different models in multi-step workflows
**Backward Compatible**: Existing code continues to work with default model
**Easy**: Just add `model="model-name"` parameter

---

## Quick Start

### 1. Check Available Models

```python
# List models currently loaded in LM Studio
list_models()

# Example output:
# Available models (3):
# 1. qwen/qwen3-coder-30b
# 2. mistralai/magistral-small-2509
# 3. deepseek/deepseek-coder-33b
```

### 2. Use a Specific Model

```python
# Default behavior (no model parameter)
autonomous_with_mcp(
    mcp_name="filesystem",
    task="List Python files"
)  # Uses default model from config

# Specify a model
autonomous_with_mcp(
    mcp_name="filesystem",
    task="Analyze codebase architecture",
    model="mistralai/magistral-small-2509"  # Use reasoning model
)
```

### 3. Handle Errors

```python
# If model not found, you get a helpful error:
autonomous_with_mcp(
    mcp_name="filesystem",
    task="task",
    model="nonexistent-model"
)
# Returns:
# "Error: Model 'nonexistent-model' not found.
#  Available models: qwen/qwen3-coder-30b, mistralai/magistral-small-2509"
```

**Solution**: Load the model in LM Studio first, then retry.

---

## Model Selection Strategy

### Model Types and Use Cases

| Model Type | Examples | Best For | Not Ideal For |
|------------|----------|----------|---------------|
| **Reasoning** | Magistral, Qwen-Thinking, o1-preview | Complex analysis, planning, architecture review, multi-step reasoning | Simple tasks, code generation |
| **Coding** | Qwen-Coder, DeepSeek-Coder, CodeLlama | Code generation, refactoring, test writing, debugging | Analysis, documentation, reasoning |
| **General** | Llama 3, Mixtral, Gemma | Mixed tasks, documentation, simple code + analysis | Specialized tasks |

### Task → Model Mapping

#### Code Analysis Tasks
```python
# Architecture review
model="mistralai/magistral-small-2509"  # Reasoning

# Design pattern identification
model="mistralai/magistral-small-2509"  # Reasoning

# Code quality analysis
model="mistralai/magistral-small-2509"  # Reasoning

# Performance bottleneck detection
model="mistralai/magistral-small-2509"  # Reasoning
```

#### Code Generation Tasks
```python
# Function implementation
model="qwen/qwen3-coder-30b"  # Coding

# Test generation
model="qwen/qwen3-coder-30b"  # Coding

# Refactoring
model="qwen/qwen3-coder-30b"  # Coding

# Bug fixing
model="qwen/qwen3-coder-30b"  # Coding
```

#### Mixed Tasks
```python
# Documentation (code understanding + writing)
model="default"  # General or omit parameter

# Simple file operations
model="default"  # General or omit parameter

# Data analysis + visualization code
model="qwen/qwen3-coder-30b"  # Coding (leans toward code)
```

---

## Common Workflows

### Workflow 1: Analysis → Implementation

**Pattern**: Reasoning model analyzes, coding model implements

```python
# Step 1: Reasoning model analyzes architecture
analysis = autonomous_with_mcp(
    mcp_name="filesystem",
    task="Analyze the codebase structure in tools/ and identify missing unit tests",
    model="mistralai/magistral-small-2509"  # Reasoning
)

print("Analysis:", analysis)

# Step 2: Coding model generates tests based on analysis
tests = autonomous_with_mcp(
    mcp_name="filesystem",
    task=f"""Based on this analysis: {analysis}

    Generate comprehensive unit tests for the identified functions.
    Use pytest and follow existing test patterns.""",
    model="qwen/qwen3-coder-30b"  # Coding
)

print("Tests generated:", tests)
```

**When to use**:
- Complex projects requiring understanding before action
- Quality-critical implementations
- When you want best-of-both-worlds (reasoning + coding)

---

### Workflow 2: Multi-Step Code Pipeline

**Pattern**: Multiple coding steps with different models

```python
# Step 1: Architecture with reasoning model
architecture = autonomous_with_mcp(
    "filesystem",
    "Design module structure for new authentication system",
    model="mistralai/magistral-small-2509"
)

# Step 2: Implementation with coding model
implementation = autonomous_with_mcp(
    "filesystem",
    f"Implement the authentication system based on: {architecture}",
    model="qwen/qwen3-coder-30b"
)

# Step 3: Tests with coding model (same or different)
tests = autonomous_with_mcp(
    "filesystem",
    "Generate integration tests for the authentication system",
    model="deepseek/deepseek-coder-33b"  # Try different coding model
)

# Step 4: Documentation with general model
docs = autonomous_with_mcp(
    "filesystem",
    "Create user-facing documentation for authentication",
    # Omit model - use default
)
```

---

### Workflow 3: Parallel Processing

**Pattern**: Run multiple models in parallel (manually orchestrate)

```python
import asyncio

async def parallel_analysis():
    # Run different models on same task to compare
    tasks = [
        autonomous_with_mcp(
            "filesystem",
            "Identify security vulnerabilities in auth module",
            model="mistralai/magistral-small-2509"
        ),
        autonomous_with_mcp(
            "filesystem",
            "Identify security vulnerabilities in auth module",
            model="qwen/qwen3-thinking-small-2509"
        )
    ]

    results = await asyncio.gather(*tasks)

    # Compare results from different reasoning models
    return results

# Best insights from multiple perspectives
results = asyncio.run(parallel_analysis())
```

**When to use**:
- Critical analysis requiring multiple perspectives
- Comparing model capabilities
- Redundancy for important decisions

---

### Workflow 4: Single-MCP with Model Switching

**Pattern**: Different tasks within same MCP, different models

```python
# Use filesystem MCP throughout, but switch models per task

# Task 1: Count files (simple - use default)
file_count = autonomous_with_mcp(
    "filesystem",
    "Count all Python files in project"
)

# Task 2: Analyze architecture (complex - use reasoning)
architecture = autonomous_with_mcp(
    "filesystem",
    "Analyze project architecture and identify design patterns",
    model="mistralai/magistral-small-2509"
)

# Task 3: Generate code (implementation - use coding)
code = autonomous_with_mcp(
    "filesystem",
    "Generate helper functions based on architecture analysis",
    model="qwen/qwen3-coder-30b"
)
```

---

### Workflow 5: Multi-MCP with Consistent Model

**Pattern**: Multiple MCPs, same model throughout

```python
# Use reasoning model across filesystem + memory + fetch
result = autonomous_with_multiple_mcps(
    mcp_names=["filesystem", "memory", "fetch"],
    task="""
    1. Analyze local codebase structure (filesystem)
    2. Fetch best practices from documentation online (fetch)
    3. Create a knowledge graph comparing our implementation to best practices (memory)
    4. Provide recommendations
    """,
    model="mistralai/magistral-small-2509"  # Reasoning for entire workflow
)
```

---

## Best Practices

### 1. Use Model Names Exactly

✅ **Correct**:
```python
model="qwen/qwen3-coder-30b"  # Exact match from list_models()
```

❌ **Wrong**:
```python
model="qwen3-coder"  # Missing organization prefix
model="Qwen/Qwen3-Coder-30B"  # Wrong capitalization
model="qwen-coder"  # Incomplete name
```

**Tip**: Always copy model name from `list_models()` output!

---

### 2. Match Model to Task Complexity

✅ **Correct**:
```python
# Simple task - use default
autonomous_with_mcp("filesystem", "List files")

# Complex analysis - use reasoning
autonomous_with_mcp(
    "filesystem",
    "Analyze entire codebase architecture",
    model="mistralai/magistral-small-2509"
)

# Code generation - use coding model
autonomous_with_mcp(
    "filesystem",
    "Generate unit tests",
    model="qwen/qwen3-coder-30b"
)
```

❌ **Wasteful**:
```python
# Using reasoning model for trivial task
autonomous_with_mcp(
    "filesystem",
    "List files",
    model="mistralai/magistral-small-2509"  # Overkill!
)
```

---

### 3. Load Models Before Use

**Workflow**:

1. Open LM Studio
2. Load model(s) you need
3. Wait for loading to complete
4. Verify with `list_models()`
5. Use in autonomous tasks

**Example**:
```python
# Check loaded models first
available = list_models()
print(available)

# If model not loaded, you'll get clear error:
# "Error: Model 'qwen/qwen3-coder-30b' not found. Available models: ..."

# Load model in LM Studio, then retry
```

---

### 4. Use Default for Most Tasks

**Philosophy**: Only specify `model` when you need something special.

✅ **Recommended**:
```python
# 80% of tasks - use default (omit parameter)
autonomous_with_mcp("filesystem", "Read and summarize README.md")

# 20% of tasks - specify model for special needs
autonomous_with_mcp(
    "filesystem",
    "Complex architectural analysis",
    model="mistralai/magistral-small-2509"
)
```

❌ **Avoid**:
```python
# Don't over-specify
autonomous_with_mcp("filesystem", "trivial task", model="...")  # Not needed
```

---

### 5. Chain Models Strategically

**Pattern**: Reasoning → Coding → General

```python
# 1. Reasoning: Understand problem
plan = autonomous_with_mcp(
    "filesystem",
    "Analyze requirements and create implementation plan",
    model="mistralai/magistral-small-2509"
)

# 2. Coding: Implement solution
code = autonomous_with_mcp(
    "filesystem",
    f"Implement this plan: {plan}",
    model="qwen/qwen3-coder-30b"
)

# 3. General: Document (or omit model)
docs = autonomous_with_mcp(
    "filesystem",
    f"Document this implementation: {code}"
)
```

---

### 6. Handle Errors Gracefully

```python
def autonomous_with_fallback(mcp_name, task, preferred_model, fallback_model=None):
    """Try preferred model, fall back to default if not available."""

    try:
        return autonomous_with_mcp(
            mcp_name=mcp_name,
            task=task,
            model=preferred_model
        )
    except Exception as e:
        if "not found" in str(e):
            print(f"Model {preferred_model} not available, using fallback")

            if fallback_model:
                return autonomous_with_mcp(mcp_name, task, model=fallback_model)
            else:
                return autonomous_with_mcp(mcp_name, task)  # Use default
        else:
            raise

# Usage
result = autonomous_with_fallback(
    "filesystem",
    "Analyze code",
    preferred_model="mistralai/magistral-small-2509",
    fallback_model="qwen/qwen3-coder-30b"
)
```

---

## Performance Considerations

### Model Validation Overhead

**Cached validation**: < 0.1ms (negligible)
**Cold validation**: ~100-200ms (one-time per task)

**Impact**: Essentially zero for most tasks.

```python
# First call: ~100ms validation
result1 = autonomous_with_mcp("filesystem", "task1", model="qwen/qwen3-coder-30b")

# Subsequent calls: < 0.1ms validation (cached)
result2 = autonomous_with_mcp("filesystem", "task2", model="qwen/qwen3-coder-30b")
result3 = autonomous_with_mcp("filesystem", "task3", model="qwen/qwen3-coder-30b")
```

**Cache TTL**: 60 seconds

---

### Model Loading Time

**Not our responsibility**: LM Studio manages model loading

**Your responsibility**: Ensure model is loaded before calling tool

```python
# If model not loaded, LM Studio will return error immediately
# No waiting for load - you must load in LM Studio first
```

---

### Model Switching Cost

**Zero cost**: Each tool call is independent

```python
# No penalty for switching models between calls
result1 = autonomous_with_mcp("filesystem", "task1", model="model-a")
result2 = autonomous_with_mcp("filesystem", "task2", model="model-b")
result3 = autonomous_with_mcp("filesystem", "task3", model="model-a")
# All three have same per-call overhead
```

---

### Memory Usage

**ModelValidator cache**: Minimal (list of model IDs)
**LLMClient instances**: One per unique model used
**Cleanup**: Automatic garbage collection

**Memory footprint**: < 10MB increase for multi-model support

---

### Recommendation

**Use multi-model freely**:
- Validation overhead is negligible
- No model switching penalty
- Memory impact minimal
- Quality gains significant

---

## Troubleshooting

### Issue 1: "Model not found"

**Symptom**:
```
Error: Model 'qwen/qwen3-coder' not found.
Available models: mistralai/magistral-small-2509, deepseek/deepseek-coder-33b
```

**Causes**:
1. Model not loaded in LM Studio
2. Typo in model name
3. Wrong model ID format

**Solutions**:

**Solution 1**: Load model in LM Studio
```bash
# Open LM Studio → My Models → Search for model → Click "Load"
# Wait for loading to complete (progress bar)
```

**Solution 2**: Verify model name
```python
# Get exact model names
list_models()

# Copy exact name from output
model="qwen/qwen3-coder-30b"  # Must match exactly
```

**Solution 3**: Check model ID format
```python
# Correct format: organization/model-name
✅ "qwen/qwen3-coder-30b"
✅ "mistralai/magistral-small-2509"
✅ "deepseek/deepseek-coder-33b"

# Wrong format:
❌ "qwen3-coder"  # Missing organization
❌ "qwen-coder"   # Wrong name
❌ "Qwen/Qwen3"   # Wrong capitalization
```

---

### Issue 2: "Model parameter ignored"

**Symptom**: Task uses default model instead of specified model

**Causes**:
1. Using old version of lmstudio-bridge-enhanced
2. Model parameter not passed correctly

**Solutions**:

**Solution 1**: Update to v2.0.0+
```bash
cd lmstudio-bridge-enhanced
git pull
pip install -r requirements.txt --upgrade
```

**Solution 2**: Verify parameter syntax
```python
✅ Correct:
autonomous_with_mcp(
    mcp_name="filesystem",
    task="task",
    model="qwen/qwen3-coder-30b"  # Named parameter
)

❌ Wrong:
autonomous_with_mcp(
    "filesystem",
    "task",
    "qwen/qwen3-coder-30b"  # Positional (won't work)
)
```

---

### Issue 3: "Wrong model used"

**Symptom**: Different model used than specified

**Debugging**:

```python
# Add logging to verify model selection
import logging
logging.basicConfig(level=logging.INFO)

result = autonomous_with_mcp(
    "filesystem",
    "task",
    model="qwen/qwen3-coder-30b"
)
# Check logs for: "Using model: qwen/qwen3-coder-30b"
```

**Solutions**:
1. Check LM Studio logs for model switching
2. Verify model parameter spelled correctly
3. Ensure model actually loaded in LM Studio

---

### Issue 4: "Connection failed after model validation"

**Symptom**: Model validates successfully but connection fails

**Cause**: LM Studio running but not serving models

**Solution**:
```bash
# Restart LM Studio
# Load at least one model
# Verify API is running:
curl http://localhost:1234/v1/models

# Should return list of models (not error)
```

---

### Issue 5: "Performance degradation with specific model"

**Symptom**: Some models are much slower than others

**Explanation**: Normal! Different models have different sizes/speeds

**Model Performance Tiers**:
- **Small models** (7B-13B): Fast, good for simple tasks
- **Medium models** (30B-33B): Balanced, most use cases
- **Large models** (70B+): Slow but highest quality

**Solutions**:
1. Use smaller models for simple tasks
2. Use larger models only for complex analysis
3. Check LM Studio GPU/CPU utilization
4. Consider model quantization (GGUF format)

---

### Issue 6: "How do I know which model to use?"

**Quick Decision Tree**:

```
Is this a code generation task?
├─ YES → Use coding model (Qwen-Coder, DeepSeek-Coder)
└─ NO
   └─ Is this complex analysis/reasoning?
      ├─ YES → Use reasoning model (Magistral, Qwen-Thinking)
      └─ NO → Use default (omit model parameter)
```

**Still unsure?**
- Start with default
- If quality insufficient, try specialized model
- Compare results from multiple models
- Pick the best for your use case

---

### Issue 7: "Can I use multiple models in single tool call?"

**Answer**: No, one model per tool call.

**Workaround**: Chain multiple calls
```python
# Step 1: Model A
result_a = autonomous_with_mcp("filesystem", "task1", model="model-a")

# Step 2: Model B (using result from A)
result_b = autonomous_with_mcp("filesystem", f"task2: {result_a}", model="model-b")

# Final result combines both
```

---

## Examples

### Example 1: Research + Implementation

```python
# Research phase with reasoning model
research = autonomous_with_mcp(
    mcp_name="fetch",
    task="Research best practices for Python async error handling",
    model="mistralai/magistral-small-2509"
)

# Implementation phase with coding model
implementation = autonomous_with_mcp(
    mcp_name="filesystem",
    task=f"""Based on this research: {research}

    Implement error handling utilities in utils/error_handling.py
    following the identified best practices.""",
    model="qwen/qwen3-coder-30b"
)
```

---

### Example 2: Multi-File Refactoring

```python
# Step 1: Analyze codebase with reasoning model
analysis = autonomous_with_mcp(
    mcp_name="filesystem",
    task="""Analyze tools/ directory and identify:
    1. Code duplication
    2. Refactoring opportunities
    3. Suggested helper functions""",
    model="mistralai/magistral-small-2509"
)

# Step 2: Create helper functions with coding model
helpers = autonomous_with_mcp(
    mcp_name="filesystem",
    task=f"""Create utils/helpers.py with functions based on: {analysis}

    Include proper type hints and docstrings.""",
    model="qwen/qwen3-coder-30b"
)

# Step 3: Refactor existing code with coding model
refactored = autonomous_with_mcp(
    mcp_name="filesystem",
    task=f"""Refactor tools/ files to use new helpers from: {helpers}

    Maintain functionality while reducing duplication.""",
    model="qwen/qwen3-coder-30b"
)
```

---

### Example 3: Documentation + Tests

```python
# Generate tests with coding model
tests = autonomous_with_mcp(
    mcp_name="filesystem",
    task="Generate pytest tests for all functions in utils/retry_logic.py",
    model="qwen/qwen3-coder-30b"
)

# Generate documentation with default model
docs = autonomous_with_mcp(
    mcp_name="filesystem",
    task="""Create comprehensive documentation for utils/retry_logic.py:
    1. Module docstring
    2. Function docstrings
    3. Usage examples
    4. README section"""
)
```

---

## See Also

- **[API Reference](API_REFERENCE.md)** - Complete tool documentation
- **[Troubleshooting](TROUBLESHOOTING.md)** - Common issues and solutions
- **[Quick Start Guide](QUICKSTART.md)** - Get started in 5 minutes
- **[Architecture](ARCHITECTURE.md)** - How multi-model support works internally
