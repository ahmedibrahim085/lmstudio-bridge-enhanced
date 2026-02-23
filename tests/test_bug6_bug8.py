"""Tests for BUG 6 (generic Exception) and BUG 8 (dict response handling).

BUG 6: lms_helper.ensure_model_loaded_with_verification raises bare Exception
       instead of custom LLMError types.

BUG 8: llm_client.list_models_enriched doesn't handle dict-wrapped responses
       from native /api/v1/models endpoint ({"models": [...]}).
"""
import logging

import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# BUG 6: Generic Exception → custom LLMError
# ---------------------------------------------------------------------------

class TestBug6CustomExceptions:
    """Verify ensure_model_loaded_with_verification raises LLMError, not Exception."""

    def test_load_failure_raises_llm_error(self):
        """When load_model returns False, should raise LLMError (not bare Exception)."""
        from llm.exceptions import LLMError
        from utils.lms_helper import LMSHelper

        with patch.object(LMSHelper, "is_model_loaded", return_value=False):
            with patch.object(LMSHelper, "load_model", return_value=False):
                with pytest.raises(LLMError, match="Failed to load"):
                    LMSHelper.ensure_model_loaded_with_verification("test-model")

    def test_verification_failure_raises_llm_error(self):
        """When verify_model_loaded returns False, should raise LLMError."""
        from llm.exceptions import LLMError
        from utils.lms_helper import LMSHelper

        with patch.object(LMSHelper, "is_model_loaded", return_value=False):
            with patch.object(LMSHelper, "load_model", return_value=True):
                with patch.object(LMSHelper, "verify_model_loaded", return_value=False):
                    with patch("time.sleep"):  # skip MODEL_LOADING_DELAY
                        with pytest.raises(LLMError, match="verification failed"):
                            LMSHelper.ensure_model_loaded_with_verification("test-model")

    def test_load_failure_not_bare_exception(self):
        """Ensure we DON'T raise bare Exception (the old behavior)."""
        from llm.exceptions import LLMError
        from utils.lms_helper import LMSHelper

        with patch.object(LMSHelper, "is_model_loaded", return_value=False):
            with patch.object(LMSHelper, "load_model", return_value=False):
                try:
                    LMSHelper.ensure_model_loaded_with_verification("test-model")
                    pytest.fail("Should have raised")
                except LLMError:
                    pass  # correct
                except Exception as e:
                    pytest.fail(
                        f"Raised bare Exception instead of LLMError: {type(e).__name__}: {e}"
                    )


# ---------------------------------------------------------------------------
# BUG 8: Dict response handling in list_models_enriched
# ---------------------------------------------------------------------------

class TestBug8DictResponse:
    """Verify list_models_enriched handles dict-wrapped native API responses."""

    def _make_client(self):
        """Create LLMClient with mocked config."""
        with patch("llm.llm_client.get_config") as mock_cfg:
            mock_cfg.return_value.lmstudio.api_base = "http://localhost:1234/v1"
            mock_cfg.return_value.lmstudio.default_model = "test-model"
            from llm.llm_client import LLMClient
            client = LLMClient()
        return client

    def test_dict_wrapped_models_response(self):
        """Native API returning {"models": [...]} must be handled correctly."""
        client = self._make_client()

        native_data = {
            "models": [
                {
                    "key": "qwen/qwen3-coder-next",
                    "type": "llm",
                    "publisher": "qwen",
                    "arch": "qwen3",
                    "max_context_length": 32768,
                    "capabilities": {"tool_calling": True},
                    "loaded_instances": [],
                    "size_bytes": 18000000000,
                    "quantization": "q4_k_m",
                    "compatibility_type": "gguf",
                }
            ]
        }

        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = native_data

        client.session.get = MagicMock(return_value=resp)

        result = client.list_models_enriched()

        assert len(result) == 1
        assert result[0]["model_id"] == "qwen/qwen3-coder-next"
        assert result[0]["type"] == "llm"

    def test_list_response_still_works(self):
        """Direct list response (old format) must still work."""
        client = self._make_client()

        native_data = [
            {
                "key": "meta/llama-3.1-8b",
                "type": "llm",
                "publisher": "meta",
            }
        ]

        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = native_data

        client.session.get = MagicMock(return_value=resp)

        result = client.list_models_enriched()

        assert len(result) == 1
        assert result[0]["model_id"] == "meta/llama-3.1-8b"

    def test_empty_dict_falls_back(self):
        """Empty dict response should fall back to /v1/models."""
        client = self._make_client()

        native_resp = MagicMock()
        native_resp.raise_for_status = MagicMock()
        native_resp.json.return_value = {"models": []}

        fallback_resp = MagicMock()
        fallback_resp.raise_for_status = MagicMock()
        fallback_resp.json.return_value = {"data": [{"id": "fallback-model"}]}

        call_count = 0

        def fake_get(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if "api/v1/models" in url:
                return native_resp
            return fallback_resp

        client.session.get = MagicMock(side_effect=fake_get)

        result = client.list_models_enriched()

        # Should have fallen back to /v1/models
        assert any(m.get("model_id") == "fallback-model" for m in result)
