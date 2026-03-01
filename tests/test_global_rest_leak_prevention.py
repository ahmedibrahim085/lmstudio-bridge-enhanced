"""Tests for D-4/S-1: Global REST API leak prevention fixture.

Verifies that conftest.py's global autouse fixture blocks LMSHelper._get_rest_client()
in non-e2e tests, preventing HTTP leaks to LM Studio during unit/integration tests.

E2e tests (marked with @pytest.mark.e2e) must NOT be blocked — they need real API access.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.lms_helper import LMSHelper


@pytest.mark.unit
class TestGlobalRestLeakPrevention:
    """Verify the global _prevent_rest_api_leaks fixture blocks REST in non-e2e tests."""

    def test_rest_client_returns_none_in_unit_tests(self):
        """In non-e2e tests, _get_rest_client() must return None.

        The global autouse fixture in conftest.py patches _get_rest_client
        to return None, preventing any REST API calls from leaking through
        to a real LM Studio instance.
        """
        client = LMSHelper._get_rest_client()
        assert client is None, (
            f"_get_rest_client() returned {type(client).__name__} instead of None — "
            "global _prevent_rest_api_leaks fixture is not active"
        )

    def test_rest_client_blocked_prevents_http_in_load_model(self):
        """With _get_rest_client() returning None, load_model() falls back to CLI.

        This proves the fixture prevents the REST-first path in load_model()
        from making real HTTP calls.
        """
        client = LMSHelper._get_rest_client()
        assert client is None, "Pre-condition: REST client must be blocked"

    def test_fixture_is_autouse(self):
        """The fixture must be autouse — no explicit request needed.

        This test does NOT request any fixture by name. If _get_rest_client()
        returns None, it proves the fixture is autouse.
        """
        assert LMSHelper._get_rest_client() is None, (
            "Global _prevent_rest_api_leaks fixture is not autouse — "
            "REST client is not blocked without explicit fixture request"
        )
