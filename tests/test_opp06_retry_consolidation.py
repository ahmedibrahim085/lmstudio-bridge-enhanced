"""OPP-06: Verify retry module hierarchy after consolidation."""
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import utils.retry_logic as rl
from utils.error_handling import retry_with_backoff
from utils.retry import run_with_retry


class TestRetryHierarchy:
    """Verify the retry module consolidation."""

    def test_retry_logic_exports_backoff_from_error_handling(self):
        """retry_logic.retry_with_exponential_backoff should BE error_handling.retry_with_backoff."""
        assert rl.retry_with_exponential_backoff is retry_with_backoff

    def test_retry_logic_no_global_circuit_breaker(self):
        """Dead global instance lms_circuit_breaker should be removed."""
        assert not hasattr(rl, "lms_circuit_breaker")

    def test_retry_logic_circuit_breaker_class_exists(self):
        """LMSCircuitBreaker class still importable for tests."""
        cb = rl.LMSCircuitBreaker(failure_threshold=3, recovery_timeout=1)
        assert cb.state == "CLOSED"

    def test_retry_logic_circuit_breaker_open_error_exists(self):
        """CircuitBreakerOpenError still importable."""
        assert issubclass(rl.CircuitBreakerOpenError, Exception)

    def test_retry_py_run_with_retry_exists(self):
        """utils.retry.run_with_retry unchanged and accessible."""
        assert callable(run_with_retry)

    def test_error_handling_retry_with_backoff_exists(self):
        """utils.error_handling.retry_with_backoff unchanged and accessible."""
        assert callable(retry_with_backoff)

    def test_retry_logic_has_deprecation_notice(self):
        """Module docstring mentions deprecation."""
        assert rl.__doc__ is not None
        doc_lower = rl.__doc__.lower()
        assert "deprecat" in doc_lower, f"Module docstring should mention deprecation: {rl.__doc__[:200]}"

    def test_circuit_breaker_state_transitions(self):
        """Full state machine: CLOSED -> OPEN -> HALF_OPEN -> CLOSED."""
        cb = rl.LMSCircuitBreaker(failure_threshold=3, recovery_timeout=0.1)

        # CLOSED -> OPEN after 3 failures
        assert cb.state == "CLOSED"
        for _ in range(3):
            cb.on_failure()
        assert cb.state == "OPEN"

        # OPEN -> raises error
        with pytest.raises(rl.CircuitBreakerOpenError):
            cb.call(lambda: None)

        # Wait for recovery timeout
        time.sleep(0.15)

        # OPEN -> HALF_OPEN on next call attempt
        # Successful call transitions to CLOSED
        result = cb.call(lambda: "ok")
        assert result == "ok"
        assert cb.state == "CLOSED"
