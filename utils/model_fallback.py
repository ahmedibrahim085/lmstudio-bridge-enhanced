#!/usr/bin/env python3
"""
Model Fallback Manager

Provides graceful handling when requested models are unavailable.
Finds suitable alternatives based on model capabilities and task requirements.

Features:
- Check if models are available locally
- Find alternative models based on capability matching
- Resolve model requests with automatic or suggested fallbacks
- Task-aware model selection
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass

from utils.lms_helper import LMSHelper

logger = logging.getLogger(__name__)


@dataclass
class ModelAlternative:
    """Represents an alternative model suggestion."""
    model_key: str
    display_name: str
    score: int
    reasons: List[str]
    size_bytes: Optional[int] = None
    trained_for_tool_use: bool = False
    max_context_length: Optional[int] = None


class ModelFallbackManager:
    """
    Handles graceful fallback when requested models are unavailable.

    Usage:
        manager = ModelFallbackManager()

        # Check if model is available
        if not manager.is_model_available("deepseek/deepseek-coder-33b"):
            # Find alternatives
            alternatives = manager.find_alternatives("deepseek/deepseek-coder-33b")

        # Or use auto-resolution
        model, message = manager.resolve_model("deepseek/deepseek-coder-33b", auto_fallback=True)
    """

    def __init__(self, cache_ttl: int = 60):
        """
        Initialize the fallback manager.

        Args:
            cache_ttl: How long to cache the downloaded models list (seconds)
        """
        self._cache_ttl = cache_ttl
        self._downloaded_models: Optional[List[Dict]] = None
        self._cache_time: float = 0

    def _refresh_cache(self, force: bool = False) -> bool:
        """
        Refresh the cached list of downloaded models.

        Args:
            force: If True, refresh even if cache is fresh

        Returns:
            True if refresh succeeded
        """
        import time

        now = time.time()
        if not force and self._downloaded_models and (now - self._cache_time) < self._cache_ttl:
            return True  # Cache is still fresh

        models = LMSHelper.list_downloaded_models()
        if models is not None:
            self._downloaded_models = models
            self._cache_time = now
            return True

        return False

    def is_model_available(self, model_key: str) -> bool:
        """
        Check if a model is downloaded locally.

        Args:
            model_key: Model identifier to check

        Returns:
            True if model is available locally
        """
        self._refresh_cache()

        if not self._downloaded_models:
            return False

        return any(m.get("modelKey") == model_key for m in self._downloaded_models)

    def get_model_info(self, model_key: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a downloaded model.

        Args:
            model_key: Model identifier

        Returns:
            Model metadata dict or None if not found
        """
        self._refresh_cache()

        if not self._downloaded_models:
            return None

        for model in self._downloaded_models:
            if model.get("modelKey") == model_key:
                return model

        return None

    def find_alternatives(
        self,
        model_key: str,
        task_type: Optional[str] = None,
        max_results: int = 5
    ) -> List[ModelAlternative]:
        """
        Find alternative models that might work for the same task.

        Args:
            model_key: The requested model that isn't available
            task_type: Optional hint about the task (e.g., "coding", "reasoning", "chat")
            max_results: Maximum number of alternatives to return

        Returns:
            List of ModelAlternative objects, sorted by relevance score
        """
        self._refresh_cache()

        if not self._downloaded_models:
            return []

        alternatives = []
        model_lower = model_key.lower()

        # Extract hints from model name
        is_coder = any(x in model_lower for x in ["coder", "code", "starcoder", "codellama"])
        is_reasoning = any(x in model_lower for x in ["thinking", "r1", "reasoning", "o1", "qwq"])
        is_instruct = any(x in model_lower for x in ["instruct", "chat"])
        is_small = any(x in model_lower for x in ["7b", "8b", "4b", "3b", "1b", "0.5b"])
        is_medium = any(x in model_lower for x in ["13b", "14b", "15b", "20b"])
        is_large = any(x in model_lower for x in ["30b", "32b", "33b", "34b", "70b", "72b"])

        # Also consider task_type hint
        if task_type:
            task_lower = task_type.lower()
            if "cod" in task_lower:
                is_coder = True
            if "reason" in task_lower or "think" in task_lower or "analy" in task_lower:
                is_reasoning = True

        for model in self._downloaded_models:
            key = model.get("modelKey", "")
            key_lower = key.lower()

            # Skip the original model
            if key_lower == model_lower:
                continue

            score = 0
            reasons = []

            # Match by capability
            if is_coder and any(x in key_lower for x in ["coder", "code", "starcoder", "codellama"]):
                score += 5
                reasons.append("coding capability")

            if is_reasoning and any(x in key_lower for x in ["thinking", "r1", "reasoning", "qwq"]):
                score += 5
                reasons.append("reasoning capability")

            if is_instruct and any(x in key_lower for x in ["instruct", "chat"]):
                score += 2
                reasons.append("instruction-tuned")

            # Match by size class
            if is_small and any(x in key_lower for x in ["7b", "8b", "4b", "3b"]):
                score += 2
                reasons.append("similar size")
            elif is_medium and any(x in key_lower for x in ["13b", "14b", "15b", "20b"]):
                score += 2
                reasons.append("similar size")
            elif is_large and any(x in key_lower for x in ["30b", "32b", "33b", "70b", "72b"]):
                score += 2
                reasons.append("similar size")

            # Prefer models trained for tool use
            if model.get("trainedForToolUse"):
                score += 3
                reasons.append("tool-use trained")

            # Match model family if possible
            requested_publisher = model_key.split("/")[0] if "/" in model_key else ""
            candidate_publisher = key.split("/")[0] if "/" in key else ""
            if requested_publisher and candidate_publisher and requested_publisher.lower() == candidate_publisher.lower():
                score += 2
                reasons.append("same publisher")

            # Add some base score for any model (fallback is better than nothing)
            if score == 0 and model.get("trainedForToolUse"):
                score = 1
                reasons.append("available with tool-use")

            if score > 0:
                alternatives.append(ModelAlternative(
                    model_key=key,
                    display_name=model.get("displayName", key),
                    score=score,
                    reasons=reasons,
                    size_bytes=model.get("sizeBytes"),
                    trained_for_tool_use=model.get("trainedForToolUse", False),
                    max_context_length=model.get("maxContextLength")
                ))

        # Sort by score (descending), then by tool-use capability
        alternatives.sort(key=lambda x: (-x.score, -int(x.trained_for_tool_use)))

        return alternatives[:max_results]

    def resolve_model(
        self,
        requested_model: str,
        auto_fallback: bool = False,
        task_type: Optional[str] = None
    ) -> Tuple[str, str, Optional[List[ModelAlternative]]]:
        """
        Resolve a model request - return available model or fallback.

        Args:
            requested_model: The model that was requested
            auto_fallback: If True, automatically use best alternative
            task_type: Optional task hint for better matching

        Returns:
            Tuple of:
            - resolved_model: The model to use (may be fallback)
            - status: "available", "fallback", or "unavailable"
            - alternatives: List of alternatives (if not available)
        """
        # Check if requested model is available
        if self.is_model_available(requested_model):
            return requested_model, "available", None

        # Find alternatives
        alternatives = self.find_alternatives(requested_model, task_type=task_type)

        if not alternatives:
            logger.warning(f"Model '{requested_model}' not found, no alternatives available")
            return requested_model, "unavailable", []

        if auto_fallback:
            best = alternatives[0]
            logger.info(
                f"Auto-fallback: '{requested_model}' → '{best.model_key}' "
                f"(reasons: {', '.join(best.reasons)})"
            )
            return best.model_key, "fallback", alternatives

        # Return info about alternatives without auto-selecting
        return requested_model, "unavailable", alternatives

    def format_alternatives_message(
        self,
        requested_model: str,
        alternatives: List[ModelAlternative]
    ) -> str:
        """
        Format a human-readable message about available alternatives.

        Args:
            requested_model: The model that was requested
            alternatives: List of alternatives

        Returns:
            Formatted message string
        """
        if not alternatives:
            return f"Model '{requested_model}' is not downloaded. No alternatives found."

        lines = [
            f"Model '{requested_model}' is not downloaded.",
            "",
            "Available alternatives:"
        ]

        for i, alt in enumerate(alternatives, 1):
            tool_icon = "✅" if alt.trained_for_tool_use else "❌"
            size_str = f"{alt.size_bytes / (1024**3):.1f}GB" if alt.size_bytes else "N/A"
            lines.append(
                f"  {i}. {alt.model_key}"
                f"\n     Score: {alt.score} | Tool-use: {tool_icon} | Size: {size_str}"
                f"\n     Reasons: {', '.join(alt.reasons)}"
            )

        lines.append("")
        lines.append("Options:")
        lines.append(f"  - Download requested model: lms_download_model('{requested_model}')")
        lines.append(f"  - Use best alternative: {alternatives[0].model_key}")

        return "\n".join(lines)


# Singleton instance for convenience
_default_manager: Optional[ModelFallbackManager] = None


def get_fallback_manager() -> ModelFallbackManager:
    """Get the default ModelFallbackManager instance."""
    global _default_manager
    if _default_manager is None:
        _default_manager = ModelFallbackManager()
    return _default_manager


__all__ = [
    'ModelFallbackManager',
    'ModelAlternative',
    'get_fallback_manager'
]
