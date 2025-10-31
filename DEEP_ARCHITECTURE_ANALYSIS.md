# Deep Architecture Analysis: Intelligent Model Capability System

**Date**: 2025-10-31
**Status**: Comprehensive Research & Design Document
**Purpose**: Design a flexible, intelligent model selection and parameter system

---

## 🚨 The Fundamental Problem I Missed

### What I Was Doing Wrong

1. **Rushing to solutions** without understanding the system architecture
2. **Manual assumptions** about model capabilities instead of programmatic discovery
3. **One-size-fits-all approach** instead of model-specific parameter handling
4. **Static configuration** instead of dynamic capability detection
5. **Allocating 9 hours** for what should be 2 hours of capture logic, ignoring the **real architecture** needed

### What You Correctly Identified

> "you are not thinking deep enough... why not implement a method or more at the beginning of the connection to the LMS Studio bridge MCP to:
> a) get the list of models available
> b) use both LMS CLI, and hugging face to find out more info about each and every model
> c) based on the result we can set one or more values that are important on deciding what we can use the model for
> d) based on the capabilities we can be able to decide which model to use and switch between them"

**This is architectural thinking** - not just "add a parameter", but **build an intelligent system**.

---

## 📊 Research Findings

### 1. LM Studio API Discovery

#### `/api/v0/models` Endpoint (Rich Metadata)

**What It Returns**:
```json
{
  "id": "qwen/qwen3-4b-thinking-2507",
  "type": "llm",
  "publisher": "qwen",
  "arch": "qwen3",
  "compatibility_type": "mlx",
  "quantization": "4bit",
  "state": "loaded",
  "max_context_length": 262144,
  "loaded_context_length": 262144,
  "capabilities": ["tool_use"]
}
```

**Current Limitations**:
- ❌ `capabilities` array only shows `["tool_use"]` - not reasoning/thinking
- ❌ No indication of reasoning support
- ❌ No parameter hints for model-specific features

**BUT** - This gives us:
- ✅ Architecture type (`qwen3`, `mistral3`, `gpt_oss`)
- ✅ Model state (loaded/not loaded)
- ✅ Context length
- ✅ Quantization level

### 2. LMS CLI Discovery

**`lms ps` Output**:
```
IDENTIFIER                       MODEL                            STATUS    SIZE        CONTEXT    TTL
qwen/qwen3-4b-thinking-2507      qwen/qwen3-4b-thinking-2507     IDLE      2.28 GB     262144
qwen/qwen3-coder-30b             qwen/qwen3-coder-30b            IDLE      32.46 GB    262144
mistralai/magistral-small-2509   mistralai/magistral-small-2509  IDLE      14.12 GB    131072
```

**What It Gives Us**:
- ✅ Context length (important for reasoning budget)
- ✅ Model size (performance considerations)
- ✅ Current status (for smart switching)

### 3. Model Naming Conventions (Pattern Detection)

**Critical Discovery**: Model names encode capabilities!

| Model ID | Pattern | Capability Indicated |
|----------|---------|---------------------|
| `qwen/qwen3-4b-thinking-2507` | `thinking` | ✅ Reasoning model |
| `qwen/qwen3-coder-30b` | `coder` | ✅ Code-specialized |
| `mistralai/magistral-small-2509` | `magistral` | ✅ Reasoning model |
| `openai/gpt-oss-20b` | `gpt-oss` | ✅ Reasoning model |
| `deepseek/deepseek-r1-*` | `r1` or `r` | ✅ Reasoning model |

**Pattern Rules**:
- Contains `thinking` → Reasoning model
- Contains `magistral` → Reasoning model
- Contains `gpt-oss` → Reasoning model
- Contains `deepseek-r` → Reasoning model
- Contains `coder` → Code-specialized
- Contains `vl` → Vision-language model

### 4. Qwen Model Specifics (From Official Docs)

#### Qwen3-Thinking Models

**From Hugging Face**:
```
This model supports only thinking mode.
specifying enable_thinking=True is no longer required.
```

**Key Facts**:
- ✅ Thinking is **automatic** (no parameter needed)
- ✅ Uses `<think></think>` tags internally
- ✅ Response has `reasoning_content` field
- ✅ Supports `thinking_budget` parameter (cloud API)
- ⚠️ LM Studio may not expose `thinking_budget` in local API

