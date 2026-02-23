"""Model validation for LM Studio.

This module provides validation of model names against LM Studio's available models.
It includes caching to minimize API calls and clear error messages when models
are not found.

Uses a single class-level cache (MODELS_FETCH_CACHE_TTL seconds) shared across
all ModelValidator instances to avoid repeated /v1/models polling.
"""

import time
from typing import Optional
import logging

import httpx

from llm.exceptions import ModelNotFoundError, LLMConnectionError
from utils.error_handling import retry_with_backoff
from config import get_config
from config.constants import MODELS_FETCH_CACHE_TTL

logger = logging.getLogger(__name__)


class ModelValidator:
    """Validates model availability against LM Studio API.

    This class fetches the list of available models from LM Studio and
    validates requested model names against that list. Uses a single
    class-level cache (MODELS_FETCH_CACHE_TTL seconds, monotonic clock)
    shared across all instances.

    Attributes:
        api_base: Base URL for LM Studio API (e.g., "http://localhost:1234")
    """

    # Class-level cache shared across all instances.
    # Prevents repeated /v1/models polling when new ModelValidator instances
    # are created per-request.
    # Uses time.monotonic() — immune to NTP jumps.
    _class_cache: Optional[list[str]] = None
    _class_cache_time: float = 0.0

    def __init__(self, api_base: Optional[str] = None):
        """Initialize model validator.

        Args:
            api_base: Base URL for LM Studio API. If None, uses config value.
        """
        config = get_config()
        self.api_base = api_base or config.lmstudio.api_base

        logger.debug(f"ModelValidator initialized with api_base: {self.api_base}")

    @retry_with_backoff(max_retries=3, base_delay=1.0, exceptions=(httpx.HTTPError,))
    async def _fetch_models(self, force_refresh: bool = False) -> list[str]:
        """Fetch available models from LM Studio API.

        Uses a class-level TTL cache (MODELS_FETCH_CACHE_TTL seconds) so
        repeated calls across multiple ModelValidator instances reuse the
        model list without hitting /v1/models each time.

        Args:
            force_refresh: If True, bypass class cache and hit the network.
                Used when get_available_models(use_cache=False) is called.

        Returns:
            List of available model IDs

        Raises:
            LLMConnectionError: If unable to connect to LM Studio API
        """
        # Check class-level cache first (shared across all instances)
        now = time.monotonic()
        if (
            not force_refresh
            and ModelValidator._class_cache is not None
            and (now - ModelValidator._class_cache_time) < MODELS_FETCH_CACHE_TTL
        ):
            logger.debug(
                f"Using class-level model cache "
                f"(age: {now - ModelValidator._class_cache_time:.1f}s)"
            )
            return ModelValidator._class_cache

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Try native /api/v1/models first (richer data)
                try:
                    native_base = self.api_base.rstrip("/")
                    if native_base.endswith("/v1"):
                        native_base = native_base[:-3]
                    native_response = await client.get(f"{native_base}/api/v1/models")
                    native_response.raise_for_status()
                    native_data = native_response.json()
                    if isinstance(native_data, list) and native_data:
                        models = [m["key"] for m in native_data if "key" in m]
                        if models:
                            logger.info(f"Fetched {len(models)} models via native API")
                            ModelValidator._class_cache = models
                            ModelValidator._class_cache_time = now
                            return models
                except Exception:
                    logger.debug("Native API unavailable, falling back to /v1/models")

                # Fallback: existing /v1/models logic
                logger.debug(f"Fetching models from {self.api_base}/models")
                response = await client.get(f"{self.api_base}/models")
                response.raise_for_status()
                data = response.json()

                # Extract model IDs from response
                # Response format: {"data": [{"id": "model-name", ...}, ...]}
                models = [model["id"] for model in data.get("data", [])]

                logger.info(f"Fetched {len(models)} models from LM Studio")
                if models:
                    logger.debug(f"Available models: {', '.join(models)}")

                ModelValidator._class_cache = models
                ModelValidator._class_cache_time = now
                return models

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch models from LM Studio: {e}")
            raise LLMConnectionError(
                f"Could not connect to LM Studio API at {self.api_base}. "
                f"Please ensure LM Studio is running and the server is started.",
                original_exception=e
            )

    async def get_available_models(self, use_cache: bool = True) -> list[str]:
        """Get list of available models.

        Delegates to _fetch_models() which manages the class-level cache.
        When use_cache=False, forces a fresh network fetch bypassing ALL
        cache layers (both class-level TTL cache and any warm data).

        Args:
            use_cache: Whether to use cached model list (default: True).
                False forces a fresh fetch from LM Studio API.

        Returns:
            List of available model IDs

        Example:
            >>> validator = ModelValidator()
            >>> models = await validator.get_available_models()
            >>> print(models)
            ['qwen/qwen3-coder-30b', 'mistralai/magistral-small-2509']
        """
        return await self._fetch_models(force_refresh=not use_cache)

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
        """Clear the class-level model cache.

        This forces the next get_available_models() call to fetch fresh data
        from the API. Useful for testing or when you know models have changed.

        Example:
            >>> validator = ModelValidator()
            >>> validator.clear_cache()  # Force refresh on next call
        """
        ModelValidator._class_cache = None
        ModelValidator._class_cache_time = 0.0
        logger.debug("Model cache cleared")


__all__ = [
    "ModelValidator",
]
