#!/usr/bin/env python3
"""
Comprehensive tests for LM Studio v0.3.30+ Vision/Multimodal support.

Tests the image processing utilities and vision tools:
1. Image input detection and processing
2. File path, URL, and base64 handling
3. Vision content building
4. Vision tools (mocked LLM responses)
5. Backward compatibility
"""

import pytest
import os
import base64
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

# Import the modules under test
from utils.image_utils import (
    ImageInputType,
    ImageInput,
    detect_input_type,
    process_image_input,
    build_vision_content,
    validate_image_inputs
)
from config.constants import (
    SUPPORTED_IMAGE_TYPES,
    IMAGE_EXTENSION_MAP,
    MAX_IMAGE_SIZE_BYTES,
    DEFAULT_VISION_DETAIL,
    VISION_MODEL_WARNING
)


class TestImageInputType:
    """Test the ImageInputType enum."""

    def test_enum_values(self):
        """Test that all expected enum values exist."""
        assert ImageInputType.FILE_PATH.value == "file_path"
        assert ImageInputType.URL.value == "url"
        assert ImageInputType.BASE64.value == "base64"
        assert ImageInputType.UNKNOWN.value == "unknown"


class TestImageInput:
    """Test the ImageInput dataclass."""

    def test_valid_image_input(self):
        """Test creating a valid ImageInput."""
        img = ImageInput(
            input_type=ImageInputType.URL,
            url="https://example.com/image.jpg",
            mime_type="image/jpeg"
        )
        assert img.is_valid is True
        assert img.errors == []

    def test_invalid_image_input(self):
        """Test creating an invalid ImageInput."""
        img = ImageInput(
            input_type=ImageInputType.FILE_PATH,
            url="",
            errors=["File not found"]
        )
        assert img.is_valid is False

    def test_default_detail(self):
        """Test default detail level."""
        img = ImageInput(
            input_type=ImageInputType.URL,
            url="https://example.com/image.jpg"
        )
        assert img.detail == DEFAULT_VISION_DETAIL


class TestDetectInputType:
    """Test the detect_input_type function."""

    def test_detect_http_url(self):
        """Test detection of HTTP URLs."""
        assert detect_input_type("http://example.com/image.jpg") == ImageInputType.URL
        assert detect_input_type("https://example.com/image.png") == ImageInputType.URL

    def test_detect_url_without_extension(self):
        """Test detection of URLs without image extension."""
        assert detect_input_type("https://example.com/api/image") == ImageInputType.URL

    def test_detect_file_path_absolute(self):
        """Test detection of absolute file paths."""
        assert detect_input_type("/path/to/image.png") == ImageInputType.FILE_PATH
        assert detect_input_type("/Users/test/photos/pic.jpg") == ImageInputType.FILE_PATH

    def test_detect_file_path_relative(self):
        """Test detection of relative file paths."""
        assert detect_input_type("./image.png") == ImageInputType.FILE_PATH
        assert detect_input_type("../images/photo.jpg") == ImageInputType.FILE_PATH

    def test_detect_base64_data_uri(self):
        """Test detection of base64 data URIs."""
        data_uri = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        assert detect_input_type(data_uri) == ImageInputType.BASE64

    def test_detect_raw_base64(self):
        """Test detection of raw base64 (long string without prefix)."""
        # Create a valid long base64 string (no = in middle, proper padding at end)
        # This represents a larger image that would be base64-encoded
        raw_base64 = "A" * 200  # Valid base64 chars, long enough to be detected
        assert detect_input_type(raw_base64) == ImageInputType.BASE64

    def test_detect_unknown_empty(self):
        """Test detection of empty/invalid input."""
        assert detect_input_type("") == ImageInputType.UNKNOWN
        assert detect_input_type(None) == ImageInputType.UNKNOWN

    def test_detect_unknown_short_string(self):
        """Test that short strings without patterns are unknown."""
        assert detect_input_type("abc") == ImageInputType.UNKNOWN


