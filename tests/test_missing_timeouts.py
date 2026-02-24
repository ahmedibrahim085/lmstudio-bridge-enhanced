"""Tests for HTTP timeout enforcement on model-listing endpoints.

Verifies that list_models(), list_models_enriched(), and get_model_info()
pass timeout=MODEL_LIST_TIMEOUT to session.get().
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


def _get_timeout_constant():
    """Import MODEL_LIST_TIMEOUT from constants (added in Fix 4)."""
    from config.constants import MODEL_LIST_TIMEOUT
    return MODEL_LIST_TIMEOUT


def _make_client():
    """Create an LLMClient with a mocked session."""
    from llm.llm_client import LLMClient

    with patch.object(LLMClient, "__init__", lambda self, **kw: None):
        client = LLMClient.__new__(LLMClient)

    client.api_base = "http://localhost:1234/v1"
    client.session = MagicMock()
    client._owns_session = False

    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": [{"id": "test-model"}]}
    mock_response.raise_for_status = MagicMock()
    client.session.get.return_value = mock_response

    return client


class TestModelListTimeouts:
    """All 3 model-listing methods must pass timeout to session.get()."""

    def test_list_models_passes_timeout(self):
        """list_models() must pass timeout=MODEL_LIST_TIMEOUT."""
        timeout = _get_timeout_constant()
        client = _make_client()
        client.list_models()

        client.session.get.assert_called_once()
        _, kwargs = client.session.get.call_args
        assert kwargs.get("timeout") == timeout

    def test_list_models_enriched_passes_timeout(self):
        """list_models_enriched() must pass timeout=MODEL_LIST_TIMEOUT."""
        timeout = _get_timeout_constant()
        client = _make_client()

        # Enriched endpoint returns list shape
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"key": "test-model", "type": "llm"}]
        mock_response.raise_for_status = MagicMock()
        client.session.get.return_value = mock_response

        client.list_models_enriched()

        client.session.get.assert_called_once()
        _, kwargs = client.session.get.call_args
        assert kwargs.get("timeout") == timeout

    def test_get_model_info_passes_timeout(self):
        """get_model_info() must pass timeout=MODEL_LIST_TIMEOUT."""
        timeout = _get_timeout_constant()
        client = _make_client()
        client.get_model_info()

        client.session.get.assert_called_once()
        _, kwargs = client.session.get.call_args
        assert kwargs.get("timeout") == timeout
