#!/usr/bin/env python3
"""
Vision tools for LM Studio multimodal support (v0.3.30+).

This module provides MCP tools for image analysis using vision-capable
models in LM Studio.

Supported input formats (auto-detected):
- File paths: /path/to/image.png
- URLs: https://example.com/image.jpg
- Base64: data:image/png;base64,... or raw base64 string

Requires a vision-capable model loaded in LM Studio (e.g., LLaVA, Qwen-VL).
"""

from typing import Optional, List, Dict, Any
from llm.llm_client import LLMClient
from config.constants import VISION_MODEL_WARNING, DEFAULT_VISION_DETAIL
import json


class VisionTools:
    """Tools for image analysis with vision-capable LLMs."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """Initialize vision tools.

        Args:
            llm_client: Optional LLM client (creates default if None)
        """
        self.llm = llm_client or LLMClient()

    def _extract_response(self, response: Dict[str, Any]) -> str:
        """Extract text content from LLM response.

        Args:
            response: Raw LLM API response

        Returns:
            The text content from the response
        """
        choices = response.get("choices", [])
        if not choices:
            return "Error: No response generated"

        message = choices[0].get("message", {})
        content = message.get("content", "")

        if not content:
            return "Error: Empty response from model"

        return content

    async def analyze_image(
        self,
        image: str,
        prompt: str = "Analyze this image in detail. Describe what you see, including objects, people, text, colors, composition, and any notable features.",
        detail: str = DEFAULT_VISION_DETAIL
    ) -> str:
        """Analyze an image and provide detailed observations.

        Args:
            image: Image input (file path, URL, or base64)
            prompt: Analysis prompt (default: comprehensive analysis)
            detail: Vision detail level (auto, low, high)

        Returns:
            Detailed analysis of the image
        """
        try:
            response = self.llm.vision_completion(
                prompt=prompt,
                images=image,
                detail=detail
            )
            return self._extract_response(response)
        except ValueError as e:
            return f"Error: {str(e)}"
        except Exception as e:
            return f"Error analyzing image: {str(e)}"

    async def describe_image(
        self,
        image: str,
        style: str = "detailed",
        detail: str = DEFAULT_VISION_DETAIL
    ) -> str:
        """Generate a description of an image.

        Args:
            image: Image input (file path, URL, or base64)
            style: Description style - "detailed", "brief", "creative", or "technical"
            detail: Vision detail level (auto, low, high)

        Returns:
            Description of the image
        """
        style_prompts = {
            "detailed": "Provide a detailed description of this image, covering all visible elements, their arrangement, colors, lighting, and mood.",
            "brief": "Describe this image in 2-3 sentences, focusing on the main subject and key details.",
            "creative": "Write a creative, evocative description of this image as if describing a scene in a novel.",
            "technical": "Provide a technical description of this image, including composition, color palette, lighting conditions, and any visible technical details."
        }

        prompt = style_prompts.get(style, style_prompts["detailed"])

        try:
            response = self.llm.vision_completion(
                prompt=prompt,
                images=image,
                detail=detail
            )
            return self._extract_response(response)
        except ValueError as e:
            return f"Error: {str(e)}"
        except Exception as e:
            return f"Error describing image: {str(e)}"

    async def compare_images(
        self,
        images: List[str],
        comparison_type: str = "differences",
        detail: str = DEFAULT_VISION_DETAIL
    ) -> str:
        """Compare multiple images and identify similarities or differences.

        Args:
            images: List of image inputs (file paths, URLs, or base64)
            comparison_type: Type of comparison - "differences", "similarities", or "both"
            detail: Vision detail level (auto, low, high)

        Returns:
            Comparison analysis of the images
        """
        if len(images) < 2:
            return "Error: At least 2 images required for comparison"

        comparison_prompts = {
            "differences": f"Compare these {len(images)} images and identify all the differences between them. List each difference clearly.",
            "similarities": f"Compare these {len(images)} images and identify what they have in common. List each similarity clearly.",
            "both": f"Compare these {len(images)} images. First, list their similarities, then list their differences."
        }

        prompt = comparison_prompts.get(comparison_type, comparison_prompts["differences"])

        try:
            response = self.llm.vision_completion(
                prompt=prompt,
                images=images,
                detail=detail
            )
            return self._extract_response(response)
        except ValueError as e:
            return f"Error: {str(e)}"
        except Exception as e:
            return f"Error comparing images: {str(e)}"

    async def extract_text_from_image(
        self,
        image: str,
        detail: str = "high"  # High detail for text extraction
    ) -> str:
        """Extract and transcribe all visible text from an image (OCR).

        Args:
            image: Image input (file path, URL, or base64)
            detail: Vision detail level (default: high for better text recognition)

        Returns:
            Extracted text from the image
        """
        prompt = """Extract all visible text from this image.
