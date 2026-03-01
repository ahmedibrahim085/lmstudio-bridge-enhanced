#!/usr/bin/env python3
"""Tests for H-dup: Vision helper deduplication.

Verifies that VisionTools._safe_vision_call() exists and all public
methods delegate to it, eliminating duplicated try/except blocks.
"""

import ast
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


VISION_PATH = Path(__file__).parent.parent / "tools" / "vision.py"


class TestSafeVisionCallExists:
    """VisionTools must have a _safe_vision_call helper method."""

    def test_method_exists(self):
        from tools.vision import VisionTools

        assert hasattr(VisionTools, "_safe_vision_call"), (
            "VisionTools._safe_vision_call() helper not found"
        )

    def test_method_is_async(self):
        """_safe_vision_call must be async."""
        import inspect
        from tools.vision import VisionTools

        method = getattr(VisionTools, "_safe_vision_call", None)
        assert method is not None
        assert inspect.iscoroutinefunction(method), (
            "_safe_vision_call must be an async method"
        )


class TestSafeVisionCallBehavior:
    """_safe_vision_call must handle the try/except pattern correctly."""

    @pytest.fixture
    def tools(self):
        from tools.vision import VisionTools

        mock_llm = MagicMock()
        return VisionTools(llm_client=mock_llm)

    @pytest.mark.asyncio
    async def test_returns_extracted_response_on_success(self, tools):
        tools.llm.vision_completion.return_value = {
            "choices": [{"message": {"content": "test response"}}]
        }
        result = await tools._safe_vision_call(
            prompt="test", images="img.png", detail="auto", error_context="test"
        )
        assert result == "test response"

    @pytest.mark.asyncio
    async def test_returns_error_json_on_value_error(self, tools):
        tools.llm.vision_completion.side_effect = ValueError("bad input")
        result = await tools._safe_vision_call(
            prompt="test", images="img.png", detail="auto", error_context="test"
        )
        parsed = json.loads(result)
        assert "error" in parsed
        assert "bad input" in parsed["error"]

    @pytest.mark.asyncio
    async def test_returns_error_json_on_exception(self, tools):
        tools.llm.vision_completion.side_effect = RuntimeError("boom")
        result = await tools._safe_vision_call(
            prompt="test", images="img.png", detail="auto", error_context="analyzing"
        )
        parsed = json.loads(result)
        assert "error" in parsed
        assert "analyzing" in parsed["error"].lower() or "boom" in parsed["error"]

    @pytest.mark.asyncio
    async def test_logs_on_exception(self, tools):
        tools.llm.vision_completion.side_effect = RuntimeError("boom")
        with patch("tools.vision.logger") as mock_logger:
            await tools._safe_vision_call(
                prompt="test", images="img.png", detail="auto",
                error_context="analyzing"
            )
            mock_logger.error.assert_called_once()


class TestPublicMethodsDelegate:
    """All 6 public vision methods must delegate to _safe_vision_call."""

    def test_no_direct_vision_completion_in_public_methods(self):
        """Public methods must NOT call self.llm.vision_completion directly."""
        source = VISION_PATH.read_text()
        tree = ast.parse(source)

        # Find VisionTools class
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "VisionTools":
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if item.name.startswith("_"):
                            continue  # Skip private methods
                        # Check if any call in this method calls self.llm.vision_completion
                        method_source = ast.get_source_segment(source, item)
                        assert "self.llm.vision_completion" not in method_source, (
                            f"Method {item.name} still calls self.llm.vision_completion "
                            "directly — should delegate to _safe_vision_call"
                        )

    def test_public_methods_call_safe_vision_call(self):
        """Each public async method must call _safe_vision_call."""
        source = VISION_PATH.read_text()
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "VisionTools":
                public_async = [
                    item for item in node.body
                    if isinstance(item, ast.AsyncFunctionDef)
                    and not item.name.startswith("_")
                ]
                assert len(public_async) >= 6, (
                    f"Expected >=6 public async methods, found {len(public_async)}"
                )
                for method in public_async:
                    method_source = ast.get_source_segment(source, method)
                    assert "_safe_vision_call" in method_source, (
                        f"Method {method.name} does not call _safe_vision_call"
                    )
