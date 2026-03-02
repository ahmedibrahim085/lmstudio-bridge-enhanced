"""Smart model selection constants — task mapping and scoring weights."""

__all__ = [
    "TASK_CAPABILITY_MAP",
    "SELECTION_WEIGHT_CAPABILITY",
    "SELECTION_WEIGHT_CONFIDENCE",
    "SELECTION_FALLBACK_SORT_KEY",
    "SELECTION_ERROR_NO_MODELS",
    "SELECTION_ERROR_INTERNAL",
]

# OPP-08: Maps task_type strings to ModelCapabilities attribute names
TASK_CAPABILITY_MAP: dict[str, str] = {
    "code_generation": "coding",
    "code_review": "coding",
    "coding": "coding",
    "summarization": "long_context",
    "long_document": "long_context",
    "reasoning": "reasoning",
    "analysis": "reasoning",
    "math": "reasoning",
    "tool_use": "tool_calling",
    "agents": "tool_calling",
    "function_calling": "tool_calling",
    "vision": "vision",
    "image_analysis": "vision",
    "multimodal": "vision",
}

# Scoring weights for smart model selection
SELECTION_WEIGHT_CAPABILITY = 1.0   # Weight for the primary capability score
SELECTION_WEIGHT_CONFIDENCE = 1.0   # Weight for the confidence multiplier

# Fallback sort key when scores are tied
SELECTION_FALLBACK_SORT_KEY = "model_id"

# Error code constants for MCP tool responses
SELECTION_ERROR_NO_MODELS = "no_models_available"
SELECTION_ERROR_INTERNAL = "selection_error"
