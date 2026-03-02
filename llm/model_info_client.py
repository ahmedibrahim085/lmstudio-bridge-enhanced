"""Model info sub-client."""

import logging
from typing import Any, Dict, List, Optional

from config.constants import MODEL_LIST_TIMEOUT
from llm.http_transport import HTTPTransport, handle_request_exception

logger = logging.getLogger(__name__)


class ModelInfoClient:
    """Handles model listing and info endpoints."""

    def __init__(self, transport: HTTPTransport) -> None:
        self._transport = transport

    def list_models(self) -> List[str]:
        """List all available models in LM Studio."""
        try:
            response = self._transport.session.get(
                self._transport.get_endpoint("models"),
                timeout=MODEL_LIST_TIMEOUT,
            )
            response.raise_for_status()
            models = response.json().get("data", [])
            return [model["id"] for model in models]
        except Exception as e:
            handle_request_exception(e, "List models")

    def list_models_enriched(self) -> List[Dict[str, Any]]:
        """List all available models with enriched metadata."""
        base_url = self._transport.api_base.rstrip("/")
        if base_url.endswith("/v1"):
            base_url = base_url[:-3]

        try:
            response = self._transport.session.get(
                f"{base_url}/api/v1/models",
                timeout=MODEL_LIST_TIMEOUT,
            )
            response.raise_for_status()
            raw_data = response.json()
            if isinstance(raw_data, dict):
                raw_list = raw_data.get("models", raw_data.get("data", []))
            else:
                raw_list = raw_data
            if isinstance(raw_list, list) and raw_list:
                return [
                    {
                        "model_id": entry.get("key", ""),
                        "key": entry.get("key", ""),
                        "type": entry.get("type", "llm"),
                        "publisher": entry.get("publisher", ""),
                        "arch": entry.get("arch", ""),
                        "max_context_length": entry.get("max_context_length"),
                        "capabilities": entry.get("capabilities", {}),
                        "loaded_instances": entry.get("loaded_instances", []),
                        "size_bytes": entry.get("size_bytes"),
                        "quantization": entry.get("quantization"),
                        "compatibility_type": entry.get("compatibility_type"),
                    }
                    for entry in raw_list
                ]
        except Exception:
            logger.warning(
                "Native /api/v1/models unavailable, falling back to /v1/models",
                exc_info=True,
            )

        return [{"model_id": m} for m in self.list_models()]

    def get_model_info(self, model_id: Optional[str] = None) -> Dict[str, Any]:
        """Get basic model information from LM Studio."""
        try:
            response = self._transport.session.get(
                self._transport.get_endpoint("models"),
                timeout=MODEL_LIST_TIMEOUT,
            )
            response.raise_for_status()
            models = response.json().get("data", [])

            if not model_id:
                if models:
                    return models[0]
                else:
                    raise ValueError("No models loaded in LM Studio")

            for model in models:
                if model.get("id") == model_id:
                    return model

            raise ValueError(f"Model '{model_id}' not found in LM Studio")

        except (ValueError, KeyError, IndexError):
            raise
        except Exception as e:
            handle_request_exception(e, "Get model info")

    @staticmethod
    def get_default_max_tokens() -> int:
        """Get default max_tokens based on Claude Code's tool response limits."""
        return 8192


__all__ = ["ModelInfoClient"]
