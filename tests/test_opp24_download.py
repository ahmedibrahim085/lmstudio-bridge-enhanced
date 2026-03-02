"""Tests for OPP-24: REST model download and status tracking.

Covers:
  - LMSRestClient.download_model() POSTs to download endpoint
  - LMSRestClient.get_download_status() GETs download progress
  - Validation: empty model_key raises ValueError
  - Error handling: 404, 409, network errors -> structured dicts

Test categories (Req 07):
- Happy: Tests 1-3 -- download success, already exists, status progress
- Negative: Tests 4-6 -- 404, empty key, network error
- Edge: Tests 7-8 -- 409 conflict, long model key
- Boundary: Tests 9-10 -- structured dict keys, timeout
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# D-1: Activate testing mode BEFORE any production imports that could trigger
# get_config() -> LMStudioConfig.from_env() -> HTTP auto-detection.
from config.constants import LMSTUDIO_TESTING_ENV_VAR  # noqa: I001
os.environ.setdefault(LMSTUDIO_TESTING_ENV_VAR, "1")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def rest_client():
    """Create LMSRestClient for testing."""
    from utils.lms_helper import LMSRestClient
    return LMSRestClient()


@pytest.fixture
def mock_http(rest_client, monkeypatch):
    """Mock HTTP client to capture POST/GET calls."""
    captured = {"calls": []}

    class MockResponse:
        def __init__(self, status_code=200, json_data=None, text=""):
            self.status_code = status_code
            self._json = json_data or {}
            self.text = text

        def json(self):
            return self._json

    class MockClient:
        def post(self, url, json=None, timeout=None):
            captured["calls"].append(
                {"method": "POST", "url": url, "json": json, "timeout": timeout}
            )
            return captured.get("response", MockResponse())

        def get(self, url, params=None, timeout=None):
            captured["calls"].append(
                {"method": "GET", "url": url, "params": params, "timeout": timeout}
            )
            return captured.get("response", MockResponse())

    monkeypatch.setattr(rest_client, "_get_client", lambda: MockClient())
    return captured


# ---------------------------------------------------------------------------
# Happy Path Tests (1-3)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_download_model_success(rest_client, mock_http):
    """Happy-1: 200 response -> success dict with model key echoed back."""
    mock_http["response"] = type(
        "MockResponse",
        (),
        {"status_code": 200, "json": lambda self: {}, "text": ""},
    )()

    result = rest_client.download_model("org/model")

    assert result["success"] is True
    assert result["model"] == "org/model"


@pytest.mark.unit
def test_download_model_already_exists(rest_client, mock_http):
    """Happy-2: 200 response with already_exists flag -> flag propagated."""
    mock_http["response"] = type(
        "MockResponse",
        (),
        {
            "status_code": 200,
            "json": lambda self: {"already_exists": True},
            "text": "",
        },
    )()

    result = rest_client.download_model("org/model")

    assert result["success"] is True
    assert result.get("already_exists") is True


@pytest.mark.unit
def test_get_download_status_returns_progress(rest_client, mock_http):
    """Happy-3: GET status endpoint -> progress and status fields returned."""
    mock_http["response"] = type(
        "MockResponse",
        (),
        {
            "status_code": 200,
            "json": lambda self: {"progress": 0.5, "status": "downloading"},
            "text": "",
        },
    )()

    result = rest_client.get_download_status("org/model")

    assert result["success"] is True
    assert result["progress"] == 0.5


# ---------------------------------------------------------------------------
# Negative Tests (4-6)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_download_model_not_found(rest_client, mock_http):
    """Negative-4: 404 response -> success is False."""
    mock_http["response"] = type(
        "MockResponse",
        (),
        {"status_code": 404, "json": lambda self: {}, "text": "not found"},
    )()

    result = rest_client.download_model("org/missing-model")

    assert result["success"] is False


@pytest.mark.unit
def test_download_model_empty_key_raises(rest_client):
    """Negative-5: Empty model_key -> ValueError raised immediately."""
    with pytest.raises(ValueError):
        rest_client.download_model("")


@pytest.mark.unit
def test_download_model_network_error(rest_client, monkeypatch):
    """Negative-6: Network error -> success is False with error message in result."""

    class BrokenClient:
        def post(self, url, json=None, timeout=None):
            raise Exception("Connection refused")

    monkeypatch.setattr(rest_client, "_get_client", lambda: BrokenClient())

    result = rest_client.download_model("org/model")

    assert result["success"] is False
    assert "Connection refused" in result.get("message", "")


# ---------------------------------------------------------------------------
# Edge Tests (7-8)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_download_model_conflict_409(rest_client, mock_http):
    """Edge-7: 409 Conflict response -> success is False with conflict indicator."""
    mock_http["response"] = type(
        "MockResponse",
        (),
        {"status_code": 409, "json": lambda self: {}, "text": "conflict"},
    )()

    result = rest_client.download_model("org/model")

    assert result["success"] is False
    # Must signal conflict either via a "conflict" key or a non-empty message
    assert result.get("conflict") is True or result.get("message")


@pytest.mark.unit
def test_download_model_long_key_accepted(rest_client, mock_http):
    """Edge-8: Very long model key -> accepted without error (no truncation)."""
    long_key = "organization/very-long-model-name-with-many-parts-v2.0-GGUF"

    mock_http["response"] = type(
        "MockResponse",
        (),
        {"status_code": 200, "json": lambda self: {}, "text": ""},
    )()

    # Should not raise any exception
    result = rest_client.download_model(long_key)
    assert result["model"] == long_key


# ---------------------------------------------------------------------------
# Boundary Tests (9-10)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_download_model_returns_structured_dict(rest_client, mock_http):
    """Boundary-9: Return value always has required keys: success, model, message."""
    mock_http["response"] = type(
        "MockResponse",
        (),
        {"status_code": 200, "json": lambda self: {}, "text": ""},
    )()

    result = rest_client.download_model("org/model")

    assert "success" in result
    assert "model" in result
    assert "message" in result


@pytest.mark.unit
def test_download_uses_correct_endpoint(rest_client, mock_http):
    """Boundary-10: POST is sent to a URL that contains the download endpoint path."""
    mock_http["response"] = type(
        "MockResponse",
        (),
        {"status_code": 200, "json": lambda self: {}, "text": ""},
    )()

    rest_client.download_model("org/model")

    assert mock_http["calls"], "Expected at least one HTTP call"
    post_call = next(
        (c for c in mock_http["calls"] if c["method"] == "POST"), None
    )
    assert post_call is not None, "Expected a POST call"
    assert "/api/v1/download" in post_call["url"]
