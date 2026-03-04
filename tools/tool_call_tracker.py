"""Tool call lifecycle tracker for orphan detection (OPP-37).

Tracks dispatched tool calls and detects orphans — calls that were dispatched
but never completed or explicitly marked as orphaned within the timeout window.

Design:
- Frozen ActiveCall dataclass for immutable call records
- threading.Lock for all shared state (safe for parallel execution)
- time.monotonic() for reliable duration measurement
"""

import logging
import threading
import time
from dataclasses import dataclass

from config.constants.tool_config import ORPHAN_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ActiveCall:
    """Immutable record of a dispatched tool call."""

    call_id: str
    tool_name: str
    dispatched_at: float


class ToolCallTracker:
    """Tracks active tool calls and detects orphans by timeout.

    A call is orphaned when:
    - It was dispatched but never completed (mark_completed not called), AND
    - The elapsed time since dispatch >= orphan_timeout.

    OR when explicitly flagged via mark_orphaned (e.g. on exception).
    """

    def __init__(self, orphan_timeout: float = ORPHAN_TIMEOUT_SECONDS) -> None:
        self._lock = threading.Lock()
        self._active_calls: dict[str, ActiveCall] = {}
        self._orphan_count: int = 0
        self._orphan_timeout = orphan_timeout

    def mark_dispatched(self, call_id: str, tool_name: str) -> None:
        """Register a tool call as dispatched and actively in-flight."""
        with self._lock:
            self._active_calls[call_id] = ActiveCall(
                call_id=call_id,
                tool_name=tool_name,
                dispatched_at=time.monotonic(),
            )

    def mark_completed(self, call_id: str) -> None:
        """Mark a call as successfully completed; removes from active tracking.

        No-op if call_id is unknown (already completed or never dispatched).
        """
        with self._lock:
            self._active_calls.pop(call_id, None)

    def mark_orphaned(self, call_id: str) -> None:
        """Explicitly mark a call as orphaned (e.g. on exception).

        Increments orphan_count only if the call was actively tracked.
        No-op if call_id is unknown.
        """
        with self._lock:
            call = self._active_calls.pop(call_id, None)
            if call is not None:
                self._orphan_count += 1
                logger.warning(
                    "Tool call '%s' (id=%s) orphaned (explicit)",
                    call.tool_name,
                    call_id,
                )

    def check_orphans(self) -> list[str]:
        """Scan active calls for timeout violations.

        Returns list of call_ids that have exceeded the orphan timeout.
        These calls are removed from active tracking and counted as orphans.
        """
        now = time.monotonic()
        orphaned_ids: list[str] = []
        with self._lock:
            for call_id, call in list(self._active_calls.items()):
                elapsed = now - call.dispatched_at
                if elapsed >= self._orphan_timeout:
                    orphaned_ids.append(call_id)
                    self._active_calls.pop(call_id)
                    self._orphan_count += 1
                    logger.warning(
                        "Tool call '%s' (id=%s) orphaned after %.1fs",
                        call.tool_name,
                        call_id,
                        elapsed,
                    )
        return orphaned_ids

    @property
    def orphan_count(self) -> int:
        """Total number of orphaned calls since this tracker was created."""
        with self._lock:
            return self._orphan_count


__all__ = ["ToolCallTracker", "ActiveCall"]