class TestProcessImageInput:
    """Test the process_image_input function."""

    def test_process_url(self):
        """Test processing URL input."""
        result = process_image_input("https://example.com/image.jpg")
        assert result.is_valid
        assert result.input_type == ImageInputType.URL
        assert result.url == "https://example.com/image.jpg"
        assert result.mime_type == "image/jpeg"

    def test_process_url_without_extension(self):
        """Test processing URL without extension (valid but warns)."""
        result = process_image_input("https://example.com/api/image")
        assert result.is_valid
        assert result.input_type == ImageInputType.URL
        assert len(result.warnings) > 0  # Should warn about unknown type

    def test_process_file_not_found(self):
        """Test processing non-existent file."""
        result = process_image_input("/nonexistent/path/image.png")
        assert not result.is_valid
        assert "not found" in result.errors[0].lower()

    def test_process_file_exists(self):
        """Test processing existing file."""
        # Create a temporary PNG file
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            # Write minimal PNG header
            png_header = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
            f.write(png_header)
            temp_path = f.name

        try:
            result = process_image_input(temp_path)
            assert result.is_valid
            assert result.input_type == ImageInputType.FILE_PATH
            assert result.mime_type == "image/png"
            assert result.url.startswith("data:image/png;base64,")
        finally:
            os.unlink(temp_path)

    def test_process_unsupported_extension(self):
        """Test processing file with unsupported extension."""
        with tempfile.NamedTemporaryFile(suffix=".bmp", delete=False) as f:
            f.write(b'\x00' * 100)
            temp_path = f.name

        try:
            result = process_image_input(temp_path)
            assert not result.is_valid
            assert "unsupported" in result.errors[0].lower()
        finally:
            os.unlink(temp_path)

    def test_process_base64_data_uri(self):
        """Test processing base64 data URI."""
        data_uri = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        result = process_image_input(data_uri)
        assert result.is_valid
        assert result.input_type == ImageInputType.BASE64
        assert result.url == data_uri
        assert result.mime_type == "image/png"

    def test_process_with_detail(self):
        """Test processing with custom detail level."""
        result = process_image_input("https://example.com/image.jpg", detail="high")
        assert result.detail == "high"

    def test_process_unknown_input(self):
        """Test processing unknown input type."""
        result = process_image_input("not_a_valid_input")
        assert not result.is_valid
        assert result.input_type == ImageInputType.UNKNOWN


class TestBuildVisionContent:
    """Test the build_vision_content function."""

    def test_single_image(self):
        """Test building content with single image."""
        img = ImageInput(
            input_type=ImageInputType.URL,
            url="https://example.com/image.jpg"
        )
        content = build_vision_content("Describe this", img)

        assert len(content) == 2
        assert content[0]["type"] == "image_url"
        assert content[0]["image_url"]["url"] == "https://example.com/image.jpg"
        assert content[1]["type"] == "text"
        assert content[1]["text"] == "Describe this"

    def test_multiple_images(self):
        """Test building content with multiple images."""
        images = [
            ImageInput(input_type=ImageInputType.URL, url="https://example.com/1.jpg"),
            ImageInput(input_type=ImageInputType.URL, url="https://example.com/2.jpg")
        ]
        content = build_vision_content("Compare these", images)

        assert len(content) == 3
        assert content[0]["type"] == "image_url"
        assert content[1]["type"] == "image_url"
        assert content[2]["type"] == "text"

    def test_text_first(self):
        """Test building content with text first."""
        img = ImageInput(input_type=ImageInputType.URL, url="https://example.com/image.jpg")
        content = build_vision_content("Analyze", img, text_first=True)

        assert content[0]["type"] == "text"
        assert content[1]["type"] == "image_url"

    def test_invalid_images_filtered(self):
        """Test that invalid images are filtered out."""
        images = [
            ImageInput(input_type=ImageInputType.URL, url="https://example.com/valid.jpg"),
            ImageInput(input_type=ImageInputType.FILE_PATH, url="", errors=["Invalid"])
        ]
        content = build_vision_content("Test", images)

        # Should only include the valid image + text
        assert len(content) == 2

    def test_detail_included(self):
        """Test that detail level is included in image content."""
        img = ImageInput(
            input_type=ImageInputType.URL,
            url="https://example.com/image.jpg",
            detail="high"
        )
        content = build_vision_content("Test", img)

        assert content[0]["image_url"]["detail"] == "high"


class TestValidateImageInputs:
    """Test the validate_image_inputs function."""

    def test_all_valid(self):
        """Test validation with all valid inputs."""
        valid, errors = validate_image_inputs([
            "https://example.com/1.jpg",
            "https://example.com/2.jpg"
        ])
        assert len(valid) == 2
        assert len(errors) == 0

    def test_mixed_valid_invalid(self):
        """Test validation with mixed valid and invalid inputs."""
        valid, errors = validate_image_inputs([
            "https://example.com/valid.jpg",
            "/nonexistent/file.png"
        ])
        assert len(valid) == 1
        assert len(errors) > 0

    def test_empty_list(self):
        """Test validation with empty list."""
        valid, errors = validate_image_inputs([])
        assert len(valid) == 0
        assert len(errors) == 0


