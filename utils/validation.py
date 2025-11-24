#!/usr/bin/env python3
"""
Input validation utilities for autonomous execution tools.
"""

import os
import re
from pathlib import Path
from typing import Optional, Union, List


class ValidationError(Exception):
    """Raised when input validation fails."""
    pass


def validate_task(task: str) -> None:
    """Validate task parameter.

    Args:
        task: Task description string

    Raises:
        ValidationError: If task is invalid
    """
    if not task:
        raise ValidationError("Task cannot be empty")

    if not isinstance(task, str):
        raise ValidationError(f"Task must be a string, got {type(task).__name__}")

    if len(task.strip()) == 0:
        raise ValidationError("Task cannot be only whitespace")

    if len(task) > 10000:
        raise ValidationError("Task description too long (max 10,000 characters)")


def validate_working_directory(
    working_directory: Optional[Union[str, List[str]]],
    allow_none: bool = False
) -> Optional[Union[str, List[str]]]:
    """Validate working directory parameter (single or multiple directories).

    Args:
        working_directory: Directory path or list of paths to validate
        allow_none: Whether None is acceptable

    Returns:
        Validated absolute path(s) or None

    Raises:
        ValidationError: If working directory is invalid
    """
    if working_directory is None:
        if allow_none:
            return None
        raise ValidationError("Working directory cannot be None")

    # Handle list of directories
    if isinstance(working_directory, list):
        if len(working_directory) == 0:
            raise ValidationError("Working directory list cannot be empty")

        validated_dirs = []
        for i, dir_path in enumerate(working_directory):
            if not isinstance(dir_path, str):
                raise ValidationError(
                    f"Directory at index {i} must be a string, got {type(dir_path).__name__}"
                )
            validated_dirs.append(_validate_single_directory(dir_path))

        return validated_dirs

    # Handle single directory
    if not isinstance(working_directory, str):
        raise ValidationError(
            f"Working directory must be a string or list of strings, got {type(working_directory).__name__}"
        )

    return _validate_single_directory(working_directory)


def _validate_single_directory(directory: str, allow_root: bool = False) -> str:
    """Validate a single directory path with comprehensive security checks.

    Args:
        directory: Directory path to validate
        allow_root: Whether to allow root directory '/' (default: False for security)

    Returns:
        Validated absolute path

    Raises:
        ValidationError: If directory is invalid or poses security risk
    """
    import logging
    logger = logging.getLogger(__name__)

    # Security: Validate input is non-empty string
    if not directory or not isinstance(directory, str):
        raise ValidationError("Directory path must be a non-empty string")

    # Security: Check for null bytes (path traversal prevention)
    if '\x00' in directory:
        raise ValidationError("Directory path contains null bytes (possible injection attempt)")

    # Convert to absolute path with full resolution
    # This resolves symlinks and normalizes the path, preventing bypass attempts
    try:
        path = Path(directory).expanduser().resolve(strict=False)
    except (RuntimeError, OSError) as e:
        raise ValidationError(f"Invalid directory path: {e}")

    # Security: Keep both the normalized (non-resolved) and resolved paths
    # This prevents symlink bypass attacks (e.g., /etc -> /private/etc on macOS)
    normalized_path = Path(directory).expanduser().absolute()

    # Security: Detect path traversal attempts
    if '..' in str(normalized_path):
        logger.warning(f"Path traversal attempt detected in: {directory}")

    # Security check: Block root directory unless explicitly allowed
    # Check both resolved and normalized paths to prevent symlink bypass
    if (str(path) == '/' or str(normalized_path) == '/') and not allow_root:
        raise ValidationError(
            "Root directory '/' is not allowed for security reasons.\n"
            "This would give the local LLM access to your ENTIRE filesystem including:\n"
            "  - System files (/etc, /var, /bin)\n"
            "  - All user data\n"
            "  - Sensitive configuration files\n"
            "\n"
            "Best practice: Specify only the directories you need, e.g.:\n"
            "  - /Users/yourname/projects\n"
            "  - /path/to/specific/project\n"
            "\n"
            "If you absolutely need root access (NOT RECOMMENDED), you must explicitly\n"
            "allow it by modifying the validation code."
        )

    # Block highly sensitive system directories (security critical)
    # Check both resolved and normalized paths to prevent symlink bypass
    blocked_dirs = {
        '/etc': 'system configuration files - access denied for security',
        '/bin': 'essential system binaries - access denied for security',
        '/sbin': 'system administration binaries - access denied for security',
        '/System': 'macOS system files - access denied for security',
        '/boot': 'Linux boot files - access denied for security',
        '/root': 'root user home directory - access denied for security',
        '/private/etc': 'system configuration files - access denied for security (symlink target)'
        # Note: /private/var NOT blocked - /var should only generate warning
    }

    for blocked_path, description in blocked_dirs.items():
        # Check both the resolved path and normalized path to catch symlinks
        if (str(path) == blocked_path or str(path).startswith(f"{blocked_path}/") or
            str(normalized_path) == blocked_path or str(normalized_path).startswith(f"{blocked_path}/")):
            raise ValidationError(
                f"Access denied to sensitive system directory: {directory}\n"
                f"Resolved to: {path}\n"
                f"Reason: {description}\n"
                "\n"
                "This directory contains critical system files and is blocked for security.\n"
                "Please specify a user directory or project-specific path instead."
            )

    # Warn about potentially sensitive directories (but allow with warning)
    # Check both resolved and normalized paths
    warning_dirs = {
        '/var': 'system variable data and logs',
        '/usr': 'user system resources',
        '/Library': 'macOS system libraries',
        '/opt': 'optional software packages',
        '/tmp': 'temporary files (world-writable)'
    }

    for warning_path, description in warning_dirs.items():
        if (str(path) == warning_path or str(path).startswith(f"{warning_path}/") or
            str(normalized_path) == warning_path or str(normalized_path).startswith(f"{warning_path}/")):
            logger.warning(
                f"\n{'='*70}\n"
                f"SECURITY WARNING: Accessing potentially sensitive directory!\n"
                f"Original: {directory}\n"
                f"Resolved to: {path}\n"
                f"Contains: {description}\n"
                f"\n"
                f"This may give the local LLM access to system files. Proceed with caution!\n"
                f"{'='*70}\n"
            )
            break

    # Check if path exists
    if not path.exists():
        raise ValidationError(f"Working directory does not exist: {path}")

    # Check if it's a directory
    if not path.is_dir():
        raise ValidationError(f"Path is not a directory: {path}")

    # Check if readable
    if not os.access(path, os.R_OK):
        raise ValidationError(f"Directory is not readable: {path}")

    return str(path)


