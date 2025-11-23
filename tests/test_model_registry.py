#!/usr/bin/env python3
"""
Tests for Model Capability Registry.

These tests validate the model registry functionality including:
- LMS CLI integration
- Caching
- Research engine
- MCP tools
"""

import pytest
import os
import sys
import tempfile
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from model_registry import (
    # Schemas
    ModelMetadata,
    ModelCapabilities,
    CapabilityScore,
    BenchmarkData,
    RegistryStats,
    ModelType,
    CapabilitySource,
    ResearchStatus,
    # LMS Integration
    LMSIntegration,
    LMSNotInstalledError,
    # Cache
    CacheManager,
    # Research
    ModelResearcher,
    ResearchResult,
    apply_research_to_metadata,
    # Registry
    ModelRegistry,
    get_registry,
    reset_registry,
    # MCP Tools
    list_available_models,
    get_model_capabilities,
    refresh_model_registry,
    get_best_tool_calling_model,
    TOOL_SCHEMAS
)


class TestSchemas:
    """Tests for data schemas."""

    def test_capability_score_creation(self):
        """Test creating a capability score."""
        score = CapabilityScore(
            supported=0.933,
            confidence=0.95,
            source=CapabilitySource.WEB_RESEARCH,
            details="BFCL score"
        )
        assert score.supported == 0.933
        assert score.confidence == 0.95
        assert score.source == CapabilitySource.WEB_RESEARCH

    def test_capability_score_serialization(self):
        """Test serializing and deserializing capability score."""
        score = CapabilityScore(
            supported=True,
            confidence=1.0,
            source=CapabilitySource.LMS_METADATA
        )
        data = score.to_dict()
        restored = CapabilityScore.from_dict(data)
        assert restored.supported == score.supported
        assert restored.confidence == score.confidence

    def test_model_metadata_from_lms_data(self):
        """Test creating metadata from LMS CLI data."""
        lms_data = {
            "modelKey": "qwen/qwen3-coder-30b",
            "type": "llm",
            "displayName": "Qwen3 Coder 30B",
            "publisher": "qwen",
            "architecture": "qwen3_moe",
            "paramsString": "30B",
            "maxContextLength": 262144,
            "trainedForToolUse": True,
            "vision": False
        }
        metadata = ModelMetadata.from_lms_data(lms_data)
        assert metadata.model_id == "qwen/qwen3-coder-30b"
        assert metadata.size_billions == 30.0
        assert metadata.capabilities.tool_calling is not None
        assert metadata.capabilities.tool_calling.supported is True

    def test_parse_params_string(self):
        """Test parsing parameter strings."""
        assert ModelMetadata._parse_params_string("30B") == 30.0
        assert ModelMetadata._parse_params_string("8B") == 8.0
        assert ModelMetadata._parse_params_string("300M") == 0.3
        assert ModelMetadata._parse_params_string("160x19B") == 160 * 19
        assert ModelMetadata._parse_params_string("") is None

    def test_extract_model_family(self):
        """Test extracting model family from model ID."""
        assert ModelMetadata._extract_model_family("qwen/qwen3-coder-30b", "") == "qwen3"
        assert ModelMetadata._extract_model_family("mistralai/magistral-small", "") == "mistral"
        assert ModelMetadata._extract_model_family("google/gemma-3-12b", "") == "gemma"


class TestCacheManager:
    """Tests for cache manager."""

    def test_cache_save_and_load(self):
        """Test saving and loading cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = os.path.join(tmpdir, "test_cache.json")
            cache = CacheManager(cache_path)

            # Create test metadata
            metadata = ModelMetadata(
                model_id="test/model-1",
                model_type=ModelType.LLM,
                display_name="Test Model",
                publisher="test",
                model_family="test",
                architecture="test"
            )

            # Save
            cache.save({"test/model-1": metadata})

            # Load
            loaded = cache.load()
            assert "test/model-1" in loaded
            assert loaded["test/model-1"].display_name == "Test Model"

    def test_cache_update_model(self):
        """Test updating a single model in cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = os.path.join(tmpdir, "test_cache.json")
            cache = CacheManager(cache_path)

            metadata = ModelMetadata(
                model_id="test/model-1",
                model_type=ModelType.LLM,
                display_name="Test Model",
                publisher="test",
                model_family="test",
                architecture="test"
            )

            cache.update_model(metadata)

            loaded = cache.load()
            assert "test/model-1" in loaded

    def test_cache_remove_model(self):
        """Test removing a model from cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = os.path.join(tmpdir, "test_cache.json")
            cache = CacheManager(cache_path)

            metadata = ModelMetadata(
                model_id="test/model-1",
                model_type=ModelType.LLM,
                display_name="Test Model",
                publisher="test",
                model_family="test",
                architecture="test"
            )

            cache.update_model(metadata)
            assert cache.remove_model("test/model-1") is True

            loaded = cache.load()
            assert "test/model-1" not in loaded

    def test_cache_sync_with_available(self):
        """Test syncing cache with available models."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = os.path.join(tmpdir, "test_cache.json")
            cache = CacheManager(cache_path)

            # Add initial models
            for i in range(3):
                metadata = ModelMetadata(
                    model_id=f"test/model-{i}",
                    model_type=ModelType.LLM,
                    display_name=f"Test Model {i}",
                    publisher="test",
                    model_family="test",
                    architecture="test"
                )
                cache.update_model(metadata)

            # Sync - model-0 removed, model-3 added
            result = cache.sync_with_available(
                available_ids=["test/model-1", "test/model-2", "test/model-3"],
                new_metadata={
                    "test/model-3": ModelMetadata(
                        model_id="test/model-3",
                        model_type=ModelType.LLM,
                        display_name="Test Model 3",
                        publisher="test",
                        model_family="test",
                        architecture="test"
                    )
                }
            )

            assert "test/model-0" in result["removed"]
            assert "test/model-3" in result["added"]


