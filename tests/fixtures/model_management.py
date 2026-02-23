"""
Model Management Fixtures for Tests.

Ensures models are loaded before tests run. Delegates ALL operations
to LMSHelper (DOGFOODING) — no raw subprocess calls.
"""

import pytest
from llm.exceptions import ModelMemoryError
from utils.lms_helper import LMSHelper


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
def require_any_model(discovered_models):
    """
    Fixture to ensure ANY model is loaded.
    Uses the session-scoped discovered_models fixture.
    """
    current_model = get_default_model()

    if current_model:
        return current_model

    if not discovered_models.lmstudio_available:
        pytest.skip("LM Studio not available")

    # Try chat model first, then any role
    for role in ["chat", "coding", "reasoning"]:
        model = discovered_models.roles.get(role)
        if model:
            try:
                if ensure_model_loaded(model):
                    return model
            except ModelMemoryError as e:
                pytest.skip(f"Model requires too much memory: {e.required_memory or 'unknown'}")

    pytest.skip("No model could be loaded for testing")


@pytest.fixture
def require_model_with_capability(discovered_models):
    """Factory fixture: require a model with a specific capability."""
    def _require(capability: str) -> str:
        model = discovered_models.roles.get(capability)
        if not model:
            pytest.skip(f"No model with '{capability}' capability available")
        if not ensure_model_loaded(model):
            pytest.skip(f"Could not load {capability} model '{model}'")
        return model

    return _require