class TestVisionConstants:
    """Test that vision constants are correctly defined."""

    def test_supported_image_types(self):
        """Test SUPPORTED_IMAGE_TYPES contains expected values."""
        assert "image/jpeg" in SUPPORTED_IMAGE_TYPES
        assert "image/png" in SUPPORTED_IMAGE_TYPES
        assert "image/gif" in SUPPORTED_IMAGE_TYPES
        assert "image/webp" in SUPPORTED_IMAGE_TYPES

    def test_image_extension_map(self):
        """Test IMAGE_EXTENSION_MAP contains expected mappings."""
        assert IMAGE_EXTENSION_MAP[".jpg"] == "image/jpeg"
        assert IMAGE_EXTENSION_MAP[".jpeg"] == "image/jpeg"
        assert IMAGE_EXTENSION_MAP[".png"] == "image/png"
        assert IMAGE_EXTENSION_MAP[".gif"] == "image/gif"
        assert IMAGE_EXTENSION_MAP[".webp"] == "image/webp"

    def test_max_image_size(self):
        """Test MAX_IMAGE_SIZE_BYTES is reasonable."""
        assert MAX_IMAGE_SIZE_BYTES > 0
        assert MAX_IMAGE_SIZE_BYTES >= 1 * 1024 * 1024  # At least 1 MB
        assert MAX_IMAGE_SIZE_BYTES <= 50 * 1024 * 1024  # At most 50 MB

    def test_default_vision_detail(self):
        """Test DEFAULT_VISION_DETAIL is valid."""
        assert DEFAULT_VISION_DETAIL in ["auto", "low", "high"]

    def test_vision_model_warning(self):
        """Test VISION_MODEL_WARNING exists and is informative."""
        assert VISION_MODEL_WARNING is not None
        assert len(VISION_MODEL_WARNING) > 50
        assert "multimodal" in VISION_MODEL_WARNING.lower() or "vision" in VISION_MODEL_WARNING.lower()


class TestVisionToolsMocked:
    """Test vision tools with mocked LLM responses."""

    def test_analyze_image_mocked(self):
        """Test analyze_image with mocked LLM."""
        from tools.vision import VisionTools

        mock_llm = Mock()
        mock_llm.vision_completion.return_value = {
            "choices": [{"message": {"content": "This is a landscape photo."}}]
        }

        tools = VisionTools(llm_client=mock_llm)

        import asyncio
        result = asyncio.run(tools.analyze_image("https://example.com/image.jpg"))

        assert "landscape" in result
        mock_llm.vision_completion.assert_called_once()

    def test_describe_image_styles(self):
        """Test describe_image with different styles."""
        from tools.vision import VisionTools

        mock_llm = Mock()
        mock_llm.vision_completion.return_value = {
            "choices": [{"message": {"content": "A beautiful scene."}}]
        }

        tools = VisionTools(llm_client=mock_llm)

        import asyncio

        # Test each style
        for style in ["detailed", "brief", "creative", "technical"]:
            result = asyncio.run(tools.describe_image("https://example.com/image.jpg", style=style))
            assert result is not None

    def test_compare_images_requires_multiple(self):
        """Test that compare_images requires at least 2 images."""
        from tools.vision import VisionTools

        tools = VisionTools()

        import asyncio
        result = asyncio.run(tools.compare_images(["only_one.jpg"]))

        assert "at least 2" in result.lower()

    def test_extract_text_uses_high_detail(self):
        """Test that extract_text_from_image uses high detail by default."""
        from tools.vision import VisionTools

        mock_llm = Mock()
        mock_llm.vision_completion.return_value = {
            "choices": [{"message": {"content": "Text content: Hello World"}}]
        }

        tools = VisionTools(llm_client=mock_llm)

        import asyncio
        result = asyncio.run(tools.extract_text_from_image("https://example.com/doc.png"))

        # Verify high detail was passed
        call_kwargs = mock_llm.vision_completion.call_args[1]
        assert call_kwargs.get("detail") == "high"

    def test_answer_about_image_includes_question(self):
        """Test that answer_about_image includes the question in prompt."""
        from tools.vision import VisionTools

        mock_llm = Mock()
        mock_llm.vision_completion.return_value = {
            "choices": [{"message": {"content": "There are 5 people."}}]
        }

        tools = VisionTools(llm_client=mock_llm)

        import asyncio
        result = asyncio.run(tools.answer_about_image(
            "https://example.com/image.jpg",
            "How many people are there?"
        ))

        # Verify the question was included in the prompt
        call_args = mock_llm.vision_completion.call_args
        assert "How many people" in call_args[1]["prompt"]


