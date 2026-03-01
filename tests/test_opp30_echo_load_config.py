#!/usr/bin/env python3
"""Tests for OPP-30: Echo Load Config."""
from unittest.mock import MagicMock, patch

import pytest

from utils.lms_helper import LMSRestClient

SAMPLE_CONFIG = {
    "gpu_offload": "max",
    "context_length": 4096,
    "flash_attention": True,
}

SAMPLE_MODEL_WITH_INSTANCES = {
    "key": "qwen/qwen3-coder-next",
    "loaded_instances": [
        {"id": "inst-old", "config": {"gpu_offload": "none"}},
        {"id": "inst-new", "config": SAMPLE_CONFIG},
    ],
}

SAMPLE_MODEL_NO_INSTANCES = {
    "key": "qwen/qwen3-coder-next",
    "loaded_instances": [],
}


@pytest.fixture
def client():
    """Create a fresh LMSRestClient for testing."""
    return LMSRestClient(base_url="http://localhost:1234")


class TestEchoLoadConfig:
    """Tests for config echo in load_model() return dict."""

    def test_load_returns_config(self, client):
        """Successful load includes config dict from _fetch_model_config."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"instance_id": "inst-new"}

        with patch.object(client, "is_model_loaded", return_value=False):
            with patch.object(client, "_get_client") as mock_client:
                mock_client.return_value.post.return_value = mock_response
                with patch.object(
                    client, "_fetch_model_config", return_value=SAMPLE_CONFIG
                ):
                    result = client.load_model("qwen/qwen3-coder-next")

        assert result["success"] is True
        assert result["config"] == SAMPLE_CONFIG

    def test_already_loaded_returns_config(self, client):
        """already_loaded=True includes config from current instance."""
        with patch.object(client, "is_model_loaded", return_value=True):
            with patch.object(
                client, "_fetch_model_config", return_value=SAMPLE_CONFIG
            ):
                result = client.load_model("qwen/qwen3-coder-next")

        assert result["already_loaded"] is True
        assert result["config"] == SAMPLE_CONFIG

    def test_config_has_expected_fields(self, client):
        """Config dict has gpu/context_length/flash_attention fields."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"instance_id": "inst-new"}

        with patch.object(client, "is_model_loaded", return_value=False):
            with patch.object(client, "_get_client") as mock_client:
                mock_client.return_value.post.return_value = mock_response
                with patch.object(
                    client, "_fetch_model_config", return_value=SAMPLE_CONFIG
                ):
                    result = client.load_model("qwen/qwen3-coder-next")

        config = result["config"]
        assert "gpu_offload" in config
        assert "context_length" in config
        assert "flash_attention" in config

    def test_config_from_latest_instance(self, client):
        """_fetch_model_config uses last loaded_instances entry."""
        with patch.object(client, "invalidate_cache"):
            with patch.object(
                client, "get_model", return_value=SAMPLE_MODEL_WITH_INSTANCES
            ):
                config = client._fetch_model_config("qwen/qwen3-coder-next")

        # Should use the LAST instance (inst-new), not inst-old
        assert config == SAMPLE_CONFIG

    def test_config_none_no_instances(self, client):
        """No loaded instances returns None config."""
        with patch.object(client, "invalidate_cache"):
            with patch.object(
                client, "get_model", return_value=SAMPLE_MODEL_NO_INSTANCES
            ):
                config = client._fetch_model_config("qwen/qwen3-coder-next")

        assert config is None

    def test_config_none_failed_load(self, client):
        """Failed load returns config=None."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch.object(client, "is_model_loaded", return_value=False):
            with patch.object(client, "_get_client") as mock_client:
                mock_client.return_value.post.return_value = mock_response
                result = client.load_model("qwen/qwen3-coder-next")

        assert result["success"] is False
        assert result["config"] is None

    def test_config_none_refetch_fails(self, client):
        """Re-fetch after load fails returns None config."""
        with patch.object(client, "invalidate_cache"):
            with patch.object(client, "get_model", return_value=None):
                config = client._fetch_model_config("qwen/qwen3-coder-next")

        assert config is None

    def test_cache_invalidated_after_load(self, client):
        """Cache cleared after successful load before re-fetch."""
        with patch.object(client, "invalidate_cache") as mock_invalidate:
            with patch.object(
                client, "get_model", return_value=SAMPLE_MODEL_WITH_INSTANCES
            ):
                client._fetch_model_config("qwen/qwen3-coder-next")

        mock_invalidate.assert_called_once()
