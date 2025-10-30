# Option A: Production-Hardened Implementation Plan V2.0

**Multi-Model Support + Qwen Critical Fixes for LM Studio Bridge Enhanced**

**Plan Updated**: October 30, 2025 (Post-Qwen Review)
**Original Plan**: Option A Hardened MVP
**Status**: 🔴 **CRITICAL UPDATES REQUIRED**

---

## Executive Summary

**Critical Update**: Qwen 3 LLM review identified **production-blocking issues** in current implementation that must be fixed before adding multi-model support.

**New Approach**: Fix critical production gaps FIRST (Phases 0-1), THEN add multi-model support (Phases 2-4)

**Timeline**: 18-22 hours total (was 8-10 hours)
- **Phase 0**: Critical Production Fixes (3-4 hours) 🔴 **MUST DO FIRST**
- **Phase 1**: Production Hardening (5-6 hours) 🟠 **HIGH PRIORITY**
- **Phase 2**: Multi-Model Foundation (3-3.5 hours)
- **Phase 3**: Multi-Model Integration (3-3.5 hours)
- **Phase 4**: Documentation & Testing (3-4 hours)

**Team**: Claude Code + Qwen 3 (reviewer/validator)

---

## Qwen Review Findings Summary

**Overall Rating**: 6/10 (Good foundation, significant production risks)
**Status**: ❌ **NOT production-ready**

### Critical Issues Identified by Qwen 🚨

| Issue | Severity | Impact | Current State |
|-------|----------|--------|---------------|
| **No-TTL Approach** | 🔴 Critical | Memory leaks, OOM crashes | Implemented incorrectly |
| **False Persistence Assumption** | 🔴 Critical | Model unloads despite preloading | Architectural flaw |
| **Zero Failure Testing** | 🔴 Critical | System breaks under stress | No tests exist |
| **Missing Error Handling** | 🔴 Critical | Silent failures, no recovery | No retry logic |
| **No Security Testing** | 🟠 High | Data leakage, unauthorized access | Not tested |
| **No Performance Testing** | 🟠 High | Cannot validate production SLAs | No benchmarks |

### Reordered Priority

**OLD Order** (wrong):
1. Add multi-model support
2. Add validation
3. Add error handling
4. Documentation

**NEW Order** (correct, based on Qwen + dependencies):
1. **Fix TTL configuration** (blocks everything)
2. **Add health checks** (validates assumptions)
3. **Add retry logic & error handling** (prevents failures)
4. **Add failure scenario tests** (validates robustness)
5. **Add performance tests** (validates production readiness)
6. THEN add multi-model support

---

## Phase 0: Critical Production Fixes (3-4 hours) 🔴

**Priority**: MUST complete before any other work
**Owner**: Claude Code
**Reviewer**: Qwen 3
**Blockers**: None

### Overview

Fix the 3 most critical production-blocking issues identified by Qwen that make current implementation unsafe for production.

---

### Task 0.1: Fix TTL Configuration (CRITICAL)

**Time**: 1 hour
**Severity**: 🔴 CRITICAL - Causes memory leaks and OOM

#### Problem (from Qwen Review)

```python
# Current (BROKEN) - No TTL = infinite loading
if not keep_loaded:
    cmd.extend(["--ttl", "300"])  # Only adds TTL when NOT keeping

# Result: Models stay loaded forever → Memory leak → OOM crash
```

**Why This Is Dangerous**:
- Models never unload → eventually fill all RAM
- No mechanism to free memory for other models
- Unscalable for production (multiple models/users)
- **FALSE ASSUMPTION**: No TTL ≠ OS can still kill process

#### Solution

```python
# utils/lms_helper.py

# Add configuration
from config import get_config

DEFAULT_MODEL_TTL = 600  # 10 minutes (configurable)
TEMP_MODEL_TTL = 300     # 5 minutes for temporary models

@classmethod
def load_model(cls, model_name: str, keep_loaded: bool = True, ttl: Optional[int] = None) -> bool:
    """
    Load model with configurable TTL.

    Args:
        model_name: Model to load
        keep_loaded: If True, use longer TTL (10m); if False, use shorter TTL (5m)
        ttl: Optional explicit TTL override

    Returns:
        True if loaded successfully
    """
    if not cls.is_installed():
        logger.warning("LMS CLI not available")
        return False

    try:
        cmd = ["lms", "load", model_name, "--yes"]

        # ALWAYS use TTL (never infinite loading)
        if ttl is not None:
            actual_ttl = ttl
        elif keep_loaded:
            actual_ttl = DEFAULT_MODEL_TTL  # 10 minutes
        else:
            actual_ttl = TEMP_MODEL_TTL      # 5 minutes

        cmd.extend(["--ttl", str(actual_ttl)])

        logger.info(f"Loading model '{model_name}' with TTL={actual_ttl}s")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            logger.info(f"✅ Model loaded: {model_name} (TTL={actual_ttl}s)")
            return True
        else:
            logger.error(f"Failed to load model: {result.stderr}")
            return False

    except Exception as e:
        logger.error(f"Error loading model: {e}")
        return False
```

