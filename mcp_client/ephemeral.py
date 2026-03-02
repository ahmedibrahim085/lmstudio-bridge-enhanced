"""Ephemeral MCP server integrations for per-request attachment.

LM Studio's /api/v1/chat accepts an ``integrations`` parameter that
attaches MCP servers on a per-request basis. This module provides
data structures and utilities for building that parameter.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from config.constants import INTEGRATION_TYPE_MCP, SUPPORTED_INTEGRATION_TYPES

logger = logging.getLogger(__name__)

__all__ = [
    "EphemeralIntegration",
    "validate_integration",
    "build_integrations_payload",
]


@dataclass(frozen=True)
class EphemeralIntegration:
    """A per-request MCP server integration for /api/v1/chat.

    Attributes:
        server_id: Unique identifier for the MCP server.
        type: Integration type. Currently only "mcp" is supported.
        allowed_tools: Optional tuple of tool names to allow. None means all tools.
    """

    server_id: str
    type: str = INTEGRATION_TYPE_MCP
    allowed_tools: Optional[Tuple[str, ...]] = None


def validate_integration(integration: EphemeralIntegration) -> None:
    """Validate an ephemeral integration configuration.

    Args:
        integration: The integration to validate.

    Raises:
        ValueError: If server_id is empty/whitespace or type is unsupported.
    """
    if not integration.server_id or not integration.server_id.strip():
        raise ValueError(
            f"server_id must be a non-empty string, got: {integration.server_id!r}"
        )
    if integration.type not in SUPPORTED_INTEGRATION_TYPES:
        raise ValueError(
            f"Unsupported integration type: {integration.type!r}. "
            f"Supported: {SUPPORTED_INTEGRATION_TYPES}"
        )


def build_integrations_payload(
    integrations: List[EphemeralIntegration],
) -> List[Dict[str, Any]]:
    """Convert EphemeralIntegration objects to the API payload format.

    Validates each integration, deduplicates by server_id (last wins),
    and formats for the /api/v1/chat integrations parameter.

    Args:
        integrations: List of integration configs.

    Returns:
        List of dicts ready for the API payload.

    Raises:
        ValueError: If any integration has invalid config.
    """
    if not integrations:
        return []

    # Validate all first
    for integration in integrations:
        validate_integration(integration)

    # Deduplicate by server_id (last wins)
    seen: Dict[str, EphemeralIntegration] = {}
    for integration in integrations:
        seen[integration.server_id] = integration

    # Build payload
    result: List[Dict[str, Any]] = []
    for integration in seen.values():
        entry: Dict[str, Any] = {
            "type": integration.type,
            "id": integration.server_id,
        }
        if integration.allowed_tools is not None:
            entry["allowed_tools"] = list(integration.allowed_tools)
        result.append(entry)

    return result
