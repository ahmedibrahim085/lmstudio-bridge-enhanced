"""Tests for OPP-43 — JIT Poll Rate Limiter (memoization).

Verifies that jit_loader.ensure_model_loaded() memoizes successful
is_model_loaded() results for POLL_JIT_GUARD_TTL seconds, reducing
redundant REST API polls from ~2/min/model to ~1/min/model.

Test categories:
- Happy: memoization works (3), per-model tracking (1)
- Negative: load failure (2), server unavailable (1)
- Edge: skip conditions (3), invalidate_jit_cache (2)
- Boundary: TTL=0 (1), exact TTL (1)
- Integration: load + memo (2)
- Concurrency: rapid sequential (1), threaded (1)
- Constant: POLL_JIT_GUARD_TTL importable (1)
- Unload wiring: lms_unload_model calls invalidate_jit_cache (1)

RED phase: ~15 fail (memoization logic doesn't exist), ~5 pass (skip conditions + constant).
"""

import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config.constants import LMSTUDIO_TESTING_ENV_VAR  # noqa: E402

os.environ.setdefault(LMSTUDIO_TESTING_ENV_VAR, "1")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clean_jit_cache():
    """Reset JIT memo before and after each test."""
    from llm.jit_loader import invalidate_jit_cache
    invalidate_jit_cache()
    yield
    invalidate_jit_cache()


@pytest.fixture()
def mock_helper():
    """Patch LMSHelper methods used by jit_loader."""
    with patch("llm.jit_loader.LMSHelper") as mock:
        mock.is_installed.return_value = True
        mock.is_model_loaded.return_value = True
        mock.ensure_model_loaded_with_verification.return_value = True
        yield mock


# ===========================================================================
# 1. Happy: memoization works — 3 tests
# ===========================================================================

class TestMemoizationHappy:
    """First call checks + memoizes; second call within TTL skips; after TTL re-checks."""

    def test_first_call_checks_and_memoizes(self, mock_helper):
        """First call should invoke is_model_loaded and memoize the result."""
        from llm.jit_loader import ensure_model_loaded
        ensure_model_loaded("test-model", ttl=1800)
        assert mock_helper.is_model_loaded.call_count == 1

    def test_second_call_within_ttl_skips(self, mock_helper):
        """Second call within TTL should skip is_model_loaded entirely."""
        from llm.jit_loader import ensure_model_loaded
        ensure_model_loaded("test-model", ttl=1800)
        ensure_model_loaded("test-model", ttl=1800)
        assert mock_helper.is_model_loaded.call_count == 1, (
            "Expected is_model_loaded called only once due to memoization"
        )

    def test_call_after_ttl_rechecks(self, mock_helper, monkeypatch):
        """After TTL expires, should re-check is_model_loaded."""
        import time
        from llm.jit_loader import ensure_model_loaded

        # Override TTL to 1 second for fast test
        monkeypatch.setattr("llm.jit_loader.POLL_JIT_GUARD_TTL", 1)

        ensure_model_loaded("test-model", ttl=1800)
        assert mock_helper.is_model_loaded.call_count == 1

        time.sleep(1.1)  # Wait past TTL

        ensure_model_loaded("test-model", ttl=1800)
        assert mock_helper.is_model_loaded.call_count == 2, (
            "Expected re-check after TTL expiry"
        )


# ===========================================================================
# 2. Happy: per-model tracking — 1 test
# ===========================================================================

class TestPerModelTracking:
    """Different models tracked independently."""

    def test_different_models_tracked_independently(self, mock_helper):
        """Memoization for model-A should not affect model-B."""
        from llm.jit_loader import ensure_model_loaded
        ensure_model_loaded("model-a", ttl=1800)
        ensure_model_loaded("model-b", ttl=1800)
        assert mock_helper.is_model_loaded.call_count == 2, (
            "Each model should trigger its own is_model_loaded check"
        )
        # Now re-call both — both should be memoized
        ensure_model_loaded("model-a", ttl=1800)
        ensure_model_loaded("model-b", ttl=1800)
        assert mock_helper.is_model_loaded.call_count == 2, (
            "Both models should be memoized independently"
        )