**Config File Addition** (`config.py`):

```python
class LMSConfig:
    """LMS CLI configuration."""
    default_model_ttl: int = 600    # 10 minutes
    temp_model_ttl: int = 300       # 5 minutes
    max_model_ttl: int = 3600       # 1 hour maximum
```

**Acceptance Criteria**:
- [ ] ALL models loaded with explicit TTL
- [ ] No models can have infinite TTL
- [ ] TTL configurable via config
- [ ] Logging shows TTL value
- [ ] Documentation updated

**Testing**:
```python
def test_model_has_ttl():
    """Verify all models get explicit TTL."""
    LMSHelper.load_model("test-model", keep_loaded=True)
    # Verify lms command includes --ttl parameter
    assert "--ttl" in captured_command
    assert "600" in captured_command  # Default TTL

def test_custom_ttl():
    """Verify custom TTL works."""
    LMSHelper.load_model("test-model", ttl=1800)
    assert "1800" in captured_command
```

---

### Task 0.2: Add Health Check Verification

**Time**: 1 hour
**Severity**: 🔴 CRITICAL - Catches false positives

#### Problem (from Qwen Review)

```python
# Current (BROKEN)
if LMSHelper.ensure_model_loaded(model_to_use):
    logger.info("✅ Model preloaded")  # But is it REALLY loaded?
    # System proceeds without verification
```

**Why This Fails**:
- `ensure_model_loaded()` returns True even if model isn't actually loaded
- No verification that model is available
- False positive causes 404 errors in production
- #1 cause of production failures per Qwen

#### Solution

```python
# utils/lms_helper.py

@classmethod
def verify_model_loaded(cls, model_name: str) -> bool:
    """
    Verify model is actually loaded (not just CLI state).

    Args:
        model_name: Model to verify

    Returns:
        True if model is actually loaded
    """
    try:
        loaded_models = cls.list_loaded_models()
        if not loaded_models:
            return False

        # Check if model is in loaded list
        for model in loaded_models:
            if model.get('identifier') == model_name:
                logger.debug(f"Model '{model_name}' verified loaded")
                return True

        logger.warning(f"Model '{model_name}' not found in loaded models")
        return False

    except Exception as e:
        logger.error(f"Error verifying model: {e}")
        return False


@classmethod
def ensure_model_loaded_with_verification(cls, model_name: str, ttl: Optional[int] = None) -> bool:
    """
    Ensure model is loaded AND verify it's actually available.

    This prevents false positives where CLI reports success but model isn't loaded.

    Args:
        model_name: Model to ensure loaded
        ttl: Optional TTL override

    Returns:
        True if model is loaded and verified

    Raises:
        ModelLoadError: If model fails to load or verify
    """
    # Step 1: Check if already loaded
    if cls.is_model_loaded(model_name):
        logger.debug(f"Model '{model_name}' already loaded")
        return True

    # Step 2: Load model
    logger.info(f"Loading model '{model_name}'...")
    if not cls.load_model(model_name, keep_loaded=True, ttl=ttl):
        raise ModelLoadError(f"Failed to load model '{model_name}'")

    # Step 3: VERIFY model is actually loaded (CRITICAL)
    import time
    time.sleep(2)  # Give LM Studio time to load

    if not cls.verify_model_loaded(model_name):
        raise ModelLoadError(
            f"Model '{model_name}' reported loaded but verification failed. "
            "This usually means LM Studio is under memory pressure."
        )

    logger.info(f"✅ Model '{model_name}' loaded and verified")
    return True


class ModelLoadError(Exception):
    """Raised when model fails to load or verify."""
    pass
```

**Update Autonomous Tools** (`tools/autonomous.py`):

