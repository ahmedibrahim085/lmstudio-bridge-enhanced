"""Tests for SSRF protection in image URL processing (H-3 security fix)."""

import os
import sys

import pytest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.image_utils import _process_url, _is_safe_url


class TestIsSafeUrl:
    """Test the URL safety validation function."""

    # -- Safe URLs (should pass) --

    def test_safe_https_url(self):
        assert _is_safe_url("https://example.com/image.png") is True

    def test_safe_http_url(self):
        assert _is_safe_url("http://cdn.example.com/photo.jpg") is True

    def test_safe_url_with_path_and_query(self):
        assert _is_safe_url("https://images.site.com/img/1?w=800") is True

    # -- Blocked schemes --

    def test_blocks_file_scheme(self):
        assert _is_safe_url("file:///etc/passwd") is False

    def test_blocks_ftp_scheme(self):
        assert _is_safe_url("ftp://evil.com/image.png") is False

    def test_blocks_gopher_scheme(self):
        assert _is_safe_url("gopher://evil.com/") is False

    def test_blocks_data_scheme(self):
        assert _is_safe_url("data:text/html,<script>alert(1)</script>") is False

    # -- Blocked private IPs --

    def test_blocks_localhost_127(self):
        assert _is_safe_url("http://127.0.0.1/image.png") is False

    def test_blocks_localhost_name(self):
        assert _is_safe_url("http://localhost/image.png") is False

    def test_blocks_10_network(self):
        assert _is_safe_url("http://10.0.0.1/admin") is False

    def test_blocks_172_16_network(self):
        assert _is_safe_url("http://172.16.0.1/") is False

    def test_blocks_172_31_network(self):
        assert _is_safe_url("http://172.31.255.255/") is False

    def test_allows_172_15_network(self):
        """172.15.x.x is NOT private — should be allowed."""
        assert _is_safe_url("http://172.15.0.1/image.png") is True

    def test_allows_172_32_network(self):
        """172.32.x.x is NOT private — should be allowed."""
        assert _is_safe_url("http://172.32.0.1/image.png") is True

    def test_blocks_192_168_network(self):
        assert _is_safe_url("http://192.168.1.1/") is False

    def test_blocks_metadata_service(self):
        assert _is_safe_url("http://169.254.169.254/latest/meta-data") is False

    def test_blocks_zero_ip(self):
        assert _is_safe_url("http://0.0.0.0/") is False

    # -- Edge cases --

    def test_blocks_localhost_localdomain(self):
        assert _is_safe_url("http://localhost.localdomain/") is False

    def test_blocks_ipv6_loopback(self):
        assert _is_safe_url("http://[::1]/image.png") is False


class TestProcessUrlSsrfProtection:
    """Test that _process_url rejects unsafe URLs."""

    def test_process_url_rejects_file_scheme(self):
        result = _process_url("file:///etc/passwd", "auto")
        assert not result.is_valid
        assert any("not allowed" in e.lower() or "scheme" in e.lower() for e in result.errors)

    def test_process_url_rejects_private_ip(self):
        result = _process_url("http://169.254.169.254/latest/meta-data", "auto")
        assert not result.is_valid
        assert any("blocked" in e.lower() or "not allowed" in e.lower() for e in result.errors)

    def test_process_url_rejects_localhost(self):
        result = _process_url("http://localhost:6379/", "auto")
        assert not result.is_valid

    @patch('utils.image_utils._get_http_session')
    def test_process_url_does_not_fetch_blocked_url(self, mock_session):
        """Blocked URLs must NOT trigger any HTTP request."""
        result = _process_url("http://127.0.0.1/secret", "auto")
        assert not result.is_valid
        mock_session.assert_not_called()  # NO HTTP request made
