"""Tests for OPP-44: Per-tool circuit breaker.

Verifies that ToolCallGuard implements the closed → open → half_open → closed
state machine with per-tool isolation, configurable threshold, and reset timer.

Test categories:
- Happy: new tool closed, success keeps closed, half_open probe allowed
- Negative: open rejects, open before reset stays open, rapid calls all rejected
- Threshold: exactly at threshold trips open, threshold-1 stays closed
- Transitions: open→half_open after reset, half_open+success→closed, half_open+failure→open
- Isolation: independent breakers per tool
- Config: disabled breaker always allows
- State: BreakerState fields, failure creates state, success resets count
"""

import time

import pytest

from config.constants.tool_config import (
    CIRCUIT_BREAKER_RESET_SECONDS,
    CIRCUIT_BREAKER_THRESHOLD,
)
from tools.tool_call_guard import BreakerState, ToolCallGuard


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _trip_breaker(guard: ToolCallGuard, tool_name: str, count: int | None = None) -> None:
    """Record exactly `count` (default: THRESHOLD) failures to open the breaker."""
    n = count if count is not None else CIRCUIT_BREAKER_THRESHOLD
    for _ in range(n):
        guard.record_failure(tool_name)


# ---------------------------------------------------------------------------
# Happy path tests
# ---------------------------------------------------------------------------


class TestBreakerInitialState:
    """Happy — fresh breaker is always closed."""

    def test_new_tool_breaker_is_closed(self) -> None:
        """check_circuit for unknown tool → (True, None)."""
        guard = ToolCallGuard()
        allowed, reason = guard.check_circuit("brand_new_tool")
        assert allowed is True
        assert reason is None

    def test_success_keeps_breaker_closed(self) -> None:
        """record_success on a tool with no state → check still returns (True, None)."""
        guard = ToolCallGuard()
        guard.record_success("my_tool")
        allowed, reason = guard.check_circuit("my_tool")
        assert allowed is True
        assert reason is None


# ---------------------------------------------------------------------------
# Threshold / failure counting tests
# ---------------------------------------------------------------------------


class TestThresholdBehaviour:
    """Boundary — exact failure count controls state transitions."""

    def test_single_failure_stays_closed(self) -> None:
        """1 failure, check → still (True, None)."""
        guard = ToolCallGuard()
        guard.record_failure("tool_a")
        allowed, reason = guard.check_circuit("tool_a")
        assert allowed is True
        assert reason is None

    def test_exactly_at_threshold_minus_one_stays_closed(self) -> None:
        """THRESHOLD-1 failures → still closed."""
        guard = ToolCallGuard()
        _trip_breaker(guard, "tool_b", count=CIRCUIT_BREAKER_THRESHOLD - 1)
        allowed, reason = guard.check_circuit("tool_b")
        assert allowed is True
        assert reason is None

    def test_failures_at_threshold_trips_open(self) -> None:
        """Exactly THRESHOLD failures → breaker OPEN."""
        guard = ToolCallGuard()
        _trip_breaker(guard, "tool_c")
        allowed, reason = guard.check_circuit("tool_c")
        assert allowed is False
        assert reason is not None
        assert "tool_c" in reason

    def test_open_breaker_rejects_calls(self) -> None:
        """After tripping → check_circuit returns (False, non-empty reason string)."""
        guard = ToolCallGuard()
        _trip_breaker(guard, "memory__create_entities")
        allowed, reason = guard.check_circuit("memory__create_entities")
        assert allowed is False
        assert isinstance(reason, str)
        assert len(reason) > 0

    def test_record_failure_creates_state(self) -> None:
        """First failure for new tool creates a BreakerState entry."""
        guard = ToolCallGuard()
        guard.record_failure("fresh_tool")
        # Access internal state to verify creation
        state = guard._breaker_state.get("fresh_tool")
        assert state is not None
        assert state.failure_count == 1


# ---------------------------------------------------------------------------
# State transition tests
# ---------------------------------------------------------------------------


