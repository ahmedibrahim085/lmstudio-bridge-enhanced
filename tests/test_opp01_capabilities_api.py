"""
OPP-01 Capabilities API -- Test Suite

Tests for replacing hardcoded model capabilities with LM Studio's native
REST API (GET /api/v1/models).

All HTTP calls are mocked via unittest.mock -- no LM Studio instance required.
"""

import unittest
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Test 1: NATIVE_MODELS_ENDPOINT constant exists and has correct value
# ---------------------------------------------------------------------------

class TestNativeModelsEndpointConstant(unittest.TestCase):
    def test_native_models_endpoint_defined(self):
        from config.constants import NATIVE_MODELS_ENDPOINT
        self.assertEqual(NATIVE_MODELS_ENDPOINT, "/api/v1/models")


# ---------------------------------------------------------------------------
# Test 2: CapabilitySource enum has LMSTUDIO_API value
# ---------------------------------------------------------------------------

class TestCapabilitySourceEnum(unittest.TestCase):
    def test_lmstudio_api_enum_value_exists(self):
        from model_registry.schemas import CapabilitySource
        self.assertEqual(CapabilitySource.LMSTUDIO_API.value, "lmstudio_api")


# ---------------------------------------------------------------------------
# Tests 3-8: ModelMetadata.from_api_data() parsing
# ---------------------------------------------------------------------------

_MINIMAL_API_PAYLOAD = {
    "key": "qwen/qwen3-coder-30b",
    "type": "llm",
    "publisher": "qwen",
    "arch": "qwen3",
    "compatibility_type": "gguf",
    "quantization": "Q4_K_M",
    "size_bytes": 18500000000,
    "params_string": "30B",
    "max_context_length": 65536,
    "capabilities": {
        "vision": False,
        "trained_for_tool_use": True,
    },
    "loaded_instances": [
        {"instance_id": "inst_abc", "context_length": 32768}
    ],
}


class TestFromApiDataParsing(unittest.TestCase):

    def test_from_api_data_minimal_payload(self):
        from model_registry.schemas import ModelMetadata
        meta = ModelMetadata.from_api_data(_MINIMAL_API_PAYLOAD)
        self.assertEqual(meta.model_id, "qwen/qwen3-coder-30b")
        self.assertEqual(meta.publisher, "qwen")
        self.assertIsNotNone(meta.capabilities)

    def test_from_api_data_vision_model(self):
        from model_registry.schemas import CapabilityScore, ModelMetadata
        data = dict(_MINIMAL_API_PAYLOAD)
        data["capabilities"] = {"vision": True, "trained_for_tool_use": False}
        meta = ModelMetadata.from_api_data(data)
        self.assertIsNotNone(meta.capabilities.vision)
        self.assertIsInstance(meta.capabilities.vision, CapabilityScore)
        self.assertTrue(meta.capabilities.vision.supported)

    def test_from_api_data_long_context_threshold(self):
        from model_registry.schemas import ModelMetadata
        data = dict(_MINIMAL_API_PAYLOAD)
        data["max_context_length"] = 131072  # > 32768
        meta = ModelMetadata.from_api_data(data)
        self.assertIsNotNone(meta.capabilities.long_context)
        self.assertTrue(meta.capabilities.long_context.supported)

        data2 = dict(_MINIMAL_API_PAYLOAD)
        data2["max_context_length"] = 8192  # <= 32768
        meta2 = ModelMetadata.from_api_data(data2)
        self.assertIsNotNone(meta2.capabilities.long_context)
        self.assertFalse(meta2.capabilities.long_context.supported)

    def test_from_api_data_null_fields_do_not_crash(self):
        from model_registry.schemas import ModelMetadata
        sparse = {
            "key": "vendor/some-model",
            "type": "llm",
        }
        try:
            meta = ModelMetadata.from_api_data(sparse)
        except Exception as exc:
            self.fail(f"from_api_data raised {exc} on sparse payload")
            return  # unreachable; satisfies static analysis
        self.assertEqual(meta.model_id, "vendor/some-model")

    def test_from_api_data_embedding_type(self):
        from model_registry.schemas import ModelMetadata, ModelType
        data = dict(_MINIMAL_API_PAYLOAD)
        data["type"] = "embedding"
        data["key"] = "nomic/nomic-embed-text"
        meta = ModelMetadata.from_api_data(data)
        self.assertEqual(meta.model_type, ModelType.EMBEDDING)

    def test_from_api_data_source_is_lmstudio_api(self):
        from model_registry.schemas import CapabilitySource, ModelMetadata
        meta = ModelMetadata.from_api_data(_MINIMAL_API_PAYLOAD)
        self.assertIsNotNone(meta.capabilities.tool_calling)
        self.assertEqual(meta.capabilities.tool_calling.source, CapabilitySource.LMSTUDIO_API)
        self.assertEqual(meta.capabilities.tool_calling.confidence, 1.0)


