#!/usr/bin/env python3
"""
OPP-08: Smart Model Selection.

Selects the best available (loaded) model for a given task type by scoring
each model against the capability most relevant to that task.

Public API
----------
- SmartModelSelector       — stateless scorer; accepts a pre-built dict of models
- select_best_model()      — convenience function that queries LM Studio live
- NoModelsAvailableError   — raised when the filtered candidate set is empty
"""

import logging
from typing import Optional

from config.constants import (
    SELECTION_WEIGHT_CAPABILITY,
    TASK_CAPABILITY_MAP,
)
from model_registry.cache import CacheManager
from model_registry.lms_integration import LMSIntegration
from model_registry.schemas import ModelMetadata, ModelType

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------


class NoModelsAvailableError(Exception):
    """Raised when no candidate models remain after filtering."""


# ---------------------------------------------------------------------------
# SmartModelSelector
# ---------------------------------------------------------------------------


class SmartModelSelector:
    """Score and rank loaded models for a given task type.

    Parameters
    ----------
    loaded_models:
        Mapping of model_id → ModelMetadata for the models that are currently
        loaded in LM Studio.  Embedding models are automatically excluded from
        selection.
    """

    def __init__(self, loaded_models: dict[str, ModelMetadata]) -> None:
        self._models = loaded_models

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def select(
        self,
        task_type: str,
        max_vram_gb: Optional[float] = None,
    ) -> str:
        """Return the model_id of the best model for *task_type*.

        Parameters
        ----------
        task_type:
            Task identifier string (e.g. ``"code_generation"``,
            ``"summarization"``).  Unknown values trigger graceful fallback.
        max_vram_gb:
            Optional VRAM budget in gigabytes.  Models whose
            ``estimated_vram_gb`` **exceeds** this value are excluded.
            Models with ``estimated_vram_gb = None`` are always included.

        Returns
        -------
        str
            The model_id of the selected model.

        Raises
        ------
        NoModelsAvailableError
            When the candidate set is empty (nothing loaded, all filtered by
            VRAM budget, or only embedding models present).
        """
        # 1. Build candidate set (LLMs only)
        candidates = [
            m for m in self._models.values()
            if m.model_type == ModelType.LLM
        ]

        # 2. Apply VRAM budget filter
        if max_vram_gb is not None:
            candidates = [
                m for m in candidates
                if m.estimated_vram_gb is None or m.estimated_vram_gb <= max_vram_gb
            ]

        if not candidates:
            raise NoModelsAvailableError(
                f"No loaded LLM models available for task '{task_type}'. "
                "Ensure at least one LLM is loaded in LM Studio."
            )

        # 3. Classify task → capability name
        capability = self._classify_task(task_type)

        # 4. Score each candidate
        scored = [
            (m, self._score_model(m, capability) if capability else 0.0)
            for m in candidates
        ]

        # 5. Sort: highest score first; break ties by model_id (deterministic)
        scored.sort(key=lambda t: (-t[1], t[0].model_id))

        best = scored[0][0]
        logger.debug(
            "Smart selection: task=%s capability=%s selected=%s score=%.3f",
            task_type, capability, best.model_id, scored[0][1],
        )
        return best.model_id

    # ------------------------------------------------------------------
    # Task classification
    # ------------------------------------------------------------------

    def _classify_task(self, task_type: str) -> Optional[str]:
        """Map a task_type string to a ModelCapabilities attribute name.

        Returns ``None`` when no mapping exists (unknown task).
        """
        return TASK_CAPABILITY_MAP.get(task_type.lower())

    # ------------------------------------------------------------------
    # Per-model scoring
    # ------------------------------------------------------------------

    def _score_model(self, model: ModelMetadata, capability: Optional[str]) -> float:
        """Compute a numeric score for *model* on *capability*.

        Score formula
        -------------
        - If ``capability`` is ``None`` → 0.0 (no basis to differentiate)
        - If the capability field is absent (``None``) → 0.0
        - If ``supported`` is ``False`` / ``0`` → 0.0
        - If ``supported`` is ``True``  → ``confidence * SELECTION_WEIGHT_CAPABILITY``
        - If ``supported`` is a float   → ``supported * confidence * SELECTION_WEIGHT_CAPABILITY``

        Returns
        -------
        float
            Non-negative score; higher = better.
        """
        if not capability:
            return 0.0

        cap_score = getattr(model.capabilities, capability, None)
        if cap_score is None:
            return 0.0

        supported = cap_score.supported
        confidence = cap_score.confidence

        if isinstance(supported, bool):
            if not supported:
                return 0.0
            return confidence * SELECTION_WEIGHT_CAPABILITY

        # float score
        if supported <= 0:
            return 0.0
        return float(supported) * confidence * SELECTION_WEIGHT_CAPABILITY


# ---------------------------------------------------------------------------
# Convenience function (live LM Studio query)
# ---------------------------------------------------------------------------


def select_best_model(
    task_type: str,
    requirements: Optional[dict] = None,
    cache_path: Optional[str] = None,
) -> str:
    """Select the best loaded model for *task_type* by querying LM Studio.

    This is the primary public API.  It:

    1. Fetches currently loaded model IDs from LM Studio via the REST/CLI.
    2. Looks up full metadata from the local capability cache.
    3. Falls back to minimal stubs for models not yet in the cache.
    4. Delegates scoring and selection to :class:`SmartModelSelector`.

    Parameters
    ----------
    task_type:
        Task identifier (e.g. ``"code_generation"``, ``"summarization"``).
    requirements:
        Optional dict with selection constraints.  Recognised keys:

        - ``"max_vram_gb"`` (*float*) — VRAM budget in GB.

    cache_path:
        Override the default cache file path.

    Returns
    -------
    str
        The model_id of the best available model.

    Raises
    ------
    NoModelsAvailableError
        When no suitable model can be found.
    """
    requirements = requirements or {}

    # 1. Discover which models are currently loaded
    loaded_ids: list[str] = LMSIntegration.get_loaded_model_ids()

    # 2. Load capability cache
    cache = CacheManager(cache_path)
    all_cached: dict[str, ModelMetadata] = cache.load()

    # 3. Build the loaded-models dict (cached metadata where available)
    loaded_models: dict[str, ModelMetadata] = {}
    for model_id in loaded_ids:
        if model_id in all_cached:
            loaded_models[model_id] = all_cached[model_id]
        else:
            # Build a minimal stub so the selector can still work
            stub = ModelMetadata(
                model_id=model_id,
                model_type=ModelType.LLM,
                display_name=model_id,
                publisher="",
                model_family="unknown",
                architecture="unknown",
            )
            loaded_models[model_id] = stub
            logger.debug("Model %s not in cache; using stub for selection", model_id)

    # 4. Delegate to the selector
    max_vram_gb: Optional[float] = requirements.get("max_vram_gb")
    selector = SmartModelSelector(loaded_models=loaded_models)
    return selector.select(task_type, max_vram_gb=max_vram_gb)
