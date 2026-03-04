"""Tool result cache with TTL and namespace normalization (OPP-40).

Caches results of idempotent tool calls (e.g. read_file, list_directory)
to eliminate duplicate dispatches within the same autonomous loop session.

Design:
- Frozen CacheEntry dataclass for immutable cached records
- threading.Lock for all shared state (safe for parallel execution)
- time.monotonic() for reliable TTL measurement
- SHA-256 key derived from (normalized_tool_name, sorted JSON args)
- Namespace normalization: "filesystem__read_file" -> "read_file"
- LRU-style eviction: oldest inserted entry evicted when max_size reached
- Error results never cached (is_error=True is a no-op)
- TTL=0 disables caching entirely
"""

import hashlib
import json
import logging
import threading
import time
from dataclasses import dataclass

from config.constants.tool_config import (
    TOOL_RESULT_CACHE_ALLOWLIST,
    TOOL_RESULT_CACHE_MAX_SIZE,
    TOOL_RESULT_CACHE_TTL,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CacheEntry:
    """Immutable record of a cached tool result."""

    result: str
    created_at: float
    tool_name: str


class ToolResultCache:
    """Cache for idempotent tool results with TTL and allowlist filtering.

    Only tools present in the allowlist are eligible for caching.
    Namespace prefixes (e.g. "filesystem__") are stripped before lookup,
    so "filesystem__read_file" and "read_file" share the same cache space.
    """

    def __init__(
        self,
        ttl: float = TOOL_RESULT_CACHE_TTL,
        max_size: int = TOOL_RESULT_CACHE_MAX_SIZE,
        allowlist: frozenset[str] | None = None,
    ) -> None:
        self._lock = threading.Lock()
        self._cache: dict[str, CacheEntry] = {}
        self._insertion_order: list[str] = []  # Tracks order for LRU eviction
        self._ttl = ttl
        self._max_size = max_size
        self._allowlist = allowlist if allowlist is not None else TOOL_RESULT_CACHE_ALLOWLIST
        self._hits: int = 0
        self._misses: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, tool_name: str, args: dict) -> str | None:
        """Return cached result for tool + args, or None on miss/expiry."""
        normalized = self._normalize_name(tool_name)

        if normalized not in self._allowlist:
            self._misses += 1
            return None

        if self._ttl <= 0:
            self._misses += 1
            return None

        key = self._make_key(normalized, args)
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return None

            if time.monotonic() - entry.created_at >= self._ttl:
                # Entry expired — evict it
                self._cache.pop(key, None)
                if key in self._insertion_order:
                    self._insertion_order.remove(key)
                self._misses += 1
                return None

            # Cache hit — refresh position in insertion order for LRU
            if key in self._insertion_order:
                self._insertion_order.remove(key)
            self._insertion_order.append(key)
            self._hits += 1
            return entry.result

    def put(
        self,
        tool_name: str,
        args: dict,
        result: str,
        is_error: bool = False,
    ) -> None:
        """Store a tool result in the cache.

        No-op when:
        - is_error is True (never cache error results)
        - tool_name not in allowlist
        - TTL is zero or negative
        """
        if is_error:
            return

        normalized = self._normalize_name(tool_name)
        if normalized not in self._allowlist:
            return

        if self._ttl <= 0:
            return

        key = self._make_key(normalized, args)
        with self._lock:
            # Evict oldest entries until we have room
            while len(self._cache) >= self._max_size and self._insertion_order:
                oldest_key = self._insertion_order.pop(0)
                self._cache.pop(oldest_key, None)

            self._cache[key] = CacheEntry(
                result=result,
                created_at=time.monotonic(),
                tool_name=normalized,
            )
            # Remove existing position to avoid duplicates, then append
            if key in self._insertion_order:
                self._insertion_order.remove(key)
            self._insertion_order.append(key)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def hits(self) -> int:
        """Total cache hits since creation."""
        return self._hits

    @property
    def misses(self) -> int:
        """Total cache misses since creation."""
        return self._misses

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_name(tool_name: str) -> str:
        """Strip MCP namespace prefix: 'filesystem__read_file' -> 'read_file'."""
        if "__" in tool_name:
            return tool_name.rsplit("__", 1)[-1]
        return tool_name

    @staticmethod
    def _make_key(normalized_name: str, args: dict) -> str:
        """Build a deterministic SHA-256 cache key from tool name + args."""
        canonical = json.dumps(args, sort_keys=True, default=str)
        raw = f"{normalized_name}:{canonical}"
        return hashlib.sha256(raw.encode()).hexdigest()


__all__ = ["ToolResultCache", "CacheEntry"]
