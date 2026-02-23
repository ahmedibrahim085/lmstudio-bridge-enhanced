"""
Model Management Fixtures for Tests.

Ensures models are loaded before tests run. Delegates ALL operations
to LMSHelper (DOGFOODING) — no raw subprocess calls.
"""

import pytest
from llm.exceptions import ModelMemoryError
from utils.lms_helper import LMSHelper
from tests.fixtures.model_discovery import discover_models


def ensure_model_loaded(model_name: str) -> bool:
    """
    Ensure a specific model is loaded in LM Studio.

    Delegates to LMSHelper.ensure_model_loaded() instead of raw subprocess.

    Args:
        model_name: Model identifier (e.g., "qwen/qwen3-coder-30b")

    Returns:
        True if model is loaded, False otherwise

    Raises:
        ModelMemoryError: If model cannot be loaded due to insufficient memory
    """
    if not LMSHelper.is_installed():
        print("❌ lms CLI not found. Install with: brew install lmstudio-ai/lmstudio/lms")
        return False

    try:
        if LMSHelper.is_model_loaded(model_name):
            return True

        print(f"⚠️  Model '{model_name}' not loaded. Attempting to load...")
        success = LMSHelper.load_model(model_name)

        if success:
            print(f"✅ Model '{model_name}' loaded successfully")
            return True
        else:
            print(f"❌ Failed to load model '{model_name}'")
            return False

    except ModelMemoryError:
        raise  # Re-raise for proper handling by callers
    except Exception as e:
        print(f"❌ Error ensuring model loaded: {e}")
        return False


def _require_model(model: str):
    """Helper to require a model with proper error handling."""
    try:
        if not ensure_model_loaded(model):
            pytest.skip(f"Model '{model}' could not be loaded")
    except ModelMemoryError as e:
        pytest.skip(f"Model '{model}' requires too much memory: {e.required_memory or 'unknown'}")


@pytest.fixture
def require_qwen_coder():
    """Fixture to ensure qwen/qwen3-coder-30b is loaded."""
    _require_model("qwen/qwen3-coder-30b")


@pytest.fixture
def require_qwen_thinking():
    """Fixture to ensure qwen/qwen3-4b-thinking-2507 is loaded."""
    _require_model("qwen/qwen3-4b-thinking-2507")


@pytest.fixture
def require_magistral():
    """Fixture to ensure mistralai/magistral-small-2509 is loaded."""
    _require_model("mistralai/magistral-small-2509")


@pytest.fixture
def require_deepseek_r1():
    """Fixture to ensure deepseek/deepseek-r1-0528-qwen3-8b is loaded."""
    _require_model("deepseek/deepseek-r1-0528-qwen3-8b")


def get_default_model() -> str | None:
    """
    Get the currently loaded model (default).

    Delegates to LMSHelper.list_loaded_models() instead of raw subprocess.

    Returns:
        Model name if one is loaded, None otherwise
    """
    try:
        loaded = LMSHelper.list_loaded_models()
        if not loaded:
            return None

        # Return the base name of the first loaded model
        for model in loaded:
            identifier = model.get("modelKey") or model.get("identifier") or ""
            base_name = LMSHelper._get_base_model_name(identifier)
            if base_name:
                return base_name

        return None
    except Exception:
        return None


@pytest.fixture
def require_any_model():
    """
    Fixture to ensure ANY model is loaded.
    Uses dynamic discovery for model selection.
    """
    current_model = get_default_model()

    if current_model:
        print(f"✅ Using currently loaded model: {current_model}")
        return current_model

    # No model loaded — try to load the best available via discovery
    discovered = discover_models()
    if not discovered.lmstudio_available:
        pytest.skip("LM Studio not available")

    # Try chat model first, then any role
    for role in ["chat", "coding", "reasoning"]:
        model = discovered.roles.get(role)
        if model:
            try:
                if ensure_model_loaded(model):
                    return model
            except ModelMemoryError as e:
                pytest.skip(f"Model requires too much memory: {e.required_memory or 'unknown'}")

    pytest.skip("No model could be loaded for testing")


@pytest.fixture
def require_model_with_capability():
    """
    Factory fixture: require a model with a specific capability.

    Usage:
        def test_vision(require_model_with_capability):
            model = require_model_with_capability("vision")
            # model is guaranteed to be loaded and vision-capable
    """
    def _require(capability: str) -> str:
        discovered = discover_models()
        model = discovered.roles.get(capability)
        if not model:
            pytest.skip(f"No model with '{capability}' capability available")
        if not ensure_model_loaded(model):
            pytest.skip(f"Could not load {capability} model '{model}'")
        return model

    return _require
