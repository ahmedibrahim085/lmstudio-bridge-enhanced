#!/usr/bin/env python3
"""
Error handling and custom exceptions for lmstudio-bridge-enhanced.
"""

from typing import Optional, Any


class LMStudioBridgeError(Exception):
    """Base exception for lmstudio-bridge-enhanced errors."""

    def __init__(self, message: str, details: Optional[Any] = None):
        """Initialize error.

        Args:
            message: Error message
            details: Optional additional details
        """
        super().__init__(message)
        self.message = message
        self.details = details

    def __str__(self) -> str:
        """String representation of error."""
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


class ConfigurationError(LMStudioBridgeError):
    """Error in configuration."""
    pass


class LLMClientError(LMStudioBridgeError):
    """Error communicating with LLM API."""
    pass


class MCPConnectionError(LMStudioBridgeError):
    """Error connecting to MCP server."""
    pass


class MCPToolExecutionError(LMStudioBridgeError):
    """Error executing MCP tool."""
    pass


class ToolDiscoveryError(LMStudioBridgeError):
    """Error discovering tools from MCP."""
    pass


class AutonomousExecutionError(LMStudioBridgeError):
    """Error during autonomous execution."""
    pass


class SchemaConversionError(LMStudioBridgeError):
    """Error converting schemas."""
    pass


def handle_error(error: Exception, context: Optional[str] = None) -> str:
    """Handle an error and return formatted message.

    Args:
        error: Exception to handle
        context: Optional context information

    Returns:
        Formatted error message
    """
    error_type = type(error).__name__

    if isinstance(error, LMStudioBridgeError):
        message = str(error)
    else:
        message = f"{error_type}: {str(error)}"

    if context:
        message = f"[{context}] {message}"

    return message


__all__ = [
    "LMStudioBridgeError",
    "ConfigurationError",
    "LLMClientError",
    "MCPConnectionError",
    "MCPToolExecutionError",
    "ToolDiscoveryError",
    "AutonomousExecutionError",
    "SchemaConversionError",
    "handle_error"
]
