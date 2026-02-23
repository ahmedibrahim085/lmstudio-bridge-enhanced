#!/usr/bin/env python3
"""
OPP-08: Smart Model Selection — Unit Tests.

RED phase: All tests here MUST FAIL before implementation exists.

Covers:
- Happy path: select_best_model("code_generation") returns a code-capable model
- Happy path: select_best_model("summarization") returns a model with large context
- Negative: select_best_model with no loaded models raises appropriate error
- Negative: select_best_model with unknown task_type falls back gracefully
- Edge case: single loaded model always returns that model regardless of task
- Edge case: all models have equal capability scores — deterministic selection
- Boundary: VRAM budget exactly at model's requirement
- MCP tool: select_best_model_tool returns structured success/error responses
- Task classifier: maps task descriptions to capability requirements
- Scoring: VRAM budget filtering works correctly
"""

import os
import sys
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from model_registry.schemas import (
    CapabilityScore,
    CapabilitySource,
    ModelCapabilities,
    ModelMetadata,
    ModelType,
)
from model_registry.selection_tool import select_best_model_tool
from model_registry.selector import (
    NoModelsAvailableError,
    SmartModelSelector,
    select_best_model,
)

# ===========================================================================
# Helpers — minimal ModelMetadata factories
# ===========================================================================


def _cap(supported: bool | float, confidence: float = 1.0) -> CapabilityScore:
    """Build a CapabilityScore quickly."""
    return CapabilityScore(
        supported=supported,
        confidence=confidence,
        source=CapabilitySource.INFERRED,
    )


def _make_coding_model(
    model_id: str = "test/coder-7b",
    estimated_vram_gb: Optional[float] = 8.0,
) -> ModelMetadata:
    """Return a model strong at coding."""
    return ModelMetadata(
        model_id=model_id,
        model_type=ModelType.LLM,
        display_name=model_id,
        publisher="test",
        model_family="test-family",
        architecture="test-arch",
        estimated_vram_gb=estimated_vram_gb,
        max_context_length=32768,
        capabilities=ModelCapabilities(
            coding=_cap(True, confidence=0.95),
            tool_calling=_cap(True, confidence=0.9),
            long_context=_cap(False),
        ),
    )


def _make_summarization_model(
    model_id: str = "test/long-ctx-14b",
    estimated_vram_gb: Optional[float] = 12.0,
) -> ModelMetadata:
    """Return a model with a large context window (good for summarization)."""
    return ModelMetadata(
        model_id=model_id,
        model_type=ModelType.LLM,
        display_name=model_id,
        publisher="test",
        model_family="test-family",
        architecture="test-arch",
        estimated_vram_gb=estimated_vram_gb,
        max_context_length=131072,
        capabilities=ModelCapabilities(
            coding=_cap(False),
            long_context=_cap(True, confidence=1.0),
            tool_calling=_cap(True, confidence=0.8),
        ),
    )


def _make_reasoning_model(
    model_id: str = "test/reasoner-8b",
    estimated_vram_gb: Optional[float] = 10.0,
) -> ModelMetadata:
    """Return a model strong at reasoning."""
    return ModelMetadata(
        model_id=model_id,
        model_type=ModelType.LLM,
        display_name=model_id,
        publisher="test",
        model_family="test-family",
        architecture="test-arch",
        estimated_vram_gb=estimated_vram_gb,
        max_context_length=32768,
        capabilities=ModelCapabilities(
            reasoning=_cap(True, confidence=0.92),
            tool_calling=_cap(True, confidence=0.85),
        ),
    )


def _make_general_model(
    model_id: str = "test/general-4b",
    estimated_vram_gb: Optional[float] = 4.0,
) -> ModelMetadata:
    """Return a basic general-purpose model with no strong specialisations."""
    return ModelMetadata(
        model_id=model_id,
        model_type=ModelType.LLM,
        display_name=model_id,
        publisher="test",
        model_family="test-family",
        architecture="test-arch",
        estimated_vram_gb=estimated_vram_gb,
        max_context_length=8192,
        capabilities=ModelCapabilities(
            tool_calling=_cap(True, confidence=0.7),
        ),
    )


# ===========================================================================
# Group 1 — Happy Path: task-type routing
# ===========================================================================