#### Qwen3-Coder Models

**From Research**:
- ✅ **CAN think** if explicitly prompted
- ✅ Supports hybrid mode (thinking + non-thinking)
- ⚠️ **NOT** thinking-only like Qwen3-4B-Thinking
- 🔑 May need `/think` command or system prompt to enable

**Critical Insight**: Qwen Coder is **hybrid** - can think but doesn't automatically.

### 5. Magistral Model Specifics (From Mistral Docs)

**From Official Docs**:
```
Reasoning with Chat Completions:
- Uses [THINK] content chunks (not <think> tags)
- System prompt controls reasoning behavior
- prompt_mode parameter: "reasoning" or null
```

**Key Facts**:
- ✅ Reasoning via system prompt + content chunks
- ✅ Uses `thinking` content type (not `reasoning_content` field)
- ❌ Does NOT use `reasoning_effort` parameter
- ✅ Uses `prompt_mode` parameter instead
- ⚠️ Different response structure than Qwen

**Response Format** (Magistral):
```json
{
  "choices": [{
    "message": {
      "content": [
        {"type": "thinking", "thinking": "reasoning process..."},
        {"type": "text", "text": "final answer..."}
      ]
    }
  }]
}
```

**vs Qwen Format**:
```json
{
  "choices": [{
    "message": {
      "content": "final answer...",
      "reasoning_content": "reasoning process..."
    }
  }]
}
```

### 6. Testing Actual Behavior

**Qwen3-4B-Thinking Test** (Earlier):
```bash
curl http://localhost:1234/v1/chat/completions \
  -d '{"model": "qwen/qwen3-4b-thinking-2507", "messages": [...]}'
```

**Result**:
```json
{
  "message": {
    "content": "...final answer...",
    "reasoning_content": "Okay, let's see. I need to figure out...",
    "tool_calls": []
  },
  "usage": {
    "prompt_tokens": 24,
    "completion_tokens": 1704,
    "total_tokens": 1728
  }
}
```

**Key Observations**:
- ✅ `reasoning_content` is **already there** automatically
- ❌ No `reasoning_tokens` field (different from OpenAI format)
- ✅ Model is thinking without any parameter
- 🔑 We're just not capturing/returning the reasoning!

---

## 🏗️ The Architecture We Actually Need

### Phase 1: Model Capability Discovery System

#### 1.1 ModelCapabilityDiscovery Class

