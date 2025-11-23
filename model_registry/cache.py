#!/usr/bin/env python3
"""
Model Registry Cache Manager.

This module handles persistence of model capability data with
dynamic cache path configuration.

Cache Design:
- Models don't change - only new models/versions appear
- Cache is valid until new models are detected
- Removed models are cleaned from cache on refresh
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from .schemas import ModelMetadata, RegistryStats, ResearchStatus

logger = logging.getLogger(__name__)

# Default cache filename
DEFAULT_CACHE_FILENAME = "model_registry.json"

# Environment variable for custom cache path
ENV_CACHE_PATH = "MODEL_REGISTRY_CACHE"


class CacheManager:
    """
    Manages persistence of model registry data.

    Cache path resolution order:
    1. Explicit path argument to __init__
    2. MODEL_REGISTRY_CACHE environment variable
    3. Project cache: .cache/model_registry.json
    4. User cache: ~/.lmstudio-bridge/model_registry.json
    """

    def __init__(self, cache_path: Optional[str] = None):
        """
        Initialize cache manager.

        Args:
            cache_path: Optional explicit path to cache file
        """
        self.cache_path = Path(self._resolve_cache_path(cache_path))
        self._ensure_cache_dir()
        logger.debug(f"Cache path: {self.cache_path}")

    def _resolve_cache_path(self, explicit_path: Optional[str]) -> str:
        """
        Resolve cache path from various sources.

        Priority:
        1. Explicit path argument
        2. Environment variable
        3. Project cache (.cache/)
        4. User cache (~/.lmstudio-bridge/)
        """
        # 1. Explicit path
        if explicit_path:
            logger.debug(f"Using explicit cache path: {explicit_path}")
            return explicit_path

        # 2. Environment variable
        env_path = os.environ.get(ENV_CACHE_PATH)
        if env_path:
            logger.debug(f"Using cache path from {ENV_CACHE_PATH}: {env_path}")
            return env_path

        # 3. Project cache (relative to cwd)
        project_cache = Path.cwd() / ".cache" / DEFAULT_CACHE_FILENAME
        if project_cache.parent.exists():
            logger.debug(f"Using project cache: {project_cache}")
            return str(project_cache)

        # 4. User cache (in home directory)
        user_cache = Path.home() / ".lmstudio-bridge" / DEFAULT_CACHE_FILENAME
        logger.debug(f"Using user cache: {user_cache}")
        return str(user_cache)

    def _ensure_cache_dir(self) -> None:
        """Ensure cache directory exists."""
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> Dict[str, ModelMetadata]:
        """
        Load cached model data.

        Returns:
            Dictionary mapping model_id to ModelMetadata
        """
        if not self.cache_path.exists():
            logger.info("No cache file found, starting fresh")
            return {}

        try:
            with open(self.cache_path, "r") as f:
                data = json.load(f)

            # Parse metadata objects
            models = {}
            for model_id, model_data in data.get("models", {}).items():
                try:
                    models[model_id] = ModelMetadata.from_dict(model_data)
                except Exception as e:
                    logger.warning(f"Failed to parse cached model '{model_id}': {e}")

            logger.info(f"Loaded {len(models)} models from cache")
            return models

        except json.JSONDecodeError as e:
            logger.error(f"Cache file corrupted, starting fresh: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error loading cache: {e}")
            return {}

    def save(self, models: Dict[str, ModelMetadata]) -> None:
        """
        Save model data to cache.

        Args:
            models: Dictionary mapping model_id to ModelMetadata
        """
        try:
            data = {
                "version": "1.0",
                "updated_at": datetime.now().isoformat(),
                "models": {
                    model_id: metadata.to_dict()
                    for model_id, metadata in models.items()
                }
            }

            # Write atomically using temp file
            temp_path = self.cache_path.with_suffix(".tmp")
            with open(temp_path, "w") as f:
                json.dump(data, f, indent=2)

            # Rename to final path
            temp_path.rename(self.cache_path)

            logger.info(f"Saved {len(models)} models to cache")

        except Exception as e:
            logger.error(f"Error saving cache: {e}")
            raise

    def get_model(self, model_id: str) -> Optional[ModelMetadata]:
        """
        Get a specific model from cache.

        Args:
            model_id: Model identifier

        Returns:
            ModelMetadata if found, None otherwise
        """
        models = self.load()
        return models.get(model_id)

    def update_model(self, metadata: ModelMetadata) -> None:
        """
        Update a single model in cache.

        Args:
            metadata: Updated model metadata
        """
        models = self.load()
        models[metadata.model_id] = metadata
        self.save(models)

    def remove_model(self, model_id: str) -> bool:
        """
        Remove a model from cache.

        Args:
            model_id: Model identifier to remove

        Returns:
            True if model was removed, False if not found
        """
        models = self.load()
        if model_id in models:
            del models[model_id]
            self.save(models)
            logger.info(f"Removed model '{model_id}' from cache")
            return True
        return False

    def remove_models(self, model_ids: List[str]) -> int:
        """
        Remove multiple models from cache.

        Args:
            model_ids: List of model identifiers to remove

        Returns:
            Number of models removed
        """
        models = self.load()
        removed = 0

        for model_id in model_ids:
            if model_id in models:
                del models[model_id]
                removed += 1
                logger.info(f"Removed model '{model_id}' from cache")

        if removed > 0:
            self.save(models)

        return removed

    def get_cached_model_ids(self) -> List[str]:
        """
        Get list of cached model IDs.

        Returns:
            List of model identifiers in cache
        """
        models = self.load()
        return list(models.keys())

    def get_models_by_research_status(
        self,
        status: ResearchStatus
    ) -> List[ModelMetadata]:
        """
        Get models filtered by research status.

        Args:
            status: Research status to filter by

        Returns:
            List of ModelMetadata matching the status
        """
        models = self.load()
        return [m for m in models.values() if m.research_status == status]

    def get_stats(self) -> RegistryStats:
        """
        Get statistics about cached models.

        Returns:
            RegistryStats with counts and status
        """
        models = self.load()

        stats = RegistryStats(
            total_models=len(models),
            llm_models=sum(1 for m in models.values() if m.model_type.value == "llm"),
            embedding_models=sum(1 for m in models.values() if m.model_type.value == "embedding"),
            researched_models=sum(
                1 for m in models.values()
                if m.research_status == ResearchStatus.COMPLETED
            ),
            pending_research=sum(
                1 for m in models.values()
                if m.research_status == ResearchStatus.NOT_RESEARCHED
            ),
            failed_research=sum(
                1 for m in models.values()
                if m.research_status == ResearchStatus.FAILED
            ),
        )

        # Get last updated time from cache file
        if self.cache_path.exists():
            try:
                with open(self.cache_path, "r") as f:
                    data = json.load(f)
                if data.get("updated_at"):
                    stats.last_updated = datetime.fromisoformat(data["updated_at"])
            except Exception:
                pass

        return stats

    def clear(self) -> None:
        """Clear all cached data."""
        if self.cache_path.exists():
            self.cache_path.unlink()
            logger.info("Cache cleared")

    def sync_with_available(
        self,
        available_ids: List[str],
        new_metadata: Optional[Dict[str, ModelMetadata]] = None
    ) -> Dict[str, Any]:
        """
        Synchronize cache with currently available models.

        This method:
        1. Adds new models to cache
        2. Removes models no longer available
        3. Preserves research data for unchanged models

        Args:
            available_ids: List of currently available model IDs
            new_metadata: Optional metadata for new models

        Returns:
            Dictionary with sync results:
            {
                "added": [...],
                "removed": [...],
                "unchanged": [...]
            }
        """
        cached = self.load()
        cached_ids = set(cached.keys())
        available_set = set(available_ids)

        # Calculate delta
        new_ids = available_set - cached_ids
        removed_ids = cached_ids - available_set
        unchanged_ids = cached_ids & available_set

        # Add new models
        for model_id in new_ids:
            if new_metadata and model_id in new_metadata:
                cached[model_id] = new_metadata[model_id]
                logger.info(f"Added new model to cache: {model_id}")

        # Remove unavailable models
        for model_id in removed_ids:
            del cached[model_id]
            logger.info(f"Removed unavailable model from cache: {model_id}")

        # Save if changed
        if new_ids or removed_ids:
            self.save(cached)

        return {
            "added": list(new_ids),
            "removed": list(removed_ids),
            "unchanged": list(unchanged_ids)
        }

    def export_to_dict(self) -> Dict[str, Any]:
        """
        Export entire cache as dictionary.

        Returns:
            Complete cache data as dictionary
        """
        if not self.cache_path.exists():
            return {"version": "1.0", "models": {}}

        with open(self.cache_path, "r") as f:
            return json.load(f)

    def import_from_dict(self, data: Dict[str, Any]) -> int:
        """
        Import cache data from dictionary.

        Args:
            data: Cache data dictionary

        Returns:
            Number of models imported
        """
        models = {}
        for model_id, model_data in data.get("models", {}).items():
            try:
                models[model_id] = ModelMetadata.from_dict(model_data)
            except Exception as e:
                logger.warning(f"Failed to import model '{model_id}': {e}")

        self.save(models)
        return len(models)
