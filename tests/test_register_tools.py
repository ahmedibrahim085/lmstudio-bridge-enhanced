#!/usr/bin/env python3
"""Tests for untested register_*_tools() public API functions.

Covers C-16/C-17 findings: register_completion_tools() and
register_lms_cli_tools() had zero test coverage.
"""
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# register_completion_tools
# ---------------------------------------------------------------------------

class TestRegisterCompletionTools:
    """register_completion_tools must register 5 tools on mock MCP server."""

    def test_registers_five_tools(self):
        from tools.completions import register_completion_tools

        mock_mcp = MagicMock()
        register_completion_tools(mock_mcp, llm_client=MagicMock())
        assert mock_mcp.tool.call_count == 5

    def test_registers_chat_completion(self):
        from tools.completions import register_completion_tools

        mock_mcp = MagicMock()
        register_completion_tools(mock_mcp, llm_client=MagicMock())
        registered = [
            call[0][0].__name__
            for call in mock_mcp.tool.return_value.call_args_list
        ]
        assert "chat_completion" in registered

    def test_registers_text_completion(self):
        from tools.completions import register_completion_tools

        mock_mcp = MagicMock()
        register_completion_tools(mock_mcp, llm_client=MagicMock())
        registered = [
            call[0][0].__name__
            for call in mock_mcp.tool.return_value.call_args_list
        ]
        assert "text_completion" in registered

    def test_registers_create_response(self):
        from tools.completions import register_completion_tools

        mock_mcp = MagicMock()
        register_completion_tools(mock_mcp, llm_client=MagicMock())
        registered = [
            call[0][0].__name__
            for call in mock_mcp.tool.return_value.call_args_list
        ]
        assert "create_response" in registered

    def test_registers_validate_json_schema(self):
        from tools.completions import register_completion_tools

        mock_mcp = MagicMock()
        register_completion_tools(mock_mcp, llm_client=MagicMock())
        registered = [
            call[0][0].__name__
            for call in mock_mcp.tool.return_value.call_args_list
        ]
        assert "validate_json_schema" in registered

    def test_registers_anthropic_messages(self):
        from tools.completions import register_completion_tools

        mock_mcp = MagicMock()
        register_completion_tools(mock_mcp, llm_client=MagicMock())
        registered = [
            call[0][0].__name__
            for call in mock_mcp.tool.return_value.call_args_list
        ]
        assert "anthropic_messages" in registered

    def test_accepts_none_llm_client(self):
        """register_completion_tools works when llm_client=None (creates default)."""
        from tools.completions import register_completion_tools

        mock_mcp = MagicMock()
        register_completion_tools(mock_mcp, llm_client=None)
        assert mock_mcp.tool.call_count == 5

    def test_creates_completion_tools_instance(self):
        """Must create a CompletionTools instance internally."""
        from tools.completions import register_completion_tools, CompletionTools

        mock_mcp = MagicMock()
        mock_llm = MagicMock()
        with patch.object(CompletionTools, "__init__", return_value=None) as mock_init:
            register_completion_tools(mock_mcp, llm_client=mock_llm)
            mock_init.assert_called_once_with(mock_llm)


# ---------------------------------------------------------------------------
# register_lms_cli_tools
# ---------------------------------------------------------------------------

class TestRegisterLmsCliTools:
    """register_lms_cli_tools must register 9 tools on mock MCP server."""

    def test_registers_nine_tools(self):
        from tools.lms_cli_tools import register_lms_cli_tools

        mock_mcp = MagicMock()
        register_lms_cli_tools(mock_mcp)
        assert mock_mcp.tool.call_count == 9

    def test_registers_lms_list_loaded_models(self):
        from tools.lms_cli_tools import register_lms_cli_tools, lms_list_loaded_models

        mock_mcp = MagicMock()
        register_lms_cli_tools(mock_mcp)
        registered = [
            call[0][0] for call in mock_mcp.tool.return_value.call_args_list
        ]
        assert lms_list_loaded_models in registered

    def test_registers_lms_list_downloaded_models(self):
        from tools.lms_cli_tools import register_lms_cli_tools, lms_list_downloaded_models

        mock_mcp = MagicMock()
        register_lms_cli_tools(mock_mcp)
        registered = [
            call[0][0] for call in mock_mcp.tool.return_value.call_args_list
        ]
        assert lms_list_downloaded_models in registered

    def test_registers_lms_load_model(self):
        from tools.lms_cli_tools import register_lms_cli_tools, lms_load_model

        mock_mcp = MagicMock()
        register_lms_cli_tools(mock_mcp)
        registered = [
            call[0][0] for call in mock_mcp.tool.return_value.call_args_list
        ]
        assert lms_load_model in registered

    def test_registers_lms_unload_model(self):
        from tools.lms_cli_tools import register_lms_cli_tools, lms_unload_model

        mock_mcp = MagicMock()
        register_lms_cli_tools(mock_mcp)
        registered = [
            call[0][0] for call in mock_mcp.tool.return_value.call_args_list
        ]
        assert lms_unload_model in registered

    def test_registers_lms_ensure_model_loaded(self):
        from tools.lms_cli_tools import register_lms_cli_tools, lms_ensure_model_loaded

        mock_mcp = MagicMock()
        register_lms_cli_tools(mock_mcp)
        registered = [
            call[0][0] for call in mock_mcp.tool.return_value.call_args_list
        ]
        assert lms_ensure_model_loaded in registered

    def test_registers_lms_search_models(self):
        from tools.lms_cli_tools import register_lms_cli_tools, lms_search_models

        mock_mcp = MagicMock()
        register_lms_cli_tools(mock_mcp)
        registered = [
            call[0][0] for call in mock_mcp.tool.return_value.call_args_list
        ]
        assert lms_search_models in registered

    def test_registers_lms_download_model(self):
        from tools.lms_cli_tools import register_lms_cli_tools, lms_download_model

        mock_mcp = MagicMock()
        register_lms_cli_tools(mock_mcp)
        registered = [
            call[0][0] for call in mock_mcp.tool.return_value.call_args_list
        ]
        assert lms_download_model in registered

    def test_registers_lms_resolve_model(self):
        from tools.lms_cli_tools import register_lms_cli_tools, lms_resolve_model

        mock_mcp = MagicMock()
        register_lms_cli_tools(mock_mcp)
        registered = [
            call[0][0] for call in mock_mcp.tool.return_value.call_args_list
        ]
        assert lms_resolve_model in registered

    def test_registers_lms_server_status(self):
        from tools.lms_cli_tools import register_lms_cli_tools, lms_server_status

        mock_mcp = MagicMock()
        register_lms_cli_tools(mock_mcp)
        registered = [
            call[0][0] for call in mock_mcp.tool.return_value.call_args_list
        ]
        assert lms_server_status in registered
