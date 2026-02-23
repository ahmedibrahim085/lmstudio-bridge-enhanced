"""
Dynamic Model Discovery for Tests.

Wraps LMSHelper (DOGFOODING) to discover available models at test session start.
Assigns models to roles (chat, reasoning, coding, etc.) via keyword matching.
Returns empty DiscoveredModels when LM Studio is unavailable (safe for unit tests).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from config.constants import (
    DEFAULT_FALLBACK_MODEL,
    DEFAULT_REVIEW_MODEL,
    DEFAULT_THINKING_MODEL,
    MODEL_ROLE_KEYWORDS,
)
from utils.lms_helper import LMSHelper

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredModels:
    """Snapshot of models available at test session start.

    Attributes:
        downloaded_ids: All model keys available on disk.
        loaded_ids: Model keys currently loaded in LM Studio.
        roles: Maps role name → best model key for that role.
        lmstudio_available: Whether LM Studio was reachable during discovery.
    """

    downloaded_ids: list[str] = field(default_factory=list)
    loaded_ids: list[str] = field(default_factory=list)
    roles: dict[str, str] = field(default_factory=dict)
    lmstudio_available: bool = False

    # Convenience accessors for common roles
    @property
    def chat_model(self) -> str | None:
        return self.roles.get("chat")

    @property
    def reasoning_model(self) -> str | None:
        return self.roles.get("reasoning")

    @property
    def coding_model(self) -> str | None:
        return self.roles.get("coding")

    @property
    def thinking_model(self) -> str | None:
        return self.roles.get("thinking")

    @property
    def small_model(self) -> str | None:
        return self.roles.get("small")

    @property
    def vision_model(self) -> str | None:
        return self.roles.get("vision")


def _resolve_roles(
    loaded_ids: list[str],
    downloaded_ids: list[str],
) -> dict[str, str]:
    """Assign models to roles using keyword matching.

    Priority: loaded models first, then downloaded models.
    Uses MODEL_ROLE_KEYWORDS from config/constants.py.

    Args:
        loaded_ids: Currently loaded model identifiers.
        downloaded_ids: All downloaded model identifiers.

    Returns:
        Dict mapping role name → best model identifier for that role.
    """
    roles: dict[str, str] = {}

    # Search loaded models first (prefer already-loaded for speed)
    for pool_label, pool in [("loaded", loaded_ids), ("downloaded", downloaded_ids)]:
        for role, keywords in MODEL_ROLE_KEYWORDS.items():
            if role in roles:
                continue  # Already assigned from a higher-priority pool
            for model_id in pool:
                model_lower = model_id.lower()
                if any(kw in model_lower for kw in keywords):
                    roles[role] = model_id
                    logger.debug(
                        f"Role '{role}' → '{model_id}' (matched from {pool_label})"
                    )
                    break

    # Apply fallbacks from config/constants.py for unresolved roles
    _FALLBACKS = {
        "chat": DEFAULT_FALLBACK_MODEL,
        "coding": DEFAULT_FALLBACK_MODEL,
        "reasoning": DEFAULT_REVIEW_MODEL,
        "thinking": DEFAULT_THINKING_MODEL,
    }
    for role, fallback in _FALLBACKS.items():
        if role not in roles:
            # Only use fallback if it's actually available
            if fallback in loaded_ids or fallback in downloaded_ids:
                roles[role] = fallback
                logger.debug(f"Role '{role}' → '{fallback}' (fallback)")

    return roles


def discover_models() -> DiscoveredModels:
    """Discover available models by querying LM Studio via LMSHelper.

    Safe to call even when LM Studio is not running — returns empty
    DiscoveredModels with lmstudio_available=False.

    Returns:
        DiscoveredModels with populated fields if LM Studio is available.
    """
    if not LMSHelper.is_installed():
        logger.info("LMS CLI not installed — returning empty discovery")
        return DiscoveredModels()

    try:
        # Get loaded models
        loaded_raw = LMSHelper.list_loaded_models()
        if loaded_raw is None:
            logger.info("LM Studio not reachable — returning empty discovery")
            return DiscoveredModels()

        loaded_ids = []
        for m in loaded_raw:
            model_key = m.get("modelKey") or m.get("identifier") or ""
            base_name = LMSHelper._get_base_model_name(model_key)
            if base_name and base_name not in loaded_ids:
                loaded_ids.append(base_name)

        # Get downloaded models
        downloaded_raw = LMSHelper.list_downloaded_models() or []
        downloaded_ids = []
        for m in downloaded_raw:
            model_key = m.get("modelKey") or ""
            if model_key and model_key not in downloaded_ids:
                downloaded_ids.append(model_key)

        # Resolve roles
        roles = _resolve_roles(loaded_ids, downloaded_ids)

        result = DiscoveredModels(
            downloaded_ids=downloaded_ids,
            loaded_ids=loaded_ids,
            roles=roles,
            lmstudio_available=True,
        )

        logger.info(
            f"Discovery complete: {len(loaded_ids)} loaded, "
            f"{len(downloaded_ids)} downloaded, "
            f"{len(roles)} roles assigned"
        )
        return result

    except Exception as e:
        logger.warning(f"Model discovery failed: {e}")
        return DiscoveredModels()
