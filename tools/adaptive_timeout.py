"""Adaptive timeout manager based on observed response times (OPP-46)."""

import logging
import threading
from collections import deque

from config.constants.tool_config import (
    ADAPTIVE_TIMEOUT_ENABLED,
    ADAPTIVE_TIMEOUT_MIN_OBSERVATIONS,
    ADAPTIVE_TIMEOUT_MULTIPLIER,
)

logger = logging.getLogger(__name__)

_MAX_OBSERVATIONS = 100


class AdaptiveTimeoutManager:
    """Adaptive timeout using p95 + multiplier of observed response times.

    Tracks per-(model, endpoint_type) response time distributions in a sliding
    window of the last 100 observations.  Once at least ``min_observations``
    samples have been collected, ``get_timeout()`` returns::

        max(p95(observations) * multiplier, default)

    so the timeout never shrinks below the caller-supplied default.
    """

    def __init__(
        self,
        multiplier: float = ADAPTIVE_TIMEOUT_MULTIPLIER,
        min_observations: int = ADAPTIVE_TIMEOUT_MIN_OBSERVATIONS,
        enabled: bool = ADAPTIVE_TIMEOUT_ENABLED,
    ):
        self._lock = threading.Lock()
        self._observations: dict[str, deque[float]] = {}
        self._multiplier = multiplier
        self._min_observations = min_observations
        self._enabled = enabled

    def observe(self, model: str, endpoint_type: str, elapsed: float) -> None:
        """Record an observed response time for (model, endpoint_type)."""
        key = f"{model}:{endpoint_type}"
        with self._lock:
            if key not in self._observations:
                self._observations[key] = deque(maxlen=_MAX_OBSERVATIONS)
            self._observations[key].append(elapsed)

    def get_timeout(self, model: str, endpoint_type: str, default: float) -> float:
        """Return the adaptive timeout for (model, endpoint_type).

        Returns ``default`` when:
        - adaptive timeouts are disabled, OR
        - fewer than ``min_observations`` samples have been recorded.

        Otherwise returns ``max(p95 * multiplier, default)``.
        """
        if not self._enabled:
            return default
        key = f"{model}:{endpoint_type}"
        with self._lock:
            obs = self._observations.get(key)
            if obs is None or len(obs) < self._min_observations:
                return default
            adapted = self._compute_p95(obs) * self._multiplier
        return max(adapted, default)

    def _compute_p95(self, observations: deque[float]) -> float:
        """Compute the 95th-percentile of the given observation window."""
        sorted_obs = sorted(observations)
        idx = int(len(sorted_obs) * 0.95)
        idx = min(idx, len(sorted_obs) - 1)
        return float(sorted_obs[idx])


__all__ = ["AdaptiveTimeoutManager"]
