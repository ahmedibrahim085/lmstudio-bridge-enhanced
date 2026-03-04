"""Loop observability metrics for the autonomous agent loop (OPP-07)."""

from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "LoopMetrics",
    "RoundMetrics",
]


@dataclass
class RoundMetrics:
    """Metrics for a single round of the autonomous loop."""

    round_number: int
    llm_call_duration_seconds: float
    tool_calls: list[dict[str, Any]]  # [{name, duration_seconds, success}]
    error_count: int
    orphan_count: int = 0
    cache_hits: int = 0
    cache_misses: int = 0


@dataclass
class LoopMetrics:
    """Aggregate metrics for the entire autonomous loop execution."""

    total_rounds: int
    total_duration_seconds: float
    total_tool_calls: int
    total_errors: int
    final_status: str  # "completed" | "max_rounds" | "aborted" | "context_overflow"
    rounds: list[RoundMetrics] = field(default_factory=list)
    max_rounds_tracked: int = 100

    def to_dashboard_format(self) -> dict[str, Any]:
        """Convert to format expected by nano-agent dashboard.

        Dashboard contract (nano-agent/web/server.py:260-264):
        - execution_time_seconds: float
        - token_usage: None (LM Studio /v1/responses has no token counts)
        - rounds: int
        - tool_calls: int
        - errors: int
        - status: str
        """
        return {
            "execution_time_seconds": self.total_duration_seconds,
            "token_usage": None,
            "rounds": self.total_rounds,
            "tool_calls": self.total_tool_calls,
            "errors": self.total_errors,
            "status": self.final_status,
        }
