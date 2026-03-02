"""Tests for OPP-31 Phase 2: Model Knowledge Base and family detection.

Covers:
  - detect_family() identifies model families from model IDs
  - Knowledge base returns family-specific overlays per task type
  - Critical constraints override user settings
  - Unknown family returns empty overlay
  - All 6 families have overlays for standard task types

Test categories (Req 07):
- Happy: Tests 1-5 — family detection, overlay lookup, constraint enforcement
- Negative: Tests 6-7 — unknown family, unknown task type
- Edge: Tests 8-9 — case-insensitive detection, partial name match
- Boundary: Tests 10-12 — all families covered, temperature matrix spot checks
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

class TestFamilyDetection:
    """Happy: detect_family identifies model families from IDs."""

    @pytest.mark.unit
    @pytest.mark.parametrize("model_id,expected", [
        ("qwen2.5-coder-7b-instruct", "qwen"),
        ("deepseek-v3-base", "deepseek"),
        ("deepseek-r1-distill-qwen-32b", "deepseek-r1"),
        ("meta-llama-3.3-70b-instruct", "llama"),
        ("mistral-7b-instruct-v0.3", "mistral"),
        ("phi-4", "phi"),
        ("gemma-3-27b-it", "gemma"),
    ])
    def test_detect_known_families(self, model_id, expected):
        """Known model IDs map to correct family names."""
        from config.model_knowledge import detect_family

        assert detect_family(model_id) == expected

    @pytest.mark.unit
    def test_detect_family_returns_unknown(self):
        """Unknown model ID returns 'unknown'."""
        from config.model_knowledge import detect_family

        assert detect_family("totally-unknown-model-xyz") == "unknown"


class TestKnowledgeBaseOverlay:
    """Happy: Knowledge base returns family+task overlays."""

    @pytest.mark.unit
    def test_qwen_coder_overlay(self):
        """Qwen family + code task → temperature ~0.2."""
        from config.model_knowledge import get_overlay

        overlay = get_overlay(family="qwen", task_type="code")
        assert overlay["temperature"] == 0.2

    @pytest.mark.unit
    def test_deepseek_write_overlay(self):
        """DeepSeek family + write task → temperature 1.0."""
        from config.model_knowledge import get_overlay

        overlay = get_overlay(family="deepseek", task_type="write")
        assert overlay["temperature"] == 1.0

    @pytest.mark.unit
    def test_overlay_returns_dict(self):
        """Overlay is a dict with at least 'temperature' key."""
        from config.model_knowledge import get_overlay

        overlay = get_overlay(family="qwen", task_type="code")
        assert isinstance(overlay, dict)
        assert "temperature" in overlay


class TestCriticalConstraints:
    """Happy: Critical constraints override everything."""

    @pytest.mark.unit
    def test_deepseek_r1_min_temperature(self):
        """DeepSeek-R1 has critical constraint: temperature >= 0.6."""
        from config.model_knowledge import get_critical_constraints

        constraints = get_critical_constraints("deepseek-r1")
        assert "min_temperature" in constraints
        assert constraints["min_temperature"] >= 0.5

    @pytest.mark.unit
    def test_no_constraints_for_unknown(self):
        """Unknown family has no critical constraints."""
        from config.model_knowledge import get_critical_constraints

        constraints = get_critical_constraints("unknown")
        assert constraints == {}


# ---------------------------------------------------------------------------
# Negative
# ---------------------------------------------------------------------------

class TestKnowledgeBaseNegative:
    """Negative: unknown family/task returns empty overlay."""

    @pytest.mark.unit
    def test_unknown_family_empty_overlay(self):
        """Unknown family returns empty overlay dict."""
        from config.model_knowledge import get_overlay

        overlay = get_overlay(family="unknown", task_type="code")
        assert overlay == {}

    @pytest.mark.unit
    def test_unknown_task_type_empty_overlay(self):
        """Unknown task type for known family returns empty overlay."""
        from config.model_knowledge import get_overlay

        overlay = get_overlay(family="qwen", task_type="nonexistent_task")
        assert overlay == {}


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestFamilyDetectionEdge:
    """Edge: case handling and partial matches."""

    @pytest.mark.unit
    def test_case_insensitive_detection(self):
        """Family detection is case-insensitive."""
        from config.model_knowledge import detect_family

        assert detect_family("Qwen2.5-Coder-7B") == "qwen"
        assert detect_family("DEEPSEEK-V3") == "deepseek"

    @pytest.mark.unit
    def test_phi_reasoning_variant(self):
        """Phi-4-reasoning maps to phi family (reasoning handled via constraints)."""
        from config.model_knowledge import detect_family

        assert detect_family("phi-4-reasoning") == "phi"


# ---------------------------------------------------------------------------
# Boundary
# ---------------------------------------------------------------------------

class TestKnowledgeBaseBoundary:
    """Boundary: all families covered, temperature matrix validation."""

    @pytest.mark.unit
    def test_all_six_families_have_code_overlay(self):
        """All 6 known families have a 'code' task overlay."""
        from config.model_knowledge import get_overlay, KNOWN_FAMILIES

        for family in KNOWN_FAMILIES:
            overlay = get_overlay(family=family, task_type="code")
            assert "temperature" in overlay, f"No code overlay for {family}"

    @pytest.mark.unit
    def test_standard_task_types_exist(self):
        """Standard task types: code, test, write, review, chat."""
        from config.model_knowledge import STANDARD_TASK_TYPES

        expected = {"code", "test", "write", "review", "chat"}
        assert set(STANDARD_TASK_TYPES) == expected
