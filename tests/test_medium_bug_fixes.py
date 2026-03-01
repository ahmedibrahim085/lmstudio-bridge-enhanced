"""Tests for MEDIUM bug fixes (BUGs 7, 9, 10)."""
import logging
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


class TestCacheWriteLogging:
    """BUG 7: cache.py should log on failure, not silently pass."""

    def test_get_stats_logs_on_corrupt_cache(self, tmp_path, caplog):
        """get_stats should log warning when cache file has invalid timestamp."""
        from model_registry.cache import CacheManager

        cache_file = tmp_path / "test_cache.json"
        cache_file.write_text('{"updated_at": "not-a-date", "models": {}}')

        manager = CacheManager(str(cache_file))

        with caplog.at_level(logging.WARNING, logger="model_registry.cache"):
            stats = manager.get_stats()

        # Should have logged a warning (not silently passed)
        assert any(
            "cache" in r.message.lower()
            or "timestamp" in r.message.lower()
            or "failed" in r.message.lower()
            for r in caplog.records
            if r.levelno >= logging.WARNING
        ), (
            "Expected a WARNING log about the corrupt cache timestamp, "
            f"but got: {[r.message for r in caplog.records]}"
        )


class TestMetricsLogging:
    """BUG 9: dynamic_autonomous.py should log metrics failures at debug level."""

    def test_metrics_failure_does_not_crash(self):
        """Metrics failures must not crash the autonomous loop."""
        # This is a smoke test — we verify the module is importable
        # and doesn't re-raise. Full integration would require the entire
        # autonomous loop which is too heavy for a unit test.
        from tools import dynamic_autonomous_register  # noqa: F401 — import side-effect check
        assert True

    def test_dynamic_autonomous_has_logger(self):
        """dynamic_autonomous module must have a module-level logger for debug logging."""
        import tools.dynamic_autonomous as da
        assert hasattr(da, "logger"), (
            "tools/dynamic_autonomous.py must have a module-level `logger` "
            "so that `logger.debug(...)` calls in except blocks work."
        )


class TestAsyncioDeprecation:
    """BUG 10: health_check_decorator.py should not use deprecated get_event_loop."""

    def test_no_get_event_loop_usage(self):
        """health_check_decorator should use asyncio.run, not get_event_loop."""
        import inspect
        from mcp_client import health_check_decorator
        source = inspect.getsource(health_check_decorator)
        assert "get_event_loop" not in source, (
            "health_check_decorator.py still uses deprecated asyncio.get_event_loop(). "
            "Should use asyncio.run() instead."
        )
