"""Image and multimodal vision constants."""

__all__ = [
    "SUPPORTED_IMAGE_TYPES",
    "IMAGE_EXTENSION_MAP",
    "MAX_IMAGE_SIZE_BYTES",
    "MAX_IMAGE_DIMENSION",
    "DEFAULT_VISION_DETAIL",
    "VISION_INPUT_TYPES",
    "IMAGE_URL_PATTERNS",
    "BASE64_DATA_URI_PREFIX",
    "MULTIMODAL_DETAIL_DEFAULT",
    "MAX_IMAGES_PER_AUTONOMOUS_INPUT",
]

# Supported image MIME types for vision models
SUPPORTED_IMAGE_TYPES = [
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp"
]

# File extensions mapped to MIME types
IMAGE_EXTENSION_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp"
}

# Maximum image size in bytes (10 MB default)
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

# Maximum image dimension (width or height) in pixels
MAX_IMAGE_DIMENSION = 4096

# Default detail level for vision requests
DEFAULT_VISION_DETAIL = "auto"

# Vision input types for auto-detection
VISION_INPUT_TYPES = ["file_path", "url", "base64"]

# URL patterns for detecting image URLs
IMAGE_URL_PATTERNS = [
    r"^https?://.*\.(jpg|jpeg|png|gif|webp)(\?.*)?$",
    r"^https?://.*",  # Any URL (model will validate)
]

# Base64 data URI prefix pattern
BASE64_DATA_URI_PREFIX = "data:image/"

# OPP-09: Multi-modal autonomous loops
# Reuses DEFAULT_VISION_DETAIL — "auto" lets the model decide
MULTIMODAL_DETAIL_DEFAULT = DEFAULT_VISION_DETAIL  # "auto"

# Maximum number of images allowed per autonomous loop input
MAX_IMAGES_PER_AUTONOMOUS_INPUT = 5
