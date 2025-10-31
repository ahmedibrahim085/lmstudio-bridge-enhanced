# Reasoning Tokens Explained: `"reasoning_tokens": 0`

**Date**: 2025-10-31
**Context**: Understanding the `reasoning_tokens` field in LLM API responses

---

## Quick Answer

**`"reasoning_tokens": 0`** means the LLM did NOT use any internal "thinking" tokens for this response.

---

## Part 1: General LLM Context (OpenAI Standard)

### What Are Reasoning Tokens?

**Reasoning tokens** are **hidden tokens** used by advanced LLMs for internal "thinking" before producing the final answer. They represent the model's internal reasoning process that helps it solve complex problems.

### Key Characteristics

1. **Hidden from User**
   - These tokens are NOT shown in the response text
   - You don't see the model's "thinking process"
   - They're only visible in API metadata

2. **Used for Complex Reasoning**
   - Mathematical calculations
   - Logical deduction
   - Multi-step problem solving
   - Code generation with planning

3. **Counted Separately**
   ```json
   {
     "usage": {
       "prompt_tokens": 10,
       "completion_tokens": 148,
       "completion_tokens_details": {
         "reasoning_tokens": 128,  // Hidden thinking
         "output_tokens": 20       // Visible response
       },
       "total_tokens": 158
     }
   }
   ```

### Models That Support Reasoning Tokens (2025)

**OpenAI**:
- o1 series (o1, o1-mini, o1-preview)
- o3 series (o3, o3-mini)
- GPT-5 series (GPT-5, GPT-5-mini)

**Anthropic**:
- Claude 3.7 series
- Claude 4 series
- Claude 4.1 series

**xAI**:
- All Grok reasoning models

**DeepSeek**:
- DeepSeek R1 (uses `<think>` tags)

**Local Models** (via LM Studio):
- gpt-oss models (openai/gpt-oss-20b)
- DeepSeek R1 models
- Other reasoning-capable models

### Controlling Reasoning Effort

```python
response = client.chat.completions.create(
    model="gpt-o1",
    messages=[{"role": "user", "content": "Solve this complex math problem..."}],
    reasoning_effort="high"  # Options: "low", "medium", "high", "minimal" (GPT-5)
)
```

**Effect**:
- `low`: Faster, fewer reasoning tokens (cheaper)
- `medium`: Balanced
- `high`: More thorough thinking, more tokens (more expensive)
- `minimal`: Fastest, minimal reasoning (GPT-5 only)

### Billing Impact

**Important**: Reasoning tokens are billed as **output tokens**.

**Example**:
- Prompt: 10 tokens
- Reasoning: 128 tokens (hidden, but you PAY for these!)
- Output: 20 tokens (visible response)
- **Total billed**: 10 + 128 + 20 = 158 tokens

**Cost Implication**:
- Reasoning models can be MORE EXPENSIVE per response
- More reasoning = better quality but higher cost
- You're paying for the model's "thinking time"

---

## Part 2: LM Studio v1/responses Context

### What is v1/responses?

LM Studio's `/v1/responses` endpoint is a **stateful conversation API** that:
- Maintains conversation history server-side
- Supports custom tool calling
- Supports Remote MCP integration
- **Supports reasoning models** (gpt-oss, DeepSeek R1)

### Response Structure

```json
{
  "id": "response-xyz",
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "Here's my answer...",
        "reasoning": "<think>Let me think...</think>"  // For reasoning models
      }
    }
  ],
  "usage": {
    "prompt_tokens": 50,
    "completion_tokens": 100,
    "reasoning_tokens": 0,  // ← THIS FIELD
    "total_tokens": 150
  }
}
```

### What Does `"reasoning_tokens": 0` Mean in LM Studio?

**Three Possible Scenarios**:

#### Scenario 1: Non-Reasoning Model (Most Common)

**Situation**: You're using a standard model (not a reasoning model)

**Models Like**:
- Qwen models (qwen2.5, qwen3)
- Llama models
- Mistral models
- Standard chat models

**What It Means**:
```json
"reasoning_tokens": 0  // Model doesn't have reasoning capability
```

