"""Error handling utilities for LLM operations.

This module provides decorators and utilities for handling errors in
asynchronous LLM operations, including:
- Automatic retry with exponential backoff
- Fallback strategies when operations fail
- Graceful error recovery

These utilities help make the system more resilient to transient failures.
"""

import time
import asyncio
from functools import wraps
from typing import Callable, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: Tuple[type, ...] = (Exception,)
):
    """Decorator that retries a function with exponential backoff.

    This decorator will automatically retry a function if it raises one of
    the specified exceptions. The delay between retries grows exponentially
    to avoid overwhelming the system.

    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Initial delay in seconds (default: 1.0)
        max_delay: Maximum delay in seconds (default: 60.0)
        exceptions: Tuple of exception types to catch and retry (default: Exception)

    Returns:
        Decorated function with retry logic

    Example:
        @retry_with_backoff(max_retries=3, base_delay=1.0)
        async def fetch_model_list():
            # This will retry up to 3 times if it fails
            response = await client.get("/v1/models")
            return response.json()
    """
    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            # Async version
            @wraps(func)
            async def async_wrapper(*args, **kwargs) -> Any:
                last_exception = None

                for attempt in range(max_retries):
                    try:
                        return await func(*args, **kwargs)

                    except exceptions as e:
                        last_exception = e

                        # If this was the last attempt, raise the exception
                        if attempt == max_retries - 1:
                            logger.error(
                                f"Max retries ({max_retries}) reached for {func.__name__}. "
                                f"Last error: {e}"
                            )
                            raise

                        # Calculate delay with exponential backoff
                        delay = min(base_delay * (2 ** attempt), max_delay)

                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries} failed for {func.__name__}: {e}. "
                            f"Retrying in {delay:.2f}s..."
                        )

                        await asyncio.sleep(delay)

            return async_wrapper

        else:
            # Sync version
            @wraps(func)
            def sync_wrapper(*args, **kwargs) -> Any:
                last_exception = None

                for attempt in range(max_retries):
                    try:
                        return func(*args, **kwargs)

                    except exceptions as e:
                        last_exception = e

                        # If this was the last attempt, raise the exception
                        if attempt == max_retries - 1:
                            logger.error(
                                f"Max retries ({max_retries}) reached for {func.__name__}. "
                                f"Last error: {e}"
                            )
                            raise

                        # Calculate delay with exponential backoff
                        delay = min(base_delay * (2 ** attempt), max_delay)

                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries} failed for {func.__name__}: {e}. "
                            f"Retrying in {delay:.2f}s..."
                        )

                        time.sleep(delay)

            return sync_wrapper

    return decorator


def fallback_strategy(
    fallback_func: Callable,
    fallback_args: Optional[tuple] = None,
    fallback_kwargs: Optional[dict] = None
):
    """Decorator that provides a fallback function when the main function fails.

    If the decorated function raises an exception, the fallback function will
    be called instead. This is useful for providing degraded functionality
    when the primary operation fails.

    Args:
        fallback_func: Function to call if main function fails
        fallback_args: Arguments to pass to fallback function (default: None)
        fallback_kwargs: Keyword arguments to pass to fallback function (default: None)

    Returns:
        Decorated function with fallback logic

    Example:
        async def get_default_model():
            return "default-model"

        @fallback_strategy(get_default_model)
        async def get_preferred_model():
            # If this fails, get_default_model() will be called
            response = await client.get("/v1/models/preferred")
            return response.json()
    """
    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            # Async version
            @wraps(func)
            async def async_wrapper(*args, **kwargs) -> Any:
                try:
                    return await func(*args, **kwargs)

                except Exception as e:
                    logger.warning(
                        f"{func.__name__} failed: {e}. "
                        f"Using fallback: {fallback_func.__name__}"
                    )

                    # Call fallback function
                    f_args = fallback_args or ()
                    f_kwargs = fallback_kwargs or {}

                    if asyncio.iscoroutinefunction(fallback_func):
                        return await fallback_func(*f_args, **f_kwargs)
                    else:
                        return fallback_func(*f_args, **f_kwargs)

            return async_wrapper

        else:
            # Sync version
            @wraps(func)
            def sync_wrapper(*args, **kwargs) -> Any:
                try:
                    return func(*args, **kwargs)

                except Exception as e:
                    logger.warning(
                        f"{func.__name__} failed: {e}. "
                        f"Using fallback: {fallback_func.__name__}"
                    )

                    # Call fallback function
                    f_args = fallback_args or ()
                    f_kwargs = fallback_kwargs or {}

                    return fallback_func(*f_args, **f_kwargs)

            return sync_wrapper

    return decorator


def log_errors(func: Callable) -> Callable:
    """Decorator that logs exceptions before re-raising them.

    This is useful for debugging and monitoring - it ensures that all
    errors are logged even if they're caught and handled elsewhere.

    Args:
        func: Function to wrap with error logging

    Returns:
        Decorated function with error logging

    Example:
        @log_errors
        async def risky_operation():
            # Any exceptions will be logged with full traceback
            await do_something_risky()
    """
    if asyncio.iscoroutinefunction(func):
        # Async version
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.exception(
                    f"Exception in {func.__name__}: {e}",
                    exc_info=True
                )
                raise

        return async_wrapper

    else:
        # Sync version
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.exception(
                    f"Exception in {func.__name__}: {e}",
                    exc_info=True
                )
                raise

        return sync_wrapper


__all__ = [
    "retry_with_backoff",
    "fallback_strategy",
    "log_errors",
]
