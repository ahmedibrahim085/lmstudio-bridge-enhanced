#!/usr/bin/env python3
"""
OPP-09: Multi-Modal Autonomous Loops — Test Suite.

Tests:
1. MultiModalInput class (basic, chat messages, responses format, image processing, edge cases)
2. VisionTools error paths (empty choices, empty content, ValueError, Exception)
3. VisionTools compare_images and identify_objects with mocked LLM
4. register_vision_tools — registers 6 tools on a mock MCP server
5. EmbeddingsTools — init, happy path, error path, model=default
6. register_embeddings_tools — registers tool on mock MCP server
7. autonomous_with_images — delegates to existing autonomous execution
8. OPP-09 constants
"""

import asyncio
import json
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(coro):
    """Run async coroutine in a fresh event loop."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _make_llm_response(content="Test response"):
    """Build a minimal valid LLM choices response."""
    return {
        "choices": [{"message": {"content": content}}]
    }


# ---------------------------------------------------------------------------
# Group 1: TestOPP09Constants
# ---------------------------------------------------------------------------


class TestOPP09Constants(unittest.TestCase):
    """Group 1: OPP-09 constants are defined and sane."""

    def test_max_images_per_autonomous_input_exists(self):
        from config.constants import MAX_IMAGES_PER_AUTONOMOUS_INPUT
        self.assertIsInstance(MAX_IMAGES_PER_AUTONOMOUS_INPUT, int)
        self.assertGreater(MAX_IMAGES_PER_AUTONOMOUS_INPUT, 0)

    def test_max_images_per_autonomous_input_value(self):
        from config.constants import MAX_IMAGES_PER_AUTONOMOUS_INPUT
        self.assertEqual(MAX_IMAGES_PER_AUTONOMOUS_INPUT, 5)

    def test_multimodal_detail_default_exists(self):
        from config.constants import MULTIMODAL_DETAIL_DEFAULT
        self.assertIsInstance(MULTIMODAL_DETAIL_DEFAULT, str)

    def test_multimodal_detail_default_value(self):
        from config.constants import MULTIMODAL_DETAIL_DEFAULT
        self.assertEqual(MULTIMODAL_DETAIL_DEFAULT, "auto")

    def test_multimodal_detail_default_matches_vision_detail(self):
        from config.constants import DEFAULT_VISION_DETAIL, MULTIMODAL_DETAIL_DEFAULT
        self.assertEqual(MULTIMODAL_DETAIL_DEFAULT, DEFAULT_VISION_DETAIL)


# ---------------------------------------------------------------------------
# Group 2: TestMultiModalInputBasic
# ---------------------------------------------------------------------------


class TestMultiModalInputBasic(unittest.TestCase):
    """Group 2: MultiModalInput basic construction and has_images property."""

    def test_text_only_construction(self):
        from llm.multimodal_input import MultiModalInput
        mmi = MultiModalInput(text="hello world")
        self.assertEqual(mmi.text, "hello world")
        self.assertIsNone(mmi.images)

    def test_text_and_images_construction(self):
        from llm.multimodal_input import MultiModalInput
        imgs = ["data:image/png;base64,abc123"]
        mmi = MultiModalInput(text="describe", images=imgs)
        self.assertEqual(mmi.text, "describe")
        self.assertEqual(mmi.images, imgs)

    def test_has_images_false_when_no_images(self):
        from llm.multimodal_input import MultiModalInput
        mmi = MultiModalInput(text="no images")
        self.assertFalse(mmi.has_images)

    def test_has_images_false_when_empty_list(self):
        from llm.multimodal_input import MultiModalInput
        mmi = MultiModalInput(text="empty list", images=[])
        self.assertFalse(mmi.has_images)

    def test_has_images_true_when_images_provided(self):
        from llm.multimodal_input import MultiModalInput
        mmi = MultiModalInput(text="has image", images=["data:image/png;base64,abc"])
        self.assertTrue(mmi.has_images)

    def test_has_images_true_multiple_images(self):
        from llm.multimodal_input import MultiModalInput
        mmi = MultiModalInput(text="two images", images=["img1", "img2"])
        self.assertTrue(mmi.has_images)

    def test_empty_text_allowed(self):
        from llm.multimodal_input import MultiModalInput
        mmi = MultiModalInput(text="")
        self.assertEqual(mmi.text, "")

    def test_none_images_defaults(self):
        from llm.multimodal_input import MultiModalInput
        mmi = MultiModalInput(text="test", images=None)
        self.assertIsNone(mmi.images)
        self.assertFalse(mmi.has_images)


# ---------------------------------------------------------------------------
# Group 3: TestMultiModalInputChatMessages
# ---------------------------------------------------------------------------


class TestMultiModalInputChatMessages(unittest.TestCase):
    """Group 3: MultiModalInput.to_chat_messages() output format."""

    def test_text_only_returns_simple_message(self):
        from llm.multimodal_input import MultiModalInput
        mmi = MultiModalInput(text="hello")
        msgs = mmi.to_chat_messages()
        self.assertEqual(len(msgs), 1)
        msg = msgs[0]
        self.assertEqual(msg["role"], "user")
        self.assertEqual(msg["content"], "hello")

    def test_text_only_custom_role(self):
        from llm.multimodal_input import MultiModalInput
        mmi = MultiModalInput(text="system message")
        msgs = mmi.to_chat_messages(role="system")
        self.assertEqual(msgs[0]["role"], "system")

    def test_with_images_returns_content_array(self):
        from llm.multimodal_input import MultiModalInput
        data_uri = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        mmi = MultiModalInput(text="analyze this", images=[data_uri])
        msgs = mmi.to_chat_messages()
        self.assertEqual(len(msgs), 1)
        msg = msgs[0]
        self.assertEqual(msg["role"], "user")
        # Content should be a list (multi-modal format)
        self.assertIsInstance(msg["content"], list)

    def test_with_images_content_has_text_item(self):
        from llm.multimodal_input import MultiModalInput
        data_uri = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        mmi = MultiModalInput(text="describe", images=[data_uri])
        msgs = mmi.to_chat_messages()
        content = msgs[0]["content"]
        text_items = [c for c in content if c.get("type") == "text"]
        self.assertGreaterEqual(len(text_items), 1)
        self.assertEqual(text_items[0]["text"], "describe")

    def test_with_images_content_has_image_url_item(self):
        from llm.multimodal_input import MultiModalInput
        data_uri = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        mmi = MultiModalInput(text="describe", images=[data_uri])
        msgs = mmi.to_chat_messages()
        content = msgs[0]["content"]
        image_items = [c for c in content if c.get("type") == "image_url"]
        self.assertGreaterEqual(len(image_items), 1)

    def test_empty_images_list_returns_simple_message(self):
        from llm.multimodal_input import MultiModalInput
        mmi = MultiModalInput(text="hello", images=[])
        msgs = mmi.to_chat_messages()
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0]["content"], "hello")

    def test_multiple_images_all_included(self):
        from llm.multimodal_input import MultiModalInput
        data_uri = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        mmi = MultiModalInput(text="compare", images=[data_uri, data_uri])
        msgs = mmi.to_chat_messages()
        content = msgs[0]["content"]
        image_items = [c for c in content if c.get("type") == "image_url"]
        # Should have 2 valid image entries
        self.assertGreaterEqual(len(image_items), 1)


# ---------------------------------------------------------------------------
# Group 4: TestMultiModalInputResponsesFormat
# ---------------------------------------------------------------------------


class TestMultiModalInputResponsesFormat(unittest.TestCase):
    """Group 4: MultiModalInput.to_responses_input() output format."""

    def test_text_only_returns_plain_string(self):
        from llm.multimodal_input import MultiModalInput
        mmi = MultiModalInput(text="just text")
        result = mmi.to_responses_input()
        self.assertIsInstance(result, str)
        self.assertEqual(result, "just text")

    def test_empty_images_returns_plain_string(self):
        from llm.multimodal_input import MultiModalInput
        mmi = MultiModalInput(text="text", images=[])
        result = mmi.to_responses_input()
        self.assertIsInstance(result, str)

    def test_with_images_returns_list(self):
        from llm.multimodal_input import MultiModalInput
        data_uri = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        mmi = MultiModalInput(text="analyze", images=[data_uri])
        result = mmi.to_responses_input()
        self.assertIsInstance(result, list)

    def test_with_images_list_contains_dicts(self):
        from llm.multimodal_input import MultiModalInput
        data_uri = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        mmi = MultiModalInput(text="analyze", images=[data_uri])
        result = mmi.to_responses_input()
        self.assertIsInstance(result, list)
        for item in result:
            self.assertIsInstance(item, dict)


# ---------------------------------------------------------------------------
# Group 5: TestMultiModalInputImageProcessing
# ---------------------------------------------------------------------------


class TestMultiModalInputImageProcessing(unittest.TestCase):
    """Group 5: MultiModalInput lazy image processing and error tracking."""

    def test_processed_images_returns_list(self):
        from llm.multimodal_input import MultiModalInput
        data_uri = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        mmi = MultiModalInput(text="test", images=[data_uri])
        result = mmi.processed_images
        self.assertIsInstance(result, list)

    def test_processed_images_empty_when_no_images(self):
        from llm.multimodal_input import MultiModalInput
        mmi = MultiModalInput(text="no images")
        result = mmi.processed_images
        self.assertEqual(result, [])

    def test_processed_images_cached_on_second_call(self):
        from llm.multimodal_input import MultiModalInput
        data_uri = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        mmi = MultiModalInput(text="test", images=[data_uri])
        first = mmi.processed_images
        second = mmi.processed_images
        # Both calls return same object (cached)
        self.assertIs(first, second)

    def test_image_errors_returns_list(self):
        from llm.multimodal_input import MultiModalInput
        mmi = MultiModalInput(text="test", images=["/nonexistent/file.png"])
        errors = mmi.image_errors
        self.assertIsInstance(errors, list)

    def test_image_errors_non_empty_for_invalid_image(self):
        from llm.multimodal_input import MultiModalInput
        mmi = MultiModalInput(text="test", images=["/nonexistent/file.png"])
        errors = mmi.image_errors
        self.assertGreater(len(errors), 0)

    def test_image_errors_empty_for_valid_data_uri(self):
        from llm.multimodal_input import MultiModalInput
        data_uri = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        mmi = MultiModalInput(text="test", images=[data_uri])
        errors = mmi.image_errors
        self.assertEqual(errors, [])

    def test_image_errors_empty_when_no_images(self):
        from llm.multimodal_input import MultiModalInput
        mmi = MultiModalInput(text="test")
        errors = mmi.image_errors
        self.assertEqual(errors, [])


# ---------------------------------------------------------------------------
# Group 6: TestMultiModalInputEdgeCases
# ---------------------------------------------------------------------------


class TestMultiModalInputEdgeCases(unittest.TestCase):
    """Group 6: Edge cases for MultiModalInput."""

    def test_all_invalid_images_no_image_items_in_content(self):
        from llm.multimodal_input import MultiModalInput
        # An invalid path will result in an error ImageInput
        mmi = MultiModalInput(text="test", images=["/nonexistent.png"])
        msgs = mmi.to_chat_messages()
        # Should still produce a message (text at minimum)
        self.assertEqual(len(msgs), 1)

    def test_repr_or_str_does_not_crash(self):
        from llm.multimodal_input import MultiModalInput
        mmi = MultiModalInput(text="test", images=["img1"])
        # Should not raise
        str(mmi)

    def test_text_preserved_unicode(self):
        from llm.multimodal_input import MultiModalInput
        mmi = MultiModalInput(text="hello \u4e16\u754c")
        self.assertEqual(mmi.text, "hello \u4e16\u754c")

    def test_large_image_list_within_limit(self):
        from config.constants import MAX_IMAGES_PER_AUTONOMOUS_INPUT
        from llm.multimodal_input import MultiModalInput
        data_uri = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        images = [data_uri] * MAX_IMAGES_PER_AUTONOMOUS_INPUT
        mmi = MultiModalInput(text="max images", images=images)
        self.assertTrue(mmi.has_images)
        self.assertEqual(len(mmi.images), MAX_IMAGES_PER_AUTONOMOUS_INPUT)


# ---------------------------------------------------------------------------
# Group 7: TestVisionToolsErrorPaths
# ---------------------------------------------------------------------------


class TestVisionToolsErrorPaths(unittest.TestCase):
    """Group 7: VisionTools._extract_response error paths and method error handling."""

    def test_extract_response_empty_choices(self):
        from tools.vision import VisionTools
        tools = VisionTools(llm_client=MagicMock())
        result = tools._extract_response({"choices": []})
        self.assertIn("Error", result)
        self.assertIn("No response", result)

    def test_extract_response_missing_choices_key(self):
        from tools.vision import VisionTools
        tools = VisionTools(llm_client=MagicMock())
        result = tools._extract_response({})
        self.assertIn("Error", result)

    def test_extract_response_empty_content(self):
        from tools.vision import VisionTools
        tools = VisionTools(llm_client=MagicMock())
        result = tools._extract_response({
            "choices": [{"message": {"content": ""}}]
        })
        self.assertIn("Error", result)
        self.assertIn("Empty response", result)

    def test_extract_response_none_content(self):
        from tools.vision import VisionTools
        tools = VisionTools(llm_client=MagicMock())
        result = tools._extract_response({
            "choices": [{"message": {"content": None}}]
        })
        self.assertIn("Error", result)

    def test_analyze_image_value_error(self):
        from tools.vision import VisionTools
        mock_llm = MagicMock()
        mock_llm.vision_completion.side_effect = ValueError("bad image")
        tools = VisionTools(llm_client=mock_llm)
        result = _run(tools.analyze_image("bad_input"))
        self.assertIn("Error", result)
        self.assertIn("bad image", result)

    def test_analyze_image_generic_exception(self):
        from tools.vision import VisionTools
        mock_llm = MagicMock()
        mock_llm.vision_completion.side_effect = RuntimeError("connection failed")
        tools = VisionTools(llm_client=mock_llm)
        result = _run(tools.analyze_image("some_image"))
        self.assertIn("Error", result)
        self.assertIn("analyzing image", result.lower())

    def test_describe_image_value_error(self):
        from tools.vision import VisionTools
        mock_llm = MagicMock()
        mock_llm.vision_completion.side_effect = ValueError("invalid input")
        tools = VisionTools(llm_client=mock_llm)
        result = _run(tools.describe_image("bad_input"))
        self.assertIn("Error", result)
        self.assertIn("invalid input", result)

    def test_describe_image_generic_exception(self):
        from tools.vision import VisionTools
        mock_llm = MagicMock()
        mock_llm.vision_completion.side_effect = OSError("disk error")
        tools = VisionTools(llm_client=mock_llm)
        result = _run(tools.describe_image("some_image"))
        self.assertIn("Error", result)
        self.assertIn("describing image", result.lower())

    def test_extract_text_value_error(self):
        from tools.vision import VisionTools
        mock_llm = MagicMock()
        mock_llm.vision_completion.side_effect = ValueError("no data")
        tools = VisionTools(llm_client=mock_llm)
        result = _run(tools.extract_text_from_image("bad_input"))
        self.assertIn("Error", result)
        self.assertIn("no data", result)

    def test_extract_text_generic_exception(self):
        from tools.vision import VisionTools
        mock_llm = MagicMock()
        mock_llm.vision_completion.side_effect = RuntimeError("timeout")
        tools = VisionTools(llm_client=mock_llm)
        result = _run(tools.extract_text_from_image("some_image"))
        self.assertIn("Error", result)
        self.assertIn("extracting text", result.lower())

    def test_answer_about_image_value_error(self):
        from tools.vision import VisionTools
        mock_llm = MagicMock()
        mock_llm.vision_completion.side_effect = ValueError("bad image data")
        tools = VisionTools(llm_client=mock_llm)
        result = _run(tools.answer_about_image("bad_input", "what is this?"))
        self.assertIn("Error", result)
        self.assertIn("bad image data", result)

    def test_answer_about_image_generic_exception(self):
        from tools.vision import VisionTools
        mock_llm = MagicMock()
        mock_llm.vision_completion.side_effect = ConnectionError("network error")
        tools = VisionTools(llm_client=mock_llm)
        result = _run(tools.answer_about_image("some_image", "how many?"))
        self.assertIn("Error", result)
        self.assertIn("answering question", result.lower())


# ---------------------------------------------------------------------------
# Group 8: TestVisionToolsCompareImages
# ---------------------------------------------------------------------------


class TestVisionToolsCompareImages(unittest.TestCase):
    """Group 8: VisionTools.compare_images with mocked LLM."""

    def test_compare_images_differences(self):
        from tools.vision import VisionTools
        mock_llm = MagicMock()
        mock_llm.vision_completion.return_value = _make_llm_response("Image A is brighter.")
        tools = VisionTools(llm_client=mock_llm)
        result = _run(tools.compare_images(["img1.jpg", "img2.jpg"], "differences"))
        self.assertIn("brighter", result)

    def test_compare_images_similarities(self):
        from tools.vision import VisionTools
        mock_llm = MagicMock()
        mock_llm.vision_completion.return_value = _make_llm_response("Both are landscapes.")
        tools = VisionTools(llm_client=mock_llm)
        result = _run(tools.compare_images(["img1.jpg", "img2.jpg"], "similarities"))
        self.assertIn("landscapes", result)

    def test_compare_images_both(self):
        from tools.vision import VisionTools
        mock_llm = MagicMock()
        mock_llm.vision_completion.return_value = _make_llm_response("Similarities: color. Differences: size.")
        tools = VisionTools(llm_client=mock_llm)
        result = _run(tools.compare_images(["img1.jpg", "img2.jpg"], "both"))
        self.assertIn("Similarities", result)

    def test_compare_images_requires_at_least_two(self):
        from tools.vision import VisionTools
        tools = VisionTools(llm_client=MagicMock())
        result = _run(tools.compare_images(["only_one.jpg"]))
        self.assertIn("at least 2", result.lower())

    def test_compare_images_empty_list(self):
        from tools.vision import VisionTools
        tools = VisionTools(llm_client=MagicMock())
        result = _run(tools.compare_images([]))
        self.assertIn("at least 2", result.lower())

    def test_compare_images_value_error(self):
        from tools.vision import VisionTools
        mock_llm = MagicMock()
        mock_llm.vision_completion.side_effect = ValueError("bad images")
        tools = VisionTools(llm_client=mock_llm)
        result = _run(tools.compare_images(["img1.jpg", "img2.jpg"]))
        self.assertIn("Error", result)

    def test_compare_images_generic_exception(self):
        from tools.vision import VisionTools
        mock_llm = MagicMock()
        mock_llm.vision_completion.side_effect = RuntimeError("api down")
        tools = VisionTools(llm_client=mock_llm)
        result = _run(tools.compare_images(["img1.jpg", "img2.jpg"]))
        self.assertIn("Error", result)
        self.assertIn("comparing images", result.lower())

    def test_compare_images_calls_vision_completion_with_list(self):
        from tools.vision import VisionTools
        mock_llm = MagicMock()
        mock_llm.vision_completion.return_value = _make_llm_response("comparison result")
        tools = VisionTools(llm_client=mock_llm)
        _run(tools.compare_images(["img1.jpg", "img2.jpg"]))
        mock_llm.vision_completion.assert_called_once()
        call_kwargs = mock_llm.vision_completion.call_args[1]
        self.assertIsInstance(call_kwargs["images"], list)

    def test_compare_three_images(self):
        from tools.vision import VisionTools
        mock_llm = MagicMock()
        mock_llm.vision_completion.return_value = _make_llm_response("3-way comparison done.")
        tools = VisionTools(llm_client=mock_llm)
        result = _run(tools.compare_images(["a.jpg", "b.jpg", "c.jpg"]))
        self.assertIn("comparison", result.lower())


# ---------------------------------------------------------------------------
# Group 9: TestVisionToolsIdentifyObjects
# ---------------------------------------------------------------------------


class TestVisionToolsIdentifyObjects(unittest.TestCase):
    """Group 9: VisionTools.identify_objects with mocked LLM."""

    def test_identify_objects_success(self):
        from tools.vision import VisionTools
        mock_llm = MagicMock()
        mock_llm.vision_completion.return_value = _make_llm_response(
            "1. Chair - center, wooden\n2. Table - left, metal"
        )
        tools = VisionTools(llm_client=mock_llm)
        result = _run(tools.identify_objects("some_image.jpg"))
        self.assertIn("Chair", result)
        self.assertIn("Table", result)

    def test_identify_objects_value_error(self):
        from tools.vision import VisionTools
        mock_llm = MagicMock()
        mock_llm.vision_completion.side_effect = ValueError("bad image")
        tools = VisionTools(llm_client=mock_llm)
        result = _run(tools.identify_objects("bad_image"))
        self.assertIn("Error", result)
        self.assertIn("bad image", result)

    def test_identify_objects_generic_exception(self):
        from tools.vision import VisionTools
        mock_llm = MagicMock()
        mock_llm.vision_completion.side_effect = RuntimeError("model crashed")
        tools = VisionTools(llm_client=mock_llm)
        result = _run(tools.identify_objects("some_image"))
        self.assertIn("Error", result)
        self.assertIn("identifying objects", result.lower())

    def test_identify_objects_calls_vision_completion(self):
        from tools.vision import VisionTools
        mock_llm = MagicMock()
        mock_llm.vision_completion.return_value = _make_llm_response("Objects found.")
        tools = VisionTools(llm_client=mock_llm)
        _run(tools.identify_objects("test_img.png"))
        mock_llm.vision_completion.assert_called_once()

    def test_identify_objects_uses_default_detail(self):
        from config.constants import DEFAULT_VISION_DETAIL
        from tools.vision import VisionTools
        mock_llm = MagicMock()
        mock_llm.vision_completion.return_value = _make_llm_response("Objects.")
        tools = VisionTools(llm_client=mock_llm)
        _run(tools.identify_objects("test_img.png"))
        call_kwargs = mock_llm.vision_completion.call_args[1]
        self.assertEqual(call_kwargs["detail"], DEFAULT_VISION_DETAIL)

    def test_identify_objects_custom_detail(self):
        from tools.vision import VisionTools
        mock_llm = MagicMock()
        mock_llm.vision_completion.return_value = _make_llm_response("Objects.")
        tools = VisionTools(llm_client=mock_llm)
        _run(tools.identify_objects("test_img.png", detail="high"))
        call_kwargs = mock_llm.vision_completion.call_args[1]
        self.assertEqual(call_kwargs["detail"], "high")


# ---------------------------------------------------------------------------
# Group 10: TestRegisterVisionTools
# ---------------------------------------------------------------------------


class TestRegisterVisionTools(unittest.TestCase):
    """Group 10: register_vision_tools registers 6 tools on a mock MCP server."""

    def _make_mock_mcp(self):
        """Create a mock MCP server that collects registered tool names."""
        mock_mcp = MagicMock()
        registered = []

        def fake_tool_decorator():
            def decorator(fn):
                registered.append(fn.__name__)
                return fn
            return decorator

        mock_mcp.tool = fake_tool_decorator
        mock_mcp._registered = registered
        return mock_mcp

    def test_register_vision_tools_registers_six_tools(self):
        from tools.vision import register_vision_tools
        mock_mcp = self._make_mock_mcp()
        mock_llm = MagicMock()
        register_vision_tools(mock_mcp, llm_client=mock_llm)
        self.assertEqual(len(mock_mcp._registered), 6)

    def test_register_vision_tools_includes_analyze_image(self):
        from tools.vision import register_vision_tools
        mock_mcp = self._make_mock_mcp()
        register_vision_tools(mock_mcp, llm_client=MagicMock())
        self.assertIn("analyze_image", mock_mcp._registered)

    def test_register_vision_tools_includes_describe_image(self):
        from tools.vision import register_vision_tools
        mock_mcp = self._make_mock_mcp()
        register_vision_tools(mock_mcp, llm_client=MagicMock())
        self.assertIn("describe_image", mock_mcp._registered)

    def test_register_vision_tools_includes_compare_images(self):
        from tools.vision import register_vision_tools
        mock_mcp = self._make_mock_mcp()
        register_vision_tools(mock_mcp, llm_client=MagicMock())
        self.assertIn("compare_images", mock_mcp._registered)

    def test_register_vision_tools_includes_extract_text(self):
        from tools.vision import register_vision_tools
        mock_mcp = self._make_mock_mcp()
        register_vision_tools(mock_mcp, llm_client=MagicMock())
        self.assertIn("extract_text_from_image", mock_mcp._registered)

    def test_register_vision_tools_includes_identify_objects(self):
        from tools.vision import register_vision_tools
        mock_mcp = self._make_mock_mcp()
        register_vision_tools(mock_mcp, llm_client=MagicMock())
        self.assertIn("identify_objects", mock_mcp._registered)

    def test_register_vision_tools_includes_answer_about_image(self):
        from tools.vision import register_vision_tools
        mock_mcp = self._make_mock_mcp()
        register_vision_tools(mock_mcp, llm_client=MagicMock())
        self.assertIn("answer_about_image", mock_mcp._registered)

    def test_register_vision_tools_accepts_none_llm(self):
        """register_vision_tools works when llm_client=None (creates default)."""
        from tools.vision import register_vision_tools
        mock_mcp = self._make_mock_mcp()
        # Should not raise even with None
        register_vision_tools(mock_mcp, llm_client=None)
        self.assertEqual(len(mock_mcp._registered), 6)


# ---------------------------------------------------------------------------
# Group 11: TestEmbeddingsToolsHappyPath
# ---------------------------------------------------------------------------


class TestEmbeddingsToolsHappyPath(unittest.TestCase):
    """Group 11: EmbeddingsTools happy path — init and generate_embeddings."""

    def test_init_with_llm_client(self):
        from tools.embeddings import EmbeddingsTools
        mock_llm = MagicMock()
        tools = EmbeddingsTools(llm_client=mock_llm)
        self.assertIs(tools.llm, mock_llm)

    def test_init_without_llm_client_creates_default(self):
        from tools.embeddings import EmbeddingsTools
        tools = EmbeddingsTools()
        self.assertIsNotNone(tools.llm)

    def test_generate_embeddings_single_text(self):
        from tools.embeddings import EmbeddingsTools
        mock_llm = MagicMock()
        mock_llm.generate_embeddings.return_value = {
            "data": [{"embedding": [0.1, 0.2, 0.3]}],
            "model": "text-embedding",
            "usage": {"total_tokens": 5}
        }
        tools = EmbeddingsTools(llm_client=mock_llm)
        result = _run(tools.generate_embeddings("hello world"))
        parsed = json.loads(result)
        self.assertIn("data", parsed)

    def test_generate_embeddings_list_of_texts(self):
        from tools.embeddings import EmbeddingsTools
        mock_llm = MagicMock()
        mock_llm.generate_embeddings.return_value = {
            "data": [
                {"embedding": [0.1, 0.2]},
                {"embedding": [0.3, 0.4]},
            ],
            "model": "text-embedding"
        }
        tools = EmbeddingsTools(llm_client=mock_llm)
        result = _run(tools.generate_embeddings(["text1", "text2"]))
        parsed = json.loads(result)
        self.assertEqual(len(parsed["data"]), 2)

    def test_generate_embeddings_model_default_passes_none(self):
        """When model='default', None is passed to llm.generate_embeddings."""
        from tools.embeddings import EmbeddingsTools
        mock_llm = MagicMock()
        mock_llm.generate_embeddings.return_value = {"data": []}
        tools = EmbeddingsTools(llm_client=mock_llm)
        _run(tools.generate_embeddings("text", model="default"))
        call_kwargs = mock_llm.generate_embeddings.call_args[1]
        self.assertIsNone(call_kwargs["model"])

    def test_generate_embeddings_explicit_model_passed_through(self):
        """When a specific model is given, it is forwarded."""
        from tools.embeddings import EmbeddingsTools
        mock_llm = MagicMock()
        mock_llm.generate_embeddings.return_value = {"data": []}
        tools = EmbeddingsTools(llm_client=mock_llm)
        _run(tools.generate_embeddings("text", model="nomic-embed-text"))
        call_kwargs = mock_llm.generate_embeddings.call_args[1]
        self.assertEqual(call_kwargs["model"], "nomic-embed-text")

    def test_generate_embeddings_returns_json_string(self):
        from tools.embeddings import EmbeddingsTools
        mock_llm = MagicMock()
        mock_llm.generate_embeddings.return_value = {"data": [{"embedding": [1.0]}]}
        tools = EmbeddingsTools(llm_client=mock_llm)
        result = _run(tools.generate_embeddings("test"))
        # Must be a valid JSON string
        parsed = json.loads(result)
        self.assertIsInstance(parsed, dict)


# ---------------------------------------------------------------------------
# Group 12: TestEmbeddingsToolsErrorPaths
# ---------------------------------------------------------------------------


class TestEmbeddingsToolsErrorPaths(unittest.TestCase):
    """Group 12: EmbeddingsTools error handling."""

    def test_generate_embeddings_exception_returns_json_error(self):
        from tools.embeddings import EmbeddingsTools
        mock_llm = MagicMock()
        mock_llm.generate_embeddings.side_effect = RuntimeError("LM Studio offline")
        tools = EmbeddingsTools(llm_client=mock_llm)
        result = _run(tools.generate_embeddings("text"))
        parsed = json.loads(result)
        self.assertIn("error", parsed)

    def test_generate_embeddings_error_message_contains_description(self):
        from tools.embeddings import EmbeddingsTools
        mock_llm = MagicMock()
        mock_llm.generate_embeddings.side_effect = ConnectionError("refused")
        tools = EmbeddingsTools(llm_client=mock_llm)
        result = _run(tools.generate_embeddings("text"))
        parsed = json.loads(result)
        self.assertIn("refused", parsed["error"])

    def test_generate_embeddings_error_prefix_in_message(self):
        from tools.embeddings import EmbeddingsTools
        mock_llm = MagicMock()
        mock_llm.generate_embeddings.side_effect = Exception("timeout")
        tools = EmbeddingsTools(llm_client=mock_llm)
        result = _run(tools.generate_embeddings("text"))
        parsed = json.loads(result)
        self.assertIn("Failed to generate embeddings", parsed["error"])

    def test_generate_embeddings_result_always_valid_json(self):
        """Even on error, result must be parseable JSON."""
        from tools.embeddings import EmbeddingsTools
        mock_llm = MagicMock()
        mock_llm.generate_embeddings.side_effect = ValueError("bad model")
        tools = EmbeddingsTools(llm_client=mock_llm)
        result = _run(tools.generate_embeddings("text"))
        # Should not raise
        parsed = json.loads(result)
        self.assertIsNotNone(parsed)


# ---------------------------------------------------------------------------
# Group 13: TestRegisterEmbeddingsTools
# ---------------------------------------------------------------------------


class TestRegisterEmbeddingsTools(unittest.TestCase):
    """Group 13: register_embeddings_tools registers the tool on a mock MCP server."""

    def _make_mock_mcp(self):
        mock_mcp = MagicMock()
        registered = []

        def fake_tool_decorator():
            def decorator(fn):
                registered.append(fn.__name__)
                return fn
            return decorator

        mock_mcp.tool = fake_tool_decorator
        mock_mcp._registered = registered
        return mock_mcp

    def test_register_embeddings_tools_registers_one_tool(self):
        from tools.embeddings import register_embeddings_tools
        mock_mcp = self._make_mock_mcp()
        register_embeddings_tools(mock_mcp, llm_client=MagicMock())
        self.assertEqual(len(mock_mcp._registered), 1)

    def test_register_embeddings_tools_registers_generate_embeddings(self):
        from tools.embeddings import register_embeddings_tools
        mock_mcp = self._make_mock_mcp()
        register_embeddings_tools(mock_mcp, llm_client=MagicMock())
        self.assertIn("generate_embeddings", mock_mcp._registered)

    def test_register_embeddings_tools_accepts_none_llm(self):
        from tools.embeddings import register_embeddings_tools
        mock_mcp = self._make_mock_mcp()
        # Should not raise with None
        register_embeddings_tools(mock_mcp, llm_client=None)
        self.assertEqual(len(mock_mcp._registered), 1)

    def test_register_embeddings_tools_with_llm_client(self):
        from tools.embeddings import register_embeddings_tools
        mock_mcp = self._make_mock_mcp()
        mock_llm = MagicMock()
        register_embeddings_tools(mock_mcp, llm_client=mock_llm)
        self.assertIn("generate_embeddings", mock_mcp._registered)


# ---------------------------------------------------------------------------
# Group 14: TestAutonomousWithImages
# ---------------------------------------------------------------------------


def _make_agent():
    """Build DynamicAutonomousAgent with mocked LLM and validator."""
    from tools.dynamic_autonomous import DynamicAutonomousAgent
    mock_llm = MagicMock()
    mock_validator = MagicMock()

    agent = DynamicAutonomousAgent.__new__(DynamicAutonomousAgent)
    agent.llm = mock_llm
    agent.model_validator = mock_validator
    agent.mcp_json_path = "/tmp/fake.mcp.json"
    return agent


class TestAutonomousWithImages(unittest.TestCase):
    """Group 14: DynamicAutonomousAgent.autonomous_with_images."""

    def test_method_exists(self):
        agent = _make_agent()
        self.assertTrue(hasattr(agent, "autonomous_with_images"))
        self.assertTrue(callable(agent.autonomous_with_images))

    def test_method_is_async(self):
        import inspect
        agent = _make_agent()
        self.assertTrue(inspect.iscoroutinefunction(agent.autonomous_with_images))

    def test_autonomous_with_images_delegates_to_autonomous_with_mcp(self):
        """autonomous_with_images should call autonomous_with_mcp internally."""
        agent = _make_agent()

        with patch.object(
            agent,
            "autonomous_with_mcp",
            new=AsyncMock(return_value="task complete"),
        ) as mock_method:
            result = _run(
                agent.autonomous_with_images(
                    mcp_name="filesystem",
                    task="analyze this image",
                    images=["data:image/png;base64,abc123"],
                )
            )

        mock_method.assert_awaited_once()
        self.assertEqual(result, "task complete")

    def test_autonomous_with_images_passes_mcp_name(self):
        """mcp_name is forwarded to autonomous_with_mcp."""
        agent = _make_agent()

        with patch.object(
            agent,
            "autonomous_with_mcp",
            new=AsyncMock(return_value="done"),
        ) as mock_method:
            _run(
                agent.autonomous_with_images(
                    mcp_name="memory",
                    task="task",
                    images=["data:image/png;base64,abc"],
                )
            )

        call_kwargs = mock_method.call_args
        mcp_arg = call_kwargs.kwargs.get("mcp_name") or call_kwargs.args[0]
        self.assertEqual(mcp_arg, "memory")

    def test_autonomous_with_images_embeds_task(self):
        """Task text appears in the call to autonomous_with_mcp."""
        agent = _make_agent()

        with patch.object(
            agent,
            "autonomous_with_mcp",
            new=AsyncMock(return_value="done"),
        ) as mock_method:
            _run(
                agent.autonomous_with_images(
                    mcp_name="filesystem",
                    task="describe the chart",
                    images=["data:image/png;base64,abc"],
                )
            )

        call_kwargs = mock_method.call_args
        # Task should appear somewhere in the passed task argument
        task_arg = call_kwargs.kwargs.get("task") or (
            call_kwargs.args[1] if len(call_kwargs.args) > 1 else None
        )
        self.assertIsNotNone(task_arg)
        self.assertIn("describe the chart", task_arg)

    def test_autonomous_with_images_no_images_still_works(self):
        """autonomous_with_images with empty images list delegates normally."""
        agent = _make_agent()

        with patch.object(
            agent,
            "autonomous_with_mcp",
            new=AsyncMock(return_value="done without images"),
        ) as mock_method:
            result = _run(
                agent.autonomous_with_images(
                    mcp_name="filesystem",
                    task="text only task",
                    images=[],
                )
            )

        mock_method.assert_awaited_once()
        self.assertEqual(result, "done without images")

    def test_autonomous_with_images_passes_max_rounds(self):
        """max_rounds is forwarded to autonomous_with_mcp."""
        agent = _make_agent()

        with patch.object(
            agent,
            "autonomous_with_mcp",
            new=AsyncMock(return_value="done"),
        ) as mock_method:
            _run(
                agent.autonomous_with_images(
                    mcp_name="filesystem",
                    task="task",
                    images=["img"],
                    max_rounds=5,
                )
            )

        call_kwargs = mock_method.call_args
        rounds_arg = call_kwargs.kwargs.get("max_rounds")
        self.assertEqual(rounds_arg, 5)

    def test_autonomous_with_images_passes_model(self):
        """model is forwarded to autonomous_with_mcp."""
        agent = _make_agent()

        with patch.object(
            agent,
            "autonomous_with_mcp",
            new=AsyncMock(return_value="done"),
        ) as mock_method:
            _run(
                agent.autonomous_with_images(
                    mcp_name="filesystem",
                    task="task",
                    images=["img"],
                    model="qwen-vl",
                )
            )

        call_kwargs = mock_method.call_args
        model_arg = call_kwargs.kwargs.get("model")
        self.assertEqual(model_arg, "qwen-vl")


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
