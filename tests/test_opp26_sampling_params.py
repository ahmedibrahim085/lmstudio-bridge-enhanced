#!/usr/bin/env python3
"""Tests for OPP-26: Advanced Sampling Parameters (min_p, top_k)."""
from unittest.mock import MagicMock

import pytest

from tools.completions import _validate_generation_params


class TestMinPValidation:
    """Tests for min_p parameter validation."""

    def test_valid_min_p_accepted(self):
        """min_p=0.5 passes validation."""
        _validate_generation_params(temperature=0.7, max_tokens=100, min_p=0.5)

    def test_min_p_below_zero_rejected(self):
        """min_p=-0.1 raises ValueError."""
        with pytest.raises(ValueError, match="min_p"):
            _validate_generation_params(temperature=0.7, max_tokens=100, min_p=-0.1)

    def test_min_p_above_one_rejected(self):
        """min_p=1.5 raises ValueError."""
        with pytest.raises(ValueError, match="min_p"):
            _validate_generation_params(temperature=0.7, max_tokens=100, min_p=1.5)

    def test_min_p_none_skips(self):
        """min_p=None does not raise."""
        _validate_generation_params(temperature=0.7, max_tokens=100, min_p=None)

    def test_min_p_boundary_zero(self):
        """min_p=0.0 is valid (lower boundary)."""
        _validate_generation_params(temperature=0.7, max_tokens=100, min_p=0.0)

    def test_min_p_boundary_one(self):
        """min_p=1.0 is valid (upper boundary)."""
        _validate_generation_params(temperature=0.7, max_tokens=100, min_p=1.0)


class TestTopKValidation:
    """Tests for top_k parameter validation."""

    def test_valid_top_k_accepted(self):
        """top_k=40 passes validation."""
        _validate_generation_params(temperature=0.7, max_tokens=100, top_k=40)

    def test_top_k_below_one_rejected(self):
        """top_k=0 raises ValueError."""
        with pytest.raises(ValueError, match="top_k"):
            _validate_generation_params(temperature=0.7, max_tokens=100, top_k=0)

    def test_top_k_above_max_rejected(self):
        """top_k=1001 raises ValueError."""
        with pytest.raises(ValueError, match="top_k"):
            _validate_generation_params(temperature=0.7, max_tokens=100, top_k=1001)

    def test_top_k_none_skips(self):
        """top_k=None does not raise."""
        _validate_generation_params(temperature=0.7, max_tokens=100, top_k=None)


class TestSamplingParamsInPayload:
    """Tests for min_p/top_k in LLMClient method payloads."""

    def _make_client(self):
        """Create LLMClient with mocked session (no real HTTP)."""
        from llm.llm_client import LLMClient

        client = LLMClient.__new__(LLMClient)
        client.model = "test-model"
        client.api_base = "http://localhost:1234/v1"
        client.session = MagicMock()
        client._ensure_model_loaded = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "test"}}]
        }
        mock_response.raise_for_status = MagicMock()
        client.session.post.return_value = mock_response
        return client

    def test_min_p_in_chat_payload(self):
        """min_p=0.1 appears in chat_completion payload."""
        client = self._make_client()
        client.chat_completion(
            messages=[{"role": "user", "content": "hi"}],
            min_p=0.1,
        )
        payload = client.session.post.call_args[1]["json"]
        assert payload["min_p"] == 0.1

    def test_top_k_in_chat_payload(self):
        """top_k=40 appears in chat_completion payload."""
        client = self._make_client()
        client.chat_completion(
            messages=[{"role": "user", "content": "hi"}],
            top_k=40,
        )
        payload = client.session.post.call_args[1]["json"]
        assert payload["top_k"] == 40

    def test_none_not_in_payload(self):
        """None values are NOT included in payload."""
        client = self._make_client()
        client.chat_completion(
            messages=[{"role": "user", "content": "hi"}],
            min_p=None,
            top_k=None,
        )
        payload = client.session.post.call_args[1]["json"]
        assert "min_p" not in payload
        assert "top_k" not in payload

    def test_both_in_payload(self):
        """Both min_p and top_k set → both in payload."""
        client = self._make_client()
        client.chat_completion(
            messages=[{"role": "user", "content": "hi"}],
            min_p=0.05,
            top_k=50,
        )
        payload = client.session.post.call_args[1]["json"]
        assert payload["min_p"] == 0.05
        assert payload["top_k"] == 50
