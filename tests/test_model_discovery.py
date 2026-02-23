#!/usr/bin/env python3
"""
Unit tests for tests/fixtures/model_discovery.py.

Covers:
- DiscoveredModels dataclass defaults and convenience properties
- _resolve_roles() keyword matching, pool priority, and fallback logic
- discover_models() integration with LMSHelper (fully mocked)

All tests are @pytest.mark.unit — no real LM Studio connection is made.
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config.constants import (
    DEFAULT_FALLBACK_MODEL,
    DEFAULT_REVIEW_MODEL,
    DEFAULT_THINKING_MODEL,
)
from tests.fixtures.model_discovery import DiscoveredModels, _resolve_roles, discover_models


# ---------------------------------------------------------------------------
# _resolve_roles() tests
# ---------------------------------------------------------------------------


class TestResolveRoles:
    """Unit tests for _resolve_roles(loaded_ids, downloaded_ids)."""

    @pytest.mark.unit
    def test_resolve_roles_loaded_model_matches_keyword(self):
        """A loaded model whose identifier contains 'coder' is assigned to the coding role."""
        loaded = ["qwen/qwen3-coder-30b"]
        downloaded = []

        roles = _resolve_roles(loaded, downloaded)

        assert roles.get("coding") == "qwen/qwen3-coder-30b"

    @pytest.mark.unit
    def test_resolve_roles_loaded_has_priority_over_downloaded(self):
        """When both pools have a match for the same role, the loaded model wins."""
        loaded = ["loaded-coder-7b"]
        downloaded = ["downloaded-coder-13b"]

        roles = _resolve_roles(loaded, downloaded)

        assert roles.get("coding") == "loaded-coder-7b", (
            "Loaded pool must take priority over downloaded for the same role"
        )

    @pytest.mark.unit
    def test_resolve_roles_downloaded_used_when_loaded_has_no_match(self):
        """When no loaded model matches a role's keywords, the downloaded pool is searched."""
        loaded = ["some-generic-model"]
        downloaded = ["mistralai/magistral-small-2509"]

        roles = _resolve_roles(loaded, downloaded)

        assert roles.get("reasoning") == "mistralai/magistral-small-2509"

    @pytest.mark.unit
    def test_resolve_roles_empty_inputs_returns_empty_dict(self):
        """Both pools empty with no fallbacks in any pool yields an empty roles dict."""
        roles = _resolve_roles([], [])

        # No keyword matches, no fallbacks available
        assert roles == {}

    @pytest.mark.unit
    def test_resolve_roles_fallback_used_when_model_in_pool(self):
        """When no keyword matches a role but the fallback constant is in the pool, it is assigned."""
        # DEFAULT_FALLBACK_MODEL covers chat and coding roles.
        # Supply it in downloaded without any keyword match.
        loaded = []
        downloaded = [DEFAULT_FALLBACK_MODEL]

        roles = _resolve_roles(loaded, downloaded)

        # The fallback for chat is DEFAULT_FALLBACK_MODEL
        assert roles.get("chat") == DEFAULT_FALLBACK_MODEL
        # The fallback for coding is also DEFAULT_FALLBACK_MODEL
        assert roles.get("coding") == DEFAULT_FALLBACK_MODEL

    @pytest.mark.unit
    def test_resolve_roles_fallback_not_used_when_model_absent(self):
        """When the fallback constant is absent from both pools, the role remains unassigned."""
        loaded = ["totally-unrelated-model"]
        downloaded = ["another-unrelated-model"]

        roles = _resolve_roles(loaded, downloaded)

        # None of the fallback models are present, so fallback roles must be absent
        assert "chat" not in roles or roles.get("chat") not in (
            DEFAULT_FALLBACK_MODEL,
            DEFAULT_REVIEW_MODEL,
            DEFAULT_THINKING_MODEL,
        ), (
            "Fallback must NOT be used when the fallback model is not in any pool"
        )
        # More precise: the fallback model itself is not in any pool
        assert DEFAULT_FALLBACK_MODEL not in loaded
        assert DEFAULT_FALLBACK_MODEL not in downloaded
        # So chat role should not be assigned to the fallback value
        assert roles.get("chat") != DEFAULT_FALLBACK_MODEL

    @pytest.mark.unit
    def test_resolve_roles_multiple_roles_resolved(self):
        """Models matching chat, reasoning, coding, and vision keywords are all resolved."""
        loaded = [
            "llama-3-8b-instruct",       # chat: matches "instruct"
            "deepseek-r1-7b",             # reasoning: matches "deepseek-r1"
            "deepseek-coder-6.7b",        # coding: matches "deepseek-coder"
            "qwen-vl-7b",                 # vision: matches "-vl"
        ]
        downloaded = []

        roles = _resolve_roles(loaded, downloaded)

        assert roles.get("chat") == "llama-3-8b-instruct"
        assert roles.get("reasoning") == "deepseek-r1-7b"
        assert roles.get("coding") == "deepseek-coder-6.7b"
        assert roles.get("vision") == "qwen-vl-7b"


