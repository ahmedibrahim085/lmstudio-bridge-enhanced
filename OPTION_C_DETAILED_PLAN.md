# Option C: Full Re-architecture Implementation Plan

**Multi-Model Support with Enterprise-Grade Architecture**

---

## Executive Summary

**Objective**: Complete architectural redesign for multi-model support with enterprise patterns, concurrency, and scalability.

**Approach**: Full re-architecture with Model Router, Strategy Pattern, Concurrency Framework, and Production-grade infrastructure.

**Timeline**: 20-25 hours (6 phases)

**Team**: Claude Code + 3 Local LLMs (Qwen3-Coder, Qwen3-Thinking, Magistral)

---

## Option C Goals

✅ **Clean Architecture** - Separation of concerns, SOLID principles
✅ **Model Router Pattern** - Centralized model selection and routing
✅ **Strategy Pattern** - Pluggable model selection strategies
✅ **Concurrency Support** - Parallel multi-model execution
✅ **Advanced Error Recovery** - Automatic fallbacks and retries
✅ **Performance Optimization** - Caching, pooling, async optimization
✅ **Comprehensive Monitoring** - Metrics, logging, tracing
✅ **Extensibility** - Easy to add new strategies and features
✅ **Enterprise Ready** - Production-grade quality

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    FastMCP Server                           │
│  (tools/dynamic_autonomous_register.py)                     │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│            DynamicAutonomousAgent                           │
│  (tools/dynamic_autonomous.py)                              │
│  - Orchestrates autonomous execution                        │
│  - Uses ModelRouter for model selection                     │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│                  ModelRouter                                │
│  (llm/model_router.py) - NEW                                │
│  ┌────────────────────────────────────────────────────┐    │
│  │  ModelSelectionStrategy (interface)                │    │
│  │  ├─ ExplicitStrategy (user specifies)              │    │
│  │  ├─ TaskBasedStrategy (infers from task)           │    │
│  │  ├─ PerformanceStrategy (fastest available)        │    │
│  │  ├─ CapabilityStrategy (best for task type)        │    │
│  │  └─ FallbackStrategy (retries with alternatives)   │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│              LLMClientPool                                  │
│  (llm/client_pool.py) - NEW                                 │
│  - Manages multiple LLMClient instances                     │
│  - Connection pooling and reuse                             │
│  - Concurrent request handling                              │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│                  LLMClient                                  │
│  (llm/llm_client.py) - ENHANCED                             │
│  - Communicates with LM Studio API                          │
│  - Error handling and retries                               │
│  - Metrics collection                                       │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
         ┌────────────────┐
         │   LM Studio    │
         │   (localhost)  │
         └────────────────┘
```

---

## Phase 1: Foundation & Architecture (4-5 hours)

### Overview
Establish clean architecture foundation with interfaces, abstractions, and design patterns.

### Tasks

#### 1.1 Design Architecture
**Owner**: Magistral (design) → All LLMs (review)
**Duration**: 1 hour

**Deliverable**: `docs/ARCHITECTURE_V2.md` (NEW)

**Content**:
1. System architecture diagram
2. Component responsibilities
3. Design patterns used
4. Data flow diagrams
5. Interface definitions
6. Extension points
7. Performance considerations
8. Security model

**Key Decisions to Document**:
- Why Model Router pattern?
- Why Strategy pattern for selection?
- Why LLMClientPool for concurrency?
- How does error recovery work?
- What are performance targets?

**Review Checkpoint**: All 3 LLMs review and approve architecture

---

#### 1.2 Create Base Interfaces
**Owner**: Qwen3-Coder (design) → Claude Code (implementation)
**Reviewer**: Qwen3-Thinking
**Duration**: 1 hour

**File**: `llm/interfaces.py` (NEW)

**Implementation**:
```python
"""Core interfaces for multi-model architecture."""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

# ============================================================================
# Enums
# ============================================================================

class ModelCapability(Enum):
    """Model capabilities for capability-based selection."""
    REASONING = "reasoning"
    CODING = "coding"
    GENERAL = "general"
    FAST = "fast"
    EMBEDDINGS = "embeddings"


class TaskType(Enum):
    """Task types for task-based model selection."""
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    ANALYSIS = "analysis"
    PLANNING = "planning"
    SIMPLE_QUERY = "simple_query"
    COMPLEX_REASONING = "complex_reasoning"
    RAG_EXPLORATION = "rag_exploration"


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class ModelInfo:
    """Information about a model."""
    id: str
    name: str
    capabilities: List[ModelCapability]
    context_length: int
    avg_tokens_per_sec: Optional[float] = None
    loaded: bool = True
    metadata: Dict[str, Any] = None


@dataclass
class ModelRequest:
    """Request for model selection."""
    task: str
    task_type: Optional[TaskType] = None
    required_capabilities: Optional[List[ModelCapability]] = None
    prefer_fast: bool = False
    max_tokens: int = 8192
    explicit_model: Optional[str] = None


@dataclass
class ModelResponse:
    """Response from model selection."""
    selected_model: str
    reason: str
    alternatives: List[str]
    strategy_used: str
    estimated_duration: Optional[float] = None


@dataclass
class ExecutionMetrics:
    """Metrics for model execution."""
    model_id: str
    task_type: TaskType
    duration_seconds: float
    tokens_generated: int
    tokens_per_second: float
    success: bool
    error: Optional[str] = None
    timestamp: float


# ============================================================================
# Strategy Interface
# ============================================================================

