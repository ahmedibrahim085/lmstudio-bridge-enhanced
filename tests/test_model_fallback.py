#!/usr/bin/env python3
"""
Tests for model fallback manager and LMS search/download features.
"""

import pytest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.model_fallback import (
    ModelFallbackManager,
    ModelAlternative,
    get_fallback_manager
)
from tools.lms_cli_tools import (
    lms_search_models,
    lms_download_model,
    lms_list_downloaded_models,
    lms_resolve_model
)


class TestModelFallbackManager:
    """Tests for ModelFallbackManager class."""

    @pytest.fixture
    def mock_downloaded_models(self):
        """Sample downloaded models for testing."""
        return [
            {
                "modelKey": "qwen/qwen3-coder-30b",
                "displayName": "Qwen3 Coder 30B",
                "sizeBytes": 30000000000,
                "trainedForToolUse": True,
                "maxContextLength": 32768
            },
            {
                "modelKey": "qwen/qwen3-4b-thinking-2507",
                "displayName": "Qwen3 4B Thinking",
                "sizeBytes": 4000000000,
                "trainedForToolUse": True,
                "maxContextLength": 32768
            },
            {
                "modelKey": "mistralai/mistral-small-3.2",
                "displayName": "Mistral Small 3.2",
                "sizeBytes": 4500000000,
                "trainedForToolUse": True,
                "maxContextLength": 32768
            },
            {
                "modelKey": "meta/llama-3-8b-instruct",
                "displayName": "Llama 3 8B Instruct",
                "sizeBytes": 8000000000,
                "trainedForToolUse": False,
                "maxContextLength": 8192
            }
        ]

    @patch('utils.model_fallback.LMSHelper')
    def test_is_model_available_true(self, mock_lms, mock_downloaded_models):
        """Test checking if an available model is found."""
        mock_lms.list_downloaded_models.return_value = mock_downloaded_models

        manager = ModelFallbackManager()
        result = manager.is_model_available("qwen/qwen3-coder-30b")

        assert result is True

    @patch('utils.model_fallback.LMSHelper')
    def test_is_model_available_false(self, mock_lms, mock_downloaded_models):
        """Test checking if a missing model returns False."""
        mock_lms.list_downloaded_models.return_value = mock_downloaded_models

        manager = ModelFallbackManager()
        result = manager.is_model_available("deepseek/deepseek-coder-33b")

        assert result is False

    @patch('utils.model_fallback.LMSHelper')
    def test_find_alternatives_coding_model(self, mock_lms, mock_downloaded_models):
        """Test finding alternatives for a coding model."""
        mock_lms.list_downloaded_models.return_value = mock_downloaded_models

        manager = ModelFallbackManager()
        alternatives = manager.find_alternatives("deepseek/deepseek-coder-33b")

        # Should find qwen3-coder-30b as a good alternative
        assert len(alternatives) > 0
        model_keys = [alt.model_key for alt in alternatives]
        assert "qwen/qwen3-coder-30b" in model_keys

    @patch('utils.model_fallback.LMSHelper')
    def test_find_alternatives_reasoning_model(self, mock_lms, mock_downloaded_models):
        """Test finding alternatives for a reasoning model."""
        mock_lms.list_downloaded_models.return_value = mock_downloaded_models

        manager = ModelFallbackManager()
        alternatives = manager.find_alternatives("openai/o1-preview")

        # Should find thinking model as alternative
        assert len(alternatives) > 0
        model_keys = [alt.model_key for alt in alternatives]
        assert "qwen/qwen3-4b-thinking-2507" in model_keys

    @patch('utils.model_fallback.LMSHelper')
    def test_find_alternatives_with_task_type(self, mock_lms, mock_downloaded_models):
        """Test finding alternatives with task_type hint."""
        mock_lms.list_downloaded_models.return_value = mock_downloaded_models

        manager = ModelFallbackManager()
        alternatives = manager.find_alternatives(
            "some/random-model",
            task_type="coding"
        )

        # Should prioritize coding models
        assert len(alternatives) > 0
        # First alternative should be coding-capable
        first = alternatives[0]
        assert "coding capability" in first.reasons or first.trained_for_tool_use

    @patch('utils.model_fallback.LMSHelper')
    def test_resolve_model_available(self, mock_lms, mock_downloaded_models):
        """Test resolving an available model."""
        mock_lms.list_downloaded_models.return_value = mock_downloaded_models

        manager = ModelFallbackManager()
        resolved, status, alternatives = manager.resolve_model("qwen/qwen3-coder-30b")

        assert resolved == "qwen/qwen3-coder-30b"
        assert status == "available"
        assert alternatives is None

    @patch('utils.model_fallback.LMSHelper')
    def test_resolve_model_auto_fallback(self, mock_lms, mock_downloaded_models):
        """Test resolving with auto_fallback=True."""
        mock_lms.list_downloaded_models.return_value = mock_downloaded_models

        manager = ModelFallbackManager()
        resolved, status, alternatives = manager.resolve_model(
            "deepseek/deepseek-coder-33b",
            auto_fallback=True
        )

        # Should auto-select a fallback
        assert resolved != "deepseek/deepseek-coder-33b"
        assert status == "fallback"
        assert alternatives is not None

    @patch('utils.model_fallback.LMSHelper')
    def test_resolve_model_manual_fallback(self, mock_lms, mock_downloaded_models):
        """Test resolving with auto_fallback=False."""
        mock_lms.list_downloaded_models.return_value = mock_downloaded_models

        manager = ModelFallbackManager()
        resolved, status, alternatives = manager.resolve_model(
            "deepseek/deepseek-coder-33b",
            auto_fallback=False
        )

        # Should return original model with alternatives list
        assert resolved == "deepseek/deepseek-coder-33b"
        assert status == "unavailable"
        assert alternatives is not None
        assert len(alternatives) > 0

    @patch('utils.model_fallback.LMSHelper')
    def test_format_alternatives_message(self, mock_lms, mock_downloaded_models):
        """Test formatting alternatives message."""
        mock_lms.list_downloaded_models.return_value = mock_downloaded_models

        manager = ModelFallbackManager()
        alternatives = manager.find_alternatives("deepseek/deepseek-coder-33b")
        message = manager.format_alternatives_message(
            "deepseek/deepseek-coder-33b",
            alternatives
        )

        assert "not downloaded" in message
        assert "alternatives" in message.lower()


