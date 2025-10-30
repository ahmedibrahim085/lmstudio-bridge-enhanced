#!/usr/bin/env python3
"""
Health check and system status tools for LM Studio.
"""

from typing import Optional
from llm.llm_client import LLMClient


class HealthTools:
    """Tools for checking LM Studio health and status."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """Initialize health tools.

        Args:
            llm_client: Optional LLM client (creates default if None)
        """
        self.llm = llm_client or LLMClient()

    async def health_check(self) -> str:
        """Check if LM Studio API is accessible.

        Returns:
            A message indicating whether the LM Studio API is running.
        """
        try:
            if self.llm.health_check():
                return "LM Studio API is running and accessible."
            else:
                return "LM Studio API is not responding."
        except Exception as e:
            return f"Error connecting to LM Studio API: {str(e)}"

    async def list_models(self) -> str:
        """List all available models in LM Studio.

        Returns:
            A formatted list of available models.
        """
        try:
            models = self.llm.list_models()

            if not models:
                return "No models found in LM Studio."

            result = "Available models in LM Studio:\n\n"
            for model in models:
                result += f"- {model}\n"

            return result
        except Exception as e:
            return f"Error listing models: {str(e)}"

    async def get_current_model(self) -> str:
        """Get the currently loaded model in LM Studio.

        Returns:
            The name of the currently loaded model.
        """
        try:
            # LM Studio doesn't have a direct endpoint for currently loaded model
            # We'll check which model responds to a simple completion request
            response = self.llm.chat_completion(
                messages=[{"role": "system", "content": "What model are you?"}],
                max_tokens=10
            )

            # Extract model info from response
            model_info = response.get("model", "Unknown")
            return f"Currently loaded model: {model_info}"
        except Exception as e:
            return f"Error identifying current model: {str(e)}"


# Register tools with FastMCP
def register_health_tools(mcp, llm_client: Optional[LLMClient] = None):
    """Register health tools with FastMCP server.

    Args:
        mcp: FastMCP server instance
        llm_client: Optional LLM client
    """
    tools = HealthTools(llm_client)

    @mcp.tool()
    async def health_check() -> str:
        """Check if LM Studio API is accessible.

        Returns:
            A message indicating whether the LM Studio API is running.
        """
        return await tools.health_check()

    @mcp.tool()
    async def list_models() -> str:
        """List all available models in LM Studio.

        Returns:
            A formatted list of available models.
        """
        return await tools.list_models()

    @mcp.tool()
    async def get_current_model() -> str:
        """Get the currently loaded model in LM Studio.

        Returns:
            The name of the currently loaded model.
        """
        return await tools.get_current_model()


__all__ = [
    "HealthTools",
    "register_health_tools"
]
