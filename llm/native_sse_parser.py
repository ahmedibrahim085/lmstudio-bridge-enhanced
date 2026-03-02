"""Native SSE parser for LM Studio /api/v1/chat streaming responses.

Parses the native SSE format that uses both event: and data: fields,
supporting all 19 LM Studio event types.

SSE wire format (native /api/v1/chat)
--------------------------------------
Unlike the OpenAI-compat endpoints that only emit ``data:`` lines, the
native chat endpoint emits both an ``event:`` line and a ``data:`` line
per event block, separated by a blank line:

    event: chat.start
    data: {"model": "test-model"}

    event: message.delta
    data: {"content": "Hello"}

    event: chat.end
    data: {"result": {"content": "Full response"}}

Each block:
- ``event: <type>`` — one of the 19 NATIVE_EVENT_* types
- ``data: <json>``  — JSON payload
- blank line        — event boundary

Usage
-----
    import requests
    from llm.native_sse_parser import parse_native_sse_stream

    resp = requests.post(url, json=payload, stream=True)
    for event in parse_native_sse_stream(resp):
        if event.event_type == "error":
            handle_error(event.data)
        elif event.event_type == "message.delta":
            process_chunk(event.data)
"""

import json
import logging
from collections.abc import Generator
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

__all__ = [
    "NativeSSEEvent",
    "parse_native_sse_stream",
]


@dataclass(frozen=True)
class NativeSSEEvent:
    """A single parsed native SSE event.

    Attributes:
        event_type: Event type string (e.g., "chat.start", "message.delta").
            Defaults to "message" when the ``event:`` field is absent.
        data: Parsed JSON payload as a dict.
    """

    event_type: str
    data: dict


def parse_native_sse_stream(
    response,
) -> Generator[NativeSSEEvent, None, None]:
    """Parse a native SSE streaming response into NativeSSEEvent objects.

    The generator yields one NativeSSEEvent per SSE block. Each block
    consists of an optional ``event:`` line, a ``data:`` line, and a blank
    separator.

    Error handling:
    - Invalid JSON -> yields NativeSSEEvent(event_type="error", data={...})
    - Network/iteration errors -> yields error event, does not raise
    - Missing ``event:`` field -> uses "message" as the default type
    - Unknown event types pass through without filtering

    Args:
        response: An HTTP response object with an ``iter_lines()`` method.
            Compatible with ``requests.Response`` (stream=True) and any
            mock that provides the same interface.

    Yields:
        NativeSSEEvent for each complete SSE block encountered in the stream.
    """
    try:
        current_event_type: Optional[str] = None

        for raw_line in response.iter_lines():
            # Decode bytes to str if needed (requests yields bytes by default)
            if isinstance(raw_line, bytes):
                line = raw_line.decode("utf-8", errors="replace")
            else:
                line = raw_line

            # Blank line = event boundary; reset pending event type
            if not line.strip():
                current_event_type = None
                continue

            # Parse event: field — captures the type for the next data: line
            if line.startswith("event:"):
                current_event_type = line.split(":", 1)[1].strip()
                continue

            # Parse data: field — emit one NativeSSEEvent per data line
            if line.startswith("data:"):
                payload = line.split(":", 1)[1].strip()

                # Fall back to "message" when no preceding event: line
                event_type = current_event_type if current_event_type else "message"

                try:
                    data = json.loads(payload)
                except json.JSONDecodeError as exc:
                    logger.warning("Native SSE JSON parse error: %s", exc)
                    yield NativeSSEEvent(
                        event_type="error",
                        data={"error": f"json parse error: {exc}", "raw": payload},
                    )
                    current_event_type = None
                    continue

                yield NativeSSEEvent(event_type=event_type, data=data)
                current_event_type = None
                continue

            # Skip comment lines (starting with :) and any unrecognised fields

    except Exception as exc:  # noqa: BLE001
        logger.error("Native SSE stream error: %s", exc)
        yield NativeSSEEvent(
            event_type="error",
            data={"error": str(exc)},
        )
