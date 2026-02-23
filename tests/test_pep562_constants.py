#!/usr/bin/env python3
"""
Unit tests for PEP 562 __getattr__ lazy resolution in tests/test_constants.py.

Covers:
- __getattr__ resolution: dynamic model constants resolve via discover_models()
- Fallback behaviour: role missing or discovery raises → static fallback used
- Module-globals caching: resolved value written into module __dict__
- AttributeError: unknown attribute raises correctly
- _ensure_discovery(): runs once only, populates all 6 keys
- Static constants: accessible directly without triggering __getattr__

Each test resets global state (reset_pep562_state fixture, autouse=True) so
tests are fully isolated regardless of execution order.
"""

import os
import sys

import pytest
from unittest.mock import patch, MagicMock

# ---------------------------------------------------------------------------
# sys.path setup — required so `tests.*` imports resolve from repo root
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Import the module under test as an object so we can manipulate its globals
# and access _MODEL_ATTR_MAP, _resolved_cache, _discovery_done, __getattr__.
# NEVER use `from tests.test_constants import DEFAULT_TEST_MODEL` style for
# dynamic attrs — that triggers __getattr__ before the test can control state.
import tests.test_constants as tc

# Ground-truth fallback values imported from config.constants for assertions
from config.constants import (
    DEFAULT_FALLBACK_MODEL,
    DEFAULT_REVIEW_MODEL,
    DEFAULT_SMALL_MODEL,
    DEFAULT_THINKING_MODEL,
    DEFAULT_VISION_MODEL,
    MODEL_ROLE_KEYWORDS,
)


# ---------------------------------------------------------------------------
# Autouse fixture: reset PEP 562 global state before AND after every test
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_pep562_state():
    """Isolate PEP 562 module state around each test.

    Resets:
    - tc._discovery_done → False
    - tc._resolved_cache → {}
    - Any module-level attr cached by __getattr__ (e.g. DEFAULT_TEST_MODEL)
    """
    tc._discovery_done = False
    tc._resolved_cache.clear()
    for attr in list(tc._MODEL_ATTR_MAP.keys()):
        tc.__dict__.pop(attr, None)

    yield

    tc._discovery_done = False
    tc._resolved_cache.clear()
    for attr in list(tc._MODEL_ATTR_MAP.keys()):
        tc.__dict__.pop(attr, None)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DISCOVERY_TARGET = "tests.fixtures.model_discovery.discover_models"


def _make_discovered(roles: dict) -> MagicMock:
    """Return a MagicMock that looks like DiscoveredModels with the given roles."""
    discovered = MagicMock()
    discovered.roles = roles
    discovered.lmstudio_available = bool(roles)
    return discovered