class TestLMSCLITools:
    """Tests for LMS CLI MCP tools."""

    def test_lms_search_models_not_supported(self):
        """Test that search returns 'not supported' error (LMS CLI limitation)."""
        result = lms_search_models("qwen coder")

        assert result["success"] is False
        assert "not supported" in result["error"].lower()
        assert result["query"] == "qwen coder"
        assert "alternatives" in result
        assert len(result["alternatives"]) > 0

    @patch('tools.lms_cli_tools.LMSHelper')
    def test_lms_download_model_already_downloaded(self, mock_lms):
        """Test downloading an already downloaded model."""
        mock_lms.is_installed.return_value = True
        mock_lms.is_model_downloaded.return_value = True

        result = lms_download_model("qwen/qwen3-coder-30b")

        assert result["success"] is True
        assert result["alreadyDownloaded"] is True

    @patch('tools.lms_cli_tools.LMSHelper')
    def test_lms_download_model_new_download(self, mock_lms):
        """Test downloading a new model."""
        mock_lms.is_installed.return_value = True
        mock_lms.is_model_downloaded.return_value = False
        mock_lms.download_model.return_value = (True, "Download started")

        result = lms_download_model("qwen/qwen3-coder-30b", wait=False)

        assert result["success"] is True
        assert result["alreadyDownloaded"] is False
        assert result["isBackground"] is True

    @patch('tools.lms_cli_tools.LMSHelper')
    def test_lms_list_downloaded_models_success(self, mock_lms):
        """Test listing downloaded models."""
        mock_lms.is_installed.return_value = True
        mock_lms.list_downloaded_models.return_value = [
            {"modelKey": "model1", "sizeBytes": 1000000000},
            {"modelKey": "model2", "sizeBytes": 2000000000}
        ]

        result = lms_list_downloaded_models()

        assert result["success"] is True
        assert result["count"] == 2
        assert result["totalSizeBytes"] == 3000000000

    @patch('tools.lms_cli_tools.LMSHelper')
    @patch('tools.lms_cli_tools.get_fallback_manager')
    def test_lms_resolve_model_available(self, mock_get_manager, mock_lms):
        """Test resolving an available model."""
        mock_lms.is_installed.return_value = True

        mock_manager = MagicMock()
        mock_manager.resolve_model.return_value = (
            "qwen/qwen3-coder-30b",
            "available",
            None
        )
        mock_get_manager.return_value = mock_manager

        result = lms_resolve_model("qwen/qwen3-coder-30b")

        assert result["success"] is True
        assert result["status"] == "available"
        assert result["resolved_model"] == "qwen/qwen3-coder-30b"

    @patch('tools.lms_cli_tools.LMSHelper')
    @patch('tools.lms_cli_tools.get_fallback_manager')
    def test_lms_resolve_model_with_fallback(self, mock_get_manager, mock_lms):
        """Test resolving with auto fallback."""
        mock_lms.is_installed.return_value = True

        mock_alternative = ModelAlternative(
            model_key="qwen/qwen3-coder-30b",
            display_name="Qwen3 Coder",
            score=5,
            reasons=["coding capability"],
            trained_for_tool_use=True
        )
        mock_manager = MagicMock()
        mock_manager.resolve_model.return_value = (
            "qwen/qwen3-coder-30b",
            "fallback",
            [mock_alternative]
        )
        mock_get_manager.return_value = mock_manager

        result = lms_resolve_model(
            "deepseek/deepseek-coder-33b",
            auto_fallback=True
        )

        assert result["success"] is True
        assert result["status"] == "fallback"
        assert result["resolved_model"] == "qwen/qwen3-coder-30b"


class TestModelAlternative:
    """Tests for ModelAlternative dataclass."""

    def test_create_alternative(self):
        """Test creating a ModelAlternative."""
        alt = ModelAlternative(
            model_key="test/model",
            display_name="Test Model",
            score=5,
            reasons=["reason1", "reason2"],
            size_bytes=1000000000,
            trained_for_tool_use=True,
            max_context_length=32768
        )

        assert alt.model_key == "test/model"
        assert alt.score == 5
        assert len(alt.reasons) == 2
        assert alt.trained_for_tool_use is True


class TestGetFallbackManager:
    """Tests for singleton fallback manager."""

    def test_get_fallback_manager_singleton(self):
        """Test that get_fallback_manager returns singleton."""
        manager1 = get_fallback_manager()
        manager2 = get_fallback_manager()

        assert manager1 is manager2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
