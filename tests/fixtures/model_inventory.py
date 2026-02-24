"""Model Loading Inventory — stub for TDD RED phase.

Full implementation in GREEN phase. This stub provides importable classes
so that RED tests can be collected and fail on assertions, not ImportError.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ModelLoadRecord:
    """Tracks a single model load event. Fields defined; logic in GREEN."""

    model_name: str = ""
    loaded_at: str = ""
    reason: str = ""
    test_id: str = ""
    scope: str = ""
    phase: str = ""
    metadata: dict = field(default_factory=dict)
    unloaded: bool = False
    unloaded_at: str | None = None


class ModelLoadInventory:
    """Tracks model loads/unloads with audit trail. Stub — methods not implemented."""

    pass
