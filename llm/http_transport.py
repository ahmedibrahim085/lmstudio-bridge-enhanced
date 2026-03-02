"""HTTP transport layer for LLM sub-clients.

Owns the requests.Session lifecycle, connection pooling, and endpoint
resolution. All sub-clients receive a reference to a single HTTPTransport
instance — they never create their own sessions.
"""

import logging
import os
from typing import NoReturn, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import get_config
from config.constants import (
    AUTH_HEADER_PREFIX,
    ENV_LMS_API_KEY,
    HEALTH_CHECK_TIMEOUT,
    HTTP_RETRY_BACKOFF_FACTOR,
    HTTP_RETRY_TOTAL,
    LLM_POOL_CONNECTIONS,
    LLM_POOL_MAXSIZE,
    MODEL_LIST_TIMEOUT,
)
from llm.exceptions import (
    LLMAuthenticationError,
    LLMConnectionError,
    LLMError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
)

logger = logging.getLogger(__name__)


def handle_request_exception(e: Exception, operation: str = "LLM request") -> NoReturn:
    """Convert requests exceptions to our custom exception hierarchy.

    Args:
        e: The exception from requests library
        operation: Description of the operation that failed

    Raises:
        LLMTimeoutError: For timeout errors
        LLMConnectionError: For connection errors
        LLMRateLimitError: For rate limit errors (HTTP 429)
        LLMResponseError: For other HTTP errors
        LLMError: For other unexpected errors
    """
    if isinstance(e, requests.exceptions.Timeout):
        raise LLMTimeoutError(
            f"{operation} timed out. LM Studio may be overloaded or unresponsive.",
            original_exception=e,
        )

    elif isinstance(e, requests.exceptions.ConnectionError):
        raise LLMConnectionError(
            f"{operation} failed: Could not connect to LM Studio. "
            f"Is LM Studio running?",
            original_exception=e,
        )

    elif isinstance(e, requests.exceptions.HTTPError):
        status_code = e.response.status_code if e.response is not None else None

        if status_code == 401:
            raise LLMAuthenticationError(
                f"{operation} failed: Authentication failed (HTTP 401). "
                f"Check your API key.",
                original_exception=e,
            )
        elif status_code == 429:
            raise LLMRateLimitError(
                f"{operation} failed: Rate limit exceeded. Please try again later.",
                original_exception=e,
            )
        elif status_code == 500:
            raise LLMResponseError(
                f"{operation} failed: LM Studio internal error (HTTP 500). "
                f"This is usually transient - retry may succeed.",
                original_exception=e,
            )
        elif status_code == 404:
            raise LLMResponseError(
                f"{operation} failed: Endpoint not found (HTTP 404). "
                f"Check that LM Studio API is running correctly.",
                original_exception=e,
            )
        else:
            raise LLMResponseError(
                f"{operation} failed: HTTP {status_code} error.",
                original_exception=e,
            )

    elif isinstance(e, requests.exceptions.RequestException):
        raise LLMError(
            f"{operation} failed: {str(e)}",
            original_exception=e,
        )

    else:
        raise LLMError(
            f"{operation} failed with unexpected error: {str(e)}",
            original_exception=e,
        )


class HTTPTransport:
    """Manages HTTP session, connection pooling, and endpoint resolution.

    Attributes:
        api_base: Base URL for the LM Studio API (e.g., http://localhost:1234/v1)
        model: Default model identifier
        session: The requests.Session used for all HTTP calls
    """

    def __init__(
        self,
        api_base: Optional[str] = None,
        model: Optional[str] = None,
        session: Optional["requests.Session"] = None,
        api_key: Optional[str] = None,
    ):
        config = get_config()
        self.api_base = api_base or config.lmstudio.api_base
        self.model = model or config.lmstudio.default_model

        if session is not None:
            self.session = session
            self._owns_session = False
        else:
            self.session = requests.Session()
            self._owns_session = True
            adapter = HTTPAdapter(
                pool_connections=LLM_POOL_CONNECTIONS,
                pool_maxsize=LLM_POOL_MAXSIZE,
                max_retries=Retry(
                    total=HTTP_RETRY_TOTAL,
                    backoff_factor=HTTP_RETRY_BACKOFF_FACTOR,
                ),
            )
            self.session.mount("http://", adapter)
            self.session.mount("https://", adapter)

        # Resolve API key: constructor > env var > None
        resolved_key = api_key if api_key is not None else os.environ.get(ENV_LMS_API_KEY)
        if resolved_key is not None:
            resolved_key = resolved_key.strip()
        if resolved_key:
            self.session.headers["Authorization"] = f"{AUTH_HEADER_PREFIX} {resolved_key}"
            self._has_api_key = True
        else:
            self._has_api_key = False

    def __repr__(self) -> str:
        auth = "key=***" if self._has_api_key else "no-auth"
        return f"HTTPTransport(api_base={self.api_base!r}, model={self.model!r}, {auth})"

    def close(self) -> None:
        """Close the HTTP session if owned."""
        if self.session is not None and self._owns_session:
            self.session.close()
            self.session = None
            logger.debug("HTTPTransport session closed")

    def get_endpoint(self, path: str) -> str:
        """Get full URL for an endpoint."""
        return f"{self.api_base}/{path.lstrip('/')}"

    def health_check(self) -> bool:
        """Check if LM Studio API is accessible."""
        try:
            response = self.session.get(
                self.get_endpoint("models"), timeout=HEALTH_CHECK_TIMEOUT
            )
            return response.status_code == 200
        except Exception:
            return False


__all__ = [
    "HTTPTransport",
    "handle_request_exception",
]