```python
# Replace all calls to ensure_model_loaded with ensure_model_loaded_with_verification

# OLD (BROKEN):
if LMSHelper.ensure_model_loaded(model_to_use):
    logger.info("✅ Model preloaded")

# NEW (FIXED):
try:
    LMSHelper.ensure_model_loaded_with_verification(model_to_use)
    logger.info("✅ Model preloaded and VERIFIED")
except ModelLoadError as e:
    logger.error(f"❌ Model load failed: {e}")
    raise
```

**Acceptance Criteria**:
- [ ] Health check verifies model actually loaded
- [ ] False positives caught
- [ ] Clear error when verification fails
- [ ] All autonomous functions use new method
- [ ] Tests cover verification failure

**Testing**:
```python
def test_verification_catches_false_positive():
    """Verify health check catches when model not actually loaded."""
    # Mock: CLI says success, but model not in loaded list
    with mock.patch('LMSHelper.load_model', return_value=True):
        with mock.patch('LMSHelper.verify_model_loaded', return_value=False):
            with pytest.raises(ModelLoadError):
                LMSHelper.ensure_model_loaded_with_verification("test-model")
```

---

### Task 0.3: Add Retry Logic with Exponential Backoff

**Time**: 1-1.5 hours
**Severity**: 🔴 CRITICAL - Handles 90% of transient failures

#### Problem (from Qwen Review)

```python
# Current (BROKEN) - No retry logic
if LMSHelper.ensure_model_loaded(model_to_use):
    # Works once, fails on transient errors (network, memory pressure)
```

**Why This Fails**:
- 90% of model load failures are transient (per Qwen)
- Network latency, temporary resource constraints
- No recovery = 100% failure rate
- Production systems MUST retry

#### Solution

Already have `utils/error_handling.py` with `retry_with_backoff`, need to apply it:

```python
# utils/lms_helper.py

from utils.error_handling import retry_with_backoff

@classmethod
@retry_with_backoff(
    max_retries=3,
    base_delay=1.0,
    exceptions=(subprocess.TimeoutExpired, subprocess.CalledProcessError, ModelLoadError)
)
def ensure_model_loaded_with_verification(cls, model_name: str, ttl: Optional[int] = None) -> bool:
    """
    Ensure model loaded with automatic retry on transient failures.

    Retries up to 3 times with exponential backoff (1s, 2s, 4s).
    """
    # ... implementation from Task 0.2 ...
```

**Add Circuit Breaker** (prevent cascading failures):

```python
# utils/lms_helper.py

class LMSCircuitBreaker:
    """Circuit breaker for LMS CLI operations."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.circuit_open_time: Optional[float] = None

    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.is_open():
            if time.time() - self.circuit_open_time > self.recovery_timeout:
                logger.info("Circuit breaker: Attempting recovery")
                self.reset()
            else:
                raise CircuitBreakerOpen(
                    f"LMS CLI circuit breaker is open. "
                    f"Retry after {int(self.recovery_timeout - (time.time() - self.circuit_open_time))}s"
                )

        try:
            result = func(*args, **kwargs)
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise

    def is_open(self) -> bool:
        return self.circuit_open_time is not None

    def on_success(self):
        self.failure_count = 0

    def on_failure(self):
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            logger.error(f"Circuit breaker: OPEN after {self.failure_count} failures")
            self.circuit_open_time = time.time()

    def reset(self):
        self.failure_count = 0
        self.circuit_open_time = None


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open."""
    pass


# Add circuit breaker instance
_circuit_breaker = LMSCircuitBreaker()


@classmethod
def load_model(cls, model_name: str, keep_loaded: bool = True, ttl: Optional[int] = None) -> bool:
    """Load model with circuit breaker protection."""
    return _circuit_breaker.call(cls._load_model_impl, model_name, keep_loaded, ttl)
```

**Acceptance Criteria**:
- [ ] Retry logic applied to model loading
- [ ] Exponential backoff working (1s, 2s, 4s)
- [ ] Circuit breaker prevents cascading failures
- [ ] Clear logging of retry attempts
- [ ] Tests cover retry scenarios