class TestHappyPathTaskRouting:
    """select_best_model returns the right model family for common task types."""

    def test_code_generation_returns_coding_model(self):
        """select_best_model('code_generation') picks the coding-capable model."""
        models = {
            "test/coder-7b": _make_coding_model("test/coder-7b"),
            "test/long-ctx-14b": _make_summarization_model("test/long-ctx-14b"),
            "test/general-4b": _make_general_model("test/general-4b"),
        }
        selector = SmartModelSelector(loaded_models=models)
        result = selector.select("code_generation")
        assert result == "test/coder-7b"

    def test_summarization_returns_long_context_model(self):
        """select_best_model('summarization') picks the model with largest context."""
        models = {
            "test/coder-7b": _make_coding_model("test/coder-7b"),
            "test/long-ctx-14b": _make_summarization_model("test/long-ctx-14b"),
            "test/general-4b": _make_general_model("test/general-4b"),
        }
        selector = SmartModelSelector(loaded_models=models)
        result = selector.select("summarization")
        assert result == "test/long-ctx-14b"

    def test_reasoning_returns_reasoning_model(self):
        """select_best_model('reasoning') picks the reasoning-capable model."""
        models = {
            "test/coder-7b": _make_coding_model("test/coder-7b"),
            "test/reasoner-8b": _make_reasoning_model("test/reasoner-8b"),
            "test/general-4b": _make_general_model("test/general-4b"),
        }
        selector = SmartModelSelector(loaded_models=models)
        result = selector.select("reasoning")
        assert result == "test/reasoner-8b"

    def test_tool_use_returns_tool_calling_model(self):
        """select_best_model('tool_use') picks model with highest tool_calling score."""
        models = {
            "test/coder-7b": _make_coding_model("test/coder-7b"),   # tool_calling 0.9
            "test/general-4b": _make_general_model("test/general-4b"),  # tool_calling 0.7
        }
        selector = SmartModelSelector(loaded_models=models)
        result = selector.select("tool_use")
        assert result == "test/coder-7b"

    def test_code_review_returns_coding_model(self):
        """select_best_model('code_review') is treated as coding task."""
        models = {
            "test/coder-7b": _make_coding_model("test/coder-7b"),
            "test/long-ctx-14b": _make_summarization_model("test/long-ctx-14b"),
        }
        selector = SmartModelSelector(loaded_models=models)
        result = selector.select("code_review")
        assert result == "test/coder-7b"

    def test_analysis_returns_reasoning_model(self):
        """select_best_model('analysis') is treated as reasoning task."""
        models = {
            "test/reasoner-8b": _make_reasoning_model("test/reasoner-8b"),
            "test/general-4b": _make_general_model("test/general-4b"),
        }
        selector = SmartModelSelector(loaded_models=models)
        result = selector.select("analysis")
        assert result == "test/reasoner-8b"


# ===========================================================================
# Group 2 — Negative: error conditions
# ===========================================================================


class TestNegativeCases:
    """select_best_model raises or falls back gracefully on error conditions."""

    def test_no_loaded_models_raises(self):
        """NoModelsAvailableError is raised when loaded_models is empty."""
        selector = SmartModelSelector(loaded_models={})
        with pytest.raises(NoModelsAvailableError):
            selector.select("code_generation")

    def test_unknown_task_type_falls_back_to_general(self):
        """Unknown task type selects any available model without crashing."""
        models = {
            "test/general-4b": _make_general_model("test/general-4b"),
        }
        selector = SmartModelSelector(loaded_models=models)
        # Should not raise — returns the only available model
        result = selector.select("totally_unknown_task_xyz")
        assert result == "test/general-4b"

    def test_unknown_task_type_with_multiple_models_returns_deterministic(self):
        """Unknown task type with multiple models is deterministic (stable order)."""
        models = {
            "test/model-a": _make_general_model("test/model-a"),
            "test/model-b": _make_general_model("test/model-b"),
        }
        selector = SmartModelSelector(loaded_models=models)
        result_1 = selector.select("no_such_task")
        result_2 = selector.select("no_such_task")
        assert result_1 == result_2  # same call → same answer (deterministic)

    def test_no_models_available_error_is_descriptive(self):
        """NoModelsAvailableError message includes the task type."""
        selector = SmartModelSelector(loaded_models={})
        with pytest.raises(NoModelsAvailableError, match="code_generation"):
            selector.select("code_generation")


# ===========================================================================
# Group 3 — Edge cases
# ===========================================================================


