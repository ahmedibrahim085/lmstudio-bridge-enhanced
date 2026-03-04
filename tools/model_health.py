"""Per-model error budget with advisory demotion (OPP-45).

Tracks error rates per model within a sliding time window and promotes
models through three health states:

    active → degraded → suspended

State transitions:
- active → degraded: error rate in window exceeds threshold
- degraded → active: cooldown elapsed AND error rate drops back to/below threshold
- degraded → suspended: cooldown elapsed AND error rate still exceeds threshold
- suspended: stays suspended until explicit reset()

Design:
- ModelHealth is a mutable dataclass (status changes over time)
- Both errors_in_window and calls_in_window are timestamp lists for sliding window
- threading.Lock for all shared state (safe for parallel execution)
- time.monotonic() for reliable duration measurement
- Advisory-only: logs warnings, never auto-swaps models
"""

import logging
import threading
import time
from dataclasses import dataclass, field

from config.constants.tool_config import (
    DEMOTION_COOLDOWN_SECONDS,
    ERROR_BUDGET_THRESHOLD,
    ERROR_BUDGET_WINDOW_SECONDS,
)

logger = logging.getLogger(__name__)


@dataclass
class ModelHealth:
    """Mutable health state for a single model."""

    model_key: str
    status: str = "active"  # "active" | "degraded" | "suspended"
    errors_in_window: list[float] = field(default_factory=list)
    calls_in_window: list[float] = field(default_factory=list)
    total_calls: int = 0
    total_errors: int = 0
    demoted_at: float | None = None
    last_recovery_check: float | None = None


class ModelHealthTracker:
    """Per-model error budget with advisory demotion.

    Tracks the error rate of each model within a sliding time window.
    When the error rate exceeds *threshold*, the model is marked "degraded".
    If the model remains degraded after *cooldown_seconds*, it transitions
    to "suspended". Recovery (back to "active") requires the cooldown to
    elapse AND the window error rate to drop at or below the threshold.

    Usage::

        tracker = ModelHealthTracker()

        # Record a successful LLM call
        tracker.record_llm_call("qwen2.5-coder", success=True, elapsed=1.2)

        # Record a tool error attributed to this model
        tracker.record_tool_error("qwen2.5-coder", "memory__create", "invalid_args")

        # Check advisory status before dispatching
        status = tracker.check_health("qwen2.5-coder")
        if status == "suspended":
            logger.warning("Model is suspended — consider using an alternative")

    All methods are thread-safe.
    """

    def __init__(
        self,
        window_seconds: float = ERROR_BUDGET_WINDOW_SECONDS,
        threshold: float = ERROR_BUDGET_THRESHOLD,
        cooldown_seconds: float = DEMOTION_COOLDOWN_SECONDS,
    ) -> None:
        self._lock = threading.Lock()
        self._models: dict[str, ModelHealth] = {}
        self._window_seconds = window_seconds
        self._threshold = threshold
        self._cooldown_seconds = cooldown_seconds

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record_llm_call(self, model: str, success: bool, elapsed: float) -> None:
        """Record an LLM call outcome for *model*.

        Args:
            model: Model identifier string.
            success: True if the call succeeded, False on any error.
            elapsed: Call duration in seconds (stored for future metrics use).
        """
        now = time.monotonic()
        with self._lock:
            health = self._get_or_create(model)
            health.total_calls += 1
            health.calls_in_window.append(now)
            if not success:
                health.total_errors += 1
                health.errors_in_window.append(now)

    def record_tool_error(self, model: str, tool_name: str, error_type: str) -> None:
        """Record a tool-dispatch error attributed to *model*.

        Tool errors are counted toward both the call budget and the error
        budget so that error_rate = errors / calls never exceeds 1.0.

        Args:
            model: Model identifier string.
            tool_name: Name of the tool that failed.
            error_type: Short description of the failure (e.g. "invalid_args").
        """
        now = time.monotonic()
        with self._lock:
            health = self._get_or_create(model)
            health.total_calls += 1
            health.calls_in_window.append(now)
            health.total_errors += 1
            health.errors_in_window.append(now)
            logger.debug(
                "Tool error for model '%s': %s (%s)",
                model,
                tool_name,
                error_type,
            )

    def check_health(self, model: str) -> str:
        """Return the current health status for *model*.

        Creates a fresh "active" entry if the model has never been seen.
        Prunes expired window entries on every call.

        Returns:
            One of "active", "degraded", or "suspended".
        """
        now = time.monotonic()
        with self._lock:
            health = self._get_or_create(model)
            self._prune_window(health, now)

            windowed_calls = len(health.calls_in_window)
            windowed_errors = len(health.errors_in_window)

            # No calls in window — cannot exceed threshold
            if windowed_calls == 0:
                if health.status == "degraded":
                    # Window slid past all calls AND cooldown elapsed → recover
                    if health.demoted_at is not None and (now - health.demoted_at) >= self._cooldown_seconds:
                        health.status = "active"
                        health.demoted_at = None
                        logger.info("Model '%s' recovered to active (empty window)", model)
                return health.status

            error_rate = windowed_errors / windowed_calls

            if health.status == "active":
                if error_rate > self._threshold:
                    health.status = "degraded"
                    health.demoted_at = now
                    logger.warning(
                        "Model '%s' degraded: windowed error rate %.1f%% exceeds threshold %.1f%%",
                        model,
                        error_rate * 100,
                        self._threshold * 100,
                    )
                return health.status

            if health.status == "degraded":
                if health.demoted_at is not None and (now - health.demoted_at) >= self._cooldown_seconds:
                    if error_rate <= self._threshold:
                        health.status = "active"
                        health.demoted_at = None
                        logger.info(
                            "Model '%s' recovered to active (rate %.1f%% <= threshold %.1f%%)",
                            model,
                            error_rate * 100,
                            self._threshold * 100,
                        )
                    else:
                        health.status = "suspended"
                        logger.warning(
                            "Model '%s' suspended: sustained degradation "
                            "(windowed rate %.1f%% after %.0fs cooldown)",
                            model,
                            error_rate * 100,
                            self._cooldown_seconds,
                        )
                return health.status

            # "suspended" — stays until explicit reset()
            return health.status

    def reset(self, model: str | None = None) -> None:
        """Reset health state for one model, or all models if *model* is None.

        Args:
            model: Model identifier to clear. Pass None to clear all.
        """
        with self._lock:
            if model is None:
                self._models.clear()
            else:
                self._models.pop(model, None)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_or_create(self, model: str) -> ModelHealth:
        """Return the ModelHealth entry for *model*, creating it if absent.

        Must be called while holding self._lock.
        """
        if model not in self._models:
            self._models[model] = ModelHealth(model_key=model)
        return self._models[model]

    def _prune_window(self, health: ModelHealth, now: float) -> None:
        """Remove timestamps older than the window from both lists.

        Must be called while holding self._lock.
        """
        cutoff = now - self._window_seconds
        health.calls_in_window = [t for t in health.calls_in_window if t >= cutoff]
        health.errors_in_window = [t for t in health.errors_in_window if t >= cutoff]


__all__ = ["ModelHealthTracker", "ModelHealth"]
