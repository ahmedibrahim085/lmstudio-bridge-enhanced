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
from utils.lms_helper import LMSHelper, LMSRestClient

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredModels:
    """Snapshot of models available at test session start.

    Attributes:
        downloaded_ids: All model keys available on disk.
        loaded_ids: Model keys currently loaded in LM Studio.
        roles: Maps role name → best model key for that role.
        lmstudio_available: Whether LM Studio was reachable during discovery.
        models_metadata: Full model metadata from native API (model_key → API response dict).
    """

    downloaded_ids: list[str] = field(default_factory=list)
    loaded_ids: list[str] = field(default_factory=list)
    roles: dict[str, str] = field(default_factory=dict)
    lmstudio_available: bool = False
    # Full model metadata from native API (model_key → API response dict)
    models_metadata: dict[str, dict] = field(default_factory=dict)

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

    def get_metadata(self, model_key: str) -> dict | None:
        """Get full API metadata for a model."""
        return self.models_metadata.get(model_key)

    def has_capability(self, model_key: str, capability: str) -> bool:
        """Check if model has a specific capability (e.g., 'vision', 'trained_for_tool_use')."""
        meta = self.get_metadata(model_key)
        if not meta:
            return False
        caps = meta.get("capabilities", {})
        if isinstance(caps, dict):
            return bool(caps.get(capability, False))
        return False

    def get_size_bytes(self, model_key: str) -> int | None:
        """Get model size in bytes, or None if unknown."""
        meta = self.get_metadata(model_key)
        return meta.get("size_bytes") if meta else None


def _resolve_roles(
    loaded_ids: list[str],
    downloaded_ids: list[str],
    models_metadata: dict[str, dict] | None = None,
) -> dict[str, str]:
    """Assign models to roles. Resolution order per D-11:
    1. Env var override (LMS_TEST_{ROLE}_MODEL) — validated against available models
    2. Structured API fields (vision, tool_use, type=embedding) — from models_metadata
    3. Name-match keywords (for thinking, coding, chat, etc.)
    4. Prefer loaded, then smallest by size_bytes (D-4)

    Fallback constants used only if model exists in available pools.
    """
    import os

    from config.constants import LMS_TEST_ENV_VARS

    roles: dict[str, str] = {}
    all_available = set(loaded_ids) | set(downloaded_ids)
    if models_metadata is None:
        models_metadata = {}

    def _prefer_smallest(candidates: list[str]) -> str | None:
        """Pick the smallest model by size_bytes. Falls back to first if no size data."""
        if not candidates:
            return None
        if not models_metadata:
            return candidates[0]
        sized = [(c, models_metadata.get(c, {}).get("size_bytes")) for c in candidates]
        with_size = [(c, s) for c, s in sized if s is not None]
        if with_size:
            with_size.sort(key=lambda x: (x[1], x[0]))  # smallest first, alphabetical tiebreak
            return with_size[0][0]
        return candidates[0]

    # Tier 1: Env var overrides
    for role, env_var in LMS_TEST_ENV_VARS.items():
        if role in roles:
            continue
        env_model = os.environ.get(env_var)
        if env_model:
            if env_model in all_available:
                roles[role] = env_model
                logger.debug(f"Role '{role}' → '{env_model}' (env var {env_var})")
            else:
                logger.warning(
                    f"Env var {env_var}='{env_model}' not in available models, skipping"
                )

    # Tier 2: Structured API fields (only for roles with API-detectable capabilities)
    _STRUCTURED_ROLES = {
        "vision": lambda meta: meta.get("capabilities", {}).get("vision", False),
        "tool_use": lambda meta: meta.get("capabilities", {}).get("trained_for_tool_use", False),
        "embedding": lambda meta: meta.get("type") == "embedding",
    }
    for role, detector in _STRUCTURED_ROLES.items():
        if role in roles:
            continue
        # Prefer loaded models, then downloaded
        candidates = [m for m in loaded_ids if detector(models_metadata.get(m, {}))]
        if not candidates:
            candidates = [m for m in downloaded_ids if detector(models_metadata.get(m, {}))]
        if candidates:
            picked = _prefer_smallest(candidates)
            if picked:
                roles[role] = picked
                logger.debug(f"Role '{role}' → '{picked}' (structured API)")

    # Tier 3: Keyword matching (loaded first, then downloaded)
    for pool_label, pool in [("loaded", loaded_ids), ("downloaded", downloaded_ids)]:
        for role, keywords in MODEL_ROLE_KEYWORDS.items():
            if role in roles:
                continue
            candidates = [m for m in pool if any(kw in m.lower() for kw in keywords)]
            if candidates:
                picked = _prefer_smallest(candidates)
                if picked:
                    roles[role] = picked
                    logger.debug(f"Role '{role}' → '{picked}' (keyword match from {pool_label})")

    # Tier 4: Fallback constants (only if model exists in available pools)
    _FALLBACKS = {
        "chat": DEFAULT_FALLBACK_MODEL,
        "coding": DEFAULT_FALLBACK_MODEL,
        "reasoning": DEFAULT_REVIEW_MODEL,
        "thinking": DEFAULT_THINKING_MODEL,
    }
    for role, fallback in _FALLBACKS.items():
        if role not in roles and fallback in all_available:
            roles[role] = fallback
            logger.debug(f"Role '{role}' → '{fallback}' (fallback)")

    return roles


