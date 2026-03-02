#!/usr/bin/env python3
"""
Embeddings generation tools for LM Studio.
"""

import json
import logging
from typing import List, Optional, Union

from config.constants import is_model_sentinel
from llm.llm_client import LLMClient

logger = logging.getLogger(__name__)


class EmbeddingsTools:
    """Tools for generating vector embeddings from local LLMs."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """Initialize embeddings tools.

        Args:
            llm_client: Optional LLM client (creates default if None)
        """
        self.llm = llm_client or LLMClient()

    async def generate_embeddings(
        self,
        text: Union[str, List[str]],
        model: str = "default"
    ) -> str:
        """Generate vector embeddings for text using LM Studio.

        Supports both single text and batch processing. Useful for RAG systems,
        semantic search, text similarity, and clustering tasks.

        Args:
            text: Single text string or list of texts to embed
            model: Model to use for embeddings (default uses currently loaded model)

        Returns:
            JSON string with embeddings data including vectors and usage info
        """
        try:
            response = self.llm.generate_embeddings(
                text=text,
                model=model if not is_model_sentinel(model) else None
            )

            # Return as JSON string
            return json.dumps(response)

        except Exception as e:
            logger.error("Failed to generate embeddings: %s", e, exc_info=True)
            error_response = {
                "error": f"Failed to generate embeddings: {str(e)}"
            }
            return json.dumps(error_response)


# Register tools with FastMCP
def register_embeddings_tools(mcp, llm_client: Optional[LLMClient] = None):
    """Register embeddings tools with FastMCP server.

    Args:
        mcp: FastMCP server instance
        llm_client: Optional LLM client
    """
    tools = EmbeddingsTools(llm_client)

    @mcp.tool()
    async def generate_embeddings(text: Union[str, List[str]], model: str = "default") -> str:
        """Generate vector embeddings for text using LM Studio.

        Supports both single text and batch processing. Useful for RAG systems,
        semantic search, text similarity, and clustering tasks.

        Args:
            text: Single text string or list of texts to embed
            model: Model to use for embeddings (default uses currently loaded model)

        Returns:
            JSON string with embeddings data including vectors and usage info
        """
        return await tools.generate_embeddings(text, model)


__all__ = [
    "EmbeddingsTools",
    "register_embeddings_tools"
]
