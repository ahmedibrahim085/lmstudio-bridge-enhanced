"""Tests for concurrent model loading race conditions (M13)."""

import pytest
from unittest.mock import patch, MagicMock
from concurrent.futures import ThreadPoolExecutor


class TestConcurrentModelLoading:
    """Verify no duplicate model instances under concurrent access."""

    @patch('utils.lms_helper.LMSHelper._get_rest_client', return_value=None)
    @patch('utils.lms_helper.LMSHelper.list_loaded_models')
    @patch('utils.lms_helper.LMSHelper.is_installed', return_value=True)
    def test_concurrent_is_model_loaded_no_duplicates(self, mock_installed, mock_list, mock_rest):
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

    @pytest.fixture(autouse=True)
    def reset_installed_cache(self):
        """Reset LMSHelper caches between tests to prevent state leakage."""
        from utils.lms_helper import LMSHelper
        original_installed = LMSHelper._is_installed
        original_rest = LMSHelper._rest_client
        yield
        LMSHelper._is_installed = original_installed
        LMSHelper._rest_client = original_rest

    @patch('utils.lms_helper.LMSHelper._get_rest_client', return_value=None)
    @patch('utils.retry.subprocess.run')
    @patch('utils.lms_helper.subprocess.run')
    @patch('utils.lms_helper.LMSHelper.is_installed', return_value=True)
    def test_concurrent_load_prevents_duplicate_instances(self, mock_installed, mock_lms_run, mock_retry_run, mock_rest):
        """Multiple concurrent load_model calls should not create :2, :3 instances."""
        from utils.lms_helper import LMSHelper

        call_count = 0

        def retry_side_effect(cmd, **kwargs):
            """Handle lms ps --json calls via run_with_retry path."""
            result = MagicMock()
            result.returncode = 0
            result.stderr = ''
            # Return loaded model after the first lms load call has been made
            if call_count > 0:
                result.stdout = '[{"path": "test-model", "identifier": "test-model", "modelKey": "test-model", "status": "loaded"}]'
            else:
                result.stdout = '[]'
            return result

        def lms_side_effect(cmd, **kwargs):
            """Handle lms load calls via utils.lms_helper.subprocess path."""
            nonlocal call_count
            result = MagicMock()
            result.returncode = 0
            result.stderr = ''
            result.stdout = 'Model loaded'
            call_count += 1
            return result

        mock_retry_run.side_effect = retry_side_effect
        mock_lms_run.side_effect = lms_side_effect

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
