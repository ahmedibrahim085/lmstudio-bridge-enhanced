#!/usr/bin/env python3
"""
OPP-08: MCP Tool — select_best_model.

Exposes smart model selection as an MCP tool so Claude Code (and other
LLM agents) can request the best available model for a task at runtime.

Tool name: ``select_best_model``

Input schema
------------
task_type : str  (required)
    Task identifier, e.g. "code_generation", "summarization", "reasoning",
    "tool_use", "vision".
max_vram_gb : float | None  (optional)
    VRAM budget in gigabytes.  Models that require more VRAM are excluded.

Output schema
-------------
On success::

    {
      "success": true,
      "model_id": "qwen/qwen3-coder-30b",
      "task_type": "code_generation"
    }

On failure::

    {
      "success": false,
      "error": "<human-readable message>",
      "error_code": "no_models_available" | "selection_error"
    }
"""

import logging
from typing import Any, Optional

from config.constants import (
    SELECTION_ERROR_INTERNAL,
    SELECTION_ERROR_NO_MODELS,
)
from model_registry.selector import NoModelsAvailableError, select_best_model

logger = logging.getLogger(__name__)

__all__ = [
    "register_model_registry_tools",
    "select_best_model_tool",
]


# ---------------------------------------------------------------------------
# MCP Tool handler
# ---------------------------------------------------------------------------


def select_best_model_tool(
    task_type: str,
    max_vram_gb: Optional[float] = None,
    cache_path: Optional[str] = None,
) -> dict[str, Any]:
    """Select the best loaded model for a given task type.

    This MCP tool queries LM Studio for currently loaded models, scores each
    one against the capabilities required by *task_type*, and returns the
    model identifier that best fits.

    Parameters
    ----------
    task_type:
        The kind of task you need a model for.  Supported values:

        - ``"code_generation"`` / ``"code_review"`` / ``"coding"``
        - ``"summarization"`` / ``"long_document"``
        - ``"reasoning"`` / ``"analysis"`` / ``"math"``
        - ``"tool_use"`` / ``"agents"`` / ``"function_calling"``
        - ``"vision"`` / ``"image_analysis"`` / ``"multimodal"``

        Unknown values trigger a graceful fallback that returns the best
        general-purpose model available.

    max_vram_gb:
        Optional VRAM budget (GB).  Models that require more VRAM than this
        are excluded from selection.  Pass ``None`` (default) to disable
        the budget constraint.

    cache_path:
        Optional override for the capability cache file path.

    Returns
    -------
    dict
        MCP tool response with ``success``, ``model_id`` (on success), or
        ``error`` / ``error_code`` (on failure).
    """
    # Build requirements dict only when a constraint is present
    requirements: Optional[dict] = None
    if max_vram_gb is not None:
        requirements = {"max_vram_gb": max_vram_gb}

    try:
        model_id = select_best_model(
            task_type,
            requirements=requirements,
            cache_path=cache_path,
        )
        logger.info(
            "Smart selection: task=%s selected=%s vram_budget=%s",
            task_type, model_id, max_vram_gb,
        )
        return {
            "success": True,
            "model_id": model_id,
            "task_type": task_type,
        }

    except NoModelsAvailableError as exc:
        logger.warning("No models available for task '%s': %s", task_type, exc)
        return {
            "success": False,
            "error": str(exc),
            "error_code": SELECTION_ERROR_NO_MODELS,
        }

    except Exception as exc:
        logger.error("Unexpected error in smart selection: %s", exc, exc_info=True)
        return {
            "success": False,
            "error": f"Smart model selection failed: {exc}",
            "error_code": SELECTION_ERROR_INTERNAL,
        }


# ---------------------------------------------------------------------------
# MCP tool schema (for FastMCP / manual registration)
# ---------------------------------------------------------------------------

TOOL_SCHEMA = {
    "name": "select_best_model",
    "description": (
        "Select the best currently-loaded LM Studio model for a given task. "
        "Scores all loaded models against the capabilities required by the task "
        "(coding, reasoning, long context, vision, tool use) and returns the "
        "model identifier that best matches. "
        "Use this before making an LLM call when you want the optimal model "
        "for the job rather than the default."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "task_type": {
                "type": "string",
                "description": (
                    "Type of task. Supported: code_generation, code_review, "
                    "summarization, reasoning, analysis, tool_use, agents, "
                    "vision, image_analysis."
                ),
            },
            "max_vram_gb": {
                "type": "number",
                "description": (
                    "Optional VRAM budget in GB. "
                    "Models requiring more VRAM are excluded."
                ),
            },
        },
        "required": ["task_type"],
    },
}


# ---------------------------------------------------------------------------
# Register with FastMCP
# ---------------------------------------------------------------------------


def register_model_registry_tools(mcp) -> None:
    """Register model registry tools with FastMCP server.

    Args:
        mcp: FastMCP server instance
    """

    @mcp.tool()
    def select_best_model(
        task_type: str,
        max_vram_gb: Optional[float] = None,
    ) -> dict[str, Any]:
        """Select the best loaded model for a given task type.

        Scores all currently loaded LM Studio models against the
        capabilities required by the task and returns the best match.

        Supported task types: code_generation, code_review, summarization,
        reasoning, analysis, tool_use, agents, vision, image_analysis.

        Args:
            task_type: The kind of task you need a model for.
            max_vram_gb: Optional VRAM budget in GB (models exceeding this are excluded).

        Returns:
            Dict with success, model_id (on success), or error/error_code (on failure).
        """
        return select_best_model_tool(
            task_type=task_type,
            max_vram_gb=max_vram_gb,
        )
