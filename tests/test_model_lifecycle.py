#!/usr/bin/env python3
"""
Unit tests for ModelLifecycleManager (tests/fixtures/model_lifecycle.py).

Covers all four public methods:
  - cleanup_duplicates()     — unloads :2/:3 duplicate model instances
  - ensure_model_for_phase() — loads a model respecting VRAM budget + TTL
  - unload_models_we_loaded() — session teardown, only touches what we loaded
  - models_we_loaded         — read-only frozenset property

All LMSHelper interactions are mocked. No real LM Studio connection is made.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Ensure project root is on sys.path so imports resolve correctly.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests.fixtures.model_lifecycle import ModelLifecycleManager
from config.constants import TEST_MAX_LOADED_MODELS, TEST_MODEL_TTL


# ==============================================================================
# Helpers
# ==============================================================================

def _make_model_dict(
    identifier: str,
    instance_id: str = "",
    model_key: str = "",
) -> dict:
    """Build a minimal model dict as LMSHelper.list_loaded_models() would return."""
    return {
        "identifier": identifier,
        "modelKey": model_key or identifier,
        "instance_id": instance_id,
    }


# ==============================================================================
# cleanup_duplicates()
# ==============================================================================

class TestCleanupDuplicates:
    """Tests for ModelLifecycleManager.cleanup_duplicates()."""

    # ------------------------------------------------------------------
    # No loaded models
    # ------------------------------------------------------------------

    @pytest.mark.unit
    @patch("tests.fixtures.model_lifecycle.LMSHelper.list_loaded_models", return_value=None)
    def test_cleanup_no_loaded_models(self, mock_list):
        """When list_loaded_models returns None, cleanup returns 0 immediately."""
        manager = ModelLifecycleManager()
        result = manager.cleanup_duplicates()

        assert result == 0
        mock_list.assert_called_once()

    # ------------------------------------------------------------------
    # No duplicates (each base model loaded once)
    # ------------------------------------------------------------------

    @pytest.mark.unit
    @patch("tests.fixtures.model_lifecycle.LMSHelper._get_rest_client")
    @patch("tests.fixtures.model_lifecycle.LMSHelper._get_base_model_name")
    @patch("tests.fixtures.model_lifecycle.LMSHelper.list_loaded_models")
    def test_cleanup_no_duplicates(self, mock_list, mock_base_name, mock_rest):
        """When each model has only one instance, cleanup_duplicates returns 0."""
        mock_list.return_value = [
            _make_model_dict("qwen/qwen3-coder-30b"),
            _make_model_dict("mistralai/magistral-small"),
        ]
        # Each identifier maps to a unique base name.
        mock_base_name.side_effect = lambda ident: ident

        rest_client = MagicMock()
        mock_rest.return_value = rest_client

        manager = ModelLifecycleManager()
        result = manager.cleanup_duplicates()

        assert result == 0
        rest_client.unload_model.assert_not_called()

    # ------------------------------------------------------------------
    # Duplicates — unloaded via rest_client.unload_model(instance_id)
    # ------------------------------------------------------------------

    @pytest.mark.unit
    @patch("tests.fixtures.model_lifecycle.LMSHelper._get_rest_client")
    @patch("tests.fixtures.model_lifecycle.LMSHelper._get_base_model_name")
    @patch("tests.fixtures.model_lifecycle.LMSHelper.list_loaded_models")
    def test_cleanup_unloads_duplicates_via_rest(self, mock_list, mock_base_name, mock_rest):
        """Model loaded 3 times: keeps first, unloads 2 duplicates via rest_client."""
        base = "qwen/qwen3-coder-30b"
        mock_list.return_value = [
            _make_model_dict(base, instance_id="inst-1"),
            _make_model_dict(f"{base}:2", instance_id="inst-2"),
            _make_model_dict(f"{base}:3", instance_id="inst-3"),
        ]
        # All three identifiers resolve to the same base name.
        mock_base_name.return_value = base

        rest_client = MagicMock()
        mock_rest.return_value = rest_client

        manager = ModelLifecycleManager()
        result = manager.cleanup_duplicates()

        assert result == 2
        # Must have been called with the duplicate instance_ids (not the first).
        assert rest_client.unload_model.call_count == 2
        called_ids = {call.args[0] for call in rest_client.unload_model.call_args_list}
        assert called_ids == {"inst-2", "inst-3"}

    # ------------------------------------------------------------------
    # Fallback to LMSHelper.unload_model() when rest_client is None
    # ------------------------------------------------------------------

    @pytest.mark.unit
    @patch("tests.fixtures.model_lifecycle.LMSHelper.unload_model")
    @patch("tests.fixtures.model_lifecycle.LMSHelper._get_rest_client", return_value=None)
    @patch("tests.fixtures.model_lifecycle.LMSHelper._get_base_model_name")
    @patch("tests.fixtures.model_lifecycle.LMSHelper.list_loaded_models")
    def test_cleanup_falls_back_to_cli_when_no_rest(
        self, mock_list, mock_base_name, mock_rest, mock_unload
    ):
        """When _get_rest_client() returns None, falls back to LMSHelper.unload_model()."""
        base = "mistralai/magistral-small"
        mock_list.return_value = [
            _make_model_dict(base, instance_id="inst-1"),
            _make_model_dict(f"{base}:2", instance_id="inst-2"),
        ]
        mock_base_name.return_value = base

        manager = ModelLifecycleManager()
        result = manager.cleanup_duplicates()

        assert result == 1
        mock_unload.assert_called_once()
        # Called with the identifier of the duplicate, not the instance_id.
        call_args = mock_unload.call_args.args[0]
        assert call_args == f"{base}:2"

    # ------------------------------------------------------------------
    # Fallback to CLI when instance_id is empty (even with a rest_client)
    # ------------------------------------------------------------------

    @pytest.mark.unit
    @patch("tests.fixtures.model_lifecycle.LMSHelper.unload_model")
    @patch("tests.fixtures.model_lifecycle.LMSHelper._get_rest_client")
    @patch("tests.fixtures.model_lifecycle.LMSHelper._get_base_model_name")
    @patch("tests.fixtures.model_lifecycle.LMSHelper.list_loaded_models")
    def test_cleanup_falls_back_to_cli_when_no_instance_id(
        self, mock_list, mock_base_name, mock_rest, mock_unload
    ):
        """When duplicate has empty instance_id, falls back to CLI even with rest_client."""
        base = "llama/llama3-8b"
        mock_list.return_value = [
            _make_model_dict(base, instance_id="inst-1"),
            # Duplicate has no instance_id (empty string).
            _make_model_dict(f"{base}:2", instance_id=""),
        ]
        mock_base_name.return_value = base

        rest_client = MagicMock()
        mock_rest.return_value = rest_client

        manager = ModelLifecycleManager()
        result = manager.cleanup_duplicates()

        assert result == 1
        # rest_client.unload_model must NOT be called (no instance_id).
        rest_client.unload_model.assert_not_called()
        mock_unload.assert_called_once_with(f"{base}:2")

    # ------------------------------------------------------------------
    # Unload exception: continues, partial count returned
    # ------------------------------------------------------------------

    @pytest.mark.unit
    @patch("tests.fixtures.model_lifecycle.LMSHelper._get_rest_client")
    @patch("tests.fixtures.model_lifecycle.LMSHelper._get_base_model_name")
    @patch("tests.fixtures.model_lifecycle.LMSHelper.list_loaded_models")
    def test_cleanup_handles_unload_failure(self, mock_list, mock_base_name, mock_rest):
        """When one unload raises, cleanup continues and returns partial count."""
        base = "qwen/qwen3-4b"
        mock_list.return_value = [
            _make_model_dict(base, instance_id="inst-1"),
            _make_model_dict(f"{base}:2", instance_id="inst-2"),
            _make_model_dict(f"{base}:3", instance_id="inst-3"),
        ]
        mock_base_name.return_value = base

        rest_client = MagicMock()
        # First duplicate unload raises, second succeeds.
        rest_client.unload_model.side_effect = [RuntimeError("Network error"), None]
        mock_rest.return_value = rest_client

        manager = ModelLifecycleManager()
        result = manager.cleanup_duplicates()

        # Only the second duplicate succeeded.
        assert result == 1
        assert rest_client.unload_model.call_count == 2


# ==============================================================================
# ensure_model_for_phase()
# ==============================================================================

class TestEnsureModelForPhase:
    """Tests for ModelLifecycleManager.ensure_model_for_phase()."""

    # ------------------------------------------------------------------
    # Already loaded — no load call
    # ------------------------------------------------------------------

    @pytest.mark.unit
    @patch("tests.fixtures.model_lifecycle.LMSHelper.load_model")
    @patch("tests.fixtures.model_lifecycle.LMSHelper.is_model_loaded", return_value=True)
    @patch("tests.fixtures.model_lifecycle.LMSHelper._get_base_model_name", return_value="qwen/qwen3-4b")
    @patch("tests.fixtures.model_lifecycle.LMSHelper.list_loaded_models")
    def test_ensure_model_already_loaded(
        self, mock_list, mock_base_name, mock_is_loaded, mock_load
    ):
        """When is_model_loaded returns True, returns True without calling load_model."""
        mock_list.return_value = []

        manager = ModelLifecycleManager()
        result = manager.ensure_model_for_phase("qwen/qwen3-4b")

        assert result is True
        mock_load.assert_not_called()

    # ------------------------------------------------------------------
    # Load succeeds — model tracked in _loaded_by_us
    # ------------------------------------------------------------------

    @pytest.mark.unit
    @patch("tests.fixtures.model_lifecycle.LMSHelper.load_model", return_value=True)
    @patch("tests.fixtures.model_lifecycle.LMSHelper.is_model_loaded", return_value=False)
    @patch("tests.fixtures.model_lifecycle.LMSHelper._get_base_model_name", return_value="qwen/qwen3-4b")
    @patch("tests.fixtures.model_lifecycle.LMSHelper.list_loaded_models", return_value=[])
    def test_ensure_model_loads_successfully(
        self, mock_list, mock_base_name, mock_is_loaded, mock_load
    ):
        """Successful load returns True and tracks the model in _loaded_by_us."""
        manager = ModelLifecycleManager()
        result = manager.ensure_model_for_phase("qwen/qwen3-4b")

        assert result is True
        assert "qwen/qwen3-4b" in manager._loaded_by_us

    # ------------------------------------------------------------------
    # VRAM budget exceeded — returns False without loading
    # ------------------------------------------------------------------

    @pytest.mark.unit
    @patch("tests.fixtures.model_lifecycle.LMSHelper.load_model")
    @patch("tests.fixtures.model_lifecycle.LMSHelper.is_model_loaded", return_value=False)
    @patch("tests.fixtures.model_lifecycle.LMSHelper._get_base_model_name")
    @patch("tests.fixtures.model_lifecycle.LMSHelper.list_loaded_models")
    def test_ensure_model_vram_budget_exceeded(
        self, mock_list, mock_base_name, mock_is_loaded, mock_load
    ):
        """When loaded_bases count >= TEST_MAX_LOADED_MODELS, returns False."""
        # Return exactly TEST_MAX_LOADED_MODELS distinct models already loaded.
        models = [
            _make_model_dict(f"model-{i}") for i in range(TEST_MAX_LOADED_MODELS)
        ]
        mock_list.return_value = models
        # Each identifier is unique, so each maps to a different base name.
        mock_base_name.side_effect = lambda ident: ident

        manager = ModelLifecycleManager()
        result = manager.ensure_model_for_phase("new-model")

        assert result is False
        mock_load.assert_not_called()
        assert "new-model" not in manager._loaded_by_us

    # ------------------------------------------------------------------
    # load_model returns False — model NOT tracked
    # ------------------------------------------------------------------

    @pytest.mark.unit
    @patch("tests.fixtures.model_lifecycle.LMSHelper.load_model", return_value=False)
    @patch("tests.fixtures.model_lifecycle.LMSHelper.is_model_loaded", return_value=False)
    @patch("tests.fixtures.model_lifecycle.LMSHelper._get_base_model_name", return_value="model-x")
    @patch("tests.fixtures.model_lifecycle.LMSHelper.list_loaded_models", return_value=[])
    def test_ensure_model_load_fails(
        self, mock_list, mock_base_name, mock_is_loaded, mock_load
    ):
        """When load_model returns False, ensure_model_for_phase returns False and does not track."""
        manager = ModelLifecycleManager()
        result = manager.ensure_model_for_phase("model-x")

        assert result is False
        assert "model-x" not in manager._loaded_by_us

    # ------------------------------------------------------------------
    # load_model raises — returns False, model NOT tracked
    # ------------------------------------------------------------------

    @pytest.mark.unit
    @patch(
        "tests.fixtures.model_lifecycle.LMSHelper.load_model",
        side_effect=RuntimeError("LM Studio offline"),
    )
    @patch("tests.fixtures.model_lifecycle.LMSHelper.is_model_loaded", return_value=False)
    @patch("tests.fixtures.model_lifecycle.LMSHelper._get_base_model_name", return_value="model-x")
    @patch("tests.fixtures.model_lifecycle.LMSHelper.list_loaded_models", return_value=[])
    def test_ensure_model_load_exception(
        self, mock_list, mock_base_name, mock_is_loaded, mock_load
    ):
        """When load_model raises an exception, returns False without propagating."""
        manager = ModelLifecycleManager()
        result = manager.ensure_model_for_phase("model-x")

        assert result is False
        assert "model-x" not in manager._loaded_by_us

    # ------------------------------------------------------------------
    # Custom TTL is forwarded to load_model
    # ------------------------------------------------------------------

    @pytest.mark.unit
    @patch("tests.fixtures.model_lifecycle.LMSHelper.load_model", return_value=True)
    @patch("tests.fixtures.model_lifecycle.LMSHelper.is_model_loaded", return_value=False)
    @patch("tests.fixtures.model_lifecycle.LMSHelper._get_base_model_name", return_value="model-y")
    @patch("tests.fixtures.model_lifecycle.LMSHelper.list_loaded_models", return_value=[])
    def test_ensure_model_custom_ttl(
        self, mock_list, mock_base_name, mock_is_loaded, mock_load
    ):
        """Custom ttl parameter is forwarded to LMSHelper.load_model()."""
        custom_ttl = 600
        manager = ModelLifecycleManager()
        result = manager.ensure_model_for_phase("model-y", ttl=custom_ttl)

        assert result is True
        mock_load.assert_called_once_with("model-y", ttl=custom_ttl)

    # ------------------------------------------------------------------
    # Default TTL (TEST_MODEL_TTL) used when ttl=None
    # ------------------------------------------------------------------

    @pytest.mark.unit
    @patch("tests.fixtures.model_lifecycle.LMSHelper.load_model", return_value=True)
    @patch("tests.fixtures.model_lifecycle.LMSHelper.is_model_loaded", return_value=False)
    @patch("tests.fixtures.model_lifecycle.LMSHelper._get_base_model_name", return_value="model-z")
    @patch("tests.fixtures.model_lifecycle.LMSHelper.list_loaded_models", return_value=[])
    def test_ensure_model_default_ttl(
        self, mock_list, mock_base_name, mock_is_loaded, mock_load
    ):
        """When ttl is not provided, TEST_MODEL_TTL constant is passed to load_model."""
        manager = ModelLifecycleManager()
        result = manager.ensure_model_for_phase("model-z")

        assert result is True
        mock_load.assert_called_once_with("model-z", ttl=TEST_MODEL_TTL)


# ==============================================================================
# unload_models_we_loaded()
# ==============================================================================

class TestUnloadModelsWeLoaded:
    """Tests for ModelLifecycleManager.unload_models_we_loaded()."""

    # ------------------------------------------------------------------
    # Nothing tracked — returns 0 without any calls
    # ------------------------------------------------------------------

    @pytest.mark.unit
    @patch("tests.fixtures.model_lifecycle.LMSHelper.unload_model")
    def test_unload_nothing_loaded(self, mock_unload):
        """When _loaded_by_us is empty, returns 0 and makes no unload calls."""
        manager = ModelLifecycleManager()
        result = manager.unload_models_we_loaded()

        assert result == 0
        mock_unload.assert_not_called()

    # ------------------------------------------------------------------
    # Two tracked models — both unloaded, set cleared
    # ------------------------------------------------------------------

    @pytest.mark.unit
    @patch("tests.fixtures.model_lifecycle.LMSHelper.unload_model")
    def test_unload_all_tracked_models(self, mock_unload):
        """All tracked models are unloaded and _loaded_by_us is cleared."""
        manager = ModelLifecycleManager()
        manager._loaded_by_us = {"model-a", "model-b"}

        result = manager.unload_models_we_loaded()

        assert result == 2
        assert mock_unload.call_count == 2
        unloaded = {call.args[0] for call in mock_unload.call_args_list}
        assert unloaded == {"model-a", "model-b"}
        # Set must be cleared after teardown.
        assert len(manager._loaded_by_us) == 0

    # ------------------------------------------------------------------
    # One unload fails — continues, partial count, set still cleared
    # ------------------------------------------------------------------

    @pytest.mark.unit
    @patch("tests.fixtures.model_lifecycle.LMSHelper.unload_model")
    def test_unload_handles_failures(self, mock_unload):
        """When one unload raises, execution continues and returns partial count."""
        manager = ModelLifecycleManager()
        manager._loaded_by_us = {"model-ok", "model-fail"}

        # Raise for one specific model, succeed for the other.
        def _side_effect(name: str) -> None:
            if name == "model-fail":
                raise RuntimeError("Cannot unload")

        mock_unload.side_effect = _side_effect

        result = manager.unload_models_we_loaded()

        # Only one model successfully unloaded.
        assert result == 1
        assert mock_unload.call_count == 2
        # Set must still be cleared regardless of failures.
        assert len(manager._loaded_by_us) == 0


# ==============================================================================
# models_we_loaded (property)
# ==============================================================================

class TestModelsWeLoadedProperty:
    """Tests for the models_we_loaded read-only property."""

    @pytest.mark.unit
    def test_models_we_loaded_empty_initially(self):
        """A freshly created manager has an empty frozenset."""
        manager = ModelLifecycleManager()
        result = manager.models_we_loaded

        assert isinstance(result, frozenset)
        assert len(result) == 0

    @pytest.mark.unit
    def test_models_we_loaded_returns_frozenset(self):
        """models_we_loaded reflects current _loaded_by_us as a frozenset."""
        manager = ModelLifecycleManager()
        manager._loaded_by_us = {"model-a", "model-b", "model-c"}

        result = manager.models_we_loaded

        assert isinstance(result, frozenset)
        assert result == frozenset({"model-a", "model-b", "model-c"})

    @pytest.mark.unit
    def test_models_we_loaded_is_immutable(self):
        """Mutating the returned frozenset does not affect internal state."""
        manager = ModelLifecycleManager()
        manager._loaded_by_us = {"model-a"}

        snapshot = manager.models_we_loaded
        # frozenset does not support .add(), so attempting mutation raises TypeError.
        with pytest.raises(AttributeError):
            snapshot.add("intruder")  # type: ignore[attr-defined]

        # Internal set is unchanged.
        assert manager._loaded_by_us == {"model-a"}
