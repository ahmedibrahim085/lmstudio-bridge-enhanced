#!/usr/bin/env python3
"""
Retry Logic and Circuit Breaker for LM Studio Operations.

Provides production-hardened error handling with exponential backoff
and circuit breaker pattern to prevent cascading failures.
"""

import time
import logging
from typing import Callable, Any, Optional
from functools import wraps

logger = logging.getLogger(__name__)


def retry_with_exponential_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0
):
    """
    Decorator that retries a function with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds

    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if attempt == max_retries - 1:
                        logger.error(
                            f"Max retries ({max_retries}) reached for {func.__name__}: {e}"
                        )
                        raise

                    # Calculate exponential backoff delay
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries} failed for {func.__name__}, "
                        f"retrying in {delay}s: {e}"
                    )
                    time.sleep(delay)

            # This should never be reached, but just in case
            raise last_exception

        return wrapper
    return decorator


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

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
        """
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.circuit_open_time: Optional[float] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def is_open(self) -> bool:
        """Check if circuit is open."""
        return self.state == "OPEN"

    def reset(self):
        """Reset circuit breaker to closed state."""
        self.failure_count = 0
        self.circuit_open_time = None
        self.state = "CLOSED"
        logger.info("Circuit breaker: Reset to CLOSED state")

    def on_success(self):
        """Record successful operation."""
        if self.state == "HALF_OPEN":
            logger.info("Circuit breaker: Recovery successful, closing circuit")
            self.reset()
        elif self.failure_count > 0:
            self.failure_count = 0
            logger.debug("Circuit breaker: Failure count reset after success")

    def on_failure(self):
        """Record failed operation."""
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
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result from func

        Raises:
            CircuitBreakerOpen: If circuit is open
            Exception: Original exception from func if circuit allows
        """
        # Check if circuit is open
        if self.is_open():
            # Check if recovery timeout has passed
            if time.time() - self.circuit_open_time > self.recovery_timeout:
                logger.info("Circuit breaker: Attempting recovery (HALF_OPEN)")
                self.state = "HALF_OPEN"
            else:
                time_remaining = int(
                    self.recovery_timeout - (time.time() - self.circuit_open_time)
                )
                raise CircuitBreakerOpenError(
                    f"LMS CLI circuit breaker is open. "
                    f"Retry after {time_remaining}s"
                )

        # Try to execute function
        try:
            result = func(*args, **kwargs)
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


# Global circuit breaker instance for LMS operations
lms_circuit_breaker = LMSCircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60
)