class TestStateTransitions:
    """State machine transitions: closed → open → half_open → closed/open."""

    def test_open_to_half_open_after_reset(self) -> None:
        """After RESET_SECONDS elapses, open breaker transitions to half_open and allows probe."""
        guard = ToolCallGuard()
        _trip_breaker(guard, "probe_tool")

        # Simulate time passing beyond reset window by back-dating opened_at
        state = guard._breaker_state["probe_tool"]
        state.opened_at = time.monotonic() - (CIRCUIT_BREAKER_RESET_SECONDS + 1.0)

        allowed, reason = guard.check_circuit("probe_tool")
        assert allowed is True
        assert reason is None
        assert state.status == "half_open"

    def test_half_open_success_closes(self) -> None:
        """half_open + record_success → status back to closed, count reset."""
        guard = ToolCallGuard()
        _trip_breaker(guard, "recover_tool")

        # Manually set to half_open
        state = guard._breaker_state["recover_tool"]
        state.status = "half_open"

        guard.record_success("recover_tool")
        assert state.status == "closed"
        assert state.failure_count == 0
        assert state.opened_at is None

    def test_half_open_failure_reopens(self) -> None:
        """half_open + record_failure → status back to open, timer reset."""
        guard = ToolCallGuard()
        # First, get to THRESHOLD failures to open
        _trip_breaker(guard, "flaky_tool")
        state = guard._breaker_state["flaky_tool"]
        state.status = "half_open"

        before = time.monotonic()
        guard.record_failure("flaky_tool")
        after = time.monotonic()

        assert state.status == "open"
        assert state.opened_at is not None
        # opened_at was refreshed (within the test window)
        assert before <= state.opened_at <= after + 0.1

    def test_open_before_reset_time_stays_open(self) -> None:
        """check_circuit at reset_time/2 → still OPEN."""
        guard = ToolCallGuard()
        _trip_breaker(guard, "slow_recover")

        # opened_at is recent (just now) — well before reset window
        allowed, reason = guard.check_circuit("slow_recover")
        assert allowed is False
        assert reason is not None


# ---------------------------------------------------------------------------
# Isolation tests
# ---------------------------------------------------------------------------


class TestBreakerIsolation:
    """Independence — each tool has its own breaker state."""

    def test_independent_breakers_per_tool(self) -> None:
        """tool_a fails past threshold; tool_b is unaffected."""
        guard = ToolCallGuard()
        _trip_breaker(guard, "tool_a")

        # tool_b has no failures
        allowed, reason = guard.check_circuit("tool_b")
        assert allowed is True
        assert reason is None

    def test_success_resets_failure_count(self) -> None:
        """After some failures + record_success → failure_count == 0."""
        guard = ToolCallGuard()
        _trip_breaker(guard, "resetable_tool", count=CIRCUIT_BREAKER_THRESHOLD - 1)
        guard.record_success("resetable_tool")

        state = guard._breaker_state.get("resetable_tool")
        assert state is not None
        assert state.failure_count == 0


# ---------------------------------------------------------------------------
# Disabled breaker tests
# ---------------------------------------------------------------------------


class TestDisabledBreaker:
    """Config — CIRCUIT_BREAKER_ENABLED=False bypasses all state checks."""

    def test_disabled_breaker_always_allows(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Monkeypatch ENABLED=False → always (True, None) regardless of state."""
        import tools.tool_call_guard as guard_mod

        monkeypatch.setattr(guard_mod, "CIRCUIT_BREAKER_ENABLED", False)

        guard = ToolCallGuard()
        _trip_breaker(guard, "blocked_tool")

        allowed, reason = guard.check_circuit("blocked_tool")
        assert allowed is True
        assert reason is None

    def test_rapid_calls_during_open_all_rejected(self) -> None:
        """Multiple check_circuit calls when OPEN → all return False."""
        guard = ToolCallGuard()
        _trip_breaker(guard, "storm_tool")

        results = [guard.check_circuit("storm_tool") for _ in range(10)]
        assert all(allowed is False for allowed, _ in results)


# ---------------------------------------------------------------------------
# BreakerState dataclass tests
# ---------------------------------------------------------------------------


class TestBreakerStateDataclass:
    """Verify BreakerState has the expected fields and defaults."""

    def test_breaker_state_fields(self) -> None:
        """BreakerState dataclass has: status, failure_count, last_failure_time, opened_at."""
        state = BreakerState()
        assert hasattr(state, "status")
        assert hasattr(state, "failure_count")
        assert hasattr(state, "last_failure_time")
        assert hasattr(state, "opened_at")

    def test_breaker_state_defaults(self) -> None:
        """Default state is closed with zero counters."""
        state = BreakerState()
        assert state.status == "closed"
        assert state.failure_count == 0
        assert state.last_failure_time == 0.0
        assert state.opened_at is None
