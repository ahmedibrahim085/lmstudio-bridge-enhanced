#!/usr/bin/env python3
"""Tests for C-14: Standardize tool error return contract.

All MCP tool error returns must be JSON strings with an "error" key:
    '{"error": "Human-readable error message"}'

This enables programmatic error detection by MCP clients.

Affected modules:
- tools/vision.py: bare f-strings → json.dumps({"error": ...})
- tools/health.py: bare f-strings → json.dumps({"error": ...})
- tools/completions.py: already compliant (json.dumps pattern)
"""
import json
from unittest.mock import MagicMock, patch, AsyncMock

import pytest


# ---------------------------------------------------------------------------
# Vision tools — error returns must be JSON with "error" key
# ---------------------------------------------------------------------------

class TestVisionErrorContract:
    """All VisionTools error returns must be parseable JSON with 'error' key."""

    def _make_vision_tools(self):
        from tools.vision import VisionTools
        mock_llm = MagicMock()
        return VisionTools(llm_client=mock_llm), mock_llm

    @pytest.mark.asyncio
    async def test_analyze_image_error_is_json(self):
        """analyze_image error must return JSON with 'error' key."""
        vt, mock_llm = self._make_vision_tools()
        mock_llm.vision_completion.side_effect = RuntimeError("model crashed")

        result = await vt.analyze_image("test.png")
        parsed = json.loads(result)
        assert "error" in parsed
        assert "model crashed" in parsed["error"]

    @pytest.mark.asyncio
    async def test_describe_image_error_is_json(self):
        """describe_image error must return JSON with 'error' key."""
        vt, mock_llm = self._make_vision_tools()
        mock_llm.vision_completion.side_effect = RuntimeError("timeout")

        result = await vt.describe_image("test.png")
        parsed = json.loads(result)
        assert "error" in parsed

    @pytest.mark.asyncio
    async def test_extract_response_no_choices_is_json(self):
        """_extract_response with no choices must return JSON error."""
        vt, _ = self._make_vision_tools()

        result = vt._extract_response({"choices": []})
        parsed = json.loads(result)
        assert "error" in parsed

    @pytest.mark.asyncio
    async def test_extract_response_empty_content_is_json(self):
        """_extract_response with empty content must return JSON error."""
        vt, _ = self._make_vision_tools()

        result = vt._extract_response({"choices": [{"message": {"content": ""}}]})
        parsed = json.loads(result)
        assert "error" in parsed

    @pytest.mark.asyncio
    async def test_compare_images_too_few_is_json(self):
        """compare_images with <2 images must return JSON error."""
        vt, _ = self._make_vision_tools()

        result = await vt.compare_images(["only_one.png"])
        parsed = json.loads(result)
        assert "error" in parsed

    @pytest.mark.asyncio
    async def test_vision_valueerror_is_json(self):
        """ValueError from vision_completion must return JSON error."""
        vt, mock_llm = self._make_vision_tools()
        mock_llm.vision_completion.side_effect = ValueError("invalid image format")

        result = await vt.analyze_image("bad.png")
        parsed = json.loads(result)
        assert "error" in parsed
        assert "invalid image format" in parsed["error"]


# ---------------------------------------------------------------------------
# Health tools — error returns must be JSON with "error" key
# ---------------------------------------------------------------------------

class TestHealthErrorContract:
    """All HealthTools error returns must be parseable JSON with 'error' key."""

    def _make_health_tools(self):
        from tools.health import HealthTools
        mock_llm = MagicMock()
        return HealthTools(llm_client=mock_llm), mock_llm

    @pytest.mark.asyncio
    async def test_health_check_error_is_json(self):
        """health_check error must return JSON with 'error' key."""
        ht, mock_llm = self._make_health_tools()
        mock_llm.health_check.side_effect = ConnectionError("refused")

        result = await ht.health_check()
        parsed = json.loads(result)
        assert "error" in parsed
        assert "refused" in parsed["error"]

    @pytest.mark.asyncio
    async def test_list_models_error_is_json(self):
        """list_models error must return JSON with 'error' key."""
        ht, mock_llm = self._make_health_tools()
        mock_llm.list_models.side_effect = RuntimeError("server down")

        result = await ht.list_models()
        parsed = json.loads(result)
        assert "error" in parsed
        assert "server down" in parsed["error"]

    @pytest.mark.asyncio
    async def test_get_current_model_error_is_json(self):
        """get_current_model error must return JSON with 'error' key."""
        ht, mock_llm = self._make_health_tools()
        mock_llm.chat_completion.side_effect = RuntimeError("no model loaded")

        result = await ht.get_current_model()
        parsed = json.loads(result)
        assert "error" in parsed
        assert "no model loaded" in parsed["error"]