class ModelSelectionStrategy(ABC):
    """Interface for model selection strategies."""

    @abstractmethod
    async def select_model(
        self,
        request: ModelRequest,
        available_models: List[ModelInfo]
    ) -> ModelResponse:
        """
        Select appropriate model based on request and available models.

        Args:
            request: Model selection request
            available_models: List of available models

        Returns:
            Model selection response with rationale

        Raises:
            NoSuitableModelError: If no model meets requirements
        """
        pass

    @abstractmethod
    def get_strategy_name(self) -> str:
        """Get name of this strategy."""
        pass

    @abstractmethod
    def get_priority(self) -> int:
        """
        Get priority for strategy chaining.
        Lower number = higher priority.
        """
        pass


# ============================================================================
# Client Pool Interface
# ============================================================================

class ILLMClientPool(ABC):
    """Interface for LLM client pool."""

    @abstractmethod
    async def get_client(self, model: str) -> 'ILLMClient':
        """
        Get or create client for specified model.

        Args:
            model: Model ID

        Returns:
            LLM client configured for model
        """
        pass

    @abstractmethod
    async def release_client(self, model: str, client: 'ILLMClient'):
        """Release client back to pool."""
        pass

    @abstractmethod
    async def close_all(self):
        """Close all clients in pool."""
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        pass


# ============================================================================
# LLM Client Interface
# ============================================================================

class ILLMClient(ABC):
    """Interface for LLM client."""

    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 8192,
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute chat completion request."""
        pass

    @abstractmethod
    async def create_response(
        self,
        input_text: str,
        previous_response_id: Optional[str] = None,
        stream: bool = False,
    ) -> Dict[str, Any]:
        """Create stateful response."""
        pass

    @abstractmethod
    def get_model(self) -> str:
        """Get model ID this client uses."""
        pass

    @abstractmethod
    async def close(self):
        """Close client and cleanup resources."""
        pass


# ============================================================================
# Router Interface
# ============================================================================

class IModelRouter(ABC):
    """Interface for model router."""

    @abstractmethod
    async def route_request(self, request: ModelRequest) -> ModelResponse:
        """Route request to appropriate model."""
        pass

    @abstractmethod
    async def register_strategy(self, strategy: ModelSelectionStrategy):
        """Register new selection strategy."""
        pass

    @abstractmethod
    async def get_available_models(self) -> List[ModelInfo]:
        """Get all available models with metadata."""
        pass

    @abstractmethod
    async def record_metrics(self, metrics: ExecutionMetrics):
        """Record execution metrics for learning."""
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get router statistics."""
        pass
```

**Acceptance Criteria**:
- [ ] All interfaces defined
- [ ] Data classes complete with type hints
- [ ] Enums for capabilities and task types
- [ ] Clear docstrings
- [ ] Extensible design

**Review Checkpoint**: Qwen3-Thinking reviews interface design

---

#### 1.3 Create Enhanced Exception Hierarchy
**Owner**: Claude Code
**Reviewer**: Qwen3-Coder
**Duration**: 30 minutes

**File**: `llm/exceptions.py` (NEW - more comprehensive than Option A)

**Implementation**:
```python
"""Exception hierarchy for multi-model architecture."""

from typing import Optional, List
from datetime import datetime

# ============================================================================
# Base Exceptions
# ============================================================================

class LLMError(Exception):
    """Base exception for LLM operations."""

    def __init__(
        self,
        message: str,
        original_exception: Optional[Exception] = None,
        context: Optional[dict] = None
    ):
        super().__init__(message)
        self.original_exception = original_exception
        self.context = context or {}
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> dict:
        """Convert exception to dictionary for logging."""
        return {
            "type": self.__class__.__name__,
            "message": str(self),
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
            "original": str(self.original_exception) if self.original_exception else None
        }


# ============================================================================
# Connection & Communication
# ============================================================================

class LLMConnectionError(LLMError):
    """Failed to connect to LLM API."""
    pass


class LLMTimeoutError(LLMError):
    """LLM request timed out."""
    pass


