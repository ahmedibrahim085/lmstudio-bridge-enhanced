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


def _make_rest_unavailable():
    """Return a context manager that makes LMSRestClient.is_server_available() return False."""
    mock_rest = MagicMock()
    mock_rest.is_server_available.return_value = False
    return patch("tests.fixtures.model_discovery.LMSRestClient", return_value=mock_rest)


class TestDiscoverModels:
    """Unit tests for discover_models(), with LMSHelper fully mocked.

    All tests in this class exercise the CLI fallback path by making REST unavailable.
    The REST-first path is covered by TestDiscoverModelsV2.
    """

    @pytest.mark.unit
    def test_discover_models_lms_not_installed(self):
        """When LMSHelper.is_installed() returns False, an empty DiscoveredModels is returned."""
        with _make_rest_unavailable(), patch("tests.fixtures.model_discovery.LMSHelper") as mock_lms:
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
        with _make_rest_unavailable(), patch("tests.fixtures.model_discovery.LMSHelper") as mock_lms:
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

        with _make_rest_unavailable(), patch("tests.fixtures.model_discovery.LMSHelper") as mock_lms:
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

        with _make_rest_unavailable(), patch("tests.fixtures.model_discovery.LMSHelper") as mock_lms:
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
        with _make_rest_unavailable(), patch("tests.fixtures.model_discovery.LMSHelper") as mock_lms:
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

        with _make_rest_unavailable(), patch("tests.fixtures.model_discovery.LMSHelper") as mock_lms:
            mock_lms.is_installed.return_value = True
            mock_lms.list_loaded_models.return_value = []
            mock_lms.list_downloaded_models.return_value = downloaded_raw
            mock_lms._get_base_model_name.side_effect = lambda k: k

            result = discover_models()

        assert result.lmstudio_available is True
        assert result.loaded_ids == []
        assert "qwen3-coder-30b" in result.downloaded_ids


# ---------------------------------------------------------------------------
# DiscoveredModels — models_metadata field and convenience methods (Commit 5)
# ---------------------------------------------------------------------------


class TestDiscoveredModelsMetadata:
    """Unit tests for the models_metadata field and related convenience methods."""

    @pytest.mark.unit
    def test_discovered_models_has_models_metadata_field(self):
        """DiscoveredModels() zero-argument creates an empty models_metadata dict."""
        dm = DiscoveredModels()
        assert hasattr(dm, "models_metadata")
        assert dm.models_metadata == {}

    @pytest.mark.unit
    def test_has_capability_returns_true(self):
        """has_capability returns True when the model metadata contains capabilities.vision=True."""
        dm = DiscoveredModels(
            models_metadata={"vision-model": {"capabilities": {"vision": True}}}
        )
        assert dm.has_capability("vision-model", "vision") is True

    @pytest.mark.unit
    def test_has_capability_returns_false_missing(self):
        """has_capability returns False when the capability key is absent."""
        dm = DiscoveredModels(
            models_metadata={"text-model": {"capabilities": {"vision": False}}}
        )
        assert dm.has_capability("text-model", "vision") is False

    @pytest.mark.unit
    def test_has_capability_returns_false_no_metadata(self):
        """has_capability returns False when the model key is not in models_metadata."""
        dm = DiscoveredModels()
        assert dm.has_capability("nonexistent-model", "vision") is False

    @pytest.mark.unit
    def test_get_size_bytes_returns_value(self):
        """get_size_bytes returns the size_bytes integer from model metadata."""
        dm = DiscoveredModels(
            models_metadata={"small-model": {"size_bytes": 1000}}
        )
        assert dm.get_size_bytes("small-model") == 1000

    @pytest.mark.unit
    def test_get_size_bytes_returns_none_no_metadata(self):
        """get_size_bytes returns None when the model key is not in models_metadata."""
        dm = DiscoveredModels()
        assert dm.get_size_bytes("nonexistent-model") is None

    @pytest.mark.unit
    def test_get_metadata_returns_dict(self):
        """get_metadata returns the full metadata dict for a known model key."""
        meta = {"capabilities": {"vision": True}, "size_bytes": 5000}
        dm = DiscoveredModels(models_metadata={"my-model": meta})
        assert dm.get_metadata("my-model") == meta

    @pytest.mark.unit
    def test_get_metadata_returns_none_for_unknown(self):
        """get_metadata returns None when the model key is absent."""
        dm = DiscoveredModels()
        assert dm.get_metadata("no-such-model") is None