# ---------------------------------------------------------------------------
# DiscoveredModels tests
# ---------------------------------------------------------------------------


class TestDiscoveredModels:
    """Unit tests for the DiscoveredModels dataclass and its convenience properties."""

    @pytest.mark.unit
    def test_discovered_models_defaults(self):
        """A zero-argument DiscoveredModels has empty collections and lmstudio_available=False."""
        dm = DiscoveredModels()

        assert dm.downloaded_ids == []
        assert dm.loaded_ids == []
        assert dm.roles == {}
        assert dm.lmstudio_available is False

    @pytest.mark.unit
    def test_discovered_models_defaults_all_properties_none(self):
        """All convenience properties on an empty DiscoveredModels return None."""
        dm = DiscoveredModels()

        assert dm.chat_model is None
        assert dm.reasoning_model is None
        assert dm.coding_model is None
        assert dm.thinking_model is None
        assert dm.small_model is None
        assert dm.vision_model is None

    @pytest.mark.unit
    def test_discovered_models_properties_return_roles(self):
        """Convenience properties delegate to the roles dict correctly."""
        roles = {
            "chat": "llama-3-8b-instruct",
            "reasoning": "deepseek-r1-7b",
            "coding": "qwen3-coder-30b",
            "thinking": "qwen3-4b-thinking",
            "small": "qwen-1b-mini",
            "vision": "qwen-vl-7b",
        }
        dm = DiscoveredModels(roles=roles, lmstudio_available=True)

        assert dm.chat_model == "llama-3-8b-instruct"
        assert dm.reasoning_model == "deepseek-r1-7b"
        assert dm.coding_model == "qwen3-coder-30b"
        assert dm.thinking_model == "qwen3-4b-thinking"
        assert dm.small_model == "qwen-1b-mini"
        assert dm.vision_model == "qwen-vl-7b"

    @pytest.mark.unit
    def test_discovered_models_property_returns_none_when_role_missing(self):
        """A property whose role key is absent from the roles dict returns None."""
        dm = DiscoveredModels(roles={"chat": "llama-3-8b-instruct"})

        # All other roles are missing
        assert dm.reasoning_model is None
        assert dm.coding_model is None
        assert dm.thinking_model is None
        assert dm.small_model is None
        assert dm.vision_model is None
        # chat is present
        assert dm.chat_model == "llama-3-8b-instruct"


# ---------------------------------------------------------------------------
# discover_models() tests
# ---------------------------------------------------------------------------