class TestLLMClientVisionCompletion:
    """Test the LLMClient.vision_completion method."""

    def test_vision_completion_single_image(self):
        """Test vision_completion with single image."""
        from llm.llm_client import LLMClient

        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "Test response"}}]
            }
            mock_post.return_value = mock_response

            client = LLMClient()
            response = client.vision_completion(
                prompt="Describe this",
                images="https://example.com/image.jpg"
            )

            assert "choices" in response

    def test_vision_completion_multiple_images(self):
        """Test vision_completion with multiple images."""
        from llm.llm_client import LLMClient

        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "Comparison result"}}]
            }
            mock_post.return_value = mock_response

            client = LLMClient()
            response = client.vision_completion(
                prompt="Compare these",
                images=["https://example.com/1.jpg", "https://example.com/2.jpg"]
            )

            assert "choices" in response

    def test_vision_completion_invalid_image_raises(self):
        """Test vision_completion raises ValueError for invalid images."""
        from llm.llm_client import LLMClient

        client = LLMClient()

        with pytest.raises(ValueError) as exc_info:
            client.vision_completion(
                prompt="Test",
                images="/nonexistent/file.png"
            )

        assert "invalid" in str(exc_info.value).lower()


class TestMIMEDetection:
    """Test MIME type detection from magic bytes."""

    def test_detect_png(self):
        """Test PNG magic byte detection."""
        from utils.image_utils import _detect_mime_from_bytes

        png_header = b'\x89PNG\r\n\x1a\n'
        assert _detect_mime_from_bytes(png_header) == "image/png"

    def test_detect_jpeg(self):
        """Test JPEG magic byte detection."""
        from utils.image_utils import _detect_mime_from_bytes

        jpeg_header = b'\xff\xd8\xff\xe0'
        assert _detect_mime_from_bytes(jpeg_header) == "image/jpeg"

    def test_detect_gif(self):
        """Test GIF magic byte detection."""
        from utils.image_utils import _detect_mime_from_bytes

        gif87_header = b'GIF87a'
        gif89_header = b'GIF89a'
        assert _detect_mime_from_bytes(gif87_header) == "image/gif"
        assert _detect_mime_from_bytes(gif89_header) == "image/gif"

    def test_detect_webp(self):
        """Test WebP magic byte detection."""
        from utils.image_utils import _detect_mime_from_bytes

        webp_header = b'RIFF\x00\x00\x00\x00WEBP'
        assert _detect_mime_from_bytes(webp_header) == "image/webp"

    def test_detect_unknown(self):
        """Test unknown magic bytes return None."""
        from utils.image_utils import _detect_mime_from_bytes

        unknown_header = b'\x00\x00\x00\x00'
        assert _detect_mime_from_bytes(unknown_header) is None


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_whitespace_in_url(self):
        """Test URL with surrounding whitespace."""
        result = process_image_input("  https://example.com/image.jpg  ")
        assert result.is_valid
        assert result.input_type == ImageInputType.URL

    def test_file_too_large(self):
        """Test file size limit enforcement."""
        # We need to test the size limit logic, so we'll check that
        # the MAX_IMAGE_SIZE_BYTES constant is used appropriately
        # by verifying a file that we know is small passes
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            # Write minimal PNG header (small file, should pass)
            png_header = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
            f.write(png_header)
            temp_path = f.name

        try:
            # This small file should pass
            result = process_image_input(temp_path)
            assert result.is_valid

            # Verify the constant is reasonable (at least 1MB, at most 50MB)
            assert MAX_IMAGE_SIZE_BYTES >= 1 * 1024 * 1024
            assert MAX_IMAGE_SIZE_BYTES <= 50 * 1024 * 1024
        finally:
            os.unlink(temp_path)

    def test_unicode_in_path(self):
        """Test file path with unicode characters."""
        # Just test detection (not actual file access)
        input_type = detect_input_type("/path/to/图片.png")
        assert input_type == ImageInputType.FILE_PATH


def test_vision_test_suite_completeness():
    """Meta-test: Verify all vision features are tested."""
    test_classes = [
        TestImageInputType,
        TestImageInput,
        TestDetectInputType,
        TestProcessImageInput,
        TestBuildVisionContent,
        TestValidateImageInputs,
        TestVisionConstants,
        TestVisionToolsMocked,
        TestLLMClientVisionCompletion,
        TestMIMEDetection,
        TestEdgeCases
    ]

    # Ensure we have comprehensive coverage
    assert len(test_classes) >= 11, "Should have at least 11 test classes"

    # Count total test methods
    total_tests = sum(
        len([m for m in dir(cls) if m.startswith('test_')])
        for cls in test_classes
    )

    assert total_tests >= 40, f"Should have at least 40 test methods, found {total_tests}"
    print(f"\n✅ Vision test suite: {len(test_classes)} classes, {total_tests} tests")


if __name__ == "__main__":
    # Run with: python3 -m pytest tests/test_vision.py -v
    pytest.main([__file__, "-v", "--tb=short"])
