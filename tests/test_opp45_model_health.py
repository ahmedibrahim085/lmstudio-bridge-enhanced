"""Tests for OPP-45: Per-model error budget with advisory demotion.

TDD RED phase — all tests fail until tools/model_health.py is created.

Test categories:
- TestModelHealthActive: models below/at error threshold stay "active"
- TestModelHealthDegraded: models over threshold become "degraded"
- TestModelHealthSuspended: sustained degradation leads to "suspended"
- TestErrorTracking: record_llm_call and record_tool_error update internal state
- TestReset: reset() clears single model or all models
- TestEdgeCases: independent models, threshold=0 instant demotion
- TestDataclass: ModelHealth fields are accessible
"""

import time

import pytest

from tools.model_health import ModelHealth, ModelHealthTracker


class TestModelHealthActive:
    def test_new_model_is_active(self):
        tracker = ModelHealthTracker()
        assert tracker.check_health("model-a") == "active"

    def test_model_under_budget_stays_active(self):
        # 10 calls, 2 failures (20% < 30% threshold) → "active"
        tracker = ModelHealthTracker(threshold=0.3)
        for _ in range(8):
            tracker.record_llm_call("model-a", success=True, elapsed=1.0)
        for _ in range(2):
            tracker.record_llm_call("model-a", success=False, elapsed=1.0)
        assert tracker.check_health("model-a") == "active"

    def test_model_at_budget_stays_active(self):
        # Exactly at threshold (30%) → still "active" (not exceeded)
        tracker = ModelHealthTracker(threshold=0.3)
        for _ in range(7):
            tracker.record_llm_call("model-a", success=True, elapsed=1.0)
        for _ in range(3):
            tracker.record_llm_call("model-a", success=False, elapsed=1.0)
        assert tracker.check_health("model-a") == "active"

    def test_check_health_creates_entry(self):
        tracker = ModelHealthTracker()
        assert tracker.check_health("never-seen") == "active"

    def test_empty_window_is_active(self):
        tracker = ModelHealthTracker()
        tracker.check_health("model-x")
        assert tracker.check_health("model-x") == "active"


class TestModelHealthDegraded:
    def test_model_over_budget_becomes_degraded(self):
        # 10 calls, 4 failures (40% > 30%) → "degraded"
        tracker = ModelHealthTracker(threshold=0.3)
        for _ in range(6):
            tracker.record_llm_call("model-a", success=True, elapsed=1.0)
        for _ in range(4):
            tracker.record_llm_call("model-a", success=False, elapsed=1.0)
        assert tracker.check_health("model-a") == "degraded"

    def test_degraded_before_cooldown_stays_degraded(self, monkeypatch):
        tracker = ModelHealthTracker(threshold=0.3, cooldown_seconds=120.0)
        current_time = 1000.0
        monkeypatch.setattr("time.monotonic", lambda: current_time)
        # Push to degraded
        for _ in range(6):
            tracker.record_llm_call("model-a", success=True, elapsed=1.0)
        for _ in range(4):
            tracker.record_llm_call("model-a", success=False, elapsed=1.0)
        assert tracker.check_health("model-a") == "degraded"
        # Advance 60s (less than cooldown 120s) → stays degraded
        current_time = 1060.0
        monkeypatch.setattr("time.monotonic", lambda: current_time)
        assert tracker.check_health("model-a") == "degraded"

    def test_degraded_after_cooldown_recovers(self, monkeypatch):
        tracker = ModelHealthTracker(threshold=0.3, cooldown_seconds=120.0, window_seconds=300.0)
        current_time = 1000.0
        monkeypatch.setattr("time.monotonic", lambda: current_time)
        # Push to degraded (4/10 = 40%)
        for _ in range(6):
            tracker.record_llm_call("model-a", success=True, elapsed=1.0)
        for _ in range(4):
            tracker.record_llm_call("model-a", success=False, elapsed=1.0)
        assert tracker.check_health("model-a") == "degraded"
        # Advance past cooldown AND past window (errors slide out)
        current_time = 1500.0  # 500s later, past 300s window
        monkeypatch.setattr("time.monotonic", lambda: current_time)
        assert tracker.check_health("model-a") == "active"