class TestDiscoverModels:
    """Unit tests for discover_models(), with LMSHelper fully mocked."""

    @pytest.mark.unit
    def test_discover_models_lms_not_installed(self):
        """When LMSHelper.is_installed() returns False, an empty DiscoveredModels is returned."""
        with patch("tests.fixtures.model_discovery.LMSHelper") as mock_lms:
            mock_lms.is_installed.return_value = False

            result = discover_models()

        assert isinstance(result, DiscoveredModels)
        assert result.lmstudio_available is False
        assert result.loaded_ids == []
        assert result.downloaded_ids == []
        assert result.roles == {}
        mock_lms.list_loaded_models.assert_not_called()

    @pytest.mark.unit
    def test_discover_models_lms_unreachable(self):
        """When list_loaded_models() returns None, an empty DiscoveredModels is returned."""
        with patch("tests.fixtures.model_discovery.LMSHelper") as mock_lms:
            mock_lms.is_installed.return_value = True
            mock_lms.list_loaded_models.return_value = None

            result = discover_models()

        assert isinstance(result, DiscoveredModels)
        assert result.lmstudio_available is False
        assert result.loaded_ids == []
        assert result.downloaded_ids == []

    @pytest.mark.unit
    def test_discover_models_success(self):
        """Normal path: loaded and downloaded models are populated and roles are resolved."""
        loaded_raw = [
            {"modelKey": "llama-3-8b-instruct", "identifier": "llama-3-8b-instruct"},
            {"modelKey": "deepseek-coder-6.7b", "identifier": "deepseek-coder-6.7b"},
        ]
        downloaded_raw = [
            {"modelKey": "qwen-vl-7b"},
        ]

        with patch("tests.fixtures.model_discovery.LMSHelper") as mock_lms:
            mock_lms.is_installed.return_value = True
            mock_lms.list_loaded_models.return_value = loaded_raw
            mock_lms.list_downloaded_models.return_value = downloaded_raw
            # _get_base_model_name strips ":N" suffixes; return key as-is for these
            mock_lms._get_base_model_name.side_effect = lambda k: k

            result = discover_models()

        assert result.lmstudio_available is True
        assert "llama-3-8b-instruct" in result.loaded_ids
        assert "deepseek-coder-6.7b" in result.loaded_ids
        assert "qwen-vl-7b" in result.downloaded_ids
        # Roles must be resolved from the returned model lists
        assert result.chat_model == "llama-3-8b-instruct"
        assert result.coding_model == "deepseek-coder-6.7b"
        assert result.vision_model == "qwen-vl-7b"

    @pytest.mark.unit
    def test_discover_models_deduplicates_loaded_models(self):
        """If _get_base_model_name maps two entries to the same base name, only one appears."""
        # LM Studio may expose the same model loaded twice with ":2" suffix
        loaded_raw = [
            {"modelKey": "llama-3-8b-instruct"},
            {"modelKey": "llama-3-8b-instruct:2"},
        ]

        with patch("tests.fixtures.model_discovery.LMSHelper") as mock_lms:
            mock_lms.is_installed.return_value = True
            mock_lms.list_loaded_models.return_value = loaded_raw
            mock_lms.list_downloaded_models.return_value = []
            # Both keys resolve to the same base name (stripping ":2")
            mock_lms._get_base_model_name.side_effect = lambda k: k.split(":")[0]

            result = discover_models()

        assert result.loaded_ids.count("llama-3-8b-instruct") == 1, (
            "Duplicate base names must be deduplicated in loaded_ids"
        )

    @pytest.mark.unit
    def test_discover_models_exception_returns_empty(self):
        """When LMSHelper raises an unexpected exception, an empty DiscoveredModels is returned."""
        with patch("tests.fixtures.model_discovery.LMSHelper") as mock_lms:
            mock_lms.is_installed.return_value = True
            mock_lms.list_loaded_models.side_effect = RuntimeError("LMS crashed")

            result = discover_models()

        assert isinstance(result, DiscoveredModels)
        assert result.lmstudio_available is False
        assert result.loaded_ids == []
        assert result.downloaded_ids == []
        assert result.roles == {}

    @pytest.mark.unit
    def test_discover_models_empty_loaded_models(self):
        """When list_loaded_models() returns an empty list, lmstudio_available is True and loaded_ids is empty."""
        downloaded_raw = [{"modelKey": "qwen3-coder-30b"}]

        with patch("tests.fixtures.model_discovery.LMSHelper") as mock_lms:
            mock_lms.is_installed.return_value = True
            mock_lms.list_loaded_models.return_value = []
            mock_lms.list_downloaded_models.return_value = downloaded_raw
            mock_lms._get_base_model_name.side_effect = lambda k: k

            result = discover_models()

        assert result.lmstudio_available is True
        assert result.loaded_ids == []
        assert "qwen3-coder-30b" in result.downloaded_ids