**This is NORMAL** - Most models don't use internal reasoning tokens.

---

#### Scenario 2: Reasoning Model with Minimal Reasoning

**Situation**: You're using a reasoning model BUT:
- The question is simple
- No complex thinking needed
- Model decides reasoning is unnecessary

**Models Like**:
- gpt-oss (openai/gpt-oss-20b)
- DeepSeek R1

**What It Means**:
```json
"reasoning_tokens": 0  // Model decided not to use reasoning for this simple query
```

**Example**:
```python
# Simple query
response = llm.create_response(
    messages=[{"role": "user", "content": "What is 2+2?"}],
    model="gpt-oss"
)
# reasoning_tokens: 0 (too simple, no reasoning needed)

# Complex query
response = llm.create_response(
    messages=[{"role": "user", "content": "Prove the Riemann hypothesis"}],
    model="gpt-oss"
)
# reasoning_tokens: 500+ (model needs to think!)
```

---

#### Scenario 3: Reasoning Disabled

**Situation**: Reasoning capability is disabled in settings

**What It Means**:
```json
"reasoning_tokens": 0  // Reasoning was turned off
```

**How to Enable** (LM Studio):
1. App Settings → Developer
2. Enable "Reasoning Support"
3. Restart server

---

### Reasoning Content in LM Studio

For reasoning models like **DeepSeek R1**, the reasoning process is captured in special tags:

**DeepSeek R1 Format**:
```
<think>
Let me analyze this step by step:
1. First, I need to...
2. Then, I should...
3. Finally, I can conclude...
</think>

Final answer: Based on my analysis, the answer is X.
```

**In API Response**:
```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "Final answer: Based on my analysis, the answer is X.",
      "reasoning": "<think>Let me analyze this step by step...</think>"
    }
  }],
  "usage": {
    "reasoning_tokens": 45  // Tokens in the <think> tags
  }
}
```

**How LM Studio Handles It**:
- `reasoning_tokens`: Count of tokens in `<think>` tags
- `completion_tokens`: Total tokens (reasoning + output)
- `reasoning` field: The actual thinking content (if enabled)

---

## Part 3: Why Does This Matter?

### For Understanding Model Behavior

**`reasoning_tokens > 0`** indicates:
- ✅ Model is doing complex thinking
- ✅ Response might be more accurate/thorough
- ✅ Processing took longer (more compute)

**`reasoning_tokens = 0`** indicates:
- ✅ Model answered directly (simple query)
- ✅ Faster response
- ✅ Less compute used

### For Cost Management (OpenAI/Cloud APIs)

**Important for budgeting**:
```python
# Example cost calculation
response = client.chat.completions.create(...)

usage = response.usage
prompt_cost = usage.prompt_tokens * $0.01 / 1000
reasoning_cost = usage.completion_tokens_details.reasoning_tokens * $0.03 / 1000  # Higher rate!
output_cost = usage.completion_tokens_details.output_tokens * $0.03 / 1000

total_cost = prompt_cost + reasoning_cost + output_cost
```

**Reasoning tokens can be EXPENSIVE** - they're billed at output token rates.

### For LM Studio (Local) - Why It Still Matters

Even though LM Studio is FREE (local inference), `reasoning_tokens` is useful for:

1. **Performance Monitoring**
   - Track when model is using heavy reasoning
   - Identify queries that trigger complex thinking
   - Optimize query patterns

2. **Quality Assessment**
   - More reasoning tokens ≠ always better
   - But for complex tasks, 0 reasoning tokens might indicate insufficient thinking
   - Can help tune `reasoning_effort` parameter

3. **Debugging**
   - If expecting reasoning but seeing 0 tokens → check model/settings
   - If seeing high reasoning tokens on simple queries → model might be over-thinking

---

## Part 4: Practical Implications in Our Codebase

### Historical Context (From Our Codebase)

**We removed `reasoning_effort` parameter** because:
- Most local models don't support it
- Was causing warnings in LM Studio logs
- Not needed for standard models (Qwen, Llama, etc.)

