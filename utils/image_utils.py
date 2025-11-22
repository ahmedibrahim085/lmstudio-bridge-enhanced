#!/usr/bin/env python3
"""
Image utilities for vision/multimodal support.

This module provides utilities for handling image input in various formats
for use with LM Studio's vision-capable models (v0.3.30+).

Supports auto-detection and conversion of:
- File paths (local images)
- URLs (remote images)
- Base64-encoded data (inline images)

Usage:
    from utils.image_utils import process_image_input, ImageInput

    # Auto-detect and process any image input
    result = process_image_input("/path/to/image.png")
    result = process_image_input("https://example.com/image.jpg")
    result = process_image_input("data:image/png;base64,iVBORw0...")

    # Use in vision message
    content = build_vision_content("Describe this image", result)
"""

import os
import re
import base64
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum

from config.constants import (
    SUPPORTED_IMAGE_TYPES,
    IMAGE_EXTENSION_MAP,
    MAX_IMAGE_SIZE_BYTES,
    MAX_IMAGE_DIMENSION,
    DEFAULT_VISION_DETAIL,
    IMAGE_URL_PATTERNS,
    BASE64_DATA_URI_PREFIX
)


class ImageInputType(Enum):
    """Type of image input detected."""
    FILE_PATH = "file_path"
    URL = "url"
    BASE64 = "base64"
    UNKNOWN = "unknown"


