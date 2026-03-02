"""RED tests for Review Round 1 findings H-1 and H-2."""

import ast
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── H-1: ensure_model_loaded as free function ──────────────────────────


class TestJITLoaderModule:
    """H-1: _ensure_model_loaded extracted to llm/jit_loader.py."""

    def test_ensure_model_loaded_importable(self):
        """ensure_model_loaded must be importable from llm.jit_loader."""
        from llm.jit_loader import ensure_model_loaded

        assert callable(ensure_model_loaded)

    def test_ensure_model_loaded_in_all(self):
        """ensure_model_loaded must be in llm.jit_loader.__all__."""
        import llm.jit_loader

        assert "ensure_model_loaded" in llm.jit_loader.__all__

    def test_no_chatclient_import_in_responses_client(self):
        """ResponsesClient must NOT import ChatClient for JIT loading."""
        source_path = os.path.join(os.path.dirname(__file__), "..", "llm", "responses_client.py")
        with open(source_path) as f:
            source = f.read()
        assert "from llm.chat_client import ChatClient" not in source
        assert "ChatClient(" not in source

    def test_no_chatclient_import_in_anthropic_client(self):
        """AnthropicClient must NOT import ChatClient for JIT loading."""
        source_path = os.path.join(os.path.dirname(__file__), "..", "llm", "anthropic_client.py")
        with open(source_path) as f:
            source = f.read()
        assert "from llm.chat_client import ChatClient" not in source
        assert "ChatClient(" not in source

    def test_no_chatclient_import_in_streaming_client(self):
        """StreamingClient must NOT import ChatClient for JIT loading."""
        source_path = os.path.join(os.path.dirname(__file__), "..", "llm", "streaming_client.py")
        with open(source_path) as f:
            source = f.read()
        assert "from llm.chat_client import ChatClient" not in source
        assert "ChatClient(" not in source

    def test_no_chatclient_jit_import_in_thinking_client(self):
        """ThinkingClient must NOT import ChatClient for JIT loading (chat_fn fallback is OK)."""
        source_path = os.path.join(os.path.dirname(__file__), "..", "llm", "thinking_client.py")
        with open(source_path) as f:
            source = f.read()
        # ThinkingClient may still import ChatClient for _chat_fn fallback,
        # but NOT for _ensure_model_loaded
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Look for ChatClient(...)._ensure_model_loaded pattern
                if isinstance(node.func, ast.Attribute) and node.func.attr == "_ensure_model_loaded":
                    if isinstance(node.func.value, ast.Call):
                        func = node.func.value.func
                        if isinstance(func, ast.Name) and func.id in ("ChatClient", "CC"):
                            pytest.fail("ThinkingClient still constructs ChatClient for JIT loading")
                        if isinstance(func, ast.Attribute) and func.attr in ("ChatClient", "CC"):
                            pytest.fail("ThinkingClient still constructs ChatClient for JIT loading")

    def test_jit_loader_behavior_skips_when_not_installed(self):
        """Free function skips when LMS CLI is not installed."""
        from unittest.mock import patch

        from llm.jit_loader import ensure_model_loaded

        with patch("llm.jit_loader.LMSHelper") as mock_lms:
            mock_lms.is_installed.return_value = False
            # Should not raise
            ensure_model_loaded("test-model", ttl=1800)
            mock_lms.is_model_loaded.assert_not_called()

    def test_jit_loader_behavior_loads_when_needed(self):
        """Free function attempts load when model not loaded."""
        from unittest.mock import patch

        from llm.jit_loader import ensure_model_loaded

        with patch("llm.jit_loader.LMSHelper") as mock_lms:
            mock_lms.is_installed.return_value = True
            mock_lms.is_model_loaded.return_value = False
            mock_lms.ensure_model_loaded_with_verification.return_value = True
            ensure_model_loaded("my-model", ttl=1800)
            mock_lms.ensure_model_loaded_with_verification.assert_called_once_with(
                "my-model", ttl=1800, skip_initial_check=True,
            )


# ── H-2: Protocols wired into Facade ──────────────────────────────────


class TestProtocolsWired:
    """H-2: Protocol classes are referenced in production code (not dead)."""

    def test_protocols_imported_in_facade(self):
        """llm_client.py must import at least one Protocol from llm.protocols."""
        source_path = os.path.join(os.path.dirname(__file__), "..", "llm", "llm_client.py")
        with open(source_path) as f:
            source = f.read()
        assert "from llm.protocols import" in source

    def test_protocols_are_runtime_checkable(self):
        """All protocols must be @runtime_checkable for isinstance checks."""
        from llm.protocols import (
            AnthropicProvider,
            ChatProvider,
            ModelInfoProvider,
            ResponseProvider,
            StreamProvider,
            ThinkingProvider,
        )

        for proto in (ChatProvider, ResponseProvider, AnthropicProvider,
                      StreamProvider, ModelInfoProvider, ThinkingProvider):
            # runtime_checkable protocols have _is_runtime_protocol = True
            assert getattr(proto, "_is_runtime_protocol", False), (
                f"{proto.__name__} is not @runtime_checkable"
            )

    def test_chatclient_satisfies_chat_provider(self):
        """ChatClient must satisfy the ChatProvider protocol."""
        from llm.chat_client import ChatClient
        from llm.protocols import ChatProvider

        assert isinstance(ChatClient.__new__(ChatClient), ChatProvider)

    def test_responses_client_satisfies_response_provider(self):
        """ResponsesClient must satisfy the ResponseProvider protocol."""
        from llm.protocols import ResponseProvider
        from llm.responses_client import ResponsesClient

        assert isinstance(ResponsesClient.__new__(ResponsesClient), ResponseProvider)

    def test_anthropic_client_satisfies_anthropic_provider(self):
        """AnthropicClient must satisfy the AnthropicProvider protocol."""
        from llm.anthropic_client import AnthropicClient
        from llm.protocols import AnthropicProvider

        assert isinstance(AnthropicClient.__new__(AnthropicClient), AnthropicProvider)

    def test_streaming_client_satisfies_stream_provider(self):
        """StreamingClient must satisfy the StreamProvider protocol."""
        from llm.protocols import StreamProvider
        from llm.streaming_client import StreamingClient

        assert isinstance(StreamingClient.__new__(StreamingClient), StreamProvider)

    def test_model_info_client_satisfies_model_info_provider(self):
        """ModelInfoClient must satisfy the ModelInfoProvider protocol."""
        from llm.model_info_client import ModelInfoClient
        from llm.protocols import ModelInfoProvider

        assert isinstance(ModelInfoClient.__new__(ModelInfoClient), ModelInfoProvider)

    def test_thinking_client_satisfies_thinking_provider(self):
        """ThinkingClient must satisfy the ThinkingProvider protocol."""
        from llm.protocols import ThinkingProvider
        from llm.thinking_client import ThinkingClient

        assert isinstance(ThinkingClient.__new__(ThinkingClient), ThinkingProvider)
