#!/usr/bin/env python3
"""
LMS CLI Integration for Model Registry.

This module provides integration with the LM Studio CLI (lms) for
querying available and loaded models.

Requires: LMS CLI installed (npm install -g @lmstudio/lms or brew install lmstudio-ai/lms/lms)
"""

import subprocess
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from .schemas import ModelMetadata, ModelType

logger = logging.getLogger(__name__)


class LMSNotInstalledError(Exception):
    """Raised when LMS CLI is not installed."""

    def __init__(self):
        super().__init__(
            "LMS CLI is required but not installed.\n\n"
            "Installation options:\n"
            "  brew install lmstudio-ai/lms/lms  (Homebrew - RECOMMENDED)\n"
            "  npm install -g @lmstudio/lms     (npm)\n\n"
            "Documentation: https://github.com/lmstudio-ai/lms"
        )


class LMSCommandError(Exception):
    """Raised when LMS CLI command fails."""

    def __init__(self, command: str, stderr: str, returncode: int):
        self.command = command
        self.stderr = stderr
        self.returncode = returncode
        super().__init__(
            f"LMS command failed: {command}\n"
            f"Return code: {returncode}\n"
            f"Error: {stderr}"
        )


@dataclass
class LMSModelInfo:
    """Information about a model from LMS CLI."""
    model_id: str
    is_loaded: bool
    status: Optional[str] = None  # "loaded", "idle", etc.
    metadata: Optional[ModelMetadata] = None
    raw_data: Optional[Dict[str, Any]] = None