class TestResearcher:
    """Tests for model researcher."""

    def test_lookup_known_benchmarks(self):
        """Test looking up known benchmark data."""
        researcher = ModelResearcher(web_search_enabled=False)
        data = researcher._lookup_known_benchmarks(
            "qwen/qwen3-coder-30b",
            "qwen3"
        )
        assert data is not None
        assert "bfcl_score" in data
        assert data["bfcl_score"] == 0.933

    def test_lookup_glm_benchmarks(self):
        """Test GLM model benchmark lookup."""
        researcher = ModelResearcher(web_search_enabled=False)
        data = researcher._lookup_known_benchmarks("glm-4", "glm")
        assert data is not None
        assert data["bfcl_score"] == 0.906

    @pytest.mark.asyncio
    async def test_research_model(self):
        """Test researching a model."""
        researcher = ModelResearcher(web_search_enabled=False)

        metadata = ModelMetadata(
            model_id="qwen/qwen3-coder-30b",
            model_type=ModelType.LLM,
            display_name="Qwen3 Coder 30B",
            publisher="qwen",
            model_family="qwen3",
            architecture="qwen3_moe"
        )

        result = await researcher.research_model(metadata)
        assert result.success
        assert result.capabilities is not None
        assert "tool_use" in result.recommended_for or "agents" in result.recommended_for


class TestLMSIntegration:
    """Tests for LMS CLI integration."""

    def test_is_installed(self):
        """Test checking if LMS CLI is installed."""
        # Reset cache first
        LMSIntegration.reset_cache()
        result = LMSIntegration.is_installed()
        # Should be True in the test environment
        assert isinstance(result, bool)

    @pytest.mark.skipif(
        not LMSIntegration.is_installed(),
        reason="LMS CLI not installed"
    )
    def test_get_all_model_ids(self):
        """Test getting all model IDs."""
        model_ids = LMSIntegration.get_all_model_ids()
        assert isinstance(model_ids, list)
        assert len(model_ids) > 0

    @pytest.mark.skipif(
        not LMSIntegration.is_installed(),
        reason="LMS CLI not installed"
    )
    def test_get_loaded_model_ids(self):
        """Test getting loaded model IDs."""
        loaded_ids = LMSIntegration.get_loaded_model_ids()
        assert isinstance(loaded_ids, list)


class TestMCPTools:
    """Tests for MCP tool functions."""

    @pytest.mark.skipif(
        not LMSIntegration.is_installed(),
        reason="LMS CLI not installed"
    )
    def test_list_available_models(self):
        """Test list_available_models tool."""
        result = list_available_models()
        assert result["success"] is True
        assert "available" in result
        assert "loaded" in result
        assert "unknown" in result
        assert isinstance(result["available"], list)

    @pytest.mark.skipif(
        not LMSIntegration.is_installed(),
        reason="LMS CLI not installed"
    )
    def test_get_model_capabilities_valid(self):
        """Test get_model_capabilities with valid model."""
        # First get available models
        available = list_available_models()
        if available["success"] and available["available"]:
            model_id = available["available"][0]
            result = get_model_capabilities(model_id)
            assert result["success"] is True
            assert result["model_id"] == model_id
            assert "capabilities" in result

    def test_get_model_capabilities_invalid(self):
        """Test get_model_capabilities with invalid model."""
        result = get_model_capabilities("")
        assert result["success"] is False
        assert result["error_code"] == "invalid_argument"

    def test_tool_schemas_defined(self):
        """Test that tool schemas are defined."""
        assert "list_available_models" in TOOL_SCHEMAS
        assert "get_model_capabilities" in TOOL_SCHEMAS
        assert "refresh_model_registry" in TOOL_SCHEMAS


class TestModelRegistry:
    """Tests for main ModelRegistry class."""

    @pytest.mark.skipif(
        not LMSIntegration.is_installed(),
        reason="LMS CLI not installed"
    )
    def test_registry_list_models(self):
        """Test listing models through registry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = os.path.join(tmpdir, "test_cache.json")
            registry = ModelRegistry(cache_path=cache_path)

            result = registry.list_available_models()
            assert "available" in result
            assert "loaded" in result
            assert len(result["available"]) > 0

    @pytest.mark.skipif(
        not LMSIntegration.is_installed(),
        reason="LMS CLI not installed"
    )
    def test_registry_get_capabilities(self):
        """Test getting capabilities through registry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = os.path.join(tmpdir, "test_cache.json")
            registry = ModelRegistry(cache_path=cache_path)

            # Get first available model
            models = registry.list_available_models()
            if models["available"]:
                model_id = models["available"][0]
                caps = registry.get_model_capabilities(model_id)
                assert caps is not None
                assert "model_id" in caps
                assert "capabilities" in caps


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
