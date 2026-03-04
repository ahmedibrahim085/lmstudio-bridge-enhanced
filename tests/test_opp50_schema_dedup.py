"""Tests for OPP-50: Tool schema dedup experiment.

RED phase — these tests will FAIL until the conditional is added to
ResponsesClient.create_response().
"""
import json
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SAMPLE_TOOLS: list[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List files in a directory",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    }
]


def _make_client() -> Any:
    """Build a ResponsesClient with a fully mocked transport + session."""
    from llm.responses_client import ResponsesClient
    from llm.http_transport import HTTPTransport

    mock_session = MagicMock()
    # Simulate a successful 200 JSON response from LM Studio
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "resp-1", "output": []}
    mock_response.raise_for_status.return_value = None
    mock_session.post.return_value = mock_response

    mock_transport = MagicMock(spec=HTTPTransport)
    mock_transport.session = mock_session
    mock_transport.model = "test-model"
    mock_transport.get_endpoint.return_value = "http://localhost:1234/v1/responses"

    return ResponsesClient(transport=mock_transport), mock_session


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestToolSchemaDedup:
    """Conditional tool omission when previous_response_id is set."""

    @patch("llm.responses_client.ensure_model_loaded")
    def test_flag_true_with_previous_id_omits_tools(
        self, mock_ensure: MagicMock
    ) -> None:
        """When dedup enabled + previous_response_id set, tools NOT in payload."""
        client, mock_session = _make_client()

        with patch(
            "config.constants.tool_config.TOOL_SCHEMA_DEDUP_ENABLED", True
        ), patch(
            "llm.responses_client.TOOL_SCHEMA_DEDUP_ENABLED", True
        ):
            client.create_response(
                input_text="hello",
                tools=_SAMPLE_TOOLS,
                previous_response_id="prev-123",
            )

        payload: Dict[str, Any] = mock_session.post.call_args.kwargs["json"]
        assert "tools" not in payload, (
            "Expected tools to be omitted when TOOL_SCHEMA_DEDUP_ENABLED=True "
            "and previous_response_id is set, but 'tools' was present in payload"
        )

    @patch("llm.responses_client.ensure_model_loaded")
    def test_flag_true_without_previous_id_sends_tools(
        self, mock_ensure: MagicMock
    ) -> None:
        """When dedup enabled but no previous_response_id, tools included."""
        client, mock_session = _make_client()

        with patch(
            "config.constants.tool_config.TOOL_SCHEMA_DEDUP_ENABLED", True
        ), patch(
            "llm.responses_client.TOOL_SCHEMA_DEDUP_ENABLED", True
        ):
            client.create_response(
                input_text="hello",
                tools=_SAMPLE_TOOLS,
                previous_response_id=None,
            )

        payload: Dict[str, Any] = mock_session.post.call_args.kwargs["json"]
        assert "tools" in payload, (
            "Expected tools to be present when previous_response_id is None, "
            "even with TOOL_SCHEMA_DEDUP_ENABLED=True"
        )

    @patch("llm.responses_client.ensure_model_loaded")
    def test_flag_false_always_sends_tools(
        self, mock_ensure: MagicMock
    ) -> None:
        """When dedup disabled (default), tools always included even with previous_response_id."""
        client, mock_session = _make_client()

        with patch(
            "config.constants.tool_config.TOOL_SCHEMA_DEDUP_ENABLED", False
        ), patch(
            "llm.responses_client.TOOL_SCHEMA_DEDUP_ENABLED", False
        ):
            client.create_response(
                input_text="hello",
                tools=_SAMPLE_TOOLS,
                previous_response_id="prev-456",
            )

        payload: Dict[str, Any] = mock_session.post.call_args.kwargs["json"]
        assert "tools" in payload, (
            "Expected tools to be present when TOOL_SCHEMA_DEDUP_ENABLED=False "
            "(the default), but 'tools' was absent from payload"
        )
