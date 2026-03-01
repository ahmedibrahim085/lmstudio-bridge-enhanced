#!/usr/bin/env python3
"""Tests for C-15: TTL caches must use time.monotonic(), not time.time().

time.time() is affected by NTP adjustments and system clock changes.
time.monotonic() guarantees monotonically increasing values for TTL/timeout use.

Affected locations:
- utils/lms_helper.py: list_all_models(), get_model() cache TTL
- utils/retry_logic.py: LMSCircuitBreaker open/recovery timing
- utils/model_fallback.py: _refresh_cache() TTL
"""
from unittest.mock import MagicMock, patch

import pytest


class TestLmsHelperUsesMonotonicClock:
    """LMSRestClient cache must use time.monotonic for TTL checks."""

    def test_list_all_models_uses_monotonic(self):
        """list_all_models() cache TTL must use time.monotonic()."""
        from utils.lms_helper import LMSRestClient

        client = LMSRestClient(base_url="http://localhost:1234")
        mock_http = MagicMock()
        client._client = mock_http
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [{"key": "m", "loaded_instances": []}]
        mock_http.get.return_value = mock_resp

        with patch("utils.lms_helper.time") as mock_time:
            mock_time.monotonic.return_value = 1000.0
            mock_time.time.return_value = 1000.0  # Fallback so code doesn't crash
            client.list_all_models()
            mock_time.monotonic.assert_called()

    def test_get_model_cache_check_uses_monotonic(self):
        """get_model() cache freshness check must use time.monotonic()."""
        from utils.lms_helper import LMSRestClient

        client = LMSRestClient(base_url="http://localhost:1234")
        client._models_cache = [{"key": "test/model", "loaded_instances": []}]
        client._models_cache_time = 999.0

        with patch("utils.lms_helper.time") as mock_time:
            mock_time.monotonic.return_value = 1000.0
            mock_time.time.return_value = 1000.0
            # Import the constant so TTL comparison works
            from config.constants import LMS_REST_MODELS_CACHE_TTL

            mock_time.monotonic.return_value = 999.0 + LMS_REST_MODELS_CACHE_TTL - 1
            client.get_model("test/model")
            mock_time.monotonic.assert_called()


class TestCircuitBreakerUsesMonotonicClock:
    """LMSCircuitBreaker must use time.monotonic for timeout tracking."""

    def test_on_failure_sets_time_with_monotonic(self):
        """When circuit opens, circuit_open_time uses time.monotonic()."""
        from utils.retry_logic import LMSCircuitBreaker

        cb = LMSCircuitBreaker(failure_threshold=1, recovery_timeout=60)

        with patch("utils.retry_logic.time") as mock_time:
            mock_time.monotonic.return_value = 5000.0
            mock_time.time.return_value = 5000.0
            cb.on_failure()
            # After threshold reached, should use monotonic
            mock_time.monotonic.assert_called()

    def test_call_recovery_check_uses_monotonic(self):
        """Recovery timeout check in call() must use time.monotonic()."""
        from utils.retry_logic import LMSCircuitBreaker

        cb = LMSCircuitBreaker(failure_threshold=1, recovery_timeout=60)
        cb.state = "OPEN"
        cb.circuit_open_time = 5000.0

        with patch("utils.retry_logic.time") as mock_time:
            mock_time.monotonic.return_value = 5100.0  # 100s > 60s recovery
            mock_time.time.return_value = 5100.0
            result = cb.call(lambda: "ok")
            assert result == "ok"
            mock_time.monotonic.assert_called()


class TestModelFallbackUsesMonotonicClock:
    """ModelFallbackManager cache must use time.monotonic for TTL."""

    def test_refresh_cache_uses_monotonic(self):
        """_refresh_cache() TTL check must use time.monotonic()."""
        from utils.model_fallback import ModelFallbackManager

        mgr = ModelFallbackManager.__new__(ModelFallbackManager)
        mgr._downloaded_models = [{"key": "test"}]
        mgr._cache_time = 999.0
        mgr._cache_ttl = 300

        with patch("time.time", return_value=1000.0) as mock_tt, patch(
            "time.monotonic", return_value=1000.0
        ) as mock_mono:
            mgr._refresh_cache()
            # Should use monotonic, not time
            mock_mono.assert_called()