# ---------------------------------------------------------------------------
# Section 1: __getattr__ resolution tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetattr:
    """Tests for the module-level __getattr__ hook."""

    def test_getattr_resolves_dynamic_model_constant(self):
        """__getattr__ returns the role-matched value from discover_models().

        Scenario: discover_models() returns roles={"chat": "my-chat-model"}.
        Accessing DEFAULT_TEST_MODEL (which maps to role "chat") must return
        "my-chat-model".
        """
        with patch(
            _DISCOVERY_TARGET,
            return_value=_make_discovered({"chat": "my-chat-model"}),
        ):
            result = tc.__getattr__("DEFAULT_TEST_MODEL")

        assert result == "my-chat-model", (
            f"Expected 'my-chat-model', got {result!r}"
        )

    def test_getattr_uses_fallback_when_role_missing(self):
        """__getattr__ falls back to the static value when the role is absent.

        Scenario: discover_models() returns roles={} (no role matched).
        DEFAULT_TEST_MODEL maps to role "chat" with fallback DEFAULT_FALLBACK_MODEL.
        """
        with patch(
            _DISCOVERY_TARGET,
            return_value=_make_discovered({}),
        ):
            result = tc.__getattr__("DEFAULT_TEST_MODEL")

        assert result == DEFAULT_FALLBACK_MODEL, (
            f"Expected fallback {DEFAULT_FALLBACK_MODEL!r}, got {result!r}"
        )

    def test_getattr_uses_fallback_on_discovery_exception(self):
        """__getattr__ uses static fallbacks when discover_models() raises.

        All 6 dynamic attrs must land on their configured static fallbacks
        when discovery raises an exception.
        """
        with patch(
            _DISCOVERY_TARGET,
            side_effect=RuntimeError("LM Studio not reachable"),
        ):
            default_test_model = tc.__getattr__("DEFAULT_TEST_MODEL")
            reasoning_model = tc.__getattr__("REASONING_MODEL")
            coding_model = tc.__getattr__("CODING_MODEL")
            thinking_model = tc.__getattr__("THINKING_MODEL")
            small_model = tc.__getattr__("SMALL_MODEL")
            vision_model = tc.__getattr__("VISION_MODEL")

        assert default_test_model == DEFAULT_FALLBACK_MODEL
        assert reasoning_model == DEFAULT_REVIEW_MODEL
        assert coding_model == DEFAULT_FALLBACK_MODEL
        assert thinking_model == DEFAULT_THINKING_MODEL
        assert small_model == DEFAULT_SMALL_MODEL
        assert vision_model == DEFAULT_VISION_MODEL

    def test_getattr_caches_in_module_globals(self):
        """After first access, the resolved value is written into module.__dict__.

        This means Python's attribute lookup finds it directly on the next
        access and __getattr__ is NOT called again.
        """
        assert "DEFAULT_TEST_MODEL" not in tc.__dict__, (
            "Attr must not be pre-cached before first access"
        )

        with patch(
            _DISCOVERY_TARGET,
            return_value=_make_discovered({"chat": "cached-model"}),
        ):
            _ = tc.__getattr__("DEFAULT_TEST_MODEL")

        # After first resolution __getattr__ must have written to module globals
        assert "DEFAULT_TEST_MODEL" in tc.__dict__, (
            "Resolved value was not written into tc.__dict__"
        )
        assert tc.__dict__["DEFAULT_TEST_MODEL"] == "cached-model", (
            f"Cached value mismatch: {tc.__dict__['DEFAULT_TEST_MODEL']!r}"
        )

    def test_getattr_raises_attributeerror_for_unknown(self):
        """Accessing a name not in _MODEL_ATTR_MAP must raise AttributeError."""
        with pytest.raises(AttributeError) as exc_info:
            tc.__getattr__("NONEXISTENT_ATTR")

        assert "NONEXISTENT_ATTR" in str(exc_info.value), (
            f"AttributeError message missing attribute name: {exc_info.value}"
        )

    def test_getattr_raises_attributeerror_message_contains_module_name(self):
        """The AttributeError message must mention the module name."""
        with pytest.raises(AttributeError) as exc_info:
            tc.__getattr__("TOTALLY_UNKNOWN")

        # PEP 562 convention: "module 'tests.test_constants' has no attribute 'X'"
        assert "tests.test_constants" in str(exc_info.value), (
            f"Expected module name in error: {exc_info.value}"
        )

    def test_getattr_resolves_reasoning_model_via_role(self):
        """REASONING_MODEL resolves correctly when role 'reasoning' is present."""
        with patch(
            _DISCOVERY_TARGET,
            return_value=_make_discovered({"reasoning": "my-reasoning-model"}),
        ):
            result = tc.__getattr__("REASONING_MODEL")

        assert result == "my-reasoning-model"

    def test_getattr_resolves_all_six_dynamic_attrs(self):
        """All 6 dynamic attrs resolve to their role-matched values."""
        roles = {
            "chat": "chat-model-x",
            "reasoning": "reasoning-model-x",
            "coding": "coding-model-x",
            "thinking": "thinking-model-x",
            "small": "small-model-x",
            "vision": "vision-model-x",
        }
        with patch(
            _DISCOVERY_TARGET,
            return_value=_make_discovered(roles),
        ):
            assert tc.__getattr__("DEFAULT_TEST_MODEL") == "chat-model-x"
            # Reset so each call re-runs discovery independently
            tc._discovery_done = False
            tc._resolved_cache.clear()
            assert tc.__getattr__("REASONING_MODEL") == "reasoning-model-x"
            tc._discovery_done = False
            tc._resolved_cache.clear()
            assert tc.__getattr__("CODING_MODEL") == "coding-model-x"
            tc._discovery_done = False
            tc._resolved_cache.clear()
            assert tc.__getattr__("THINKING_MODEL") == "thinking-model-x"
            tc._discovery_done = False
            tc._resolved_cache.clear()
            assert tc.__getattr__("SMALL_MODEL") == "small-model-x"
            tc._discovery_done = False
            tc._resolved_cache.clear()
            assert tc.__getattr__("VISION_MODEL") == "vision-model-x"