# ===========================================================================
# 3. Negative: load failure — 2 tests
# ===========================================================================

class TestLoadFailure:
    """Model not loaded or load fails → no memo / memo cleared."""

    def test_model_not_loaded_no_memo(self, mock_helper):
        """is_model_loaded returns False, load succeeds → memo set after load."""
        from llm.jit_loader import ensure_model_loaded
        mock_helper.is_model_loaded.return_value = False
        mock_helper.ensure_model_loaded_with_verification.return_value = True

        ensure_model_loaded("test-model", ttl=1800)
        assert mock_helper.ensure_model_loaded_with_verification.call_count == 1

        # Second call should be memoized (load succeeded)
        ensure_model_loaded("test-model", ttl=1800)
        assert mock_helper.is_model_loaded.call_count == 1, (
            "After successful load, second call should be memoized"
        )

    def test_load_fails_memo_cleared(self, mock_helper):
        """is_model_loaded=False, load fails → LLMConnectionError, no memo."""
        from llm.exceptions import LLMConnectionError
        from llm.jit_loader import ensure_model_loaded

        mock_helper.is_model_loaded.return_value = False
        mock_helper.ensure_model_loaded_with_verification.return_value = False

        with pytest.raises(LLMConnectionError):
            ensure_model_loaded("test-model", ttl=1800)

        # Next call should re-check (not memoized)
        mock_helper.is_model_loaded.return_value = True
        ensure_model_loaded("test-model", ttl=1800)
        assert mock_helper.is_model_loaded.call_count == 2, (
            "After failed load, should not be memoized"
        )


# ===========================================================================
# 4. Negative: server unavailable — 1 test
# ===========================================================================

class TestServerUnavailable:
    """is_model_loaded returns None → no memoization, retry next call."""

    def test_server_down_no_memo(self, mock_helper):
        """When server is down (None return), should not memoize."""
        from llm.jit_loader import ensure_model_loaded
        mock_helper.is_model_loaded.return_value = None

        ensure_model_loaded("test-model", ttl=1800)
        ensure_model_loaded("test-model", ttl=1800)
        assert mock_helper.is_model_loaded.call_count == 2, (
            "Server unavailable (None) should not be memoized"
        )


# ===========================================================================
# 5. Edge: skip conditions — 3 tests
# ===========================================================================

class TestSkipConditions:
    """target_model=None, 'default', LMS not installed → skip, no memo."""

    def test_skip_when_target_none(self, mock_helper):
        """target_model=None → returns immediately, no is_model_loaded call."""
        from llm.jit_loader import ensure_model_loaded
        ensure_model_loaded(None, ttl=1800)
        mock_helper.is_model_loaded.assert_not_called()

    def test_skip_when_target_default(self, mock_helper):
        """target_model='default' → returns immediately, no is_model_loaded call."""
        from llm.jit_loader import ensure_model_loaded
        ensure_model_loaded("default", ttl=1800)
        mock_helper.is_model_loaded.assert_not_called()

    def test_skip_when_lms_not_installed(self, mock_helper):
        """LMS not installed → returns immediately, no is_model_loaded call."""
        from llm.jit_loader import ensure_model_loaded
        mock_helper.is_installed.return_value = False
        ensure_model_loaded("test-model", ttl=1800)
        mock_helper.is_model_loaded.assert_not_called()


# ===========================================================================
# 6. Edge: invalidate_jit_cache — 2 tests
# ===========================================================================