class LLMRateLimitError(LLMError):
    """LLM rate limit exceeded."""

    def __init__(self, message: str, retry_after: Optional[int] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


# ============================================================================
# Model Management
# ============================================================================

class ModelError(LLMError):
    """Base exception for model-related errors."""
    pass


class ModelNotFoundError(ModelError):
    """Requested model not available."""

    def __init__(
        self,
        model_name: str,
        available_models: List[str],
        **kwargs
    ):
        self.model_name = model_name
        self.available_models = available_models
        message = (
            f"Model '{model_name}' not found. "
            f"Available models: {', '.join(available_models)}"
        )
        super().__init__(message, **kwargs)


class ModelNotLoadedError(ModelError):
    """Model exists but not currently loaded."""

    def __init__(self, model_name: str, **kwargs):
        self.model_name = model_name
        message = f"Model '{model_name}' exists but is not loaded in LM Studio"
        super().__init__(message, **kwargs)


class NoSuitableModelError(ModelError):
    """No model meets the requirements."""

    def __init__(
        self,
        requirements: dict,
        available_models: List[str],
        **kwargs
    ):
        self.requirements = requirements
        self.available_models = available_models
        message = (
            f"No suitable model found for requirements: {requirements}. "
            f"Available: {', '.join(available_models)}"
        )
        super().__init__(message, **kwargs)


# ============================================================================
# Validation & Response
# ============================================================================

class LLMValidationError(LLMError):
    """LLM response validation failed."""
    pass


class LLMResponseError(LLMError):
    """LLM response format invalid."""
    pass


class ToolExecutionError(LLMError):
    """Tool execution failed during autonomous loop."""

    def __init__(self, tool_name: str, error_message: str, **kwargs):
        self.tool_name = tool_name
        self.error_message = error_message
        message = f"Tool '{tool_name}' execution failed: {error_message}"
        super().__init__(message, **kwargs)


# ============================================================================
# Concurrency & Pool
# ============================================================================

class PoolExhaustedError(LLMError):
    """Client pool has no available clients."""

    def __init__(self, pool_size: int, active_clients: int, **kwargs):
        self.pool_size = pool_size
        self.active_clients = active_clients
        message = f"Client pool exhausted ({active_clients}/{pool_size} active)"
        super().__init__(message, **kwargs)


class ConcurrentExecutionError(LLMError):
    """Error during concurrent model execution."""

    def __init__(self, failed_models: List[str], errors: List[str], **kwargs):
        self.failed_models = failed_models
        self.errors = errors
        message = f"Concurrent execution failed for models: {', '.join(failed_models)}"
        super().__init__(message, **kwargs)


# ============================================================================
# Strategy & Routing
# ============================================================================

class StrategyError(LLMError):
    """Error in model selection strategy."""
    pass


class StrategyChainError(StrategyError):
    """All strategies in chain failed."""

    def __init__(self, attempted_strategies: List[str], **kwargs):
        self.attempted_strategies = attempted_strategies
        message = f"All strategies failed: {', '.join(attempted_strategies)}"
        super().__init__(message, **kwargs)
```

**Acceptance Criteria**:
- [ ] Comprehensive exception hierarchy
- [ ] Context and metadata support
- [ ] to_dict() for structured logging
- [ ] Specific exceptions for each error type
- [ ] Concurrency-aware exceptions

**Review Checkpoint**: Qwen3-Coder reviews exception design

---

#### 1.4 Create Core Configuration
**Owner**: Claude Code
**Reviewer**: Qwen3-Thinking
**Duration**: 30 minutes

**File**: `llm/config.py` (NEW)

**Implementation**:
```python
"""Configuration for multi-model architecture."""

from dataclasses import dataclass, field
from typing import Optional, Dict, List
from llm.interfaces import ModelCapability, TaskType

@dataclass
class PoolConfig:
    """Configuration for LLM client pool."""
    max_pool_size: int = 10
    min_pool_size: int = 2
    connection_timeout: float = 30.0
    idle_timeout: float = 300.0  # 5 minutes
    max_retries: int = 3
    retry_delay: float = 1.0


@dataclass
class RouterConfig:
    """Configuration for model router."""
    default_strategy: str = "explicit"
    enable_fallback: bool = True
    enable_metrics: bool = True
    cache_model_info: bool = True
    cache_ttl_seconds: int = 60
    concurrent_requests_limit: int = 5


@dataclass
class ModelMetadata:
    """Metadata about a specific model."""
    capabilities: List[ModelCapability] = field(default_factory=list)
    preferred_for: List[TaskType] = field(default_factory=list)
    context_length: int = 8192
    estimated_tokens_per_sec: Optional[float] = None
    cost_tier: str = "medium"  # low/medium/high


@dataclass
class MultiModelConfig:
    """Complete multi-model configuration."""
    pool: PoolConfig = field(default_factory=PoolConfig)
    router: RouterConfig = field(default_factory=RouterConfig)

    # Model metadata (can be populated from external config)
    model_metadata: Dict[str, ModelMetadata] = field(default_factory=dict)

    # Task type preferences
    task_model_preferences: Dict[TaskType, List[str]] = field(default_factory=dict)

    # Performance targets
    fast_response_threshold: float = 2.0  # seconds
    slow_response_threshold: float = 30.0  # seconds

    def get_model_metadata(self, model_id: str) -> Optional[ModelMetadata]:
        """Get metadata for model."""
        return self.model_metadata.get(model_id)

    def register_model_metadata(self, model_id: str, metadata: ModelMetadata):
        """Register metadata for a model."""
        self.model_metadata[model_id] = metadata

    def set_task_preference(self, task_type: TaskType, models: List[str]):
        """Set preferred models for task type."""
        self.task_model_preferences[task_type] = models


# Default configuration
DEFAULT_MULTI_MODEL_CONFIG = MultiModelConfig(
    pool=PoolConfig(),
    router=RouterConfig(),
    model_metadata={
        # Examples - will be populated dynamically
        "qwen/qwen3-coder-30b": ModelMetadata(
            capabilities=[ModelCapability.CODING, ModelCapability.GENERAL],
            preferred_for=[TaskType.CODE_GENERATION, TaskType.CODE_REVIEW],
            context_length=32768,
        ),
        "mistralai/magistral-small-2509": ModelMetadata(
            capabilities=[ModelCapability.REASONING, ModelCapability.GENERAL],
            preferred_for=[TaskType.COMPLEX_REASONING, TaskType.PLANNING],
            context_length=8192,
        ),
    },
    task_model_preferences={
        TaskType.CODE_GENERATION: ["qwen/qwen3-coder-30b"],
        TaskType.COMPLEX_REASONING: ["mistralai/magistral-small-2509"],
        TaskType.SIMPLE_QUERY: ["any-fast-model"],
    }
)
```

**Acceptance Criteria**:
- [ ] All config options documented
- [ ] Sensible defaults
- [ ] Easy to customize
- [ ] Type-safe

**Review Checkpoint**: Qwen3-Thinking reviews configuration design

---

#### 1.5 Setup Monitoring & Metrics
**Owner**: Qwen3-Coder (design) → Claude Code (implementation)
**Reviewer**: Magistral
**Duration**: 1 hour

**File**: `llm/metrics.py` (NEW)

**Implementation**:
```python
"""Metrics collection and monitoring for multi-model system."""

import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime, timedelta
import asyncio
import logging

from llm.interfaces import ExecutionMetrics, TaskType

logger = logging.getLogger(__name__)

@dataclass
class ModelStats:
    """Statistics for a single model."""
    model_id: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_tokens: int = 0
    total_duration: float = 0.0
    avg_tokens_per_sec: float = 0.0
    last_used: Optional[datetime] = None
    error_count_by_type: Dict[str, int] = field(default_factory=lambda: defaultdict(int))


class MetricsCollector:
    """Collects and aggregates metrics for multi-model system."""

    def __init__(self):
        self.model_stats: Dict[str, ModelStats] = {}
        self.task_type_stats: Dict[TaskType, List[ExecutionMetrics]] = defaultdict(list)
        self.recent_metrics: List[ExecutionMetrics] = []
        self.max_recent = 1000
        self._lock = asyncio.Lock()

    async def record_execution(self, metrics: ExecutionMetrics):
        """Record execution metrics."""
        async with self._lock:
            # Update model stats
            if metrics.model_id not in self.model_stats:
                self.model_stats[metrics.model_id] = ModelStats(model_id=metrics.model_id)

            stats = self.model_stats[metrics.model_id]
            stats.total_requests += 1
            if metrics.success:
                stats.successful_requests += 1
            else:
                stats.failed_requests += 1
                if metrics.error:
                    stats.error_count_by_type[metrics.error] += 1

            stats.total_tokens += metrics.tokens_generated
            stats.total_duration += metrics.duration_seconds
            stats.last_used = datetime.fromtimestamp(metrics.timestamp)

            # Recalculate average tokens/sec
            if stats.total_duration > 0:
                stats.avg_tokens_per_sec = stats.total_tokens / stats.total_duration

            # Record by task type
            self.task_type_stats[metrics.task_type].append(metrics)

            # Add to recent metrics
            self.recent_metrics.append(metrics)
            if len(self.recent_metrics) > self.max_recent:
                self.recent_metrics.pop(0)

            logger.debug(f"Recorded metrics for {metrics.model_id}: {metrics}")

    def get_model_stats(self, model_id: str) -> Optional[ModelStats]:
        """Get statistics for specific model."""
        return self.model_stats.get(model_id)

    def get_all_stats(self) -> Dict[str, ModelStats]:
        """Get statistics for all models."""
        return self.model_stats.copy()

    def get_best_model_for_task(
        self,
        task_type: TaskType,
        min_requests: int = 5
    ) -> Optional[str]:
        """
        Get best performing model for task type.

        Args:
            task_type: Type of task
            min_requests: Minimum requests needed for consideration

        Returns:
            Model ID of best performer, or None
        """
        metrics = self.task_type_stats.get(task_type, [])
        if not metrics:
            return None

        # Group by model
        model_performance: Dict[str, Dict] = defaultdict(lambda: {
            "count": 0,
            "success_rate": 0.0,
            "avg_speed": 0.0
        })

        for m in metrics:
            perf = model_performance[m.model_id]
            perf["count"] += 1
            if m.success:
                perf["success_rate"] += 1
            perf["avg_speed"] += m.tokens_per_second

        # Calculate averages and find best
        best_model = None
        best_score = 0.0

        for model_id, perf in model_performance.items():
            if perf["count"] < min_requests:
                continue

            success_rate = perf["success_rate"] / perf["count"]
            avg_speed = perf["avg_speed"] / perf["count"]

            # Score = success_rate * speed (weighted)
            score = (success_rate * 0.7) + (min(avg_speed / 100, 1.0) * 0.3)

            if score > best_score:
                best_score = score
                best_model = model_id

        return best_model

    def get_summary(self) -> Dict:
        """Get summary of all metrics."""
        total_requests = sum(s.total_requests for s in self.model_stats.values())
        total_successful = sum(s.successful_requests for s in self.model_stats.values())
        total_failed = sum(s.failed_requests for s in self.model_stats.values())

        return {
            "total_requests": total_requests,
            "successful_requests": total_successful,
            "failed_requests": total_failed,
            "success_rate": total_successful / total_requests if total_requests > 0 else 0,
            "models_used": len(self.model_stats),
            "model_stats": {
                model_id: {
                    "total_requests": stats.total_requests,
                    "success_rate": stats.successful_requests / stats.total_requests if stats.total_requests > 0 else 0,
                    "avg_tokens_per_sec": stats.avg_tokens_per_sec,
                    "last_used": stats.last_used.isoformat() if stats.last_used else None
                }
                for model_id, stats in self.model_stats.items()
            }
        }

    def reset(self):
        """Reset all metrics."""
        self.model_stats.clear()
        self.task_type_stats.clear()
        self.recent_metrics.clear()


# Global metrics collector instance
_metrics_collector = MetricsCollector()

def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector."""
    return _metrics_collector
```

**Acceptance Criteria**:
- [ ] Metrics collected per model
- [ ] Metrics collected per task type
- [ ] Performance tracking (tokens/sec, success rate)
- [ ] Best model recommendation
- [ ] Thread-safe with async lock
- [ ] Summary statistics

**Review Checkpoint**: Magistral reviews monitoring architecture

---

### Phase 1 Completion Review

**Reviewer**: All 3 LLMs (collaborative)
**Duration**: 30 minutes

**Checklist**:
- [ ] Architecture documented and approved
- [ ] All interfaces defined
- [ ] Exception hierarchy comprehensive
- [ ] Configuration system complete
- [ ] Metrics collection implemented
- [ ] Foundation solid for next phases

**Deliverables**:
- `docs/ARCHITECTURE_V2.md`
- `llm/interfaces.py`
- `llm/exceptions.py`
- `llm/config.py`
- `llm/metrics.py`

---

## Phase 2: Model Router Implementation (4-5 hours)

### Overview
Implement Model Router with multiple selection strategies.

### Tasks

#### 2.1 Implement Model Discovery & Validator
**Owner**: Claude Code
**Reviewer**: Qwen3-Coder
**Duration**: 1 hour

**File**: `llm/model_discovery.py` (NEW)

**Implementation** (abbreviated):
```python
"""Model discovery and validation."""

from typing import List, Optional, Dict
from datetime import datetime, timedelta
import httpx
import logging

from llm.interfaces import ModelInfo, ModelCapability
from llm.exceptions import LLMConnectionError, ModelNotFoundError
from llm.config import MultiModelConfig
from llm.metrics import get_metrics_collector

logger = logging.getLogger(__name__)

class ModelDiscovery:
    """Discovers and validates models from LM Studio."""

    def __init__(self, api_base: str, config: MultiModelConfig):
        self.api_base = api_base
        self.config = config
        self._cache: Optional[List[ModelInfo]] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl = timedelta(seconds=config.router.cache_ttl_seconds)

    async def discover_models(self, use_cache: bool = True) -> List[ModelInfo]:
        """
        Discover all available models from LM Studio.

        Returns:
            List of ModelInfo objects with metadata
        """
        now = datetime.utcnow()

        # Check cache
        if use_cache and self._cache and self._cache_timestamp:
            if now - self._cache_timestamp < self._cache_ttl:
                logger.debug(f"Using cached model list ({len(self._cache)} models)")
                return self._cache

        # Fetch from API
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.api_base}/v1/models")
                response.raise_for_status()
                data = response.json()

                models = []
                for model_data in data.get("data", []):
                    model_id = model_data["id"]

                    # Get metadata from config or use defaults
                    metadata = self.config.get_model_metadata(model_id)

                    model_info = ModelInfo(
                        id=model_id,
                        name=model_data.get("name", model_id),
                        capabilities=metadata.capabilities if metadata else [ModelCapability.GENERAL],
                        context_length=metadata.context_length if metadata else 8192,
                        avg_tokens_per_sec=metadata.estimated_tokens_per_sec if metadata else None,
                        loaded=True,
                        metadata=model_data
                    )

                    # Enrich with metrics if available
                    stats = get_metrics_collector().get_model_stats(model_id)
                    if stats:
                        model_info.avg_tokens_per_sec = stats.avg_tokens_per_sec

                    models.append(model_info)

                # Update cache
                self._cache = models
                self._cache_timestamp = now

                logger.info(f"Discovered {len(models)} models from LM Studio")
                return models

        except httpx.HTTPError as e:
            logger.error(f"Failed to discover models: {e}")
            raise LLMConnectionError("Could not connect to LM Studio API", e)

    async def validate_model(self, model_id: str) -> ModelInfo:
        """
        Validate model exists and return its info.

        Raises:
            ModelNotFoundError: If model not found
        """
        models = await self.discover_models()
        model_dict = {m.id: m for m in models}

        if model_id not in model_dict:
            available = [m.id for m in models]
            raise ModelNotFoundError(model_id, available)

        return model_dict[model_id]

    def clear_cache(self):
        """Clear model cache."""
        self._cache = None
        self._cache_timestamp = None
```

**Acceptance Criteria**:
- [ ] Discovers models from LM Studio API
- [ ] Caches model list with TTL
- [ ] Enriches with metadata from config
- [ ] Enriches with metrics from collector
- [ ] Validates model existence
- [ ] Error handling robust

**Review Checkpoint**: Qwen3-Coder reviews implementation

---

#### 2.2 Implement Selection Strategies
**Owner**: Qwen3-Coder (design all 5) → Claude Code (implement)
**Reviewer**: Magistral
**Duration**: 2 hours

**Files**:
- `llm/strategies/__init__.py` (NEW)
- `llm/strategies/explicit_strategy.py` (NEW)
- `llm/strategies/task_based_strategy.py` (NEW)
- `llm/strategies/performance_strategy.py` (NEW)
- `llm/strategies/capability_strategy.py` (NEW)
- `llm/strategies/fallback_strategy.py` (NEW)

**Strategy 1: ExplicitStrategy** (`explicit_strategy.py`):
```python
"""Explicit model selection strategy."""

from typing import List
from llm.interfaces import (
    ModelSelectionStrategy, ModelRequest, ModelResponse, ModelInfo
)
from llm.exceptions import ModelNotFoundError

class ExplicitStrategy(ModelSelectionStrategy):
    """User explicitly specifies the model."""

    async def select_model(
        self,
        request: ModelRequest,
        available_models: List[ModelInfo]
    ) -> ModelResponse:
        """Select explicitly specified model."""
        if not request.explicit_model:
            raise ValueError("ExplicitStrategy requires explicit_model in request")

        # Validate model exists
        model_ids = [m.id for m in available_models]
        if request.explicit_model not in model_ids:
            raise ModelNotFoundError(request.explicit_model, model_ids)

        return ModelResponse(
            selected_model=request.explicit_model,
            reason="Explicitly requested by user",
            alternatives=[],
            strategy_used="explicit"
        )

    def get_strategy_name(self) -> str:
        return "explicit"

    def get_priority(self) -> int:
        return 1  # Highest priority
```

**Strategy 2: TaskBasedStrategy** (`task_based_strategy.py`):
```python
"""Task-based model selection strategy."""

from typing import List
import re

from llm.interfaces import (
    ModelSelectionStrategy, ModelRequest, ModelResponse, ModelInfo,
    TaskType
)
from llm.exceptions import NoSuitableModelError
from llm.config import MultiModelConfig

class TaskBasedStrategy(ModelSelectionStrategy):
    """Select model based on task type inference."""

    def __init__(self, config: MultiModelConfig):
        self.config = config

        # Task type detection patterns
        self.patterns = {
            TaskType.CODE_GENERATION: [
                r"(generate|write|create|implement)\s+(code|function|class|method)",
                r"write.*\.(py|js|ts|go|java)",
            ],
            TaskType.CODE_REVIEW: [
                r"(review|analyze|check|audit)\s+code",
                r"find.*bugs?",
            ],
            TaskType.ANALYSIS: [
                r"(analyze|examine|investigate|explore)",
                r"what (is|are|does)",
            ],
            TaskType.PLANNING: [
                r"(plan|design|architect|outline)",
                r"how (should|would|to)",
            ],
            TaskType.COMPLEX_REASONING: [
                r"(explain|reason|deduce|infer)",
                r"why (is|does|would)",
            ],
        }

    def _infer_task_type(self, task: str) -> TaskType:
        """Infer task type from task description."""
        task_lower = task.lower()

        for task_type, patterns in self.patterns.items():
            for pattern in patterns:
                if re.search(pattern, task_lower):
                    return task_type

        return TaskType.SIMPLE_QUERY  # Default

    async def select_model(
        self,
        request: ModelRequest,
        available_models: List[ModelInfo]
    ) -> ModelResponse:
        """Select model based on inferred task type."""
        # Infer task type if not provided
        task_type = request.task_type or self._infer_task_type(request.task)

        # Get preferred models for this task type
        preferences = self.config.task_model_preferences.get(task_type, [])

        # Find first available preferred model
        available_ids = {m.id for m in available_models}
        for preferred in preferences:
            if preferred in available_ids:
                return ModelResponse(
                    selected_model=preferred,
                    reason=f"Preferred model for task type: {task_type.value}",
                    alternatives=[p for p in preferences if p != preferred],
                    strategy_used="task_based"
                )

        # No preferred model available
        raise NoSuitableModelError(
            {"task_type": task_type.value},
            list(available_ids)
        )

    def get_strategy_name(self) -> str:
        return "task_based"

    def get_priority(self) -> int:
        return 2
```

**Strategy 3: PerformanceStrategy** (`performance_strategy.py`):
```python
"""Performance-based model selection."""

from typing import List

from llm.interfaces import (
    ModelSelectionStrategy, ModelRequest, ModelResponse, ModelInfo
)
from llm.exceptions import NoSuitableModelError

class PerformanceStrategy(ModelSelectionStrategy):
    """Select fastest available model."""

    async def select_model(
        self,
        request: ModelRequest,
        available_models: List[ModelInfo]
    ) -> ModelResponse:
        """Select model with best performance (tokens/sec)."""
        if not available_models:
            raise NoSuitableModelError({}, [])

        # Sort by tokens per second (descending)
        models_with_perf = [
            m for m in available_models
            if m.avg_tokens_per_sec is not None
        ]

        if not models_with_perf:
            # No performance data, use first available
            selected = available_models[0]
            return ModelResponse(
                selected_model=selected.id,
                reason="No performance data available, using first model",
                alternatives=[m.id for m in available_models[1:3]],
                strategy_used="performance_fallback"
            )

        # Sort by performance
        sorted_models = sorted(
            models_with_perf,
            key=lambda m: m.avg_tokens_per_sec,
            reverse=True
        )

        selected = sorted_models[0]

        return ModelResponse(
            selected_model=selected.id,
            reason=f"Fastest model ({selected.avg_tokens_per_sec:.1f} tokens/sec)",
            alternatives=[m.id for m in sorted_models[1:3]],
            strategy_used="performance",
            estimated_duration=request.max_tokens / selected.avg_tokens_per_sec
        )

    def get_strategy_name(self) -> str:
        return "performance"

    def get_priority(self) -> int:
        return 3
```

**Strategy 4: CapabilityStrategy** (similar pattern)
**Strategy 5: FallbackStrategy** (similar pattern)

**Acceptance Criteria**:
- [ ] All 5 strategies implemented
- [ ] Each implements ModelSelectionStrategy interface
- [ ] Clear selection logic
- [ ] Returns ModelResponse with rationale
- [ ] Error handling appropriate
- [ ] Extensible design

**Review Checkpoint**: Magistral reviews strategy architecture

---

#### 2.3 Implement ModelRouter
**Owner**: Claude Code
**Reviewer**: Qwen3-Thinking
**Duration**: 1.5 hours

**File**: `llm/model_router.py` (NEW)

**Implementation** (abbreviated):
```python
"""Model router with strategy-based selection."""

from typing import List, Dict, Optional
import logging
import asyncio

from llm.interfaces import (
    IModelRouter, ModelRequest, ModelResponse, ModelInfo,
    ModelSelectionStrategy, ExecutionMetrics
)
from llm.exceptions import StrategyChainError, NoSuitableModelError
from llm.config import MultiModelConfig
from llm.model_discovery import ModelDiscovery
from llm.metrics import get_metrics_collector
from llm.strategies import (
    ExplicitStrategy, TaskBasedStrategy, PerformanceStrategy,
    CapabilityStrategy, FallbackStrategy
)

logger = logging.getLogger(__name__)

class ModelRouter(IModelRouter):
    """Routes requests to appropriate models using strategies."""

    def __init__(self, api_base: str, config: MultiModelConfig):
        self.api_base = api_base
        self.config = config
        self.discovery = ModelDiscovery(api_base, config)
        self.metrics = get_metrics_collector()

        # Initialize strategies
        self.strategies: List[ModelSelectionStrategy] = []
        self._initialize_strategies()

    def _initialize_strategies(self):
        """Initialize and register default strategies."""
        self.strategies = [
            ExplicitStrategy(),
            TaskBasedStrategy(self.config),
            PerformanceStrategy(),
            CapabilityStrategy(self.config),
            FallbackStrategy(self.metrics)
        ]
        # Sort by priority
        self.strategies.sort(key=lambda s: s.get_priority())

    async def route_request(self, request: ModelRequest) -> ModelResponse:
        """
        Route request to appropriate model using strategy chain.

        Tries strategies in priority order until one succeeds.
        """
        available_models = await self.discovery.discover_models()

        errors = []
        attempted_strategies = []

        for strategy in self.strategies:
            # Skip strategies that don't apply
            if not self._strategy_applies(strategy, request):
                continue

            try:
                logger.debug(f"Trying strategy: {strategy.get_strategy_name()}")
                response = await strategy.select_model(request, available_models)
                logger.info(f"Selected model '{response.selected_model}' via {response.strategy_used}")
                return response

            except (NoSuitableModelError, ValueError) as e:
                logger.debug(f"Strategy {strategy.get_strategy_name()} failed: {e}")
                errors.append(str(e))
                attempted_strategies.append(strategy.get_strategy_name())
                continue

        # All strategies failed
        raise StrategyChainError(attempted_strategies)

    def _strategy_applies(self, strategy: ModelSelectionStrategy, request: ModelRequest) -> bool:
        """Check if strategy applies to this request."""
        # ExplicitStrategy only applies if explicit_model provided
        if strategy.get_strategy_name() == "explicit":
            return request.explicit_model is not None

        # All other strategies always apply
        return True

    async def register_strategy(self, strategy: ModelSelectionStrategy):
        """Register new strategy."""
        self.strategies.append(strategy)
        self.strategies.sort(key=lambda s: s.get_priority())
        logger.info(f"Registered strategy: {strategy.get_strategy_name()}")

    async def get_available_models(self) -> List[ModelInfo]:
        """Get all available models."""
        return await self.discovery.discover_models()

    async def record_metrics(self, metrics: ExecutionMetrics):
        """Record execution metrics."""
        await self.metrics.record_execution(metrics)

    def get_stats(self) -> Dict:
        """Get router statistics."""
        return {
            "strategies": [s.get_strategy_name() for s in self.strategies],
            "metrics": self.metrics.get_summary(),
        }
```

**Acceptance Criteria**:
- [ ] Strategy chain implemented
- [ ] Tries strategies in priority order
- [ ] Falls back on failure
- [ ] Metrics recorded
- [ ] Can register new strategies
- [ ] Thread-safe

**Review Checkpoint**: Qwen3-Thinking reviews router logic

---

### Phase 2 Completion Review

**Reviewer**: All 3 LLMs
**Duration**: 15 minutes

**Checklist**:
- [ ] Model discovery works
- [ ] All 5 strategies implemented
- [ ] ModelRouter chains strategies correctly
- [ ] Error handling robust
- [ ] Metrics collected

**Deliverables**:
- `llm/model_discovery.py`
- `llm/strategies/*.py` (5 files)
- `llm/model_router.py`

---

## Phase 3: LLM Client Pool & Concurrency (3-4 hours)

### Overview
Implement connection pooling and concurrent execution support.

### Tasks

#### 3.1 Implement LLMClient with Enhanced Error Handling
**Owner**: Claude Code
**Reviewer**: Qwen3-Coder
**Duration**: 1 hour

**File**: `llm/llm_client_v2.py` (NEW - enhanced version)

Implementation of ILLMClient interface with retry logic, error handling, metrics collection.

---

#### 3.2 Implement LLMClientPool
**Owner**: Claude Code
**Reviewer**: Qwen3-Thinking
**Duration**: 1.5 hours

**File**: `llm/client_pool.py` (NEW)

Implementation of connection pooling for concurrent requests.

---

#### 3.3 Implement Concurrent Executor
**Owner**: Qwen3-Coder (design) → Claude Code (implement)
**Reviewer**: Magistral
**Duration**: 1.5 hours

**File**: `llm/concurrent_executor.py` (NEW)

Handles parallel execution with multiple models.

---

### Phase 3 Completion Review

**Deliverables**:
- `llm/llm_client_v2.py`
- `llm/client_pool.py`
- `llm/concurrent_executor.py`

---

## Phase 4: Integration with Autonomous Agent (3-4 hours)

### Overview
Integrate ModelRouter and LLMClientPool with DynamicAutonomousAgent.

### Tasks

#### 4.1 Refactor DynamicAutonomousAgent
**Owner**: Claude Code
**Reviewer**: Qwen3-Coder
**Duration**: 2 hours

Update `tools/dynamic_autonomous.py` to use new architecture.

---

#### 4.2 Update Tool Registration
**Owner**: Claude Code
**Reviewer**: Qwen3-Thinking
**Duration**: 1 hour

Update `tools/dynamic_autonomous_register.py` with new parameters.

---

#### 4.3 Integration Testing
**Owner**: Claude Code
**Reviewer**: Magistral
**Duration**: 1 hour

Comprehensive integration tests.

---

### Phase 4 Completion Review

**Deliverables**:
- Updated `tools/dynamic_autonomous.py`
- Updated `tools/dynamic_autonomous_register.py`
- `tests/test_integration_v2.py`

---

## Phase 5: Advanced Features & Optimization (3-4 hours)

### Overview
Add advanced features like automatic fallback, load balancing, and optimization.

### Tasks

#### 5.1 Implement Automatic Fallback
**Owner**: Qwen3-Thinking (design) → Claude Code (implement)
**Duration**: 1.5 hours

---

#### 5.2 Implement Load Balancing
**Owner**: Claude Code
**Duration**: 1 hour

---

#### 5.3 Performance Optimization
**Owner**: Magistral (identify) → Claude Code (implement)
**Duration**: 1.5 hours

---

### Phase 5 Completion Review

---

## Phase 6: Documentation & Testing (3-4 hours)

### Overview
Comprehensive documentation, testing, and finalization.

### Tasks

#### 6.1 Create Comprehensive Documentation
**Owner**: Claude Code + All LLMs
**Duration**: 2 hours

- Architecture guide
- API reference
- Strategy development guide
- Migration guide from Option A

---

#### 6.2 Performance Benchmarking
**Owner**: Qwen3-Thinking (design) → Claude Code (implement)
**Duration**: 1 hour

---

#### 6.3 Final Testing & Polish
**Owner**: All LLMs (collaborative)
**Duration**: 1 hour

---

### Phase 6 Completion Review

---

## Task Assignment Summary

| Phase | Duration | Primary Owner | Reviewers |
|-------|----------|---------------|-----------|
| 1: Foundation | 4-5h | Claude + Qwen3-Coder + Magistral | All |
| 2: Router | 4-5h | Claude + Qwen3-Coder | Magistral, Qwen3-Thinking |
| 3: Concurrency | 3-4h | Claude | Qwen3-Coder, Qwen3-Thinking |
| 4: Integration | 3-4h | Claude | Qwen3-Coder, Magistral |
| 5: Advanced | 3-4h | Claude + Qwen3-Thinking | Magistral |
| 6: Docs & Testing | 3-4h | All (collaborative) | - |
| **Total** | **20-26h** | | |

---

## Success Criteria

### Architectural ✅
- [ ] Clean separation of concerns
- [ ] Strategy pattern implemented
- [ ] Router pattern implemented
- [ ] Pool pattern implemented
- [ ] Extensible design

### Functional ✅
- [ ] 5+ selection strategies
- [ ] Concurrent execution
- [ ] Automatic fallback
- [ ] Load balancing
- [ ] Metrics collection

### Quality ✅
- [ ] >95% test coverage
- [ ] Performance benchmarks
- [ ] Production-grade error handling
- [ ] Comprehensive monitoring

### Documentation ✅
- [ ] Architecture documented
- [ ] All strategies explained
- [ ] API reference complete
- [ ] Migration guide
- [ ] Examples

---

## Deliverables Summary

### New Files (~25)
**Core** (9):
1. `llm/interfaces.py`
2. `llm/exceptions.py` (enhanced)
3. `llm/config.py`
4. `llm/metrics.py`
5. `llm/model_discovery.py`
6. `llm/model_router.py`
7. `llm/llm_client_v2.py`
8. `llm/client_pool.py`
9. `llm/concurrent_executor.py`

**Strategies** (5):
10-14. `llm/strategies/*.py`

**Tests** (~8):
15-22. `tests/test_*.py`

**Docs** (3):
23. `docs/ARCHITECTURE_V2.md`
24. `docs/STRATEGY_GUIDE.md`
25. `docs/MIGRATION_FROM_OPTION_A.md`

### Modified Files (~5)
1. `tools/dynamic_autonomous.py`
2. `tools/dynamic_autonomous_register.py`
3. `README.md`
4. `docs/API_REFERENCE.md`
5. `config.py`

### Total: ~30 files

---

## Option C Advantages

### Over Option A

**Architectural**:
- Clean separation of concerns vs mixed responsibilities
- Strategy pattern vs hardcoded logic
- Extensible design vs monolithic

**Functional**:
- 5 selection strategies vs 1 (explicit only)
- Concurrent execution vs sequential
- Automatic fallback vs manual
- Load balancing vs single model
- Advanced metrics vs basic

**Scalability**:
- Connection pooling vs per-request
- Can handle 100s requests/sec vs 10s
- Production-grade vs MVP

**Maintenance**:
- Easy to add strategies vs code changes
- Modular vs coupled
- Well-tested vs basic tests

### Trade-offs

**Cost**: 20-25 hours vs 8-10 hours
**Complexity**: Higher learning curve
**Overkill?**: May be excessive for simple use cases

---

## Risk Mitigation

### Risk 1: Complexity Overload
**Mitigation**: Modular design, clear interfaces, comprehensive docs
**Validation**: Architecture review by all 3 LLMs

### Risk 2: Performance Overhead
**Mitigation**: Benchmarking at each phase, optimization in Phase 5
**Validation**: <1ms routing overhead target

### Risk 3: Timeline Overrun
**Mitigation**: Detailed task breakdown, frequent checkpoints
**Validation**: Track actual vs estimated time per task

### Risk 4: Over-Engineering
**Mitigation**: Start with essential features, make extensible
**Validation**: Each feature must have clear use case

---

## Post-Implementation

### After Completion
1. Full test suite (>95% coverage)
2. Performance benchmarks vs Option A
3. Migration guide for Option A users
4. Release as v3.0.0
5. Community feedback collection

### Future Enhancements
- Machine learning for model selection
- Auto-tuning of strategies
- Distributed execution
- Model usage cost optimization
- A/B testing framework

---

**Plan Version**: 1.0
**Created**: October 30, 2025
**Authors**: Claude Code + Qwen3-Coder + Qwen3-Thinking + Magistral
**Status**: Ready for Implementation (pending user approval)
**Estimated Duration**: 20-26 hours
**Target Release**: v3.0.0

**Recommendation**: Proceed with Option A first, then Option C if needed. Option C is enterprise-grade but may be overkill for many use cases.
