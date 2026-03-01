#!/usr/bin/env python3
"""Tests for C-1: Thread safety of _models_cache in LMSRestClient.

The _models_cache dict is read/written by multiple LMSRestClient methods
(list_all_models, get_model, invalidate_cache) without synchronization.
A threading.Lock must protect all cache access.
"""
import threading
from unittest.mock import MagicMock

import pytest

from utils.lms_helper import LMSRestClient


class TestCacheLockExists:
    """LMSRestClient must have a _cache_lock attribute."""

    def test_client_has_cache_lock(self):
        """LMSRestClient.__init__ must create a threading.Lock for cache."""
        client = LMSRestClient(base_url="http://localhost:1234")
        assert hasattr(client, "_cache_lock"), "Must have _cache_lock attribute"
        assert isinstance(
            client._cache_lock, type(threading.Lock())
        ), "_cache_lock must be a threading.Lock"


class TestConcurrentCacheAccess:
    """Concurrent cache operations must not corrupt state."""

    def _make_client(self):
        """Create LMSRestClient with mocked HTTP client."""
        client = LMSRestClient(base_url="http://localhost:1234")
        mock_http = MagicMock()
        client._client = mock_http
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"key": "test/model", "loaded_instances": []}
        ]
        mock_http.get.return_value = mock_response
        return client

    def test_concurrent_list_and_invalidate(self):
        """Concurrent list_all_models + invalidate_cache must not corrupt cache."""
        client = self._make_client()
        errors = []

        def list_worker():
            try:
                for _ in range(100):
                    result = client.list_all_models()
                    if result is not None:
                        assert isinstance(result, list)
            except Exception as e:
                errors.append(e)

        def invalidate_worker():
            try:
                for _ in range(100):
                    client.invalidate_cache()
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=list_worker),
            threading.Thread(target=list_worker),
            threading.Thread(target=invalidate_worker),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Thread safety violation: {errors}"

    def test_concurrent_get_model_safe(self):
        """Concurrent get_model calls must not raise."""
        client = self._make_client()
        # Pre-populate cache
        client.list_all_models()
        errors = []

        def worker():
            try:
                for _ in range(100):
                    client.get_model("test/model")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Thread safety violation: {errors}"
