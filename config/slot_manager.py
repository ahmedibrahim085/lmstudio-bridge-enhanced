"""Agent Slot Manager — concurrent slot lifecycle (OPP-31 Phase 4).

Manages multiple concurrent agent slots, each independently configured
with a resolved config (role + model + overlay + constraints).

Thread-safe: all slot mutations protected by threading.Lock.
"""

import logging
import threading
from typing import Any, Dict, List, Optional

from config.resolved_config import ResolvedConfig
from config.resolver import DynamicResolver

logger = logging.getLogger(__name__)


class AgentSlotManager:
    """Manages multiple concurrent agent slots.

    Each slot is a named binding of role + model + resolved config.
    Slots are independent — same role can be used in multiple slots
    with different models.

    Thread-safe: concurrent create/remove/get operations are protected
    by a lock per V5 plan code review requirements.

    Args:
        resolver: DynamicResolver for config resolution.
    """

    def __init__(self, resolver: DynamicResolver) -> None:
        self._resolver = resolver
        self._slots: Dict[str, ResolvedConfig] = {}
        self._lock = threading.Lock()

    def create_slot(
        self,
        name: str,
        role: str,
        model_id: Optional[str] = None,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> ResolvedConfig:
        """Create a new agent slot.

        Args:
            name: Unique slot name (e.g. "my-coder", "pr-reviewer").
            role: Role template name (e.g. "coder", "tester").
            model_id: Explicit model ID, or None for auto-resolve.
            overrides: Optional param overrides (temperature, etc.).

        Returns:
            Frozen ResolvedConfig for the new slot.

        Raises:
            ValueError: If a slot with this name already exists.
            KeyError: If the role name is not in the registry.
        """
        with self._lock:
            if name in self._slots:
                raise ValueError(
                    f"Slot '{name}' already exists. "
                    f"Remove it first or choose a different name."
                )
            config = self._resolver.resolve(
                role_name=role,
                model_id=model_id,
                user_overrides=overrides,
            )
            self._slots[name] = config
            logger.debug("Created slot '%s': role=%s model=%s", name, role, config.model_id)
            return config

    def get_slot(self, name: str) -> ResolvedConfig:
        """Get a slot's resolved config.

        Raises:
            KeyError: If the slot name doesn't exist.
        """
        with self._lock:
            if name not in self._slots:
                raise KeyError(
                    f"Slot '{name}' not found. "
                    f"Available: {sorted(self._slots.keys())}"
                )
            return self._slots[name]

    def remove_slot(self, name: str) -> None:
        """Remove an agent slot. Does NOT unload the model.

        Raises:
            KeyError: If the slot name doesn't exist.
        """
        with self._lock:
            if name not in self._slots:
                raise KeyError(
                    f"Slot '{name}' not found. "
                    f"Available: {sorted(self._slots.keys())}"
                )
            del self._slots[name]
            logger.debug("Removed slot '%s'", name)

    def list_slots(self) -> List[Dict[str, Any]]:
        """List all active slots with their configs.

        Returns:
            List of dicts with slot info (name, role, model_id, family, temperature).
        """
        with self._lock:
            return [
                {
                    "name": name,
                    "role": config.role_name,
                    "model_id": config.model_id,
                    "family": config.family,
                    "task_type": config.task_type,
                    "temperature": config.temperature,
                }
                for name, config in sorted(self._slots.items())
            ]


__all__ = [
    "AgentSlotManager",
]