**Testing**:
```python
def test_retry_succeeds_on_second_attempt():
    """Verify retry logic recovers from transient failure."""
    attempts = []

    def flaky_load(model_name):
        attempts.append(1)
        if len(attempts) < 2:
            raise subprocess.TimeoutExpired("lms", 5)
        return True

    with mock.patch('LMSHelper._load_model_impl', side_effect=flaky_load):
        result = LMSHelper.load_model("test-model")
        assert result is True
        assert len(attempts) == 2  # Failed once, succeeded second time

def test_circuit_breaker_opens_after_failures():
    """Verify circuit breaker opens after threshold failures."""
    for _ in range(5):  # Trigger 5 failures
        try:
            LMSHelper.load_model("failing-model")
        except:
            pass

    # Circuit should be open now
    with pytest.raises(CircuitBreakerOpen):
        LMSHelper.load_model("test-model")
```

---

### Phase 0 Completion Criteria

**All 3 tasks must be completed before proceeding to Phase 1**

- [ ] Task 0.1: TTL configuration fixed (all models have explicit TTL)
- [ ] Task 0.2: Health check verification added (catches false positives)
- [ ] Task 0.3: Retry logic + circuit breaker implemented
- [ ] All tests passing
- [ ] Qwen review approves fixes
- [ ] No regressions in existing tests

**Deliverables**:
- Updated `utils/lms_helper.py` with TTL fix, verification, retry, circuit breaker
- Updated `tools/autonomous.py` to use new verification method
- Updated `config.py` with TTL configuration
- New tests for retry logic and circuit breaker
- Updated documentation

---

## Phase 1: Production Hardening (5-6 hours) 🟠

**Priority**: HIGH - Must complete before multi-model support
**Owner**: Claude Code
**Reviewer**: Qwen 3
**Depends On**: Phase 0 complete

### Overview

Add missing failure testing, performance benchmarks, and observability that Qwen identified as critical gaps.

---

### Task 1.1: Add Failure Scenario Tests

**Time**: 2 hours
**Severity**: 🔴 CRITICAL - Zero failure tests currently

#### Missing Tests (from Qwen Review)

```python
# tests/test_failure_scenarios.py (NEW)

"""Failure scenario tests - CRITICAL for production."""

import pytest
import asyncio
from tools.autonomous import autonomous_filesystem_full
from llm.exceptions import ModelNotFoundError, LLMConnectionError
from utils.lms_helper import LMSHelper, ModelLoadError

class TestModelLoadingFailures:
    """Test model loading failure scenarios."""

    def test_model_not_loaded_returns_error(self):
        """Test system handles model not loaded gracefully."""
        # Unload all models first
        # ... implementation

    def test_model_unloads_during_execution(self):
        """Test recovery when model unloads mid-execution."""
        # Start execution, unload model after first call
        # Verify retry logic kicks in
        # ... implementation

    def test_lms_cli_not_installed(self):
        """Test graceful degradation when LMS CLI not available."""
        with mock.patch('LMSHelper.is_installed', return_value=False):
            # Should still work but with warnings
            # ... implementation

    def test_lms_cli_timeout(self):
        """Test handling of LMS CLI command timeout."""
        with mock.patch('subprocess.run', side_effect=subprocess.TimeoutExpired("lms", 5)):
            with pytest.raises(ModelLoadError):
                LMSHelper.load_model("test-model")

    def test_verification_failure_after_load(self):
        """Test when model reports loaded but verification fails."""
        # Mock: load succeeds, but verification shows not loaded
        # ... implementation

class TestConcurrentOperations:
    """Test concurrent operation scenarios."""

    @pytest.mark.asyncio
    async def test_concurrent_model_loading(self):
        """Test thread safety of concurrent model loading."""
        # Start 10 concurrent load operations
        tasks = [
            LMSHelper.ensure_model_loaded_with_verification("test-model")
            for _ in range(10)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Should not have race conditions
        assert all(r is True or isinstance(r, Exception) for r in results)

    @pytest.mark.asyncio
    async def test_concurrent_autonomous_executions(self):
        """Test multiple simultaneous autonomous executions."""
        tasks = [
            autonomous_filesystem_full(task=f"Task {i}", max_rounds=5)
            for i in range(5)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should complete without errors
        assert len(results) == 5

class TestResourceExhaustion:
    """Test resource exhaustion scenarios."""

    def test_memory_exhaustion_handling(self):
        """Test behavior when system runs out of memory."""
        # Mock OOM condition
        # Verify graceful failure
        # ... implementation

    def test_multiple_models_loaded(self):
        """Test system with many models loaded simultaneously."""
        # Load 10 models
        # Verify TTLs prevent memory issues
        # ... implementation

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_invalid_model_name_formats(self):
        """Test various invalid model name formats."""
        invalid_names = [
            "",
            "   ",
            "model/with/too/many/slashes",
            "model@invalid",
            "../../../etc/passwd"
        ]

        for name in invalid_names:
            with pytest.raises((ModelNotFoundError, ValueError)):
                # ... test each invalid name

    def test_model_name_too_long(self):
        """Test extremely long model names."""
        long_name = "a" * 10000
        with pytest.raises((ModelNotFoundError, ValueError)):
            LMSHelper.load_model(long_name)

    def test_rapid_load_unload_cycles(self):
        """Test rapid loading and unloading."""
        # Load and unload 100 times rapidly
        # Verify no resource leaks
        # ... implementation
```

