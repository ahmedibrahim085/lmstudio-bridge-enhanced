"""LM Studio server, logging, and environment variable constants."""

__all__ = [
    "DEFAULT_LMSTUDIO_HOST",
    "DEFAULT_LMSTUDIO_PORT",
    "DEFAULT_LMSTUDIO_BASE_URL",
    "HEALTH_CHECK_TIMEOUT",
    "HEALTH_CHECK_INTERVAL",
    "DIAGNOSTICS_ENDPOINT",
    "SYSTEM_STATUS_ENDPOINT",
    "SERVER_TYPE_HEADER",
    "SERVER_TYPE_GUI",
    "SERVER_TYPE_HEADLESS",
    "LLMSTER_PROCESS_NAME",
    "ENABLE_CACHING",
    "ENABLE_RETRY",
    "ENABLE_LOGGING",
    "ENABLE_METRICS",
    "LOG_LEVEL",
    "LOG_FORMAT",
    "DEFAULT_LOG_DIR",
    "DEFAULT_CACHE_DIR",
    "DEFAULT_CONFIG_DIR",
    "ENV_LMSTUDIO_HOST",
    "ENV_LMSTUDIO_PORT",
    "ENV_LOG_LEVEL",
    "ENV_MAX_RETRIES",
    "ENV_REQUEST_TIMEOUT",
    "ENV_MCP_FILESYSTEM_ROOT",
]

# LM Studio Server Configuration
DEFAULT_LMSTUDIO_HOST = "localhost"
DEFAULT_LMSTUDIO_PORT = 1234
DEFAULT_LMSTUDIO_BASE_URL = f"http://{DEFAULT_LMSTUDIO_HOST}:{DEFAULT_LMSTUDIO_PORT}"

# OPP-18: Headless deployment — Health Check Configuration
HEALTH_CHECK_TIMEOUT = 5.0
HEALTH_CHECK_INTERVAL = 30.0

# LM Studio diagnostics endpoint (available in 0.4.x headless/GUI)
DIAGNOSTICS_ENDPOINT = "/api/v1/diagnostics"
SYSTEM_STATUS_ENDPOINT = "/api/v1/system/status"

# HTTP response header that identifies the LM Studio server variant
SERVER_TYPE_HEADER = "x-lmstudio-server-type"
SERVER_TYPE_GUI = "gui"
SERVER_TYPE_HEADLESS = "headless"

# Process name used by the llmster headless daemon
LLMSTER_PROCESS_NAME = "llmster"

# Feature Flags
ENABLE_CACHING = True
ENABLE_RETRY = True
ENABLE_LOGGING = True
ENABLE_METRICS = True

# Logging
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# File Paths
DEFAULT_LOG_DIR = "logs"
DEFAULT_CACHE_DIR = ".cache"
DEFAULT_CONFIG_DIR = "config"

# Environment Variable Names
ENV_LMSTUDIO_HOST = "LMSTUDIO_HOST"
ENV_LMSTUDIO_PORT = "LMSTUDIO_PORT"
ENV_LOG_LEVEL = "LOG_LEVEL"
ENV_MAX_RETRIES = "MAX_RETRIES"
ENV_REQUEST_TIMEOUT = "REQUEST_TIMEOUT"
ENV_MCP_FILESYSTEM_ROOT = "MCP_FILESYSTEM_ROOT"
