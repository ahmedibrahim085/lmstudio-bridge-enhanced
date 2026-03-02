"""Validation bounds, schema limits, and branching constraints."""

__all__ = [
    "MIN_TEMPERATURE",
    "MAX_TEMPERATURE",
    "MIN_MAX_TOKENS",
    "MAX_MAX_TOKENS",
    "MIN_MIN_P",
    "MAX_MIN_P",
    "MIN_TOP_K",
    "MAX_TOP_K",
    "MIN_THINKING_BUDGET_TOKENS",
    "MAX_THINKING_BUDGET_TOKENS",
    "MAX_JSON_SCHEMA_DEPTH",
    "MAX_JSON_SCHEMA_PROPERTIES",
    "DEFAULT_JSON_SCHEMA_STRICT",
    "STRUCTURED_OUTPUT_TYPES",
    "DEFAULT_MAX_ROUNDS",
    "E2E_TEST_MAX_ROUNDS",
    "MAX_CONSECUTIVE_ERRORS",
    "MAX_BRANCH_DEPTH",
    "MAX_BRANCHES_PER_TREE",
    "DEFAULT_BRANCH_PREFIX",
]

# H-10: Input validation bounds for MCP tool parameters
MIN_TEMPERATURE = 0.0
MAX_TEMPERATURE = 2.0
MIN_MAX_TOKENS = 1
MAX_MAX_TOKENS = 131072  # 128K context — upper bound for any model

# Advanced sampling parameters (OPP-26)
MIN_MIN_P = 0.0
MAX_MIN_P = 1.0
MIN_TOP_K = 1
MAX_TOP_K = 1000

# OPP-14: Extended thinking budget bounds
MIN_THINKING_BUDGET_TOKENS = 128
MAX_THINKING_BUDGET_TOKENS = 32768

# Structured output configuration (LM Studio v0.3.32+)
MAX_JSON_SCHEMA_DEPTH = 10
MAX_JSON_SCHEMA_PROPERTIES = 100
DEFAULT_JSON_SCHEMA_STRICT = True
STRUCTURED_OUTPUT_TYPES = ["json_schema", "json_object"]

# Autonomous execution
DEFAULT_MAX_ROUNDS = 10000  # High limit - let LLM work until task complete
E2E_TEST_MAX_ROUNDS = 5  # Budget: 5 * DEFAULT_LLM_TIMEOUT(58s) = 290s < LONG_TEST_TIMEOUT(300s)
MAX_CONSECUTIVE_ERRORS = 3  # Abort autonomous loop after this many consecutive errors

# OPP-15: Conversation branching
MAX_BRANCH_DEPTH = 50
MAX_BRANCHES_PER_TREE = 100
DEFAULT_BRANCH_PREFIX = "branch"