```python
# llm/model_capabilities.py

from typing import Dict, List, Optional, Set
from dataclasses import dataclass
import re
import requests

@dataclass
class ModelCapabilities:
    """Comprehensive model capability metadata."""

    # Basic Info
    model_id: str
    publisher: str
    arch: str
    model_type: str  # "llm", "vlm", "embeddings"

    # Context & Performance
    max_context_length: int
    loaded_context_length: int
    quantization: str
    state: str  # "loaded" or "not-loaded"

    # Capabilities (inferred)
    supports_reasoning: bool
    reasoning_type: str  # "automatic", "hybrid", "none"
    supports_vision: bool
    supports_code: bool
    supports_tool_use: bool

    # Reasoning Configuration
    reasoning_parameter: Optional[str]  # "thinking_budget", "prompt_mode", None
    reasoning_response_format: str  # "reasoning_content", "thinking_chunks", "none"
    default_reasoning_enabled: bool

    # Usage Hints
    recommended_for: List[str]  # ["complex_reasoning", "code_generation", ...]
    notes: List[str]


class ModelCapabilityDiscovery:
    """
    Intelligent model capability discovery system.

    Discovers model capabilities through:
    1. LM Studio API (/api/v0/models)
    2. LMS CLI (lms ps)
    3. Model ID pattern matching
    4. Heuristic testing (optional)
    5. Cached metadata from Hugging Face (optional)
    """

    # Pattern matchers for capability inference
    REASONING_PATTERNS = [
        r"thinking",
        r"magistral",
        r"gpt-oss",
        r"deepseek-r\d+",
        r"o\d+(-mini|-preview)?",  # o1, o3, o1-mini, etc.
    ]

    CODER_PATTERNS = [
        r"coder",
        r"code",
        r"codegen",
    ]

    VISION_PATTERNS = [
        r"-vl-",
        r"vision",
        r"pixtral",
    ]

    def __init__(self, base_url: str = "http://localhost:1234"):
        self.base_url = base_url
        self.capabilities_cache: Dict[str, ModelCapabilities] = {}

    def discover_all_models(self) -> Dict[str, ModelCapabilities]:
        """
        Discover capabilities for all available models.

        Returns:
            Dict mapping model_id to ModelCapabilities
        """
        models = self._fetch_models_from_api()

        for model_data in models:
            model_id = model_data["id"]
            capabilities = self._infer_capabilities(model_data)
            self.capabilities_cache[model_id] = capabilities

        return self.capabilities_cache

    def _fetch_models_from_api(self) -> List[Dict]:
        """Fetch model list from LM Studio API."""
        try:
            response = requests.get(
                f"{self.base_url}/api/v0/models",
                timeout=5
            )
            response.raise_for_status()
            return response.json()["data"]
        except Exception as e:
            # Fallback to standard endpoint
            response = requests.get(
                f"{self.base_url}/v1/models",
                timeout=5
            )
            return response.json()["data"]

    def _infer_capabilities(self, model_data: Dict) -> ModelCapabilities:
        """
        Infer comprehensive capabilities from model metadata and patterns.
        """
        model_id = model_data["id"]
        model_id_lower = model_id.lower()

        # Detect reasoning capability
        supports_reasoning = any(
            re.search(pattern, model_id_lower)
            for pattern in self.REASONING_PATTERNS
        )

        # Determine reasoning type and configuration
        reasoning_type, reasoning_param, reasoning_format, default_enabled = \
            self._determine_reasoning_config(model_id_lower)

        # Detect other capabilities
        supports_code = any(
            re.search(pattern, model_id_lower)
            for pattern in self.CODER_PATTERNS
        )

        supports_vision = (
            model_data.get("type") == "vlm" or
            any(re.search(pattern, model_id_lower) for pattern in self.VISION_PATTERNS)
        )

        # Generate usage recommendations
        recommended_for = self._generate_recommendations(
            supports_reasoning, supports_code, supports_vision
        )

        return ModelCapabilities(
            model_id=model_id,
            publisher=model_data.get("publisher", ""),
            arch=model_data.get("arch", ""),
            model_type=model_data.get("type", "llm"),
            max_context_length=model_data.get("max_context_length", 0),
            loaded_context_length=model_data.get("loaded_context_length", 0),
            quantization=model_data.get("quantization", ""),
            state=model_data.get("state", "not-loaded"),
            supports_reasoning=supports_reasoning,
            reasoning_type=reasoning_type,
            supports_vision=supports_vision,
            supports_code=supports_code,
            supports_tool_use="tool_use" in model_data.get("capabilities", []),
            reasoning_parameter=reasoning_param,
            reasoning_response_format=reasoning_format,
            default_reasoning_enabled=default_enabled,
            recommended_for=recommended_for,
            notes=[]
        )

    def _determine_reasoning_config(self, model_id_lower: str) -> tuple:
        """
        Determine reasoning configuration based on model type.

        Returns:
            (reasoning_type, parameter_name, response_format, default_enabled)
        """
        # Qwen Thinking models (thinking-only)
        if "thinking" in model_id_lower and "qwen" in model_id_lower:
            return (
                "automatic",           # Always thinking
                "thinking_budget",     # Parameter (may not work in LM Studio)
                "reasoning_content",   # Response field
                True                   # Enabled by default
            )

        # Qwen Coder models (hybrid)
        if "coder" in model_id_lower and "qwen" in model_id_lower:
            return (
                "hybrid",              # Can think if prompted
                "thinking_budget",     # Parameter
                "reasoning_content",   # Response field
                False                  # Not enabled by default
            )

        # Magistral models (prompt-based reasoning)
        if "magistral" in model_id_lower:
            return (
                "automatic",           # Uses system prompt
                "prompt_mode",         # Parameter ("reasoning" or null)
                "thinking_chunks",     # Response format (content array)
                True                   # Enabled by default
            )

        # DeepSeek R models
        if "deepseek" in model_id_lower and re.search(r"r\d+", model_id_lower):
            return (
                "automatic",
                "thinking_budget",
                "reasoning_content",
                True
            )

        # OpenAI o-series models
        if re.search(r"o\d+", model_id_lower):
            return (
                "automatic",
                "reasoning_effort",    # OpenAI-style
                "reasoning_content",
                True
            )

        # No reasoning
        return ("none", None, "none", False)

    def _generate_recommendations(
        self,
        supports_reasoning: bool,
        supports_code: bool,
        supports_vision: bool
    ) -> List[str]:
        """Generate usage recommendations based on capabilities."""
        recommendations = []

        if supports_reasoning:
            recommendations.extend([
                "complex_reasoning",
                "math_problems",
                "logical_deduction",
                "multi_step_planning"
            ])

        if supports_code:
            recommendations.extend([
                "code_generation",
                "code_review",
                "debugging",
                "refactoring"
            ])

        if supports_vision:
            recommendations.extend([
                "image_analysis",
                "visual_qa",
                "document_understanding"
            ])

        if not recommendations:
            recommendations.append("general_purpose")

        return recommendations

    def get_best_model_for_task(
        self,
        task_type: str,
        prefer_loaded: bool = True
    ) -> Optional[str]:
        """
        Select the best model for a given task type.

        Args:
            task_type: One of the recommendation categories
            prefer_loaded: Prefer models that are already loaded

        Returns:
            Model ID or None
        """
        candidates = [
            (model_id, caps)
            for model_id, caps in self.capabilities_cache.items()
            if task_type in caps.recommended_for
        ]

        if not candidates:
            return None

        # Sort by: loaded status, then context length
        candidates.sort(
            key=lambda x: (
                x[1].state == "loaded" if prefer_loaded else True,
                x[1].max_context_length
            ),
            reverse=True
        )

        return candidates[0][0]
```