Include:
- All text exactly as it appears (preserve formatting where possible)
- Labels, captions, signs, or annotations
- Any text in different languages
- Numbers, dates, or codes

If no text is visible, state that clearly."""

        try:
            response = self.llm.vision_completion(
                prompt=prompt,
                images=image,
                detail=detail
            )
            return self._extract_response(response)
        except ValueError as e:
            return f"Error: {str(e)}"
        except Exception as e:
            return f"Error extracting text: {str(e)}"

    async def identify_objects(
        self,
        image: str,
        detail: str = DEFAULT_VISION_DETAIL
    ) -> str:
        """Identify and list all objects visible in an image.

        Args:
            image: Image input (file path, URL, or base64)
            detail: Vision detail level (auto, low, high)

        Returns:
            JSON-formatted list of identified objects
        """
        prompt = """Identify all objects visible in this image.
For each object, provide:
1. Object name/type
2. Approximate location (e.g., center, top-left, background)
3. Brief description (size, color, condition)

Format the response as a structured list."""

        try:
            response = self.llm.vision_completion(
                prompt=prompt,
                images=image,
                detail=detail
            )
            return self._extract_response(response)
        except ValueError as e:
            return f"Error: {str(e)}"
        except Exception as e:
            return f"Error identifying objects: {str(e)}"

    async def answer_about_image(
        self,
        image: str,
        question: str,
        detail: str = DEFAULT_VISION_DETAIL
    ) -> str:
        """Answer a specific question about an image.

        Args:
            image: Image input (file path, URL, or base64)
            question: The question to answer about the image
            detail: Vision detail level (auto, low, high)

        Returns:
            Answer to the question based on the image
        """
        prompt = f"Looking at this image, please answer the following question:\n\n{question}"

        try:
            response = self.llm.vision_completion(
                prompt=prompt,
                images=image,
                detail=detail
            )
            return self._extract_response(response)
        except ValueError as e:
            return f"Error: {str(e)}"
        except Exception as e:
            return f"Error answering question: {str(e)}"


def register_vision_tools(mcp, llm_client: Optional[LLMClient] = None):
    """Register vision tools with FastMCP server.

    Args:
        mcp: FastMCP server instance
        llm_client: Optional LLM client
    """
    tools = VisionTools(llm_client)

    @mcp.tool()
    async def analyze_image(
        image: str,
        prompt: str = "Analyze this image in detail. Describe what you see, including objects, people, text, colors, composition, and any notable features.",
        detail: str = "auto"
    ) -> str:
        """
        Analyze an image using a vision-capable local LLM.

        ## Input Formats (Auto-Detected)
        The image parameter accepts ANY of these formats:
        - **File path**: `/path/to/image.png` or `./relative/path.jpg`
        - **URL**: `https://example.com/image.jpg`
        - **Base64**: `data:image/png;base64,iVBORw0...` or raw base64 string

        ## Requirements
        Requires a multimodal/vision model loaded in LM Studio:
        - LLaVA variants (llava-v1.5, llava-v1.6, etc.)
        - Qwen-VL (qwen-vl-chat, etc.)
        - GPT-4V compatible models
        - Other vision-capable models

        Text-only models will return an error.

        ## Examples
        ```python
        # Analyze local file
        analyze_image(image="/Users/me/photos/landscape.jpg")

        # Analyze from URL
        analyze_image(image="https://example.com/chart.png")

        # Custom analysis prompt
        analyze_image(
            image="/path/to/diagram.png",
            prompt="Explain the workflow shown in this diagram"
        )

        # Use high detail for complex images
        analyze_image(
            image="/path/to/document.png",
            detail="high"
        )
        ```

        Args:
            image: Image to analyze (file path, URL, or base64 - auto-detected)
            prompt: What to analyze or look for (default: comprehensive analysis)
            detail: Detail level - "auto" (default), "low" (faster), or "high" (more accurate)

        Returns:
            Detailed analysis of the image from the vision model
        """
        return await tools.analyze_image(image, prompt, detail)

    @mcp.tool()
    async def describe_image(
        image: str,
        style: str = "detailed",
        detail: str = "auto"
    ) -> str:
        """
        Generate a description of an image.

        ## Input Formats (Auto-Detected)
        - **File path**: `/path/to/image.png`
        - **URL**: `https://example.com/image.jpg`
        - **Base64**: `data:image/png;base64,...` or raw base64

        ## Description Styles
        - **detailed**: Comprehensive description of all elements
        - **brief**: 2-3 sentence summary
        - **creative**: Evocative, narrative description
        - **technical**: Focus on composition, lighting, technical aspects

        ## Examples
        ```python
        # Get detailed description
        describe_image(image="/path/to/photo.jpg")

        # Brief summary
        describe_image(image="/path/to/photo.jpg", style="brief")

        # Creative writing style
        describe_image(image="/path/to/landscape.jpg", style="creative")
        ```

        Args:
            image: Image to describe (file path, URL, or base64 - auto-detected)
            style: Description style - "detailed", "brief", "creative", or "technical"
            detail: Vision detail level - "auto", "low", or "high"

        Returns:
            Description of the image in the requested style
        """
        return await tools.describe_image(image, style, detail)

    @mcp.tool()
    async def compare_images(
        images: List[str],
        comparison_type: str = "differences",
        detail: str = "auto"
    ) -> str:
        """
        Compare multiple images and identify similarities or differences.

        ## Input Formats (Auto-Detected)
        Each image in the list can be:
        - **File path**: `/path/to/image.png`
        - **URL**: `https://example.com/image.jpg`
        - **Base64**: `data:image/png;base64,...`

        ## Comparison Types
        - **differences**: Focus on what's different between images
        - **similarities**: Focus on what's common across images
        - **both**: List both similarities and differences

        ## Examples
        ```python
        # Compare two versions of a design
        compare_images(
            images=["/path/to/design_v1.png", "/path/to/design_v2.png"],
            comparison_type="differences"
        )

        # Find common elements across multiple images
        compare_images(
            images=["img1.jpg", "img2.jpg", "img3.jpg"],
            comparison_type="similarities"
        )

        # Full comparison
        compare_images(
            images=["before.png", "after.png"],
            comparison_type="both"
        )
        ```

        Args:
            images: List of images to compare (minimum 2, each can be file path/URL/base64)
            comparison_type: Type of comparison - "differences", "similarities", or "both"
            detail: Vision detail level - "auto", "low", or "high"

        Returns:
            Detailed comparison analysis of the images
        """
        return await tools.compare_images(images, comparison_type, detail)

    @mcp.tool()
    async def extract_text_from_image(
        image: str,
        detail: str = "high"
    ) -> str:
        """
        Extract all visible text from an image (OCR-like functionality).

        ## Input Formats (Auto-Detected)
        - **File path**: `/path/to/document.png`
        - **URL**: `https://example.com/screenshot.jpg`
        - **Base64**: `data:image/png;base64,...`

        ## Best For
        - Screenshots with text
        - Photos of documents or signs
        - Images with labels or annotations
        - Diagrams with text elements

        ## Examples
        ```python
        # Extract text from a screenshot
        extract_text_from_image(image="/path/to/screenshot.png")

        # Extract from document photo
        extract_text_from_image(image="https://example.com/receipt.jpg")
        ```

        Args:
            image: Image containing text (file path, URL, or base64 - auto-detected)
            detail: Vision detail level - defaults to "high" for better text recognition

        Returns:
            All visible text extracted from the image
        """
        return await tools.extract_text_from_image(image, detail)

    @mcp.tool()
    async def identify_objects(
        image: str,
        detail: str = "auto"
    ) -> str:
        """
        Identify and list all objects visible in an image.

        ## Input Formats (Auto-Detected)
        - **File path**: `/path/to/image.png`
        - **URL**: `https://example.com/image.jpg`
        - **Base64**: `data:image/png;base64,...`

        ## Output Format
        Returns a structured list of objects with:
        - Object name/type
        - Approximate location
        - Brief description

        ## Examples
        ```python
        # Identify objects in a room photo
        identify_objects(image="/path/to/room.jpg")

        # Analyze a product photo
        identify_objects(image="https://example.com/product.png")
        ```

        Args:
            image: Image to analyze (file path, URL, or base64 - auto-detected)
            detail: Vision detail level - "auto", "low", or "high"

        Returns:
            Structured list of identified objects with locations and descriptions
        """
        return await tools.identify_objects(image, detail)

    @mcp.tool()
    async def answer_about_image(
        image: str,
        question: str,
        detail: str = "auto"
    ) -> str:
        """
        Answer a specific question about an image.

        ## Input Formats (Auto-Detected)
        - **File path**: `/path/to/image.png`
        - **URL**: `https://example.com/image.jpg`
        - **Base64**: `data:image/png;base64,...`

        ## Use Cases
        - Ask specific questions about image content
        - Get counts or measurements
        - Verify information visible in image
        - Request specific details

        ## Examples
        ```python
        # Ask about specific content
        answer_about_image(
            image="/path/to/chart.png",
            question="What is the value shown for Q3 2024?"
        )

        # Count objects
        answer_about_image(
            image="/path/to/photo.jpg",
            question="How many people are in this image?"
        )

        # Verify information
        answer_about_image(
            image="/path/to/screenshot.png",
            question="What error message is displayed?"
        )
        ```

        Args:
            image: Image to analyze (file path, URL, or base64 - auto-detected)
            question: The specific question to answer about the image
            detail: Vision detail level - "auto", "low", or "high"

        Returns:
            Answer to the question based on the image content
        """
        return await tools.answer_about_image(image, question, detail)


__all__ = [
    "VisionTools",
    "register_vision_tools"
]
