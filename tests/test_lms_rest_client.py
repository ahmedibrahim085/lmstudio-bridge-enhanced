#!/usr/bin/env python3
"""
Tests for OPP-04 — Model Lifecycle REST API.

LMSRestClient replaces subprocess CLI calls with LM Studio native REST endpoints.
All tests use mocked httpx to avoid real network calls.

Coverage:
- Constants (3 tests)
- LMSRestClient list/status (9 tests)
- LMSRestClient load/unload (7 tests)
- LMSHelper dispatch (4 tests)
"""

from unittest.mock import MagicMock, patch

import pytest

# ==============================================================================
# Constants Tests (3)
# ==============================================================================

class TestConstants:
    """Verify new endpoint constants exist with correct values."""

    def test_lms_load_model_endpoint_is_correct(self):
        from config.constants import LMS_LOAD_MODEL_ENDPOINT
        assert LMS_LOAD_MODEL_ENDPOINT == "/api/v1/models/load"

    def test_lms_unload_model_endpoint_is_correct(self):
        from config.constants import LMS_UNLOAD_MODEL_ENDPOINT
        assert LMS_UNLOAD_MODEL_ENDPOINT == "/api/v1/models/unload"

    def test_lms_rest_load_timeout_is_reasonable(self):
        from config.constants import LMS_REST_LOAD_TIMEOUT
        assert 60 <= LMS_REST_LOAD_TIMEOUT <= 300


# ==============================================================================
# LMSRestClient — list_all_models / is_server_available (9 tests)
# ==============================================================================

class TestLMSRestClientListStatus:
    """Unit tests for LMSRestClient.list_all_models(), is_model_loaded(), is_server_available()."""

    def _make_client(self):
        from utils.lms_helper import LMSRestClient
        return LMSRestClient(base_url="http://localhost:1234")

    def test_list_all_models_happy_path(self):
        """GET /api/v1/models 200 → returns model list."""
        client = self._make_client()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"key": "qwen/qwen3-coder-30b", "loaded_instances": [{"instance_id": "inst-1"}]},
            {"key": "mistral/mistral-7b", "loaded_instances": []},
        ]

        with patch("httpx.get", return_value=mock_response) as mock_get:
            result = client.list_all_models()

        assert result is not None
        assert len(result) == 2
        assert result[0]["key"] == "qwen/qwen3-coder-30b"
        mock_get.assert_called_once()

    def test_list_all_models_connection_error_returns_none(self):
        """ConnectionError → returns None (not raises)."""
        import httpx
        client = self._make_client()

        with patch("httpx.get", side_effect=httpx.ConnectError("refused")):
            result = client.list_all_models()

        assert result is None

    def test_list_all_models_timeout_returns_none(self):
        """Timeout → returns None (not raises)."""
        import httpx
        client = self._make_client()

        with patch("httpx.get", side_effect=httpx.TimeoutException("timed out")):
            result = client.list_all_models()

        assert result is None

    def test_is_model_loaded_via_rest_loaded_present(self):
        """Model with non-empty loaded_instances → True."""
        client = self._make_client()

        mock_models = [
            {"key": "qwen/qwen3-coder-30b", "loaded_instances": [{"instance_id": "inst-1"}]},
        ]

        with patch.object(client, "list_all_models", return_value=mock_models):
            result = client.is_model_loaded("qwen/qwen3-coder-30b")

        assert result is True

    def test_is_model_loaded_via_rest_empty_instances(self):
        """Model with empty loaded_instances → False."""
        client = self._make_client()

        mock_models = [
            {"key": "mistral/mistral-7b", "loaded_instances": []},
        ]

        with patch.object(client, "list_all_models", return_value=mock_models):
            result = client.is_model_loaded("mistral/mistral-7b")

        assert result is False

    def test_is_model_loaded_via_rest_model_not_in_list(self):
        """Model key not in list → False."""
        client = self._make_client()

        mock_models = [
            {"key": "other/model", "loaded_instances": [{"instance_id": "inst-2"}]},
        ]

        with patch.object(client, "list_all_models", return_value=mock_models):
            result = client.is_model_loaded("qwen/qwen3-coder-30b")

        assert result is False

    def test_is_model_loaded_via_rest_api_failure(self):
        """API failure (list_all_models returns None) → None."""
        client = self._make_client()

        with patch.object(client, "list_all_models", return_value=None):
            result = client.is_model_loaded("qwen/qwen3-coder-30b")

        assert result is None

    def test_is_server_available_returns_true_on_200(self):
        """GET /api/v1/models 200 → True."""
        client = self._make_client()

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("httpx.get", return_value=mock_response):
            result = client.is_server_available()

        assert result is True

    def test_is_server_available_returns_false_on_error(self):
        """ConnectionError → False (not raises)."""
        import httpx
        client = self._make_client()

        with patch("httpx.get", side_effect=httpx.ConnectError("refused")):
            result = client.is_server_available()

        assert result is False


