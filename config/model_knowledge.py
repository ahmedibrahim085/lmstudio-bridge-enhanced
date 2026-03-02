"""Model knowledge base — vendor-researched optimal params per family x task (OPP-31 Phase 2).

Maps model families to optimal sampling parameters for each task type.
Data sourced from vendor documentation and benchmark studies (126+ sources).

Extensible: add new family = 1 pattern + 1 dict (no other code changes).
"""

import re
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# Family detection patterns (order matters — first match wins)
# ---------------------------------------------------------------------------

_FAMILY_PATTERNS: List[Tuple[str, str]] = [
    (r"deepseek[_-]?r1", "deepseek-r1"),   # Must be before generic deepseek
    (r"deepseek", "deepseek"),
    (r"qwen", "qwen"),
    (r"llama", "llama"),
    (r"mistral|mixtral", "mistral"),
    (r"phi", "phi"),
    (r"gemma", "gemma"),
]

KNOWN_FAMILIES: List[str] = [
    "qwen", "deepseek", "deepseek-r1", "llama", "mistral", "phi", "gemma",
]

STANDARD_TASK_TYPES: List[str] = ["code", "test", "write", "review", "chat"]


def detect_family(model_id: str) -> str:
    """Detect model family from a model identifier.

    Case-insensitive. Returns 'unknown' if no pattern matches.
    """
    lower = model_id.lower()
    for pattern, family in _FAMILY_PATTERNS:
        if re.search(pattern, lower):
            return family
    return "unknown"


# ---------------------------------------------------------------------------
# Temperature matrix (from OPP-31 spec Appendix A, vendor-researched)
# ---------------------------------------------------------------------------
# Format: {family: {task_type: {param: value}}}

_KNOWLEDGE_BASE: Dict[str, Dict[str, Dict[str, float]]] = {
    "qwen": {
        "code":   {"temperature": 0.2, "top_p": 0.8, "top_k": 20},
        "test":   {"temperature": 0.3, "top_p": 0.8, "top_k": 20},
        "write":  {"temperature": 0.7, "top_p": 0.9, "top_k": 40},
        "review": {"temperature": 0.2, "top_p": 0.8, "top_k": 20},
        "chat":   {"temperature": 0.7, "top_p": 0.9, "top_k": 40},
    },
    "deepseek": {
        "code":   {"temperature": 0.0},
        "test":   {"temperature": 0.3},
        "write":  {"temperature": 1.0},
        "review": {"temperature": 0.3},
        "chat":   {"temperature": 1.3},
    },
    "deepseek-r1": {
        "code":   {"temperature": 0.6},
        "test":   {"temperature": 0.6},
        "write":  {"temperature": 0.6},
        "review": {"temperature": 0.6},
        "chat":   {"temperature": 0.6},
    },
    "llama": {
        "code":   {"temperature": 0.2},
        "test":   {"temperature": 0.3},
        "write":  {"temperature": 0.7},
        "review": {"temperature": 0.2},
        "chat":   {"temperature": 0.6},
    },
    "mistral": {
        "code":   {"temperature": 0.2},
        "test":   {"temperature": 0.2},
        "write":  {"temperature": 0.7},
        "review": {"temperature": 0.2},
        "chat":   {"temperature": 0.15},
    },
    "phi": {
        "code":   {"temperature": 0.0},
        "test":   {"temperature": 0.1},
        "write":  {"temperature": 0.7},
        "review": {"temperature": 0.2},
        "chat":   {"temperature": 0.7},
    },
    "gemma": {
        "code":   {"temperature": 0.5, "top_k": 64},
        "test":   {"temperature": 0.4, "top_k": 64},
        "write":  {"temperature": 1.0, "top_k": 64},
        "review": {"temperature": 0.4, "top_k": 64},
        "chat":   {"temperature": 1.0, "top_k": 64},
    },
}


# ---------------------------------------------------------------------------
# Critical constraints (override everything, per vendor docs)
# ---------------------------------------------------------------------------

_CRITICAL_CONSTRAINTS: Dict[str, Dict[str, float]] = {
    "deepseek-r1": {"min_temperature": 0.6},
    "phi": {},  # phi-reasoning has temp=0.8 but handled via overlay
}


def get_overlay(family: str, task_type: str) -> Dict[str, float]:
    """Get vendor-optimal param overlay for a family+task combination.

    Returns empty dict if family or task type is unknown.
    """
    family_data = _KNOWLEDGE_BASE.get(family, {})
    return dict(family_data.get(task_type, {}))


def get_critical_constraints(family: str) -> Dict[str, float]:
    """Get critical constraints that MUST override user settings.

    Returns empty dict if no constraints exist for the family.
    """
    return dict(_CRITICAL_CONSTRAINTS.get(family, {}))


__all__ = [
    "detect_family",
    "get_overlay",
    "get_critical_constraints",
    "KNOWN_FAMILIES",
    "STANDARD_TASK_TYPES",
]
