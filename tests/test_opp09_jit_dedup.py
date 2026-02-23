"""OPP-09: Verify JIT guard deduplication and TTL fix."""
import ast
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestEnsureModelLoadedExtraction:
    """Tests for _ensure_model_loaded helper."""

    def test_method_exists(self):
        """_ensure_model_loaded must exist on LLMClient."""
        from llm.llm_client import LLMClient
        assert hasattr(LLMClient, "_ensure_model_loaded")

    def test_method_is_callable(self):
        """_ensure_model_loaded must be callable."""
        from llm.llm_client import LLMClient
        assert callable(getattr(LLMClient, "_ensure_model_loaded"))


class TestHardcodedTTLRemoved:
    """Verify ttl=600 hardcoded values are replaced with constants."""

    def test_no_ttl_600_in_source(self):
        """No ttl=600 literal should appear in llm_client.py."""
        source_path = os.path.join(os.path.dirname(__file__), "..", "llm", "llm_client.py")
        with open(source_path) as f:
            source = f.read()
        # Check for ttl=600 literal in source
        tree = ast.parse(source)
        ttl_600_found = False
        for node in ast.walk(tree):
            if isinstance(node, ast.keyword) and node.arg == "ttl":
                if isinstance(node.value, ast.Constant) and node.value.value == 600:
                    ttl_600_found = True
                    break
        assert not ttl_600_found, "Found ttl=600 hardcoded value — should use JIT_TTL_DEFAULT"


class TestJITGuardConsolidation:
    """Verify that ensure_model_loaded_with_verification is only called from _ensure_model_loaded."""

    def test_single_call_site_for_ensure_model_loaded_with_verification(self):
        """ensure_model_loaded_with_verification should appear exactly ONCE (inside _ensure_model_loaded)."""
        source_path = os.path.join(os.path.dirname(__file__), "..", "llm", "llm_client.py")
        with open(source_path) as f:
            source = f.read()
        count = source.count("ensure_model_loaded_with_verification")
        assert count == 1, (
            f"ensure_model_loaded_with_verification should appear exactly 1 time "
            f"(inside _ensure_model_loaded), found {count}"
        )


class TestStaleExportRemoved:
    """Verify stale ToolCallTracker removed from message_manager.__all__."""

    def test_no_toolcalltracker_in_all(self):
        """ToolCallTracker should NOT be in message_manager.__all__."""
        import llm.message_manager
        assert "ToolCallTracker" not in llm.message_manager.__all__, \
            "ToolCallTracker should be removed from __all__ (it doesn't exist)"


class TestJITGuardBehavior:
    """Verify _ensure_model_loaded behavior with mocks."""

    def test_skips_when_not_installed(self):
        """Should skip silently when LMS CLI is not installed."""
        from unittest.mock import patch, MagicMock
        from llm.llm_client import LLMClient

        client = LLMClient.__new__(LLMClient)
        client.model = "test-model"
        client.api_base = "http://localhost:1234/v1"
        client.session = MagicMock()

        with patch("llm.llm_client.LMSHelper") as mock_lms:
            mock_lms.is_installed.return_value = False
            # Should not raise
            client._ensure_model_loaded("test-model", ttl=1800)

    def test_skips_when_model_is_default(self):
        """Should skip when target_model is 'default'."""
        from unittest.mock import patch, MagicMock
        from llm.llm_client import LLMClient

        client = LLMClient.__new__(LLMClient)
        client.model = "test-model"
        client.api_base = "http://localhost:1234/v1"
        client.session = MagicMock()

        with patch("llm.llm_client.LMSHelper") as mock_lms:
            mock_lms.is_installed.return_value = True
            # Should not call is_model_loaded
            client._ensure_model_loaded("default", ttl=1800)
            mock_lms.is_model_loaded.assert_not_called()

    def test_skips_when_model_is_none(self):
        """Should skip when target_model is None."""
        from unittest.mock import patch, MagicMock
        from llm.llm_client import LLMClient

        client = LLMClient.__new__(LLMClient)
        client.model = "test-model"
        client.api_base = "http://localhost:1234/v1"
        client.session = MagicMock()

        with patch("llm.llm_client.LMSHelper") as mock_lms:
            mock_lms.is_installed.return_value = True
            client._ensure_model_loaded(None, ttl=1800)
            mock_lms.is_model_loaded.assert_not_called()

    def test_loads_when_not_loaded(self):
        """Should attempt loading when model is not loaded."""
        from unittest.mock import patch, MagicMock
        from llm.llm_client import LLMClient

        client = LLMClient.__new__(LLMClient)
        client.model = "test-model"
        client.api_base = "http://localhost:1234/v1"
        client.session = MagicMock()

        with patch("llm.llm_client.LMSHelper") as mock_lms:
            mock_lms.is_installed.return_value = True
            mock_lms.is_model_loaded.return_value = False
            mock_lms.ensure_model_loaded_with_verification.return_value = True
            client._ensure_model_loaded("my-model", ttl=1800)
            mock_lms.ensure_model_loaded_with_verification.assert_called_once_with("my-model", ttl=1800, skip_initial_check=True)

    def test_raises_on_load_failure(self):
        """Should raise LLMConnectionError when loading fails."""
        import pytest
        from unittest.mock import patch, MagicMock
        from llm.llm_client import LLMClient
        from llm.exceptions import LLMConnectionError

        client = LLMClient.__new__(LLMClient)
        client.model = "test-model"
        client.api_base = "http://localhost:1234/v1"
        client.session = MagicMock()

        with patch("llm.llm_client.LMSHelper") as mock_lms:
            mock_lms.is_installed.return_value = True
            mock_lms.is_model_loaded.return_value = False
            mock_lms.ensure_model_loaded_with_verification.return_value = False
            with pytest.raises(LLMConnectionError):
                client._ensure_model_loaded("my-model", ttl=1800)

    def test_already_loaded_skips_loading(self):
        """Should skip loading when model is already loaded."""
        from unittest.mock import patch, MagicMock
        from llm.llm_client import LLMClient

        client = LLMClient.__new__(LLMClient)
        client.model = "test-model"
        client.api_base = "http://localhost:1234/v1"
        client.session = MagicMock()

        with patch("llm.llm_client.LMSHelper") as mock_lms:
            mock_lms.is_installed.return_value = True
            mock_lms.is_model_loaded.return_value = True
            client._ensure_model_loaded("my-model", ttl=1800)
            mock_lms.ensure_model_loaded_with_verification.assert_not_called()

    def test_proceeds_on_unexpected_error(self):
        """Should log warning and proceed on unexpected errors."""
        from unittest.mock import patch, MagicMock
        from llm.llm_client import LLMClient

        client = LLMClient.__new__(LLMClient)
        client.model = "test-model"
        client.api_base = "http://localhost:1234/v1"
        client.session = MagicMock()

        with patch("llm.llm_client.LMSHelper") as mock_lms:
            mock_lms.is_installed.return_value = True
            mock_lms.is_model_loaded.side_effect = RuntimeError("unexpected")
            # Should NOT raise — just log warning and continue
            client._ensure_model_loaded("my-model", ttl=1800)
