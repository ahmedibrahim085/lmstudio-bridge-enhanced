#!/usr/bin/env python3
"""
Retry utilities for resilient subprocess execution.

Provides exponential backoff retry logic for LMS CLI commands
that may timeout due to server load or startup delays.
"""

import os
import time
import random
import logging
import subprocess
from typing import List, Any

logger = logging.getLogger(__name__)

# Configuration via environment variables
DEFAULT_MAX_RETRIES = int(os.environ.get("LMS_MAX_RETRIES", "3"))
DEFAULT_BASE_DELAY = float(os.environ.get("LMS_RETRY_BASE_DELAY", "1.0"))
DEFAULT_MAX_DELAY = float(os.environ.get("LMS_RETRY_MAX_DELAY", "10.0"))


def run_with_retry(
    cmd: List[str],
    timeout: int,
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    retry_on_error: bool = False,
    capture_output: bool = True,
    text: bool = True
) -> subprocess.CompletedProcess:
    """
    Run a subprocess command with exponential backoff retry on timeout.

    Args:
        cmd: Command and arguments to run
        timeout: Timeout in seconds for each attempt
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Initial delay between retries in seconds (default: 1.0)
        max_delay: Maximum delay between retries (default: 10.0)
        retry_on_error: If True, also retry on non-zero exit codes
        capture_output: Capture stdout/stderr (default: True)
        text: Return output as text (default: True)

    Returns:
        subprocess.CompletedProcess from successful execution (may have non-zero returncode
        if retry_on_error=False and command fails)

    Raises:
        subprocess.TimeoutExpired: If all retries exhausted due to timeout
        FileNotFoundError: If command executable not found
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            result = subprocess.run(
                cmd,
                capture_output=capture_output,
                text=text,
                timeout=timeout
            )

            # Check if we should retry on error
            if retry_on_error and result.returncode != 0:
                if attempt < max_retries:
                    delay = _calculate_delay(attempt, base_delay, max_delay)
                    logger.warning(
                        f"Command failed (attempt {attempt + 1}/{max_retries + 1}), "
                        f"retrying in {delay:.1f}s: {' '.join(cmd[:2])}"
                    )
                    time.sleep(delay)
                    continue

            # Success or non-retryable error
            if attempt > 0:
                logger.info(f"Command succeeded after {attempt + 1} attempts")
            return result

        except subprocess.TimeoutExpired as e:
            last_exception = e
            if attempt < max_retries:
                delay = _calculate_delay(attempt, base_delay, max_delay)
                logger.warning(
                    f"Command timed out (attempt {attempt + 1}/{max_retries + 1}), "
                    f"retrying in {delay:.1f}s: {' '.join(cmd[:2])}"
                )
                time.sleep(delay)
            else:
                logger.error(
                    f"Command timed out after {max_retries + 1} attempts: {' '.join(cmd[:2])}"
                )
                raise

        except FileNotFoundError:
            # Don't retry if command doesn't exist
            raise

        except Exception as e:
            # Don't retry on unexpected errors
            logger.error(f"Unexpected error running command: {e}")
            raise

    # Should not reach here, but just in case
    if last_exception:
        raise last_exception
    raise RuntimeError("Retry logic error - no result or exception")


def _calculate_delay(attempt: int, base_delay: float, max_delay: float) -> float:
    """
    Calculate delay with exponential backoff and jitter.

    Formula: min(max_delay, base_delay * 2^attempt * (0.5 + random(0, 0.5)))

    Args:
        attempt: Current attempt number (0-indexed)
        base_delay: Base delay in seconds
        max_delay: Maximum delay cap

    Returns:
        Delay in seconds
    """
    # Exponential backoff: 1s, 2s, 4s, 8s...
    exponential = base_delay * (2 ** attempt)

    # Add jitter (0.5x to 1.0x of exponential)
    jitter = 0.5 + random.random() * 0.5
    delay = exponential * jitter

    # Cap at max_delay
    return min(delay, max_delay)


__all__ = [
    'run_with_retry',
    'DEFAULT_MAX_RETRIES',
    'DEFAULT_BASE_DELAY',
    'DEFAULT_MAX_DELAY',
]
