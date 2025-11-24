#!/usr/bin/env python3
"""
Model Capability Registry - Main Orchestrator.

This module provides the main interface for the Model Registry,
coordinating LMS integration, caching, and research.

Features:
- List all available models with metadata
- Get capabilities for specific models
- Refresh registry (research new models, remove unavailable)
- Smart caching with delta updates
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

# Enable nested asyncio.run() calls to prevent RuntimeError when called from
# within an already-running event loop (e.g., from FastMCP async context)
import nest_asyncio
nest_asyncio.apply()

from .schemas import (
    ModelMetadata,
    ModelCapabilities,
    RegistryStats,
    ResearchStatus,
    ModelType
)
from .lms_integration import (
    LMSIntegration,
    LMSNotInstalledError,
    LMSCommandError
)
from .cache import CacheManager
from .research import (
    ModelResearcher,
    ResearchResult,
    apply_research_to_metadata
)

logger = logging.getLogger(__name__)


class ModelRegistry:
    """
    Main interface for the Model Capability Registry.

    This class orchestrates:
    - LMS CLI queries for available/loaded models
    - Caching of model metadata and capabilities
    - Research of new model capabilities
    - Delta updates (only research new models)
    """

    def __init__(
        self,
        cache_path: Optional[str] = None,
        web_search_enabled: bool = True
    ):
        """
        Initialize the model registry.

        Args:
            cache_path: Optional custom path for cache file
            web_search_enabled: Whether to enable web search for research
        """
        self.cache = CacheManager(cache_path)
        self.researcher = ModelResearcher(web_search_enabled=web_search_enabled)
        self._lms_checked = False

    def _ensure_lms(self) -> None:
        """Ensure LMS CLI is available."""
        if not self._lms_checked:
            LMSIntegration.check_prerequisites()
            self._lms_checked = True

    # =========================================================================
    # Public API - List Models
    # =========================================================================

    def list_available_models(
        self,
        include_embeddings: bool = False
    ) -> Dict[str, Any]:
        """
        List all available models with their status.

        Returns dict with:
        - available: All downloaded model IDs
        - loaded: Currently loaded model IDs
        - unknown: Models not yet in registry (need research)
        - stats: Registry statistics

        Args:
            include_embeddings: Whether to include embedding models

        Returns:
            Dictionary with model lists and stats

        Raises:
            LMSNotInstalledError: If LMS CLI not installed
        """
        self._ensure_lms()

        # Get current model lists from LMS
        available_ids = LMSIntegration.get_all_model_ids(
            include_embeddings=include_embeddings
        )
        loaded_ids = LMSIntegration.get_loaded_model_ids()

        # Get cached model IDs
        cached_ids = set(self.cache.get_cached_model_ids())

        # Identify unknown models (not in cache)
        unknown_ids = [mid for mid in available_ids if mid not in cached_ids]

        # Get stats
        stats = self.cache.get_stats()

        return {
            "available": available_ids,
            "loaded": loaded_ids,
            "unknown": unknown_ids,
            "total_available": len(available_ids),
            "total_loaded": len(loaded_ids),
            "total_unknown": len(unknown_ids),
            "stats": stats.to_dict()
        }

    def get_all_models_metadata(
        self,
        include_embeddings: bool = False
    ) -> List[ModelMetadata]:
        """
        Get metadata for all available models.

        Returns cached data where available, LMS metadata otherwise.

        Args:
            include_embeddings: Whether to include embedding models

        Returns:
            List of ModelMetadata objects
        """
        self._ensure_lms()

        # Get all models from LMS
        lms_models = LMSIntegration.get_all_models_with_metadata(
            include_embeddings=include_embeddings
        )

        # Load cache
        cached = self.cache.load()

        # Merge: use cached data if available, otherwise LMS data
        result = []
        for lms_meta in lms_models:
            if lms_meta.model_id in cached:
                # Use cached data (has research results)
                result.append(cached[lms_meta.model_id])
            else:
                # Use fresh LMS data
                result.append(lms_meta)

        return result

    # =========================================================================
    # Public API - Get Model Info
    # =========================================================================

    def get_model_capabilities(
        self,
        model_id: str,
        auto_research: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Get capabilities for a specific model.

        Args:
            model_id: Model identifier
            auto_research: Automatically research if not cached

        Returns:
            Dictionary with model capabilities, or None if not found
        """
        self._ensure_lms()

        # Check cache first
        cached = self.cache.get_model(model_id)

        if cached:
            logger.debug(f"Cache hit for {model_id}")
            return self._format_capabilities_response(cached)

        # Not in cache - get from LMS
        lms_meta = LMSIntegration.get_model_metadata_from_lms(model_id)

        if not lms_meta:
            logger.warning(f"Model '{model_id}' not found in LMS")
            return None

        # Auto-research if enabled
        if auto_research:
            logger.info(f"Auto-researching capabilities for {model_id}")
            result = asyncio.run(self.researcher.research_model(lms_meta))

            if result.success:
                lms_meta = apply_research_to_metadata(lms_meta, result)

            # Cache the result
            self.cache.update_model(lms_meta)

        return self._format_capabilities_response(lms_meta)

    def _format_capabilities_response(
        self,
        metadata: ModelMetadata
    ) -> Dict[str, Any]:
        """Format model metadata as API response."""
        caps = metadata.capabilities

        return {
            "model_id": metadata.model_id,
            "display_name": metadata.display_name,
            "publisher": metadata.publisher,
            "model_family": metadata.model_family,
            "model_type": metadata.model_type.value,
            "size_billions": metadata.size_billions,
            "max_context_length": metadata.max_context_length,
            "quantization": metadata.quantization,
            "capabilities": {
                "tool_calling": self._format_capability(caps.tool_calling),
                "vision": self._format_capability(caps.vision),
                "structured_output": self._format_capability(caps.structured_output),
                "reasoning": self._format_capability(caps.reasoning),
                "coding": self._format_capability(caps.coding),
                "long_context": self._format_capability(caps.long_context),
            },
            "benchmarks": metadata.benchmarks.to_dict() if metadata.benchmarks else {},
            "recommended_for": metadata.recommended_for,
            "research_status": metadata.research_status.value,
            "researched_at": (
                metadata.researched_at.isoformat()
                if metadata.researched_at else None
            )
        }

    def _format_capability(self, cap) -> Optional[Dict[str, Any]]:
        """Format a capability score for API response."""
        if cap is None:
            return None
        return cap.to_dict()

    # =========================================================================
    # Public API - Refresh Registry
    # =========================================================================

    async def refresh_registry(
        self,
        models: Optional[List[str]] = None,
        force_all: bool = False,
        remove_unavailable: bool = True
    ) -> Dict[str, Any]:
        """
        Refresh the model registry.

        This method:
        1. Gets current model list from LMS
        2. Removes models no longer available (if remove_unavailable=True)
        3. Researches new models (delta only, unless force_all=True)
        4. Updates cache

        Args:
            models: Specific models to refresh (None = all new)
            force_all: Re-research all models, not just new ones
            remove_unavailable: Remove models no longer in LMS

        Returns:
            Dictionary with refresh results
        """
        self._ensure_lms()

        # Get current available models from LMS
        lms_models = LMSIntegration.get_all_models_with_metadata(
            include_embeddings=True
        )
        available_ids = [m.model_id for m in lms_models]

        # Load current cache
        cached = self.cache.load()
        cached_ids = set(cached.keys())

        # Calculate delta
        new_ids = set(available_ids) - cached_ids
        removed_ids = cached_ids - set(available_ids)

        results = {
            "researched": [],
            "cached": [],
            "removed": [],
            "failed": [],
            "total_available": len(available_ids)
        }

        # Remove unavailable models
        if remove_unavailable and removed_ids:
            for model_id in removed_ids:
                del cached[model_id]
                results["removed"].append(model_id)
                logger.info(f"Removed unavailable model: {model_id}")

        # Determine which models to research
        if models:
            # Specific models requested
            to_research = [m for m in lms_models if m.model_id in models]
        elif force_all:
            # Research everything
            to_research = lms_models
        else:
            # Only new models (delta)
            to_research = [m for m in lms_models if m.model_id in new_ids]

        # Research models
        if to_research:
            logger.info(f"Researching {len(to_research)} models...")
            research_results = await self.researcher.research_models_batch(
                to_research,
                concurrency=5
            )

            for metadata in to_research:
                model_id = metadata.model_id
                result = research_results.get(model_id)

                if result and result.success:
                    updated = apply_research_to_metadata(metadata, result)
                    cached[model_id] = updated
                    results["researched"].append(model_id)
                else:
                    # Still cache the LMS metadata even if research failed
                    metadata.research_status = ResearchStatus.FAILED
                    cached[model_id] = metadata
                    results["failed"].append(model_id)

        # Track unchanged cached models
        for model_id in cached_ids - removed_ids:
            if model_id not in [r for r in results["researched"]]:
                if model_id not in [f for f in results["failed"]]:
                    results["cached"].append(model_id)

        # Save updated cache
        self.cache.save(cached)

        results["total_researched"] = len(results["researched"])
        results["total_cached"] = len(results["cached"])
        results["total_removed"] = len(results["removed"])
        results["total_failed"] = len(results["failed"])

        return results

    def refresh_registry_sync(
        self,
        models: Optional[List[str]] = None,
        force_all: bool = False,
        remove_unavailable: bool = True
    ) -> Dict[str, Any]:
        """Synchronous wrapper for refresh_registry."""
        return asyncio.run(
            self.refresh_registry(
                models=models,
                force_all=force_all,
                remove_unavailable=remove_unavailable
            )
        )

    # =========================================================================
    # Public API - Query Helpers
    # =========================================================================

    def get_models_by_capability(
        self,
        capability: str,
        min_score: float = 0.0
    ) -> List[ModelMetadata]:
        """
        Get models that have a specific capability.

        Args:
            capability: Capability name (tool_calling, vision, etc.)
            min_score: Minimum score/confidence threshold

        Returns:
            List of models with the capability
        """
        models = self.cache.load()
        result = []

        for metadata in models.values():
            cap = getattr(metadata.capabilities, capability, None)
            if cap is not None:
                # Check if supported (bool or score)
                if isinstance(cap.supported, bool) and cap.supported:
                    if cap.confidence >= min_score:
                        result.append(metadata)
                elif isinstance(cap.supported, (int, float)) and cap.supported >= min_score:
                    result.append(metadata)

        # Sort by score/confidence
        def sort_key(m):
            cap = getattr(m.capabilities, capability, None)
            if cap is None:
                return 0
            if isinstance(cap.supported, (int, float)):
                return cap.supported
            return cap.confidence if cap.supported else 0

        result.sort(key=sort_key, reverse=True)
        return result

    def get_best_model_for(
        self,
        use_case: str,
        loaded_only: bool = False
    ) -> Optional[ModelMetadata]:
        """
        Get the best model for a specific use case.

        Args:
            use_case: Use case (tool_use, coding, vision, etc.)
            loaded_only: Only consider currently loaded models

        Returns:
            Best model for the use case, or None
        """
        models = self.cache.load()

        if loaded_only:
            loaded_ids = set(LMSIntegration.get_loaded_model_ids())
            models = {k: v for k, v in models.items() if k in loaded_ids}

        # Filter models that recommend this use case
        candidates = [
            m for m in models.values()
            if use_case in m.recommended_for
        ]

        if not candidates:
            return None

        # Sort by relevant capability score
        capability_map = {
            "tool_use": "tool_calling",
            "agents": "tool_calling",
            "coding": "coding",
            "code_review": "coding",
            "vision": "vision",
            "image_analysis": "vision",
            "reasoning": "reasoning",
            "analysis": "reasoning",
            "long_documents": "long_context"
        }

        cap_name = capability_map.get(use_case, "tool_calling")

        def score_model(m):
            cap = getattr(m.capabilities, cap_name, None)
            if cap is None:
                return 0
            if isinstance(cap.supported, (int, float)):
                return cap.supported * cap.confidence
            return cap.confidence if cap.supported else 0

        candidates.sort(key=score_model, reverse=True)
        return candidates[0] if candidates else None

    # =========================================================================
    # Public API - Stats and Info
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        return self.cache.get_stats().to_dict()

    def clear_cache(self) -> None:
        """Clear all cached data."""
        self.cache.clear()
        logger.info("Registry cache cleared")


# Singleton instance for convenience
_registry: Optional[ModelRegistry] = None


def get_registry(
    cache_path: Optional[str] = None,
    web_search_enabled: bool = True
) -> ModelRegistry:
    """
    Get the global model registry instance.

    Args:
        cache_path: Optional custom cache path
        web_search_enabled: Whether to enable web search

    Returns:
        ModelRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = ModelRegistry(
            cache_path=cache_path,
            web_search_enabled=web_search_enabled
        )
    return _registry


def reset_registry() -> None:
    """Reset the global registry instance."""
    global _registry
    _registry = None
