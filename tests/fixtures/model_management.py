"""
Model Management Fixtures for Tests

Ensures models are loaded before tests run.
Prevents test failures due to unloaded models.
"""

import subprocess
import re
import pytest
from llm.llm_client import LLMClient
from llm.exceptions import ModelMemoryError


def ensure_model_loaded(model_name: str) -> bool:
    """
    Ensure a specific model is loaded in LM Studio.

    Args:
        model_name: Model identifier (e.g., "qwen/qwen3-coder-30b")

    Returns:
        True if model is loaded, False otherwise

    Raises:
        ModelMemoryError: If model cannot be loaded due to insufficient memory
    """
    try:
        # Check if model is loaded
        result = subprocess.run(
            ["lms", "ps"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0 and model_name in result.stdout:
            return True

        # Model not loaded, try to load it
        print(f"⚠️  Model '{model_name}' not loaded. Attempting to load...")
        load_result = subprocess.run(
            ["lms", "load", model_name],
            capture_output=True,
            text=True,
            timeout=60  # Increased timeout for larger models
        )

        if load_result.returncode == 0:
            print(f"✅ Model '{model_name}' loaded successfully")
            return True
        else:
            error_msg = load_result.stderr or load_result.stdout or ""
            print(f"❌ Failed to load model '{model_name}': {error_msg}")

            # Detect memory errors and raise specific exception
            memory_match = re.search(r'requires approximately ([\d.]+\s*GB)', error_msg, re.IGNORECASE)
            if memory_match or 'memory' in error_msg.lower() or 'insufficient' in error_msg.lower():
                required_memory = memory_match.group(1) if memory_match else None
                raise ModelMemoryError(model_name, required_memory)

            return False

    except ModelMemoryError:
        raise  # Re-raise memory errors for proper handling
    except subprocess.TimeoutExpired:
        print(f"⏱️  Timeout while checking/loading model '{model_name}'")
        return False
    except FileNotFoundError:
        print("❌ lms CLI not found. Install with: brew install lmstudio-ai/lmstudio/lms")
        return False
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


def get_default_model() -> str:
    """
    Get the currently loaded model (default).

    Returns:
        Model name if one is loaded, None otherwise
    """
    try:
        result = subprocess.run(
            ["lms", "ps"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            return None

        # Parse output to find loaded model
        lines = result.stdout.strip().split('\n')
        for line in lines:
            if line and not line.startswith('Error') and not line.startswith('To load'):
                # Extract model name from lms ps output
                parts = line.split()
                if parts:
                    return parts[0]

        return None

    except Exception:
        return None


@pytest.fixture
def require_any_model():
    """
    Fixture to ensure ANY model is loaded.
    If no model is loaded, tries to load qwen/qwen3-coder-30b as default.
    """
    current_model = get_default_model()

    if current_model:
        print(f"✅ Using currently loaded model: {current_model}")
        return current_model

    # No model loaded, try to load default
    default_model = "qwen/qwen3-coder-30b"
    print(f"⚠️  No model loaded. Attempting to load default: {default_model}")

    try:
        if ensure_model_loaded(default_model):
            return default_model
        else:
            pytest.skip("No model could be loaded for testing")
    except ModelMemoryError as e:
        pytest.skip(f"Default model requires too much memory: {e.required_memory or 'unknown'}")