@dataclass
class ImageInput:
    """Processed image input ready for API use.

    Attributes:
        input_type: The detected type of input (file_path, url, base64)
        url: The URL or data URI for the image
        mime_type: The MIME type of the image (if known)
        original_input: The original input string
        detail: Vision detail level (auto, low, high)
        errors: List of any errors during processing
        warnings: List of any warnings during processing
    """
    input_type: ImageInputType
    url: str
    mime_type: Optional[str] = None
    original_input: str = ""
    detail: str = DEFAULT_VISION_DETAIL
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Check if the image input is valid for use."""
        return len(self.errors) == 0 and self.url != ""


def detect_input_type(image_input: str) -> ImageInputType:
    """Detect the type of image input.

    Args:
        image_input: The image input string to analyze

    Returns:
        ImageInputType enum indicating the detected type
    """
    if not image_input or not isinstance(image_input, str):
        return ImageInputType.UNKNOWN

    image_input = image_input.strip()

    # Check for base64 data URI first (most specific)
    if image_input.startswith(BASE64_DATA_URI_PREFIX):
        return ImageInputType.BASE64

    # Check for raw base64 (no data URI prefix, but valid base64 pattern)
    if _is_likely_base64(image_input):
        return ImageInputType.BASE64

    # Check for URL patterns
    for pattern in IMAGE_URL_PATTERNS:
        if re.match(pattern, image_input, re.IGNORECASE):
            return ImageInputType.URL

    # Check if it looks like a file path
    if _is_likely_file_path(image_input):
        return ImageInputType.FILE_PATH

    return ImageInputType.UNKNOWN


def _is_likely_base64(s: str) -> bool:
    """Check if string is likely base64 encoded image data.

    Args:
        s: String to check

    Returns:
        True if string appears to be base64 encoded
    """
    # Base64 strings are long and contain only valid base64 characters
    if len(s) < 100:  # Too short to be an image
        return False

    # Check for base64 character set (with optional padding)
    base64_pattern = r'^[A-Za-z0-9+/]+=*$'
    return bool(re.match(base64_pattern, s.replace('\n', '').replace('\r', '')))


def _is_likely_file_path(s: str) -> bool:
    """Check if string is likely a file path.

    Args:
        s: String to check

    Returns:
        True if string appears to be a file path
    """
    # Check for common path patterns
    if s.startswith('/') or s.startswith('./') or s.startswith('../'):
        return True

    # Windows paths
    if re.match(r'^[A-Za-z]:\\', s):
        return True

    # Check for image extension
    ext = Path(s).suffix.lower()
    if ext in IMAGE_EXTENSION_MAP:
        return True

    # Check if path exists (for ambiguous cases)
    if os.path.exists(s):
        return True

    return False


def process_image_input(
    image_input: str,
    detail: str = DEFAULT_VISION_DETAIL
) -> ImageInput:
    """Process any image input and prepare it for the vision API.

    Automatically detects the input type and converts to the appropriate format:
    - File paths: Read and convert to base64 data URI
    - URLs: Pass through directly
    - Base64: Wrap in data URI if needed

    Args:
        image_input: The image input (file path, URL, or base64)
        detail: Vision detail level (auto, low, high)

    Returns:
        ImageInput object with processed URL and metadata
    """
    input_type = detect_input_type(image_input)

    if input_type == ImageInputType.FILE_PATH:
        return _process_file_path(image_input, detail)
    elif input_type == ImageInputType.URL:
        return _process_url(image_input, detail)
    elif input_type == ImageInputType.BASE64:
        return _process_base64(image_input, detail)
    else:
        return ImageInput(
            input_type=ImageInputType.UNKNOWN,
            url="",
            original_input=image_input,
            detail=detail,
            errors=[f"Could not detect image input type for: {image_input[:50]}..."]
        )


def _process_file_path(file_path: str, detail: str) -> ImageInput:
    """Process a local file path into a base64 data URI.

    Args:
        file_path: Path to the local image file
        detail: Vision detail level

    Returns:
        ImageInput with base64 data URI
    """
    errors = []
    warnings = []

    # Resolve and validate path
    path = Path(file_path).expanduser().resolve()

    if not path.exists():
        return ImageInput(
            input_type=ImageInputType.FILE_PATH,
            url="",
            original_input=file_path,
            detail=detail,
            errors=[f"File not found: {file_path}"]
        )

    if not path.is_file():
        return ImageInput(
            input_type=ImageInputType.FILE_PATH,
            url="",
            original_input=file_path,
            detail=detail,
            errors=[f"Path is not a file: {file_path}"]
        )

    # Check file extension
    ext = path.suffix.lower()
    if ext not in IMAGE_EXTENSION_MAP:
        return ImageInput(
            input_type=ImageInputType.FILE_PATH,
            url="",
            original_input=file_path,
            detail=detail,
            errors=[f"Unsupported image format: {ext}. Supported: {list(IMAGE_EXTENSION_MAP.keys())}"]
        )

    mime_type = IMAGE_EXTENSION_MAP[ext]

    # Check file size
    file_size = path.stat().st_size
    if file_size > MAX_IMAGE_SIZE_BYTES:
        return ImageInput(
            input_type=ImageInputType.FILE_PATH,
            url="",
            original_input=file_path,
            mime_type=mime_type,
            detail=detail,
            errors=[f"File too large: {file_size / (1024*1024):.1f} MB. Maximum: {MAX_IMAGE_SIZE_BYTES / (1024*1024):.0f} MB"]
        )

    if file_size > MAX_IMAGE_SIZE_BYTES * 0.8:
        warnings.append(f"Large file: {file_size / (1024*1024):.1f} MB. May cause slow processing.")

    # Read and encode file
    try:
        with open(path, 'rb') as f:
            image_data = f.read()

        base64_data = base64.b64encode(image_data).decode('utf-8')
        data_uri = f"data:{mime_type};base64,{base64_data}"

        return ImageInput(
            input_type=ImageInputType.FILE_PATH,
            url=data_uri,
            mime_type=mime_type,
            original_input=file_path,
            detail=detail,
            warnings=warnings
        )

    except IOError as e:
        return ImageInput(
            input_type=ImageInputType.FILE_PATH,
            url="",
            original_input=file_path,
            detail=detail,
            errors=[f"Failed to read file: {str(e)}"]
        )


def _process_url(url: str, detail: str) -> ImageInput:
    """Process an image URL by fetching and converting to base64.

    LM Studio requires base64-encoded images, so we fetch the URL content
    and convert it to a data URI.

    Args:
        url: The image URL
        detail: Vision detail level

    Returns:
        ImageInput with base64 data URI (not the original URL)
    """
    import requests

    warnings = []

    # Try to infer MIME type from URL extension
    mime_type = None
    url_path = url.split('?')[0]  # Remove query string
    ext = Path(url_path).suffix.lower()
    if ext in IMAGE_EXTENSION_MAP:
        mime_type = IMAGE_EXTENSION_MAP[ext]

    # Fetch the image from URL
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; LMStudioBridge/3.2; +https://github.com/ahmedibrahim085/lmstudio-bridge-enhanced)'
        }
        response = requests.get(url, timeout=30, stream=True, headers=headers)
        response.raise_for_status()

        # Check content length if available
        content_length = response.headers.get('content-length')
        if content_length and int(content_length) > MAX_IMAGE_SIZE_BYTES:
            return ImageInput(
                input_type=ImageInputType.URL,
                url="",
                original_input=url,
                detail=detail,
                errors=[f"Image too large: {int(content_length) / (1024*1024):.1f} MB. Maximum: {MAX_IMAGE_SIZE_BYTES / (1024*1024):.0f} MB"]
            )

        # Read image data
        image_data = response.content

        # Check actual size
        if len(image_data) > MAX_IMAGE_SIZE_BYTES:
            return ImageInput(
                input_type=ImageInputType.URL,
                url="",
                original_input=url,
                detail=detail,
                errors=[f"Image too large: {len(image_data) / (1024*1024):.1f} MB. Maximum: {MAX_IMAGE_SIZE_BYTES / (1024*1024):.0f} MB"]
            )

        # Detect MIME type from content if not known
        if mime_type is None:
            detected_mime = _detect_mime_from_bytes(image_data[:16])
            if detected_mime:
                mime_type = detected_mime
            else:
                # Try from content-type header
                content_type = response.headers.get('content-type', '')
                if content_type.startswith('image/'):
                    mime_type = content_type.split(';')[0]
                else:
                    mime_type = "image/jpeg"  # Default assumption
                    warnings.append("Could not determine image type. Assuming JPEG.")

        # Convert to base64
        base64_data = base64.b64encode(image_data).decode('utf-8')
        data_uri = f"data:{mime_type};base64,{base64_data}"

        return ImageInput(
            input_type=ImageInputType.URL,
            url=data_uri,  # Return data URI, not original URL
            mime_type=mime_type,
            original_input=url,
            detail=detail,
            warnings=warnings
        )

    except requests.exceptions.Timeout:
        return ImageInput(
            input_type=ImageInputType.URL,
            url="",
            original_input=url,
            detail=detail,
            errors=["Timeout fetching image from URL (30s limit)"]
        )
    except requests.exceptions.RequestException as e:
        return ImageInput(
            input_type=ImageInputType.URL,
            url="",
            original_input=url,
            detail=detail,
            errors=[f"Failed to fetch image from URL: {str(e)}"]
        )


def _process_base64(base64_input: str, detail: str) -> ImageInput:
    """Process base64-encoded image data.

    Args:
        base64_input: Base64 string (with or without data URI prefix)
        detail: Vision detail level

    Returns:
        ImageInput with data URI
    """
    warnings = []

    # If already has data URI prefix, validate and return
    if base64_input.startswith(BASE64_DATA_URI_PREFIX):
        # Extract MIME type from data URI
        match = re.match(r'data:(image/[^;]+);base64,(.+)', base64_input)
        if match:
            mime_type = match.group(1)
            if mime_type not in SUPPORTED_IMAGE_TYPES:
                warnings.append(f"Unusual MIME type: {mime_type}. May not be supported.")
            return ImageInput(
                input_type=ImageInputType.BASE64,
                url=base64_input,
                mime_type=mime_type,
                original_input=base64_input[:50] + "...",
                detail=detail,
                warnings=warnings
            )

    # Raw base64 without prefix - assume PNG (most common for generated images)
    # Clean up the base64 string
    clean_base64 = base64_input.replace('\n', '').replace('\r', '').replace(' ', '')

    # Validate base64
    try:
        # Try to decode to verify it's valid base64
        decoded = base64.b64decode(clean_base64)
        # Check for image magic bytes
        mime_type = _detect_mime_from_bytes(decoded[:16])
        if mime_type is None:
            mime_type = "image/png"  # Default assumption
            warnings.append("Could not detect image type from data. Assuming PNG.")

        data_uri = f"data:{mime_type};base64,{clean_base64}"

        return ImageInput(
            input_type=ImageInputType.BASE64,
            url=data_uri,
            mime_type=mime_type,
            original_input=base64_input[:50] + "...",
            detail=detail,
            warnings=warnings
        )

    except Exception as e:
        return ImageInput(
            input_type=ImageInputType.BASE64,
            url="",
            original_input=base64_input[:50] + "...",
            detail=detail,
            errors=[f"Invalid base64 data: {str(e)}"]
        )


def _detect_mime_from_bytes(data: bytes) -> Optional[str]:
    """Detect MIME type from image magic bytes.

    Args:
        data: First few bytes of the image

    Returns:
        MIME type string or None if unknown
    """
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return "image/png"
    elif data[:2] == b'\xff\xd8':
        return "image/jpeg"
    elif data[:6] in (b'GIF87a', b'GIF89a'):
        return "image/gif"
    elif data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return "image/webp"
    return None


def build_vision_content(
    prompt: str,
    images: Union[ImageInput, List[ImageInput]],
    text_first: bool = False
) -> List[Dict[str, Any]]:
    """Build the content array for a vision message.

    Creates the properly formatted content array with text and image(s)
    for use with the chat completion API.

    Args:
        prompt: The text prompt
        images: Single ImageInput or list of ImageInputs
        text_first: If True, put text before images (default: images first)

    Returns:
        List of content items for the message

    Example:
        >>> img = process_image_input("/path/to/image.png")
        >>> content = build_vision_content("What's in this image?", img)
        >>> message = {"role": "user", "content": content}
    """
    if isinstance(images, ImageInput):
        images = [images]

    content = []

    # Build image content items
    image_items = []
    for img in images:
        if img.is_valid:
            image_items.append({
                "type": "image_url",
                "image_url": {
                    "url": img.url,
                    "detail": img.detail
                }
            })

    # Build text content item
    text_item = {
        "type": "text",
        "text": prompt
    }

    # Order based on preference
    if text_first:
        content.append(text_item)
        content.extend(image_items)
    else:
        content.extend(image_items)
        content.append(text_item)

    return content


def validate_image_inputs(images: List[str]) -> Tuple[List[ImageInput], List[str]]:
    """Validate multiple image inputs.

    Args:
        images: List of image inputs (paths, URLs, or base64)

    Returns:
        Tuple of (valid ImageInputs, error messages)
    """
    valid_inputs = []
    errors = []

    for i, img in enumerate(images):
        result = process_image_input(img)
        if result.is_valid:
            valid_inputs.append(result)
        else:
            errors.extend([f"Image {i+1}: {e}" for e in result.errors])

    return valid_inputs, errors


__all__ = [
    "ImageInputType",
    "ImageInput",
    "detect_input_type",
    "process_image_input",
    "build_vision_content",
    "validate_image_inputs"
]
