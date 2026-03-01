"""Tests for ARCH-5: platform-abstract MCP process spawning.

Verifies that node/npx resolution uses shutil.which() first with
platform-specific fallbacks, replacing hardcoded Homebrew paths.

Test categories (Req 07):
- Happy: Tests 1, 2 — shutil.which finds npx/node directly
- Negative: Test 3 — shutil.which returns None on non-macOS → returns (None, None)
- Edge: Tests 4, 5 — empty string from which treated as falsy; macOS fallback used
- Boundary: Test 6 — get_connection_params uses resolved paths
- Edge: Test 7 — _resolve_homebrew_node isolation
- Edge: Test 8 — shutil.which finds node but not npx
"""

from unittest.mock import patch, MagicMock

import pytest

from mcp_client.discovery import MCPDiscovery


class TestResolveNodeAndNpx:
    """Tests for _resolve_node_and_npx helper."""

    def test_shutil_which_finds_both(self) -> None:
        """Happy: shutil.which finds both node and npx → used directly."""
        with patch("mcp_client.discovery.shutil") as mock_shutil:
            mock_shutil.which.side_effect = lambda cmd: {
                "node": "/usr/local/bin/node",
                "npx": "/usr/local/bin/npx",
            }.get(cmd)

            node, npx = MCPDiscovery._resolve_node_and_npx()

        assert node == "/usr/local/bin/node"
        assert npx == "/usr/local/bin/npx"

    def test_shutil_which_finds_npx_only(self) -> None:
        """Happy: shutil.which finds npx but not node → npx still returned."""
        with patch("mcp_client.discovery.shutil") as mock_shutil:
            mock_shutil.which.side_effect = lambda cmd: {
                "npx": "/usr/bin/npx",
            }.get(cmd)
            with patch("mcp_client.discovery.platform") as mock_platform:
                mock_platform.system.return_value = "Linux"

                node, npx = MCPDiscovery._resolve_node_and_npx()

        assert node is None
        assert npx == "/usr/bin/npx"

    def test_nothing_found_non_macos(self) -> None:
        """Negative: shutil.which returns None on Linux → (None, None)."""
        with patch("mcp_client.discovery.shutil") as mock_shutil:
            mock_shutil.which.return_value = None
            with patch("mcp_client.discovery.platform") as mock_platform:
                mock_platform.system.return_value = "Linux"

                node, npx = MCPDiscovery._resolve_node_and_npx()

        assert node is None
        assert npx is None

    def test_empty_string_treated_as_falsy(self) -> None:
        """Edge: shutil.which returns empty string → treated as not found."""
        with patch("mcp_client.discovery.shutil") as mock_shutil:
            mock_shutil.which.return_value = ""
            with patch("mcp_client.discovery.platform") as mock_platform:
                mock_platform.system.return_value = "Linux"

                node, npx = MCPDiscovery._resolve_node_and_npx()

        assert node is None
        assert npx is None

    def test_macos_homebrew_fallback(self) -> None:
        """Edge: shutil.which fails on macOS → Homebrew fallback used."""
        with patch("mcp_client.discovery.shutil") as mock_shutil:
            mock_shutil.which.return_value = None
            with patch("mcp_client.discovery.platform") as mock_platform:
                mock_platform.system.return_value = "Darwin"
                with patch.object(
                    MCPDiscovery,
                    "_resolve_homebrew_node",
                    return_value=("/opt/homebrew/bin/node", "/opt/homebrew/bin/npx"),
                ) as mock_hb:
                    node, npx = MCPDiscovery._resolve_node_and_npx()
                    mock_hb.assert_called_once()

        assert node == "/opt/homebrew/bin/node"
        assert npx == "/opt/homebrew/bin/npx"


class TestResolveHomebrewNode:
    """Tests for _resolve_homebrew_node isolation."""

    def test_finds_cellar_binaries(self) -> None:
        """Edge: Homebrew Cellar glob finds node and npx."""
        with patch("mcp_client.discovery.glob") as mock_glob:
            mock_glob.glob.side_effect = lambda pattern: {
                "/opt/homebrew/Cellar/node/*/bin/node": [
                    "/opt/homebrew/Cellar/node/22.0.0/bin/node"
                ],
                "/opt/homebrew/Cellar/node/*/bin/npx": [
                    "/opt/homebrew/Cellar/node/22.0.0/bin/npx"
                ],
            }.get(pattern, [])
            with patch("mcp_client.discovery.os.path.isfile", return_value=False):
                node, npx = MCPDiscovery._resolve_homebrew_node()

        assert node == "/opt/homebrew/Cellar/node/22.0.0/bin/node"
        assert npx == "/opt/homebrew/Cellar/node/22.0.0/bin/npx"

    def test_falls_back_to_symlink_paths(self) -> None:
        """Edge: Cellar glob empty → falls back to /opt/homebrew/bin."""
        with patch("mcp_client.discovery.glob") as mock_glob:
            mock_glob.glob.return_value = []
            with patch(
                "mcp_client.discovery.os.path.isfile",
                side_effect=lambda p: p in (
                    "/opt/homebrew/bin/node",
                    "/opt/homebrew/bin/npx",
                ),
            ):
                node, npx = MCPDiscovery._resolve_homebrew_node()

        assert node == "/opt/homebrew/bin/node"
        assert npx == "/opt/homebrew/bin/npx"

    def test_nothing_found_returns_none(self) -> None:
        """Boundary: No Homebrew node at all → (None, None)."""
        with patch("mcp_client.discovery.glob") as mock_glob:
            mock_glob.glob.return_value = []
            with patch("mcp_client.discovery.os.path.isfile", return_value=False):
                node, npx = MCPDiscovery._resolve_homebrew_node()

        assert node is None
        assert npx is None


class TestGetConnectionParamsUsesResolved:
    """Boundary: get_connection_params uses _resolve_node_and_npx for npx commands."""

    def test_npx_command_resolved(self) -> None:
        """get_connection_params resolves npx command via _resolve_node_and_npx."""
        discovery = MCPDiscovery.__new__(MCPDiscovery)
        discovery.mcp_configs = {
            "test-mcp": {
                "command": "npx",
                "args": ["-y", "@test/mcp-server"],
            }
        }

        with patch.object(
            MCPDiscovery,
            "_resolve_node_and_npx",
            return_value=("/usr/local/bin/node", "/usr/local/bin/npx"),
        ):
            params = discovery.get_connection_params("test-mcp")

        assert params["command"] == "/usr/local/bin/node"
        assert params["args"][0] == "/usr/local/bin/npx"
        assert "-y" in params["args"]

    def test_non_npx_command_unchanged(self) -> None:
        """Non-npx commands pass through unmodified."""
        discovery = MCPDiscovery.__new__(MCPDiscovery)
        discovery.mcp_configs = {
            "test-mcp": {
                "command": "python",
                "args": ["server.py"],
            }
        }

        params = discovery.get_connection_params("test-mcp")

        assert params["command"] == "python"
        assert params["args"] == ["server.py"]
