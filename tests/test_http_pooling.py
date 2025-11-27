#!/usr/bin/env python3
"""
Tests for HTTP connection pooling.

Verifies that LLMClient and image_utils use connection pooling
for better performance and resource management.
"""

import pytest
from unittest.mock import Mock, patch
import requests
from requests.adapters import HTTPAdapter

from llm.llm_client import LLMClient
from utils.image_utils import _get_http_session


class TestLLMClientPooling:
    """Test HTTP connection pooling in LLMClient."""

    def test_session_created_on_init(self):
        """Verify that LLMClient creates a session on initialization."""
        client = LLMClient()

        assert hasattr(client, 'session'), "LLMClient should have a 'session' attribute"
        assert isinstance(client.session, requests.Session), "session should be a requests.Session instance"

    def test_session_has_adapter(self):
        """Verify that the session has HTTP adapters configured."""
        client = LLMClient()

        # Check that adapters are mounted for http and https
        assert 'http://' in client.session.adapters, "HTTP adapter should be mounted"
        assert 'https://' in client.session.adapters, "HTTPS adapter should be mounted"

        # Verify adapter type
        http_adapter = client.session.adapters['http://']
        assert isinstance(http_adapter, HTTPAdapter), "Adapter should be HTTPAdapter instance"

    def test_session_pool_configuration(self):
        """Verify that connection pool is configured correctly."""
        client = LLMClient()

        http_adapter = client.session.adapters['http://']

        # Check pool configuration
        assert hasattr(http_adapter, '_pool_connections'), "Adapter should have pool_connections"
        assert hasattr(http_adapter, '_pool_maxsize'), "Adapter should have pool_maxsize"

        # Verify reasonable pool sizes (should be > 1 for pooling)
        assert http_adapter._pool_connections > 1, "Pool connections should be > 1"
        assert http_adapter._pool_maxsize > 1, "Pool max size should be > 1"

    @patch('llm.llm_client.requests.Session.post')
    def test_uses_session_for_chat_completion(self, mock_post):
        """Verify chat_completion uses session instead of direct requests."""
        # Setup mock
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"role": "assistant", "content": "test"}}]
        }
        mock_post.return_value = mock_response

        client = LLMClient()

        # Make a call
        messages = [{"role": "user", "content": "test"}]
        client.chat_completion(messages=messages)

        # Verify session.post was called (not requests.post directly)
        assert mock_post.called, "Session.post should be called"
        assert mock_post.call_count == 1, "Should make exactly 1 request"

    @patch('llm.llm_client.requests.Session.get')
    def test_uses_session_for_list_models(self, mock_get):
        """Verify list_models uses session instead of direct requests."""
        # Setup mock
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"id": "model1"}, {"id": "model2"}]
        }
        mock_get.return_value = mock_response

        client = LLMClient()

        # Make a call
        models = client.list_models()

        # Verify session.get was called
        assert mock_get.called, "Session.get should be called"
        assert len(models) == 2, "Should return 2 models"


class TestImageUtilsPooling:
    """Test HTTP connection pooling in image_utils."""

    def test_http_session_created(self):
        """Verify that image_utils creates an HTTP session."""
        session = _get_http_session()

        assert isinstance(session, requests.Session), "Should return a requests.Session"

    def test_http_session_is_cached(self):
        """Verify that the same session is reused across calls."""
        session1 = _get_http_session()
        session2 = _get_http_session()

        assert session1 is session2, "Should return the same session instance"

    def test_http_session_has_adapters(self):
        """Verify that the session has HTTP adapters configured."""
        session = _get_http_session()

        assert 'http://' in session.adapters, "HTTP adapter should be mounted"
        assert 'https://' in session.adapters, "HTTPS adapter should be mounted"

        # Verify adapter type
        http_adapter = session.adapters['http://']
        assert isinstance(http_adapter, HTTPAdapter), "Adapter should be HTTPAdapter instance"

    def test_http_session_pool_configuration(self):
        """Verify that connection pool is configured correctly."""
        session = _get_http_session()

        http_adapter = session.adapters['http://']

        # Check pool configuration
        assert hasattr(http_adapter, '_pool_connections'), "Adapter should have pool_connections"
        assert hasattr(http_adapter, '_pool_maxsize'), "Adapter should have pool_maxsize"

        # Verify reasonable pool sizes
        assert http_adapter._pool_connections > 0, "Pool connections should be > 0"
        assert http_adapter._pool_maxsize > 0, "Pool max size should be > 0"


class TestPoolingBenefits:
    """Test the benefits of connection pooling."""

    def test_multiple_clients_have_separate_sessions(self):
        """Verify that different LLMClient instances have separate sessions."""
        client1 = LLMClient()
        client2 = LLMClient()

        # Each client should have its own session
        assert client1.session is not client2.session, "Each client should have its own session"

    def test_session_persists_across_calls(self):
        """Verify that the same session is used across multiple API calls."""
        client = LLMClient()

        # Get session reference
        original_session = client.session

        # Make multiple (mocked) calls
        with patch.object(client.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": []}
            mock_get.return_value = mock_response

            client.list_models()
            client.list_models()

            # Verify same session used
            assert client.session is original_session, "Session should persist"
            assert mock_get.call_count == 2, "Should reuse session for multiple calls"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