#### 1.2 Integration with LLMClient

```python
# llm/llm_client.py

class LLMClient:
    """Enhanced LLM client with intelligent model selection."""

    def __init__(self, base_url: str = "http://localhost:1234", model: Optional[str] = None):
        self.base_url = base_url
        self.model = model

        # Initialize capability discovery
        self.capability_discovery = ModelCapabilityDiscovery(base_url)
        self.model_capabilities: Dict[str, ModelCapabilities] = {}

        # Auto-discover on initialization
        self._discover_capabilities()

    def _discover_capabilities(self):
        """Discover all model capabilities at initialization."""
        try:
            self.model_capabilities = self.capability_discovery.discover_all_models()
            logger.info(f"Discovered {len(self.model_capabilities)} models with capabilities")
        except Exception as e:
            logger.warning(f"Failed to discover model capabilities: {e}")

    def get_model_capabilities(self, model_id: Optional[str] = None) -> Optional[ModelCapabilities]:
        """Get capabilities for a specific model."""
        target_model = model_id or self.model
        return self.model_capabilities.get(target_model)

    def list_models_by_capability(self, capability: str) -> List[str]:
        """
        List all models supporting a specific capability.

        Args:
            capability: "reasoning", "code", "vision", etc.

        Returns:
            List of model IDs
        """
        models = []

        for model_id, caps in self.model_capabilities.items():
            if capability == "reasoning" and caps.supports_reasoning:
                models.append(model_id)
            elif capability == "code" and caps.supports_code:
                models.append(model_id)
            elif capability == "vision" and caps.supports_vision:
                models.append(model_id)

        return models

    def select_best_model(self, task_type: str) -> Optional[str]:
        """Intelligently select the best model for a task."""
        return self.capability_discovery.get_best_model_for_task(task_type)
```

### Phase 2: Flexible Parameter System

#### 2.1 ReasoningParameterAdapter