# ---------------------------------------------------------------------------
# Section 2: _ensure_discovery() tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestEnsureDiscovery:
    """Tests for the _ensure_discovery() internal function."""

    def test_ensure_discovery_runs_only_once(self):
        """discover_models() is called exactly once even if _ensure_discovery()
        is called multiple times.
        """
        mock_discover = MagicMock(
            return_value=_make_discovered({"chat": "once-model"})
        )

        with patch(_DISCOVERY_TARGET, mock_discover):
            tc._ensure_discovery()
            tc._ensure_discovery()
            tc._ensure_discovery()

        assert mock_discover.call_count == 1, (
            f"discover_models() called {mock_discover.call_count} times; expected 1"
        )

    def test_ensure_discovery_populates_resolved_cache(self):
        """After _ensure_discovery(), _resolved_cache has all 6 expected keys."""
        roles = {
            "chat": "c",
            "reasoning": "r",
            "coding": "co",
            "thinking": "t",
            "small": "s",
            "vision": "v",
        }
        with patch(
            _DISCOVERY_TARGET,
            return_value=_make_discovered(roles),
        ):
            tc._ensure_discovery()

        expected_keys = set(tc._MODEL_ATTR_MAP.keys())
        cached_keys = set(tc._resolved_cache.keys())

        assert cached_keys == expected_keys, (
            f"Cache keys mismatch.\n"
            f"Expected: {sorted(expected_keys)}\n"
            f"Got:      {sorted(cached_keys)}"
        )

    def test_ensure_discovery_sets_discovery_done_flag(self):
        """_discovery_done must be True after _ensure_discovery() runs."""
        assert tc._discovery_done is False, "Pre-condition: flag must start False"

        with patch(
            _DISCOVERY_TARGET,
            return_value=_make_discovered({}),
        ):
            tc._ensure_discovery()

        assert tc._discovery_done is True, (
            "_discovery_done was not set to True after _ensure_discovery()"
        )

    def test_ensure_discovery_on_exception_still_sets_flag(self):
        """_discovery_done is True even when discovery raises."""
        with patch(
            _DISCOVERY_TARGET,
            side_effect=ConnectionError("unreachable"),
        ):
            tc._ensure_discovery()

        assert tc._discovery_done is True

    def test_ensure_discovery_on_exception_fills_fallbacks(self):
        """When discovery raises, _resolved_cache is populated with static fallbacks."""
        with patch(
            _DISCOVERY_TARGET,
            side_effect=Exception("boom"),
        ):
            tc._ensure_discovery()

        expected = {
            "DEFAULT_TEST_MODEL": DEFAULT_FALLBACK_MODEL,
            "REASONING_MODEL": DEFAULT_REVIEW_MODEL,
            "CODING_MODEL": DEFAULT_FALLBACK_MODEL,
            "THINKING_MODEL": DEFAULT_THINKING_MODEL,
            "SMALL_MODEL": DEFAULT_SMALL_MODEL,
            "VISION_MODEL": DEFAULT_VISION_MODEL,
        }
        for attr, fallback in expected.items():
            assert tc._resolved_cache.get(attr) == fallback, (
                f"Fallback mismatch for {attr}: "
                f"expected {fallback!r}, got {tc._resolved_cache.get(attr)!r}"
            )

    def test_ensure_discovery_skips_second_call_entirely(self):
        """Second call to _ensure_discovery() is a no-op: cache is NOT re-populated."""
        first_roles = {"chat": "first-chat"}
        second_roles = {"chat": "second-chat"}

        with patch(
            _DISCOVERY_TARGET,
            return_value=_make_discovered(first_roles),
        ):
            tc._ensure_discovery()

        first_value = tc._resolved_cache.get("DEFAULT_TEST_MODEL")

        # Second call with different mock — should NOT change anything
        with patch(
            _DISCOVERY_TARGET,
            return_value=_make_discovered(second_roles),
        ):
            tc._ensure_discovery()

        assert tc._resolved_cache.get("DEFAULT_TEST_MODEL") == first_value, (
            "Cache was modified on second _ensure_discovery() call — should be no-op"
        )