# ==============================================================================
# LMSRestClient — load_model / unload_model (7 tests)
# ==============================================================================

class TestLMSRestClientLoadUnload:
    """Unit tests for LMSRestClient.load_model() and unload_model()."""

    def _make_client(self):
        from utils.lms_helper import LMSRestClient
        return LMSRestClient(base_url="http://localhost:1234")

    def test_load_model_happy_path(self):
        """POST /api/v1/models/load 200 → success=True with instance_id."""
        client = self._make_client()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"instance_id": "inst-abc"}

        with patch.object(client, "is_model_loaded", return_value=False):
            with patch("httpx.post", return_value=mock_response):
                result = client.load_model("qwen/qwen3-coder-30b")

        assert result["success"] is True
        assert result["instance_id"] == "inst-abc"
        assert result["already_loaded"] is False
        assert result["memory_error"] is False

    def test_load_model_already_loaded_skips(self):
        """is_model_loaded=True → no POST made, returns already_loaded=True."""
        client = self._make_client()

        with patch.object(client, "is_model_loaded", return_value=True):
            with patch("httpx.post") as mock_post:
                result = client.load_model("qwen/qwen3-coder-30b")

        assert result["success"] is True
        assert result["already_loaded"] is True
        mock_post.assert_not_called()

    def test_load_model_memory_error(self):
        """POST 400 with 'insufficient memory' text → memory_error=True."""
        client = self._make_client()

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Insufficient memory: model requires 24GB VRAM"

        with patch.object(client, "is_model_loaded", return_value=False):
            with patch("httpx.post", return_value=mock_response):
                result = client.load_model("big/model")

        assert result["success"] is False
        assert result["memory_error"] is True

    def test_load_model_connection_error(self):
        """ConnectionError → success=False, memory_error=False."""
        import httpx
        client = self._make_client()

        with patch.object(client, "is_model_loaded", return_value=False):
            with patch("httpx.post", side_effect=httpx.ConnectError("refused")):
                result = client.load_model("qwen/qwen3-coder-30b")

        assert result["success"] is False
        assert result["memory_error"] is False
        assert result["instance_id"] is None

    def test_load_model_with_context_length(self):
        """context_length is forwarded in POST body."""
        client = self._make_client()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"instance_id": "inst-xyz"}

        with patch.object(client, "is_model_loaded", return_value=False):
            with patch("httpx.post", return_value=mock_response) as mock_post:
                client.load_model("qwen/qwen3-coder-30b", context_length=8192)

        call_kwargs = mock_post.call_args
        body = call_kwargs[1]["json"] if call_kwargs[1] else call_kwargs[0][1]
        assert body["context_length"] == 8192
        assert body["model"] == "qwen/qwen3-coder-30b"

    def test_unload_model_happy_path(self):
        """POST /api/v1/models/unload 200 → True."""
        client = self._make_client()

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("httpx.post", return_value=mock_response):
            result = client.unload_model("inst-abc")

        assert result is True

    def test_unload_model_failure(self):
        """POST /api/v1/models/unload 404 → False."""
        client = self._make_client()

        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("httpx.post", return_value=mock_response):
            result = client.unload_model("inst-nonexistent")

        assert result is False


