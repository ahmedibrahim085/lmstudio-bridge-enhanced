"""OPP-40: Tool Result Cache — RED test suite.

Tests for ToolResultCache that will FAIL because the module does not exist yet.

ALL tests import from tools.tool_result_cache which does not exist until GREEN.
"""

from unittest.mock import patch

import pytest

from tools.tool_result_cache import CacheEntry, ToolResultCache


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_ALLOWLIST = frozenset({"read_file", "list_directory", "search_files"})


def _cache(
    ttl: float = 120.0,
    max_size: int = 200,
    allowlist: frozenset[str] | None = None,
) -> ToolResultCache:
    return ToolResultCache(
        ttl=ttl,
        max_size=max_size,
        allowlist=allowlist if allowlist is not None else _ALLOWLIST,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestToolResultCacheBasic:
    """Core put/get semantics."""

    def test_allowlisted_tool_cached(self) -> None:
        """put + get returns the cached result for an allowlisted tool."""
        cache = _cache()
        cache.put("read_file", {"path": "/tmp/f.txt"}, "file contents")
        result = cache.get("read_file", {"path": "/tmp/f.txt"})
        assert result == "file contents"

    def test_cache_hit_counter(self) -> None:
        """hits increments on each cache hit."""
        cache = _cache()
        cache.put("read_file", {"path": "/a"}, "data")
        assert cache.hits == 0
        cache.get("read_file", {"path": "/a"})
        cache.get("read_file", {"path": "/a"})
        assert cache.hits == 2

    def test_not_in_allowlist_not_cached(self) -> None:
        """Tool not in allowlist: put is a no-op, get always returns None."""
        cache = _cache()
        cache.put("execute_command", {"cmd": "ls"}, "output")
        result = cache.get("execute_command", {"cmd": "ls"})
        assert result is None

    def test_cache_expired_ttl(self) -> None:
        """Advance time past TTL → get returns None (entry expired)."""
        cache = _cache(ttl=30.0)
        with patch("time.monotonic", return_value=0.0):
            cache.put("read_file", {"path": "/x"}, "cached data")
        # Advance past TTL
        with patch("time.monotonic", return_value=31.0):
            result = cache.get("read_file", {"path": "/x"})
        assert result is None

    def test_different_args_different_entries(self) -> None:
        """Same tool, different args → different cache entries."""
        cache = _cache()
        cache.put("read_file", {"path": "/a"}, "content_a")
        cache.put("read_file", {"path": "/b"}, "content_b")
        assert cache.get("read_file", {"path": "/a"}) == "content_a"
        assert cache.get("read_file", {"path": "/b"}) == "content_b"

    def test_namespace_normalization(self) -> None:
        """filesystem__read_file and read_file map to the same cache key."""
        cache = _cache()
        cache.put("read_file", {"path": "/norm"}, "normalized content")
        # Namespaced variant should hit same entry
        result = cache.get("filesystem__read_file", {"path": "/norm"})
        assert result == "normalized content"

    def test_error_result_not_cached(self) -> None:
        """put with is_error=True is a no-op; subsequent get returns None."""
        cache = _cache()
        cache.put("read_file", {"path": "/err"}, "Error: not found", is_error=True)
        result = cache.get("read_file", {"path": "/err"})
        assert result is None

    def test_ttl_zero_disables_caching(self) -> None:
        """TTL=0 → get always returns None (caching effectively disabled)."""
        cache = _cache(ttl=0.0)
        cache.put("read_file", {"path": "/z"}, "content")
        assert cache.get("read_file", {"path": "/z"}) is None

    def test_empty_allowlist_nothing_cached(self) -> None:
        """Empty allowlist → nothing is ever cached regardless of tool name."""
        cache = _cache(allowlist=frozenset())
        cache.put("read_file", {"path": "/e"}, "data")
        assert cache.get("read_file", {"path": "/e"}) is None

    def test_hit_miss_counters(self) -> None:
        """Verify hits and misses count correctly across multiple operations."""
        cache = _cache()
        # 2 misses (not in cache yet)
        cache.get("read_file", {"path": "/m1"})
        cache.get("read_file", {"path": "/m2"})
        # populate
        cache.put("read_file", {"path": "/h1"}, "data")
        # 1 hit
        cache.get("read_file", {"path": "/h1"})
        assert cache.hits == 1
        assert cache.misses == 2

    def test_cache_key_deterministic(self) -> None:
        """Same tool + same args always produces the same cache key (deterministic)."""
        cache = _cache()
        args = {"path": "/det", "flag": True}
        cache.put("list_directory", args, "listing")
        # Retrieve twice with identical args — both must hit
        r1 = cache.get("list_directory", args)
        r2 = cache.get("list_directory", args)
        assert r1 == "listing"
        assert r2 == "listing"
        assert cache.hits == 2


class TestToolResultCacheEviction:
    """LRU/FIFO eviction when max_size is reached."""

    def test_cache_max_size_evicts_oldest(self) -> None:
        """Fill cache to max_size, add one more → oldest entry evicted."""
        cache = _cache(max_size=3)
        # Fill to capacity
        cache.put("read_file", {"path": "/1"}, "data1")
        cache.put("read_file", {"path": "/2"}, "data2")
        cache.put("read_file", {"path": "/3"}, "data3")
        # Adding a 4th entry should evict the oldest (/1)
        cache.put("list_directory", {"path": "/4"}, "data4")
        # Oldest must be gone
        assert cache.get("read_file", {"path": "/1"}) is None
        # Newer entries still present
        assert cache.get("read_file", {"path": "/2"}) == "data2"
        assert cache.get("list_directory", {"path": "/4"}) == "data4"


class TestCacheEntryDataclass:
    """Verify CacheEntry is a frozen dataclass with correct fields."""

    def test_cache_entry_fields(self) -> None:
        entry = CacheEntry(result="content", created_at=100.0, tool_name="read_file")
        assert entry.result == "content"
        assert entry.created_at == 100.0
        assert entry.tool_name == "read_file"

    def test_cache_entry_is_frozen(self) -> None:
        """CacheEntry must be immutable (frozen=True)."""
        entry = CacheEntry(result="x", created_at=0.0, tool_name="t")
        with pytest.raises((AttributeError, TypeError)):
            entry.result = "mutated"  # type: ignore[misc]
