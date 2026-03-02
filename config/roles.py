"""User-defined role templates and registry (OPP-31 Phase 1).

A role is a named behavioral template: system prompt + sampling params +
capability hints. Users create any role they need via YAML files or the
runtime API. Nothing is hardcoded — example roles are shipped as starting
points, not mandated defaults.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple

import yaml

logger = logging.getLogger(__name__)

# Example roles shipped with the bridge
EXAMPLE_ROLES_DIR = Path(__file__).resolve().parent.parent / "roles" / "examples"


@dataclass(frozen=True)
class RoleTemplate:
    """A named behavioral template. Fully user-definable.

    Attributes:
        name: Any name the user chooses (must be unique per registry)
        description: Human-readable purpose
        system_prompt: Behavioral instructions for the LLM
        temperature: Default sampling temperature
        max_tokens: Maximum output tokens
        context_length: Working memory context window
        context_overflow_policy: How to handle context overflow
        preferred_capabilities: Capability hints for auto-resolution
    """

    name: str
    description: str
    system_prompt: str
    temperature: float = 0.7
    max_tokens: int = 4096
    context_length: int = 16384
    context_overflow_policy: str = "truncateMiddle"
    preferred_capabilities: Tuple[str, ...] = ()


def _parse_role_yaml(path: Path) -> RoleTemplate:
    """Parse a single YAML file into a RoleTemplate."""
    with open(path, "r") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Invalid YAML in {path}: expected a mapping")

    if "name" not in data:
        raise ValueError(f"Missing required field 'name' in {path}")
    if "system_prompt" not in data:
        raise ValueError(f"Missing required field 'system_prompt' in {path}")

    # Convert list to tuple for frozen dataclass
    caps = data.get("preferred_capabilities", ())
    if isinstance(caps, list):
        caps = tuple(caps)

    return RoleTemplate(
        name=data["name"],
        description=data.get("description", ""),
        system_prompt=data["system_prompt"],
        temperature=float(data.get("temperature", 0.7)),
        max_tokens=int(data.get("max_tokens", 4096)),
        context_length=int(data.get("context_length", 16384)),
        context_overflow_policy=data.get("context_overflow_policy", "truncateMiddle"),
        preferred_capabilities=caps,
    )


class RoleRegistry:
    """Registry of named role templates, loaded from YAML files.

    Roles can be loaded from a directory of YAML files at construction
    time, and new roles can be added at runtime via add().

    Args:
        roles_dir: Directory containing .yaml role files. If None or
            non-existent, starts with an empty registry.
    """

    def __init__(self, roles_dir: Path = None) -> None:
        self._roles: dict[str, RoleTemplate] = {}
        if roles_dir is not None and roles_dir.exists():
            self._load_directory(roles_dir)

    def _load_directory(self, roles_dir: Path) -> None:
        """Load all .yaml files from a directory."""
        for yaml_file in sorted(roles_dir.glob("*.yaml")):
            role = _parse_role_yaml(yaml_file)
            if role.name in self._roles:
                raise ValueError(
                    f"Duplicate role name '{role.name}' in {yaml_file} "
                    f"(already loaded)"
                )
            self._roles[role.name] = role
            logger.debug("Loaded role '%s' from %s", role.name, yaml_file)

    def get(self, name: str) -> RoleTemplate:
        """Get a role by name. Raises KeyError if not found."""
        if name not in self._roles:
            raise KeyError(f"Role '{name}' not found. Available: {self.list()}")
        return self._roles[name]

    def list(self) -> List[str]:
        """Return sorted list of all role names."""
        return sorted(self._roles.keys())

    def add(self, role: RoleTemplate) -> None:
        """Add a role at runtime. Raises ValueError if name already exists."""
        if role.name in self._roles:
            raise ValueError(f"Duplicate role name '{role.name}'")
        self._roles[role.name] = role


__all__ = [
    "RoleTemplate",
    "RoleRegistry",
    "EXAMPLE_ROLES_DIR",
]
