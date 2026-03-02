#!/usr/bin/env python3
"""Tests for OPP-27: Advanced model load parameters.

Covers:
  - LMSRestClient.load_model() accepts gpu_layers, max_concurrent_predictions, ttl, draft_model
  - New params appear in POST body when provided
  - Validation: gpu_layers >= -1, max_concurrent_predictions >= 1
  - Backward compat: all new params None → payload unchanged

Test categories (Req 07):
- Happy: Tests 1-4 — each new param present in POST body
- Negative: Tests 5-7 — invalid values raise ValueError
- Edge: Tests 8-9 — all None (backward compat), combined params
- Boundary: Tests 10-12 — boundary values (-1, 0) accepted
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def rest_client():
    """Create LMSRestClient for testing."""
    from utils.lms_helper import LMSRestClient

    return LMSRestClient()


@pytest.fixture
def mock_post(rest_client, monkeypatch):
    """Mock POST to capture request body sent to load endpoint.

    Sets up:
    - is_model_loaded → False (so load proceeds every time)
    - _fetch_model_config → {} (avoids a second real HTTP call)
    - _get_client → a MockClient that records the JSON body of every POST
    """
    captured: dict = {}

    class MockResponse:
        """Minimal httpx-like response for the load endpoint."""

        status_code = 200
        text = '{"instance_id": "test-123"}'

        def json(self):
            return {"instance_id": "test-123"}

    def fake_post(url, json=None, timeout=None):
        captured["url"] = url
        captured["body"] = json
        return MockResponse()

    class MockClient:
        """Minimal httpx client that captures POST calls."""

        def post(self, url, json=None, timeout=None):
            return fake_post(url, json=json, timeout=timeout)

    monkeypatch.setattr(rest_client, "is_model_loaded", lambda key: False)
    monkeypatch.setattr(rest_client, "_fetch_model_config", lambda key: {})
    monkeypatch.setattr(rest_client, "_get_client", lambda: MockClient())

    return captured


# ==============================================================================
# Happy Path — each new param appears in POST body (Tests 1-4)
# ==============================================================================


class TestHappyPath:
    """Happy-path tests: each new parameter is forwarded into the POST body."""

    @pytest.mark.unit
    def test_gpu_layers_in_payload(self, rest_client, mock_post):
        """gpu_layers=35 appears as body['gpu_layers'] == 35 in the load POST."""
        rest_client.load_model("test-model", gpu_layers=35)
        assert mock_post["body"]["gpu_layers"] == 35

    @pytest.mark.unit
    def test_ttl_in_payload(self, rest_client, mock_post):
        """ttl=300 appears as body['ttl'] == 300 in the load POST."""
        rest_client.load_model("test-model", ttl=300)
        assert mock_post["body"]["ttl"] == 300

    @pytest.mark.unit
    def test_draft_model_in_payload(self, rest_client, mock_post):
        """draft_model='small-model' appears as body['draft_model'] in the load POST."""
        rest_client.load_model("test-model", draft_model="small-model")
        assert mock_post["body"]["draft_model"] == "small-model"

    @pytest.mark.unit
    def test_max_concurrent_predictions_in_payload(self, rest_client, mock_post):
        """max_concurrent_predictions=4 appears in the load POST body."""
        rest_client.load_model("test-model", max_concurrent_predictions=4)
        assert mock_post["body"]["max_concurrent_predictions"] == 4


# ==============================================================================
# Negative — invalid values raise ValueError (Tests 5-7)
# ==============================================================================


class TestNegativeCases:
    """Negative tests: invalid parameter values must raise ValueError."""

    @pytest.mark.unit
    def test_gpu_layers_below_minus_one_raises(self, rest_client, mock_post):
        """gpu_layers=-2 is below the minimum of -1 and must raise ValueError."""
        with pytest.raises(ValueError, match="gpu_layers"):
            rest_client.load_model("test-model", gpu_layers=-2)

    @pytest.mark.unit
    def test_max_concurrent_zero_raises(self, rest_client, mock_post):
        """max_concurrent_predictions=0 is below the minimum of 1 and must raise ValueError."""
        with pytest.raises(ValueError, match="max_concurrent_predictions"):
            rest_client.load_model("test-model", max_concurrent_predictions=0)

    @pytest.mark.unit
    def test_max_concurrent_negative_raises(self, rest_client, mock_post):
        """max_concurrent_predictions=-1 is negative and must raise ValueError."""
        with pytest.raises(ValueError, match="max_concurrent_predictions"):
            rest_client.load_model("test-model", max_concurrent_predictions=-1)


# ==============================================================================
# Edge Cases (Tests 8-9)
# ==============================================================================


class TestEdgeCases:
    """Edge-case tests: backward compatibility and combined parameters."""

    @pytest.mark.unit
    def test_all_new_params_none_backward_compat(self, rest_client, mock_post):
        """When all new params are None the POST body contains only the 'model' key.

        Existing params (context_length, flash_attention) are also absent when
        not supplied. The new keys must NOT appear in the body.
        """
        rest_client.load_model(
            "test-model",
            gpu_layers=None,
            max_concurrent_predictions=None,
            ttl=None,
            draft_model=None,
        )
        body = mock_post["body"]
        assert body == {"model": "test-model"}, (
            f"Expected exactly {{'model': 'test-model'}}, got {body}"
        )
        assert "gpu_layers" not in body
        assert "max_concurrent_predictions" not in body
        assert "ttl" not in body
        assert "draft_model" not in body

    @pytest.mark.unit
    def test_combined_params_all_in_payload(self, rest_client, mock_post):
        """All four new params together all appear in the POST body."""
        rest_client.load_model(
            "test-model",
            gpu_layers=16,
            ttl=600,
            draft_model="draft",
            max_concurrent_predictions=2,
        )
        body = mock_post["body"]
        assert body["gpu_layers"] == 16
        assert body["ttl"] == 600
        assert body["draft_model"] == "draft"
        assert body["max_concurrent_predictions"] == 2


# ==============================================================================
# Boundary Values (Tests 10-12)
# ==============================================================================


class TestBoundaryValues:
    """Boundary tests: minimum valid values must be accepted, not rejected."""

    @pytest.mark.unit
    def test_gpu_layers_minus_one_valid(self, rest_client, mock_post):
        """gpu_layers=-1 means 'all GPU layers' and is the minimum valid value."""
        rest_client.load_model("test-model", gpu_layers=-1)
        assert mock_post["body"]["gpu_layers"] == -1

    @pytest.mark.unit
    def test_gpu_layers_zero_valid(self, rest_client, mock_post):
        """gpu_layers=0 means 'CPU only' and must be accepted."""
        rest_client.load_model("test-model", gpu_layers=0)
        assert mock_post["body"]["gpu_layers"] == 0

    @pytest.mark.unit
    def test_ttl_zero_valid(self, rest_client, mock_post):
        """ttl=0 means 'never auto-unload' and must be accepted and forwarded."""
        rest_client.load_model("test-model", ttl=0)
        assert mock_post["body"]["ttl"] == 0
