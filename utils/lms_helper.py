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

import subprocess
import json
import logging
from typing import Optional, Dict, List, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# TTL Configuration
DEFAULT_MODEL_TTL = 600  # 10 minutes (configurable)
TEMP_MODEL_TTL = 300     # 5 minutes for temporary models


class LMSHelper:
    """Helper for LM Studio CLI operations (optional)."""

    _is_installed = None  # Cache the installation check

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
                timeout=5
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

        Args:
            model_name: Name of model to load
            keep_loaded: If True, use longer TTL (10m); if False, use shorter TTL (5m)
            ttl: Optional explicit TTL override in seconds

        Returns:
            True if successful, False otherwise
        """
        if not cls.is_installed():
            logger.warning("LMS CLI not available - cannot load model")
            return False

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
                timeout=60  # Model loading can take time
            )

            if result.returncode == 0:
                logger.info(f"✅ Model loaded: {model_name} (TTL={actual_ttl}s)")
                return True
            else:
                logger.error(f"Failed to load model: {result.stderr}")
                return False

        except Exception as e:
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

        try:
            result = subprocess.run(
                ["lms", "unload", model_name],
                capture_output=True,
                text=True,
                timeout=30
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
    def list_loaded_models(cls) -> Optional[List[Dict[str, Any]]]:
        """
        List currently loaded models.

        Returns:
            List of loaded models with details, or None if LMS not available
        """
        if not cls.is_installed():
            return None

        try:
            result = subprocess.run(
                ["lms", "ps", "--json"],
                capture_output=True,
                text=True,
                timeout=10
            )

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
        Check if a specific model is loaded.

        Args:
            model_name: Name of model to check

        Returns:
            True if loaded, False if not loaded, None if LMS not available
        """
        models = cls.list_loaded_models()
        if models is None:
            return None

        return any(m.get("identifier") == model_name or m.get("modelKey") == model_name for m in models)

    @classmethod
    def ensure_model_loaded(cls, model_name: str) -> bool:
        """
        Ensure a model is loaded, load if necessary.

        Args:
            model_name: Name of model to ensure is loaded

        Returns:
            True if model is loaded (or successfully loaded), False otherwise
        """
        if not cls.is_installed():
            logger.warning("LMS CLI not available - cannot ensure model loaded")
            return False

        # Check if already loaded
        is_loaded = cls.is_model_loaded(model_name)

        if is_loaded is None:
            return False  # LMS not available

        if is_loaded:
            logger.info(f"✅ Model already loaded: {model_name}")
            return True

        # Not loaded - load it now
        logger.info(f"Loading model: {model_name}")
        return cls.load_model(model_name, keep_loaded=True)

    @classmethod
    def verify_model_loaded(cls, model_name: str) -> bool:
        """
        Verify model is actually loaded (not just CLI state).

        This is a health check to catch false positives where CLI reports
        success but model isn't actually available (memory pressure, etc).

        Args:
            model_name: Name of model to verify

        Returns:
            True if model is confirmed loaded, False otherwise
        """
        try:
            loaded_models = cls.list_loaded_models()
            if not loaded_models:
                return False

            for model in loaded_models:
                if model.get('identifier') == model_name:
                    logger.debug(f"Model '{model_name}' verified loaded")
                    return True

            logger.warning(f"Model '{model_name}' not found in loaded models")
            return False
        except Exception as e:
            logger.error(f"Error verifying model: {e}")
            return False

    @classmethod
    def ensure_model_loaded_with_verification(cls, model_name: str, ttl: Optional[int] = None) -> bool:
        """
        Ensure model is loaded AND verify it's actually available.

        This is the production-hardened version that includes health checks
        to catch false positives from the load command.

        Args:
            model_name: Name of model to ensure is loaded
            ttl: Optional TTL override

        Returns:
            True if model is loaded and verified

        Raises:
            Exception: If model loading or verification fails
        """
        if cls.is_model_loaded(model_name):
            logger.debug(f"Model '{model_name}' already loaded")
            return True

        logger.info(f"Loading model '{model_name}'...")
        if not cls.load_model(model_name, keep_loaded=True, ttl=ttl):
            raise Exception(f"Failed to load model '{model_name}'")

        # Give LM Studio time to fully load the model
        import time
        time.sleep(2)

        if not cls.verify_model_loaded(model_name):
            raise Exception(
                f"Model '{model_name}' reported loaded but verification failed. "
                "This usually means LM Studio is under memory pressure."
            )

        logger.info(f"✅ Model '{model_name}' loaded and verified")
        return True

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