# ---------------------------------------------------------------------------
# _resolve_roles() v2 — structured API + env overrides (Commit 6)
# ---------------------------------------------------------------------------


class TestResolveRolesV2:
    """Unit tests for the rewritten _resolve_roles with 3-tier resolution."""

    @pytest.mark.unit
    def test_env_var_override_valid_model(self, monkeypatch):
        """Env var for a role assigns the model when it is in the available pool."""
        monkeypatch.setenv("LMS_TEST_CHAT_MODEL", "custom-chat-model")
        loaded = ["custom-chat-model"]
        downloaded = []
        roles = _resolve_roles(loaded, downloaded)
        assert roles.get("chat") == "custom-chat-model"

    @pytest.mark.unit
    def test_env_var_override_invalid_model(self, monkeypatch):
        """Env var pointing to a model not in any pool is silently skipped."""
        monkeypatch.setenv("LMS_TEST_CHAT_MODEL", "ghost-model-not-available")
        # ghost-model-not-available is NOT in loaded or downloaded
        loaded = ["some-instruct-model"]
        downloaded = []
        roles = _resolve_roles(loaded, downloaded)
        # The env var override must be skipped; role may still be resolved by keyword
        assert roles.get("chat") != "ghost-model-not-available"

    @pytest.mark.unit
    def test_structured_api_vision_detection(self):
        """A model with capabilities.vision=True in metadata is assigned the vision role."""
        loaded = ["vision-capable-model"]
        downloaded = []
        metadata = {"vision-capable-model": {"capabilities": {"vision": True}}}
        roles = _resolve_roles(loaded, downloaded, metadata)
        assert roles.get("vision") == "vision-capable-model"

    @pytest.mark.unit
    def test_structured_api_embedding_detection(self):
        """A model with type='embedding' in metadata is assigned the embedding role."""
        loaded = []
        downloaded = ["embed-model"]
        metadata = {"embed-model": {"type": "embedding"}}
        roles = _resolve_roles(loaded, downloaded, metadata)
        assert roles.get("embedding") == "embed-model"

    @pytest.mark.unit
    def test_keyword_match_still_works(self):
        """Keyword matching for the coding role still works (backward compat)."""
        loaded = ["my-coder-7b"]
        downloaded = []
        roles = _resolve_roles(loaded, downloaded)
        assert roles.get("coding") == "my-coder-7b"

    @pytest.mark.unit
    def test_prefer_smallest_by_size(self):
        """When two vision models are available, the smaller one (by size_bytes) is picked."""
        loaded = ["vision-large", "vision-small"]
        downloaded = []
        metadata = {
            "vision-large": {"capabilities": {"vision": True}, "size_bytes": 8_000_000_000},
            "vision-small": {"capabilities": {"vision": True}, "size_bytes": 2_000_000_000},
        }
        roles = _resolve_roles(loaded, downloaded, metadata)
        assert roles.get("vision") == "vision-small"

    @pytest.mark.unit
    def test_prefer_smallest_tiebreak_alphabetical(self):
        """When two vision models have the same size, alphabetical order picks the first."""
        loaded = ["beta-vision", "alpha-vision"]
        downloaded = []
        metadata = {
            "beta-vision": {"capabilities": {"vision": True}, "size_bytes": 4_000_000_000},
            "alpha-vision": {"capabilities": {"vision": True}, "size_bytes": 4_000_000_000},
        }
        roles = _resolve_roles(loaded, downloaded, metadata)
        assert roles.get("vision") == "alpha-vision"

    @pytest.mark.unit
    def test_empty_pools_empty_roles(self):
        """No models in either pool produces an empty roles dict."""
        roles = _resolve_roles([], [])
        assert roles == {}

    @pytest.mark.unit
    def test_loaded_preferred_over_downloaded(self):
        """When a capability is present in both loaded and downloaded, loaded model wins."""
        loaded = ["loaded-vision"]
        downloaded = ["downloaded-vision"]
        metadata = {
            "loaded-vision": {"capabilities": {"vision": True}, "size_bytes": 5_000_000_000},
            "downloaded-vision": {"capabilities": {"vision": True}, "size_bytes": 3_000_000_000},
        }
        # Even though downloaded-vision is smaller, loaded-vision should win
        roles = _resolve_roles(loaded, downloaded, metadata)
        assert roles.get("vision") == "loaded-vision"


