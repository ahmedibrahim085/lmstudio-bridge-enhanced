"""Tests for defense-in-depth session model cleanup.

Verifies _snapshot_loaded_models() and _unload_new_models() correctly:
- Snapshot initial models
- Unload only NEW models at teardown
- Handle errors gracefully
"""

from __future__ import annotations

from unittest.mock import patch

from tests.conftest import _snapshot_loaded_models, _unload_new_models
from utils.lms_helper import LMSHelper


def _make_model_entry(name: str) -> dict:
    """Create a mock model entry as returned by LMSHelper.list_loaded_models()."""
    return {"identifier": name, "modelKey": name}


class TestSessionModelCleanup:
    """Verify defense-in-depth cleanup logic."""

    def test_cleanup_unloads_new_models(self):
        """Models not in the initial snapshot get unload_model() called."""
        initial_entries = [_make_model_entry("model-a")]
        after_entries = [_make_model_entry("model-a"), _make_model_entry("model-b")]

        with patch.object(LMSHelper, "_get_base_model_name", side_effect=lambda x: x):
            with patch.object(LMSHelper, "list_loaded_models", return_value=initial_entries):
                initial = _snapshot_loaded_models()

            with (
                patch.object(LMSHelper, "list_loaded_models", return_value=after_entries),
                patch.object(LMSHelper, "unload_model") as mock_unload,
            ):
                _unload_new_models(initial)

            mock_unload.assert_called_once_with("model-b")

    def test_cleanup_preserves_initial_models(self):
        """Models present before tests are NOT unloaded."""
        entries = [_make_model_entry("model-a"), _make_model_entry("model-b")]

        with patch.object(LMSHelper, "_get_base_model_name", side_effect=lambda x: x):
            with patch.object(LMSHelper, "list_loaded_models", return_value=entries):
                initial = _snapshot_loaded_models()

            with (
                patch.object(LMSHelper, "list_loaded_models", return_value=entries),
                patch.object(LMSHelper, "unload_model") as mock_unload,
            ):
                _unload_new_models(initial)

            mock_unload.assert_not_called()

    def test_cleanup_handles_lmstudio_unavailable(self):
        """No crash when list_loaded_models() raises during snapshot."""
        with patch.object(
            LMSHelper, "list_loaded_models", side_effect=ConnectionError("down")
        ):
            # _snapshot_loaded_models raises — caller (fixture) catches it
            try:
                _snapshot_loaded_models()
                raised = False
            except ConnectionError:
                raised = True

            assert raised, "Should propagate exception for fixture to handle"

    def test_cleanup_handles_unload_failure(self):
        """Continues cleanup if one model fails to unload."""
        initial_entries = [_make_model_entry("model-a")]
        after_entries = [
            _make_model_entry("model-a"),
            _make_model_entry("model-b"),
            _make_model_entry("model-c"),
        ]

        def unload_side_effect(name):
            if name == "model-b":
                raise RuntimeError("unload failed")

        with patch.object(LMSHelper, "_get_base_model_name", side_effect=lambda x: x):
            with patch.object(LMSHelper, "list_loaded_models", return_value=initial_entries):
                initial = _snapshot_loaded_models()

            with (
                patch.object(LMSHelper, "list_loaded_models", return_value=after_entries),
                patch.object(
                    LMSHelper, "unload_model", side_effect=unload_side_effect
                ) as mock_unload,
            ):
                _unload_new_models(initial)

            # Both model-b and model-c should have been attempted
            assert mock_unload.call_count == 2

    def test_snapshot_empty_when_no_models(self):
        """Empty snapshot when list_loaded_models() returns []."""
        after_entries = [_make_model_entry("model-new")]

        with patch.object(LMSHelper, "_get_base_model_name", side_effect=lambda x: x):
            with patch.object(LMSHelper, "list_loaded_models", return_value=[]):
                initial = _snapshot_loaded_models()

            assert initial == set()

            with (
                patch.object(LMSHelper, "list_loaded_models", return_value=after_entries),
                patch.object(LMSHelper, "unload_model") as mock_unload,
            ):
                _unload_new_models(initial)

            mock_unload.assert_called_once_with("model-new")