# ---------------------------------------------------------------------------
# Section 3: Static constants are NOT affected by __getattr__
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestStaticConstants:
    """Static constants in tests/test_constants.py must be accessible directly
    without involving __getattr__ or model discovery.
    """

    def test_filesystem_mcp_accessible_directly(self):
        """FILESYSTEM_MCP is a static string constant."""
        assert tc.FILESYSTEM_MCP == "filesystem"

    def test_default_timeout_accessible_directly(self):
        """DEFAULT_TIMEOUT is a static integer constant."""
        assert tc.DEFAULT_TIMEOUT == 120

    def test_simple_task_accessible_directly(self):
        """SIMPLE_TASK is a static string constant."""
        assert isinstance(tc.SIMPLE_TASK, str)
        assert len(tc.SIMPLE_TASK) > 0

    def test_static_constants_not_in_model_attr_map(self):
        """Static constants must not appear in _MODEL_ATTR_MAP."""
        static_names = [
            "FILESYSTEM_MCP",
            "MEMORY_MCP",
            "FETCH_MCP",
            "GITHUB_MCP",
            "DEFAULT_TIMEOUT",
            "SHORT_TIMEOUT",
            "LONG_TIMEOUT",
            "DEFAULT_MAX_ROUNDS",
            "SIMPLE_TASK",
            "INVALID_MODEL_NAME",
        ]
        for name in static_names:
            assert name not in tc._MODEL_ATTR_MAP, (
                f"Static constant {name!r} must not be in _MODEL_ATTR_MAP"
            )

    def test_static_constants_do_not_trigger_discovery(self):
        """Accessing a static constant must NOT cause discover_models() to run."""
        mock_discover = MagicMock(
            return_value=_make_discovered({"chat": "unused"})
        )

        with patch(_DISCOVERY_TARGET, mock_discover):
            _ = tc.FILESYSTEM_MCP
            _ = tc.DEFAULT_TIMEOUT
            _ = tc.SIMPLE_TASK

        assert mock_discover.call_count == 0, (
            f"discover_models() was called {mock_discover.call_count} time(s) "
            "while accessing static constants — it must not be called"
        )

    def test_fallback_models_list_is_static(self):
        """FALLBACK_MODELS is a static list containing the three default model IDs."""
        assert isinstance(tc.FALLBACK_MODELS, list)
        assert DEFAULT_FALLBACK_MODEL in tc.FALLBACK_MODELS
        assert DEFAULT_REVIEW_MODEL in tc.FALLBACK_MODELS
        assert DEFAULT_THINKING_MODEL in tc.FALLBACK_MODELS

    def test_model_attr_map_has_exactly_six_entries(self):
        """_MODEL_ATTR_MAP must map exactly 6 dynamic model constant names."""
        assert len(tc._MODEL_ATTR_MAP) == 6, (
            f"Expected 6 entries in _MODEL_ATTR_MAP, got {len(tc._MODEL_ATTR_MAP)}"
        )

    def test_model_attr_map_keys_are_correct(self):
        """_MODEL_ATTR_MAP must contain the exact 6 expected attribute names."""
        expected = {
            "DEFAULT_TEST_MODEL",
            "REASONING_MODEL",
            "CODING_MODEL",
            "THINKING_MODEL",
            "SMALL_MODEL",
            "VISION_MODEL",
        }
        assert set(tc._MODEL_ATTR_MAP.keys()) == expected, (
            f"_MODEL_ATTR_MAP key mismatch.\n"
            f"Expected: {sorted(expected)}\n"
            f"Got:      {sorted(tc._MODEL_ATTR_MAP.keys())}"
        )