**Acceptance Criteria**:
- [ ] 20+ failure scenario tests added
- [ ] All tests pass
- [ ] Coverage for model loading failures
- [ ] Coverage for concurrent operations
- [ ] Coverage for resource exhaustion
- [ ] Coverage for edge cases
- [ ] Test coverage > 95%

---

### Task 1.2: Add Performance Benchmarks

**Time**: 1.5 hours
**Severity**: 🟠 HIGH - Cannot validate production SLAs

#### Missing Benchmarks (from Qwen Review)

```python
# tests/benchmark_production_performance.py (NEW)

"""Production performance benchmarks."""

import time
import asyncio
import pytest
from tools.autonomous import autonomous_filesystem_full
from utils.lms_helper import LMSHelper

class PerformanceBenchmarks:
    """Production performance benchmarks."""

    def benchmark_model_load_time(self):
        """Measure model loading time."""
        model_name = "qwen/qwen3-4b-thinking-2507"

        # Cold start (model not loaded)
        LMSHelper.unload_model(model_name)
        start = time.perf_counter()
        LMSHelper.ensure_model_loaded_with_verification(model_name)
        cold_start_time = time.perf_counter() - start

        # Warm start (model already loaded)
        start = time.perf_counter()
        LMSHelper.ensure_model_loaded_with_verification(model_name)
        warm_start_time = time.perf_counter() - start

        print(f"\nModel Load Performance:")
        print(f"  Cold start: {cold_start_time:.2f}s")
        print(f"  Warm start: {warm_start_time:.4f}s")

        # Acceptance criteria
        assert cold_start_time < 10.0  # < 10s for cold start
        assert warm_start_time < 0.1   # < 100ms for warm start

    def benchmark_verification_overhead(self):
        """Measure model verification overhead."""
        model_name = "qwen/qwen3-4b-thinking-2507"
        LMSHelper.ensure_model_loaded_with_verification(model_name)

        # Benchmark 100 verifications
        start = time.perf_counter()
        for _ in range(100):
            LMSHelper.verify_model_loaded(model_name)
        end = time.perf_counter()

        avg_time = (end - start) / 100 * 1000  # ms

        print(f"\nVerification Performance:")
        print(f"  Average: {avg_time:.4f}ms")

        # Acceptance: < 1ms per verification
        assert avg_time < 1.0

    @pytest.mark.asyncio
    async def benchmark_autonomous_execution_latency(self):
        """Measure end-to-end autonomous execution latency."""
        tasks = [
            ("Count to 5", 10),
            ("What is 2+2?", 5),
            ("List current directory", 15)
        ]

        for task_desc, max_rounds in tasks:
            start = time.perf_counter()
            result = await autonomous_filesystem_full(
                task=task_desc,
                max_rounds=max_rounds
            )
            latency = time.perf_counter() - start

            print(f"\nTask: {task_desc}")
            print(f"  Latency: {latency:.2f}s")
            print(f"  Result length: {len(result)} chars")

            # Acceptance: P95 < 30s for simple tasks
            assert latency < 30.0

    @pytest.mark.asyncio
    async def benchmark_throughput(self):
        """Measure request throughput."""
        num_requests = 10
        task = "Count to 3"

        start = time.perf_counter()
        tasks = [
            autonomous_filesystem_full(task=task, max_rounds=5)
            for _ in range(num_requests)
        ]
        await asyncio.gather(*tasks)
        total_time = time.perf_counter() - start

        throughput = num_requests / total_time

        print(f"\nThroughput Benchmark:")
        print(f"  Requests: {num_requests}")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Throughput: {throughput:.2f} req/s")

        # Acceptance: > 0.5 req/s
        assert throughput > 0.5

    def benchmark_memory_usage(self):
        """Measure memory usage under load."""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Load 3 models
        models = ["model1", "model2", "model3"]
        for model in models:
            LMSHelper.load_model(model, ttl=600)

        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = peak_memory - initial_memory

        print(f"\nMemory Usage:")
        print(f"  Initial: {initial_memory:.2f} MB")
        print(f"  Peak: {peak_memory:.2f} MB")
        print(f"  Increase: {memory_increase:.2f} MB")

        # Acceptance: < 500MB increase for 3 models
        assert memory_increase < 500.0
```

