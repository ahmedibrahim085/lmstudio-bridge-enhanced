#!/usr/bin/env python3
"""Tests for OPP-22: Single-Model Lookup."""
import time
from unittest.mock import patch

import pytest

from config.constants import LMS_REST_MODELS_CACHE_TTL
from utils.lms_helper import LMSRestClient

SAMPLE_MODELS = [
    {"key": "qwen/qwen3-coder-next", "loaded_instances": [{"id": "inst-1"}]},
    {"key": "mistralai/magistral-small", "loaded_instances": []},
    {"key": "qwen/qwen3-4b", "loaded_instances": [{"id": "inst-2"}, {"id": "inst-3"}]},
]


@pytest.fixture
def client():
    """Create a fresh LMSRestClient for testing."""
    return LMSRestClient(base_url="http://localhost:1234")


class TestGetModel:
    """Tests for LMSRestClient.get_model()."""

    def test_get_model_cache_hit(self, client):
        """Found in valid cache, no HTTP call needed."""
        client._models_cache = SAMPLE_MODELS.copy()
        client._models_cache_time = time.monotonic()

        with patch.object(client, "list_all_models") as mock_fetch:
            result = client.get_model("qwen/qwen3-coder-next")

        assert result is not None
        assert result["key"] == "qwen/qwen3-coder-next"
        mock_fetch.assert_not_called()

    def test_get_model_cache_miss_fetches(self, client):
        """Cache is empty, fetches from API and finds model."""
        assert client._models_cache is None

        with patch.object(client, "list_all_models", return_value=SAMPLE_MODELS):
            result = client.get_model("mistralai/magistral-small")

        assert result is not None
        assert result["key"] == "mistralai/magistral-small"

    def test_get_model_not_found(self, client):
        """Model not in cache or API returns None."""
        client._models_cache = SAMPLE_MODELS.copy()
        client._models_cache_time = time.monotonic()

        result = client.get_model("nonexistent/model")
        assert result is None

    def test_get_model_cache_expired(self, client):
        """Stale cache triggers re-fetch."""
        client._models_cache = SAMPLE_MODELS.copy()
        client._models_cache_time = time.monotonic() - LMS_REST_MODELS_CACHE_TTL - 1

        with patch.object(client, "list_all_models", return_value=SAMPLE_MODELS) as mock_fetch:
            result = client.get_model("qwen/qwen3-coder-next")

        assert result is not None
        assert result["key"] == "qwen/qwen3-coder-next"
        mock_fetch.assert_called_once()

    def test_get_model_key_matching(self, client):
        """Exact key match, not substring."""
        client._models_cache = SAMPLE_MODELS.copy()
        client._models_cache_time = time.monotonic()

        # "qwen/qwen3-4b" should NOT match "qwen/qwen3-4b-thinking"
        result = client.get_model("qwen/qwen3-4b-thinking")
        assert result is None

        # Exact match should work
        result = client.get_model("qwen/qwen3-4b")
        assert result is not None
        assert result["key"] == "qwen/qwen3-4b"

    def test_get_model_empty_string_key(self, client):
        """Empty string key returns None when no model has empty key."""
        client._models_cache = SAMPLE_MODELS.copy()
        client._models_cache_time = time.monotonic()

        result = client.get_model("")
        assert result is None

    def test_get_model_partial_key_no_match(self, client):
        """Partial key 'qwen/qwen3' does not match 'qwen/qwen3-coder-next'."""
        client._models_cache = SAMPLE_MODELS.copy()
        client._models_cache_time = time.monotonic()

        result = client.get_model("qwen/qwen3")
        assert result is None

    def test_get_model_api_returns_none(self, client):
        """When API is unavailable (list_all_models returns None), get_model returns None."""
        assert client._models_cache is None  # No cache

        with patch.object(client, "list_all_models", return_value=None):
            result = client.get_model("qwen/qwen3-coder-next")

        assert result is None


class TestIsModelLoadedRefactored:
    """Tests for refactored is_model_loaded() using get_model()."""

    def test_is_model_loaded_uses_get_model(self, client):
        """is_model_loaded delegates to get_model internally."""
        with patch.object(client, "get_model", return_value=SAMPLE_MODELS[0]) as mock_get:
            result = client.is_model_loaded("qwen/qwen3-coder-next")

        assert result is True
        mock_get.assert_called_once_with("qwen/qwen3-coder-next")

    def test_is_model_loaded_loaded_true(self, client):
        """Model with non-empty loaded_instances returns True."""
        client._models_cache = SAMPLE_MODELS.copy()
        client._models_cache_time = time.monotonic()

        result = client.is_model_loaded("qwen/qwen3-coder-next")
        assert result is True

    def test_is_model_loaded_unloaded_false(self, client):
        """Model with empty loaded_instances returns False."""
        client._models_cache = SAMPLE_MODELS.copy()
        client._models_cache_time = time.monotonic()

        result = client.is_model_loaded("mistralai/magistral-small")
        assert result is False

    def test_is_model_loaded_not_found(self, client):
        """Model not in list returns False (not None, since API is reachable)."""
        with patch.object(client, "get_model", return_value=None):
            with patch.object(client, "list_all_models", return_value=SAMPLE_MODELS):
                result = client.is_model_loaded("nonexistent/model")

        assert result is False

    def test_is_model_loaded_api_unavailable(self, client):
        """API error (list_all_models returns None) -> returns None."""
        with patch.object(client, "get_model", return_value=None):
            with patch.object(client, "list_all_models", return_value=None):
                result = client.is_model_loaded("any/model")

        assert result is None
