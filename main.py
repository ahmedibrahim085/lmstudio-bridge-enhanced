#!/usr/bin/env python3
"""
Main entry point for lmstudio-bridge-enhanced MCP server.

This server acts as both:
1. MCP Server - Serves tools to Claude
2. MCP Client - Connects to other battle-tested MCP servers

Architecture: Orchestrator Pattern
- Provides autonomous tool execution for local LLMs via LM Studio
- Dynamically connects to filesystem, fetch, memory, docker MCPs
- Generic - works with ANY local LLM, not specific to any model
"""

from mcp.server.fastmcp import FastMCP
from config import get_config
from llm.llm_client import LLMClient
from utils import get_logger, log_info
from tools.health import register_health_tools
from tools.completions import register_completion_tools
from tools.embeddings import register_embeddings_tools
from tools.autonomous import register_autonomous_tools
from tools.dynamic_autonomous_register import register_dynamic_autonomous_tools
from tools.lms_cli_tools import register_lms_cli_tools
from tools.vision import register_vision_tools


# Initialize FastMCP server
mcp = FastMCP("lmstudio-bridge-enhanced")

# Get logger
logger = get_logger("lmstudio-bridge-enhanced")


def initialize_server():
    """Initialize the MCP server with all tools."""
    log_info("Initializing lmstudio-bridge-enhanced MCP server...")

    # Load configuration
    config = get_config()
    logger.info(
        "Configuration loaded",
        lmstudio_host=config.lmstudio.host,
        lmstudio_port=config.lmstudio.port
    )

    # Create LLM client (generic, not model-specific)
    llm_client = LLMClient()

    # Register all tools
    log_info("Registering tools...")

    # Health and system tools
    register_health_tools(mcp, llm_client)
    logger.info("Registered health tools")

    # Completion tools (chat, text, responses)
    register_completion_tools(mcp, llm_client)
    logger.info("Registered completion tools")

    # Embeddings tools
    register_embeddings_tools(mcp, llm_client)
    logger.info("Registered embeddings tools")

    # Autonomous execution tools (connects to other MCPs)
    register_autonomous_tools(mcp, llm_client)
    logger.info("Registered autonomous execution tools")

    # Dynamic autonomous tools (truly dynamic MCP discovery from .mcp.json!)
    register_dynamic_autonomous_tools(mcp, llm_client)
    logger.info("Registered dynamic autonomous tools (MCP discovery enabled)")

    # LMS CLI tools (model lifecycle management)
    register_lms_cli_tools(mcp)
    logger.info("Registered LMS CLI tools (model management enabled)")

    # Vision tools (image analysis, multimodal support)
    register_vision_tools(mcp, llm_client)
    logger.info("Registered vision tools (multimodal support enabled)")

    log_info("Server initialization complete")


def main():
    """Entry point for the MCP server."""
    try:
        # Initialize server
        initialize_server()

        # Run the server
        log_info("Starting lmstudio-bridge-enhanced MCP server on stdio")
        logger.info("Server starting", transport="stdio")

        mcp.run(transport='stdio')

    except KeyboardInterrupt:
        log_info("Server shutting down (KeyboardInterrupt)")
        logger.info("Server shutdown", reason="KeyboardInterrupt")

    except Exception as e:
        logger.error("Server startup failed", error=str(e))
        raise


if __name__ == "__main__":
    main()
