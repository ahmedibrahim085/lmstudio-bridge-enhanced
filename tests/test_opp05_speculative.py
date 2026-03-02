"""Tests for OPP-05: Speculative decoding hints (compatibility_type + draft_model)."""

import pytest
from unittest.mock import patch, MagicMock

from model_registry.schemas import ModelMetadata, ModelType
from llm.llm_client import LLMClient


@pytest.fixture
def client():
    """Create an LLMClient with mocked config."""
    with patch("llm.http_transport.get_config") as mock_config:
        mock_config.return_value.lmstudio.api_base = "http://localhost:1234"
        mock_config.return_value.lmstudio.default_model = "test-model"
        c = LLMClient()
    return c


@pytest.fixture
def mock_session(client):
    """Mock the client's HTTP session."""
    mock = MagicMock()
    client.session = mock
    return mock


def _make_base_metadata(**overrides):
    """Create a minimal ModelMetadata for testing."""
    defaults = dict(
        model_id="test/model-7b",
        model_type=ModelType.LLM,
        display_name="Test Model",
        publisher="test",
        model_family="test",
        architecture="llama",
    )
    defaults.update(overrides)
    return ModelMetadata(**defaults)


class TestCompatibilityTypeField:
    """Tests for compatibility_type field on ModelMetadata."""

    def test_metadata_compatibility_type_default_none(self):
        """Default value is None."""
        meta = _make_base_metadata()
        assert meta.compatibility_type is None

    def test_metadata_from_api_data_gguf(self):
        """Parses 'gguf' from native API response."""
        data = {
            "key": "test/model-7b",
            "type": "llm",
            "publisher": "test",
            "arch": "llama",
            "compatibility_type": "gguf",
        }
        meta = ModelMetadata.from_api_data(data)
        assert meta.compatibility_type == "gguf"

    def test_metadata_from_api_data_mlx(self):
        """Parses 'mlx' from native API response."""
        data = {
            "key": "test/model-7b",
            "type": "llm",
            "publisher": "test",
            "arch": "llama",
            "compatibility_type": "mlx",
        }
        meta = ModelMetadata.from_api_data(data)
        assert meta.compatibility_type == "mlx"

    def test_metadata_from_api_data_missing(self):
        """None when compatibility_type absent from API data."""
        data = {
            "key": "test/model-7b",
            "type": "llm",
            "publisher": "test",
            "arch": "llama",
        }
        meta = ModelMetadata.from_api_data(data)
        assert meta.compatibility_type is None

    def test_metadata_from_lms_data_with_compatibility_type(self):
        """CLI output includes compatibility_type -> parsed."""
        lms_data = {
            "modelKey": "test/model-7b",
            "type": "llm",
            "publisher": "test",
            "architecture": "llama",
            "displayName": "Test Model",
            "compatibility_type": "gguf",
        }
        meta = ModelMetadata.from_lms_data(lms_data)
        assert meta.compatibility_type == "gguf"

    def test_metadata_from_lms_data_without_compatibility_type(self):
        """CLI output lacks compatibility_type -> None."""
        lms_data = {
            "modelKey": "test/model-7b",
            "type": "llm",
            "publisher": "test",
            "architecture": "llama",
            "displayName": "Test Model",
        }
        meta = ModelMetadata.from_lms_data(lms_data)
        assert meta.compatibility_type is None


class TestSupportsSpeculativeDecoding:
    """Tests for supports_speculative_decoding property."""

    def test_supports_speculative_gguf_true(self):
        """GGUF models support speculative decoding."""
        meta = _make_base_metadata(compatibility_type="gguf")
        assert meta.supports_speculative_decoding is True

    def test_supports_speculative_gguf_case_insensitive(self):
        """'GGUF' (uppercase) also returns True."""
        meta = _make_base_metadata(compatibility_type="GGUF")
        assert meta.supports_speculative_decoding is True

    def test_supports_speculative_mlx_false(self):
        """MLX models do NOT support speculative decoding."""
        meta = _make_base_metadata(compatibility_type="mlx")
        assert meta.supports_speculative_decoding is False

    def test_supports_speculative_none_false(self):
        """None compatibility_type -> does not support."""
        meta = _make_base_metadata(compatibility_type=None)
        assert meta.supports_speculative_decoding is False


class TestSerialization:
    """Tests for to_dict/from_dict roundtrip with compatibility_type."""

    def test_metadata_to_dict_includes_compatibility_type(self):
        """to_dict includes compatibility_type when set."""
        meta = _make_base_metadata(compatibility_type="gguf")
        d = meta.to_dict()
        assert d.get("compatibility_type") == "gguf"

    def test_metadata_from_dict_roundtrip_preserves_compatibility_type(self):
        """from_dict preserves compatibility_type from to_dict output."""
        meta = _make_base_metadata(compatibility_type="mlx")
        d = meta.to_dict()
        restored = ModelMetadata.from_dict(d)
        assert restored.compatibility_type == "mlx"


class TestDraftModel:
    """Tests for draft_model parameter in create_response."""

    def test_create_response_draft_model_in_payload(self, client, mock_session):
        """draft_model present in payload when set."""
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"id": "resp_1", "output": []}
        resp.raise_for_status = MagicMock()
        mock_session.post.return_value = resp

        client.create_response(
            input_text="Hello",
            draft_model="small-model",
        )

        call_kwargs = mock_session.post.call_args
        payload = call_kwargs[1]["json"] if "json" in call_kwargs[1] else call_kwargs.kwargs["json"]
        assert payload["draft_model"] == "small-model"

    def test_create_response_no_draft_model(self, client, mock_session):
        """draft_model absent from payload when None."""
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"id": "resp_1", "output": []}
        resp.raise_for_status = MagicMock()
        mock_session.post.return_value = resp

        client.create_response(input_text="Hello")

        call_kwargs = mock_session.post.call_args
        payload = call_kwargs[1]["json"] if "json" in call_kwargs[1] else call_kwargs.kwargs["json"]
        assert "draft_model" not in payload

    def test_create_response_draft_model_on_non_gguf(self, client, mock_session):
        """draft_model passes through even for non-GGUF (let LM Studio reject)."""
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"id": "resp_1", "output": []}
        resp.raise_for_status = MagicMock()
        mock_session.post.return_value = resp

        client.create_response(
            input_text="Hello",
            draft_model="tiny-model",
        )

        call_kwargs = mock_session.post.call_args
        payload = call_kwargs[1]["json"] if "json" in call_kwargs[1] else call_kwargs.kwargs["json"]
        assert payload["draft_model"] == "tiny-model"


class TestListModelsEnriched:
    """Tests for list_models_enriched including compatibility_type."""

    def test_list_models_enriched_includes_compatibility_type(self, client, mock_session):
        """list_models_enriched returns compatibility_type in dict."""
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = [
            {
                "key": "test/model-7b",
                "type": "llm",
                "publisher": "test",
                "arch": "llama",
                "compatibility_type": "gguf",
                "max_context_length": 4096,
            }
        ]
        resp.raise_for_status = MagicMock()
        mock_session.get.return_value = resp

        result = client.list_models_enriched()
        assert len(result) == 1
        assert result[0]["compatibility_type"] == "gguf"
