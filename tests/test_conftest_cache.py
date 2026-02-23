"""Integration test: ModelValidator cache survives between tests.

With the autouse cache reset removed, the class-level cache should
persist across test functions. This test verifies that behavior.
"""
import time
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from llm.model_validator import ModelValidator


# Two sequential tests — the second must see the first's cached result.

@pytest.mark.asyncio
async def test_cache_populate():
    """First test: populate cache via mocked _fetch_models."""
    # Ensure clean state for this test pair
    ModelValidator._class_cache = None
    ModelValidator._class_cache_time = 0.0

    validator = ModelValidator(api_base="http://localhost:1234")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"models": [{"key": "test-cached-model"}]}
    mock_response.raise_for_status = MagicMock()

    mock_native_response = MagicMock()
    mock_native_response.status_code = 200
    mock_native_response.json.return_value = {"models": [{"key": "test-cached-model"}]}
    mock_native_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_native_response

    with patch("httpx.AsyncClient") as mock_async_client:
        mock_async_client.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_async_client.return_value.__aexit__ = AsyncMock(return_value=False)
        models = await validator._fetch_models(force_refresh=True)

    assert "test-cached-model" in models
    assert ModelValidator._class_cache is not None


@pytest.mark.asyncio
async def test_cache_survives():
    """Second test: cache from first test should still be warm."""
    # Do NOT reset cache — that's the whole point
    assert ModelValidator._class_cache is not None, (
        "Cache was reset between tests — autouse fixture may still be active!"
    )
    assert "test-cached-model" in ModelValidator._class_cache

    # Clean up after ourselves
    ModelValidator._class_cache = None
    ModelValidator._class_cache_time = 0.0