class TestEdgeCases:
    """Edge cases: single model, ties, embedding-only registry."""

    def test_single_model_always_selected_regardless_of_task(self):
        """When only one model is loaded it is always returned."""
        models = {"test/only-model": _make_general_model("test/only-model")}
        selector = SmartModelSelector(loaded_models=models)
        for task in ["code_generation", "summarization", "reasoning", "vision", "unknown"]:
            assert selector.select(task) == "test/only-model"

    def test_equal_scores_deterministic_selection(self):
        """When all models tie on the relevant capability, selection is deterministic."""
        # Two coding models with identical coding scores
        m1 = _make_coding_model("aaa/model-1")
        m2 = _make_coding_model("bbb/model-2")
        models = {"aaa/model-1": m1, "bbb/model-2": m2}

        selector = SmartModelSelector(loaded_models=models)
        first_call = selector.select("code_generation")
        second_call = selector.select("code_generation")
        # Must be stable (same model each time)
        assert first_call == second_call
        # Must be one of the valid models
        assert first_call in models

    def test_embedding_models_excluded_from_selection(self):
        """Embedding models are excluded; only LLM models are candidates."""
        embed = ModelMetadata(
            model_id="test/embed-model",
            model_type=ModelType.EMBEDDING,
            display_name="test/embed-model",
            publisher="test",
            model_family="test",
            architecture="bert",
        )
        llm = _make_general_model("test/llm-model")
        models = {"test/embed-model": embed, "test/llm-model": llm}
        selector = SmartModelSelector(loaded_models=models)
        result = selector.select("code_generation")
        assert result == "test/llm-model"

    def test_all_embeddings_raises_no_models(self):
        """If all loaded models are embeddings, NoModelsAvailableError is raised."""
        embed = ModelMetadata(
            model_id="test/embed-only",
            model_type=ModelType.EMBEDDING,
            display_name="test/embed-only",
            publisher="test",
            model_family="test",
            architecture="bert",
        )
        models = {"test/embed-only": embed}
        selector = SmartModelSelector(loaded_models=models)
        with pytest.raises(NoModelsAvailableError):
            selector.select("code_generation")


# ===========================================================================
# Group 4 — Boundary: VRAM budget filtering
# ===========================================================================


class TestVRAMBudget:
    """select_best_model respects an optional max_vram_gb budget."""

    def test_vram_budget_excludes_large_model(self):
        """Model exceeding VRAM budget is excluded from candidates."""
        small = _make_general_model("test/small-4b", estimated_vram_gb=4.0)
        large = _make_coding_model("test/coder-30b", estimated_vram_gb=20.0)
        models = {"test/small-4b": small, "test/coder-30b": large}
        selector = SmartModelSelector(loaded_models=models)
        # With 10 GB budget, only small qualifies
        result = selector.select("code_generation", max_vram_gb=10.0)
        assert result == "test/small-4b"

    def test_vram_budget_exactly_at_model_requirement(self):
        """Model with VRAM exactly equal to budget IS included (boundary inclusive)."""
        model = _make_coding_model("test/exact-model", estimated_vram_gb=8.0)
        models = {"test/exact-model": model}
        selector = SmartModelSelector(loaded_models=models)
        result = selector.select("code_generation", max_vram_gb=8.0)
        assert result == "test/exact-model"

    def test_vram_budget_all_exceed_raises(self):
        """When all models exceed the VRAM budget, NoModelsAvailableError is raised."""
        large1 = _make_coding_model("test/large-1", estimated_vram_gb=24.0)
        large2 = _make_summarization_model("test/large-2", estimated_vram_gb=32.0)
        models = {"test/large-1": large1, "test/large-2": large2}
        selector = SmartModelSelector(loaded_models=models)
        with pytest.raises(NoModelsAvailableError):
            selector.select("code_generation", max_vram_gb=16.0)

    def test_model_with_no_vram_info_is_included(self):
        """Models without VRAM info (None) are always included in budget checks."""
        no_vram = _make_coding_model("test/no-vram-info", estimated_vram_gb=None)
        large = _make_summarization_model("test/large", estimated_vram_gb=32.0)
        models = {"test/no-vram-info": no_vram, "test/large": large}
        selector = SmartModelSelector(loaded_models=models)
        # With tight budget, the no-VRAM model should still be considered
        result = selector.select("code_generation", max_vram_gb=8.0)
        assert result == "test/no-vram-info"


# ===========================================================================
# Group 5 — select_best_model() functional API
# ===========================================================================


