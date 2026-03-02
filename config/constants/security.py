"""SSRF protection constants — allowed schemes and blocked IP ranges."""

__all__ = [
    "ALLOWED_URL_SCHEMES",
    "BLOCKED_IP_PREFIXES",
    "BLOCKED_IP_RANGES_172",
    "BLOCKED_HOSTNAMES",
    "ENV_LMS_API_KEY",
    "AUTH_HEADER_PREFIX",
]

ALLOWED_URL_SCHEMES = ("http", "https")
BLOCKED_IP_PREFIXES = (
    "127.", "10.", "0.", "169.254.",
    "192.168.",
)
BLOCKED_IP_RANGES_172 = range(16, 32)  # 172.16.0.0 - 172.31.255.255
BLOCKED_HOSTNAMES = ("localhost", "localhost.localdomain", "::1")

# API authentication (OPP-28)
ENV_LMS_API_KEY = "LMS_API_KEY"
AUTH_HEADER_PREFIX = "Bearer"
