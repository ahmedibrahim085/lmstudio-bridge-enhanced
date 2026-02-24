"""Tests for defense-in-depth session model cleanup.

Verifies _snapshot_loaded_models() and _unload_new_models() correctly:
- Snapshot initial models
- Unload only NEW models at teardown
- Handle errors gracefully
"""

from __future__ import annotations

from unittest.mock import patch

from config.constants import (
    MODEL_INVENTORY_REASON_LIFECYCLE,
    MODEL_INVENTORY_SCOPE_MODULE,
    MODEL_INVENTORY_SCOPE_SESSION,
)
from tests.conftest import _snapshot_loaded_models, _unload_new_models
from tests.fixtures.model_inventory import ModelLoadInventory
from tests.fixtures.model_lifecycle import ModelLifecycleManager
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

    def test_cleanup_removes_duplicates_at_teardown(self):
        """Duplicate instances (model:2, model:3) are cleaned at teardown."""
        mgr = ModelLifecycleManager()

        # Simulate 3 instances of one model
        loaded = [
            {
                "identifier": "test/model",
                "modelKey": "test/model",
                "status": "loaded",
                "instance_id": "inst-1",
            },
            {
                "identifier": "test/model",
                "modelKey": "test/model",
                "status": "loaded",
                "instance_id": "inst-2",
            },
            {
                "identifier": "test/model",
                "modelKey": "test/model",
                "status": "loaded",
                "instance_id": "inst-3",
            },
        ]

        mock_rest = type("MockRest", (), {"unload_model": None})()

        with (
            patch.object(LMSHelper, "list_loaded_models", return_value=loaded),
            patch.object(
                LMSHelper, "_get_base_model_name", return_value="test/model"
            ),
            patch.object(LMSHelper, "_get_rest_client", return_value=mock_rest),
            patch.object(mock_rest, "unload_model") as mock_unload,
        ):
            cleaned = mgr.cleanup_duplicates()

        # Should unload 2 duplicates (keep first, remove inst-2 and inst-3)
        assert cleaned == 2
        assert mock_unload.call_count == 2


class TestInventoryIntegration:
    """Verify inventory integrates with session cleanup and lifecycle manager.

    ADDITIVE: These tests supplement the 7 existing defense-in-depth tests above.
    """

    def test_inventory_cleanup_unloads_all_at_session_end(self):
        """inventory.unload_all() is called at session teardown."""
        inv = ModelLoadInventory()
        inv.record_load(
            "teardown-model",
            MODEL_INVENTORY_REASON_LIFECYCLE,
            "test::teardown",
            MODEL_INVENTORY_SCOPE_SESSION,
            "unit",
        )

        with patch.object(LMSHelper, "unload_model") as mock_unload:
            count = inv.unload_all()

        assert count == 1
        mock_unload.assert_called_once_with("teardown-model")

    def test_module_cleanup_unloads_module_scope(self):
        """Module-scoped fixture calls inventory.unload_scope('module')."""
        inv = ModelLoadInventory()
        inv.record_load("mod-model", MODEL_INVENTORY_REASON_LIFECYCLE, "t1", MODEL_INVENTORY_SCOPE_MODULE, "unit")
        inv.record_load("sess-model", MODEL_INVENTORY_REASON_LIFECYCLE, "t2", MODEL_INVENTORY_SCOPE_SESSION, "unit")

        with patch.object(LMSHelper, "unload_model") as mock_unload:
            count = inv.unload_scope(MODEL_INVENTORY_SCOPE_MODULE)

        # Only module-scoped model unloaded
        assert count == 1
        mock_unload.assert_called_once_with("mod-model")

        # Session model still active
        active = inv.get_active_for_scope(MODEL_INVENTORY_SCOPE_SESSION)
        assert "sess-model" in active

    def test_lifecycle_records_to_inventory(self):
        """ensure_model_for_phase() calls inventory.record_load() with metadata."""
        inv = ModelLoadInventory()
        mgr = ModelLifecycleManager(inventory=inv)

        with (
            patch.object(LMSHelper, "list_loaded_models", return_value=[]),
            patch.object(LMSHelper, "is_model_loaded", return_value=False),
            patch.object(LMSHelper, "load_model", return_value=True),
        ):
            mgr.ensure_model_for_phase(
                "test/model-inv",
                test_id="tests/test_x.py::test_y",
                scope=MODEL_INVENTORY_SCOPE_SESSION,
            )

        # Verify inventory has the record
        active = inv.get_active_for_scope(MODEL_INVENTORY_SCOPE_SESSION)
        assert "test/model-inv" in active
