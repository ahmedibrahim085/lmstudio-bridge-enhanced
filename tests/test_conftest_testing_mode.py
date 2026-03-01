"""Tests for D-1: LMSTUDIO_TESTING activation in conftest.py.

Verifies that conftest.py sets LMSTUDIO_TESTING env var before any
production imports, preventing HTTP auto-detection during pytest sessions.

The CAPABILITY was added in R-2 (config_main.py:82-83). D-1 ACTIVATES it.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config.constants import LMSTUDIO_TESTING_ENV_VAR


class TestConftestTestingModeActivation:
    """Verify conftest.py activates LMSTUDIO_TESTING for all pytest sessions."""

    @pytest.mark.unit
    def test_lmstudio_testing_env_active(self):
        """LMSTUDIO_TESTING env var must be set (truthy) during pytest sessions.

        conftest.py should call os.environ.setdefault(LMSTUDIO_TESTING_ENV_VAR, "1")
        before any production imports that could trigger get_config().
        """
        value = os.environ.get(LMSTUDIO_TESTING_ENV_VAR)
        assert value, (
            f"{LMSTUDIO_TESTING_ENV_VAR} env var not set during pytest session. "
            f"conftest.py must activate testing mode to prevent HTTP auto-detection."
        )

    @pytest.mark.unit
    def test_lmstudio_testing_uses_correct_env_var_name(self):
        """The env var name matches the constant (no hardcoded strings)."""
        assert LMSTUDIO_TESTING_ENV_VAR == "LMSTUDIO_TESTING"
        # Verify the env var is set using the SAME name as the constant
        assert os.environ.get("LMSTUDIO_TESTING") == os.environ.get(LMSTUDIO_TESTING_ENV_VAR)

    @pytest.mark.unit
    def test_get_config_does_not_http_in_testing_mode(self):
        """With LMSTUDIO_TESTING active, get_config() skips HTTP auto-detection.

        This is the integration proof: conftest.py's activation + R-2's capability
        together prevent HTTP calls during test collection.
        """
        from unittest.mock import patch

        from config_main import LMStudioConfig, reset_config

        # Reset to force fresh config creation
        reset_config()

        with patch.object(
            LMStudioConfig, "_get_first_available_model",
            return_value="mock-model",
        ) as mock_detect:
            from config_main import get_config

            config = get_config()
            # With LMSTUDIO_TESTING active, auto-detection must NOT be called
            mock_detect.assert_not_called()
            assert config.lmstudio.default_model is not None

        # Clean up
        reset_config()