```python
# llm/reasoning_adapter.py

from typing import Dict, Any, Optional
from .model_capabilities import ModelCapabilities

class ReasoningParameterAdapter:
    """
    Adapts reasoning requests to model-specific parameter formats.

    Handles differences between:
    - Qwen: thinking_budget, reasoning_content response
    - Magistral: prompt_mode, thinking chunks response
    - OpenAI: reasoning_effort
    - DeepSeek: thinking_budget
    """

    @staticmethod
    def prepare_reasoning_request(
        base_payload: Dict[str, Any],
        capabilities: ModelCapabilities,
        enable_reasoning: bool = True,
        reasoning_intensity: str = "medium",  # "low", "medium", "high"
        max_reasoning_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Prepare request payload with model-specific reasoning parameters.

        Args:
            base_payload: Base request payload
            capabilities: Model capabilities
            enable_reasoning: Whether to enable reasoning
            reasoning_intensity: How much reasoning ("low", "medium", "high")
            max_reasoning_tokens: Max tokens for reasoning (model-specific)

        Returns:
            Enhanced payload with reasoning parameters
        """
        if not enable_reasoning or not capabilities.supports_reasoning:
            return base_payload

        payload = base_payload.copy()

        # Qwen models (thinking_budget)
        if capabilities.reasoning_parameter == "thinking_budget":
            if max_reasoning_tokens:
                payload["thinking_budget"] = max_reasoning_tokens
            else:
                # Map intensity to token budget
                budget_map = {"low": 2048, "medium": 8192, "high": 32768}
                payload["thinking_budget"] = budget_map.get(reasoning_intensity, 8192)

        # Magistral models (prompt_mode + system prompt)
        elif capabilities.reasoning_parameter == "prompt_mode":
            payload["prompt_mode"] = "reasoning" if enable_reasoning else None

            # Ensure system prompt enables reasoning
            if enable_reasoning and "messages" in payload:
                messages = payload["messages"]
                if not messages or messages[0].get("role") != "system":
                    # Add default reasoning system prompt
                    messages.insert(0, {
                        "role": "system",
                        "content": "You are a helpful assistant that thinks step-by-step before answering."
                    })

        # OpenAI o-series models (reasoning_effort)
        elif capabilities.reasoning_parameter == "reasoning_effort":
            payload["reasoning_effort"] = reasoning_intensity

        return payload

    @staticmethod
    def extract_reasoning_from_response(
        response: Dict[str, Any],
        capabilities: ModelCapabilities
    ) -> tuple[str, Optional[str]]:
        """
        Extract content and reasoning from response based on model format.

        Returns:
            (final_content, reasoning_process)
        """
        if not capabilities.supports_reasoning:
            content = response["choices"][0]["message"]["content"]
            return (content, None)

        # Qwen format (reasoning_content field)
        if capabilities.reasoning_response_format == "reasoning_content":
            message = response["choices"][0]["message"]
            content = message.get("content", "")
            reasoning = message.get("reasoning_content", "")
            return (content, reasoning if reasoning else None)

        # Magistral format (content array with thinking chunks)
        elif capabilities.reasoning_response_format == "thinking_chunks":
            message = response["choices"][0]["message"]
            content_array = message.get("content", [])

            if isinstance(content_array, str):
                # Fallback if content is string
                return (content_array, None)

            # Extract thinking and text chunks
            thinking_parts = []
            text_parts = []

            for chunk in content_array:
                if chunk.get("type") == "thinking":
                    thinking_parts.append(chunk.get("thinking", ""))
                elif chunk.get("type") == "text":
                    text_parts.append(chunk.get("text", ""))

            final_content = "\n".join(text_parts)
            reasoning = "\n".join(thinking_parts) if thinking_parts else None

            return (final_content, reasoning)

        # Fallback
        content = response["choices"][0]["message"]["content"]
        return (content, None)
```

#### 2.2 Enhanced LLMClient Methods