class TestSelectBestModelFunction:
    """Tests for the top-level select_best_model() function with mocked registry."""

    def test_select_best_model_queries_loaded_models(self):
        """select_best_model() calls the registry to get loaded model IDs."""
        coding_model = _make_coding_model("test/coder-7b")

        with (
            patch("model_registry.selector.LMSIntegration") as mock_lms,
            patch("model_registry.selector.CacheManager") as mock_cache_cls,
        ):
            mock_lms.get_loaded_model_ids.return_value = ["test/coder-7b"]

            mock_cache = MagicMock()
            mock_cache.load.return_value = {"test/coder-7b": coding_model}
            mock_cache_cls.return_value = mock_cache

            result = select_best_model("code_generation")

        assert result == "test/coder-7b"

    def test_select_best_model_no_loaded_models_raises(self):
        """select_best_model() raises NoModelsAvailableError when nothing is loaded."""
        with (
            patch("model_registry.selector.LMSIntegration") as mock_lms,
            patch("model_registry.selector.CacheManager") as mock_cache_cls,
        ):
            mock_lms.get_loaded_model_ids.return_value = []

            mock_cache = MagicMock()
            mock_cache.load.return_value = {}
            mock_cache_cls.return_value = mock_cache

            with pytest.raises(NoModelsAvailableError):
                select_best_model("code_generation")

    def test_select_best_model_with_requirements_dict(self):
        """select_best_model() accepts an optional requirements dict."""
        coding_model = _make_coding_model("test/coder-7b")

        with (
            patch("model_registry.selector.LMSIntegration") as mock_lms,
            patch("model_registry.selector.CacheManager") as mock_cache_cls,
        ):
            mock_lms.get_loaded_model_ids.return_value = ["test/coder-7b"]
            mock_cache = MagicMock()
            mock_cache.load.return_value = {"test/coder-7b": coding_model}
            mock_cache_cls.return_value = mock_cache

            result = select_best_model(
                "code_generation",
                requirements={"max_vram_gb": 16.0},
            )

        assert result == "test/coder-7b"


# ===========================================================================
# Group 6 — MCP Tool: select_best_model_tool
# ===========================================================================


class TestSelectBestModelTool:
    """Tests for the MCP tool wrapper around smart selection."""

    def test_tool_returns_success_response(self):
        """select_best_model_tool returns success=True with model_id on success."""
        with patch("model_registry.selection_tool.select_best_model") as mock_select:
            mock_select.return_value = "test/coder-7b"
            result = select_best_model_tool(task_type="code_generation")

        assert result["success"] is True
        assert result["model_id"] == "test/coder-7b"
        assert result["task_type"] == "code_generation"

    def test_tool_returns_error_when_no_models(self):
        """select_best_model_tool returns success=False when no models available."""
        with patch("model_registry.selection_tool.select_best_model") as mock_select:
            mock_select.side_effect = NoModelsAvailableError("no models for code_generation")
            result = select_best_model_tool(task_type="code_generation")

        assert result["success"] is False
        assert "error" in result
        assert result["error_code"] == "no_models_available"

    def test_tool_returns_error_on_unexpected_exception(self):
        """select_best_model_tool returns success=False on unexpected errors."""
        with patch("model_registry.selection_tool.select_best_model") as mock_select:
            mock_select.side_effect = RuntimeError("Something went wrong")
            result = select_best_model_tool(task_type="code_generation")

        assert result["success"] is False
        assert "error" in result

    def test_tool_passes_max_vram_gb_to_selector(self):
        """select_best_model_tool passes max_vram_gb to the underlying selector."""
        with patch("model_registry.selection_tool.select_best_model") as mock_select:
            mock_select.return_value = "test/small-model"
            select_best_model_tool(task_type="code_generation", max_vram_gb=8.0)

        mock_select.assert_called_once_with(
            "code_generation",
            requirements={"max_vram_gb": 8.0},
            cache_path=None,
        )

    def test_tool_includes_task_type_in_response(self):
        """The tool response always echoes back the task_type."""
        with patch("model_registry.selection_tool.select_best_model") as mock_select:
            mock_select.return_value = "test/model"
            result = select_best_model_tool(task_type="summarization")

        assert result["task_type"] == "summarization"

    def test_tool_no_max_vram_calls_without_budget(self):
        """When max_vram_gb is None, requirements dict does not include it."""
        with patch("model_registry.selection_tool.select_best_model") as mock_select:
            mock_select.return_value = "test/model"
            select_best_model_tool(task_type="reasoning", max_vram_gb=None)

        mock_select.assert_called_once_with("reasoning", requirements=None, cache_path=None)


