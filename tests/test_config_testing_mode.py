"""Tests for LMSTUDIO_TESTING config mode — skip HTTP auto-detection (R-2)."""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestLMStudioTestingMode:
    """Tests for LMSTUDIO_TESTING env var in LMStudioConfig.from_env()."""

    @pytest.mark.unit
    def test_testing_mode_skips_auto_detect(self, monkeypatch):
        """With LMSTUDIO_TESTING set, _get_first_available_model is NOT called."""
        monkeypatch.setenv("LMSTUDIO_TESTING", "1")
        monkeypatch.delenv("DEFAULT_MODEL", raising=False)

        with patch("config_main.LMStudioConfig._get_first_available_model") as mock_detect:
            from config_main import LMStudioConfig
            config = LMStudioConfig.from_env()
            mock_detect.assert_not_called()

    @pytest.mark.unit
    def test_testing_mode_uses_default_model(self, monkeypatch):
        """With LMSTUDIO_TESTING set, default_model is 'default'."""
        monkeypatch.setenv("LMSTUDIO_TESTING", "1")
        monkeypatch.delenv("DEFAULT_MODEL", raising=False)

        with patch("config_main.LMStudioConfig._get_first_available_model") as mock_detect:
            from config_main import LMStudioConfig
            config = LMStudioConfig.from_env()
            assert config.default_model == "default"

    @pytest.mark.unit
    def test_normal_mode_auto_detects(self, monkeypatch):
        """Without LMSTUDIO_TESTING env var, _get_first_available_model IS called."""
        monkeypatch.delenv("LMSTUDIO_TESTING", raising=False)
        monkeypatch.delenv("DEFAULT_MODEL", raising=False)

        with patch("config_main.LMStudioConfig._get_first_available_model", return_value="some-model") as mock_detect:
            from config_main import LMStudioConfig
            config = LMStudioConfig.from_env()
            mock_detect.assert_called_once()

    @pytest.mark.unit
    def test_explicit_model_overrides_testing_mode(self, monkeypatch):
        """DEFAULT_MODEL env var takes priority even when LMSTUDIO_TESTING is set."""
        monkeypatch.setenv("LMSTUDIO_TESTING", "1")
        monkeypatch.setenv("DEFAULT_MODEL", "my-explicit-model")

        with patch("config_main.LMStudioConfig._get_first_available_model") as mock_detect:
            from config_main import LMStudioConfig
            config = LMStudioConfig.from_env()
            assert config.default_model == "my-explicit-model"
            mock_detect.assert_not_called()

    @pytest.mark.unit
    def test_testing_mode_empty_string(self, monkeypatch):
        """LMSTUDIO_TESTING="" is treated as falsy — auto-detects normally."""
        monkeypatch.setenv("LMSTUDIO_TESTING", "")
        monkeypatch.delenv("DEFAULT_MODEL", raising=False)

        with patch("config_main.LMStudioConfig._get_first_available_model", return_value="detected-model") as mock_detect:
            from config_main import LMStudioConfig
            config = LMStudioConfig.from_env()
            mock_detect.assert_called_once()

    @pytest.mark.unit
    def test_testing_mode_does_not_make_http_calls(self, monkeypatch):
        """With LMSTUDIO_TESTING set, zero HTTP calls are made."""
        monkeypatch.setenv("LMSTUDIO_TESTING", "1")
        monkeypatch.delenv("DEFAULT_MODEL", raising=False)

        with patch("config_main.LMStudioConfig._get_first_available_model") as mock_detect, \
             patch("config_main.requests", create=True) as mock_requests:
            from config_main import LMStudioConfig
            config = LMStudioConfig.from_env()
            mock_detect.assert_not_called()

    @pytest.mark.unit
    def test_testing_mode_zero_string_is_truthy(self, monkeypatch):
        """LMSTUDIO_TESTING='0' is truthy in Python (os.environ.get returns '0')."""
        monkeypatch.setenv("LMSTUDIO_TESTING", "0")
        monkeypatch.delenv("DEFAULT_MODEL", raising=False)

        with patch("config_main.LMStudioConfig._get_first_available_model") as mock_detect:
            from config_main import LMStudioConfig
            config = LMStudioConfig.from_env()
            # "0" is a truthy string in Python — testing mode IS active
            mock_detect.assert_not_called()
            assert config.default_model == "default"
