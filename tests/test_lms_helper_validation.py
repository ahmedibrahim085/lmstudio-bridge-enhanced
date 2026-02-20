#!/usr/bin/env python3
"""
Tests for validate_model_name() enforcement in download_model().

Verifies that download_model() rejects invalid model names before
passing them to subprocess.run(), matching the pattern used by
load_model() and unload_model().
"""

from unittest.mock import MagicMock, patch

import pytest

from utils.lms_helper import LMSHelper


class TestDownloadModelValidation:
    """Verify download_model() enforces validate_model_name() before subprocess."""

    # ------------------------------------------------------------------
    # Fixtures
    # ------------------------------------------------------------------

    @pytest.fixture(autouse=True)
    def reset_installed_cache(self):
        """Reset the class-level is_installed cache before each test."""
        original = LMSHelper._is_installed
        yield
        LMSHelper._is_installed = original

    # ------------------------------------------------------------------
    # Invalid names — must be rejected BEFORE subprocess is called
    #
    # Note: validate_model_name() uses regex ^[a-zA-Z0-9/_.-]+$
    # Characters allowed: alphanumeric, '/', '_', '-', '.'
    # Characters rejected: ';', '$', '`', ' ', '&', '|', '>', etc.
    # Path traversal ("../../../etc/passwd") is NOT caught by this regex
    # because '.' and '/' are both allowed — that is an existing validator
    # limitation outside the scope of this task.
    # ------------------------------------------------------------------

    @pytest.mark.parametrize("bad_name, description", [
        ("; rm -rf /", "shell injection with semicolon"),
        ("$(id)", "command substitution"),
        ("`whoami`", "backtick injection"),
        ("model name", "space in name"),
        ("model&name", "ampersand injection"),
        ("model|name", "pipe injection"),
        ("model>out", "redirection"),
        ("", "empty string"),
    ])
    def test_download_model_rejects_invalid_names(self, bad_name, description):
        """download_model() must return (False, 'Invalid model name: ...') for bad inputs."""
        with patch.object(LMSHelper, "is_installed", return_value=True), \
             patch("subprocess.run") as mock_run:

            success, message = LMSHelper.download_model(bad_name)

            assert success is False, (
                f"Expected failure for {description!r} ({bad_name!r}), got success=True"
            )
            assert "Invalid model name" in message, (
                f"Expected 'Invalid model name' in message for {description!r}, got: {message!r}"
            )
            mock_run.assert_not_called()

    # ------------------------------------------------------------------
    # Valid names — subprocess must be invoked
    # ------------------------------------------------------------------

    @pytest.mark.parametrize("valid_name", [
        "qwen/qwen3-4b",
        "mistral-7b",
        "mistral-7b-instruct-v0.2",
        "llama3.1-8b",
        "org/model-name_variant.gguf",
    ])
    def test_download_model_accepts_valid_names(self, valid_name):
        """download_model() must proceed to subprocess for safe model names."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_result.stdout = ""

        with patch.object(LMSHelper, "is_installed", return_value=True), \
             patch("subprocess.run", return_value=mock_result) as mock_run:

            success, message = LMSHelper.download_model(valid_name)

            assert success is True, (
                f"Expected success for valid name {valid_name!r}, got: message={message!r}"
            )
            mock_run.assert_called_once()
            called_cmd = mock_run.call_args[0][0]
            assert valid_name in called_cmd, (
                f"Expected {valid_name!r} in subprocess cmd, got: {called_cmd!r}"
            )

    # ------------------------------------------------------------------
    # Guard: lms not installed — must short-circuit before validation
    # ------------------------------------------------------------------

    def test_download_model_lms_not_installed_short_circuits(self):
        """download_model() must return early if LMS CLI is not installed."""
        with patch.object(LMSHelper, "is_installed", return_value=False), \
             patch("subprocess.run") as mock_run:

            success, message = LMSHelper.download_model("qwen/qwen3-4b")

            assert success is False
            assert "LMS CLI not installed" in message
            mock_run.assert_not_called()
