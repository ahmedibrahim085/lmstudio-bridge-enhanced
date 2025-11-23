#!/usr/bin/env python3
"""
Integration tests for LMS CLI functionality.

These tests require:
1. LMS CLI to be installed (brew install lmstudio-ai/lms/lms)
2. LM Studio to be running

Tests are marked with @pytest.mark.integration and can be skipped with:
    pytest -m "not integration"

Or run only integration tests with:
    pytest -m integration
"""

import pytest
import subprocess
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.lms_helper import LMSHelper


def lms_cli_available():
    """Check if LMS CLI is actually available (not mocked)."""
    try:
        result = subprocess.run(
            ["lms", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


# Skip all tests in this module if LMS CLI is not available
pytestmark = pytest.mark.skipif(
    not lms_cli_available(),
    reason="LMS CLI not installed or not available"
)


@pytest.mark.integration
class TestLMSHelperIntegration:
    """Integration tests that use real LMS CLI."""

    def test_is_installed_real(self):
        """Test that is_installed returns True when LMS CLI is available."""
        # Clear the cached value to force re-check
        LMSHelper._is_installed = None

        result = LMSHelper.is_installed()

        assert result is True
        # Cache should be set
        assert LMSHelper._is_installed is True

    def test_list_downloaded_models_real(self):
        """Test listing downloaded models with real LMS CLI."""
        models = LMSHelper.list_downloaded_models()

        # Should return a list (possibly empty if no models downloaded)
        assert models is not None
        assert isinstance(models, list)

        # If models exist, verify structure
        if models:
            model = models[0]
            assert "modelKey" in model
            # Other expected fields from LMS metadata
            assert "type" in model or "sizeBytes" in model

    def test_list_loaded_models_real(self):
        """Test listing loaded models with real LMS CLI."""
        models = LMSHelper.list_loaded_models()

        # Should return a list (possibly empty if no models loaded)
        assert models is not None
        assert isinstance(models, list)

        # If models are loaded, verify structure
        if models:
            model = models[0]
            assert "identifier" in model or "modelKey" in model

    def test_get_server_status_real(self):
        """Test getting server status with real LMS CLI."""
        status = LMSHelper.get_server_status()

        # May return None if server not running, but should not raise
        # If server is running, should return dict
        if status is not None:
            assert isinstance(status, dict)


@pytest.mark.integration
class TestRetryIntegration:
    """Integration tests for retry functionality."""

    def test_list_models_with_retry(self):
        """Test that list_downloaded_models uses retry correctly."""
        # This just verifies the retry-enabled method works
        # In production, retry kicks in on timeout
        models = LMSHelper.list_downloaded_models()

        # Should succeed (with or without retry)
        assert models is not None or LMSHelper.is_installed() is False


if __name__ == "__main__":
    if lms_cli_available():
        pytest.main([__file__, "-v", "-m", "integration"])
    else:
        print("LMS CLI not available - skipping integration tests")
        print("Install with: brew install lmstudio-ai/lms/lms")
