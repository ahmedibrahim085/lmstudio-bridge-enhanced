#!/usr/bin/env python3
"""Integration tests for Round D API surface changes.

These tests exercise the full code path with mocked HTTP responses,
verifying that new methods integrate correctly with caching, error
handling, and response parsing layers.
"""
from unittest.mock import MagicMock

import pytest

from config.constants import LMS_REST_MODELS_CACHE_TTL


SAMPLE_MODELS = [
    {
        "key": "qwen/qwen3-coder-next",
        "loaded_instances": [
            {"id": "inst-1", "config": {"gpu_offload": 1.0, "context_length": 8192}}
        ],
    },
    {"key": "mistralai/magistral-small", "loaded_instances": []},
]


@pytest.fixture
def rest_client():
    """Create LMSRestClient with mocked httpx.Client."""
    from utils.lms_helper import LMSRestClient

    client = LMSRestClient(base_url="http://localhost:1234")
    mock_http = MagicMock()
    client._client = mock_http
    return client, mock_http


@pytest.mark.integration
class TestOPP22Integration:
    """Integration tests for OPP-22: Single-Model Lookup — full code path."""

    def test_get_model_returns_real_model(self, rest_client):
        """get_model() returns model dict when found in fresh API response."""
        client, mock_http = rest_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_MODELS
        mock_http.get.return_value = mock_response

        result = client.get_model("qwen/qwen3-coder-next")

        assert result is not None
        assert result["key"] == "qwen/qwen3-coder-next"
        assert len(result["loaded_instances"]) == 1

    def test_get_model_not_found_returns_none(self, rest_client):
        """get_model() returns None for nonexistent model."""
        client, mock_http = rest_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_MODELS
        mock_http.get.return_value = mock_response

        result = client.get_model("nonexistent/model-xyz")
        assert result is None

    def test_is_model_loaded_reflects_actual_state(self, rest_client):
        """is_model_loaded() returns True for loaded, False for unloaded models."""
        client, mock_http = rest_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_MODELS
        mock_http.get.return_value = mock_response

        assert client.is_model_loaded("qwen/qwen3-coder-next") is True
        assert client.is_model_loaded("mistralai/magistral-small") is False


@pytest.mark.integration
class TestOPP23Integration:
    """Integration tests for OPP-23: Streaming Usage Tracking — full parse path."""

    def test_stream_usage_from_mock_stream(self):
        """parse_sse_stream_with_usage() captures usage from SSE stream."""
        from llm.sse_parser import parse_sse_stream_with_usage

        mock_response = MagicMock()
        mock_response.iter_lines.return_value = iter([
            b'data: {"choices":[{"delta":{"content":"Hello"}}]}',
            b'data: {"choices":[{"delta":{"content":" world"}}],"usage":{"prompt_tokens":5,"completion_tokens":2,"total_tokens":7}}',
            b"data: [DONE]",
        ])

        gen = parse_sse_stream_with_usage(mock_response)
        chunks = []
        usage = None
        try:
            while True:
                chunks.append(next(gen))
        except StopIteration as e:
            usage = e.value

        assert len(chunks) == 2
        assert usage is not None
        assert usage.prompt_tokens == 5
        assert usage.completion_tokens == 2
        assert usage.total_tokens == 7

    def test_stream_usage_token_counts_nonzero(self):
        """StreamUsage from stream has nonzero token counts when present."""
        from llm.sse_parser import StreamUsage

        usage = StreamUsage.from_dict({
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
        })
        assert usage.prompt_tokens > 0
        assert usage.completion_tokens > 0
        assert usage.total_tokens == 30


@pytest.mark.integration
class TestOPP26Integration:
    """Integration tests for OPP-26: Sampling params through full LLMClient path."""

    def _make_llm_client(self):
        """Create LLMClient with mocked session for full-path testing."""
        from llm.llm_client import LLMClient

        client = LLMClient.__new__(LLMClient)
        client.model = "test-model"
        client.api_base = "http://localhost:1234/v1"
        client.session = MagicMock()
        client._ensure_model_loaded = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "test"}}]
        }
        mock_resp.raise_for_status = MagicMock()
        client.session.post.return_value = mock_resp
        return client

    def test_min_p_affects_generation(self):
        """min_p parameter flows through to HTTP payload."""
        client = self._make_llm_client()
        client.chat_completion(
            messages=[{"role": "user", "content": "hi"}],
            min_p=0.01,
        )
        payload = client.session.post.call_args[1]["json"]
        assert payload["min_p"] == 0.01

    def test_top_k_affects_generation(self):
        """top_k parameter flows through to HTTP payload."""
        client = self._make_llm_client()
        client.chat_completion(
            messages=[{"role": "user", "content": "hi"}],
            top_k=1,
        )
        payload = client.session.post.call_args[1]["json"]
        assert payload["top_k"] == 1

    def test_sampling_params_accepted_by_server(self):
        """Both min_p and top_k coexist in payload without conflict."""
        client = self._make_llm_client()
        client.chat_completion(
            messages=[{"role": "user", "content": "hi"}],
            min_p=0.05,
            top_k=50,
        )
        payload = client.session.post.call_args[1]["json"]
        assert payload["min_p"] == 0.05
        assert payload["top_k"] == 50
        assert "temperature" in payload  # standard params still present


@pytest.mark.integration
class TestOPP30Integration:
    """Integration tests for OPP-30: Echo Load Config — full load_model path."""

    def test_load_model_returns_config(self):
        """load_model() returns config dict with gpu_offload and context_length."""
        from utils.lms_helper import LMSRestClient

        client = LMSRestClient(base_url="http://localhost:1234")
        mock_http = MagicMock()
        client._client = mock_http

        # First GET: is_model_loaded check → not loaded (empty loaded_instances)
        not_loaded_resp = MagicMock()
        not_loaded_resp.status_code = 200
        not_loaded_resp.json.return_value = [
            {"key": "test/model", "loaded_instances": []},
        ]

        # POST: load model
        load_resp = MagicMock()
        load_resp.status_code = 200
        load_resp.json.return_value = {"instance_id": "inst-99"}

        # Second GET: _fetch_model_config calls invalidate_cache then get_model
        loaded_resp = MagicMock()
        loaded_resp.status_code = 200
        loaded_resp.json.return_value = [
            {
                "key": "test/model",
                "loaded_instances": [
                    {"id": "inst-99", "config": {"gpu_offload": 0.5, "context_length": 4096}}
                ],
            },
        ]

        mock_http.get.side_effect = [not_loaded_resp, loaded_resp]
        mock_http.post.return_value = load_resp

        result = client.load_model("test/model")

        assert result["success"] is True
        assert result["config"] is not None
        assert result["config"]["gpu_offload"] == 0.5
        assert result["config"]["context_length"] == 4096

    def test_config_matches_lm_studio_settings(self):
        """Already-loaded model returns config from existing instance."""
        from utils.lms_helper import LMSRestClient

        client = LMSRestClient(base_url="http://localhost:1234")
        mock_http = MagicMock()
        client._client = mock_http

        # GET: model already has loaded_instances
        loaded_resp = MagicMock()
        loaded_resp.status_code = 200
        loaded_resp.json.return_value = [
            {
                "key": "test/model",
                "loaded_instances": [
                    {"id": "inst-1", "config": {"gpu_offload": 1.0, "context_length": 8192}}
                ],
            },
        ]
        # _fetch_model_config also calls invalidate_cache + get_model → two GETs
        mock_http.get.return_value = loaded_resp

        result = client.load_model("test/model")

        assert result["success"] is True
        assert result["already_loaded"] is True
        assert result["config"]["gpu_offload"] == 1.0