```python
# llm/llm_client.py (continued)

class LLMClient:

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto",
        timeout: int = DEFAULT_LLM_TIMEOUT,
        model: Optional[str] = None,
        # NEW: Reasoning control parameters
        enable_reasoning: bool = True,
        reasoning_intensity: str = "medium",
        max_reasoning_tokens: Optional[int] = None,
        return_reasoning: bool = True
    ) -> Dict[str, Any]:
        """
        Enhanced chat completion with intelligent reasoning support.

        Args:
            messages: Conversation messages
            temperature: Sampling temperature
            max_tokens: Maximum completion tokens
            tools: Optional tools for function calling
            tool_choice: Tool selection strategy
            timeout: Request timeout
            model: Optional model override
            enable_reasoning: Enable reasoning for capable models
            reasoning_intensity: "low", "medium", or "high"
            max_reasoning_tokens: Max tokens for reasoning (overrides intensity)
            return_reasoning: Include reasoning in response

        Returns:
            {
                "content": "final answer",
                "reasoning": "thinking process" or None,
                "tool_calls": [...],
                "usage": {...}
            }
        """
        target_model = model or self.model
        capabilities = self.get_model_capabilities(target_model)

        # Build base payload
        payload = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice

        # Apply reasoning parameters if model supports it
        if capabilities:
            payload = ReasoningParameterAdapter.prepare_reasoning_request(
                payload,
                capabilities,
                enable_reasoning,
                reasoning_intensity,
                max_reasoning_tokens
            )

        # Make request
        response = self._make_request_with_retry(payload, timeout)

        # Extract content and reasoning
        if capabilities and return_reasoning:
            content, reasoning = ReasoningParameterAdapter.extract_reasoning_from_response(
                response,
                capabilities
            )
        else:
            content = response["choices"][0]["message"]["content"]
            reasoning = None

        # Return enhanced response
        return {
            "content": content,
            "reasoning": reasoning,
            "tool_calls": response["choices"][0]["message"].get("tool_calls", []),
            "usage": response.get("usage", {}),
            "model": response.get("model", target_model),
        }
```

### Phase 3: Intelligent Model Switching

```python
# llm/model_selector.py

from typing import Optional, List, Dict
from .model_capabilities import ModelCapabilities

class IntelligentModelSelector:
    """
    Intelligently select and switch between models based on task requirements.
    """

    def __init__(self, llm_client):
        self.llm_client = llm_client

    def select_for_task(
        self,
        task_description: str,
        task_type: Optional[str] = None,
        require_reasoning: bool = False,
        require_vision: bool = False,
        min_context: int = 0
    ) -> str:
        """
        Select the best model for a task.

        Args:
            task_description: Natural language task description
            task_type: Explicit task type hint
            require_reasoning: Must support reasoning
            require_vision: Must support vision
            min_context: Minimum context length required

        Returns:
            Model ID
        """
        # Filter candidates
        candidates = []

        for model_id, caps in self.llm_client.model_capabilities.items():
            # Apply filters
            if require_reasoning and not caps.supports_reasoning:
                continue
            if require_vision and not caps.supports_vision:
                continue
            if min_context > caps.max_context_length:
                continue

            # Calculate match score
            score = self._score_model_for_task(
                caps, task_description, task_type
            )

            candidates.append((model_id, caps, score))

        if not candidates:
            raise ValueError("No suitable model found for task requirements")

        # Sort by score (higher is better)
        candidates.sort(key=lambda x: x[2], reverse=True)

        return candidates[0][0]

    def _score_model_for_task(
        self,
        capabilities: ModelCapabilities,
        task_description: str,
        task_type: Optional[str]
    ) -> float:
        """Score how well a model fits a task (0.0 to 1.0)."""
        score = 0.5  # Base score

        task_lower = task_description.lower()

        # Bonus for reasoning models on complex tasks
        if capabilities.supports_reasoning:
            reasoning_keywords = ["think", "reason", "analyze", "solve", "prove", "complex"]
            if any(kw in task_lower for kw in reasoning_keywords):
                score += 0.3

        # Bonus for code models on code tasks
        if capabilities.supports_code:
            code_keywords = ["code", "function", "program", "debug", "refactor"]
            if any(kw in task_lower for kw in code_keywords):
                score += 0.2

        # Bonus for loaded models (faster response)
        if capabilities.state == "loaded":
            score += 0.1

        # Bonus for matching task_type
        if task_type and task_type in capabilities.recommended_for:
            score += 0.2

        return min(score, 1.0)
```

### Phase 4: Initialization System

