"""Tests for ModelValidator thread-safe cache — BUG 2 fix.

BUG 2: _class_cache and _class_cache_time are mutable class-level attributes
shared across all instances with no locking. Multiple concurrent async tasks
(FastMCP serves requests concurrently) can read/write simultaneously — data race.

Fix: Add threading.Lock to protect all cache read-check and write points.
Network I/O happens OUTSIDE the lock (no lock-held-during-I/O).
"""
import threading
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from llm.model_validator import ModelValidator


class TestModelValidatorCacheLock:
    """Verify ModelValidator has a thread-safe cache lock."""

    def setup_method(self):
        """Reset cache before each test."""
        ModelValidator._class_cache = None
        ModelValidator._class_cache_time = 0.0

    def teardown_method(self):
        """Reset cache after each test."""
        ModelValidator._class_cache = None
        ModelValidator._class_cache_time = 0.0

    # --- Structural: lock must exist on the class ---

    def test_class_has_cache_lock_attribute(self):
        """ModelValidator must have a _class_cache_lock class attribute."""
        assert hasattr(ModelValidator, "_class_cache_lock"), (
            "ModelValidator must have '_class_cache_lock' for thread safety"
        )

    def test_cache_lock_is_threading_lock(self):
        """_class_cache_lock must be a threading.Lock instance (not asyncio.Lock)."""
        lock = ModelValidator._class_cache_lock
        # threading.Lock() returns a _thread.lock / _RLock — check with acquire/release
        assert hasattr(lock, "acquire") and hasattr(lock, "release"), (
            "_class_cache_lock must be a threading lock with acquire/release"
        )
        # Must NOT be an asyncio.Lock (which lacks blocking acquire with timeout)
        import asyncio
        assert not isinstance(lock, asyncio.Lock), (
            "_class_cache_lock must be threading.Lock, not asyncio.Lock"
        )

    def test_cache_lock_is_shared_class_attribute(self):
        """Lock must be on the class, not per-instance (shared across all instances)."""
        v1 = ModelValidator()
        v2 = ModelValidator()
        assert v1._class_cache_lock is v2._class_cache_lock, (
            "_class_cache_lock must be a class-level attribute shared by all instances"
        )

    # --- reset_cache classmethod ---

    def test_reset_cache_classmethod_exists(self):
        """ModelValidator must have a reset_cache classmethod."""
        assert hasattr(ModelValidator, "reset_cache"), (
            "ModelValidator must have reset_cache() classmethod"
        )
        assert callable(ModelValidator.reset_cache), (
            "reset_cache must be callable"
        )

    def test_reset_cache_clears_cache_and_time(self):
        """reset_cache() sets _class_cache=None and _class_cache_time=0.0."""
        ModelValidator._class_cache = ["model-a", "model-b"]
        ModelValidator._class_cache_time = time.monotonic()

        ModelValidator.reset_cache()

        assert ModelValidator._class_cache is None, (
            "reset_cache() must set _class_cache to None"
        )
        assert ModelValidator._class_cache_time == 0.0, (
            "reset_cache() must set _class_cache_time to 0.0"
        )

    def test_reset_cache_works_when_already_empty(self):
        """reset_cache() is idempotent — safe to call when cache is already empty."""
        ModelValidator._class_cache = None
        ModelValidator._class_cache_time = 0.0

        ModelValidator.reset_cache()  # Should not raise

        assert ModelValidator._class_cache is None
        assert ModelValidator._class_cache_time == 0.0

    # --- clear_cache instance method also thread-safe ---

    def test_clear_cache_still_works(self):
        """Existing clear_cache() instance method still clears the cache."""
        ModelValidator._class_cache = ["model-x"]
        ModelValidator._class_cache_time = time.monotonic()

        validator = ModelValidator()
        validator.clear_cache()

        assert ModelValidator._class_cache is None
        assert ModelValidator._class_cache_time == 0.0

    # --- Thread safety: concurrent reset_cache calls ---

    def test_concurrent_reset_cache_no_crash(self):
        """Multiple threads resetting cache concurrently must not crash or corrupt."""
        errors: list[Exception] = []

        def reset_many():
            try:
                for _ in range(200):
                    ModelValidator._class_cache = ["model-x"]
                    ModelValidator._class_cache_time = time.monotonic()
                    ModelValidator.reset_cache()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=reset_many) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15)

        assert all(t.is_alive() is False for t in threads), (
            "All threads must finish within timeout"
        )
        assert len(errors) == 0, f"Thread safety errors: {errors}"

    def test_concurrent_clear_cache_no_crash(self):
        """Multiple threads calling clear_cache() concurrently must not crash."""
        errors: list[Exception] = []
        validator = ModelValidator()

        def clear_many():
            try:
                for _ in range(200):
                    ModelValidator._class_cache = ["model-y"]
                    ModelValidator._class_cache_time = time.monotonic()
                    validator.clear_cache()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=clear_many) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15)

        assert len(errors) == 0, f"Thread safety errors in clear_cache: {errors}"

    def test_concurrent_cache_read_write_no_crash(self):
        """Concurrent readers and writers on the class cache must not corrupt state."""
        errors: list[Exception] = []

        def writer():
            try:
                for i in range(200):
                    with ModelValidator._class_cache_lock:
                        ModelValidator._class_cache = [f"model-{i}"]
                        ModelValidator._class_cache_time = time.monotonic()
            except Exception as e:
                errors.append(e)

        def reader():
            try:
                for _ in range(200):
                    with ModelValidator._class_cache_lock:
                        _ = ModelValidator._class_cache
                        _ = ModelValidator._class_cache_time
            except Exception as e:
                errors.append(e)

        threads = (
            [threading.Thread(target=writer) for _ in range(4)]
            + [threading.Thread(target=reader) for _ in range(4)]
        )
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15)

        assert len(errors) == 0, f"Concurrent read/write errors: {errors}"

    # --- Async: _fetch_models uses lock on cache read and write ---

    @pytest.mark.asyncio
    async def test_fetch_models_cache_hit_uses_lock(self):
        """_fetch_models() cache hit path must return cached value under lock.

        Setup: warm cache with a known list.
        Expect: returns same list without hitting network.
        """
        ModelValidator._class_cache = ["cached-model-1", "cached-model-2"]
        ModelValidator._class_cache_time = time.monotonic()  # fresh

        validator = ModelValidator()

        with patch("llm.model_validator.httpx.AsyncClient") as mock_client_cls:
            result = await validator._fetch_models(force_refresh=False)

        # Network should NOT be called — cache hit
        mock_client_cls.assert_not_called()
        assert result == ["cached-model-1", "cached-model-2"]

    @pytest.mark.asyncio
    async def test_fetch_models_cache_write_uses_lock(self):
        """_fetch_models() cache miss path must write to cache under lock.

        Setup: empty cache, mock network returns known list.
        Expect: cache populated after fetch.
        """
        ModelValidator._class_cache = None
        ModelValidator._class_cache_time = 0.0

        validator = ModelValidator(api_base="http://localhost:1234/v1")

        native_response = MagicMock()
        native_response.status_code = 200
        native_response.json.return_value = {
            "models": [{"key": "model-alpha"}, {"key": "model-beta"}]
        }
        native_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=native_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("llm.model_validator.httpx.AsyncClient", return_value=mock_client):
            result = await validator._fetch_models(force_refresh=True)

        assert result == ["model-alpha", "model-beta"]
        # Lock must have been acquired to write — verify cache was written
        assert ModelValidator._class_cache == ["model-alpha", "model-beta"]
        assert ModelValidator._class_cache_time > 0.0

    @pytest.mark.asyncio
    async def test_fetch_models_lock_not_held_during_network_io(self):
        """Lock must NOT be held during network I/O.

        Verify: while _fetch_models is awaiting the network, the lock is released
        so other threads can still access the cache.

        Strategy: use a threading.Event to signal when network I/O starts,
        then verify the lock is acquirable from another thread at that moment.
        """
        ModelValidator._class_cache = None
        ModelValidator._class_cache_time = 0.0

        validator = ModelValidator(api_base="http://localhost:1234/v1")

        io_started = threading.Event()
        lock_acquirable_during_io = threading.Event()

        async def slow_get(*args, **kwargs):
            """Simulate slow network: signal start, pause, return response."""
            io_started.set()
            # Wait briefly to let the checker thread run
            import asyncio
            await asyncio.sleep(0.05)
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            resp.json.return_value = {"models": [{"key": "model-z"}]}
            return resp

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=slow_get)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        def check_lock():
            io_started.wait(timeout=2.0)
            # Try to acquire lock — should succeed if NOT held during I/O
            acquired = ModelValidator._class_cache_lock.acquire(blocking=True, timeout=0.5)
            if acquired:
                ModelValidator._class_cache_lock.release()
                lock_acquirable_during_io.set()

        checker = threading.Thread(target=check_lock)
        checker.start()

        with patch("llm.model_validator.httpx.AsyncClient", return_value=mock_client):
            result = await validator._fetch_models(force_refresh=True)

        checker.join(timeout=5)

        assert lock_acquirable_during_io.is_set(), (
            "Lock was held during network I/O — must release lock before awaiting network"
        )
        assert result == ["model-z"]
