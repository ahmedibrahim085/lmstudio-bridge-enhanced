"""Test infrastructure constants — timeouts, inventory, and env var overrides."""

__all__ = [
    "TEST_TIMEOUT",
    "SHORT_TEST_TIMEOUT",
    "LONG_TEST_TIMEOUT",
    "SLOW_TEST_THRESHOLD_SECONDS",
    "CACHE_VALIDATION_TARGET_MS",
    "MEMORY_OVERHEAD_TARGET_MB",
    "MODEL_INVENTORY_DIR",
    "MODEL_INVENTORY_SCOPE_SESSION",
    "MODEL_INVENTORY_SCOPE_MODULE",
    "MODEL_INVENTORY_SCOPE_CLASS",
    "MODEL_INVENTORY_SCOPE_FUNCTION",
    "MODEL_INVENTORY_REASON_FIXTURE",
    "MODEL_INVENTORY_REASON_LIFECYCLE",
    "MODEL_INVENTORY_REASON_DIRECT",
    "TEST_MODEL_TTL",
    "TEST_MAX_LOADED_MODELS",
    "LMS_TEST_ENV_VAR_PREFIX",
    "LMS_TEST_ENV_VARS",
    "WAKE_UP_PING_MAX_TOKENS",
    "LMSTUDIO_TESTING_ENV_VAR",
    "LMSTUDIO_TESTING_DEFAULT_MODEL",
]

# Test Configuration
TEST_TIMEOUT = 120  # 2 minutes
SHORT_TEST_TIMEOUT = 30
LONG_TEST_TIMEOUT = 300
SLOW_TEST_THRESHOLD_SECONDS = 30

# Performance Targets (for testing)
CACHE_VALIDATION_TARGET_MS = 0.1  # Target: < 0.1ms for cached validation
MEMORY_OVERHEAD_TARGET_MB = 10.0  # Target: < 10 MB memory overhead

# Model Loading Inventory — tracks every model load/unload with audit trail
MODEL_INVENTORY_DIR = ".omc/model-inventory"
MODEL_INVENTORY_SCOPE_SESSION = "session"
MODEL_INVENTORY_SCOPE_MODULE = "module"
MODEL_INVENTORY_SCOPE_CLASS = "class"
MODEL_INVENTORY_SCOPE_FUNCTION = "function"
MODEL_INVENTORY_REASON_FIXTURE = "fixture"
MODEL_INVENTORY_REASON_LIFECYCLE = "ensure_model_for_phase"
MODEL_INVENTORY_REASON_DIRECT = "direct"

# TTL (seconds) for models loaded by the test session
TEST_MODEL_TTL = 1800  # 30 minutes

# Maximum number of models the test session will keep loaded simultaneously
TEST_MAX_LOADED_MODELS = 3

# Env var overrides for explicit model selection in tests (D-13)
LMS_TEST_ENV_VAR_PREFIX = "LMS_TEST"
LMS_TEST_ENV_VARS: dict[str, str] = {
    "chat": "LMS_TEST_CHAT_MODEL",
    "thinking": "LMS_TEST_THINKING_MODEL",
    "coding": "LMS_TEST_CODING_MODEL",
    "vision": "LMS_TEST_VISION_MODEL",
    "embedding": "LMS_TEST_EMBEDDING_MODEL",
}

# Wake-up ping constants (D-5)
WAKE_UP_PING_MAX_TOKENS = 1

# Testing mode — env var to skip HTTP auto-detection in get_config()
LMSTUDIO_TESTING_ENV_VAR = "LMSTUDIO_TESTING"
LMSTUDIO_TESTING_DEFAULT_MODEL = "default"
