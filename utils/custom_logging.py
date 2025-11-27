#!/usr/bin/env python3
"""
Logging utilities for lmstudio-bridge-enhanced.

Provides structured logging with proper context and levels.
"""

import sys
import logging
from typing import Optional
from datetime import datetime


# Logging levels
DEBUG = logging.DEBUG
INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR
CRITICAL = logging.CRITICAL


class GenericLogger:
    """Generic structured logger with context support for standard logging.

    This logger provides standard log levels (debug, info, warning, error, critical)
    and is suitable for general-purpose logging across the application.
    """

    def __init__(self, name: str, level: int = INFO):
        """Initialize generic logger.

        Args:
            name: Logger name
            level: Logging level
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        # Add stderr handler if not already present
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stderr)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def debug(self, message: str, **context) -> None:
        """Log debug message.

        Args:
            message: Log message
            **context: Additional context fields
        """
        self._log(DEBUG, message, context)

    def info(self, message: str, **context) -> None:
        """Log info message.

        Args:
            message: Log message
            **context: Additional context fields
        """
        self._log(INFO, message, context)

    def warning(self, message: str, **context) -> None:
        """Log warning message.

        Args:
            message: Log message
            **context: Additional context fields
        """
        self._log(WARNING, message, context)

    def error(self, message: str, **context) -> None:
        """Log error message.

        Args:
            message: Log message
            **context: Additional context fields
        """
        self._log(ERROR, message, context)

    def critical(self, message: str, **context) -> None:
        """Log critical message.

        Args:
            message: Log message
            **context: Additional context fields
        """
        self._log(CRITICAL, message, context)

    def exception(self, exception: Exception, message: str = None, **context) -> None:
        """Log exception with automatic error categorization.

        This method provides structured error logging by automatically extracting:
        - error_type: Exception class name (e.g., "LLMTimeoutError")
        - error_message: Exception message
        - timestamp: When the error occurred (if exception has timestamp attribute)

        Args:
            exception: The exception to log
            message: Optional custom message (defaults to exception message)
            **context: Additional context fields

        Example:
            >>> try:
            ...     raise LLMTimeoutError("Request timed out")
            ... except Exception as e:
            ...     logger.exception(e, "Failed to process request")
            # Logs: Failed to process request | error_type=LLMTimeoutError | error_message=Request timed out
        """
        # Extract error type (class name)
        error_type = exception.__class__.__name__

        # Use custom message or exception message
        error_message = str(exception)
        log_message = message if message else error_message

        # Build context with error categorization
        error_context = {
            "error_type": error_type,
            "error_message": error_message,
            **context
        }

        # Add timestamp if exception has it (LLM exceptions do)
        if hasattr(exception, 'timestamp'):
            error_context["timestamp"] = exception.timestamp.isoformat()

        # Log at ERROR level with full context
        self._log(ERROR, log_message, error_context)

    def _log(self, level: int, message: str, context: dict) -> None:
        """Internal logging method.

        Args:
            level: Logging level
            message: Log message
            context: Context dictionary
        """
        if context:
            context_str = " | ".join(f"{k}={v}" for k, v in context.items())
            full_message = f"{message} | {context_str}"
        else:
            full_message = message

        self.logger.log(level, full_message)


# Global logger instances
_loggers = {}


def get_logger(name: str, level: int = INFO) -> GenericLogger:
    """Get or create a generic logger instance.

    Args:
        name: Logger name
        level: Logging level

    Returns:
        GenericLogger instance
    """
    if name not in _loggers:
        _loggers[name] = GenericLogger(name, level)
    return _loggers[name]


# Convenience functions for backward compatibility
def log_error(message: str) -> None:
    """Log error message to stderr (backward compatible).

    Args:
        message: Error message
    """
    print(f"ERROR: {message}", file=sys.stderr)


def log_categorized_error(exception: Exception, context_message: str = None, **context) -> None:
    """Log exception with automatic error categorization.

    This is a convenience function that provides categorized error logging without
    needing to create a logger instance. It automatically extracts error_type from
    the exception and includes it in the log output.

    Args:
        exception: The exception to log
        context_message: Optional context message (defaults to exception message)
        **context: Additional context fields (e.g., model="gpt-4", operation="validate")

    Example:
        >>> try:
        ...     raise LLMTimeoutError("Request timed out")
        ... except Exception as e:
        ...     log_categorized_error(e, "Model validation failed", model="gpt-4")
        # Logs with error_type=LLMTimeoutError, error_message=Request timed out, model=gpt-4
    """
    # Get a logger for the caller's module
    import inspect
    frame = inspect.currentframe().f_back
    module_name = frame.f_globals['__name__'] if frame else __name__

    logger = get_logger(module_name)
    logger.exception(exception, message=context_message, **context)


def log_info(message: str) -> None:
    """Log info message to stderr (backward compatible).

    Args:
        message: Info message
    """
    print(f"INFO: {message}", file=sys.stderr)


def log_warning(message: str) -> None:
    """Log warning message to stderr.

    Args:
        message: Warning message
    """
    print(f"WARNING: {message}", file=sys.stderr)


def log_debug(message: str) -> None:
    """Log debug message to stderr.

    Args:
        message: Debug message
    """
    print(f"DEBUG: {message}", file=sys.stderr)


__all__ = [
    "GenericLogger",
    "get_logger",
    "log_error",
    "log_categorized_error",
    "log_info",
    "log_warning",
    "log_debug",
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL"
]