class TestInvalidateJitCache:
    """Clear specific model or all models."""

    def test_invalidate_specific_model(self, mock_helper):
        """After invalidating a specific model, next call should re-check."""
        from llm.jit_loader import ensure_model_loaded, invalidate_jit_cache

        ensure_model_loaded("model-a", ttl=1800)
        ensure_model_loaded("model-b", ttl=1800)
        assert mock_helper.is_model_loaded.call_count == 2

        # Invalidate only model-a
        invalidate_jit_cache("model-a")

        ensure_model_loaded("model-a", ttl=1800)  # Should re-check
        ensure_model_loaded("model-b", ttl=1800)  # Should still be cached
        assert mock_helper.is_model_loaded.call_count == 3, (
            "Only invalidated model should re-check"
        )

    def test_invalidate_all_models(self, mock_helper):
        """After invalidating all, both models should re-check."""
        from llm.jit_loader import ensure_model_loaded, invalidate_jit_cache

        ensure_model_loaded("model-a", ttl=1800)
        ensure_model_loaded("model-b", ttl=1800)
        assert mock_helper.is_model_loaded.call_count == 2

        invalidate_jit_cache()  # Clear all

        ensure_model_loaded("model-a", ttl=1800)
        ensure_model_loaded("model-b", ttl=1800)
        assert mock_helper.is_model_loaded.call_count == 4, (
            "All models should re-check after full invalidation"
        )


# ===========================================================================
# 7. Boundary: TTL=0 — 1 test
# ===========================================================================

class TestTTLZero:
    """POLL_JIT_GUARD_TTL=0 → always checks (memo effectively disabled)."""

    def test_ttl_zero_always_checks(self, mock_helper, monkeypatch):
        """With TTL=0, every call should invoke is_model_loaded."""
        from llm.jit_loader import ensure_model_loaded
        monkeypatch.setattr("llm.jit_loader.POLL_JIT_GUARD_TTL", 0)

        ensure_model_loaded("test-model", ttl=1800)
        ensure_model_loaded("test-model", ttl=1800)
        ensure_model_loaded("test-model", ttl=1800)
        assert mock_helper.is_model_loaded.call_count == 3, (
            "TTL=0 should disable memoization — every call checks"
        )


# ===========================================================================
# 8. Boundary: exact TTL — 1 test
# ===========================================================================

class TestExactTTL:
    """Call at exactly TTL seconds → should re-check (not < but >=)."""

    def test_exact_ttl_rechecks(self, mock_helper, monkeypatch):
        """At exactly TTL elapsed, the guard should re-check."""
        import time as _time

        from llm.jit_loader import ensure_model_loaded

        monkeypatch.setattr("llm.jit_loader.POLL_JIT_GUARD_TTL", 0.5)

        ensure_model_loaded("test-model", ttl=1800)
        assert mock_helper.is_model_loaded.call_count == 1

        _time.sleep(0.55)  # Just past TTL

        ensure_model_loaded("test-model", ttl=1800)
        assert mock_helper.is_model_loaded.call_count == 2, (
            "At TTL boundary, should re-check"
        )


# ===========================================================================
# 9. Integration: load + memo — 2 tests
# ===========================================================================

class TestLoadAndMemo:
    """Successful load memoizes; load then invalidate then re-check."""

    def test_successful_load_memoizes(self, mock_helper):
        """Model not loaded → load succeeds → memoized → second call skips."""
        from llm.jit_loader import ensure_model_loaded
        mock_helper.is_model_loaded.return_value = False
        mock_helper.ensure_model_loaded_with_verification.return_value = True

        ensure_model_loaded("test-model", ttl=1800)
        ensure_model_loaded("test-model", ttl=1800)
        # is_model_loaded called once, then load, then memoized
        assert mock_helper.is_model_loaded.call_count == 1
        assert mock_helper.ensure_model_loaded_with_verification.call_count == 1

    def test_load_then_invalidate_then_recheck(self, mock_helper):
        """Load succeeds → invalidate → next call re-checks."""
        from llm.jit_loader import ensure_model_loaded, invalidate_jit_cache
        mock_helper.is_model_loaded.return_value = False
        mock_helper.ensure_model_loaded_with_verification.return_value = True

        ensure_model_loaded("test-model", ttl=1800)
        invalidate_jit_cache("test-model")

        # Now model is actually loaded, but we invalidated the memo
        mock_helper.is_model_loaded.return_value = True
        ensure_model_loaded("test-model", ttl=1800)
        assert mock_helper.is_model_loaded.call_count == 2, (
            "After invalidation, should re-check"
        )


