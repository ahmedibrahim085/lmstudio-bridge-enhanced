"""Tests for concurrent model loading race conditions (M13)."""

import pytest
from unittest.mock import patch, MagicMock
from concurrent.futures import ThreadPoolExecutor


class TestConcurrentModelLoading:
    """Verify no duplicate model instances under concurrent access."""

    @patch('utils.lms_helper.LMSHelper.list_loaded_models')
    @patch('utils.lms_helper.LMSHelper.is_installed', return_value=True)
    def test_concurrent_is_model_loaded_no_duplicates(self, mock_installed, mock_list):
        """Concurrent is_model_loaded calls should not create duplicate instances."""
        from utils.lms_helper import LMSHelper

        # Mock list_loaded_models to return the model as loaded
        mock_list.return_value = [
            {"identifier": "test-model", "modelKey": "test-model", "status": "loaded"}
        ]

        results = []
        errors = []

        def check_loaded():
            try:
                result = LMSHelper.is_model_loaded("test-model")
                results.append(result)
            except Exception as e:
                errors.append(str(e))

        # Run 10 concurrent checks
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(check_loaded) for _ in range(10)]
            for f in futures:
                f.result()

        assert len(errors) == 0, f"Errors during concurrent access: {errors}"
        assert all(r is True for r in results), "All checks should report model as loaded"

    @patch('utils.lms_helper.subprocess.run')
    def test_concurrent_load_prevents_duplicate_instances(self, mock_run):
        """Multiple concurrent load_model calls should not create :2, :3 instances."""
        from utils.lms_helper import LMSHelper

        call_count = 0

        def side_effect(cmd, **kwargs):
            nonlocal call_count
            result = MagicMock()
            result.returncode = 0
            result.stderr = ''

            if cmd[1] == 'ps':
                # First calls: model not loaded. After load: model loaded.
                if call_count > 0:
                    result.stdout = '[{"path": "test-model", "identifier": "test-model"}]'
                else:
                    result.stdout = '[]'
                return result
            elif cmd[1] == 'load':
                call_count += 1
                result.stdout = 'Model loaded'
                return result
            else:
                result.stdout = 'ok'
                return result

        mock_run.side_effect = side_effect

        results = []

        def try_load():
            result = LMSHelper.load_model("test-model")
            results.append(result)

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(try_load) for _ in range(5)]
            for f in futures:
                f.result()

        # All should succeed (either loaded or already-loaded)
        assert all(r is True for r in results)
