"""Tool configuration constants for Round G OPPs (OPP-32 through OPP-50)."""

SCHEMA_COERCION_ENABLED: bool = True

# OPP-44: Per-tool circuit breaker
CIRCUIT_BREAKER_THRESHOLD: int = 5
CIRCUIT_BREAKER_RESET_SECONDS: float = 60.0
CIRCUIT_BREAKER_ENABLED: bool = True

# OPP-37: Orphan detection timeout
ORPHAN_TIMEOUT_SECONDS: float = 120.0

# OPP-40: Tool result cache
TOOL_RESULT_CACHE_TTL: float = 120.0
TOOL_RESULT_CACHE_MAX_SIZE: int = 200
TOOL_RESULT_CACHE_ALLOWLIST: frozenset[str] = frozenset({
    "list_directory",
    "read_file",
    "read_text_file",
    "search_files",
    "get_file_info",
    "directory_tree",
    "list_allowed_directories",
})

# OPP-45: Per-model error budget with advisory demotion
ERROR_BUDGET_WINDOW_SECONDS: float = 300.0
ERROR_BUDGET_THRESHOLD: float = 0.3
DEMOTION_COOLDOWN_SECONDS: float = 120.0

# OPP-46: Adaptive timeout based on observed response times
ADAPTIVE_TIMEOUT_ENABLED: bool = True
ADAPTIVE_TIMEOUT_MULTIPLIER: float = 1.5
ADAPTIVE_TIMEOUT_MIN_OBSERVATIONS: int = 10

# OPP-50: Tool schema dedup experiment — omit tool schemas on follow-up turns
TOOL_SCHEMA_DEDUP_ENABLED: bool = False

__all__: list[str] = [
    "SCHEMA_COERCION_ENABLED",
    "CIRCUIT_BREAKER_THRESHOLD",
    "CIRCUIT_BREAKER_RESET_SECONDS",
    "CIRCUIT_BREAKER_ENABLED",
    "ORPHAN_TIMEOUT_SECONDS",
    "TOOL_RESULT_CACHE_TTL",
    "TOOL_RESULT_CACHE_MAX_SIZE",
    "TOOL_RESULT_CACHE_ALLOWLIST",
    "ERROR_BUDGET_WINDOW_SECONDS",
    "ERROR_BUDGET_THRESHOLD",
    "DEMOTION_COOLDOWN_SECONDS",
    "ADAPTIVE_TIMEOUT_ENABLED",
    "ADAPTIVE_TIMEOUT_MULTIPLIER",
    "ADAPTIVE_TIMEOUT_MIN_OBSERVATIONS",
    "TOOL_SCHEMA_DEDUP_ENABLED",
]
