"""Utility modules for logging, error handling, validation, and helpers."""

from .custom_logging import (
    GenericLogger,
    get_logger,
    log_error,
    log_categorized_error,
    log_info,
    log_warning,
    log_debug,
    DEBUG,
    INFO,
    WARNING,
    ERROR,
    CRITICAL
)
from .validation import (
    ValidationError,
    validate_task,
    validate_working_directory,
    validate_max_rounds,
    validate_max_tokens
)

__all__ = [
    # Logging
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
    "CRITICAL",
    # Validation
    "ValidationError",
    "validate_task",
    "validate_working_directory",
    "validate_max_rounds",
    "validate_max_tokens"
]
