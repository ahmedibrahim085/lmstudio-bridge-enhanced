"""Tests for Model Loading Inventory system.

Verifies ModelLoadInventory correctly:
- Records model loads with full metadata (timestamp, reason, test_id, scope, phase)
- Tracks active vs unloaded models
- Provides scoped cleanup (unload by scope)
- Persists audit trail to JSON per session
- All unload methods are IDEMPOTENT (double-unload = no-op)

RED phase: These tests FAIL because ModelLoadInventory stub has no methods.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config.constants import (
    MODEL_INVENTORY_REASON_DIRECT,
    MODEL_INVENTORY_REASON_FIXTURE,
    MODEL_INVENTORY_REASON_LIFECYCLE,
    MODEL_INVENTORY_SCOPE_CLASS,
    MODEL_INVENTORY_SCOPE_MODULE,
    MODEL_INVENTORY_SCOPE_SESSION,
)
from tests.fixtures.model_inventory import ModelLoadInventory
from utils.lms_helper import LMSHelper


@pytest.mark.unit
class TestModelLoadInventoryRecording:
    """Verify load/unload recording and metadata tracking."""

    def test_record_load_adds_to_active(self):
        """After record_load(), model is in _active dict."""
        inv = ModelLoadInventory()
        inv.record_load(
            model_name="test/model-a",
            reason=MODEL_INVENTORY_REASON_FIXTURE,
            test_id="tests/test_foo.py::test_bar",
            scope=MODEL_INVENTORY_SCOPE_SESSION,
            phase="unit",
        )

        active = inv.get_active_for_scope(MODEL_INVENTORY_SCOPE_SESSION)
        assert "test/model-a" in active

    def test_record_load_stores_metadata(self):
        """Record has correct timestamp, reason, test_id, scope, phase."""
        inv = ModelLoadInventory()
        inv.record_load(
            model_name="test/model-b",
            reason=MODEL_INVENTORY_REASON_LIFECYCLE,
            test_id="tests/test_x.py::TestY::test_z",
            scope=MODEL_INVENTORY_SCOPE_MODULE,
            phase="integration",
            vram_estimate="4GB",
        )

        # Check that record exists and has metadata
        assert hasattr(inv, "_records")
        assert len(inv._records) >= 1

        record = inv._records[-1]
        assert record.model_name == "test/model-b"
        assert record.reason == MODEL_INVENTORY_REASON_LIFECYCLE
        assert record.test_id == "tests/test_x.py::TestY::test_z"
        assert record.scope == MODEL_INVENTORY_SCOPE_MODULE
        assert record.phase == "integration"
        assert record.loaded_at != ""  # ISO 8601 timestamp
        assert record.metadata.get("vram_estimate") == "4GB"
        assert record.unloaded is False

    def test_record_unload_marks_inactive(self):
        """After record_unload(), model removed from _active, unloaded=True."""
        inv = ModelLoadInventory()
        inv.record_load(
            model_name="test/model-c",
            reason=MODEL_INVENTORY_REASON_DIRECT,
            test_id="test::unload",
            scope=MODEL_INVENTORY_SCOPE_SESSION,
            phase="unit",
        )

        with patch.object(LMSHelper, "unload_model"):
            inv.record_unload("test/model-c")

        active = inv.get_active_for_scope(MODEL_INVENTORY_SCOPE_SESSION)
        assert "test/model-c" not in active

        # Check the record is marked as unloaded
        record = inv._records[-1]
        assert record.unloaded is True
        assert record.unloaded_at is not None
        assert record.unloaded_at != ""

    def test_duplicate_load_updates_record(self):
        """Loading same model twice updates existing record (no duplicates in active)."""
        inv = ModelLoadInventory()
        inv.record_load(
            model_name="test/dup-model",
            reason=MODEL_INVENTORY_REASON_FIXTURE,
            test_id="test::first",
            scope=MODEL_INVENTORY_SCOPE_SESSION,
            phase="unit",
        )
        inv.record_load(
            model_name="test/dup-model",
            reason=MODEL_INVENTORY_REASON_LIFECYCLE,
            test_id="test::second",
            scope=MODEL_INVENTORY_SCOPE_MODULE,
            phase="e2e",
        )

        # Should have 2 records total (audit trail), but only 1 active entry
        active = inv.get_active_for_scope(MODEL_INVENTORY_SCOPE_SESSION)
        active_module = inv.get_active_for_scope(MODEL_INVENTORY_SCOPE_MODULE)

        # The model should appear in active (under whichever scope it was last loaded)
        all_active = list(active) + list(active_module)
        assert "test/dup-model" in all_active


@pytest.mark.unit
class TestModelLoadInventoryScoping:
    """Verify scope-based filtering and cleanup."""

    def test_get_active_for_scope_filters_correctly(self):
        """Returns only models loaded at the given scope."""
        inv = ModelLoadInventory()
        inv.record_load("model-session", MODEL_INVENTORY_REASON_FIXTURE, "t1", MODEL_INVENTORY_SCOPE_SESSION, "unit")
        inv.record_load("model-class", MODEL_INVENTORY_REASON_FIXTURE, "t2", MODEL_INVENTORY_SCOPE_CLASS, "unit")
        inv.record_load("model-module", MODEL_INVENTORY_REASON_FIXTURE, "t3", MODEL_INVENTORY_SCOPE_MODULE, "unit")

        session_models = inv.get_active_for_scope(MODEL_INVENTORY_SCOPE_SESSION)
        class_models = inv.get_active_for_scope(MODEL_INVENTORY_SCOPE_CLASS)

        assert "model-session" in session_models
        assert "model-class" not in session_models
        assert "model-class" in class_models
        assert "model-session" not in class_models

    def test_unload_scope_unloads_only_that_scope(self):
        """unload_scope('class') unloads class-scoped models, preserves session-scoped."""
        inv = ModelLoadInventory()
        inv.record_load("keep-model", MODEL_INVENTORY_REASON_FIXTURE, "t1", MODEL_INVENTORY_SCOPE_SESSION, "unit")
        inv.record_load("remove-model", MODEL_INVENTORY_REASON_FIXTURE, "t2", MODEL_INVENTORY_SCOPE_CLASS, "unit")

        with patch.object(LMSHelper, "unload_model") as mock_unload:
            count = inv.unload_scope(MODEL_INVENTORY_SCOPE_CLASS)

        assert count == 1
        mock_unload.assert_called_once_with("remove-model")

        # Session model still active
        session_models = inv.get_active_for_scope(MODEL_INVENTORY_SCOPE_SESSION)
        assert "keep-model" in session_models

    def test_unload_scope_returns_count(self):
        """Returns correct count of models unloaded."""
        inv = ModelLoadInventory()
        inv.record_load("m1", MODEL_INVENTORY_REASON_FIXTURE, "t1", MODEL_INVENTORY_SCOPE_MODULE, "unit")
        inv.record_load("m2", MODEL_INVENTORY_REASON_FIXTURE, "t2", MODEL_INVENTORY_SCOPE_MODULE, "unit")
        inv.record_load("m3", MODEL_INVENTORY_REASON_FIXTURE, "t3", MODEL_INVENTORY_SCOPE_SESSION, "unit")

        with patch.object(LMSHelper, "unload_model"):
            count = inv.unload_scope(MODEL_INVENTORY_SCOPE_MODULE)

        assert count == 2

    def test_unload_all_clears_everything(self):
        """All active models get unload_model() called."""
        inv = ModelLoadInventory()
        inv.record_load("m1", MODEL_INVENTORY_REASON_FIXTURE, "t1", MODEL_INVENTORY_SCOPE_SESSION, "unit")
        inv.record_load("m2", MODEL_INVENTORY_REASON_FIXTURE, "t2", MODEL_INVENTORY_SCOPE_MODULE, "unit")
        inv.record_load("m3", MODEL_INVENTORY_REASON_FIXTURE, "t3", MODEL_INVENTORY_SCOPE_CLASS, "unit")

        with patch.object(LMSHelper, "unload_model") as mock_unload:
            count = inv.unload_all()

        assert count == 3
        assert mock_unload.call_count == 3
        unloaded_names = {c.args[0] for c in mock_unload.call_args_list}
        assert unloaded_names == {"m1", "m2", "m3"}

    def test_unload_scope_handles_failure_gracefully(self):
        """Continues unloading if one model fails, logs warning."""
        inv = ModelLoadInventory()
        inv.record_load("fail-model", MODEL_INVENTORY_REASON_FIXTURE, "t1", MODEL_INVENTORY_SCOPE_CLASS, "unit")
        inv.record_load("ok-model", MODEL_INVENTORY_REASON_FIXTURE, "t2", MODEL_INVENTORY_SCOPE_CLASS, "unit")

        def unload_side_effect(name):
            if name == "fail-model":
                raise RuntimeError("unload failed")

        with patch.object(LMSHelper, "unload_model", side_effect=unload_side_effect) as mock_unload:
            count = inv.unload_scope(MODEL_INVENTORY_SCOPE_CLASS)

        # Both should have been attempted
        assert mock_unload.call_count == 2
        # At least one succeeded
        assert count >= 1


@pytest.mark.unit
class TestModelLoadInventoryIdempotency:
    """Verify idempotent behavior (double-unload = no-op)."""

    def test_record_unload_idempotent(self):
        """Calling record_unload() on already-unloaded model is a no-op."""
        inv = ModelLoadInventory()
        inv.record_load("model-x", MODEL_INVENTORY_REASON_FIXTURE, "t1", MODEL_INVENTORY_SCOPE_SESSION, "unit")

        with patch.object(LMSHelper, "unload_model") as mock_unload:
            inv.record_unload("model-x")
            # Second call should be a no-op — no LMSHelper call
            inv.record_unload("model-x")

        mock_unload.assert_called_once_with("model-x")

    def test_unload_scope_idempotent(self):
        """Calling unload_scope('class') twice returns 0 on second call."""
        inv = ModelLoadInventory()
        inv.record_load("model-y", MODEL_INVENTORY_REASON_FIXTURE, "t1", MODEL_INVENTORY_SCOPE_CLASS, "unit")

        with patch.object(LMSHelper, "unload_model"):
            count1 = inv.unload_scope(MODEL_INVENTORY_SCOPE_CLASS)
            count2 = inv.unload_scope(MODEL_INVENTORY_SCOPE_CLASS)

        assert count1 == 1
        assert count2 == 0


@pytest.mark.unit
class TestModelLoadInventoryPersistence:
    """Verify JSON persistence and summary."""

    def test_save_creates_json_file(self, tmp_path):
        """JSON file created at expected path with correct structure."""
        inv = ModelLoadInventory(inventory_dir=str(tmp_path))
        inv.record_load("model-save", MODEL_INVENTORY_REASON_FIXTURE, "t1", MODEL_INVENTORY_SCOPE_SESSION, "unit")

        inv.save()

        # Find the JSON file
        json_files = list(tmp_path.glob("*.json"))
        assert len(json_files) == 1

        data = json.loads(json_files[0].read_text())
        assert "records" in data
        assert "session_id" in data
        assert len(data["records"]) >= 1

    def test_save_includes_all_records(self, tmp_path):
        """JSON contains both load and unload records with all metadata fields."""
        inv = ModelLoadInventory(inventory_dir=str(tmp_path))
        inv.record_load("model-a", MODEL_INVENTORY_REASON_FIXTURE, "t1", MODEL_INVENTORY_SCOPE_SESSION, "unit")
        inv.record_load("model-b", MODEL_INVENTORY_REASON_LIFECYCLE, "t2", MODEL_INVENTORY_SCOPE_MODULE, "e2e")

        with patch.object(LMSHelper, "unload_model"):
            inv.record_unload("model-a")

        inv.save()

        json_files = list(tmp_path.glob("*.json"))
        data = json.loads(json_files[0].read_text())

        assert len(data["records"]) == 2

        # Check all fields present
        for record in data["records"]:
            assert "model_name" in record
            assert "loaded_at" in record
            assert "reason" in record
            assert "test_id" in record
            assert "scope" in record
            assert "phase" in record
            assert "unloaded" in record

    def test_save_creates_directory_on_demand(self, tmp_path):
        """save() works even if inventory dir doesn't exist yet."""
        nested_dir = str(tmp_path / "deep" / "nested" / "inventory")
        inv = ModelLoadInventory(inventory_dir=nested_dir)
        inv.record_load("model-z", MODEL_INVENTORY_REASON_DIRECT, "t1", MODEL_INVENTORY_SCOPE_SESSION, "unit")

        inv.save()

        assert Path(nested_dir).exists()
        json_files = list(Path(nested_dir).glob("*.json"))
        assert len(json_files) == 1

    def test_summary_returns_correct_counts(self):
        """Summary dict has total, active, unloaded, by-scope breakdowns."""
        inv = ModelLoadInventory()
        inv.record_load("m1", MODEL_INVENTORY_REASON_FIXTURE, "t1", MODEL_INVENTORY_SCOPE_SESSION, "unit")
        inv.record_load("m2", MODEL_INVENTORY_REASON_FIXTURE, "t2", MODEL_INVENTORY_SCOPE_MODULE, "unit")
        inv.record_load("m3", MODEL_INVENTORY_REASON_FIXTURE, "t3", MODEL_INVENTORY_SCOPE_CLASS, "unit")

        with patch.object(LMSHelper, "unload_model"):
            inv.record_unload("m2")

        summary = inv.summary()

        assert summary["total"] == 3
        assert summary["active"] == 2
        assert summary["unloaded"] == 1
        assert MODEL_INVENTORY_SCOPE_SESSION in summary["by_scope"]
        assert MODEL_INVENTORY_SCOPE_MODULE in summary["by_scope"]
        assert MODEL_INVENTORY_SCOPE_CLASS in summary["by_scope"]