# ---------------------------------------------------------------------------
# discover_models() v2 — REST-first + wake-up ping (Commit 7)
# ---------------------------------------------------------------------------


class TestDiscoverModelsV2:
    """Unit tests for the rewritten discover_models() with REST-first path."""

    @pytest.mark.unit
    def test_discover_models_uses_rest_when_available(self):
        """When REST is available, discovery uses native metadata and sets lmstudio_available=True."""
        raw_models = [
            {
                "key": "qwen/qwen3-coder-30b",
                "loaded_instances": [{"instance_id": "inst-1"}],
                "capabilities": {"vision": False},
                "size_bytes": 18_000_000_000,
            }
        ]
        with (
            patch("tests.fixtures.model_discovery.LMSRestClient") as mock_rest_cls,
            patch("tests.fixtures.model_discovery.LMSHelper") as mock_lms,
            patch("tests.fixtures.model_discovery._wake_up_loaded_role_models"),
        ):
            mock_rest = MagicMock()
            mock_rest_cls.return_value = mock_rest
            mock_rest.is_server_available.return_value = True
            mock_rest.list_all_models.return_value = raw_models
            mock_rest.base_url = "http://localhost:1234"
            mock_lms._get_base_model_name.side_effect = lambda k: k

            result = discover_models()

        assert result.lmstudio_available is True
        assert "qwen/qwen3-coder-30b" in result.loaded_ids
        assert "qwen/qwen3-coder-30b" in result.downloaded_ids

    @pytest.mark.unit
    def test_discover_models_falls_back_to_cli(self):
        """When REST is unavailable, discovery falls back to CLI and still returns models."""
        loaded_raw = [{"modelKey": "some-instruct-7b", "identifier": "some-instruct-7b"}]
        with (
            patch("tests.fixtures.model_discovery.LMSRestClient") as mock_rest_cls,
            patch("tests.fixtures.model_discovery.LMSHelper") as mock_lms,
        ):
            mock_rest = MagicMock()
            mock_rest_cls.return_value = mock_rest
            mock_rest.is_server_available.return_value = False

            mock_lms.is_installed.return_value = True
            mock_lms.list_loaded_models.return_value = loaded_raw
            mock_lms.list_downloaded_models.return_value = []
            mock_lms._get_base_model_name.side_effect = lambda k: k

            result = discover_models()

        assert result.lmstudio_available is True
        assert "some-instruct-7b" in result.loaded_ids

    @pytest.mark.unit
    def test_discover_models_populates_metadata(self):
        """REST path populates models_metadata with capabilities from native API."""
        raw_models = [
            {
                "key": "vision-model",
                "loaded_instances": [],
                "capabilities": {"vision": True},
                "size_bytes": 8_000_000_000,
            }
        ]
        with (
            patch("tests.fixtures.model_discovery.LMSRestClient") as mock_rest_cls,
            patch("tests.fixtures.model_discovery.LMSHelper") as mock_lms,
            patch("tests.fixtures.model_discovery._wake_up_loaded_role_models"),
        ):
            mock_rest = MagicMock()
            mock_rest_cls.return_value = mock_rest
            mock_rest.is_server_available.return_value = True
            mock_rest.list_all_models.return_value = raw_models
            mock_rest.base_url = "http://localhost:1234"
            mock_lms._get_base_model_name.side_effect = lambda k: k

            result = discover_models()

        assert "vision-model" in result.models_metadata
        assert result.models_metadata["vision-model"]["capabilities"]["vision"] is True

    @pytest.mark.unit
    def test_wake_up_ping_called_for_loaded_role_models(self):
        """_wake_up_loaded_role_models is called when REST discovery finds loaded role models."""
        raw_models = [
            {
                "key": "chat-instruct",
                "loaded_instances": [{"instance_id": "inst-1"}],
                "capabilities": {},
                "size_bytes": 4_000_000_000,
            }
        ]
        with (
            patch("tests.fixtures.model_discovery.LMSRestClient") as mock_rest_cls,
            patch("tests.fixtures.model_discovery.LMSHelper") as mock_lms,
            patch("tests.fixtures.model_discovery._wake_up_loaded_role_models") as mock_ping,
        ):
            mock_rest = MagicMock()
            mock_rest_cls.return_value = mock_rest
            mock_rest.is_server_available.return_value = True
            mock_rest.list_all_models.return_value = raw_models
            mock_rest.base_url = "http://localhost:1234"
            mock_lms._get_base_model_name.side_effect = lambda k: k

            discover_models()

        mock_ping.assert_called_once()


