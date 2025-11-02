#!/usr/bin/env python3
"""
Input validation utilities for autonomous execution tools.
"""

import os
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
    """Validate a single directory path.

    Args:
        directory: Directory path to validate
        allow_root: Whether to allow root directory '/' (default: False for security)

    Returns:
        Validated absolute path

    Raises:
        ValidationError: If directory is invalid
    """
    # Convert to absolute path
    path = Path(directory).expanduser().resolve()

    # Security check: Block root directory unless explicitly allowed
    if str(path) == '/' and not allow_root:
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

    # Warn about sensitive system directories (but don't block - user might have legitimate reasons)
    sensitive_dirs = {
        '/etc': 'system configuration files',
        '/var': 'system variable data and logs',
        '/bin': 'essential system binaries',
        '/sbin': 'system administration binaries',
        '/usr': 'user system resources',
        '/System': 'macOS system files',
        '/Library': 'macOS system libraries',
        '/boot': 'Linux boot files',
        '/root': 'root user home directory'
    }

    for sensitive_path, description in sensitive_dirs.items():
        if str(path) == sensitive_path or str(path).startswith(f"{sensitive_path}/"):
            import warnings
            warnings.warn(
                f"\n{'='*70}\n"
                f"SECURITY WARNING: Allowing access to sensitive directory!\n"
                f"Path: {path}\n"
                f"Contains: {description}\n"
                f"\n"
                f"This gives the local LLM access to system files. Be careful!\n"
                f"{'='*70}\n",
                UserWarning,
                stacklevel=3
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


__all__ = [
    "ValidationError",
    "validate_task",
    "validate_working_directory",
    "validate_max_rounds",
    "validate_max_tokens"
]
