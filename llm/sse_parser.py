#!/usr/bin/env python3
"""
SSE (Server-Sent Events) stream parser for LM Studio streaming responses.

This module provides a generator function that parses the SSE wire format
produced by LM Studio's streaming endpoints:
- /v1/chat/completions  (stream=True)
- /v1/responses         (stream=True)
- /v1/messages          (stream=True, Anthropic-compat)

SSE wire format recap
---------------------
Each event is one or more lines terminated by a blank line:

    data: {"id":"c1","choices":[...]}\n
    \n
    data: [DONE]\n
    \n

Only the ``data:`` field is used here.  ``event:``, ``id:``, and
``retry:`` fields are ignored.

Usage
-----
    import requests
    from llm.sse_parser import parse_sse_stream

    resp = requests.post(url, json=payload, stream=True)
    for event in parse_sse_stream(resp):
        if "error" in event:
            handle_error(event)
        else:
            process_chunk(event)
"""

import json
import logging
from collections.abc import Generator
from typing import Any

import requests

from config.constants import SSE_DATA_PREFIX, SSE_DONE_SENTINEL

logger = logging.getLogger(__name__)

__all__ = [
    "parse_sse_stream",
]


def parse_sse_stream(
    response: requests.Response,
) -> Generator[dict[str, Any], None, None]:
    """Parse an SSE streaming response and yield each event as a dict.

    The generator stops when the ``[DONE]`` sentinel is encountered or the
    response body is exhausted.  Network errors that occur mid-stream are
    caught and yielded as error events so callers can handle them gracefully
    without a bare ``try/except`` at the call site.

    Args:
        response: An open ``requests.Response`` obtained with
            ``stream=True``.  The caller is responsible for calling
            ``response.raise_for_status()`` before passing it here.

    Yields:
        dict: Parsed JSON payload for each ``data:`` line, or an error
        dict ``{"error": "<message>"}`` on network / parse failures.

    Example::

        resp = session.post(url, json=payload, stream=True, timeout=300)
        resp.raise_for_status()
        for chunk in parse_sse_stream(resp):
            if "error" in chunk:
                log.error("Stream error: %s", chunk["error"])
                break
            process(chunk)
    """
    try:
        for raw_line in response.iter_lines():
            # iter_lines() returns bytes or str depending on encoding
            if isinstance(raw_line, bytes):
                line = raw_line.decode("utf-8", errors="replace")
            else:
                line = raw_line

            # Skip blank / whitespace-only lines (SSE field separators)
            if not line.strip():
                continue

            # Skip non-data fields (event:, id:, retry:, comments)
            if not line.startswith(SSE_DATA_PREFIX):
                continue

            # Extract the payload after "data: "
            payload = line[len(SSE_DATA_PREFIX):]

            # Stop on [DONE] sentinel — do NOT yield it
            if payload.strip() == SSE_DONE_SENTINEL:
                return

            # Parse JSON and yield
            try:
                yield json.loads(payload)
            except json.JSONDecodeError as exc:
                logger.warning("SSE parse error on line %r: %s", line, exc)
                yield {"error": f"json parse error: {exc}"}

    except (
        requests.exceptions.ConnectionError,
        requests.exceptions.ChunkedEncodingError,
        requests.exceptions.StreamConsumedError,
    ) as exc:
        logger.error("SSE stream connection error: %s", exc)
        yield {"error": str(exc)}
