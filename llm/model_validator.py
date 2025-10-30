"""Model validation for LM Studio.

This module provides validation of model names against LM Studio's available models.
It includes caching to minimize API calls and clear error messages when models
are not found.

The validator uses a 60-second cache TTL to balance freshness with performance.
"""

import asyncio
from typing import List, Optional
from datetime import datetime, timedelta, UTC
import logging
import httpx

from llm.exceptions import ModelNotFoundError, LLMConnectionError
from utils.error_handling import retry_with_backoff
from config import get_config

logger = logging.getLogger(__name__)


class ModelValidator:
    """Validates model availability against LM Studio API.

    This class fetches the list of available models from LM Studio and
    validates requested model names against that list. It uses caching
    to minimize API calls.

    Attributes:
        api_base: Base URL for LM Studio API (e.g., "http://localhost:1234")
        _cache: Cached list of available model IDs
        _cache_timestamp: When the cache was last updated
        _cache_ttl: How long cache is valid (60 seconds)
    """

    def __init__(self, api_base: Optional[str] = None):
        """Initialize model validator.

        Args:
            api_base: Base URL for LM Studio API. If None, uses config value.
        """
        config = get_config()
        self.api_base = api_base or config.lmstudio.api_base

        # Cache to minimize API calls
        self._cache: Optional[List[str]] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl = timedelta(seconds=60)  # 60-second cache

        logger.debug(f"ModelValidator initialized with api_base: {self.api_base}")

    @retry_with_backoff(max_retries=3, base_delay=1.0, exceptions=(httpx.HTTPError,))
    async def _fetch_models(self) -> List[str]:
        """Fetch available models from LM Studio API.

        This method makes an HTTP request to LM Studio's /v1/models endpoint
        to get the list of currently available models. It uses retry logic
        to handle transient failures.

        Returns:
            List of available model IDs

        Raises:
            LLMConnectionError: If unable to connect to LM Studio API

        Example:
            ["qwen/qwen3-coder-30b", "mistralai/magistral-small-2509"]
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                logger.debug(f"Fetching models from {self.api_base}/v1/models")
                response = await client.get(f"{self.api_base}/v1/models")
                response.raise_for_status()
                data = response.json()

                # Extract model IDs from response
                # Response format: {"data": [{"id": "model-name", ...}, ...]}
                models = [model["id"] for model in data.get("data", [])]

                logger.info(f"Fetched {len(models)} models from LM Studio")
                if models:
                    logger.debug(f"Available models: {', '.join(models)}")

                return models

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch models from LM Studio: {e}")
            raise LLMConnectionError(
                f"Could not connect to LM Studio API at {self.api_base}. "
                f"Please ensure LM Studio is running and the server is started.",
                original_exception=e
            )

    async def get_available_models(self, use_cache: bool = True) -> List[str]:
        """Get list of available models.

        This method returns the list of available models, using the cache
        if it's still valid.

        Args:
            use_cache: Whether to use cached model list (default: True)

        Returns:
            List of available model IDs

        Example:
            >>> validator = ModelValidator()
            >>> models = await validator.get_available_models()
            >>> print(models)
            ['qwen/qwen3-coder-30b', 'mistralai/magistral-small-2509']
        """
        now = datetime.now(UTC)

        # Check if cache is valid
        if use_cache and self._cache is not None and self._cache_timestamp is not None:
            cache_age = now - self._cache_timestamp
            if cache_age < self._cache_ttl:
                logger.debug(
                    f"Using cached model list (age: {cache_age.total_seconds():.1f}s)"
                )
                return self._cache

        # Fetch fresh model list
        logger.debug("Cache miss or expired, fetching fresh model list")
        models = await self._fetch_models()

        # Update cache
        self._cache = models
        self._cache_timestamp = now

        return models

    async def validate_model(self, model_name: Optional[str]) -> bool:
        """Validate if model exists in LM Studio.

        This method checks if the specified model is available. Special handling
        for None and "default" which always return True (means use default model).

        Args:
            model_name: Model ID to validate (None means use default)

        Returns:
            True if model exists or is None/default

        Raises:
            ModelNotFoundError: If model not found in available models

        Example:
            >>> validator = ModelValidator()
            >>> await validator.validate_model("qwen/qwen3-coder-30b")
            True
            >>> await validator.validate_model("nonexistent-model")
            ModelNotFoundError: Model 'nonexistent-model' not found. Available: ...
        """
        # None or "default" means use default model (always valid)
        if model_name is None or model_name == "default":
            logger.debug("Model name is None or 'default', using default model")
            return True

        # Get available models
        available_models = await self.get_available_models()

        # Check if model exists
        if model_name not in available_models:
            logger.error(
                f"Model '{model_name}' not found. "
                f"Available models: {', '.join(available_models)}"
            )
            raise ModelNotFoundError(model_name, available_models)

        logger.info(f"Model '{model_name}' validated successfully")
        return True

    def clear_cache(self):
        """Clear the model cache.

        This forces the next get_available_models() call to fetch fresh data
        from the API. Useful for testing or when you know models have changed.

        Example:
            >>> validator = ModelValidator()
            >>> validator.clear_cache()  # Force refresh on next call
        """
        self._cache = None
        self._cache_timestamp = None
        logger.debug("Model cache cleared")


__all__ = [
    "ModelValidator",
]
