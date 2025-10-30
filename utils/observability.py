#!/usr/bin/env python3
"""
Observability Module for LM Studio Bridge Enhanced.

Provides structured logging, metrics collection, and monitoring
for production deployments.
"""

import logging
import time
from typing import Optional, Dict, Any
from functools import wraps
from datetime import datetime

# Try to import prometheus_client, but make it optional
try:
    from prometheus_client import Counter, Histogram, Gauge, Summary
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    # Provide stub classes if prometheus not available
    class Counter:
        def __init__(self, *args, **kwargs):
            pass
        def labels(self, **kwargs):
            return self
        def inc(self, amount=1):
            pass

    class Histogram:
        def __init__(self, *args, **kwargs):
            pass
        def labels(self, **kwargs):
            return self
        def observe(self, amount):
            pass

    class Gauge:
        def __init__(self, *args, **kwargs):
            pass
        def labels(self, **kwargs):
            return self
        def set(self, value):
            pass

    class Summary:
        def __init__(self, *args, **kwargs):
            pass
        def labels(self, **kwargs):
            return self
        def observe(self, amount):
            pass


# Configure structured logging
logger = logging.getLogger(__name__)


# Prometheus Metrics (optional)
model_load_attempts = Counter(
    'lms_model_load_attempts_total',
    'Total model load attempts',
    ['model_name', 'result']
)

model_load_duration = Histogram(
    'lms_model_load_duration_seconds',
    'Model loading duration',
    ['model_name'],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0)
)

model_verification_attempts = Counter(
    'lms_model_verification_attempts_total',
    'Total model verification attempts',
    ['model_name', 'result']
)

model_verification_duration = Histogram(
    'lms_model_verification_duration_seconds',
    'Model verification duration',
    ['model_name'],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0)
)

active_models = Gauge(
    'lms_active_models',
    'Number of currently loaded models'
)

circuit_breaker_state = Gauge(
    'lms_circuit_breaker_state',
    'Circuit breaker state (0=closed, 1=open, 2=half_open)',
    ['operation']
)

autonomous_task_duration = Histogram(
    'lms_autonomous_task_duration_seconds',
    'Autonomous task execution duration',
    ['mcp_name', 'result'],
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 300.0, 600.0)
)

autonomous_task_rounds = Histogram(
    'lms_autonomous_task_rounds',
    'Number of rounds in autonomous tasks',
    ['mcp_name'],
    buckets=(1, 5, 10, 20, 50, 100, 500, 1000)
)


