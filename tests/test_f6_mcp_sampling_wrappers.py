#!/usr/bin/env python3
"""Tests for F-6: MCP tool wrappers must expose min_p/top_k parameters."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tools.completions import CompletionTools, _validate_generation_params


class TestCompletionToolsChatMinPTopK:
    """CompletionTools.chat_completion passes min_p/top_k to LLMClient."""

    def _make_tools(self):
        """Create CompletionTools with mocked LLMClient."""
        mock_client = MagicMock()
        mock_client.chat_completion.return_value = {
            "choices": [{"message": {"content": "test response"}}]
        }
        return CompletionTools(llm_client=mock_client), mock_client

    @pytest.mark.asyncio
    async def test_chat_passes_min_p(self):
        """chat_completion passes min_p to LLMClient."""
        tools, mock_client = self._make_tools()
        await tools.chat_completion(prompt="hi", min_p=0.1)
        mock_client.chat_completion.assert_called_once()
        call_kwargs = mock_client.chat_completion.call_args[1]
        assert call_kwargs["min_p"] == 0.1

    @pytest.mark.asyncio
    async def test_chat_passes_top_k(self):
        """chat_completion passes top_k to LLMClient."""
        tools, mock_client = self._make_tools()
        await tools.chat_completion(prompt="hi", top_k=40)
        mock_client.chat_completion.assert_called_once()
        call_kwargs = mock_client.chat_completion.call_args[1]
        assert call_kwargs["top_k"] == 40

    @pytest.mark.asyncio
    async def test_chat_none_not_forced(self):
        """Default None values don't force min_p/top_k."""
        tools, mock_client = self._make_tools()
        await tools.chat_completion(prompt="hi")
        mock_client.chat_completion.assert_called_once()
        # Should still be called but params are None by default
        call_kwargs = mock_client.chat_completion.call_args[1]
        assert call_kwargs.get("min_p") is None
        assert call_kwargs.get("top_k") is None

    @pytest.mark.asyncio
    async def test_chat_validates_before_call(self):
        """Invalid min_p raises ValueError before LLMClient call."""
        tools, mock_client = self._make_tools()
        with pytest.raises(ValueError, match="min_p"):
            await tools.chat_completion(prompt="hi", min_p=-1.0)
        mock_client.chat_completion.assert_not_called()


class TestCompletionToolsTextMinPTopK:
    """CompletionTools.text_completion passes min_p/top_k to LLMClient."""

    def _make_tools(self):
        mock_client = MagicMock()
        mock_client.text_completion.return_value = {
            "choices": [{"text": "completed text"}]
        }
        return CompletionTools(llm_client=mock_client), mock_client

    @pytest.mark.asyncio
    async def test_text_passes_min_p(self):
        tools, mock_client = self._make_tools()
        await tools.text_completion(prompt="hello", min_p=0.2)
        call_kwargs = mock_client.text_completion.call_args[1]
        assert call_kwargs["min_p"] == 0.2

    @pytest.mark.asyncio
    async def test_text_passes_top_k(self):
        tools, mock_client = self._make_tools()
        await tools.text_completion(prompt="hello", top_k=50)
        call_kwargs = mock_client.text_completion.call_args[1]
        assert call_kwargs["top_k"] == 50


class TestCompletionToolsAnthropicMinPTopK:
    """CompletionTools.anthropic_messages passes min_p/top_k to LLMClient."""

    def _make_tools(self):
        mock_client = MagicMock()
        mock_client.anthropic_messages.return_value = {
            "content": [{"type": "text", "text": "response"}]
        }
        return CompletionTools(llm_client=mock_client), mock_client

    @pytest.mark.asyncio
    async def test_anthropic_passes_min_p(self):
        tools, mock_client = self._make_tools()
        await tools.anthropic_messages(
            messages='[{"role": "user", "content": "hi"}]',
            min_p=0.15,
        )
        call_kwargs = mock_client.anthropic_messages.call_args[1]
        assert call_kwargs["min_p"] == 0.15

    @pytest.mark.asyncio
    async def test_anthropic_passes_top_k(self):
        tools, mock_client = self._make_tools()
        await tools.anthropic_messages(
            messages='[{"role": "user", "content": "hi"}]',
            top_k=30,
        )
        call_kwargs = mock_client.anthropic_messages.call_args[1]
        assert call_kwargs["top_k"] == 30
