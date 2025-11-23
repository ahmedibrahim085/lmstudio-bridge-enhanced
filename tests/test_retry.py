#!/usr/bin/env python3
"""
Tests for retry utilities.
"""

import pytest
import subprocess
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.retry import run_with_retry, _calculate_delay


class TestRunWithRetry:
    """Tests for run_with_retry function."""

    @patch('utils.retry.subprocess.run')
    def test_success_first_try(self, mock_run):
        """Test successful execution on first try."""
        mock_run.return_value = MagicMock(returncode=0, stdout="success", stderr="")

        result = run_with_retry(["echo", "test"], timeout=5)

        assert result.returncode == 0
        assert mock_run.call_count == 1

    @patch('utils.retry.subprocess.run')
    def test_success_after_timeout_retry(self, mock_run):
        """Test successful execution after timeout retry."""
        # First call times out, second succeeds
        mock_run.side_effect = [
            subprocess.TimeoutExpired(cmd=["test"], timeout=5),
            MagicMock(returncode=0, stdout="success", stderr="")
        ]

        result = run_with_retry(["echo", "test"], timeout=5, max_retries=2)

        assert result.returncode == 0
        assert mock_run.call_count == 2

    @patch('utils.retry.subprocess.run')
    def test_all_retries_exhausted(self, mock_run):
        """Test that TimeoutExpired is raised after all retries."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["test"], timeout=5)

        with pytest.raises(subprocess.TimeoutExpired):
            run_with_retry(["echo", "test"], timeout=5, max_retries=2)

        # Initial + 2 retries = 3 calls
        assert mock_run.call_count == 3

    @patch('utils.retry.subprocess.run')
    def test_file_not_found_no_retry(self, mock_run):
        """Test that FileNotFoundError is not retried."""
        mock_run.side_effect = FileNotFoundError("command not found")

        with pytest.raises(FileNotFoundError):
            run_with_retry(["nonexistent_command"], timeout=5)

        # Should not retry
        assert mock_run.call_count == 1

    @patch('utils.retry.subprocess.run')
    def test_retry_on_error_flag(self, mock_run):
        """Test retry_on_error flag for non-zero exit codes."""
        # First call fails with exit code 1, second succeeds
        mock_run.side_effect = [
            MagicMock(returncode=1, stdout="", stderr="error"),
            MagicMock(returncode=0, stdout="success", stderr="")
        ]

        result = run_with_retry(
            ["test"], timeout=5, max_retries=2, retry_on_error=True
        )

        assert result.returncode == 0
        assert mock_run.call_count == 2


class TestCalculateDelay:
    """Tests for delay calculation."""

    def test_exponential_backoff(self):
        """Test that delay increases exponentially."""
        delays = [_calculate_delay(i, 1.0, 100.0) for i in range(4)]

        # Each delay should be roughly 2x the previous (with jitter)
        # delay[0] ≈ 1s, delay[1] ≈ 2s, delay[2] ≈ 4s, delay[3] ≈ 8s
        assert delays[1] > delays[0]
        assert delays[2] > delays[1]
        assert delays[3] > delays[2]

    def test_max_delay_cap(self):
        """Test that delay is capped at max_delay."""
        delay = _calculate_delay(10, 1.0, 5.0)  # Would be 1024s without cap

        assert delay <= 5.0

    def test_jitter_applied(self):
        """Test that jitter is applied (delays should vary)."""
        # Run multiple times and check for variation
        delays = [_calculate_delay(1, 1.0, 100.0) for _ in range(10)]

        # Not all delays should be exactly the same due to jitter
        unique_delays = len(set(delays))
        assert unique_delays > 1  # At least some variation


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
