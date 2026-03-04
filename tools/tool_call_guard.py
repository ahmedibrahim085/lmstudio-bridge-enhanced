"""Pre-dispatch validation and per-tool circuit breaker (OPP-33 + OPP-44)."""

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from config.constants.tool_config import (
    CIRCUIT_BREAKER_ENABLED,
    CIRCUIT_BREAKER_RESET_SECONDS,
    CIRCUIT_BREAKER_THRESHOLD,
)

logger = logging.getLogger(__name__)


@dataclass
class BreakerState:
    status: str = "closed"  # "closed", "open", "half_open"
    failure_count: int = 0
    last_failure_time: float = 0.0
    opened_at: float | None = None
    probe_in_flight: bool = False


class ToolCallGuard:
    def __init__(self, tool_schemas: dict[str, dict[str, Any]] | None = None):
        self._schemas = tool_schemas or {}
        self._breaker_lock = threading.Lock()
        self._breaker_state: dict[str, BreakerState] = {}

    def validate_args(self, tool_name: str, args: dict[str, Any]) -> list[str]:
        """Validate args against schema. Returns list of error strings (empty=valid)."""
        schema = self._schemas.get(tool_name)
        if not schema:
            return []
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        errors: list[str] = []
        for param_name in required:
            if param_name not in args:
                errors.append(f"Missing required parameter: '{param_name}'")
            elif param_name in properties:
                expected_type = properties[param_name].get("type")
                if expected_type and not self._type_matches(args[param_name], expected_type):
                    errors.append(
                        f"Parameter '{param_name}' expected type '{expected_type}', "
                        f"got {type(args[param_name]).__name__}"
                    )
        return errors

    @staticmethod
    def _type_matches(value: Any, expected_type: str) -> bool:
        # In Python, bool is a subclass of int, so isinstance(True, int) is True.
        # For JSON Schema semantics, booleans must NOT match integer or number.
        if expected_type in ("integer", "number") and isinstance(value, bool):
            return False
        type_map: dict[str, type | tuple[type, ...]] = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        expected = type_map.get(expected_type)
        if expected is None:
            return True  # Unknown type, don't validate
        return isinstance(value, expected)

    def check_circuit(self, tool_name: str) -> tuple[bool, str | None]:
        """Check if tool call is allowed. Returns (allowed, reason)."""
        if not CIRCUIT_BREAKER_ENABLED:
            return True, None
        with self._breaker_lock:
            state = self._breaker_state.get(tool_name)
            if state is None:
                return True, None
            if state.status == "closed":
                return True, None
            if state.status == "open":
                elapsed = time.monotonic() - (state.opened_at or 0.0)
                if elapsed >= CIRCUIT_BREAKER_RESET_SECONDS:
                    state.status = "half_open"
                    state.probe_in_flight = True
                    return True, None  # Allow one probe
                return False, f"Circuit breaker OPEN for '{tool_name}' ({state.failure_count} failures)"
            if state.status == "half_open":
                if state.probe_in_flight:
                    return False, f"Probe already in-flight for '{tool_name}'"
                state.probe_in_flight = True
                return True, None  # Allow the probe call
            return True, None

    def record_success(self, tool_name: str) -> None:
        """Record a successful tool call; resets failure count and closes breaker."""
        with self._breaker_lock:
            state = self._breaker_state.get(tool_name)
            if state is not None:
                state.status = "closed"
                state.failure_count = 0
                state.opened_at = None
                state.probe_in_flight = False

    def record_failure(self, tool_name: str) -> None:
        """Record a failed tool call; opens breaker when threshold is reached."""
        with self._breaker_lock:
            state = self._breaker_state.get(tool_name)
            if state is None:
                state = BreakerState()
                self._breaker_state[tool_name] = state
            state.failure_count += 1
            state.last_failure_time = time.monotonic()
            state.probe_in_flight = False
            if state.failure_count >= CIRCUIT_BREAKER_THRESHOLD:
                if state.status in ("half_open", "closed"):
                    state.status = "open"
                    state.opened_at = time.monotonic()
                logger.warning(
                    "Circuit breaker OPEN for '%s' after %d failures",
                    tool_name,
                    state.failure_count,
                )


__all__ = ["ToolCallGuard", "BreakerState"]
