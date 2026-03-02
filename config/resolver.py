"""Dynamic configuration resolver (OPP-31 Phase 3).

Composes with OPP-08's SmartModelSelector to auto-pick or accept explicit
model assignments, then layers config from multiple sources:

    Priority (highest wins):
      1. Critical constraints  — mandatory model-specific (R1 temp>=0.6)
      2. User overrides        — explicit per-request params
      3. Family overlay        — knowledge base per-family per-task
      4. Role template         — user-defined role defaults
      5. Global defaults       — constants.py fallbacks
"""

import logging
from typing import Any, Dict, Optional

from config.model_knowledge import (
    STANDARD_TASK_TYPES,
    detect_family,
    get_critical_constraints,
    get_overlay,
)
from config.resolved_config import ResolvedConfig
from config.roles import RoleRegistry, RoleTemplate

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Task type inference
# ---------------------------------------------------------------------------

# Maps preferred_capabilities to knowledge base task types.
_CAPABILITY_TASK_MAP: Dict[str, str] = {
    "code": "code",
    "reasoning": "chat",
    "long_context": "write",
}


def infer_task_type(role: RoleTemplate) -> str:
    """Infer knowledge base task type from a role template.

    Strategy:
      1. Role name exact match to standard task types (code/test/write/review/chat)
      2. Preferred capabilities mapping
      3. Default to 'chat'
    """
    if role.name in STANDARD_TASK_TYPES:
        return role.name

    for cap in role.preferred_capabilities:
        if cap in _CAPABILITY_TASK_MAP:
            return _CAPABILITY_TASK_MAP[cap]

    return "chat"


# ---------------------------------------------------------------------------
# DynamicResolver
# ---------------------------------------------------------------------------


class DynamicResolver:
    """Resolve a fully-configured ResolvedConfig from role + model + overrides.

    Two resolution modes:
      - **Explicit**: caller provides model_id directly.
      - **Auto-resolve**: model_id=None → delegates to SmartModelSelector.

    Args:
        role_registry: Registry of named role templates.
        model_selector: Optional OPP-08 SmartModelSelector for auto-resolve.
    """

    def __init__(
        self,
        role_registry: RoleRegistry,
        model_selector: Any = None,
    ) -> None:
        self._registry = role_registry
        self._selector = model_selector

    def resolve(
        self,
        role_name: str,
        model_id: Optional[str] = None,
        user_overrides: Optional[Dict[str, Any]] = None,
    ) -> ResolvedConfig:
        """Resolve a fully-configured agent config.

        Args:
            role_name: Name of a registered role template.
            model_id: Explicit model ID, or None for auto-resolve.
            user_overrides: Optional param overrides (temperature, etc.).

        Returns:
            Frozen ResolvedConfig ready for LM Studio API.

        Raises:
            KeyError: If role_name is not in the registry.
            ValueError: If model_id is None and no model_selector is configured.
        """
        # 1. Look up role template (raises KeyError if unknown)
        role = self._registry.get(role_name)

        # 2. Resolve model
        if model_id is None:
            if self._selector is None:
                raise ValueError(
                    "Cannot auto-resolve model: no model_selector configured. "
                    "Provide an explicit model_id or configure a SmartModelSelector."
                )
            task_type = infer_task_type(role)
            model_id = self._selector.select(task_type)

        # 3. Detect family
        family = detect_family(model_id)

        # 4. Infer task type for knowledge base lookup
        task_type = infer_task_type(role)

        # 5. Layer config: role defaults → family overlay → user overrides → constraints
        temperature = role.temperature
        top_p: Optional[float] = None
        top_k: Optional[int] = None

        # Layer 4: Family overlay
        overlay = get_overlay(family, task_type)
        if "temperature" in overlay:
            temperature = overlay["temperature"]
        if "top_p" in overlay:
            top_p = overlay["top_p"]
        if "top_k" in overlay:
            top_k = int(overlay["top_k"])

        # Layer 2: User overrides
        overrides = user_overrides or {}
        if "temperature" in overrides:
            temperature = float(overrides["temperature"])
        if "top_p" in overrides:
            top_p = float(overrides["top_p"])
        if "top_k" in overrides:
            top_k = int(overrides["top_k"])

        # Layer 1: Critical constraints (ALWAYS win)
        constraints = get_critical_constraints(family)
        if "min_temperature" in constraints:
            min_temp = constraints["min_temperature"]
            if temperature < min_temp:
                logger.warning(
                    "Critical constraint: %s requires temperature >= %.1f, "
                    "overriding %.1f → %.1f",
                    family, min_temp, temperature, min_temp,
                )
                temperature = min_temp

        return ResolvedConfig(
            role_name=role_name,
            model_id=model_id,
            family=family,
            task_type=task_type,
            system_prompt=role.system_prompt,
            temperature=temperature,
            max_tokens=role.max_tokens,
            top_p=top_p,
            top_k=top_k,
            context_length=role.context_length,
            context_overflow_policy=role.context_overflow_policy,
        )


__all__ = [
    "DynamicResolver",
    "ResolvedConfig",
    "infer_task_type",
]
