"""Tests for error handling utilities.

This module tests the retry and fallback decorators in utils/error_handling.py.
"""

import pytest
import asyncio
from utils.error_handling import retry_with_backoff, fallback_strategy, log_errors


# Test fixtures and helpers

class TestException(Exception):
    """Custom exception for testing."""
    pass


@pytest.mark.asyncio
async def test_retry_success_on_first_attempt():
    """Should succeed on first attempt without retries."""
    attempts = []

    @retry_with_backoff(max_retries=3, base_delay=0.01)
    async def successful_function():
        attempts.append(1)
        return "success"

    result = await successful_function()

    assert result == "success"
    assert len(attempts) == 1


@pytest.mark.asyncio
async def test_retry_success_on_second_attempt():
    """Should retry and succeed on second attempt."""
    attempts = []

    @retry_with_backoff(max_retries=3, base_delay=0.01)
    async def flaky_function():
        attempts.append(1)
        if len(attempts) < 2:
            raise TestException("Temporary error")
        return "success"

    result = await flaky_function()

    assert result == "success"
    assert len(attempts) == 2


@pytest.mark.asyncio
async def test_retry_fails_after_max_attempts():
    """Should fail after maximum retries."""
    attempts = []

    @retry_with_backoff(max_retries=3, base_delay=0.01)
    async def always_failing_function():
        attempts.append(1)
        raise TestException("Persistent error")

    with pytest.raises(TestException):
        await always_failing_function()

    assert len(attempts) == 3


@pytest.mark.asyncio
async def test_retry_exponential_backoff():
    """Should use exponential backoff between retries."""
    import time
    timestamps = []

    @retry_with_backoff(max_retries=3, base_delay=0.1, max_delay=1.0)
    async def failing_function():
        timestamps.append(time.time())
        raise TestException("Error")

    try:
        await failing_function()
    except TestException:
        pass

    # Check that delays increase exponentially
    assert len(timestamps) == 3

    # Delay between 1st and 2nd attempt should be ~0.1s
    delay1 = timestamps[1] - timestamps[0]
    assert 0.08 < delay1 < 0.15

    # Delay between 2nd and 3rd attempt should be ~0.2s
    delay2 = timestamps[2] - timestamps[1]
    assert 0.18 < delay2 < 0.25


@pytest.mark.asyncio
async def test_retry_only_catches_specified_exceptions():
    """Should only retry on specified exception types."""
    attempts = []

    @retry_with_backoff(max_retries=3, base_delay=0.01, exceptions=(TestException,))
    async def selective_function():
        attempts.append(1)
        if len(attempts) < 2:
            raise TestException("This will be retried")
        raise ValueError("This will not be retried")

    with pytest.raises(ValueError):
        await selective_function()

    assert len(attempts) == 2


def test_retry_sync_function():
    """Should work with synchronous functions."""
    attempts = []

    @retry_with_backoff(max_retries=3, base_delay=0.01)
    def sync_flaky_function():
        attempts.append(1)
        if len(attempts) < 2:
            raise TestException("Temporary error")
        return "success"

    result = sync_flaky_function()

    assert result == "success"
    assert len(attempts) == 2


@pytest.mark.asyncio
async def test_fallback_on_failure():
    """Should call fallback function on failure."""
    async def main_function():
        raise TestException("Main function failed")

    async def fallback_function():
        return "fallback result"

    @fallback_strategy(fallback_function)
    async def decorated_function():
        return await main_function()

    result = await decorated_function()

    assert result == "fallback result"


@pytest.mark.asyncio
async def test_fallback_not_called_on_success():
    """Should not call fallback if main function succeeds."""
    fallback_called = []

    async def main_function():
        return "main result"

    async def fallback_function():
        fallback_called.append(1)
        return "fallback result"

    @fallback_strategy(fallback_function)
    async def decorated_function():
        return await main_function()

    result = await decorated_function()

    assert result == "main result"
    assert len(fallback_called) == 0


@pytest.mark.asyncio
async def test_fallback_with_arguments():
    """Should pass arguments to fallback function."""
    async def fallback_with_args(arg1, arg2, kwarg1=None):
        return f"{arg1}-{arg2}-{kwarg1}"

    @fallback_strategy(
        fallback_with_args,
        fallback_args=("a", "b"),
        fallback_kwargs={"kwarg1": "c"}
    )
    async def decorated_function():
        raise TestException("Fail")

    result = await decorated_function()

    assert result == "a-b-c"


def test_fallback_sync_function():
    """Should work with synchronous functions."""
    def main_function():
        raise TestException("Failed")

    def fallback_function():
        return "fallback result"

    @fallback_strategy(fallback_function)
    def decorated_function():
        return main_function()

    result = decorated_function()

    assert result == "fallback result"


@pytest.mark.asyncio
async def test_log_errors_async():
    """Should log errors before re-raising (async)."""
    @log_errors
    async def failing_function():
        raise TestException("Test error")

    with pytest.raises(TestException):
        await failing_function()


def test_log_errors_sync():
    """Should log errors before re-raising (sync)."""
    @log_errors
    def failing_function():
        raise TestException("Test error")

    with pytest.raises(TestException):
        failing_function()


@pytest.mark.asyncio
async def test_combined_decorators():
    """Should work with multiple decorators combined."""
    attempts = []

    async def fallback_function():
        return "fallback"

    @fallback_strategy(fallback_function)
    @retry_with_backoff(max_retries=2, base_delay=0.01)
    async def decorated_function():
        attempts.append(1)
        raise TestException("Always fails")

    result = await decorated_function()

    # Retry decorator tries twice, then fallback is used
    assert result == "fallback"
    assert len(attempts) == 2


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
