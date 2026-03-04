"""Tool configuration constants for Round G OPPs (OPP-32 through OPP-50)."""

SCHEMA_COERCION_ENABLED: bool = True

# OPP-44: Per-tool circuit breaker
CIRCUIT_BREAKER_THRESHOLD: int = 5
CIRCUIT_BREAKER_RESET_SECONDS: float = 60.0
CIRCUIT_BREAKER_ENABLED: bool = True

__all__: list[str] = [
    "SCHEMA_COERCION_ENABLED",
    "CIRCUIT_BREAKER_THRESHOLD",
    "CIRCUIT_BREAKER_RESET_SECONDS",
    "CIRCUIT_BREAKER_ENABLED",
]
