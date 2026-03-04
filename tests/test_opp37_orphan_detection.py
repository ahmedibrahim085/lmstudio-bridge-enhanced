"""OPP-37: Orphan Detection — RED test suite.

Tests for ToolCallTracker that will FAIL because the module does not exist yet.

ALL tests import from tools.tool_call_tracker which does not exist until GREEN.
"""

import threading
import time
from unittest.mock import patch

import pytest

from tools.tool_call_tracker import ActiveCall, ToolCallTracker


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tracker(timeout: float = 120.0) -> ToolCallTracker:
    return ToolCallTracker(orphan_timeout=timeout)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestToolCallTrackerBasic:
    """Basic dispatch / complete lifecycle."""

    def test_completed_call_not_orphaned(self) -> None:
        """mark_dispatched + mark_completed → call absent from check_orphans."""
        tracker = _tracker(timeout=5.0)
        with patch("time.monotonic", return_value=0.0):
            tracker.mark_dispatched("id-1", "read_file")
        with patch("time.monotonic", return_value=3.0):
            tracker.mark_completed("id-1")
        # Advance past timeout; id-1 is already removed so must not appear
        with patch("time.monotonic", return_value=200.0):
            orphans = tracker.check_orphans()
        assert "id-1" not in orphans

    def test_timed_out_call_marked_orphaned(self) -> None:
        """mark_dispatched, advance time past timeout → check_orphans returns it."""
        tracker = _tracker(timeout=10.0)
        with patch("time.monotonic", return_value=0.0):
            tracker.mark_dispatched("id-2", "list_directory")
        # Advance well past the 10s timeout
        with patch("time.monotonic", return_value=15.0):
            orphans = tracker.check_orphans()
        assert "id-2" in orphans

    def test_exception_marks_orphaned(self) -> None:
        """mark_dispatched + mark_orphaned → orphan_count increments."""
        tracker = _tracker()
        tracker.mark_dispatched("id-3", "bad_tool")
        tracker.mark_orphaned("id-3")
        assert tracker.orphan_count == 1

    def test_orphan_counter_increments(self) -> None:
        """Multiple mark_orphaned calls → orphan_count == N."""
        tracker = _tracker()
        for i in range(5):
            tracker.mark_dispatched(f"id-{i}", "tool")
            tracker.mark_orphaned(f"id-{i}")
        assert tracker.orphan_count == 5

    def test_concurrent_dispatches_tracked_independently(self) -> None:
        """3 different call_ids are tracked separately."""
        tracker = _tracker(timeout=60.0)
        with patch("time.monotonic", return_value=0.0):
            tracker.mark_dispatched("a", "tool_a")
            tracker.mark_dispatched("b", "tool_b")
            tracker.mark_dispatched("c", "tool_c")
        # Only 'b' times out
        with patch("time.monotonic", return_value=61.0):
            tracker.mark_completed("a")
            tracker.mark_completed("c")
            orphans = tracker.check_orphans()
        assert "b" in orphans
        assert "a" not in orphans
        assert "c" not in orphans

    def test_exactly_at_timeout_is_orphaned(self) -> None:
        """dispatched_at + timeout == now → orphaned (>= semantics)."""
        tracker = _tracker(timeout=30.0)
        with patch("time.monotonic", return_value=0.0):
            tracker.mark_dispatched("id-edge", "some_tool")
        # Exactly at timeout boundary
        with patch("time.monotonic", return_value=30.0):
            orphans = tracker.check_orphans()
        assert "id-edge" in orphans

    def test_check_orphans_returns_correct_ids(self) -> None:
        """Only timed-out calls returned; non-timed-out calls excluded."""
        tracker = _tracker(timeout=20.0)
        with patch("time.monotonic", return_value=0.0):
            tracker.mark_dispatched("old", "tool_old")
        with patch("time.monotonic", return_value=15.0):
            tracker.mark_dispatched("recent", "tool_recent")
        # 25s elapsed: old (25 >= 20) → orphan; recent (10 < 20) → still active
        with patch("time.monotonic", return_value=25.0):
            orphans = tracker.check_orphans()
        assert "old" in orphans
        assert "recent" not in orphans

    def test_mark_completed_removes_from_active(self) -> None:
        """Completed call is removed from active tracking."""
        tracker = _tracker(timeout=5.0)
        tracker.mark_dispatched("id-rm", "cleanup_tool")
        tracker.mark_completed("id-rm")
        # Even past timeout, completed call must not appear
        with patch("time.monotonic", return_value=999.0):
            orphans = tracker.check_orphans()
        assert "id-rm" not in orphans

    def test_mark_orphaned_removes_from_active(self) -> None:
        """mark_orphaned removes the call from active tracking."""
        tracker = _tracker(timeout=5.0)
        tracker.mark_dispatched("id-orp", "stale_tool")
        tracker.mark_orphaned("id-orp")
        # Second check must not double-count
        with patch("time.monotonic", return_value=999.0):
            orphans = tracker.check_orphans()
        assert "id-orp" not in orphans
        assert tracker.orphan_count == 1  # Only counted once


class TestToolCallTrackerEdgeCases:
    """Edge cases: unknown IDs, no-ops."""

    def test_unknown_call_id_completed_is_noop(self) -> None:
        """mark_completed with unknown id does not crash."""
        tracker = _tracker()
        tracker.mark_completed("does-not-exist")  # Must not raise

    def test_unknown_call_id_orphaned_is_noop(self) -> None:
        """mark_orphaned with unknown id does not crash and does not increment counter."""
        tracker = _tracker()
        tracker.mark_orphaned("does-not-exist")  # Must not raise
        assert tracker.orphan_count == 0


class TestActiveCallDataclass:
    """Verify ActiveCall is a frozen dataclass with correct fields."""

    def test_active_call_fields(self) -> None:
        call = ActiveCall(call_id="x", tool_name="read_file", dispatched_at=1234.5)
        assert call.call_id == "x"
        assert call.tool_name == "read_file"
        assert call.dispatched_at == 1234.5

    def test_active_call_is_frozen(self) -> None:
        """ActiveCall must be immutable (frozen=True)."""
        call = ActiveCall(call_id="x", tool_name="t", dispatched_at=0.0)
        with pytest.raises((AttributeError, TypeError)):
            call.call_id = "mutated"  # type: ignore[misc]