class LMSIntegration:
    """
    Integration with LM Studio CLI for model management.

    This class provides methods to:
    - Check if LMS CLI is installed
    - List all downloaded models (lms ls)
    - List loaded models (lms ps)
    - Get model metadata
    """

    _is_installed: Optional[bool] = None

    @classmethod
    def check_prerequisites(cls) -> None:
        """
        Check if LMS CLI is installed.

        Raises:
            LMSNotInstalledError: If LMS CLI is not installed
        """
        if not cls.is_installed():
            raise LMSNotInstalledError()

    @classmethod
    def is_installed(cls) -> bool:
        """
        Check if LMS CLI is installed and working.

        Returns:
            True if LMS CLI is available, False otherwise
        """
        if cls._is_installed is not None:
            return cls._is_installed

        try:
            result = subprocess.run(
                ["lms", "version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            cls._is_installed = result.returncode == 0

            if cls._is_installed:
                version = result.stdout.strip()
                logger.info(f"LMS CLI detected: {version}")
            else:
                logger.debug("LMS CLI not working")

            return cls._is_installed

        except FileNotFoundError:
            logger.debug("LMS CLI not found in PATH")
            cls._is_installed = False
            return False
        except subprocess.TimeoutExpired:
            logger.warning("LMS CLI check timed out")
            cls._is_installed = False
            return False
        except Exception as e:
            logger.warning(f"Error checking LMS CLI: {e}")
            cls._is_installed = False
            return False

    @classmethod
    def reset_cache(cls) -> None:
        """Reset the installation check cache (useful for testing)."""
        cls._is_installed = None

    @classmethod
    def _run_lms_command(
        cls,
        args: List[str],
        timeout: int = 30
    ) -> str:
        """
        Run an LMS CLI command and return output.

        Args:
            args: Command arguments (e.g., ["ls", "--json"])
            timeout: Command timeout in seconds

        Returns:
            Command stdout

        Raises:
            LMSNotInstalledError: If LMS CLI not installed
            LMSCommandError: If command fails
        """
        cls.check_prerequisites()

        cmd = ["lms"] + args
        logger.debug(f"Running: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            if result.returncode != 0:
                raise LMSCommandError(
                    command=" ".join(cmd),
                    stderr=result.stderr,
                    returncode=result.returncode
                )

            return result.stdout

        except subprocess.TimeoutExpired:
            raise LMSCommandError(
                command=" ".join(cmd),
                stderr=f"Command timed out after {timeout}s",
                returncode=-1
            )

    @classmethod
    def get_all_models(cls, include_embeddings: bool = True) -> List[Dict[str, Any]]:
        """
        Get all downloaded models from LM Studio.

        This uses 'lms ls --json' to get complete model list with metadata.

        Args:
            include_embeddings: Whether to include embedding models

        Returns:
            List of raw model data from LMS CLI

        Raises:
            LMSNotInstalledError: If LMS CLI not installed
            LMSCommandError: If command fails
        """
        args = ["ls", "--json"]
        if not include_embeddings:
            args.append("--llm")

        output = cls._run_lms_command(args, timeout=30)

        try:
            models = json.loads(output)
            logger.info(f"Found {len(models)} models in LM Studio")
            return models
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LMS ls output: {e}")
            raise LMSCommandError(
                command="lms ls --json",
                stderr=f"Invalid JSON output: {e}",
                returncode=0
            )

    @classmethod
    def get_loaded_models(cls) -> List[Dict[str, Any]]:
        """
        Get currently loaded models.

        This uses 'lms ps --json' to get loaded model list.

        Returns:
            List of loaded model data

        Raises:
            LMSNotInstalledError: If LMS CLI not installed
            LMSCommandError: If command fails
        """
        output = cls._run_lms_command(["ps", "--json"], timeout=10)

        try:
            models = json.loads(output)
            logger.info(f"Found {len(models)} loaded models")
            return models
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LMS ps output: {e}")
            raise LMSCommandError(
                command="lms ps --json",
                stderr=f"Invalid JSON output: {e}",
                returncode=0
            )

    @classmethod
    def get_all_model_ids(cls, include_embeddings: bool = True) -> List[str]:
        """
        Get list of all downloaded model IDs.

        Args:
            include_embeddings: Whether to include embedding models

        Returns:
            List of model IDs (e.g., ["qwen/qwen3-coder-30b", ...])
        """
        models = cls.get_all_models(include_embeddings=include_embeddings)
        return [m.get("modelKey", "") for m in models if m.get("modelKey")]

    @classmethod
    def get_loaded_model_ids(cls) -> List[str]:
        """
        Get list of currently loaded model IDs.

        Returns:
            List of loaded model IDs
        """
        models = cls.get_loaded_models()
        return [
            m.get("identifier", "") or m.get("modelKey", "")
            for m in models
            if m.get("identifier") or m.get("modelKey")
        ]

    @classmethod
    def get_model_metadata_from_lms(cls, model_id: str) -> Optional[ModelMetadata]:
        """
        Get metadata for a specific model from LMS.

        Args:
            model_id: Model identifier

        Returns:
            ModelMetadata if found, None otherwise
        """
        models = cls.get_all_models(include_embeddings=True)

        for model_data in models:
            if model_data.get("modelKey") == model_id:
                return ModelMetadata.from_lms_data(model_data)

        logger.warning(f"Model '{model_id}' not found in LMS")
        return None

    @classmethod
    def get_all_models_with_metadata(
        cls,
        include_embeddings: bool = True
    ) -> List[ModelMetadata]:
        """
        Get all models with parsed metadata.

        Args:
            include_embeddings: Whether to include embedding models

        Returns:
            List of ModelMetadata objects
        """
        models = cls.get_all_models(include_embeddings=include_embeddings)
        result = []

        for model_data in models:
            try:
                metadata = ModelMetadata.from_lms_data(model_data)
                result.append(metadata)
            except Exception as e:
                logger.warning(
                    f"Failed to parse metadata for model "
                    f"'{model_data.get('modelKey', 'unknown')}': {e}"
                )

        return result

    @classmethod
    def compare_model_lists(
        cls,
        current_ids: List[str],
        cached_ids: List[str]
    ) -> Tuple[List[str], List[str], List[str]]:
        """
        Compare current model list with cached list.

        Args:
            current_ids: List of currently available model IDs
            cached_ids: List of previously cached model IDs

        Returns:
            Tuple of (new_models, removed_models, unchanged_models)
        """
        current_set = set(current_ids)
        cached_set = set(cached_ids)

        new_models = list(current_set - cached_set)
        removed_models = list(cached_set - current_set)
        unchanged_models = list(current_set & cached_set)

        return new_models, removed_models, unchanged_models

    @classmethod
    def is_model_available(cls, model_id: str) -> bool:
        """
        Check if a model is available (downloaded) in LM Studio.

        Args:
            model_id: Model identifier

        Returns:
            True if model is available, False otherwise
        """
        try:
            model_ids = cls.get_all_model_ids(include_embeddings=True)
            return model_id in model_ids
        except Exception as e:
            logger.error(f"Error checking model availability: {e}")
            return False

    @classmethod
    def is_model_loaded(cls, model_id: str) -> bool:
        """
        Check if a model is currently loaded.

        Args:
            model_id: Model identifier

        Returns:
            True if model is loaded, False otherwise
        """
        try:
            loaded_ids = cls.get_loaded_model_ids()
            return model_id in loaded_ids
        except Exception as e:
            logger.error(f"Error checking if model is loaded: {e}")
            return False

    @classmethod
    def get_installation_instructions(cls) -> str:
        """Get formatted installation instructions for LMS CLI."""
        return """
╔══════════════════════════════════════════════════════════════════════════════╗
║                       LMS CLI REQUIRED                                       ║
╚══════════════════════════════════════════════════════════════════════════════╝

The Model Registry requires LM Studio CLI (lms) to query available models.

INSTALLATION:
  # Option 1: Homebrew (macOS/Linux - RECOMMENDED)
  brew install lmstudio-ai/lms/lms

  # Option 2: npm (All platforms)
  npm install -g @lmstudio/lms

DOCUMENTATION:
  https://github.com/lmstudio-ai/lms

VERIFY INSTALLATION:
  lms version
  lms ls --json

════════════════════════════════════════════════════════════════════════════════
"""
