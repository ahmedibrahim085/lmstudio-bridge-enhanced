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


class StructuredLogger:
    """Structured logger with context support."""

    def __init__(self, name: str, level: int = INFO):
        """Initialize structured logger.

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


def get_logger(name: str, level: int = INFO) -> StructuredLogger:
    """Get or create a logger instance.

    Args:
        name: Logger name
        level: Logging level

    Returns:
        StructuredLogger instance
    """
    if name not in _loggers:
        _loggers[name] = StructuredLogger(name, level)
    return _loggers[name]


# Convenience functions for backward compatibility
def log_error(message: str) -> None:
    """Log error message to stderr (backward compatible).

    Args:
        message: Error message
    """
    print(f"ERROR: {message}", file=sys.stderr)


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
    "StructuredLogger",
    "get_logger",
    "log_error",
    "log_info",
    "log_warning",
    "log_debug",
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL"
]
