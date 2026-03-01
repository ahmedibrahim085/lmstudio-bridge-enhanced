"""Model Loading Inventory — tracks every model load/unload with audit trail.

Provides structured tracking of model lifecycle during test sessions:
- Records load/unload events with metadata (timestamp, reason, test_id, scope, phase)
- Scoped cleanup (unload by scope: function, class, module, session)
- JSON persistence per session for post-mortem debugging
- All unload methods are IDEMPOTENT (double-unload = no-op)

Architecture:
- ModelLoadRecord: dataclass for a single load event
- ModelLoadInventory: manages records, active models, scoped cleanup, JSON persistence
- Delegates actual unloading to LMSHelper.unload_model()
"""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from config.constants import MODEL_INVENTORY_DIR

logger = logging.getLogger(__name__)


@dataclass
class ModelLoadRecord:
    """Tracks a single model load event."""

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
    """Tracks model loads/unloads with full audit trail and JSON persistence.

    Thread-safety: NOT thread-safe. Designed for single-threaded pytest execution.
    Idempotency: All unload methods check `unloaded` flag before calling LMSHelper.
    """

    def __init__(self, inventory_dir: str | None = None) -> None:
        self._records: list[ModelLoadRecord] = []
        self._active: dict[str, ModelLoadRecord] = {}
        self._session_id: str = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
        self._inventory_dir: Path = Path(inventory_dir or MODEL_INVENTORY_DIR)

    def record_load(
        self,
        model_name: str,
        reason: str = "",
        test_id: str = "",
        scope: str = "",
        phase: str = "",
        **meta: object,
    ) -> None:
        """Record a model load event.

        If the model is already active, a new record is appended to the audit
        trail and the active entry is updated (latest scope/reason wins).
        """
        record = ModelLoadRecord(
            model_name=model_name,
            loaded_at=datetime.now(tz=timezone.utc).isoformat(),
            reason=reason,
            test_id=test_id,
            scope=scope,
            phase=phase,
            metadata=dict(meta),
        )
        self._records.append(record)
        self._active[model_name] = record

    def record_unload(self, model_name: str) -> None:
        """Mark a model as unloaded. IDEMPOTENT: no-op if already unloaded.

        Calls LMSHelper.unload_model() only if the model is still active.
        """
        record = self._active.get(model_name)
        if record is None or record.unloaded:
            return  # Already unloaded or never tracked — no-op

        from utils.lms_helper import LMSHelper

        LMSHelper.unload_model(model_name)
        record.unloaded = True
        record.unloaded_at = datetime.now(tz=timezone.utc).isoformat()
        del self._active[model_name]

    def get_active_for_scope(self, scope: str, test_id: str | None = None) -> list[str]:
        """Return model names loaded at the given scope.

        Args:
            scope: The scope to filter by (session, module, class, function).
            test_id: Optional test node ID for finer filtering.
        """
        results: list[str] = []
        for name, record in self._active.items():
            if record.scope == scope:
                if test_id is None or record.test_id == test_id:
                    results.append(name)
        return results

    def unload_scope(self, scope: str, test_id: str | None = None) -> int:
        """Unload all active models loaded at the given scope. Returns count.

        IDEMPOTENT: Skips already-unloaded models. Continues on failure.
        """
        from utils.lms_helper import LMSHelper

        to_unload = self.get_active_for_scope(scope, test_id)
        count = 0
        for model_name in to_unload:
            record = self._active.get(model_name)
            if record is None or record.unloaded:
                continue
            try:
                LMSHelper.unload_model(model_name)
                record.unloaded = True
                record.unloaded_at = datetime.now(tz=timezone.utc).isoformat()
                del self._active[model_name]
                count += 1
            except Exception as e:
                logger.warning(f"Inventory: failed to unload '{model_name}': {e}")
        return count

    def unload_all(self) -> int:
        """Unload all active models. Final sweep at session teardown. Returns count.

        IDEMPOTENT: Skips already-unloaded models. Continues on failure.
        """
        from utils.lms_helper import LMSHelper

        to_unload = list(self._active.keys())
        count = 0
        for model_name in to_unload:
            record = self._active.get(model_name)
            if record is None or record.unloaded:
                continue
            try:
                LMSHelper.unload_model(model_name)
                record.unloaded = True
                record.unloaded_at = datetime.now(tz=timezone.utc).isoformat()
                del self._active[model_name]
                count += 1
            except Exception as e:
                logger.warning(f"Inventory: failed to unload '{model_name}': {e}")
        return count

    def save(self) -> None:
        """Persist full audit trail to JSON. Creates directory on demand."""
        self._inventory_dir.mkdir(parents=True, exist_ok=True)
        filepath = self._inventory_dir / f"{self._session_id}.json"

        data = {
            "session_id": self._session_id,
            "saved_at": datetime.now(tz=timezone.utc).isoformat(),
            "records": [asdict(r) for r in self._records],
            "summary": self.summary(),
        }

        filepath.write_text(json.dumps(data, indent=2, default=str))
        logger.info(f"Inventory saved: {filepath} ({len(self._records)} records)")

    def summary(self) -> dict:
        """Return summary for logging: total, active, unloaded, by-scope."""
        by_scope: dict[str, int] = {}
        for record in self._records:
            scope = record.scope or "unknown"
            by_scope[scope] = by_scope.get(scope, 0) + 1

        return {
            "total": len(self._records),
            "active": len(self._active),
            "unloaded": sum(1 for r in self._records if r.unloaded),
            "by_scope": by_scope,
        }
