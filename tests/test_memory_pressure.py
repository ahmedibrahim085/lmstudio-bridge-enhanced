"""Tests for memory pressure / OOM handling (M14)."""

import pytest
from unittest.mock import patch, MagicMock


class TestMemoryPressure:
    """Verify proper handling when model loading fails due to insufficient memory."""

    @patch('utils.lms_helper.subprocess.run')
    def test_oom_raises_model_memory_error(self, mock_run):
        """When lms reports insufficient memory, ModelMemoryError should be raised."""
        from utils.lms_helper import LMSHelper
        from llm.exceptions import ModelMemoryError

        def side_effect(cmd, **kwargs):
            result = MagicMock()
            result.stderr = ''

            if cmd[1] == 'ps':
                # Model not loaded
                result.returncode = 0
                result.stdout = '[]'
                return result
            elif cmd[1] == 'load':
                # Loading fails with memory error
                result.returncode = 1
                result.stdout = ''
                result.stderr = 'Error: insufficient memory - model requires approximately 117.19 GB'
                return result
            else:
                result.returncode = 0
                result.stdout = 'ok'
                return result

        mock_run.side_effect = side_effect

        with pytest.raises(ModelMemoryError) as exc_info:
            LMSHelper.load_model("huge-model-70b")

        assert exc_info.value.model_name == "huge-model-70b"
        assert exc_info.value.required_memory == "117.19 GB"

    @patch('utils.lms_helper.subprocess.run')
    def test_oom_keyword_triggers_memory_error(self, mock_run):
        """Memory-related keywords in stderr should trigger ModelMemoryError."""
        from utils.lms_helper import LMSHelper
        from llm.exceptions import ModelMemoryError

        def side_effect(cmd, **kwargs):
            result = MagicMock()
            result.stderr = ''

            if cmd[1] == 'ps':
                result.returncode = 0
                result.stdout = '[]'
                return result
            elif cmd[1] == 'load':
                result.returncode = 1
                result.stdout = ''
                result.stderr = 'Failed: not enough memory available'
                return result
            else:
                result.returncode = 0
                result.stdout = 'ok'
                return result

        mock_run.side_effect = side_effect

        with pytest.raises(ModelMemoryError):
            LMSHelper.load_model("large-model")

    def test_model_fallback_suggests_alternative(self):
        """ModelFallbackManager should suggest alternatives when a model is unavailable."""
        from utils.model_fallback import ModelFallbackManager

        manager = ModelFallbackManager()

        # Mock the internal cache with some downloaded models
        manager._downloaded_models = [
            {"path": "qwen/qwen3-4b", "size_bytes": 4_000_000_000},
            {"path": "mistral-7b", "size_bytes": 7_000_000_000},
        ]
        manager._cache_time = 9999999999  # Far future so cache is valid

        # Model not in downloaded list should not be available
        assert manager.is_model_available("huge-model-70b") is False

        # Find alternatives
        alternatives = manager.find_alternatives("huge-model-70b")
        assert isinstance(alternatives, list)
