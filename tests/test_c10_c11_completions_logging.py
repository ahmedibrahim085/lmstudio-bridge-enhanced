#!/usr/bin/env python3
"""Tests for C-10/C-11: Error logging in CompletionTools.

C-10: create_response() catches bare Exception with zero logging.
C-11: anthropic_messages() catches bare Exception with zero logging.
Both must call logger.error(exc_info=True) before returning error JSON.
"""
import json
from unittest.mock import MagicMock, patch

import pytest


class TestCompletionsModuleLogger:
    """Module-level logger must exist for error visibility."""

    def test_module_has_logger(self):
        """tools.completions must define a module-level logger."""
        import tools.completions as mod

        assert hasattr(mod, "logger"), "Module must have a logger attribute"


class TestCreateResponseErrorLogging:
    """C-10: create_response must log errors, not silently swallow."""

    def _make_tools(self):
        from tools.completions import CompletionTools

        mock_client = MagicMock()
        return CompletionTools(llm_client=mock_client), mock_client

    @pytest.mark.asyncio
    async def test_create_response_logs_on_error(self):
        """When create_response raises, logger.error is called with exc_info."""
        tools, mock_client = self._make_tools()
        mock_client.create_response.side_effect = RuntimeError("boom")

        with patch("tools.completions.logger") as mock_logger:
            result = await tools.create_response(input_text="hi")
            mock_logger.error.assert_called_once()
            # Must include exc_info=True for stack trace
            _, kwargs = mock_logger.error.call_args
            assert kwargs.get("exc_info") is True

        # Still returns error JSON (existing behavior preserved)
        parsed = json.loads(result)
        assert "error" in parsed

    @pytest.mark.asyncio
    async def test_create_response_error_message_has_context(self):
        """Error log message includes method name context."""
        tools, mock_client = self._make_tools()
        mock_client.create_response.side_effect = RuntimeError("specific failure")

        with patch("tools.completions.logger") as mock_logger:
            await tools.create_response(input_text="hi")
            log_args = mock_logger.error.call_args[0][0]
            assert "create_response" in log_args.lower() or "response" in log_args.lower()


class TestAnthropicMessagesErrorLogging:
    """C-11: anthropic_messages must log errors, not silently swallow."""

    def _make_tools(self):
        from tools.completions import CompletionTools

        mock_client = MagicMock()
        return CompletionTools(llm_client=mock_client), mock_client

    @pytest.mark.asyncio
    async def test_anthropic_messages_logs_on_error(self):
        """When anthropic_messages raises, logger.error is called with exc_info."""
        tools, mock_client = self._make_tools()
        mock_client.anthropic_messages.side_effect = RuntimeError("boom")

        with patch("tools.completions.logger") as mock_logger:
            result = await tools.anthropic_messages(
                messages='[{"role": "user", "content": "hi"}]'
            )
            mock_logger.error.assert_called_once()
            _, kwargs = mock_logger.error.call_args
            assert kwargs.get("exc_info") is True

        parsed = json.loads(result)
        assert "error" in parsed

    @pytest.mark.asyncio
    async def test_anthropic_error_message_has_context(self):
        """Error log message includes method name context."""
        tools, mock_client = self._make_tools()
        mock_client.anthropic_messages.side_effect = RuntimeError("auth failure")

        with patch("tools.completions.logger") as mock_logger:
            await tools.anthropic_messages(
                messages='[{"role": "user", "content": "hi"}]'
            )
            log_args = mock_logger.error.call_args[0][0]
            assert "anthropic" in log_args.lower() or "message" in log_args.lower()
