#!/usr/bin/env python3
"""
Multi-modal input builder for autonomous loops (OPP-09).

Encapsulates text + optional images into a single object that can be
serialised to either OpenAI chat-completion format or /v1/responses format.

Uses the existing image processing infrastructure from utils/image_utils.py
(process_image_input, build_vision_content) so all image type detection and
base64 conversion is handled consistently.

Usage::

    from llm.multimodal_input import MultiModalInput

    # Text only — behaves identically to a plain string
    mmi = MultiModalInput(text="Summarise this document")
    messages = mmi.to_chat_messages()           # [{"role": "user", "content": "..."}]

    # Text + images
    mmi = MultiModalInput(
        text="Describe the chart",
        images=["data:image/png;base64,...", "/path/to/image.png"],
    )
    messages = mmi.to_chat_messages()           # multi-modal content array
    responses_input = mmi.to_responses_input()  # str | list[dict]
"""

from __future__ import annotations

from config.constants import MULTIMODAL_DETAIL_DEFAULT
from utils.image_utils import ImageInput, build_vision_content, process_image_input


class MultiModalInput:
    """Encapsulates text + optional images for autonomous loop input.

    Lazy-processes image inputs on first access and caches the result so
    repeated calls to :py:meth:`to_chat_messages` or
    :py:meth:`to_responses_input` pay the processing cost only once.

    Args:
        text: The task/prompt text.
        images: Optional list of image inputs.  Each item may be a local file
            path, a URL, or a base64-encoded data URI.  URLs are fetched and
            converted to base64 data URIs by :func:`process_image_input`.
    """

    def __init__(
        self,
        text: str,
        images: list[str] | None = None,
    ) -> None:
        self.text = text
        self.images = images
        # Private cache — populated lazily by the `processed_images` property
        self._processed: list[ImageInput] | None = None

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def has_images(self) -> bool:
        """Whether this input contains at least one image."""
        return bool(self.images)

    @property
    def processed_images(self) -> list[ImageInput]:
        """Lazy-process and cache image inputs.

        Returns an empty list when :attr:`images` is ``None`` or empty.
        Results are cached after the first call.
        """
        if self._processed is not None:
            return self._processed

        if not self.images:
            self._processed = []
            return self._processed

        self._processed = [
            process_image_input(img, detail=MULTIMODAL_DETAIL_DEFAULT)
            for img in self.images
        ]
        return self._processed

    @property
    def image_errors(self) -> list[str]:
        """Return any errors collected during image processing."""
        errors: list[str] = []
        for img_input in self.processed_images:
            errors.extend(img_input.errors)
        return errors

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_chat_messages(self, role: str = "user") -> list[dict]:
        """Convert to OpenAI chat completion message format.

        - **Text only**: returns ``[{"role": role, "content": text}]``.
        - **With images**: returns a single message whose ``content`` is a
          list of ``image_url`` and ``text`` content items, using
          :func:`build_vision_content`.  Invalid images are silently skipped.

        Args:
            role: The message role (default ``"user"``).

        Returns:
            A list containing exactly one message dict.
        """
        if not self.has_images:
            return [{"role": role, "content": self.text}]

        valid_images = [img for img in self.processed_images if img.is_valid]

        if not valid_images:
            # All images failed processing — fall back to text-only
            return [{"role": role, "content": self.text}]

        content = build_vision_content(self.text, valid_images)
        return [{"role": role, "content": content}]

    def to_responses_input(self) -> str | list[dict]:
        """Convert to /v1/responses input format.

        - **Text only**: returns the plain text string.
        - **With images**: returns a list of content dicts with
          ``image_url`` items (one per valid image) followed by a ``text``
          item.  Invalid images are silently skipped.

        Returns:
            Plain string when there are no images, otherwise a list of dicts.
        """
        if not self.has_images:
            return self.text

        valid_images = [img for img in self.processed_images if img.is_valid]

        if not valid_images:
            return self.text

        content: list[dict] = []
        for img in valid_images:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": img.url,
                    "detail": img.detail,
                },
            })
        content.append({"type": "text", "text": self.text})
        return content

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __repr__(self) -> str:  # pragma: no cover
        image_count = len(self.images) if self.images else 0
        return (
            f"MultiModalInput(text={self.text!r:.40}, images={image_count})"
        )


__all__ = ["MultiModalInput"]