**Acceptance Criteria**:
- [ ] Performance benchmarks added
- [ ] Latency benchmarks (P50, P95, P99)
- [ ] Throughput benchmarks
- [ ] Memory usage benchmarks
- [ ] All benchmarks pass acceptance criteria
- [ ] Results documented

---

### Task 1.3: Add Structured Logging & Metrics

**Time**: 1.5-2 hours
**Severity**: 🟠 HIGH - Essential for production debugging

#### Solution

```python
# utils/observability.py (NEW)

"""Production observability - structured logging and metrics."""

from loguru import logger
import sys
from typing import Dict, Any
from prometheus_client import Counter, Histogram, Gauge
import time

# Configure structured logging
logger.remove()  # Remove default handler
logger.add(
    sys.stderr,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
    level="INFO"
)
logger.add(
    "logs/lmstudio_bridge_{time:YYYY-MM-DD}.log",
    rotation="500 MB",
    retention="30 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {extra} | {message}",
    serialize=True  # JSON format for parsing
)

# Prometheus metrics
model_load_attempts = Counter(
    'model_load_attempts_total',
    'Total model load attempts',
    ['model_name', 'result']
)

model_load_duration = Histogram(
    'model_load_duration_seconds',
    'Model loading duration',
    ['model_name']
)

model_verification_failures = Counter(
    'model_verification_failures_total',
    'Model verification failures',
    ['model_name', 'reason']
)

active_models = Gauge(
    'active_models_count',
    'Number of currently loaded models'
)

autonomous_execution_duration = Histogram(
    'autonomous_execution_duration_seconds',
    'Autonomous execution duration',
    ['mcp_name', 'success']
)

retry_attempts = Counter(
    'retry_attempts_total',
    'Retry attempts',
    ['operation', 'attempt_number']
)


def log_with_context(level: str, message: str, **context):
    """Log with structured context."""
    logger.bind(**context).log(level, message)


class MetricsCollector:
    """Collect and export metrics."""

    @staticmethod
    def record_model_load(model_name: str, success: bool, duration: float):
        """Record model load metrics."""
        result = "success" if success else "failure"
        model_load_attempts.labels(model_name=model_name, result=result).inc()
        if success:
            model_load_duration.labels(model_name=model_name).observe(duration)

    @staticmethod
    def record_verification_failure(model_name: str, reason: str):
        """Record model verification failure."""
        model_verification_failures.labels(
            model_name=model_name,
            reason=reason
        ).inc()

    @staticmethod
    def update_active_models(count: int):
        """Update active models gauge."""
        active_models.set(count)

    @staticmethod
    def record_autonomous_execution(mcp_name: str, success: bool, duration: float):
        """Record autonomous execution metrics."""
        autonomous_execution_duration.labels(
            mcp_name=mcp_name,
            success=str(success)
        ).observe(duration)
```

**Update LMS Helper** to use observability:

```python
# utils/lms_helper.py

from utils.observability import log_with_context, MetricsCollector

@classmethod
def load_model(cls, model_name: str, keep_loaded: bool = True, ttl: Optional[int] = None) -> bool:
    """Load model with metrics and structured logging."""
    start_time = time.perf_counter()

    log_with_context(
        "INFO",
        "Loading model",
        model_name=model_name,
        keep_loaded=keep_loaded,
        ttl=ttl,
        operation="model_load"
    )

    try:
        # ... existing implementation ...

        duration = time.perf_counter() - start_time
        MetricsCollector.record_model_load(model_name, success=True, duration=duration)

        log_with_context(
            "INFO",
            "Model loaded successfully",
            model_name=model_name,
            duration_seconds=duration,
            operation="model_load"
        )

        return True

    except Exception as e:
        duration = time.perf_counter() - start_time
        MetricsCollector.record_model_load(model_name, success=False, duration=duration)

        log_with_context(
            "ERROR",
            "Model load failed",
            model_name=model_name,
            error=str(e),
            duration_seconds=duration,
            operation="model_load"
        )

        raise
```