# ===========================================================================
# Group 7 — Task classifier internals
# ===========================================================================


class TestTaskClassifier:
    """Tests for SmartModelSelector._classify_task()."""

    def test_code_generation_maps_to_coding(self):
        selector = SmartModelSelector(loaded_models={})
        cap = selector._classify_task("code_generation")
        assert cap == "coding"

    def test_summarization_maps_to_long_context(self):
        selector = SmartModelSelector(loaded_models={})
        cap = selector._classify_task("summarization")
        assert cap == "long_context"

    def test_reasoning_maps_to_reasoning(self):
        selector = SmartModelSelector(loaded_models={})
        cap = selector._classify_task("reasoning")
        assert cap == "reasoning"

    def test_tool_use_maps_to_tool_calling(self):
        selector = SmartModelSelector(loaded_models={})
        cap = selector._classify_task("tool_use")
        assert cap == "tool_calling"

    def test_vision_maps_to_vision(self):
        selector = SmartModelSelector(loaded_models={})
        cap = selector._classify_task("vision")
        assert cap == "vision"

    def test_unknown_task_returns_none(self):
        selector = SmartModelSelector(loaded_models={})
        cap = selector._classify_task("totally_unknown_xyz_task")
        assert cap is None


# ===========================================================================
# Group 8 — Scoring internals
# ===========================================================================


class TestScoringInternals:
    """Tests for SmartModelSelector._score_model()."""

    def test_score_model_coding_high_for_coding_model(self):
        """A coding model gets a higher score for coding task than a general one."""
        coding = _make_coding_model("test/coder")
        general = _make_general_model("test/general")
        selector = SmartModelSelector(loaded_models={})
        score_coding = selector._score_model(coding, "coding")
        score_general = selector._score_model(general, "coding")
        assert score_coding > score_general

    def test_score_model_returns_zero_for_missing_capability(self):
        """A model with no capability info returns 0 score for that capability."""
        model = ModelMetadata(
            model_id="test/bare",
            model_type=ModelType.LLM,
            display_name="test/bare",
            publisher="test",
            model_family="family",
            architecture="arch",
        )
        selector = SmartModelSelector(loaded_models={})
        score = selector._score_model(model, "coding")
        assert score == 0.0

    def test_score_model_bool_true_returns_confidence(self):
        """A bool=True capability returns confidence as the score."""
        model = _make_coding_model("test/coder")
        selector = SmartModelSelector(loaded_models={})
        score = selector._score_model(model, "coding")
        # coding cap: supported=True, confidence=0.95 → score >= 0.95
        assert score >= 0.95

    def test_score_model_bool_false_returns_zero(self):
        """A bool=False capability returns 0 score (not supported)."""
        model = _make_summarization_model("test/long-ctx")  # coding=False
        selector = SmartModelSelector(loaded_models={})
        score = selector._score_model(model, "coding")
        assert score == 0.0


# ---------------------------------------------------------------------------
# Group 8 — select_best_model registered as MCP tool (C-1 fix)
# ---------------------------------------------------------------------------


class TestSelectBestModelRegistered:
    """C-1 regression: select_best_model must be exposed as MCP tool via register function."""

    @staticmethod
    def _make_mock_mcp():
        """Create a mock MCP server that collects registered tool names."""
        mock_mcp = MagicMock()
        registered = []

        def fake_tool_decorator():
            def decorator(fn):
                registered.append(fn.__name__)
                return fn
            return decorator

        mock_mcp.tool = fake_tool_decorator
        mock_mcp._registered = registered
        return mock_mcp

    def test_register_function_exists(self):
        """model_registry must have a register_model_registry_tools function."""
        from model_registry.selection_tool import register_model_registry_tools

        assert callable(register_model_registry_tools)

    def test_register_includes_select_best_model(self):
        """register_model_registry_tools must register select_best_model tool."""
        from model_registry.selection_tool import register_model_registry_tools

        mock_mcp = self._make_mock_mcp()
        register_model_registry_tools(mock_mcp)
        assert "select_best_model" in mock_mcp._registered, (
            "select_best_model not registered as MCP tool"
        )

    def test_main_calls_register_model_registry_tools(self):
        """main.py must import and call register_model_registry_tools."""
        import inspect
        import main

        source = inspect.getsource(main)
        assert "register_model_registry_tools" in source, (
            "main.py must call register_model_registry_tools"
        )