def validate_max_rounds(max_rounds: int) -> int:
    """Validate max_rounds parameter.

    Args:
        max_rounds: Maximum number of autonomous rounds

    Returns:
        Validated max_rounds value

    Raises:
        ValidationError: If max_rounds is invalid
    """
    if not isinstance(max_rounds, int):
        raise ValidationError(
            f"max_rounds must be an integer, got {type(max_rounds).__name__}"
        )

    if max_rounds < 1:
        raise ValidationError("max_rounds must be at least 1")

    if max_rounds > 10000:
        raise ValidationError(
            "max_rounds too high (max 10,000). Consider if this is really needed."
        )

    return max_rounds


def validate_max_tokens(max_tokens: int, model_max: Optional[int] = None) -> int:
    """Validate max_tokens parameter.

    Args:
        max_tokens: Maximum tokens to generate
        model_max: Optional maximum tokens supported by model

    Returns:
        Validated max_tokens value

    Raises:
        ValidationError: If max_tokens is invalid
    """
    if not isinstance(max_tokens, int):
        raise ValidationError(
            f"max_tokens must be an integer, got {type(max_tokens).__name__}"
        )

    if max_tokens < 1:
        raise ValidationError("max_tokens must be at least 1")

    # Check against model's maximum if provided
    if model_max and max_tokens > model_max:
        raise ValidationError(
            f"max_tokens ({max_tokens}) exceeds model's maximum ({model_max}). "
            f"Use 'auto' or a value <= {model_max}"
        )

    return max_tokens


# Pattern for valid MCP server names
# Allows: alphanumeric, @, /, -, _, .
# Examples: "filesystem", "@modelcontextprotocol/server-filesystem", "my_custom-mcp.v2"
MCP_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9@/_.-]+$')

# Pattern for valid model names
# Allows: alphanumeric, /, -, _, .
# Examples: "qwen/qwen3-4b", "mistral-7b-instruct-v0.2", "local_model.gguf"
MODEL_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9/_.-]+$')


def validate_mcp_name(name: str) -> str:
    """Validate MCP server name to prevent injection attacks.

    Args:
        name: MCP server name to validate

    Returns:
        Validated name (unchanged if valid)

    Raises:
        ValidationError: If name contains invalid characters

    Examples:
        >>> validate_mcp_name("filesystem")  # Valid
        'filesystem'
        >>> validate_mcp_name("@modelcontextprotocol/server-filesystem")  # Valid
        '@modelcontextprotocol/server-filesystem'
        >>> validate_mcp_name("bad;name")  # Raises ValidationError
    """
    if not name:
        raise ValidationError("MCP name cannot be empty")

    if not isinstance(name, str):
        raise ValidationError(f"MCP name must be a string, got {type(name).__name__}")

    if not MCP_NAME_PATTERN.match(name):
        raise ValidationError(
            f"Invalid MCP name: '{name}'. "
            f"Names may only contain alphanumeric characters, @, /, -, _, and ."
        )

    return name


def validate_model_name(name: str) -> str:
    """Validate model name to prevent injection attacks.

    Args:
        name: Model name to validate

    Returns:
        Validated name (unchanged if valid)

    Raises:
        ValidationError: If name contains invalid characters

    Examples:
        >>> validate_model_name("qwen/qwen3-4b")  # Valid
        'qwen/qwen3-4b'
        >>> validate_model_name("mistral-7b-instruct-v0.2")  # Valid
        'mistral-7b-instruct-v0.2'
        >>> validate_model_name("bad;model")  # Raises ValidationError
    """
    if not name:
        raise ValidationError("Model name cannot be empty")

    if not isinstance(name, str):
        raise ValidationError(f"Model name must be a string, got {type(name).__name__}")

    if not MODEL_NAME_PATTERN.match(name):
        raise ValidationError(
            f"Invalid model name: '{name}'. "
            f"Names may only contain alphanumeric characters, /, -, _, and ."
        )

    return name


__all__ = [
    "ValidationError",
    "validate_task",
    "validate_working_directory",
    "validate_max_rounds",
    "validate_max_tokens",
    "validate_mcp_name",
    "validate_model_name",
    "MCP_NAME_PATTERN",
    "MODEL_NAME_PATTERN"
]
