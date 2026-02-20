#!/usr/bin/env python3
"""
DEPRECATION SHIM -- Retry Logic and Circuit Breaker.

This module is deprecated. The retry decorator has been consolidated:

  - For async/sync retry decorator: use ``utils.error_handling.retry_with_backoff``
  - For subprocess retry: use ``utils.retry.run_with_retry``

The ``retry_with_exponential_backoff`` name is kept here as a backward-compatible
alias that delegates to ``utils.error_handling.retry_with_backoff``.

The ``LMSCircuitBreaker`` class remains here because it is self-contained
and tested independently.
"""

import logging
import time
from typing import Any, Callable

from utils.error_handling import retry_with_backoff

logger = logging.getLogger(__name__)

# Backward-compatible alias -- delegates to the canonical implementation
retry_with_exponential_backoff = retry_with_backoff


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


class LMSCircuitBreaker:
    """
    Circuit breaker for LMS CLI operations.

    Prevents cascading failures by opening the circuit after repeated failures
    and closing it after a recovery timeout.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests fail fast
    - HALF_OPEN: Testing if service recovered
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.circuit_open_time: float = 0.0
        self.state = "CLOSED"

    def is_open(self) -> bool:
        return self.state == "OPEN"

    def reset(self):
        self.failure_count = 0
        self.circuit_open_time = 0.0
        self.state = "CLOSED"
        logger.info("Circuit breaker: Reset to CLOSED state")

    def on_success(self):
        if self.state == "HALF_OPEN":
            logger.info("Circuit breaker: Recovery successful, closing circuit")
            self.reset()
        elif self.failure_count > 0:
            self.failure_count = 0
            logger.debug("Circuit breaker: Failure count reset after success")

    def on_failure(self):
        self.failure_count += 1
        logger.warning(
            f"Circuit breaker: Failure {self.failure_count}/{self.failure_threshold}"
        )
        if self.failure_count >= self.failure_threshold and self.state == "CLOSED":
            self.state = "OPEN"
            self.circuit_open_time = time.time()
            logger.error(
                f"Circuit breaker: OPENED after {self.failure_count} failures. "
                f"Will attempt recovery after {self.recovery_timeout}s"
            )

    def call(self, func: Callable, *args, **kwargs) -> Any:
        if self.is_open():
            if time.time() - self.circuit_open_time > self.recovery_timeout:
                logger.info("Circuit breaker: Attempting recovery (HALF_OPEN)")
                self.state = "HALF_OPEN"
            else:
                time_remaining = int(
                    self.recovery_timeout - (time.time() - self.circuit_open_time)
                )
                raise CircuitBreakerOpenError(
                    f"LMS CLI circuit breaker is open. Retry after {time_remaining}s"
                )

        try:
            result = func(*args, **kwargs)
            self.on_success()
            return result
        except Exception:
            self.on_failure()
            raise


__all__ = [
    "retry_with_exponential_backoff",
    "LMSCircuitBreaker",
    "CircuitBreakerOpenError",
]