# ==============================================================================
# LMSHelper dispatch tests (4)
# ==============================================================================

class TestLMSHelperDispatch:
    """Verify LMSHelper uses REST-first dispatch with subprocess fallback."""

    @pytest.fixture(autouse=True)
    def reset_rest_client_cache(self):
        """Reset _rest_client class cache between tests."""
        from utils.lms_helper import LMSHelper
        original = LMSHelper._rest_client
        yield
        LMSHelper._rest_client = original

    def test_lms_helper_load_uses_rest_when_available(self):
        """When REST client is available, load_model() uses it and returns True."""
        from utils.lms_helper import LMSHelper, LMSRestClient

        mock_rest = MagicMock(spec=LMSRestClient)
        mock_rest.load_model.return_value = {
            "success": True,
            "instance_id": "inst-1",
            "already_loaded": False,
            "memory_error": False,
            "message": "loaded",
        }

        with patch.object(LMSHelper, "_get_rest_client", return_value=mock_rest):
            with patch.object(LMSHelper, "is_model_loaded", return_value=False):
                with patch.object(LMSHelper, "is_installed", return_value=True):
                    with patch("utils.lms_helper.validate_model_name"):
                        result = LMSHelper.load_model("qwen/qwen3-coder-30b")

        assert result is True
        mock_rest.load_model.assert_called_once_with("qwen/qwen3-coder-30b")

    def test_lms_helper_load_falls_back_to_subprocess(self):
        """When REST client is unavailable, load_model() falls back to subprocess."""
        from utils.lms_helper import LMSHelper

        with patch.object(LMSHelper, "_get_rest_client", return_value=None):
            with patch.object(LMSHelper, "is_model_loaded", return_value=False):
                with patch.object(LMSHelper, "is_installed", return_value=True):
                    with patch("utils.lms_helper.validate_model_name"):
                        with patch("subprocess.run") as mock_run:
                            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
                            result = LMSHelper.load_model("qwen/qwen3-coder-30b")

        assert result is True
        mock_run.assert_called_once()

    def test_lms_helper_is_model_loaded_uses_rest(self):
        """is_model_loaded() tries REST first; returns REST result if non-None."""
        from utils.lms_helper import LMSHelper, LMSRestClient

        mock_rest = MagicMock(spec=LMSRestClient)
        mock_rest.is_model_loaded.return_value = True

        with patch.object(LMSHelper, "_get_rest_client", return_value=mock_rest):
            result = LMSHelper.is_model_loaded("qwen/qwen3-coder-30b")

        assert result is True
        mock_rest.is_model_loaded.assert_called_once_with("qwen/qwen3-coder-30b")

    def test_lms_helper_list_loaded_uses_rest(self):
        """list_loaded_models() uses REST and normalizes to legacy format."""
        from utils.lms_helper import LMSHelper, LMSRestClient

        mock_rest = MagicMock(spec=LMSRestClient)
        mock_rest.list_all_models.return_value = [
            {
                "key": "qwen/qwen3-coder-30b",
                "loaded_instances": [{"instance_id": "inst-1"}],
            }
        ]

        with patch.object(LMSHelper, "_get_rest_client", return_value=mock_rest):
            result = LMSHelper.list_loaded_models()

        assert result is not None
        assert len(result) == 1
        assert result[0]["identifier"] == "qwen/qwen3-coder-30b"
        assert result[0]["modelKey"] == "qwen/qwen3-coder-30b"
        assert result[0]["status"] == "loaded"
        assert result[0]["instance_id"] == "inst-1"
