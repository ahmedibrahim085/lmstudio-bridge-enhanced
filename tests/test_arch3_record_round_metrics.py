"""Tests for ARCH-3: extracted _record_round_metrics helper.

Verifies the helper method correctly records RoundMetrics with
the same behavior as the 4 duplicated blocks it replaces.

Test categories (Req 07):
- Happy: Tests 1, 2 — normal recording with correct field values
- Negative: Test 3 — exception in helper never propagates
- Edge: Test 4, 5 — empty tool_calls, zero errors
- Boundary: Test 6 — list at exactly 100 entries triggers pop(0)
"""

import pytest

from tools.dynamic_autonomous import DynamicAutonomousAgent
from tools.loop_metrics import RoundMetrics


@pytest.fixture
def agent():
    """Create a DynamicAutonomousAgent for testing."""
    return DynamicAutonomousAgent.__new__(DynamicAutonomousAgent)


class TestRecordRoundMetrics:
    """Tests for _record_round_metrics helper method."""

    def test_records_correct_fields(self, agent):
        """Happy: RoundMetrics created with exact field values."""
        metrics_list: list[RoundMetrics] = []
        tool_calls = [{"name": "read_file", "duration_seconds": 1.5, "success": True}]

        agent._record_round_metrics(
            round_metrics_list=metrics_list,
            completed_rounds=3,
            llm_call_duration=2.5,
            round_tool_calls=tool_calls,
            round_errors=0,
        )

        assert len(metrics_list) == 1
        rm = metrics_list[0]
        assert rm.round_number == 3
        assert rm.llm_call_duration_seconds == 2.5
        assert rm.tool_calls == tool_calls
        assert rm.error_count == 0

    def test_appends_multiple_rounds(self, agent):
        """Happy: Multiple calls append sequentially."""
        metrics_list: list[RoundMetrics] = []

        for i in range(5):
            agent._record_round_metrics(
                round_metrics_list=metrics_list,
                completed_rounds=i + 1,
                llm_call_duration=float(i),
                round_tool_calls=[],
                round_errors=i,
            )

        assert len(metrics_list) == 5
        assert metrics_list[0].round_number == 1
        assert metrics_list[4].round_number == 5
        assert metrics_list[4].error_count == 4

    def test_exception_never_propagates(self, agent):
        """Negative: Errors inside helper are swallowed (metrics must never break loop)."""
        # Pass a non-list to trigger an internal error
        broken_list = "not_a_list"  # type: ignore[assignment]

        # Should NOT raise — metrics must never break the autonomous loop
        agent._record_round_metrics(
            round_metrics_list=broken_list,
            completed_rounds=1,
            llm_call_duration=1.0,
            round_tool_calls=[],
            round_errors=0,
        )

    def test_empty_tool_calls(self, agent):
        """Edge: Empty tool_calls list recorded correctly."""
        metrics_list: list[RoundMetrics] = []

        agent._record_round_metrics(
            round_metrics_list=metrics_list,
            completed_rounds=1,
            llm_call_duration=0.5,
            round_tool_calls=[],
            round_errors=0,
        )

        assert metrics_list[0].tool_calls == []
        assert metrics_list[0].error_count == 0

    def test_zero_duration(self, agent):
        """Edge: Zero duration recorded correctly."""
        metrics_list: list[RoundMetrics] = []

        agent._record_round_metrics(
            round_metrics_list=metrics_list,
            completed_rounds=1,
            llm_call_duration=0.0,
            round_tool_calls=[],
            round_errors=0,
        )

        assert metrics_list[0].llm_call_duration_seconds == 0.0

    def test_cap_at_100_entries(self, agent):
        """Boundary: At exactly 100 entries, oldest is popped and new appended."""
        metrics_list: list[RoundMetrics] = []

        # Fill to exactly 100
        for i in range(100):
            agent._record_round_metrics(
                round_metrics_list=metrics_list,
                completed_rounds=i + 1,
                llm_call_duration=float(i),
                round_tool_calls=[],
                round_errors=0,
            )

        assert len(metrics_list) == 100
        assert metrics_list[0].round_number == 1  # First entry is round 1

        # Add one more — should pop oldest
        agent._record_round_metrics(
            round_metrics_list=metrics_list,
            completed_rounds=101,
            llm_call_duration=100.0,
            round_tool_calls=[],
            round_errors=0,
        )

        assert len(metrics_list) == 100  # Still 100
        assert metrics_list[0].round_number == 2  # Round 1 was popped
        assert metrics_list[-1].round_number == 101  # New entry at end
