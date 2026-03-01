#!/usr/bin/env python3
"""
LM Studio CLI Helper - Optional Enhancement

This module provides integration with the LM Studio CLI (lms) for advanced
model management and server control.

GitHub: https://github.com/lmstudio-ai/lms

Installation:
    npm install -g @lmstudio/lms

Benefits:
- Prevents intermittent 404 errors by keeping models loaded
- Better model discovery and validation
- Advanced server management and diagnostics
- Production-ready deployment tools

Note: This is OPTIONAL. The system works without it, but LMS CLI provides
      better reliability and debugging capabilities.
"""

__all__ = [
    "LMSHelper",
    "LMSRestClient",
    "check_lms_availability",
]

import subprocess
import json
import logging
import threading
import time
from typing import Optional, Dict, List, Any
from pathlib import Path

from config.constants import (
    LMS_CLI_CHECK_TIMEOUT,
    LMS_CLI_DEFAULT_TIMEOUT,
    LMS_CLI_LOAD_TIMEOUT,
    LMS_CLI_PS_TIMEOUT,
    LMS_CLI_UNLOAD_TIMEOUT,
    LMS_REST_MODELS_CACHE_TTL,
    MODEL_LOADING_DELAY,
    MODEL_REACTIVATION_DELAY,
)
from llm.exceptions import LLMError
from utils.retry import run_with_retry
from utils.validation import validate_model_name, ValidationError

logger = logging.getLogger(__name__)

# TTL Configuration
DEFAULT_MODEL_TTL = 600  # 10 minutes (configurable)
TEMP_MODEL_TTL = 300     # 5 minutes for temporary models


