"""JIT model loading guard — free function with no class coupling.

Extracted from ChatClient._ensure_model_loaded (H-1 review finding) so that
sub-clients can call it without constructing throwaway ChatClient instances.
"""

import logging
import threading
import time
from typing import Optional

from config.constants import DEFAULT_MODEL_KEYWORD, POLL_JIT_GUARD_TTL
from utils.lms_helper import LMSHelper

logger = logging.getLogger(__name__)

# Module-level memoization (OPP-43)
# Lock follows codebase convention: 5 other caches use threading.Lock
# (LMSRestClient._cache_lock, ModelValidator._class_cache_lock,
#  _registry_lock, SlotManager._lock, _config_lock)
_memo_lock = threading.Lock()
_confirmed_models: dict[str, float] = {}


def ensure_model_loaded(
    target_model: Optional[str],
    ttl: int,
    label: str = "Model",
) -> None:
    """Ensure a model is loaded in LM Studio, loading it if needed.

    Args:
        target_model: Model identifier to load (skips if None or "default").
        ttl: Time-to-live for the model loading verification.
        label: Human-readable label for log messages.
    """
    from llm.exceptions import LLMConnectionError

    if not target_model or target_model == DEFAULT_MODEL_KEYWORD or not LMSHelper.is_installed():
        return

    # OPP-43: Skip check if model confirmed loaded within guard TTL
    now = time.monotonic()
    with _memo_lock:
        last_confirmed = _confirmed_models.get(target_model, 0.0)
        if (now - last_confirmed) < POLL_JIT_GUARD_TTL:
            return

    # I/O happens OUTSIDE the lock (same pattern as ModelValidator)
    try:
        is_loaded = LMSHelper.is_model_loaded(target_model)
        if is_loaded is True:
            with _memo_lock:
                _confirmed_models[target_model] = now
            logger.debug(f"{label} '{target_model}' already loaded")
        elif is_loaded is False:
            with _memo_lock:
                _confirmed_models.pop(target_model, None)
            logger.warning(f"{label} '{target_model}' not loaded, attempting to load...")
            load_success = LMSHelper.ensure_model_loaded_with_verification(
                target_model, ttl=ttl, skip_initial_check=True,
            )
            if not load_success:
                raise LLMConnectionError(
                    f"{label} '{target_model}' is not loaded and failed to load automatically."
                )
            with _memo_lock:
                _confirmed_models[target_model] = time.monotonic()
            logger.info(f"{label} '{target_model}' loaded successfully")
        # is_loaded is None (server unavailable) → no memoization, will retry next call
    except LLMConnectionError:
        raise
    except Exception as e:
        logger.warning(f"Could not verify {label.lower()} load state: {e}. Proceeding anyway...")


def invalidate_jit_cache(model_name: Optional[str] = None) -> None:
    """Clear JIT memoization cache. For testing and explicit invalidation.

    Args:
        model_name: Specific model to invalidate, or None to clear all.
    """
    with _memo_lock:
        if model_name is not None:
            _confirmed_models.pop(model_name, None)
        else:
            _confirmed_models.clear()


__all__ = ["ensure_model_loaded", "invalidate_jit_cache"]