class TestModelHealthSuspended:
    def test_sustained_degradation_becomes_suspended(self, monkeypatch):
        tracker = ModelHealthTracker(threshold=0.3, cooldown_seconds=60.0, window_seconds=300.0)
        current_time = 1000.0
        monkeypatch.setattr("time.monotonic", lambda: current_time)
        # Push to degraded
        for _ in range(6):
            tracker.record_llm_call("model-a", success=True, elapsed=1.0)
        for _ in range(4):
            tracker.record_llm_call("model-a", success=False, elapsed=1.0)
        assert tracker.check_health("model-a") == "degraded"
        # Advance past cooldown, but add more errors to stay over threshold
        current_time = 1070.0
        monkeypatch.setattr("time.monotonic", lambda: current_time)
        for _ in range(3):
            tracker.record_llm_call("model-a", success=True, elapsed=1.0)
        for _ in range(4):
            tracker.record_llm_call("model-a", success=False, elapsed=1.0)
        # Should now be suspended (sustained failure)
        assert tracker.check_health("model-a") == "suspended"


class TestErrorTracking:
    def test_record_llm_call_success_tracked(self):
        tracker = ModelHealthTracker()
        tracker.record_llm_call("model-a", success=True, elapsed=1.0)
        health = tracker._models.get("model-a")
        assert health is not None
        assert health.total_calls == 1
        assert health.total_errors == 0

    def test_record_llm_call_failure_tracked(self):
        tracker = ModelHealthTracker()
        tracker.record_llm_call("model-a", success=False, elapsed=1.0)
        health = tracker._models.get("model-a")
        assert health is not None
        assert health.total_calls == 1
        assert health.total_errors == 1

    def test_record_tool_error_counts(self):
        tracker = ModelHealthTracker()
        tracker.record_tool_error("model-a", "memory__create_entities", "invalid_args")
        health = tracker._models.get("model-a")
        assert health is not None
        assert health.total_errors == 1

    def test_errors_outside_window_dont_count(self, monkeypatch):
        tracker = ModelHealthTracker(threshold=0.3, window_seconds=60.0)
        current_time = 1000.0
        monkeypatch.setattr("time.monotonic", lambda: current_time)
        # Record errors at time 1000
        for _ in range(4):
            tracker.record_llm_call("model-a", success=False, elapsed=1.0)
        for _ in range(6):
            tracker.record_llm_call("model-a", success=True, elapsed=1.0)
        assert tracker.check_health("model-a") == "degraded"
        # Advance 70s (past 60s window) → errors slide out
        current_time = 1070.0
        monkeypatch.setattr("time.monotonic", lambda: current_time)
        assert tracker.check_health("model-a") == "active"


class TestReset:
    def test_reset_single_model(self):
        tracker = ModelHealthTracker()
        tracker.record_llm_call("model-a", success=False, elapsed=1.0)
        tracker.record_llm_call("model-b", success=False, elapsed=1.0)
        tracker.reset("model-a")
        assert "model-a" not in tracker._models
        assert "model-b" in tracker._models

    def test_reset_all_models(self):
        tracker = ModelHealthTracker()
        tracker.record_llm_call("model-a", success=False, elapsed=1.0)
        tracker.record_llm_call("model-b", success=False, elapsed=1.0)
        tracker.reset()
        assert len(tracker._models) == 0


class TestEdgeCases:
    def test_independent_models(self):
        tracker = ModelHealthTracker(threshold=0.3)
        # Model A: 100% errors → degraded
        for _ in range(5):
            tracker.record_llm_call("model-a", success=False, elapsed=1.0)
        # Model B: 100% success → active
        for _ in range(5):
            tracker.record_llm_call("model-b", success=True, elapsed=1.0)
        assert tracker.check_health("model-a") == "degraded"
        assert tracker.check_health("model-b") == "active"

    def test_threshold_zero_instant_demotion(self):
        tracker = ModelHealthTracker(threshold=0.0)
        tracker.record_llm_call("model-a", success=False, elapsed=1.0)
        assert tracker.check_health("model-a") == "degraded"


class TestDataclass:
    def test_model_health_fields(self):
        health = ModelHealth(
            model_key="test",
            status="active",
            errors_in_window=[],
            calls_in_window=[],
            total_calls=0,
            total_errors=0,
            demoted_at=None,
            last_recovery_check=None,
        )
        assert health.model_key == "test"
        assert health.status == "active"
