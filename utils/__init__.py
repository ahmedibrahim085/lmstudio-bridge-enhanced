"""Utility modules for logging, error handling, validation, and helpers."""

from .custom_logging import (
    GenericLogger,
    get_logger,
    log_error,
    log_info,
    log_warning,
    log_debug,
    DEBUG,
    INFO,
    WARNING,
    ERROR,
    CRITICAL
)
from .errors import (
    LMStudioBridgeError,
    ConfigurationError,
    LLMClientError,
    MCPConnectionError,
    MCPToolExecutionError,
    ToolDiscoveryError,
    AutonomousExecutionError,
    SchemaConversionError,
    handle_error
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
    "log_info",
    "log_warning",
    "log_debug",
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL",
    # Errors
    "LMStudioBridgeError",
    "ConfigurationError",
    "LLMClientError",
    "MCPConnectionError",
    "MCPToolExecutionError",
    "ToolDiscoveryError",
    "AutonomousExecutionError",
    "SchemaConversionError",
    "handle_error",
    # Validation
    "ValidationError",
    "validate_task",
    "validate_working_directory",
    "validate_max_rounds",
    "validate_max_tokens"
]