# ---------------------------------------------------------------------------
# Section 4: config/constants.py — model names and role keywords (Commit 1)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestConfigConstantsCommit1:
    """Tests for updated model names and role keywords in config/constants.py.

    These tests will FAIL (RED) until the constants are updated.
    """

    def test_default_fallback_model_is_updated(self):
        """DEFAULT_FALLBACK_MODEL must be 'qwen/qwen3-coder-next'."""
        assert DEFAULT_FALLBACK_MODEL == "qwen/qwen3-coder-next", (
            f"Expected 'qwen/qwen3-coder-next', got {DEFAULT_FALLBACK_MODEL!r}"
        )

    def test_default_vision_model_is_updated(self):
        """DEFAULT_VISION_MODEL must be 'qwen/qwen3-vl-8b'."""
        assert DEFAULT_VISION_MODEL == "qwen/qwen3-vl-8b", (
            f"Expected 'qwen/qwen3-vl-8b', got {DEFAULT_VISION_MODEL!r}"
        )

    def test_r1_in_reasoning_keywords(self):
        """'r1' must be present in MODEL_ROLE_KEYWORDS['reasoning']."""
        keywords = MODEL_ROLE_KEYWORDS.get("reasoning", [])
        assert "r1" in keywords, (
            f"'r1' not found in reasoning keywords: {keywords!r}"
        )

    def test_devstral_in_coding_keywords(self):
        """'devstral' must be present in MODEL_ROLE_KEYWORDS['coding']."""
        keywords = MODEL_ROLE_KEYWORDS.get("coding", [])
        assert "devstral" in keywords, (
            f"'devstral' not found in coding keywords: {keywords!r}"
        )

    def test_reasoning_keywords_preserves_existing(self):
        """Existing reasoning keywords must still be present after adding 'r1'."""
        keywords = MODEL_ROLE_KEYWORDS.get("reasoning", [])
        for kw in ("magistral", "deepseek-r1", "reasoning"):
            assert kw in keywords, (
                f"Pre-existing keyword {kw!r} missing from reasoning: {keywords!r}"
            )

    def test_coding_keywords_preserves_existing(self):
        """Existing coding keywords must still be present after adding 'devstral'."""
        keywords = MODEL_ROLE_KEYWORDS.get("coding", [])
        for kw in ("coder", "codestral", "starcoder", "deepseek-coder"):
            assert kw in keywords, (
                f"Pre-existing keyword {kw!r} missing from coding: {keywords!r}"
            )


