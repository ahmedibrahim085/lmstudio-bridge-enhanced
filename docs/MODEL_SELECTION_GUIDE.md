# Model Selection Guide for Tool Calling Agents

> Reference document for selecting optimal LLMs for CrewAI agents based on benchmark research.

## Quick Reference: Best Models for Tool Calling

| Rank | Model | Tool Calling | Size | Best For |
|------|-------|--------------|------|----------|
| 1 | qwen/qwen3-30b-a3b | Excellent | 30B | General agents with tools |
| 2 | qwen/qwen3-coder-30b | Excellent | 30B | Coding + debugging agents |
| 3 | qwen/qwen3-vl-30b | Excellent | 30B | Vision + tools |
| 4 | mistralai/magistral-small-2509 | Very Good | 24B | Reasoning + tools |
| 5 | qwen/qwen3-4b-thinking-2507 | Good | 4B | Lightweight reasoning |
| 6 | llama-3.2-3b-instruct | Moderate | 3B | Resource-constrained |

---

## Research Sources

### 1. Docker's Practical Evaluation (2024)

**Source**: https://www.docker.com/blog/local-llm-tool-calling-a-practical-evaluation/

Docker tested local LLMs using "chat2cart", a shopping assistant requiring accurate tool calling.

#### Benchmark Results:

| Model | F1 Score | Latency | Notes |
|-------|----------|---------|-------|
| **Qwen 3 (8B)** | **0.933** | ~84s | **Winner** - Best accuracy/speed balance |
| Claude 3 Haiku (cloud) | 0.933 | 3.56s | Cloud reference benchmark |
| LLaMA 3 Groq 7B | Modest | Low | Good for constrained resources |
| XLam 8B (LLaMA-based) | 0.570 | - | Missed correct tool paths |
| Watt 8B (quantized) | 0.484 | - | Struggled with parameters |

#### Key Finding:
> "Qwen models dominate. Even the 8B version of Qwen3 outperformed any other local model."

#### Common Failure Modes Observed:
- **Eager invocation**: Tools called even for greetings like "Hi there!"
- **Wrong tool selection**: Picking incorrect function for the task
- **Invalid arguments**: Missing or malformed parameters (product_name, quantity)

---

### 2. Berkeley Function Calling Leaderboard (BFCL)

**Source**: https://gorilla.cs.berkeley.edu/leaderboard.html

The **defacto standard** for evaluating LLM function/tool calling capabilities.

#### What BFCL Tests:
- 2,000+ question-function-answer pairs
- Multiple languages: Python, Java, JavaScript, REST API
- Complex scenarios:
  - Parallel function calls
  - Multi-turn conversations
  - When NOT to call a tool (critical!)
  - Sequential function dependencies

#### Key Insight:
> "Top AIs ace the one-shot questions but still stumble when they must remember context, manage long conversations, or decide when not to act."

#### Evaluation Metrics:
- **Overall Accuracy**: Unweighted average of all sub-categories
- **Cost**: Estimated USD for entire benchmark
- **Latency**: Measured in seconds

---

## LM Studio Model Metadata

LM Studio provides a critical field: `trainedForToolUse`

### Models with trainedForToolUse: true

These models are specifically trained for function/tool calling:

```
glm-4.6
ibm/granite-4-h-tiny
qwen/qwen3-vl-30b
qwen/qwen3-vl-8b
qwen/qwen3-vl-4b
qwen/qwen3-30b-a3b-2507
mistralai/magistral-small-2509
qwen/qwen3-coder-30b
openai/gpt-oss-120b
openai/gpt-oss-20b
qwen/qwen3-4b-thinking-2507
llama-3.2-3b-instruct
```

### Models with trainedForToolUse: false

**Avoid these for tool-heavy agents:**

```
mistralai/mistral-small-3.2
google/gemma-3-12b
google/gemma-3-27b
deepseek/deepseek-r1-0528-qwen3-8b
google/gemma-3n-e4b
```

---

## Model Selection by Agent Type

### Coding Agents
```
Primary:   qwen/qwen3-coder-30b
Fallback:  qwen/qwen3-30b-a3b-2507
Lightweight: qwen/qwen3-4b-thinking-2507
```

### Research/Analysis Agents
```
Primary:   qwen/qwen3-30b-a3b-2507
Fallback:  mistralai/magistral-small-2509
Lightweight: llama-3.2-3b-instruct
```