class LMSRestClient:
    """REST client for LM Studio native API (v0.4.x+).

    Uses a shared httpx.Client for connection pooling across all requests.
    """

    def __init__(self, base_url=None):
        from config.constants import (  # noqa: PLC0415
            DEFAULT_LMSTUDIO_BASE_URL,
            LMS_LOAD_MODEL_ENDPOINT,
            LMS_REST_DEFAULT_TIMEOUT,
            LMS_REST_LOAD_TIMEOUT,
            LMS_UNLOAD_MODEL_ENDPOINT,
            NATIVE_MODELS_ENDPOINT,
        )
        self.base_url = base_url or DEFAULT_LMSTUDIO_BASE_URL
        self._models_endpoint = NATIVE_MODELS_ENDPOINT
        self._load_endpoint = LMS_LOAD_MODEL_ENDPOINT
        self._unload_endpoint = LMS_UNLOAD_MODEL_ENDPOINT
        self._load_timeout = LMS_REST_LOAD_TIMEOUT
        self._default_timeout = LMS_REST_DEFAULT_TIMEOUT
        self._client: "httpx.Client | None" = None
        self._cache_lock = threading.Lock()
        self._models_cache: list[dict] | None = None
        self._models_cache_time: float = 0.0

    def _get_client(self) -> "httpx.Client":
        """Get or create the shared httpx.Client for connection pooling."""
        if self._client is None:
            import httpx
            self._client = httpx.Client(timeout=self._default_timeout)
        return self._client

    def list_all_models(self) -> Optional[List[Dict[str, Any]]]:
        """GET /api/v1/models — returns models[] or None on error. Cached for LMS_REST_MODELS_CACHE_TTL seconds."""
        with self._cache_lock:
            now = time.monotonic()
            if self._models_cache is not None and (now - self._models_cache_time) < LMS_REST_MODELS_CACHE_TTL:
                return self._models_cache

        try:
            response = self._get_client().get(
                f"{self.base_url}{self._models_endpoint}",
                timeout=self._default_timeout
            )
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    result = data
                elif isinstance(data, dict):
                    # Native /api/v1/models wraps in {"models": [...]}
                    result = data.get("models", data.get("data", []))
                else:
                    result = []
                with self._cache_lock:
                    self._models_cache = result
                    self._models_cache_time = time.monotonic()
                return result
            logger.warning(f"Native models API returned {response.status_code}")
            return None
        except Exception as e:
            logger.warning(f"Native models API unavailable: {e}", exc_info=True)
            return None

    def invalidate_cache(self) -> None:
        """Clear the models cache. Forces a fresh HTTP GET on next call."""
        with self._cache_lock:
            self._models_cache = None
            self._models_cache_time = 0.0

    def is_model_loaded(self, model_key: str) -> Optional[bool]:
        """Check if model is loaded via loaded_instances. Returns True/False/None."""
        model = self.get_model(model_key)
        if model is None:
            return None if self.list_all_models() is None else False
        return len(model.get("loaded_instances", [])) > 0

    def get_model(self, model_key: str) -> Optional[dict[str, Any]]:
        """Get single model by key. Cache-first, fetch on miss."""
        with self._cache_lock:
            if self._models_cache is not None:
                now = time.monotonic()
                if (now - self._models_cache_time) < LMS_REST_MODELS_CACHE_TTL:
                    for m in self._models_cache:
                        if m.get("key") == model_key:
                            return m
                    return None
        models = self.list_all_models()
        if models is None:
            return None
        for m in models:
            if m.get("key") == model_key:
                return m
        return None

    def _fetch_model_config(self, model_key: str) -> Optional[dict[str, Any]]:
        """Fetch load config from latest loaded instance after cache invalidation."""
        self.invalidate_cache()
        model = self.get_model(model_key)
        if model is None:
            return None
        instances = model.get("loaded_instances", [])
        if not instances:
            return None
        return instances[-1].get("config", {})

    def is_server_available(self) -> bool:
        """Check if LM Studio REST API is reachable."""
        try:
            response = self._get_client().get(
                f"{self.base_url}{self._models_endpoint}",
                timeout=self._default_timeout
            )
            return response.status_code == 200
        except Exception:
            logger.warning("LM Studio server availability check failed", exc_info=True)
            return False

    def load_model(self, model_key: str, context_length=None, flash_attention=None):
        """
        Load model via REST. Check-before-load to prevent duplicates.

        Returns dict: {success, instance_id, already_loaded, memory_error, message}
        """
        # CRITICAL: Check if already loaded to prevent duplicate instances
        is_loaded = self.is_model_loaded(model_key)
        if is_loaded is True:
            return {
                "success": True,
                "instance_id": None,
                "already_loaded": True,
                "memory_error": False,
                "message": f"Model '{model_key}' already loaded",
                "config": self._fetch_model_config(model_key),
            }

        try:
            body = {"model": model_key}
            if context_length is not None:
                body["context_length"] = context_length
            if flash_attention is not None:
                body["flash_attention"] = flash_attention

            response = self._get_client().post(
                f"{self.base_url}{self._load_endpoint}",
                json=body,
                timeout=self._load_timeout
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "instance_id": data.get("instance_id"),
                    "already_loaded": False,
                    "memory_error": False,
                    "message": f"Model '{model_key}' loaded successfully",
                    "config": self._fetch_model_config(model_key),
                }
            else:
                body_text = response.text
                is_memory = any(kw in body_text.lower() for kw in ("memory", "insufficient", "vram"))
                return {
                    "success": False,
                    "instance_id": None,
                    "already_loaded": False,
                    "memory_error": is_memory,
                    "message": body_text,
                    "config": None,
                }
        except Exception as e:
            return {
                "success": False,
                "instance_id": None,
                "already_loaded": False,
                "memory_error": False,
                "message": str(e),
                "config": None,
            }

    def unload_model(self, instance_id: str) -> bool:
        """Unload model by instance_id. POST /api/v1/models/unload."""
        try:
            response = self._get_client().post(
                f"{self.base_url}{self._unload_endpoint}",
                json={"instance_id": instance_id},
                timeout=self._default_timeout
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to unload model: {e}")
            return False


class LMSHelper:
    """Helper for LM Studio CLI operations (optional)."""

    _is_installed = None  # Cache the installation check
    _rest_client: Optional['LMSRestClient'] = None  # Cache the REST client
    from config.constants import DEFAULT_LMSTUDIO_BASE_URL as _BASE_URL
    LM_STUDIO_BASE_URL = _BASE_URL + "/v1"  # Default LM Studio API endpoint (OpenAI-compatible)

    @classmethod
    def _get_rest_client(cls) -> Optional[LMSRestClient]:
        """Get or create the REST client if LM Studio server is available."""
        if cls._rest_client is None:
            client = LMSRestClient()
            if client.is_server_available():
                cls._rest_client = client
            else:
                return None
        return cls._rest_client

    @staticmethod
    def _get_base_model_name(model_identifier: str) -> str:
        """
        Extract base model name from LM Studio model identifier.

        LM Studio creates instances with suffixes like:
        - "llama-3.2-3b-instruct" (first instance)
        - "llama-3.2-3b-instruct:2" (second instance)
        - "llama-3.2-3b-instruct:9" (ninth instance)

        This function strips the ":N" suffix to get the base model name.

        Args:
            model_identifier: Full model identifier (may include :N suffix)

        Returns:
            Base model name without instance suffix
        """
        if not model_identifier:
            return model_identifier

        # Split on ":" and check if last part is a number (instance suffix)
        parts = model_identifier.rsplit(":", 1)
        if len(parts) == 2 and parts[1].isdigit():
            return parts[0]
        return model_identifier

    @classmethod
    def _model_matches(cls, loaded_identifier: str, requested_model: str) -> bool:
        """
        Check if a loaded model identifier matches the requested model.

        Handles LM Studio's instance numbering where the same model can be loaded
        multiple times with suffixes like ":2", ":3", etc.

        Args:
            loaded_identifier: Identifier from loaded model (may have :N suffix)
            requested_model: Model name requested by user

        Returns:
            True if the loaded model is an instance of the requested model
        """
        if not loaded_identifier or not requested_model:
            return False

        # Get base names for both
        loaded_base = cls._get_base_model_name(loaded_identifier)
        requested_base = cls._get_base_model_name(requested_model)

        # Exact base name match
        return loaded_base == requested_base

    @classmethod
    def is_installed(cls) -> bool:
        """
        Check if LMS CLI is installed.

        Returns:
            True if lms command is available, False otherwise
        """
        if cls._is_installed is not None:
            return cls._is_installed

        try:
            result = subprocess.run(
                ["lms", "ps"],
                capture_output=True,
                text=True,
                timeout=LMS_CLI_CHECK_TIMEOUT
            )
            cls._is_installed = result.returncode == 0

            if cls._is_installed:
                logger.info("LMS CLI detected and working")
            else:
                logger.debug("LMS CLI not installed")

            return cls._is_installed

        except FileNotFoundError:
            logger.debug("LMS CLI not found in PATH")
            cls._is_installed = False
            return False
        except Exception as e:
            logger.warning(f"Error checking LMS CLI: {e}")
            cls._is_installed = False
            return False

    @classmethod
    def get_installation_instructions(cls) -> str:
        """
        Get installation instructions for LMS CLI.

        Returns:
            Formatted installation instructions
        """
        return """
╔══════════════════════════════════════════════════════════════════════════════╗
║                         LMS CLI NOT FOUND                                    ║
╚══════════════════════════════════════════════════════════════════════════════╝

The LM Studio CLI (lms) is not installed. While OPTIONAL, it provides:

  ✅ Prevents intermittent 404 errors (keeps models loaded)
  ✅ Better model discovery and validation
  ✅ Advanced server management
  ✅ Production-ready deployment tools

INSTALLATION:
  # Option 1: Homebrew (macOS/Linux - RECOMMENDED)
  brew install lmstudio-ai/lms/lms

  # Option 2: npm (All platforms)
  npm install -g @lmstudio/lms

DOCUMENTATION:
  https://github.com/lmstudio-ai/lms

ALTERNATIVE:
  The system works without LMS CLI, but may experience:
  - Intermittent 404 errors when models auto-unload
  - Slower test startup (model loading delays)
  - Limited debugging capabilities

════════════════════════════════════════════════════════════════════════════════
"""

    @classmethod
    def print_recommendation(cls):
        """Print a recommendation to install LMS CLI."""
        print("\n" + "⚠️  " * 40)
        print(cls.get_installation_instructions())
        print("⚠️  " * 40 + "\n")

    @classmethod
    def load_model(cls, model_name: str, keep_loaded: bool = True, ttl: Optional[int] = None) -> bool:
        """
        Load a model using LMS CLI with configurable TTL.

        IMPORTANT: This method checks if the model is already loaded (by base name)
        before attempting to load. This prevents creating duplicate instances like
        "model:2", "model:3" that waste memory.

        Args:
            model_name: Name of model to load
            keep_loaded: If True, use longer TTL (10m); if False, use shorter TTL (5m)
            ttl: Optional explicit TTL override in seconds

        Returns:
            True if successful (or already loaded), False otherwise

        Raises:
            ValueError: If model_name is None
        """
        # Validate input - raise exception for None (programming error)
        if model_name is None:
            raise ValueError("model_name cannot be None")

        # Return False for empty/whitespace strings (fail gracefully)
        if isinstance(model_name, str) and not model_name.strip():
            logger.error("model_name cannot be empty or whitespace")
            return False

        # Defense-in-depth: validate model name against safe character pattern
        try:
            validate_model_name(model_name)
        except ValidationError as e:
            logger.error(f"Invalid model name rejected: {e}")
            return False

        if not cls.is_installed():
            logger.warning("LMS CLI not available - cannot load model")
            return False

        # CRITICAL: Check if model is already loaded to prevent duplicates
        # LM Studio creates instances like "model:2", "model:3" when the same
        # model is loaded multiple times without unloading first
        if cls.is_model_loaded(model_name):
            logger.info(f"✅ Model '{model_name}' already loaded - skipping load to prevent duplicate")
            return True

        # Try REST API first
        rest_client = cls._get_rest_client()
        if rest_client is not None:
            rest_result = rest_client.load_model(model_name)
            if rest_result["memory_error"]:
                from llm.exceptions import ModelMemoryError
                raise ModelMemoryError(model_name)
            if rest_result["success"]:
                logger.info(f"Model '{model_name}' loaded via REST API")
                return True
            logger.debug(f"REST load failed, falling back to subprocess: {rest_result['message']}")

        try:
            cmd = ["lms", "load", model_name, "--yes"]  # --yes suppresses confirmations

            # ALWAYS use TTL (never infinite loading) - CRITICAL FIX for memory leaks
            if ttl is not None:
                actual_ttl = ttl
            elif keep_loaded:
                actual_ttl = DEFAULT_MODEL_TTL  # 10 minutes
            else:
                actual_ttl = TEMP_MODEL_TTL      # 5 minutes

            cmd.extend(["--ttl", str(actual_ttl)])
            logger.info(f"Loading model '{model_name}' with TTL={actual_ttl}s")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=LMS_CLI_LOAD_TIMEOUT  # Model loading can take time
            )

            if result.returncode == 0:
                logger.info(f"✅ Model loaded: {model_name} (TTL={actual_ttl}s)")
                return True
            else:
                error_msg = result.stderr or result.stdout or ""
                logger.error(f"Failed to load model: {error_msg}")

                # Check for memory errors - LM Studio reports this in error message
                import re
                memory_match = re.search(r'requires approximately ([\d.]+\s*GB)', error_msg, re.IGNORECASE)
                if memory_match or 'memory' in error_msg.lower() or 'insufficient' in error_msg.lower():
                    from llm.exceptions import ModelMemoryError
                    required_memory = memory_match.group(1) if memory_match else None
                    raise ModelMemoryError(model_name, required_memory)

                return False

        except Exception as e:
            # Re-raise ModelMemoryError to allow proper handling upstream
            from llm.exceptions import ModelMemoryError
            if isinstance(e, ModelMemoryError):
                raise
            logger.error(f"Error loading model with LMS: {e}")
            return False

    @classmethod
    def unload_model(cls, model_name: str) -> bool:
        """
        Unload a model using LMS CLI.

        Args:
            model_name: Name of model to unload

        Returns:
            True if successful, False otherwise
        """
        if not cls.is_installed():
            return False

        # Defense-in-depth: validate model name against safe character pattern
        try:
            validate_model_name(model_name)
        except ValidationError as e:
            logger.error(f"Invalid model name rejected: {e}")
            return False

        try:
            result = subprocess.run(
                ["lms", "unload", model_name],
                capture_output=True,
                text=True,
                timeout=LMS_CLI_UNLOAD_TIMEOUT
            )

            if result.returncode == 0:
                logger.info(f"Model unloaded: {model_name}")
                return True
            else:
                logger.error(f"Failed to unload model: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Error unloading model with LMS: {e}")
            return False

    @classmethod
    def list_downloaded_models(cls, llm_only: bool = True) -> Optional[List[Dict[str, Any]]]:
        """
        List ALL downloaded models (loaded or not).

        Returns rich metadata from lms ls --json:
        - modelKey, displayName, sizeBytes
        - trainedForToolUse, vision, maxContextLength
        - paramsString, architecture, quantization

        Args:
            llm_only: If True, only return LLM models (exclude embeddings)

        Returns:
            List of all downloaded models with metadata, or None if LMS not available
        """
        if not cls.is_installed():
            return None

        try:
            cmd = ["lms", "ls", "--json"]
            if llm_only:
                cmd.append("--llm")

            # Use retry for resilience against timeouts
            result = run_with_retry(cmd, timeout=LMS_CLI_DEFAULT_TIMEOUT)

            if result.returncode == 0:
                models = json.loads(result.stdout)
                logger.info(f"Found {len(models)} downloaded models")
                return models
            else:
                logger.error(f"Failed to list downloaded models: {result.stderr}")
                return None

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from lms ls: {e}")
            return None
        except Exception as e:
            logger.error(f"Error listing downloaded models with LMS: {e}")
            return None

    @classmethod
    def list_loaded_models(cls) -> Optional[List[Dict[str, Any]]]:
        """
        List currently loaded models.

        Returns:
            List of loaded models with details, or None if LMS not available
        """
        # Try REST API first
        rest_client = cls._get_rest_client()
        if rest_client is not None:
            models = rest_client.list_all_models()
            if models is not None:
                # Normalize to legacy format expected by existing callers
                loaded = []
                for m in models:
                    if m.get("loaded_instances"):
                        for inst in m["loaded_instances"]:
                            loaded.append({
                                "identifier": m.get("key", ""),
                                "modelKey": m.get("key", ""),
                                "status": "loaded",
                                "instance_id": inst.get("id", ""),
                            })
                return loaded
        # Fall back to subprocess

        if not cls.is_installed():
            return None

        try:
            # Use retry for resilience against timeouts
            result = run_with_retry(["lms", "ps", "--json"], timeout=LMS_CLI_PS_TIMEOUT)

            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                logger.error(f"Failed to list models: {result.stderr}")
                return None

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from lms ps: {e}")
            return None
        except Exception as e:
            logger.error(f"Error listing models with LMS: {e}")
            return None

    @classmethod
    def is_model_loaded(cls, model_name: str) -> Optional[bool]:
        """
        Check if a specific model is available (loaded or idle).

        According to LM Studio docs: "Any API request to an idle model automatically reactivates it"
        So we treat both "loaded" and "idle" as available.

        CRITICAL FIX: LM Studio creates multiple instances of the same model with
        suffixes like ":2", ":3", etc. This method now matches by BASE model name,
        not exact identifier. For example, if "llama-3.2-3b-instruct:2" is loaded,
        checking for "llama-3.2-3b-instruct" will return True.

        Status meanings:
        - "loaded" (active, ready to serve) → Returns True
        - "idle" (present in memory, will auto-activate) → Returns True
        - "loading" (currently loading) → Returns False
        - "processingprompt" (currently processing) → Returns True (busy but loaded)
        - Not in list → Returns False

        Args:
            model_name: Name of model to check (base name without instance suffix)

        Returns:
            True if model is available (loaded or idle), False otherwise, None if LMS not available
        """
        # Try REST API first (faster, no subprocess)
        rest_client = cls._get_rest_client()
        if rest_client is not None:
            result = rest_client.is_model_loaded(model_name)
            if result is not None:
                return result
        # Fall back to subprocess
        models = cls.list_loaded_models()
        if models is None:
            return None

        # Check if any loaded model matches the requested base model name
        for m in models:
            identifier = m.get("identifier", "")
            model_key = m.get("modelKey", "")

            # Use _model_matches to handle instance suffixes (e.g., ":2", ":3")
            if cls._model_matches(identifier, model_name) or cls._model_matches(model_key, model_name):
                status = m.get("status", "").lower()

                # "loaded", "idle", and "processingprompt" are all usable states
                # (processingprompt means model is loaded but busy - still valid)
                is_available = status in ("loaded", "idle", "processingprompt")

                if not is_available:
                    logger.debug(
                        f"Model '{model_name}' found but status='{status}'. "
                        f"Expected 'loaded', 'idle', or 'processingprompt'"
                    )
                else:
                    logger.debug(
                        f"Model '{model_name}' found as '{identifier}' with status='{status}'"
                    )

                return is_available

        # Model not found in list
        return False

    @classmethod
    def ensure_model_loaded(cls, model_name: str) -> bool:
        """
        Ensure a model is loaded AND active, reactivate if idle.

        CRITICAL: This now handles IDLE state explicitly:
        - If model is "loaded" (active) → Return True
        - If model is "idle" → Unload then reload to reactivate
        - If model is "loading" → Wait then check again
        - If model not in list → Load it

        Args:
            model_name: Name of model to ensure is loaded

        Returns:
            True if model is loaded (or successfully loaded/reactivated), False otherwise
        """
        if not cls.is_installed():
            logger.warning("LMS CLI not available - cannot ensure model loaded")
            return False

        # Get detailed model info including status
        models = cls.list_loaded_models()
        if not models:
            # No models loaded, proceed to load
            logger.info(f"No models loaded, loading: {model_name}")
            return cls.load_model(model_name, keep_loaded=True)

        # Check if model exists and its status (using base name matching)
        for m in models:
            identifier = m.get("identifier", "")
            model_key = m.get("modelKey", "")

            if cls._model_matches(identifier, model_name) or cls._model_matches(model_key, model_name):
                status = m.get("status", "").lower()

                if status in ("loaded", "processingprompt"):
                    # Model is active and ready (or busy processing)
                    logger.info(f"✅ Model already active: {model_name} (as '{identifier}')")
                    return True

                if status == "idle":
                    # Model is IDLE but present in memory
                    # According to LM Studio docs: "Any API request to an idle model automatically reactivates it"
                    # Try to wake it up with a simple API call first
                    logger.info(
                        f"ℹ️  Model '{model_name}' is IDLE. "
                        f"Attempting to reactivate with API call..."
                    )

                    # Try a simple chat completion to wake up the model
                    try:
                        import httpx
                        response = httpx.post(
                            f"{cls.LM_STUDIO_BASE_URL}/chat/completions",
                            json={
                                "model": model_name,
                                "messages": [{"role": "user", "content": "ping"}],
                                "max_tokens": 1,
                                "temperature": 0
                            },
                            timeout=10.0
                        )

                        if response.status_code == 200:
                            # API call succeeded, check if model is now active
                            time.sleep(MODEL_REACTIVATION_DELAY)  # Give it a moment to transition

                            # Verify model is now loaded
                            if cls.is_model_loaded(model_name):
                                logger.info(f"✅ Model '{model_name}' reactivated successfully via API call")
                                return True
                            else:
                                logger.warning(f"⚠️  API call succeeded but model still not active")
                                # Fall through to unload+reload
                        else:
                            logger.warning(f"⚠️  API call failed with status {response.status_code}")
                            # Fall through to unload+reload

                    except Exception as e:
                        logger.warning(f"⚠️  API call failed: {e}")
                        # Fall through to unload+reload

                    # If API call didn't work, try unload+reload
                    logger.info(f"Falling back to unload+reload for model '{model_name}'")
                    cls.unload_model(model_name)
                    return cls.load_model(model_name, keep_loaded=True)

                if status == "loading":
                    # Model is currently loading, wait briefly
                    logger.info(f"⏳ Model '{model_name}' is loading, waiting...")
                    time.sleep(MODEL_LOADING_DELAY)
                    # Check again after wait
                    return cls.is_model_loaded(model_name) or False

                # Unknown status
                logger.warning(
                    f"⚠️  Model '{model_name}' has unknown status: {status}. "
                    f"Attempting reload..."
                )
                cls.unload_model(model_name)
                return cls.load_model(model_name, keep_loaded=True)

        # Model not in list at all - load it
        logger.info(f"Model '{model_name}' not found in loaded models, loading...")
        return cls.load_model(model_name, keep_loaded=True)

    @classmethod
    def verify_model_loaded(cls, model_name: str) -> bool:
        """
        Verify model is available (loaded or idle).

        According to LM Studio docs: "Any API request to an idle model automatically reactivates it"
        So both "loaded" and "idle" status are acceptable.

        CRITICAL FIX: Uses base name matching to handle LM Studio's instance suffixes
        (e.g., ":2", ":3"). If "llama-3.2-3b-instruct:2" is loaded, verifying
        "llama-3.2-3b-instruct" will return True.

        This is a health check to catch cases where model isn't available at all.

        Args:
            model_name: Name of model to verify (base name without instance suffix)

        Returns:
            True if model is available (loaded or idle), False otherwise
        """
        try:
            loaded_models = cls.list_loaded_models()
            if not loaded_models:
                return False

            for model in loaded_models:
                identifier = model.get('identifier', '')

                # Use _model_matches for base name matching
                if cls._model_matches(identifier, model_name):
                    status = model.get('status', '').lower()

                    # "loaded", "idle", and "processingprompt" are acceptable
                    is_available = status in ("loaded", "idle", "processingprompt")

                    if is_available:
                        logger.debug(
                            f"Model '{model_name}' verified available as '{identifier}' (status={status})"
                        )
                        return True
                    else:
                        logger.warning(
                            f"Model '{model_name}' found as '{identifier}' but status={status}. "
                            f"Expected 'loaded' or 'idle'"
                        )
                        return False

            logger.warning(f"Model '{model_name}' not found in loaded models")
            return False
        except Exception as e:
            logger.error(f"Error verifying model: {e}")
            return False

    @classmethod
    def ensure_model_loaded_with_verification(
        cls,
        model_name: str,
        ttl: Optional[int] = None,
        skip_initial_check: bool = False,
    ) -> bool:
        """
        Ensure model is loaded AND verify it's actually available.

        This is the production-hardened version that includes health checks
        to catch false positives from the load command.

        Args:
            model_name: Name of model to ensure is loaded
            ttl: Optional TTL override
            skip_initial_check: If True, skip the initial is_model_loaded() call.
                Set by callers (e.g. _ensure_model_loaded) that have already
                performed this check to avoid a redundant HTTP GET.

        Returns:
            True if model is loaded and verified

        Raises:
            Exception: If model loading or verification fails
        """
        if not skip_initial_check:
            if cls.is_model_loaded(model_name):
                logger.debug(f"Model '{model_name}' already loaded")
                return True

        logger.info(f"Loading model '{model_name}'...")
        if not cls.load_model(model_name, keep_loaded=True, ttl=ttl):
            raise LLMError(f"Failed to load model '{model_name}'")

        # Give LM Studio time to fully load the model
        time.sleep(MODEL_LOADING_DELAY)

        if not cls.verify_model_loaded(model_name):
            raise LLMError(
                f"Model '{model_name}' reported loaded but verification failed. "
                "This usually means LM Studio is under memory pressure."
            )

        logger.info(f"✅ Model '{model_name}' loaded and verified")
        return True

    @classmethod
    def download_model(
        cls,
        model_key: str,
        wait: bool = True,
        timeout: int = 3600
    ) -> tuple[bool, str]:
        """
        Download a model using lms get.

        Args:
            model_key: Model identifier to download (e.g., "qwen/qwen3-coder-30b")
            wait: If True, block until download completes (default: True)
            timeout: Timeout in seconds for download (default: 3600 = 1 hour)

        Returns:
            Tuple of (success: bool, message: str)
        """
        if not cls.is_installed():
            return False, "LMS CLI not installed"

        # Defense-in-depth: validate model name against safe character pattern
        try:
            validate_model_name(model_key)
        except ValidationError as e:
            logger.error(f"Invalid model name rejected: {e}")
            return False, f"Invalid model name: {e}"

        try:
            cmd = ["lms", "get", model_key, "--yes"]  # --yes to auto-confirm

            if wait:
                logger.info(f"Downloading model '{model_key}' (this may take a while)...")
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )

                if result.returncode == 0:
                    logger.info(f"✅ Model '{model_key}' downloaded successfully")
                    return True, f"Model '{model_key}' downloaded successfully"
                else:
                    error_msg = result.stderr or result.stdout or "Download failed"
                    logger.error(f"Download failed: {error_msg}")
                    return False, error_msg
            else:
                # Start download in background (non-blocking)
                logger.info(f"Starting background download of '{model_key}'...")
                subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                return True, f"Download started for '{model_key}' (running in background)"

        except subprocess.TimeoutExpired:
            return False, f"Download timed out after {timeout} seconds"
        except Exception as e:
            logger.error(f"Error downloading model: {e}")
            return False, str(e)

    @classmethod
    def is_model_downloaded(cls, model_key: str) -> Optional[bool]:
        """
        Check if a model is downloaded locally (may or may not be loaded).

        Args:
            model_key: Model identifier to check

        Returns:
            True if downloaded, False if not, None if LMS not available
        """
        downloaded = cls.list_downloaded_models()
        if downloaded is None:
            return None

        return any(m.get("modelKey") == model_key for m in downloaded)

    @classmethod
    def get_server_status(cls) -> Optional[Dict[str, Any]]:
        """
        Get LM Studio server status.

        Returns:
            Server status dict, or None if LMS not available
        """
        if not cls.is_installed():
            return None

        try:
            result = subprocess.run(
                ["lms", "server", "status", "--json"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                return None

        except Exception as e:
            logger.error(f"Error getting server status: {e}")
            return None

    @classmethod
    def show_warning_if_not_installed(cls, context: str = "operation"):
        """
        Show a warning if LMS CLI is not installed.

        Args:
            context: Description of what operation would benefit from LMS CLI
        """
        if not cls.is_installed():
            print(f"\n{'='*80}")
            print(f"⚠️  WARNING: LMS CLI not installed")
            print(f"{'='*80}")
            print(f"\nContext: {context}")
            print("\nWithout LMS CLI, you may experience:")
            print("  - Intermittent 404 errors when models auto-unload")
            print("  - Slower test execution due to model loading delays")
            print("  - Limited debugging capabilities")
            print("\nInstallation:")
            print("  brew install lmstudio-ai/lms/lms  (Homebrew - RECOMMENDED)")
            print("  npm install -g @lmstudio/lms     (npm)")
            print(f"{'='*80}\n")


def check_lms_availability(verbose: bool = True) -> bool:
    """
    Check if LMS CLI is available and print status.

    Args:
        verbose: If True, print detailed status

    Returns:
        True if LMS CLI is available, False otherwise
    """
    available = LMSHelper.is_installed()

    if verbose:
        if available:
            print("✅ LMS CLI detected - Advanced features enabled")
            models = LMSHelper.list_loaded_models()
            if models:
                print(f"   Currently loaded models: {len(models)}")
                for m in models[:3]:  # Show first 3
                    print(f"     - {m.get('name', 'unknown')}")
        else:
            print("⚠️  LMS CLI not found - Using basic mode")
            print("   Install: npm install -g @lmstudio/lms")
            print("   Benefits: Prevents 404 errors, better model management")

    return available


if __name__ == "__main__":
    """Test LMS CLI helper."""
    print("Testing LMS CLI Helper\n")
    print("="*80)

    # Check installation
    if LMSHelper.is_installed():
        print("✅ LMS CLI is installed\n")

        # List loaded models
        print("Loaded models:")
        models = LMSHelper.list_loaded_models()
        if models:
            for m in models:
                print(f"  - {m.get('name', 'unknown')}")
        else:
            print("  (none)")

        # Get server status
        print("\nServer status:")
        status = LMSHelper.get_server_status()
        if status:
            print(f"  {json.dumps(status, indent=2)}")
        else:
            print("  (unavailable)")

    else:
        print("❌ LMS CLI is not installed\n")
        LMSHelper.print_recommendation()