# ---------------------------------------------------------------------------
# Section 5: config/constants.py — new env-var and cache constants (Commit 2)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestConfigConstantsCommit2:
    """Tests for new constants added in Commit 2.

    These tests will FAIL (RED) until the constants are added to config/constants.py.
    """

    def test_lms_test_env_var_prefix_exists(self):
        """LMS_TEST_ENV_VAR_PREFIX must be importable from config.constants."""
        from config import constants as cc
        assert hasattr(cc, "LMS_TEST_ENV_VAR_PREFIX"), (
            "LMS_TEST_ENV_VAR_PREFIX not found in config.constants"
        )

    def test_lms_test_env_var_prefix_value(self):
        """LMS_TEST_ENV_VAR_PREFIX must equal 'LMS_TEST'."""
        from config.constants import LMS_TEST_ENV_VAR_PREFIX
        assert LMS_TEST_ENV_VAR_PREFIX == "LMS_TEST", (
            f"Expected 'LMS_TEST', got {LMS_TEST_ENV_VAR_PREFIX!r}"
        )

    def test_lms_test_env_vars_exists(self):
        """LMS_TEST_ENV_VARS must be importable from config.constants."""
        from config import constants as cc
        assert hasattr(cc, "LMS_TEST_ENV_VARS"), (
            "LMS_TEST_ENV_VARS not found in config.constants"
        )

    def test_lms_test_env_vars_is_dict(self):
        """LMS_TEST_ENV_VARS must be a dict."""
        from config.constants import LMS_TEST_ENV_VARS
        assert isinstance(LMS_TEST_ENV_VARS, dict), (
            f"Expected dict, got {type(LMS_TEST_ENV_VARS)!r}"
        )

    def test_lms_test_env_vars_has_all_five_roles(self):
        """LMS_TEST_ENV_VARS must map all 5 roles: chat, thinking, coding, vision, embedding."""
        from config.constants import LMS_TEST_ENV_VARS
        expected_roles = {"chat", "thinking", "coding", "vision", "embedding"}
        assert set(LMS_TEST_ENV_VARS.keys()) == expected_roles, (
            f"Role keys mismatch.\nExpected: {sorted(expected_roles)}\n"
            f"Got:      {sorted(LMS_TEST_ENV_VARS.keys())}"
        )

    def test_lms_test_env_vars_values_correct(self):
        """LMS_TEST_ENV_VARS values must match the LMS_TEST_<ROLE>_MODEL pattern."""
        from config.constants import LMS_TEST_ENV_VARS
        expected = {
            "chat": "LMS_TEST_CHAT_MODEL",
            "thinking": "LMS_TEST_THINKING_MODEL",
            "coding": "LMS_TEST_CODING_MODEL",
            "vision": "LMS_TEST_VISION_MODEL",
            "embedding": "LMS_TEST_EMBEDDING_MODEL",
        }
        for role, var_name in expected.items():
            assert LMS_TEST_ENV_VARS.get(role) == var_name, (
                f"Role {role!r}: expected {var_name!r}, got {LMS_TEST_ENV_VARS.get(role)!r}"
            )

    def test_lms_rest_models_cache_ttl_exists(self):
        """LMS_REST_MODELS_CACHE_TTL must be importable from config.constants."""
        from config import constants as cc
        assert hasattr(cc, "LMS_REST_MODELS_CACHE_TTL"), (
            "LMS_REST_MODELS_CACHE_TTL not found in config.constants"
        )

    def test_lms_rest_models_cache_ttl_value(self):
        """LMS_REST_MODELS_CACHE_TTL must be 30 (seconds)."""
        from config.constants import LMS_REST_MODELS_CACHE_TTL
        assert LMS_REST_MODELS_CACHE_TTL == 30, (
            f"Expected 30, got {LMS_REST_MODELS_CACHE_TTL!r}"
        )

    def test_wake_up_ping_max_tokens_exists(self):
        """WAKE_UP_PING_MAX_TOKENS must be importable from config.constants."""
        from config import constants as cc
        assert hasattr(cc, "WAKE_UP_PING_MAX_TOKENS"), (
            "WAKE_UP_PING_MAX_TOKENS not found in config.constants"
        )

    def test_wake_up_ping_max_tokens_value(self):
        """WAKE_UP_PING_MAX_TOKENS must be 1."""
        from config.constants import WAKE_UP_PING_MAX_TOKENS
        assert WAKE_UP_PING_MAX_TOKENS == 1, (
            f"Expected 1, got {WAKE_UP_PING_MAX_TOKENS!r}"
        )

    def test_wake_up_ping_timeout_exists(self):
        """WAKE_UP_PING_TIMEOUT must be importable from config.constants."""
        from config import constants as cc
        assert hasattr(cc, "WAKE_UP_PING_TIMEOUT"), (
            "WAKE_UP_PING_TIMEOUT not found in config.constants"
        )

    def test_wake_up_ping_timeout_value(self):
        """WAKE_UP_PING_TIMEOUT must be 10 (seconds)."""
        from config.constants import WAKE_UP_PING_TIMEOUT
        assert WAKE_UP_PING_TIMEOUT == 10, (
            f"Expected 10, got {WAKE_UP_PING_TIMEOUT!r}"
        )