# ---------------------------------------------------------------------------
# discover_models() DI tests (R-3) — rest_client injection
# ---------------------------------------------------------------------------


class TestDiscoverModelsDI:
    """Tests for optional rest_client parameter in discover_models() (R-3)."""

    @pytest.mark.unit
    def test_discover_models_uses_injected_client(self):
        """When rest_client is provided, its methods are called instead of creating a new one."""
        mock_client = MagicMock()
        mock_client.is_server_available.return_value = True
        mock_client.list_all_models.return_value = [
            {"key": "test-model-7b", "loaded_instances": [{}]},
        ]
        mock_client.base_url = "http://localhost:1234"

        with patch("tests.fixtures.model_discovery.LMSRestClient") as mock_cls, \
             patch("tests.fixtures.model_discovery.LMSHelper") as mock_lms, \
             patch("tests.fixtures.model_discovery._wake_up_loaded_role_models"):
            mock_lms._get_base_model_name.side_effect = lambda k: k
            result = discover_models(rest_client=mock_client)
            # LMSRestClient() constructor should NOT be called — we injected our own
            mock_cls.assert_not_called()
            # The injected client's methods should be called
            mock_client.is_server_available.assert_called_once()
            mock_client.list_all_models.assert_called_once()

    @pytest.mark.unit
    def test_discover_models_none_creates_default(self):
        """When rest_client=None (default), a new LMSRestClient is created."""
        with patch("tests.fixtures.model_discovery.LMSRestClient") as mock_cls, \
             patch("tests.fixtures.model_discovery.LMSHelper") as mock_lms:
            mock_instance = MagicMock()
            mock_instance.is_server_available.return_value = False
            mock_cls.return_value = mock_instance
            mock_lms.is_installed.return_value = False

            result = discover_models(rest_client=None)
            # LMSRestClient() constructor SHOULD be called
            mock_cls.assert_called_once()

    @pytest.mark.unit
    def test_discover_models_injected_client_not_available(self):
        """When injected client reports server unavailable, falls back to CLI."""
        mock_client = MagicMock()
        mock_client.is_server_available.return_value = False

        with patch("tests.fixtures.model_discovery.LMSHelper") as mock_lms:
            mock_lms.is_installed.return_value = False
            result = discover_models(rest_client=mock_client)

        assert result.lmstudio_available is False
        assert result.loaded_ids == []

    @pytest.mark.unit
    def test_discover_models_injected_client_raises(self):
        """When injected client raises an exception, falls back to CLI path."""
        mock_client = MagicMock()
        mock_client.is_server_available.return_value = True
        mock_client.list_all_models.side_effect = ConnectionError("boom")

        with patch("tests.fixtures.model_discovery.LMSHelper") as mock_lms:
            mock_lms.is_installed.return_value = False
            result = discover_models(rest_client=mock_client)

        # Should gracefully fall back to CLI (which also fails → empty result)
        assert isinstance(result, DiscoveredModels)
        assert result.lmstudio_available is False

    @pytest.mark.unit
    def test_discover_models_default_call_unchanged(self):
        """Calling discover_models() without arguments still works (backward compat)."""
        with _make_rest_unavailable(), \
             patch("tests.fixtures.model_discovery.LMSHelper") as mock_lms:
            mock_lms.is_installed.return_value = True
            mock_lms.list_loaded_models.return_value = [
                {"modelKey": "compat-model", "identifier": "compat-model"},
            ]
            mock_lms.list_downloaded_models.return_value = []
            mock_lms._get_base_model_name.side_effect = lambda k: k

            result = discover_models()

        assert result.lmstudio_available is True
        assert "compat-model" in result.loaded_ids