**Acceptance Criteria**:
- [ ] Structured logging implemented
- [ ] Prometheus metrics exposed
- [ ] All operations logged with context
- [ ] Metrics dashboard created (Grafana)
- [ ] Log aggregation working (ELK/Splunk)

---

### Phase 1 Completion Criteria

- [ ] Task 1.1: 20+ failure scenario tests added and passing
- [ ] Task 1.2: Performance benchmarks created and passing
- [ ] Task 1.3: Structured logging and metrics implemented
- [ ] Test coverage > 95%
- [ ] All benchmarks meet acceptance criteria
- [ ] Metrics visible in monitoring system
- [ ] Qwen review approves hardening

**Deliverables**:
- `tests/test_failure_scenarios.py` (NEW)
- `tests/benchmark_production_performance.py` (NEW)
- `utils/observability.py` (NEW)
- Updated `utils/lms_helper.py` with metrics
- Grafana dashboard JSON
- Documentation for monitoring

---

## Phase 2-4: Multi-Model Support

**Note**: These phases remain largely unchanged from original Option A plan, but now execute AFTER critical fixes.

**Timeline**: 9-11 hours (Phases 2-4 combined)

See original OPTION_A_DETAILED_PLAN.md for detailed tasks in:
- Phase 2: Model Validation Layer (2-2.5h)
- Phase 3: Core Tool Interface Updates (3-3.5h)
- Phase 4: Documentation & Testing (3-4h)

**Key Change**: All multi-model code must use the production-hardened infrastructure from Phases 0-1.

---

## Updated Timeline Summary

| Phase | Description | Duration | Dependencies |
|-------|-------------|----------|--------------|
| **Phase 0** | Critical Production Fixes | 3-4 hours | None (START HERE) |
| **Phase 1** | Production Hardening | 5-6 hours | Phase 0 complete |
| **Phase 2** | Model Validation Layer | 2-2.5 hours | Phase 1 complete |
| **Phase 3** | Core Tool Interface | 3-3.5 hours | Phase 2 complete |
| **Phase 4** | Documentation & Testing | 3-4 hours | Phase 3 complete |
| **TOTAL** | **18-22 hours** | **(was 8-10h)** | |

---

## Success Criteria (Updated)

### Phase 0 Success (MUST ACHIEVE)
- [ ] All models have explicit TTL (no infinite loading)
- [ ] Health check verification catches false positives
- [ ] Retry logic handles transient failures
- [ ] Circuit breaker prevents cascading failures
- [ ] Qwen rating improves from 6/10 to 8/10

### Phase 1 Success (MUST ACHIEVE)
- [ ] 20+ failure scenario tests passing
- [ ] Performance benchmarks meet SLAs
- [ ] Structured logging and metrics working
- [ ] Test coverage > 95%
- [ ] Qwen rating improves to 9/10

### Phases 2-4 Success (Original Goals)
- [ ] Multi-model support working
- [ ] Backward compatible
- [ ] Documentation complete
- [ ] Production ready
- [ ] Qwen rating 9-10/10

---

## Risk Mitigation (Updated)

### Risk 1: Timeline Doubled (8h → 18h)
**Mitigation**: Critical fixes are non-negotiable for production
**Justification**: Qwen identified production-blocking issues

### Risk 2: Breaking Changes from Fixes
**Mitigation**: Comprehensive test suite catches regressions
**Validation**: Run existing tests after each phase

### Risk 3: Qwen Recommendations Too Strict
**Mitigation**: Prioritize by severity (Critical → High → Medium)
**Reality Check**: 6/10 rating confirms issues are real

---

## Next Steps

1. **STOP** any work on multi-model support
2. **START** Phase 0 immediately (TTL fix, health checks, retry logic)
3. **VALIDATE** Qwen approves Phase 0 before Phase 1
4. **CONTINUE** to Phases 1-4 only after production hardening complete

---

**Plan Version**: 2.0 (Post-Qwen Review)
**Created**: October 30, 2025
**Authors**: Claude Code (based on Qwen 3 critical review)
**Status**: Ready for Implementation (Phase 0 first!)
**Target Release**: v2.1.0 (production-hardened + multi-model)