### Vision-Capable Agents
```
Primary:   qwen/qwen3-vl-30b
Fallback:  qwen/qwen3-vl-8b
Lightweight: qwen/qwen3-vl-4b
```

### Creative/Writing Agents (less tool-dependent)
```
Primary:   mistralai/mistral-small-3.2
Fallback:  google/gemma-3-27b
Note:      These don't need strong tool calling
```

### Reasoning/Planning Agents
```
Primary:   mistralai/magistral-small-2509
Fallback:  qwen/qwen3-30b-a3b-2507
Deep:      openai/gpt-oss-120b (if VRAM allows)
```

---

## Model Selection Algorithm

```python
def suggest_model_for_agent(
    role: str,
    goal: str,
    backstory: str,
    tools: List[str],
    available_models: List[dict]
) -> List[dict]:
    """
    Suggest optimal models based on agent requirements.

    Returns list of suggestions with confidence scores and reasoning.
    """
    text = f"{role} {goal} {backstory}".lower()
    suggestions = []

    # Filter to only trainedForToolUse models if agent has tools
    if tools:
        candidates = [m for m in available_models if m.get("trainedForToolUse", False)]
    else:
        candidates = available_models

    # Coding detection
    coding_keywords = ["code", "develop", "program", "debug", "engineer", "software", "api"]
    if any(k in text for k in coding_keywords):
        for m in candidates:
            if "coder" in m["modelKey"].lower():
                suggestions.append({
                    "model": m["modelKey"],
                    "confidence": 0.95,
                    "reason": "Agent involves coding tasks - Qwen Coder excels at this"
                })

    # Vision detection
    vision_keywords = ["image", "visual", "see", "screenshot", "diagram", "picture", "photo"]
    if any(k in text for k in vision_keywords):
        for m in candidates:
            if m.get("vision", False):
                suggestions.append({
                    "model": m["modelKey"],
                    "confidence": 0.90,
                    "reason": "Agent needs vision capabilities"
                })

    # Research/Analysis detection
    research_keywords = ["research", "analyze", "investigate", "study", "explore"]
    if any(k in text for k in research_keywords):
        for m in candidates:
            if "qwen3-30b" in m["modelKey"] or "magistral" in m["modelKey"]:
                suggestions.append({
                    "model": m["modelKey"],
                    "confidence": 0.85,
                    "reason": "Agent requires deep analysis and reasoning"
                })

    # Default: prioritize Qwen for tool calling (proven best)
    if tools and not suggestions:
        for m in candidates:
            if "qwen" in m["modelKey"].lower() and m.get("trainedForToolUse"):
                suggestions.append({
                    "model": m["modelKey"],
                    "confidence": 0.80,
                    "reason": "Qwen models proven best for tool calling (Docker benchmark)"
                })

    # Sort by confidence
    suggestions.sort(key=lambda x: -x["confidence"])

    # Remove duplicates while preserving order
    seen = set()
    unique = []
    for s in suggestions:
        if s["model"] not in seen:
            seen.add(s["model"])
            unique.append(s)

    return unique[:5]  # Top 5 suggestions
```

---

## VRAM Estimation

Use `sizeBytes` from `lms ls --json` for rough VRAM estimates:

| Model | sizeBytes | ~VRAM |
|-------|-----------|-------|
| qwen/qwen3-30b-a3b-2507 | 17.2GB | ~18GB |
| qwen/qwen3-coder-30b (8bit) | 32.5GB | ~34GB |
| mistralai/magistral-small-2509 | 14.1GB | ~15GB |
| qwen/qwen3-vl-30b | 18.3GB | ~19GB |
| llama-3.2-3b-instruct | 1.8GB | ~2GB |
| openai/gpt-oss-120b | 63.4GB | ~65GB |

**Rule of thumb**: VRAM needed ≈ sizeBytes × 1.1 (10% overhead)

---

## Additional Resources

- [Qwen Function Calling Documentation](https://qwen.readthedocs.io/en/latest/framework/function_call.html)
- [Analytics Vidhya: Top 6 LLMs for Function Calling](https://www.analyticsvidhya.com/blog/2024/10/function-calling-llms/)
- [vLLM Tool Calling](https://docs.vllm.ai/en/stable/features/tool_calling/)
- [BFCL GitHub Repository](https://github.com/ShishirPatil/gorilla/tree/main/berkeley-function-call-leaderboard)

---

## Changelog

- **2024-11-22**: Initial version based on Docker and Berkeley BFCL research
