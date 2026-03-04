"""Timeout, retry, connection pool, cache TTL, and delay constants."""

__all__ = [
    "DEFAULT_REQUEST_TIMEOUT",
    "DEFAULT_CONNECTION_TIMEOUT",
    "DEFAULT_READ_TIMEOUT",
    "DEFAULT_LLM_TIMEOUT",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_RETRY_BASE_DELAY",
    "DEFAULT_RETRY_MAX_DELAY",
    "LLM_POOL_CONNECTIONS",
    "LLM_POOL_MAXSIZE",
    "IMAGE_POOL_CONNECTIONS",
    "IMAGE_POOL_MAXSIZE",
    "HTTP_RETRY_TOTAL",
    "HTTP_RETRY_BACKOFF_FACTOR",
    "IMAGE_DOWNLOAD_TIMEOUT",
    "LMS_CLI_CHECK_TIMEOUT",
    "LMS_CLI_LOAD_TIMEOUT",
    "LMS_CLI_UNLOAD_TIMEOUT",
    "LMS_CLI_DEFAULT_TIMEOUT",
    "LMS_CLI_PS_TIMEOUT",
    "LMS_REST_LOAD_TIMEOUT",
    "LMS_REST_DEFAULT_TIMEOUT",
    "MODEL_CACHE_TTL_SECONDS",
    "MODEL_VALIDATION_TIMEOUT",
    "MODEL_LIST_TIMEOUT",
    "MODELS_FETCH_CACHE_TTL",
    "LMS_REST_MODELS_CACHE_TTL",
    "MODEL_REACTIVATION_DELAY",
    "MODEL_LOADING_DELAY",
    "JIT_TTL_DEFAULT",
    "JIT_TTL_EMBEDDING",
    "JIT_TTL_AUTONOMOUS",
    "POLL_JIT_GUARD_TTL",
    "DEFAULT_AUTONOMOUS_TIMEOUT",
    "STREAM_READ_TIMEOUT",
    "WAKE_UP_PING_TIMEOUT",
    "DEFAULT_MCP_TIMEOUT",
]

# Timeout Configuration (seconds)
DEFAULT_REQUEST_TIMEOUT = 120.0
DEFAULT_CONNECTION_TIMEOUT = 10.0
DEFAULT_READ_TIMEOUT = 300.0
# Default timeout for LLM API calls via LLMClient
# Set to 58s to accommodate slower models (Magistral: 45-46s response time)
# Still safely under Claude Code's 60-second MCP timeout limit
# See: https://github.com/anthropics/claude-code/issues/7575
DEFAULT_LLM_TIMEOUT = 58

# Retry Configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_BASE_DELAY = 1.0
DEFAULT_RETRY_MAX_DELAY = 60.0

# HTTP Connection Pool Configuration
LLM_POOL_CONNECTIONS = 10       # Pool connections for LLMClient HTTP adapter
LLM_POOL_MAXSIZE = 20           # Pool max size for LLMClient HTTP adapter
IMAGE_POOL_CONNECTIONS = 5      # Pool connections for image_utils HTTP adapter
IMAGE_POOL_MAXSIZE = 10         # Pool max size for image_utils HTTP adapter
HTTP_RETRY_TOTAL = 3            # urllib3 Retry total attempts
HTTP_RETRY_BACKOFF_FACTOR = 0.3  # urllib3 Retry exponential backoff factor

# Image Download
IMAGE_DOWNLOAD_TIMEOUT = 30     # Timeout for downloading images from URLs

# LMS CLI Timeouts (seconds) — used in subprocess.run calls
LMS_CLI_CHECK_TIMEOUT = 5       # Quick CLI availability check (lms ps)
LMS_CLI_LOAD_TIMEOUT = 60       # Model loading via CLI (can take time)
LMS_CLI_UNLOAD_TIMEOUT = 30     # Model unloading via CLI
LMS_CLI_DEFAULT_TIMEOUT = 30    # General CLI operations (discover, etc.)
LMS_CLI_PS_TIMEOUT = 10         # lms ps --json / lms server status --json

# LM Studio REST API timeouts
LMS_REST_LOAD_TIMEOUT = 120.0   # 2 minutes for model loading
LMS_REST_DEFAULT_TIMEOUT = 10.0  # 10 seconds for quick checks

# Model Validation
MODEL_CACHE_TTL_SECONDS = 60    # 60-second cache for model validation
MODEL_VALIDATION_TIMEOUT = 5.0
MODEL_LIST_TIMEOUT = 10

# Cache TTLs
MODELS_FETCH_CACHE_TTL = 30     # seconds
LMS_REST_MODELS_CACHE_TTL = 30  # seconds

# Model loading delays (seconds) — used in sync LMSHelper methods
MODEL_REACTIVATION_DELAY = 1    # Delay after reactivation API call before verifying
MODEL_LOADING_DELAY = 2         # Delay for model loading/verification transitions

# JIT (Just-In-Time) Model Loading TTL (seconds)
JIT_TTL_DEFAULT = 1800          # 30 minutes for general requests
JIT_TTL_EMBEDDING = 900         # 15 minutes for embedding requests (shorter-lived)
JIT_TTL_AUTONOMOUS = 10800      # 3 hours for autonomous tasks (long-running)

# JIT Poll Guard (OPP-43) — skip is_model_loaded if confirmed within this window
# 2× LMS_REST_MODELS_CACHE_TTL (30s) — at most 1 HTTP GET per model per 60s
POLL_JIT_GUARD_TTL = 60

# Autonomous execution timeout
DEFAULT_AUTONOMOUS_TIMEOUT = 600  # 10 minutes per autonomous task

# Streaming timeout
STREAM_READ_TIMEOUT = 300.0

# Wake-up ping
WAKE_UP_PING_TIMEOUT = 10       # seconds

# MCP timeout
DEFAULT_MCP_TIMEOUT = 30.0