**Commits**:
- `878ef56` - Update max_tokens to 8192 and remove reasoning_effort warnings
- `9eb69ee` - Complete removal of reasoning_effort from all FastMCP tool wrappers

**What This Means**:
```python
# OLD (caused warnings):
response = llm.chat_completion(
    messages=messages,
    reasoning_effort="high"  # ← Removed!
)

# NEW (works with all models):
response = llm.chat_completion(
    messages=messages
    # No reasoning_effort parameter
)
```

### Current State in Our Bridge

**All responses from our LM Studio bridge will have**:
```json
"reasoning_tokens": 0
```

**Why?**:
1. We use standard models (Qwen3, etc.) - no reasoning capability
2. We removed `reasoning_effort` parameter
3. Our focus is on tool usage, not advanced reasoning

**This is CORRECT and EXPECTED** for our use case.

---

## Part 5: When Should You Care About Reasoning Tokens?

### ✅ You SHOULD Care If:

1. **Using OpenAI o1/o3 models** - You're paying for reasoning tokens
2. **Using Claude 4+ reasoning models** - Same cost concern
3. **Doing complex reasoning tasks** - Math, logic, multi-step problems
4. **Budget-conscious** - Reasoning tokens can 2-3x your API costs
5. **Using DeepSeek R1** - Want to see the thinking process

### ❌ You DON'T Need to Care If:

1. **Using LM Studio locally** - No cost (inference is free)
2. **Using standard models** - They don't have reasoning tokens
3. **Simple queries** - Won't trigger reasoning anyway
4. **Our current bridge** - We don't use reasoning models

---

## Part 6: Summary

### What `"reasoning_tokens": 0` Means

| Context | Meaning | Is This Normal? |
|---------|---------|-----------------|
| **Standard Model** (Qwen, Llama, etc.) | Model doesn't support reasoning | ✅ YES - Expected |
| **Reasoning Model + Simple Query** | Model decided no reasoning needed | ✅ YES - Efficient |
| **Reasoning Model + Complex Query** | Reasoning disabled or model didn't engage | ⚠️ MAYBE - Check settings |
| **LM Studio Local** | Standard model or reasoning disabled | ✅ YES - Expected |
| **Our Bridge** | We use standard models without reasoning | ✅ YES - By design |

### Key Takeaways

1. **Reasoning tokens** = hidden thinking tokens used by advanced models
2. **`reasoning_tokens: 0`** = no internal reasoning used (normal for most models)
3. **Cost impact** = reasoning tokens are expensive (cloud APIs only)
4. **Our codebase** = doesn't use reasoning (by design)
5. **When to care** = using o1/o3/Claude 4/DeepSeek R1 with complex queries

### For Our LM Studio Bridge Specifically

**Expected Behavior**:
```json
{
  "usage": {
    "prompt_tokens": 50,
    "completion_tokens": 100,
    "reasoning_tokens": 0,  // ← ALWAYS 0 (we use standard models)
    "total_tokens": 150
  }
}
```

**This is CORRECT** - we focus on:
- Tool usage (45 MCP tools working)
- Fast responses (standard models)
- Cost-free inference (local LM Studio)

We DON'T focus on:
- Advanced reasoning (not needed for tool usage)
- Complex problem-solving (tool chaining handles this)
- Visible reasoning chains (tools provide the logic)

---

## Additional Resources

### OpenAI Documentation
- [Reasoning Models Guide](https://platform.openai.com/docs/guides/reasoning)
- [Token Counting](https://help.openai.com/en/articles/4936856-what-are-tokens-and-how-to-count-them)

### LM Studio Documentation
- [Tool Use - Advanced](https://lmstudio.ai/docs/advanced/tool-use)
- [REST API](https://lmstudio.ai/docs/api/rest-api)
- [DeepSeek R1 Blog](https://lmstudio.ai/blog/deepseek-r1)

### Related Concepts
- **Chain-of-Thought (CoT)**: Visible reasoning steps (shown to user)
- **System 2 Thinking**: Deliberate, analytical reasoning (vs fast System 1)
- **o1-style Reasoning**: Hidden reasoning process (not shown to user)

---

🎯 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