class MetricsCollector:
    """Collect and export metrics for monitoring."""

    @staticmethod
    def record_model_load(model_name: str, success: bool, duration: float):
        """
        Record model load metrics.

        Args:
            model_name: Name of the model
            success: Whether load succeeded
            duration: Load duration in seconds
        """
        result = "success" if success else "failure"
        model_load_attempts.labels(model_name=model_name, result=result).inc()
        if success:
            model_load_duration.labels(model_name=model_name).observe(duration)

        logger.info(
            "model_load",
            extra={
                "model_name": model_name,
                "success": success,
                "duration_seconds": duration,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    @staticmethod
    def record_model_verification(model_name: str, success: bool, duration: float):
        """
        Record model verification metrics.

        Args:
            model_name: Name of the model
            success: Whether verification succeeded
            duration: Verification duration in seconds
        """
        result = "success" if success else "failure"
        model_verification_attempts.labels(model_name=model_name, result=result).inc()
        model_verification_duration.labels(model_name=model_name).observe(duration)

        logger.debug(
            "model_verification",
            extra={
                "model_name": model_name,
                "success": success,
                "duration_seconds": duration,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    @staticmethod
    def set_active_models(count: int):
        """
        Set the number of active models.

        Args:
            count: Number of currently loaded models
        """
        active_models.set(count)

        logger.info(
            "active_models_updated",
            extra={
                "count": count,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    @staticmethod
    def record_circuit_breaker_state(operation: str, state: str):
        """
        Record circuit breaker state change.

        Args:
            operation: Operation name (e.g., 'model_load')
            state: State (CLOSED=0, OPEN=1, HALF_OPEN=2)
        """
        state_map = {"CLOSED": 0, "OPEN": 1, "HALF_OPEN": 2}
        state_value = state_map.get(state, 0)
        circuit_breaker_state.labels(operation=operation).set(state_value)

        logger.warning(
            "circuit_breaker_state_change",
            extra={
                "operation": operation,
                "state": state,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    @staticmethod
    def record_autonomous_task(
        mcp_name: str,
        success: bool,
        duration: float,
        rounds: int
    ):
        """
        Record autonomous task execution metrics.

        Args:
            mcp_name: Name of the MCP used
            success: Whether task succeeded
            duration: Task duration in seconds
            rounds: Number of rounds executed
        """
        result = "success" if success else "failure"
        autonomous_task_duration.labels(mcp_name=mcp_name, result=result).observe(duration)
        autonomous_task_rounds.labels(mcp_name=mcp_name).observe(rounds)

        logger.info(
            "autonomous_task_completed",
            extra={
                "mcp_name": mcp_name,
                "success": success,
                "duration_seconds": duration,
                "rounds": rounds,
                "timestamp": datetime.utcnow().isoformat()
            }
        )


def track_performance(operation_name: str):
    """
    Decorator to track performance of functions.

    Args:
        operation_name: Name of the operation for logging

    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            success = False
            error = None

            try:
                result = func(*args, **kwargs)
                success = True
                return result
            except Exception as e:
                error = e
                raise
            finally:
                duration = time.time() - start_time
                logger.info(
                    f"{operation_name}_performance",
                    extra={
                        "operation": operation_name,
                        "duration_seconds": duration,
                        "success": success,
                        "error": str(error) if error else None,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )

        return wrapper
    return decorator


class StructuredLogger:
    """
    Structured logging helper for consistent log format.

    Provides methods for logging with structured context.
    """

    def __init__(self, name: str):
        """
        Initialize structured logger.

        Args:
            name: Logger name (usually module name)
        """
        self.logger = logging.getLogger(name)

    def log_model_operation(
        self,
        operation: str,
        model_name: str,
        success: bool,
        duration: Optional[float] = None,
        error: Optional[str] = None,
        **kwargs
    ):
        """
        Log model operation with structured context.

        Args:
            operation: Operation type (load, unload, verify)
            model_name: Model name
            success: Whether operation succeeded
            duration: Operation duration in seconds
            error: Error message if failed
            **kwargs: Additional context
        """
        level = logging.INFO if success else logging.ERROR

        self.logger.log(
            level,
            f"Model operation: {operation}",
            extra={
                "operation": operation,
                "model_name": model_name,
                "success": success,
                "duration_seconds": duration,
                "error": error,
                "timestamp": datetime.utcnow().isoformat(),
                **kwargs
            }
        )

    def log_autonomous_task(
        self,
        mcp_name: str,
        task: str,
        round_num: int,
        total_rounds: int,
        action: str,
        **kwargs
    ):
        """
        Log autonomous task execution step.

        Args:
            mcp_name: MCP name
            task: Task description
            round_num: Current round number
            total_rounds: Total rounds
            action: Action taken in this round
            **kwargs: Additional context
        """
        self.logger.info(
            f"Autonomous task round {round_num}/{total_rounds}",
            extra={
                "mcp_name": mcp_name,
                "task": task,
                "round": round_num,
                "total_rounds": total_rounds,
                "action": action,
                "timestamp": datetime.utcnow().isoformat(),
                **kwargs
            }
        )

    def log_error(
        self,
        error_type: str,
        error_message: str,
        **kwargs
    ):
        """
        Log error with structured context.

        Args:
            error_type: Type of error
            error_message: Error message
            **kwargs: Additional context
        """
        self.logger.error(
            f"Error: {error_type}",
            extra={
                "error_type": error_type,
                "error_message": error_message,
                "timestamp": datetime.utcnow().isoformat(),
                **kwargs
            }
        )


# Global metrics collector instance
metrics = MetricsCollector()


def setup_observability(enable_prometheus: bool = True):
    """
    Setup observability infrastructure.

    Args:
        enable_prometheus: Whether to enable Prometheus metrics export
    """
    # Configure structured logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    if enable_prometheus and PROMETHEUS_AVAILABLE:
        logger.info("Prometheus metrics enabled")
    elif enable_prometheus and not PROMETHEUS_AVAILABLE:
        logger.warning(
            "Prometheus metrics requested but prometheus_client not installed. "
            "Install with: pip install prometheus-client"
        )
    else:
        logger.info("Prometheus metrics disabled")

    logger.info("Observability setup complete")


# Example usage
if __name__ == "__main__":
    setup_observability()

    # Example: Record model load
    metrics.record_model_load("test-model", success=True, duration=2.5)

    # Example: Track function performance
    @track_performance("test_operation")
    def test_function():
        time.sleep(0.1)
        return "success"

    result = test_function()
    print(f"Result: {result}")

    # Example: Structured logging
    struct_logger = StructuredLogger(__name__)
    struct_logger.log_model_operation(
        operation="load",
        model_name="test-model",
        success=True,
        duration=2.5
    )
