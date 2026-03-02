"""SSE streaming protocol constants."""

__all__ = [
    "SSE_DATA_PREFIX",
    "SSE_DONE_SENTINEL",
    "SSE_USAGE_KEY",
]

# OPP-12: SSE Streaming Configuration
SSE_DATA_PREFIX = "data: "
SSE_DONE_SENTINEL = "[DONE]"
SSE_USAGE_KEY = "usage"