# ===========================================================================
# 10. Concurrency: rapid sequential — 1 test
# ===========================================================================

class TestRapidSequential:
    """100 rapid sequential calls → is_model_loaded called only once."""

    def test_100_rapid_calls_one_check(self, mock_helper):
        """Rapid sequential calls should all be served from memo."""
        from llm.jit_loader import ensure_model_loaded
        for _ in range(100):
            ensure_model_loaded("test-model", ttl=1800)
        assert mock_helper.is_model_loaded.call_count == 1, (
            f"Expected 1 check for 100 calls, got {mock_helper.is_model_loaded.call_count}"
        )


# ===========================================================================
# 11. Concurrency: threaded — 1 test
# ===========================================================================

class TestThreaded:
    """10 threads via ThreadPoolExecutor → no race, is_model_loaded <= 1 call."""

    def test_threaded_no_race(self, mock_helper):
        """Concurrent threads should not race on the memo dict."""
        from llm.jit_loader import ensure_model_loaded

        barrier = threading.Barrier(10)

        def worker():
            barrier.wait()  # Synchronize all threads to start together
            ensure_model_loaded("test-model", ttl=1800)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker) for _ in range(10)]
            for f in futures:
                f.result(timeout=5)

        # Due to lock contention, might get 1-2 calls but not 10
        assert mock_helper.is_model_loaded.call_count <= 2, (
            f"Expected <= 2 checks under concurrency, got {mock_helper.is_model_loaded.call_count}"
        )


# ===========================================================================
# 12. Constant: POLL_JIT_GUARD_TTL importable — 1 test
# ===========================================================================

class TestConstantExport:
    """POLL_JIT_GUARD_TTL importable from config.constants."""

    def test_poll_jit_guard_ttl_importable(self):
        """Constant should be importable and have expected value."""
        from config.constants import POLL_JIT_GUARD_TTL
        assert isinstance(POLL_JIT_GUARD_TTL, (int, float))
        assert POLL_JIT_GUARD_TTL == 60


# ===========================================================================
# 13. Unload wiring: lms_unload_model calls invalidate_jit_cache — 1 test
# ===========================================================================

class TestUnloadWiring:
    """lms_unload_model calls invalidate_jit_cache on success."""

    def test_unload_calls_invalidate(self):
        """Successful unload should call invalidate_jit_cache(model_name)."""
        with patch("tools.lms_cli_tools.LMSHelper") as mock_lms, \
             patch("tools.lms_cli_tools.invalidate_jit_cache") as mock_invalidate:
            mock_lms.is_installed.return_value = True
            mock_lms.unload_model.return_value = True

            from tools.lms_cli_tools import lms_unload_model
            result = lms_unload_model("test-model")

            assert result["success"] is True
            mock_invalidate.assert_called_once_with("test-model")

    def test_failed_unload_no_invalidate(self):
        """Failed unload should NOT call invalidate_jit_cache."""
        with patch("tools.lms_cli_tools.LMSHelper") as mock_lms, \
             patch("tools.lms_cli_tools.invalidate_jit_cache") as mock_invalidate:
            mock_lms.is_installed.return_value = True
            mock_lms.unload_model.return_value = False

            from tools.lms_cli_tools import lms_unload_model
            result = lms_unload_model("test-model")

            assert result["success"] is False
            mock_invalidate.assert_not_called()