def _wake_up_loaded_role_models(
    roles: dict[str, str],
    loaded_ids: list[str],
    base_url: str,
) -> None:
    """Send 1-token completion to each loaded role model to verify responsiveness (D-5)."""
    import httpx

    from config.constants import WAKE_UP_PING_MAX_TOKENS, WAKE_UP_PING_TIMEOUT

    pinged: set[str] = set()
    for role, model_key in roles.items():
        if model_key in loaded_ids and model_key not in pinged:
            try:
                response = httpx.post(
                    f"{base_url}/v1/chat/completions",
                    json={
                        "model": model_key,
                        "messages": [{"role": "user", "content": "hi"}],
                        "max_tokens": WAKE_UP_PING_MAX_TOKENS,
                    },
                    timeout=WAKE_UP_PING_TIMEOUT,
                )
                if response.status_code == 200:
                    logger.debug(f"Wake-up ping OK: {model_key} (role={role})")
                else:
                    logger.warning(
                        f"Wake-up ping failed for {model_key}: HTTP {response.status_code}"
                    )
                pinged.add(model_key)
            except Exception as e:
                logger.warning(f"Wake-up ping failed for {model_key}: {e}")
                pinged.add(model_key)


def discover_models() -> DiscoveredModels:
    """Discover available models by querying LM Studio.

    Uses REST API first (native metadata with capabilities),
    falls back to LMSHelper CLI if REST unavailable.
    Safe to call when LM Studio is not running.
    """
    # Try REST API first (richer metadata)
    rest_client = LMSRestClient()
    if rest_client.is_server_available():
        try:
            raw_models = rest_client.list_all_models()
            if raw_models is not None:
                models_metadata: dict[str, dict] = {}
                loaded_ids: list[str] = []
                downloaded_ids: list[str] = []

                for m in raw_models:
                    key = m.get("key", "")
                    if not key:
                        continue
                    base_name = LMSHelper._get_base_model_name(key)
                    models_metadata[base_name] = m
                    downloaded_ids.append(base_name)
                    if m.get("loaded_instances"):
                        if base_name not in loaded_ids:
                            loaded_ids.append(base_name)

                # Deduplicate downloaded
                downloaded_ids = list(dict.fromkeys(downloaded_ids))

                roles = _resolve_roles(loaded_ids, downloaded_ids, models_metadata)

                # Wake-up ping for loaded models assigned to roles
                _wake_up_loaded_role_models(roles, loaded_ids, rest_client.base_url)

                result = DiscoveredModels(
                    downloaded_ids=downloaded_ids,
                    loaded_ids=loaded_ids,
                    roles=roles,
                    lmstudio_available=True,
                    models_metadata=models_metadata,
                )
                logger.info(
                    f"Discovery via REST: {len(loaded_ids)} loaded, "
                    f"{len(downloaded_ids)} downloaded, {len(roles)} roles"
                )
                return result
        except Exception as e:
            logger.warning(f"REST discovery failed, falling back to CLI: {e}")

    # Fallback: CLI-based discovery (existing logic)
    if not LMSHelper.is_installed():
        logger.info("LMS CLI not installed — returning empty discovery")
        return DiscoveredModels()

    try:
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

        downloaded_raw = LMSHelper.list_downloaded_models() or []
        downloaded_ids = []
        for m in downloaded_raw:
            model_key = m.get("modelKey") or ""
            if model_key and model_key not in downloaded_ids:
                downloaded_ids.append(model_key)

        roles = _resolve_roles(loaded_ids, downloaded_ids)

        result = DiscoveredModels(
            downloaded_ids=downloaded_ids,
            loaded_ids=loaded_ids,
            roles=roles,
            lmstudio_available=True,
        )
        logger.info(
            f"Discovery via CLI: {len(loaded_ids)} loaded, "
            f"{len(downloaded_ids)} downloaded, {len(roles)} roles"
        )
        return result
    except Exception as e:
        logger.warning(f"Model discovery failed: {e}")
        return DiscoveredModels()