```python
# lmstudio_bridge.py (main entry point)

# Global capability system
_capability_discovery = None
_llm_client = None

async def initialize_model_capabilities():
    """
    Initialize model capability discovery on MCP startup.

    This runs ONCE when the MCP connects to LM Studio.
    """
    global _capability_discovery, _llm_client

    try:
        logger.info("Initializing model capability discovery...")

        # Create LLM client (this triggers auto-discovery)
        _llm_client = LLMClient()
        _capability_discovery = _llm_client.capability_discovery

        # Log discovered models
        capabilities = _llm_client.model_capabilities
        logger.info(f"Discovered {len(capabilities)} models:")

        for model_id, caps in capabilities.items():
            logger.info(
                f"  {model_id}: "
                f"reasoning={caps.supports_reasoning} ({caps.reasoning_type}), "
                f"code={caps.supports_code}, "
                f"vision={caps.supports_vision}, "
                f"state={caps.state}"
            )

        # Log reasoning-capable models
        reasoning_models = [
            model_id for model_id, caps in capabilities.items()
            if caps.supports_reasoning
        ]
        logger.info(f"Reasoning-capable models: {reasoning_models}")

        return True

    except Exception as e:
        logger.error(f"Failed to initialize model capabilities: {e}")
        return False


# Add FastMCP lifecycle hook
@mcp.on_startup
async def on_startup():
    """Called when MCP server starts."""
    await initialize_model_capabilities()


# Enhanced tool that uses capability system
@mcp.tool()
async def list_available_models() -> str:
    """
    List all available models with their capabilities.

    Returns:
        JSON string with model details and capabilities
    """
    if not _llm_client:
        return json.dumps({"error": "Capability system not initialized"})

    models_info = []

    for model_id, caps in _llm_client.model_capabilities.items():
        models_info.append({
            "id": model_id,
            "publisher": caps.publisher,
            "architecture": caps.arch,
            "type": caps.model_type,
            "state": caps.state,
            "context_length": caps.max_context_length,
            "capabilities": {
                "reasoning": caps.supports_reasoning,
                "reasoning_type": caps.reasoning_type,
                "code": caps.supports_code,
                "vision": caps.supports_vision,
                "tools": caps.supports_tool_use,
            },
            "reasoning_config": {
                "parameter": caps.reasoning_parameter,
                "response_format": caps.reasoning_response_format,
                "default_enabled": caps.default_reasoning_enabled,
            } if caps.supports_reasoning else None,
            "recommended_for": caps.recommended_for,
        })

    return json.dumps(models_info, indent=2)


@mcp.tool()
async def select_best_model_for_task(
    task_description: str,
    require_reasoning: bool = False,
    require_vision: bool = False,
    require_code: bool = False
) -> str:
    """
    Intelligently select the best model for a task.

    Args:
        task_description: Description of the task
        require_reasoning: Task requires reasoning capability
        require_vision: Task requires vision capability
        require_code: Task requires code specialization

    Returns:
        JSON with selected model and reasoning
    """
    if not _llm_client:
        return json.dumps({"error": "Capability system not initialized"})

    try:
        selector = IntelligentModelSelector(_llm_client)

        selected_model = selector.select_for_task(
            task_description,
            require_reasoning=require_reasoning,
            require_vision=require_vision
        )

        caps = _llm_client.get_model_capabilities(selected_model)

        return json.dumps({
            "selected_model": selected_model,
            "reasoning": f"Selected {selected_model} because:",
            "capabilities": {
                "reasoning": caps.supports_reasoning,
                "code": caps.supports_code,
                "vision": caps.supports_vision,
            },
            "recommended_for": caps.recommended_for,
        }, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)})
```

---

## 📝 Implementation Timeline (Realistic)

### Phase 1: Model Capability Discovery (8-10 hours)
- ✅ ModelCapabilities dataclass (1h)
- ✅ ModelCapabilityDiscovery class (3h)
- ✅ Pattern matching logic (2h)
- ✅ Integration with LLMClient (2h)
- ✅ Testing and refinement (2h)

### Phase 2: Reasoning Parameter Adapter (6-8 hours)
- ✅ ReasoningParameterAdapter class (3h)
- ✅ Response parsing for different formats (2h)
- ✅ Integration with chat_completion (1h)
- ✅ Testing with all model types (2h)

### Phase 3: Intelligent Model Switching (4-6 hours)
- ✅ IntelligentModelSelector class (2h)
- ✅ Scoring logic (1h)
- ✅ Integration and testing (2h)
- ✅ Documentation (1h)

