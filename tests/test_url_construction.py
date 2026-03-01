"""
Tests for URL construction in LLMClient._get_endpoint callers.

These tests verify that no double-prefix bugs exist when api_base already
contains '/v1' (e.g. 'http://localhost:1234/v1').

RED phase: written BEFORE fixes — these tests must fail first, then pass
after the 3 fixes are applied.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch


class TestGetEndpointNoPrefixDoubling:
    """_get_endpoint must never produce /v1/v1/... URLs."""

    def _make_client(self, api_base: str = "http://localhost:1234/v1") -> object:
        """Return an LLMClient instance without hitting the network."""
        with patch("llm.llm_client.LLMClient._ensure_model_loaded"):
            from llm.llm_client import LLMClient

            client = LLMClient.__new__(LLMClient)
            client.api_base = api_base
            client.session = MagicMock()
            return client

    # ------------------------------------------------------------------
    # Core contract: _get_endpoint itself
    # ------------------------------------------------------------------

    def test_get_endpoint_chat_completions(self):
        """chat/completions -> /v1/chat/completions, not /v1/v1/chat/completions."""
        client = self._make_client()
        url = client._get_endpoint("chat/completions")
        assert url == "http://localhost:1234/v1/chat/completions", (
            f"Expected http://localhost:1234/v1/chat/completions, got {url}"
        )
        assert url.count("/v1") == 1, (
            f"URL contains duplicate /v1: {url}"
        )

    def test_get_endpoint_messages_no_double_prefix(self):
        """'messages' path -> /v1/messages, not /v1/v1/messages."""
        client = self._make_client()
        url = client._get_endpoint("messages")
        assert url == "http://localhost:1234/v1/messages", (
            f"Expected http://localhost:1234/v1/messages, got {url}"
        )
        assert url.count("/v1") == 1, (
            f"URL contains duplicate /v1: {url}"
        )

    def test_get_endpoint_models(self):
        """models -> /v1/models, no double prefix."""
        client = self._make_client()
        url = client._get_endpoint("models")
        assert url == "http://localhost:1234/v1/models", (
            f"Expected http://localhost:1234/v1/models, got {url}"
        )
        assert url.count("/v1") == 1, (
            f"URL contains duplicate /v1: {url}"
        )

    # ------------------------------------------------------------------
    # Bug 1: ANTHROPIC_MESSAGES_ENDPOINT must not contain leading /v1
    # ------------------------------------------------------------------

    def test_anthropic_messages_endpoint_constant_has_no_v1_prefix(self):
        """ANTHROPIC_MESSAGES_ENDPOINT must be 'messages', not '/v1/messages'.

        When passed to _get_endpoint, '/v1/messages' produces /v1/v1/messages.
        The constant must be 'messages' so the result is /v1/messages.
        """
        from config.constants import ANTHROPIC_MESSAGES_ENDPOINT

        assert ANTHROPIC_MESSAGES_ENDPOINT == "messages", (
            f"ANTHROPIC_MESSAGES_ENDPOINT should be 'messages' (no /v1 prefix), "
            f"got '{ANTHROPIC_MESSAGES_ENDPOINT}'. "
            f"When api_base already ends with /v1, passing '/v1/messages' produces /v1/v1/messages."
        )

    def test_anthropic_messages_endpoint_via_get_endpoint(self):
        """ANTHROPIC_MESSAGES_ENDPOINT used with _get_endpoint produces correct URL."""
        from config.constants import ANTHROPIC_MESSAGES_ENDPOINT

        client = self._make_client()
        url = client._get_endpoint(ANTHROPIC_MESSAGES_ENDPOINT)
        assert url == "http://localhost:1234/v1/messages", (
            f"Expected http://localhost:1234/v1/messages, got {url}"
        )
        assert "/v1/v1/" not in url, (
            f"Double /v1 prefix detected in URL: {url}"
        )

    # ------------------------------------------------------------------
    # Bug 2: chat_completion_with_native_mcp must use "chat/completions"
    # ------------------------------------------------------------------

    def test_native_mcp_chat_completions_path_no_v1_prefix(self):
        """chat_completion_with_native_mcp must call _get_endpoint('chat/completions').

        Line 1132 previously used 'v1/chat/completions' which produces /v1/v1/chat/completions.
        """
        import ast

        with open(Path(__file__).parent.parent / "llm" / "llm_client.py") as f:
            tree = ast.parse(f.read())

        # Find chat_completion_with_native_mcp function body
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "chat_completion_with_native_mcp":
                    for child in ast.walk(node):
                        if isinstance(child, ast.Call):
                            # Look for self._get_endpoint(...) calls
                            if (
                                isinstance(child.func, ast.Attribute)
                                and child.func.attr == "_get_endpoint"
                                and child.args
                            ):
                                arg = child.args[0]
                                if isinstance(arg, ast.Constant):
                                    val = arg.value
                                    assert val == "chat/completions", (
                                        f"chat_completion_with_native_mcp calls "
                                        f"_get_endpoint('{val}') — should be "
                                        f"'chat/completions' not '{val}'. "
                                        f"Passing 'v1/chat/completions' when api_base already "
                                        f"ends with /v1 produces /v1/v1/chat/completions."
                                    )
                    return

        # If function not found, fail with a clear message
        assert False, "chat_completion_with_native_mcp not found in llm_client.py"

    # ------------------------------------------------------------------
    # Bug 3: supports_native_mcp must bypass _get_endpoint for /api/v1/...
    # ------------------------------------------------------------------

    def test_supports_native_mcp_does_not_use_get_endpoint_for_server_info(self):
        """supports_native_mcp must NOT call _get_endpoint('api/v1/server/info').

        That path is under /api/v1/, not under the OpenAI-compat /v1 prefix.
        Using _get_endpoint would produce /v1/api/v1/server/info.
        Instead, the base URL (/v1 stripped) must be used directly.
        """
        import ast

        with open(Path(__file__).parent.parent / "llm" / "llm_client.py") as f:
            tree = ast.parse(f.read())

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "supports_native_mcp":
                    for child in ast.walk(node):
                        if isinstance(child, ast.Call):
                            if (
                                isinstance(child.func, ast.Attribute)
                                and child.func.attr == "_get_endpoint"
                                and child.args
                            ):
                                arg = child.args[0]
                                if isinstance(arg, ast.Constant):
                                    val = arg.value
                                    assert "api/v1" not in val, (
                                        f"supports_native_mcp calls _get_endpoint('{val}'). "
                                        f"The /api/v1/server/info endpoint lives at the base URL, "
                                        f"not under the /v1 OpenAI-compat prefix. "
                                        f"This produces /v1/api/v1/server/info — wrong URL."
                                    )
                    return

        assert False, "supports_native_mcp not found in llm_client.py"

    def test_supports_native_mcp_server_info_url_uses_base_without_v1(self):
        """supports_native_mcp GET request URL must end with /api/v1/server/info.

        The URL must be built from base_url (api_base with /v1 stripped),
        not from _get_endpoint which appends to api_base including /v1.
        """
        import ast

        with open(Path(__file__).parent.parent / "llm" / "llm_client.py") as f:
            source = f.read()
            tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "supports_native_mcp":
                    # The function body must reference rsplit or equivalent
                    # to strip /v1 from api_base
                    func_lines = ast.get_source_segment(source, node) or ""
                    assert "rsplit" in func_lines or "base_url" in func_lines, (
                        "supports_native_mcp must compute base_url by stripping /v1 from "
                        "api_base (e.g. self.api_base.rsplit('/v1', 1)[0]) before "
                        "building the /api/v1/server/info URL."
                    )
                    return

        assert False, "supports_native_mcp not found in llm_client.py"
