"""JIT model loading guard — free function with no class coupling.

Extracted from ChatClient._ensure_model_loaded (H-1 review finding) so that
sub-clients can call it without constructing throwaway ChatClient instances.
"""

import logging
from typing import Optional

from config.constants import DEFAULT_MODEL_KEYWORD
from utils.lms_helper import LMSHelper

logger = logging.getLogger(__name__)


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
    try:
        is_loaded = LMSHelper.is_model_loaded(target_model)
        if is_loaded is False:
            logger.warning(f"{label} '{target_model}' not loaded, attempting to load...")
            load_success = LMSHelper.ensure_model_loaded_with_verification(
                target_model, ttl=ttl, skip_initial_check=True,
            )
            if not load_success:
                raise LLMConnectionError(
                    f"{label} '{target_model}' is not loaded and failed to load automatically."
                )
            logger.info(f"{label} '{target_model}' loaded successfully")
        elif is_loaded is True:
            logger.debug(f"{label} '{target_model}' already loaded")
    except LLMConnectionError:
        raise
    except Exception as e:
        logger.warning(f"Could not verify {label.lower()} load state: {e}. Proceeding anyway...")


__all__ = ["ensure_model_loaded"]
