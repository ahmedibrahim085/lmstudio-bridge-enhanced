#!/usr/bin/env python3
"""
OPP-07: Mocked unit tests for model_registry/ schemas and cache modules.

Covers:
- Group 1: ModelMetadata factory methods (from_lms_data, from_api_data)
- Group 2: _parse_params_string, _estimate_vram_gb, _is_thinking_model,
           _extract_model_family static helpers
- Group 3: Serialization roundtrips (CapabilityScore, BenchmarkData,
           ModelCapabilities, ModelMetadata)
- Group 4: Enum values and RegistryStats.to_dict()
- Group 5: CacheManager (path resolution, load/save, corruption recovery,
           get_stats, export/import, sync delta)

All tests are self-contained — no LMS CLI, no network, no running services.
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure project root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from model_registry.cache import CacheManager
from model_registry.schemas import (
    BenchmarkData,
    CapabilityScore,
    CapabilitySource,
    ModelCapabilities,
    ModelMetadata,
    ModelType,
    RegistryStats,
    ResearchStatus,
)

# ---------------------------------------------------------------------------
# Helpers — minimal valid ModelMetadata factory
# ---------------------------------------------------------------------------

def _make_metadata(
    model_id: str = "test/model-a",
    model_type: ModelType = ModelType.LLM,
) -> ModelMetadata:
    """Return a minimal but valid ModelMetadata instance."""
    return ModelMetadata(
        model_id=model_id,
        model_type=model_type,
        display_name=model_id,
        publisher="test-publisher",
        model_family="test-family",
        architecture="test-arch",
    )


# ===========================================================================
# Group 1 — ModelMetadata factory methods
# ===========================================================================


class TestSchemas:
    """Tests for ModelMetadata factory constructors and static helpers."""

    # -----------------------------------------------------------------------
    # from_lms_data
    # -----------------------------------------------------------------------

    def test_model_metadata_from_lms_data(self):
        """Create ModelMetadata from mock LMS CLI JSON; assert key fields."""
        lms_data = {
            "modelKey": "qwen/qwen3-coder-30b",
            "type": "llm",
            "displayName": "Qwen3 Coder 30B",
            "publisher": "qwen",
            "architecture": "qwen3_moe",
            "paramsString": "30B",
            "maxContextLength": 131072,
            "trainedForToolUse": True,
            "vision": False,
            "sizeBytes": 17 * 1024 ** 3,
            "quantization": {"name": "Q4_K_M"},
        }
        m = ModelMetadata.from_lms_data(lms_data)

        assert m.model_id == "qwen/qwen3-coder-30b"
        assert m.model_type == ModelType.LLM
        assert m.display_name == "Qwen3 Coder 30B"
        assert m.publisher == "qwen"
        assert m.model_family == "qwen3"
        assert m.size_billions == 30.0
        assert m.quantization == "Q4_K_M"
        assert m.max_context_length == 131072
        # Tool calling capability must be parsed from trainedForToolUse
        assert m.capabilities.tool_calling is not None
        assert m.capabilities.tool_calling.supported is True
        assert m.capabilities.tool_calling.source == CapabilitySource.LMS_METADATA
        # Vision capability: False (not None)
        assert m.capabilities.vision is not None
        assert m.capabilities.vision.supported is False
        # Coding inferred from "coder" in model_id
        assert m.capabilities.coding is not None
        assert m.capabilities.coding.supported is True

    def test_model_metadata_from_lms_data_embedding(self):
        """from_lms_data with type='embedding' produces ModelType.EMBEDDING."""
        lms_data = {
            "modelKey": "nomic/nomic-embed-text-v1",
            "type": "embedding",
            "displayName": "Nomic Embed Text v1",
            "publisher": "nomic",
            "architecture": "bert",
            "paramsString": "137M",
            "maxContextLength": 8192,
        }
        m = ModelMetadata.from_lms_data(lms_data)

        assert m.model_type == ModelType.EMBEDDING
        assert m.size_billions == pytest.approx(0.137, abs=0.001)

    # -----------------------------------------------------------------------
    # from_api_data
    # -----------------------------------------------------------------------

    def test_model_metadata_from_api_data(self):
        """Create ModelMetadata from native REST API format (snake_case keys)."""
        api_data = {
            "key": "meta-llama/llama-3-8b",
            "type": "llm",
            "arch": "llama3",
            "publisher": "meta",
            "params_string": "8B",
            "max_context_length": 8192,
            "size_bytes": 5 * 1024 ** 3,
            "quantization": "Q4_K_M",
            "capabilities": {
                "trained_for_tool_use": True,
                "vision": False,
            },
        }
        m = ModelMetadata.from_api_data(api_data)

        assert m.model_id == "meta-llama/llama-3-8b"
        assert m.model_type == ModelType.LLM
        assert m.model_family == "llama3"
        assert m.size_billions == 8.0
        assert m.quantization == "Q4_K_M"
        assert m.max_context_length == 8192
        # Capabilities from API native format
        assert m.capabilities.tool_calling is not None
        assert m.capabilities.tool_calling.supported is True
        assert m.capabilities.tool_calling.source == CapabilitySource.LMSTUDIO_API
        assert m.capabilities.vision is not None
        assert m.capabilities.vision.supported is False

    def test_model_metadata_from_api_data_unknown_type_defaults_llm(self):
        """from_api_data falls back to LLM when type is unrecognised."""
        api_data = {
            "key": "some/model",
            "type": "unknown_future_type",
            "arch": "",
            "params_string": "",
            "capabilities": {},
        }
        m = ModelMetadata.from_api_data(api_data)
        assert m.model_type == ModelType.LLM

    # -----------------------------------------------------------------------
    # _parse_params_string
    # -----------------------------------------------------------------------

    def test_parse_params_string_standard(self):
        """Standard B/M suffix parsing."""
        assert ModelMetadata._parse_params_string("30B") == 30.0
        assert ModelMetadata._parse_params_string("8B") == 8.0
        assert ModelMetadata._parse_params_string("300M") == pytest.approx(0.3, abs=0.001)

    def test_parse_params_string_moe(self):
        """MoE format like '160x19B' should multiply the parts."""
        result = ModelMetadata._parse_params_string("160x19B")
        assert result == pytest.approx(3040.0, abs=0.01)

    def test_parse_params_string_empty(self):
        """Empty string returns None."""
        assert ModelMetadata._parse_params_string("") is None

    def test_parse_params_string_none_like(self):
        """Garbage input returns None without raising."""
        assert ModelMetadata._parse_params_string("???") is None

    # -----------------------------------------------------------------------
    # _estimate_vram_gb
    # -----------------------------------------------------------------------

    def test_estimate_vram_gb_basic(self):
        """17 GB file + Q4_K_M quantization gives a reasonable VRAM estimate."""
        size_bytes = 17 * 1024 ** 3
        result = ModelMetadata._estimate_vram_gb(
            size_bytes=size_bytes,
            quantization="Q4_K_M",
        )
        assert result is not None
        # Q4 multiplier = 1.0, overhead 1.1 => ~18.7 GB; allow generous range
        assert 18.0 <= result <= 21.0

    def test_estimate_vram_gb_fp16_higher_than_q4(self):
        """FP16 quantization should require more VRAM than Q4 for the same file."""
        size_bytes = 10 * 1024 ** 3
        q4_vram = ModelMetadata._estimate_vram_gb(size_bytes=size_bytes, quantization="Q4_K_M")
        fp16_vram = ModelMetadata._estimate_vram_gb(size_bytes=size_bytes, quantization="FP16")
        assert fp16_vram is not None
        assert q4_vram is not None
        assert fp16_vram > q4_vram

    def test_estimate_vram_gb_none_when_no_size(self):
        """Returns None when size_bytes is None."""
        result = ModelMetadata._estimate_vram_gb(size_bytes=None, quantization="Q4_K_M")
        assert result is None

    def test_estimate_vram_gb_with_context_and_params(self):
        """Providing context length and size_billions increases KV cache contribution."""
        size_bytes = 10 * 1024 ** 3
        without_ctx = ModelMetadata._estimate_vram_gb(
            size_bytes=size_bytes,
            quantization="Q4_K_M",
        )
        with_ctx = ModelMetadata._estimate_vram_gb(
            size_bytes=size_bytes,
            quantization="Q4_K_M",
            max_context_length=131072,
            size_billions=30.0,
        )
        # With long context, estimate should be >= without
        assert with_ctx is not None
        assert without_ctx is not None
        assert with_ctx >= without_ctx

    # -----------------------------------------------------------------------
    # _is_thinking_model
    # -----------------------------------------------------------------------

    def test_is_thinking_model_qwq(self):
        """QwQ models are thinking models."""
        assert ModelMetadata._is_thinking_model("qwen/qwq-32b") is True

    def test_is_thinking_model_deepseek_r1(self):
        """DeepSeek-R1 is a thinking model."""
        assert ModelMetadata._is_thinking_model("deepseek-r1-14b") is True

    def test_is_thinking_model_regular(self):
        """A regular coder model is NOT a thinking model."""
        assert ModelMetadata._is_thinking_model("qwen/qwen3-coder-30b") is False

    def test_is_thinking_model_r1_variant(self):
        """A model with 'r1-' in the name is a thinking model."""
        assert ModelMetadata._is_thinking_model("some-org/r1-distill-7b") is True

    # -----------------------------------------------------------------------
    # _extract_model_family
    # -----------------------------------------------------------------------

    def test_extract_model_family_qwen3(self):
        """qwen3 family is detected from model_id."""
        assert ModelMetadata._extract_model_family("qwen/qwen3-coder-30b", "") == "qwen3"

    def test_extract_model_family_llama3(self):
        """llama3 family is detected from model_id."""
        assert ModelMetadata._extract_model_family("meta-llama/llama-3-8b", "") == "llama3"

    def test_extract_model_family_unknown(self):
        """Unknown model with empty architecture returns 'unknown'."""
        assert ModelMetadata._extract_model_family("some-org/totally-new-model", "") == "unknown"

    def test_extract_model_family_fallback_to_arch(self):
        """When model_id has no known pattern, architecture is used as fallback."""
        family = ModelMetadata._extract_model_family("corp/custom-llm", "transformer_block")
        assert family == "transformer"


# ===========================================================================
# Group 2 — Serialization roundtrips
# ===========================================================================


class TestSchemaSerialization:
    """Tests that to_dict() / from_dict() are invertible."""

    def test_capability_score_roundtrip(self):
        """CapabilityScore survives a to_dict / from_dict cycle."""
        original = CapabilityScore(
            supported=0.933,
            confidence=0.95,
            source=CapabilitySource.WEB_RESEARCH,
            details="BFCL score from leaderboard",
        )
        restored = CapabilityScore.from_dict(original.to_dict())

        assert restored.supported == original.supported
        assert restored.confidence == original.confidence
        assert restored.source == original.source
        assert restored.details == original.details

    def test_capability_score_roundtrip_no_details(self):
        """CapabilityScore without details field omits it from dict."""
        original = CapabilityScore(
            supported=True,
            confidence=1.0,
            source=CapabilitySource.LMS_METADATA,
        )
        d = original.to_dict()
        assert "details" not in d  # omitted when None

        restored = CapabilityScore.from_dict(d)
        assert restored.supported is True
        assert restored.details is None

    def test_benchmark_data_roundtrip(self):
        """BenchmarkData with bfcl_score survives a to_dict / from_dict cycle."""
        ts = datetime(2025, 6, 1, 12, 0, 0)
        original = BenchmarkData(
            bfcl_score=0.933,
            bfcl_rank=3,
            bfcl_ast_accuracy=0.91,
            bfcl_exec_accuracy=0.88,
            other_benchmarks={"mmlu": 0.85},
            source_url="https://example.com/bfcl",
            retrieved_at=ts,
        )
        restored = BenchmarkData.from_dict(original.to_dict())

        assert restored.bfcl_score == original.bfcl_score
        assert restored.bfcl_rank == original.bfcl_rank
        assert restored.bfcl_ast_accuracy == original.bfcl_ast_accuracy
        assert restored.bfcl_exec_accuracy == original.bfcl_exec_accuracy
        assert restored.other_benchmarks == original.other_benchmarks
        assert restored.source_url == original.source_url
        assert restored.retrieved_at == ts

    def test_benchmark_data_empty_roundtrip(self):
        """Empty BenchmarkData produces an empty dict and restores correctly."""
        original = BenchmarkData()
        d = original.to_dict()
        assert d == {}
        restored = BenchmarkData.from_dict(d)
        assert restored.bfcl_score is None

    def test_model_capabilities_roundtrip(self):
        """ModelCapabilities with tool_calling and vision survives roundtrip."""
        original = ModelCapabilities(
            tool_calling=CapabilityScore(
                supported=True,
                confidence=1.0,
                source=CapabilitySource.LMS_METADATA,
                details="From LM Studio model metadata",
            ),
            vision=CapabilityScore(
                supported=False,
                confidence=1.0,
                source=CapabilitySource.LMS_METADATA,
            ),
        )
        restored = ModelCapabilities.from_dict(original.to_dict())

        assert restored.tool_calling is not None
        assert restored.tool_calling.supported is True
        assert restored.tool_calling.details == "From LM Studio model metadata"
        assert restored.vision is not None
        assert restored.vision.supported is False
        assert restored.structured_output is None

    def test_model_metadata_roundtrip(self):
        """Full ModelMetadata survives to_dict / from_dict cycle."""
        original = ModelMetadata(
            model_id="qwen/qwen3-coder-30b",
            model_type=ModelType.LLM,
            display_name="Qwen3 Coder 30B",
            publisher="qwen",
            model_family="qwen3",
            architecture="qwen3_moe",
            size_billions=30.0,
            size_bytes=17 * 1024 ** 3,
            estimated_vram_gb=18.7,
            quantization="Q4_K_M",
            max_context_length=131072,
            is_thinking_model=False,
            capabilities=ModelCapabilities(
                tool_calling=CapabilityScore(
                    supported=True,
                    confidence=1.0,
                    source=CapabilitySource.LMS_METADATA,
                )
            ),
            benchmarks=BenchmarkData(bfcl_score=0.933),
            recommended_for=["tool_use", "agents", "coding"],
            research_status=ResearchStatus.COMPLETED,
            researched_at=datetime(2025, 6, 1, 12, 0, 0),
        )
        restored = ModelMetadata.from_dict(original.to_dict())

        assert restored.model_id == original.model_id
        assert restored.model_type == original.model_type
        assert restored.publisher == original.publisher
        assert restored.model_family == original.model_family
        assert restored.size_billions == original.size_billions
        assert restored.quantization == original.quantization
        assert restored.max_context_length == original.max_context_length
        assert restored.is_thinking_model == original.is_thinking_model
        assert restored.capabilities.tool_calling is not None
        assert restored.capabilities.tool_calling.supported is True
        assert restored.benchmarks.bfcl_score == 0.933
        assert restored.recommended_for == original.recommended_for
        assert restored.research_status == ResearchStatus.COMPLETED
        assert restored.researched_at == original.researched_at


# ===========================================================================
# Group 3 — Enums and RegistryStats
# ===========================================================================


class TestEnumsAndStats:
    """Tests for enum values and RegistryStats serialization."""

    def test_model_type_enum_values(self):
        """ModelType enum has the expected string values."""
        assert ModelType.LLM.value == "llm"
        assert ModelType.EMBEDDING.value == "embedding"

    def test_research_status_enum_all_four(self):
        """ResearchStatus has all four expected members."""
        values = {s.value for s in ResearchStatus}
        assert values == {"not_researched", "researching", "completed", "failed"}

    def test_registry_stats_to_dict_all_fields(self):
        """RegistryStats.to_dict() includes all numeric counts."""
        ts = datetime(2025, 6, 1, 0, 0, 0)
        stats = RegistryStats(
            total_models=10,
            llm_models=8,
            embedding_models=2,
            researched_models=5,
            pending_research=3,
            failed_research=2,
            last_updated=ts,
        )
        d = stats.to_dict()

        assert d["total_models"] == 10
        assert d["llm_models"] == 8
        assert d["embedding_models"] == 2
        assert d["researched_models"] == 5
        assert d["pending_research"] == 3
        assert d["failed_research"] == 2
        assert "last_updated" in d

    def test_registry_stats_to_dict_no_timestamp(self):
        """to_dict() omits last_updated when it is None."""
        stats = RegistryStats(total_models=3)
        d = stats.to_dict()
        assert "last_updated" not in d

    def test_capability_source_enum_lmstudio_api(self):
        """CapabilitySource.LMSTUDIO_API has the expected value."""
        assert CapabilitySource.LMSTUDIO_API.value == "lmstudio_api"


# ===========================================================================
# Group 4 — CacheManager
# ===========================================================================


class TestCacheManager:
    """Tests for CacheManager persistence, path resolution, and sync logic."""

    # -----------------------------------------------------------------------
    # Path resolution
    # -----------------------------------------------------------------------

    def test_cache_path_explicit(self, tmp_path: Path):
        """CacheManager uses the explicit path when provided."""
        explicit = str(tmp_path / "explicit.json")
        cm = CacheManager(cache_path=explicit)
        assert str(cm.cache_path) == explicit

    def test_cache_path_env_var(self, tmp_path: Path):
        """CacheManager picks up MODEL_REGISTRY_CACHE from the environment."""
        env_path = str(tmp_path / "env_cache.json")
        with patch.dict(os.environ, {"MODEL_REGISTRY_CACHE": env_path}):
            cm = CacheManager()
        assert str(cm.cache_path) == env_path

    # -----------------------------------------------------------------------
    # Save / load roundtrip
    # -----------------------------------------------------------------------

    def test_cache_save_load_roundtrip(self, tmp_path: Path):
        """Save two models; reload them and verify all fields are preserved."""
        cache_file = str(tmp_path / "cache.json")
        cm = CacheManager(cache_path=cache_file)

        model_a = ModelMetadata(
            model_id="org/model-a",
            model_type=ModelType.LLM,
            display_name="Model A",
            publisher="org",
            model_family="family-a",
            architecture="arch-a",
            size_billions=7.0,
        )
        model_b = ModelMetadata(
            model_id="org/model-b",
            model_type=ModelType.EMBEDDING,
            display_name="Model B",
            publisher="org",
            model_family="family-b",
            architecture="arch-b",
        )

        cm.save({"org/model-a": model_a, "org/model-b": model_b})
        loaded = cm.load()

        assert set(loaded.keys()) == {"org/model-a", "org/model-b"}
        assert loaded["org/model-a"].display_name == "Model A"
        assert loaded["org/model-a"].size_billions == 7.0
        assert loaded["org/model-b"].model_type == ModelType.EMBEDDING

    # -----------------------------------------------------------------------
    # Load from non-existent file
    # -----------------------------------------------------------------------

    def test_cache_load_empty_when_no_file(self, tmp_path: Path):
        """Loading from a non-existent path returns an empty dict."""
        cache_file = str(tmp_path / "missing.json")
        cm = CacheManager(cache_path=cache_file)
        result = cm.load()
        assert result == {}

    # -----------------------------------------------------------------------
    # Corruption recovery
    # -----------------------------------------------------------------------

    def test_cache_load_corrupted_returns_empty(self, tmp_path: Path):
        """Loading a corrupted (invalid JSON) cache file returns {} gracefully."""
        cache_file = tmp_path / "corrupt.json"
        cache_file.write_text("{ this is not valid json !!!}")

        cm = CacheManager(cache_path=str(cache_file))
        result = cm.load()
        assert result == {}

    # -----------------------------------------------------------------------
    # get_stats
    # -----------------------------------------------------------------------

    def test_cache_get_stats(self, tmp_path: Path):
        """get_stats() returns correct counts after saving LLM + embedding models."""
        cache_file = str(tmp_path / "stats.json")
        cm = CacheManager(cache_path=cache_file)

        llm1 = _make_metadata("org/llm-1", ModelType.LLM)
        llm2 = _make_metadata("org/llm-2", ModelType.LLM)
        embed1 = _make_metadata("org/embed-1", ModelType.EMBEDDING)

        cm.save({"org/llm-1": llm1, "org/llm-2": llm2, "org/embed-1": embed1})

        stats = cm.get_stats()
        assert stats.total_models == 3
        assert stats.llm_models == 2
        assert stats.embedding_models == 1

    def test_cache_get_stats_research_status_counts(self, tmp_path: Path):
        """get_stats() counts researched / pending / failed models correctly."""
        cache_file = str(tmp_path / "stats2.json")
        cm = CacheManager(cache_path=cache_file)

        completed = _make_metadata("org/m-completed")
        completed.research_status = ResearchStatus.COMPLETED

        pending = _make_metadata("org/m-pending")
        pending.research_status = ResearchStatus.NOT_RESEARCHED

        failed = _make_metadata("org/m-failed")
        failed.research_status = ResearchStatus.FAILED

        cm.save({
            "org/m-completed": completed,
            "org/m-pending": pending,
            "org/m-failed": failed,
        })

        stats = cm.get_stats()
        assert stats.researched_models == 1
        assert stats.pending_research == 1
        assert stats.failed_research == 1

    # -----------------------------------------------------------------------
    # export / import
    # -----------------------------------------------------------------------

    def test_cache_export_import_roundtrip(self, tmp_path: Path):
        """export_to_dict → clear → import_from_dict restores models."""
        cache_file = str(tmp_path / "export.json")
        cm = CacheManager(cache_path=cache_file)

        model = _make_metadata("org/export-model")
        cm.save({"org/export-model": model})

        exported = cm.export_to_dict()
        assert "models" in exported
        assert "org/export-model" in exported["models"]

        # Clear the cache file, then reimport
        cm.clear()
        assert cm.load() == {}

        count = cm.import_from_dict(exported)
        assert count == 1

        restored = cm.load()
        assert "org/export-model" in restored
        assert restored["org/export-model"].publisher == "test-publisher"

    def test_cache_export_empty_when_no_file(self, tmp_path: Path):
        """export_to_dict() on a missing cache returns a minimal dict."""
        cache_file = str(tmp_path / "nonexistent.json")
        cm = CacheManager(cache_path=cache_file)
        result = cm.export_to_dict()
        assert result == {"version": "1.0", "models": {}}

    # -----------------------------------------------------------------------
    # sync_with_available (delta calculation)
    # -----------------------------------------------------------------------

    def test_cache_sync_delta(self, tmp_path: Path):
        """
        Cache has [A, B, C]; available is [B, C, D].
        sync_with_available must report:
          added    = [D]
          removed  = [A]
          unchanged= [B, C]
        """
        cache_file = str(tmp_path / "sync.json")
        cm = CacheManager(cache_path=cache_file)

        cm.save({
            "org/model-a": _make_metadata("org/model-a"),
            "org/model-b": _make_metadata("org/model-b"),
            "org/model-c": _make_metadata("org/model-c"),
        })

        model_d = _make_metadata("org/model-d")
        result = cm.sync_with_available(
            available_ids=["org/model-b", "org/model-c", "org/model-d"],
            new_metadata={"org/model-d": model_d},
        )

        assert result["added"] == ["org/model-d"]
        assert result["removed"] == ["org/model-a"]
        assert set(result["unchanged"]) == {"org/model-b", "org/model-c"}

    def test_cache_sync_no_change(self, tmp_path: Path):
        """When available == cached, no added/removed entries are returned."""
        cache_file = str(tmp_path / "sync_noop.json")
        cm = CacheManager(cache_path=cache_file)

        cm.save({
            "org/model-x": _make_metadata("org/model-x"),
        })

        result = cm.sync_with_available(
            available_ids=["org/model-x"],
        )

        assert result["added"] == []
        assert result["removed"] == []
        assert result["unchanged"] == ["org/model-x"]

    def test_cache_sync_persists_after_delta(self, tmp_path: Path):
        """After sync removes a model, it is no longer present in the cache."""
        cache_file = str(tmp_path / "sync_persist.json")
        cm = CacheManager(cache_path=cache_file)

        cm.save({
            "org/keep": _make_metadata("org/keep"),
            "org/remove": _make_metadata("org/remove"),
        })

        cm.sync_with_available(available_ids=["org/keep"])

        after = cm.load()
        assert "org/keep" in after
        assert "org/remove" not in after