### Phase 4: MCP Tools & Integration (4-6 hours)
- ✅ Initialization system (2h)
- ✅ list_available_models tool (1h)
- ✅ select_best_model_for_task tool (1h)
- ✅ Update autonomous functions (2h)

### Phase 5: Testing & Documentation (6-8 hours)
- ✅ Unit tests for capability discovery (2h)
- ✅ Integration tests with all model types (3h)
- ✅ Documentation and examples (2h)
- ✅ User guide (1h)

**Total Realistic Estimate**: 28-38 hours

---

## 🎯 Key Benefits of This Architecture

### 1. **Intelligence Over Hardcoding**
- ❌ Before: Hardcode "Qwen uses thinking_budget"
- ✅ After: Discover "This model needs thinking_budget based on ID pattern"

### 2. **Flexibility**
- Supports new models automatically (pattern matching)
- Handles model-specific quirks gracefully
- No code changes needed for new Qwen/Mistral releases

### 3. **User Experience**
- User can query "what models support reasoning?"
- User can ask "what's the best model for complex math?"
- System automatically switches to appropriate model

### 4. **Maintainability**
- Single source of truth for capabilities
- Clear separation of concerns
- Easy to add new model types

### 5. **Debugging**
- Log shows exactly what capabilities were discovered
- Clear visibility into why a model was selected
- Easy to diagnose parameter issues

---

## 🚨 Critical Realizations From This Analysis

### What I Got Wrong Initially

1. **Focused on "add a parameter"** instead of "build a system"
2. **Assumed 2 hours of work** when architecture needs 30+ hours
3. **Missed the model switching** intelligence opportunity
4. **Didn't think about** different response formats (Magistral vs Qwen)
5. **Ignored the discovery problem** - how do we know what each model can do?

### What You Correctly Identified

> "why not implement a method or more at the beginning of the connection... to get the list of models available... use both LMS CLI, and hugging face... based on the result we can set one or more values... based on the capabilities we can be able to decide which model to use"

**This is the right architecture.**

Not "add reasoning_content capture" (2 hours).
But "build an intelligent model capability system" (30-38 hours).

---

## 📋 Recommended Next Steps

### 1. **User Decision Point**

**Question for you**: Should we proceed with this comprehensive architecture?

**Options**:
A. **Full architecture** (30-38 hours) - Everything above
B. **MVP architecture** (12-16 hours) - Core capability discovery + parameter adapter only
C. **Quick fix first** (2 hours) - Just capture reasoning_content, architecture later
D. **Different approach** - Your alternative idea

### 2. **If Proceeding with Architecture**

**Week 1**:
- Implement ModelCapabilityDiscovery
- Pattern matching and API integration
- Basic testing

**Week 2**:
- Implement ReasoningParameterAdapter
- Response format handling
- Integration with LLMClient

**Week 3**:
- Intelligent model selection
- MCP tools
- Comprehensive testing

**Week 4**:
- Documentation
- Examples
- Refinement based on usage

---

## 🎓 Lessons Learned (Meta-Analysis)

### What You Taught Me

1. **Think architecturally, not tactically**
   - Don't just fix the immediate problem
   - Build the system that prevents future problems

2. **Use the tools available**
   - LMS CLI gives us data - use it!
   - API endpoints give us metadata - parse it!
   - Model names encode capabilities - pattern match them!

3. **Time estimates must match complexity**
   - Simple fix = 2 hours
   - Architecture = 30+ hours
   - Don't conflate them

4. **Flexibility is a requirement, not a feature**
   - Models change (2506 → 2507 → 2509)
   - APIs evolve
   - System must adapt

### How I Should Have Approached This

1. **Research FIRST** (what I did now, finally)
   - Check all APIs
   - Read all docs
   - Test actual behavior

2. **Design THEN** (what this document is)
   - Map out the architecture
   - Identify all components
   - Estimate realistically

3. **Implement LAST** (what comes next)
   - Build incrementally
   - Test continuously
   - Document thoroughly

---

🎯 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>

**Status**: Comprehensive architecture analysis complete
**Next**: Awaiting user decision on implementation approach
**Estimated Implementation**: 28-38 hours for full architecture
