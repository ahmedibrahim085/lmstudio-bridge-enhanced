"""Tests for lifecycle manager wiring through fixtures.

Verifies that model-loading fixtures route through
ModelLifecycleManager.ensure_model_for_phase() (tracked path)
instead of the standalone ensure_model_loaded() (untracked path).
"""

from __future__ import annotations

import inspect
from unittest.mock import patch

from tests.fixtures.model_lifecycle import ModelLifecycleManager
from utils.lms_helper import LMSHelper

# ---------------------------------------------------------------------------
# Fixture → lifecycle wiring (structural verification)
# ---------------------------------------------------------------------------

class TestFixtureLifecycleWiring:
    """Verify fixtures accept model_lifecycle and call ensure_model_for_phase."""

    def test_require_any_model_uses_lifecycle(self):
        """require_any_model must accept model_lifecycle and call ensure_model_for_phase."""
        from tests.fixtures.model_management import require_any_model

        sig = inspect.signature(require_any_model)
        assert "model_lifecycle" in sig.parameters, (
            "require_any_model must accept 'model_lifecycle' parameter"
        )

        source = inspect.getsource(require_any_model)
        assert "ensure_model_for_phase" in source, (
            "require_any_model must call ensure_model_for_phase (tracked path)"
        )

    def test_require_model_with_capability_uses_lifecycle(self):
        """require_model_with_capability must use lifecycle manager."""
        from tests.fixtures.model_management import require_model_with_capability

        sig = inspect.signature(require_model_with_capability)
        assert "model_lifecycle" in sig.parameters, (
            "require_model_with_capability must accept 'model_lifecycle' parameter"
        )

        source = inspect.getsource(require_model_with_capability)
        assert "ensure_model_for_phase" in source, (
            "require_model_with_capability must call ensure_model_for_phase (tracked path)"
        )


# ---------------------------------------------------------------------------
# Lifecycle manager internal tracking
# ---------------------------------------------------------------------------

class TestLifecycleTracking:
    """Verify lifecycle manager tracks loaded models and cleans up."""

    def test_lifecycle_tracks_loaded_model(self):
        """After ensure_model_for_phase(), model is in _loaded_by_us."""
        mgr = ModelLifecycleManager()

        with (
            patch.object(LMSHelper, "list_loaded_models", return_value=[]),
            patch.object(LMSHelper, "is_model_loaded", return_value=False),
            patch.object(LMSHelper, "load_model", return_value=True),
        ):
            result = mgr.ensure_model_for_phase("test/model")

        assert result is True
        assert "test/model" in mgr._loaded_by_us

    def test_lifecycle_teardown_unloads_tracked(self):
        """unload_models_we_loaded() calls unload_model() for tracked models."""
        mgr = ModelLifecycleManager()
        mgr._loaded_by_us = {"model-a", "model-b"}

        with patch.object(LMSHelper, "unload_model") as mock_unload:
            count = mgr.unload_models_we_loaded()

        assert count == 2
        unloaded_names = {c.args[0] for c in mock_unload.call_args_list}
        assert unloaded_names == {"model-a", "model-b"}
        assert len(mgr._loaded_by_us) == 0
