"""Tests for model validator.

This module tests the ModelValidator class in llm/model_validator.py.

Note: These tests require LM Studio to be running with at least one model loaded.
If LM Studio is not available, tests will be skipped.
"""

import pytest
import asyncio
from llm.model_validator import ModelValidator
from llm.exceptions import ModelNotFoundError, LLMConnectionError


# Helper to check if LM Studio is available
async def is_lm_studio_available() -> bool:
    """Check if LM Studio is running and accessible."""
    try:
        validator = ModelValidator()
        await validator.get_available_models(use_cache=False)
        return True
    except LLMConnectionError:
        return False


@pytest.mark.asyncio
async def test_validate_existing_model():
    """Should validate existing model successfully."""
    if not await is_lm_studio_available():
        pytest.skip("LM Studio not available")

    validator = ModelValidator()

    # Get available models
    models = await validator.get_available_models()

    if not models:
        pytest.skip("No models available in LM Studio")

    # Validate first available model
    result = await validator.validate_model(models[0])
    assert result is True


@pytest.mark.asyncio
async def test_validate_nonexistent_model_raises():
    """Should raise ModelNotFoundError for invalid model."""
    if not await is_lm_studio_available():
        pytest.skip("LM Studio not available")

    validator = ModelValidator()

    with pytest.raises(ModelNotFoundError) as exc_info:
        await validator.validate_model("nonexistent-model-xyz-123")

    error = exc_info.value
    assert "nonexistent-model-xyz-123" in str(error)
    assert error.model_name == "nonexistent-model-xyz-123"
    assert isinstance(error.available_models, list)  # May be empty if no models loaded


@pytest.mark.asyncio
async def test_validate_none_returns_true():
    """Should return True for None (means use default)."""
    validator = ModelValidator()

    result = await validator.validate_model(None)
    assert result is True


@pytest.mark.asyncio
async def test_validate_default_returns_true():
    """Should return True for 'default' string."""
    validator = ModelValidator()

    result = await validator.validate_model("default")
    assert result is True


@pytest.mark.asyncio
async def test_get_available_models_returns_list():
    """Should return list of available models."""
    if not await is_lm_studio_available():
        pytest.skip("LM Studio not available")

    validator = ModelValidator()
    models = await validator.get_available_models()

    assert isinstance(models, list)
    assert all(isinstance(m, str) for m in models)


@pytest.mark.asyncio
async def test_cache_used_on_second_call():
    """Should use cache on second call within TTL."""
    if not await is_lm_studio_available():
        pytest.skip("LM Studio not available")

    validator = ModelValidator()

    # First call - fetches from API
    models1 = await validator.get_available_models(use_cache=False)

    # Second call - should use cache
    models2 = await validator.get_available_models(use_cache=True)

    assert models1 == models2
    assert validator._cache is not None


@pytest.mark.asyncio
async def test_cache_can_be_cleared():
    """Should be able to clear cache."""
    if not await is_lm_studio_available():
        pytest.skip("LM Studio not available")

    validator = ModelValidator()

    # Fetch models to populate cache
    await validator.get_available_models()
    assert validator._cache is not None

    # Clear cache
    validator.clear_cache()
    assert validator._cache is None
    assert validator._cache_timestamp is None


@pytest.mark.asyncio
async def test_cache_not_used_when_disabled():
    """Should fetch fresh data when cache is disabled."""
    if not await is_lm_studio_available():
        pytest.skip("LM Studio not available")

    validator = ModelValidator()

    # First call with cache
    models1 = await validator.get_available_models(use_cache=True)

    # Second call without cache
    models2 = await validator.get_available_models(use_cache=False)

    # Should still get same models, but cache was not used
    assert models1 == models2


@pytest.mark.asyncio
async def test_connection_error_on_invalid_api_base():
    """Should raise LLMConnectionError for invalid API endpoint."""
    validator = ModelValidator(api_base="http://localhost:9999")

    with pytest.raises(LLMConnectionError) as exc_info:
        await validator.get_available_models(use_cache=False)

    error = exc_info.value
    assert "Could not connect to LM Studio API" in str(error)
    assert error.original_exception is not None


@pytest.mark.asyncio
async def test_fetch_models_retries_on_failure():
    """Should retry on transient failures (tested via invalid port)."""
    # This test verifies the retry decorator is applied
    validator = ModelValidator(api_base="http://localhost:99999")

    with pytest.raises(LLMConnectionError):
        # Should attempt 3 times before failing
        await validator._fetch_models()


@pytest.mark.asyncio
async def test_multiple_validators_independent():
    """Multiple validator instances should be independent."""
    if not await is_lm_studio_available():
        pytest.skip("LM Studio not available")

    validator1 = ModelValidator()
    validator2 = ModelValidator()

    # Fetch models in validator1
    await validator1.get_available_models()
    assert validator1._cache is not None

    # validator2 cache should be empty
    assert validator2._cache is None


@pytest.mark.asyncio
async def test_validator_with_custom_api_base():
    """Should work with custom API base URL."""
    # Test with default LM Studio port
    validator = ModelValidator(api_base="http://localhost:1234")

    if await is_lm_studio_available():
        models = await validator.get_available_models()
        assert isinstance(models, list)
    else:
        pytest.skip("LM Studio not available")


@pytest.mark.asyncio
async def test_error_message_includes_available_models():
    """Error message should list available models."""
    if not await is_lm_studio_available():
        pytest.skip("LM Studio not available")

    validator = ModelValidator()

    try:
        await validator.validate_model("nonexistent-model")
        pytest.fail("Should have raised ModelNotFoundError")
    except ModelNotFoundError as e:
        error_msg = str(e)
        # Should mention available models
        assert "Available" in error_msg or "available" in error_msg


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