# ---------------------------------------------------------------------------
# Tests 9-11: LMSIntegration.get_all_models_via_rest()
# ---------------------------------------------------------------------------

_NATIVE_API_RESPONSE = [
    {
        "key": "qwen/qwen3-coder-30b",
        "type": "llm",
        "publisher": "qwen",
        "arch": "qwen3",
        "compatibility_type": "gguf",
        "quantization": "Q4_K_M",
        "size_bytes": 18500000000,
        "params_string": "30B",
        "max_context_length": 65536,
        "capabilities": {
            "vision": False,
            "trained_for_tool_use": True,
        },
        "loaded_instances": [
            {"instance_id": "inst_abc", "context_length": 32768}
        ],
    }
]


class TestGetAllModelsViaRest(unittest.TestCase):

    @patch("httpx.get")
    def test_get_all_models_via_rest_happy_path(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = _NATIVE_API_RESPONSE
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        from model_registry.lms_integration import LMSIntegration
        from model_registry.schemas import ModelMetadata
        result = LMSIntegration.get_all_models_via_rest(base_url="http://localhost:1234")

        self.assertIsNotNone(result)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], ModelMetadata)
        self.assertEqual(result[0].model_id, "qwen/qwen3-coder-30b")

    @patch("httpx.get", side_effect=ConnectionError("refused"))
    def test_get_all_models_via_rest_connection_error(self, mock_get):
        from model_registry.lms_integration import LMSIntegration
        result = LMSIntegration.get_all_models_via_rest(base_url="http://localhost:1234")
        self.assertIsNone(result)

    @patch("httpx.get")
    def test_get_all_models_via_rest_identifies_loaded(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = _NATIVE_API_RESPONSE
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        from model_registry.lms_integration import LMSIntegration
        result = LMSIntegration.get_all_models_via_rest(base_url="http://localhost:1234")

        self.assertIsNotNone(result)
        meta = result[0]
        self.assertIsNotNone(meta.lms_raw_data)
        loaded = meta.lms_raw_data.get("loaded_instances", [])
        self.assertGreater(len(loaded), 0)


# ---------------------------------------------------------------------------
# Test 12: ModelValidator._fetch_models() tries native endpoint first
# ---------------------------------------------------------------------------

class TestFetchModelsUsesNativeEndpoint(unittest.TestCase):

    def test_fetch_models_uses_native_endpoint(self):
        import asyncio

        native_response = MagicMock()
        native_response.raise_for_status.return_value = None
        native_response.json.return_value = [
            {"key": "qwen/qwen3-coder-30b"},
        ]

        urls_called = []

        async def fake_get(url, **kwargs):
            urls_called.append(url)
            return native_response

        mock_client = MagicMock()
        mock_client.get = fake_get

        async def aenter(self_inner):
            return mock_client

        async def aexit(self_inner, *args):
            return False

        mock_client.__aenter__ = aenter
        mock_client.__aexit__ = aexit

        async def inner():
            from llm.model_validator import ModelValidator
            validator = ModelValidator(api_base="http://localhost:1234/v1")
            with patch("httpx.AsyncClient", return_value=mock_client):
                models = await validator._fetch_models()
            return models

        models = asyncio.run(inner())

        self.assertIsInstance(models, list)
        native_called = any("/api/v1/models" in url for url in urls_called)
        self.assertTrue(native_called, f"Native endpoint not called. URLs: {urls_called}")


# ---------------------------------------------------------------------------
# Tests 13-14: LLMClient.list_models_enriched()
# ---------------------------------------------------------------------------

class TestListModelsEnriched(unittest.TestCase):

    @patch("requests.Session.get")
    def test_list_models_enriched_returns_metadata(self, mock_get):
        native_response = MagicMock()
        native_response.status_code = 200
        native_response.json.return_value = _NATIVE_API_RESPONSE
        native_response.raise_for_status.return_value = None

        mock_get.return_value = native_response

        from llm.llm_client import LLMClient
        client = LLMClient(api_base="http://localhost:1234/v1")
        result = client.list_models_enriched()

        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        first = result[0]
        self.assertIsInstance(first, dict)
        has_id = "model_id" in first or "key" in first
        self.assertTrue(has_id, f"No model identifier in result dict: {first}")

    @patch("requests.Session.get")
    def test_list_models_enriched_falls_back(self, mock_get):
        native_fail = MagicMock()
        native_fail.raise_for_status.side_effect = Exception("not found")

        fallback_response = MagicMock()
        fallback_response.status_code = 200
        fallback_response.json.return_value = {"data": [{"id": "qwen/qwen3-coder-30b"}]}
        fallback_response.raise_for_status.return_value = None

        mock_get.side_effect = [native_fail, fallback_response]

        from llm.llm_client import LLMClient
        client = LLMClient(api_base="http://localhost:1234/v1")
        result = client.list_models_enriched()

        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        self.assertIn("model_id", result[0])


# ---------------------------------------------------------------------------
# Tests 15-16: ModelRegistry.list_available_models() REST-first, CLI fallback
# ---------------------------------------------------------------------------

class TestRegistryRestFirst(unittest.TestCase):

    @patch("model_registry.lms_integration.LMSIntegration.get_all_models_via_rest")
    @patch("model_registry.lms_integration.LMSIntegration.get_loaded_model_ids")
    def test_registry_uses_rest_when_available(self, mock_loaded, mock_rest):
        from model_registry.schemas import ModelMetadata, ModelType
        mock_meta = ModelMetadata(
            model_id="qwen/qwen3-coder-30b",
            model_type=ModelType.LLM,
            display_name="Qwen3 Coder 30B",
            publisher="qwen",
            model_family="qwen3",
            architecture="qwen3",
        )
        mock_rest.return_value = [mock_meta]
        mock_loaded.return_value = []

        from model_registry.cache import CacheManager
        from model_registry.registry import ModelRegistry
        registry = ModelRegistry.__new__(ModelRegistry)
        registry.cache = MagicMock(spec=CacheManager)
        registry.cache.get_cached_model_ids.return_value = []
        registry.cache.get_stats.return_value = MagicMock(to_dict=lambda: {})
        registry._lms_checked = False

        result = registry.list_available_models()

        mock_rest.assert_called_once()
        self.assertIn("qwen/qwen3-coder-30b", result["available"])

    @patch("model_registry.lms_integration.LMSIntegration.get_all_model_ids")
    @patch("model_registry.lms_integration.LMSIntegration.get_loaded_model_ids")
    @patch("model_registry.lms_integration.LMSIntegration.get_all_models_via_rest")
    @patch("model_registry.lms_integration.LMSIntegration.check_prerequisites")
    def test_registry_falls_back_to_cli(
        self, mock_check, mock_rest, mock_loaded, mock_cli_ids
    ):
        mock_rest.return_value = None
        mock_cli_ids.return_value = ["qwen/qwen3-coder-30b"]
        mock_loaded.return_value = []
        mock_check.return_value = None

        from model_registry.cache import CacheManager
        from model_registry.registry import ModelRegistry
        registry = ModelRegistry.__new__(ModelRegistry)
        registry.cache = MagicMock(spec=CacheManager)
        registry.cache.get_cached_model_ids.return_value = []
        registry.cache.get_stats.return_value = MagicMock(to_dict=lambda: {})
        registry._lms_checked = False

        result = registry.list_available_models()

        mock_cli_ids.assert_called_once()
        self.assertIn("qwen/qwen3-coder-30b", result["available"])


    @patch("model_registry.lms_integration.LMSIntegration.get_all_models_via_rest")
    @patch("model_registry.lms_integration.LMSIntegration.get_loaded_model_ids")
    def test_registry_rest_path_filters_embeddings(self, mock_loaded, mock_rest):
        """REST path must exclude embedding models when include_embeddings=False."""
        from model_registry.schemas import ModelMetadata, ModelType
        llm_meta = ModelMetadata(
            model_id="qwen/qwen3-coder-30b",
            model_type=ModelType.LLM,
            display_name="Qwen3 Coder 30B",
            publisher="qwen",
            model_family="qwen3",
            architecture="qwen3",
        )
        embed_meta = ModelMetadata(
            model_id="nomic/nomic-embed-text",
            model_type=ModelType.EMBEDDING,
            display_name="Nomic Embed Text",
            publisher="nomic",
            model_family="nomic",
            architecture="nomic",
        )
        mock_rest.return_value = [llm_meta, embed_meta]
        mock_loaded.return_value = []

        from model_registry.cache import CacheManager
        from model_registry.registry import ModelRegistry
        registry = ModelRegistry.__new__(ModelRegistry)
        registry.cache = MagicMock(spec=CacheManager)
        registry.cache.get_cached_model_ids.return_value = []
        registry.cache.get_stats.return_value = MagicMock(to_dict=lambda: {})
        registry._lms_checked = False

        # Default include_embeddings=False should exclude embedding models
        result = registry.list_available_models(include_embeddings=False)
        self.assertIn("qwen/qwen3-coder-30b", result["available"])
        self.assertNotIn("nomic/nomic-embed-text", result["available"])

        # include_embeddings=True should include both
        result_all = registry.list_available_models(include_embeddings=True)
        self.assertIn("qwen/qwen3-coder-30b", result_all["available"])
        self.assertIn("nomic/nomic-embed-text", result_all["available"])


if __name__ == "__main__":
    unittest.main()
