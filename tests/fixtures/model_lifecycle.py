"""
Session-Level Model Lifecycle Manager for Tests.

Manages model loading/unloading during test sessions:
- Cleans up duplicate model instances (e.g., model:2, model:3)
- Tracks what THIS session loaded so teardown only unloads our models
- Delegates all operations to LMSHelper (DOGFOODING)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from config.constants import (
    MODEL_INVENTORY_REASON_LIFECYCLE,
    TEST_MAX_LOADED_MODELS,
    TEST_MODEL_TTL,
)
from utils.lms_helper import LMSHelper

if TYPE_CHECKING:
    from tests.fixtures.model_inventory import ModelLoadInventory

logger = logging.getLogger(__name__)


class ModelLifecycleManager:
    """Manages model lifecycle for a test session.

    Tracks which models were loaded by THIS session so teardown
    only unloads what we loaded (doesn't touch user's models).
    """

    def __init__(self, inventory: ModelLoadInventory | None = None) -> None:
        self._loaded_by_us: set[str] = set()
        self._inventory = inventory

    def cleanup_duplicates(self) -> int:
        """Detect and unload duplicate model instances.

        LM Studio creates instances like model:2, model:3 when the same
        model is loaded multiple times. This method keeps only the first
        instance and unloads extras.

        Returns:
            Number of duplicate instances unloaded.
        """
        loaded = LMSHelper.list_loaded_models()
        if not loaded:
            return 0

        # Group by base model name
        instances: dict[str, list[dict]] = {}
        for model in loaded:
            identifier = model.get("identifier") or model.get("modelKey") or ""
            base_name = LMSHelper._get_base_model_name(identifier)
            if base_name:
                instances.setdefault(base_name, []).append(model)

        unloaded_count = 0
        rest_client = LMSHelper._get_rest_client()

        for base_name, model_list in instances.items():
            if len(model_list) <= 1:
                continue

            # Keep the first instance, unload the rest
            duplicates = model_list[1:]
            logger.info(
                f"Found {len(duplicates)} duplicate(s) of '{base_name}', "
                f"unloading extras"
            )

            for dup in duplicates:
                instance_id = dup.get("instance_id", "")
                identifier = dup.get("identifier") or dup.get("modelKey") or ""

                if instance_id and rest_client is not None:
                    try:
                        rest_client.unload_model(instance_id)
                        unloaded_count += 1
                        logger.debug(f"Unloaded duplicate: {identifier} ({instance_id})")
                    except Exception as e:
                        logger.warning(f"Failed to unload duplicate {identifier}: {e}")
                else:
                    # Fallback: unload by name via CLI
                    try:
                        LMSHelper.unload_model(identifier)
                        unloaded_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to unload duplicate {identifier}: {e}")

        if unloaded_count:
            logger.info(f"Cleaned up {unloaded_count} duplicate model instance(s)")

        return unloaded_count

    def ensure_model_for_phase(
        self,
        model_name: str,
        ttl: int | None = None,
        test_id: str = "",
        scope: str = "",
    ) -> bool:
        """Load a model for a test phase, tracking it for teardown.

        Args:
            model_name: Model identifier to load.
            ttl: TTL in seconds (defaults to TEST_MODEL_TTL).
            test_id: Pytest node ID for inventory tracking.
            scope: Fixture scope for inventory tracking (session, module, class, function).

        Returns:
            True if model is available (loaded or already was).
        """
        actual_ttl = ttl if ttl is not None else TEST_MODEL_TTL

        # Check current load count to stay within VRAM budget
        loaded = LMSHelper.list_loaded_models() or []
        loaded_bases = {
            base
            for m in loaded
            for base in [LMSHelper._get_base_model_name(
                m.get("identifier") or m.get("modelKey") or ""
            )]
            if base
        }

        # Check if already loaded
        if LMSHelper.is_model_loaded(model_name):
            logger.debug(f"Model '{model_name}' already loaded")
            return True

        # VRAM budget check
        if len(loaded_bases) >= TEST_MAX_LOADED_MODELS:
            logger.warning(
                f"VRAM budget: {len(loaded_bases)}/{TEST_MAX_LOADED_MODELS} "
                f"models loaded, cannot load '{model_name}'"
            )
            return False

        # Load the model
        try:
            success = LMSHelper.load_model(model_name, ttl=actual_ttl)
            if success:
                self._loaded_by_us.add(model_name)
                if self._inventory is not None:
                    self._inventory.record_load(
                        model_name=model_name,
                        reason=MODEL_INVENTORY_REASON_LIFECYCLE,
                        test_id=test_id,
                        scope=scope,
                        phase="test",
                    )
                logger.info(f"Loaded '{model_name}' for test phase (TTL={actual_ttl}s)")
            return success
        except Exception as e:
            logger.warning(f"Failed to load '{model_name}': {e}")
            return False

    def unload_models_we_loaded(self) -> int:
        """Teardown: unload only models THIS session loaded.

        Returns:
            Number of models unloaded.
        """
        if not self._loaded_by_us:
            return 0

        unloaded = 0
        for model_name in list(self._loaded_by_us):
            try:
                LMSHelper.unload_model(model_name)
                unloaded += 1
                logger.debug(f"Teardown: unloaded '{model_name}'")
            except Exception as e:
                logger.warning(f"Teardown: failed to unload '{model_name}': {e}")

        self._loaded_by_us.clear()

        if unloaded:
            logger.info(f"Teardown: unloaded {unloaded} model(s) we loaded")

        return unloaded

    @property
    def models_we_loaded(self) -> frozenset[str]:
        """Read-only view of models loaded by this session."""
        return frozenset(self._loaded_by_us)
