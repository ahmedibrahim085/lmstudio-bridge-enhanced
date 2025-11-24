#!/usr/bin/env python3
"""
LMS CLI MCP Tools

Exposes LM Studio CLI (lms) functionality as MCP tools, enabling Claude Code
to directly manage LM Studio's model lifecycle for proactive error prevention,
intelligent model management, and self-healing capabilities.

Tools provided:
1. lms_list_loaded_models - List all loaded models with details
2. lms_load_model - Load a specific model (optionally keep loaded)
3. lms_unload_model - Unload a model to free memory
4. lms_ensure_model_loaded - Idempotent model preloading (RECOMMENDED)
5. lms_server_status - Get LM Studio server health and diagnostics

Benefits:
- Proactive error prevention (eliminate 404 errors)
- Self-healing (Claude Code fixes issues automatically)
- Intelligent multi-model workflows
- Performance optimization (eliminate JIT loading delays)
- Production-grade reliability

Requirements:
- LM Studio running
- LMS CLI installed (optional, but required for these tools to work)
  Installation: brew install lmstudio-ai/lms/lms
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.lms_helper import LMSHelper
from utils.model_fallback import get_fallback_manager, ModelAlternative


def lms_list_loaded_models() -> Dict[str, Any]:
    """
    List all currently loaded models in LM Studio.

    Returns detailed information about each loaded model including
    identifier, display name, status, size, context length, and memory usage.

    Use this to:
    - Check which models are available before operations
    - Monitor total memory usage
    - Optimize model selection based on what's already loaded
    - Decide whether to load a new model or use existing one

    Returns:
        Dictionary with:
        - success (bool): Whether operation succeeded
        - models (list): List of model details (if successful)
        - count (int): Number of loaded models
        - totalMemoryBytes (int): Total memory used by all models
        - totalMemoryGB (float): Total memory in GB
        - error (str): Error message (if failed)
        - installInstructions (str): How to install LMS CLI (if not installed)

    Example:
        result = lms_list_loaded_models()
        if result["success"]:
            print(f"Found {result['count']} loaded models")
            for model in result["models"]:
                print(f"  - {model['identifier']} ({model['status']})")
    """
    if not LMSHelper.is_installed():
        return {
            "success": False,
            "error": "LMS CLI not installed",
            "installInstructions": (
                "Install LMS CLI to use this tool:\n"
                "  brew install lmstudio-ai/lms/lms  (Homebrew - RECOMMENDED)\n"
                "  npm install -g @lmstudio/lms      (npm - all platforms)\n"
                "\n"
                "Benefits: Prevents 404 errors, enables model management, "
                "improves reliability"
            ),
            "alternativeSolution": (
                "Without LMS CLI, the system still works but may experience "
                "intermittent 404 errors when models auto-unload. Consider "
                "installing LMS CLI for production use."
            )
        }

    models = LMSHelper.list_loaded_models()

    if models is None:
        return {
            "success": False,
            "error": "Failed to list models. Is LM Studio running?",
            "troubleshooting": (
                "1. Check LM Studio is running\n"
                "2. Try: lms ps\n"
                "3. Check LM Studio server logs"
            )
        }

    # Calculate total memory usage
    total_size_bytes = sum(m.get("sizeBytes", 0) for m in models)
    total_size_gb = round(total_size_bytes / (1024**3), 2)

    return {
        "success": True,
        "models": models,
        "count": len(models),
        "totalMemoryBytes": total_size_bytes,
        "totalMemoryGB": total_size_gb,
        "summary": f"Found {len(models)} loaded models using {total_size_gb}GB memory"
    }


def lms_load_model(model_name: str, keep_loaded: bool = True) -> Dict[str, Any]:
    """
    Load a specific model in LM Studio.

    Args:
        model_name: Model identifier (e.g., "qwen/qwen3-coder-30b")
        keep_loaded: If True, prevents auto-unloading (default: True)

    Use this to:
    - Preload models before intensive operations
    - Switch to different model for specific tasks
    - Ensure model stays loaded during long workflows
    - Prepare for multi-model workflows

    Returns:
        Dictionary with:
        - success (bool): Whether model loaded successfully
        - model (str): Model identifier
        - keepLoaded (bool): Whether model will be kept loaded
        - message (str): Success/failure message
        - error (str): Error details (if failed)

    Example:
        # Load coder model and keep it loaded for workflow
        result = lms_load_model("qwen/qwen3-coder-30b", keep_loaded=True)
        if result["success"]:
            print("Model loaded and ready!")
    """
    if not LMSHelper.is_installed():
        return {
            "success": False,
            "error": "LMS CLI not installed",
            "installInstructions": (
                "Install LMS CLI to use this tool:\n"
                "  brew install lmstudio-ai/lms/lms"
            )
        }

    success = LMSHelper.load_model(model_name, keep_loaded=keep_loaded)

    if success:
        return {
            "success": True,
            "model": model_name,
            "keepLoaded": keep_loaded,
            "message": (
                f"Model '{model_name}' loaded successfully"
                f"{' and kept loaded (will not auto-unload)' if keep_loaded else ''}"
            )
        }
    else:
        return {
            "success": False,
            "model": model_name,
            "error": f"Failed to load model '{model_name}'",
            "troubleshooting": (
                "1. Check model name is correct (use lms_list_loaded_models to see available models)\n"
                "2. Check LM Studio is running\n"
                "3. Check model is downloaded in LM Studio\n"
                "4. Try loading manually in LM Studio first"
            )
        }


def lms_unload_model(model_name: str) -> Dict[str, Any]:
    """
    Unload a specific model to free memory.

    Args:
        model_name: Model identifier to unload

    Use this to:
    - Free memory after completing tasks
    - Make room for larger models
    - Clean up after multi-model workflows
    - Optimize memory usage

    Returns:
        Dictionary with:
        - success (bool): Whether model unloaded successfully
        - model (str): Model identifier
        - message (str): Success/failure message
        - error (str): Error details (if failed)

    Example:
        # Free memory by unloading unused model
        result = lms_unload_model("qwen/qwen3-4b-thinking-2507")
        if result["success"]:
            print("Memory freed!")
    """
    if not LMSHelper.is_installed():
        return {
            "success": False,
            "error": "LMS CLI not installed",
            "installInstructions": (
                "Install LMS CLI to use this tool:\n"
                "  brew install lmstudio-ai/lms/lms"
            )
        }

    success = LMSHelper.unload_model(model_name)

    if success:
        return {
            "success": True,
            "model": model_name,
            "message": f"Model '{model_name}' unloaded successfully"
        }
    else:
        return {
            "success": False,
            "model": model_name,
            "error": f"Failed to unload model '{model_name}'",
            "troubleshooting": (
                "1. Check model is actually loaded (use lms_list_loaded_models)\n"
                "2. Check LM Studio is running\n"
                "3. Model might already be unloaded"
            )
        }


def lms_ensure_model_loaded(model_name: str) -> Dict[str, Any]:
    """
    Ensure a model is loaded, load if necessary (idempotent).

    ⚠️ **PURPOSE: MODEL LIFECYCLE MANAGEMENT (Performance & Reliability)**

    This tool is for **preloading models** to prevent errors and delays.
    It is **NOT for task delegation** or switching models for specific tasks!

    ## When to Use This Tool
    ✅ Use for MODEL LIFECYCLE:
    - Prevent 404 errors before operations (PRIMARY USE CASE)
    - Preload models for performance (eliminate JIT loading delays)
    - Guarantee model availability for long workflows
    - Idempotent preloading (safe to call multiple times)
    - Fail-safe pattern before autonomous execution

    ❌ Do NOT use for TASK DELEGATION:
    ```python
    # ❌ WRONG - This does NOT switch which model handles the task
    lms_ensure_model_loaded("gemma-3")
    chat_completion("generate cat photo")  # Still uses default model!

    # ✅ CORRECT - Use autonomous tools with model parameter
    autonomous_with_mcp(
        mcp_name="filesystem",
        task="generate cat photo description",
        model="gemma-3"  # This ACTUALLY uses gemma-3
    )
    ```

    ## Model Lifecycle vs Task Delegation
    **Model Lifecycle** (THIS tool):
    - Loading/unloading models for memory management
    - Preventing auto-unload during workflows
    - Performance optimization (preloading)

    **Task Delegation** (USE autonomous tools instead):
    - Asking a specific model to do something
    - Multi-model workflows (different models for different tasks)
    - Using model='name' parameter in autonomous tools

    This is the RECOMMENDED way to prevent 404 errors.
    Safe to call multiple times - only loads if needed.

    Args:
        model_name: Model identifier to ensure is loaded

    Returns:
        Dictionary with:
        - success (bool): Whether model is loaded (or was loaded)
        - model (str): Model identifier
        - wasAlreadyLoaded (bool): True if model was already loaded
        - message (str): Status message
        - error (str): Error details (if failed)

    Example:
        # BEST PRACTICE: Ensure model loaded before operation
        result = lms_ensure_model_loaded("qwen/qwen3-coder-30b")
        if result["success"]:
            if result["wasAlreadyLoaded"]:
                print("Model already loaded, ready to go!")
            else:
                print("Model loaded successfully!")
            # Now safe to run autonomous task
    """
    if not LMSHelper.is_installed():
        return {
            "success": False,
            "error": "LMS CLI not installed",
            "installInstructions": (
                "Install LMS CLI to use this tool:\n"
                "  brew install lmstudio-ai/lms/lms\n"
                "\n"
                "This tool is HIGHLY RECOMMENDED for production use as it "
                "prevents intermittent 404 errors caused by model auto-unloading."
            ),
            "workaround": (
                "Without LMS CLI, you can still use the autonomous tools, "
                "but may experience intermittent failures when models unload. "
                "Consider installing LMS CLI for reliability."
            )
        }

    # Check if already loaded
    is_loaded = LMSHelper.is_model_loaded(model_name)

    if is_loaded is None:
        return {
            "success": False,
            "model": model_name,
            "error": "Failed to check model status",
            "troubleshooting": "Check LM Studio is running and LMS CLI is working"
        }

    if is_loaded:
        return {
            "success": True,
            "model": model_name,
            "wasAlreadyLoaded": True,
            "message": f"Model '{model_name}' is already loaded and ready"
        }

    # Not loaded - load it now
    success = LMSHelper.load_model(model_name, keep_loaded=True)

    if success:
        return {
            "success": True,
            "model": model_name,
            "wasAlreadyLoaded": False,
            "message": f"Model '{model_name}' loaded successfully and kept loaded"
        }
    else:
        return {
            "success": False,
            "model": model_name,
            "wasAlreadyLoaded": False,
            "error": f"Failed to load model '{model_name}'",
            "troubleshooting": (
                "1. Check model name is correct\n"
                "2. Check LM Studio is running\n"
                "3. Check model is downloaded in LM Studio\n"
                "4. Try: lms ps (to see available models)"
            )
        }


def lms_search_models(query: str, limit: int = 10) -> Dict[str, Any]:
    """
    Search for models available online in the LM Studio model hub.

    ⚠️ NOTE: This feature is NOT SUPPORTED by the LMS CLI.
    The LMS CLI only has `lms get` which is an interactive command that
    searches AND downloads together - there is no search-only mode.

    ALTERNATIVES:
    1. Use lms_list_downloaded_models() to see what's already available
    2. Use lms_download_model() to download a specific model by name
    3. Browse models at https://lmstudio.ai/models or HuggingFace

    Args:
        query: Search query (not used - feature not available)
        limit: Maximum results (not used - feature not available)

    Returns:
        Dictionary with error explaining the limitation
    """
    return {
        "success": False,
        "error": "Model search is not supported by the LMS CLI",
        "query": query,
        "explanation": (
            "The LMS CLI only has 'lms get' which is an interactive command that "
            "searches AND downloads together. There is no search-only or JSON output mode."
        ),
        "alternatives": [
            {
                "tool": "lms_list_downloaded_models",
                "description": "See what models are already downloaded locally"
            },
            {
                "tool": "lms_download_model",
                "description": "Download a specific model by name (e.g., 'qwen/qwen3-coder-30b')"
            },
            {
                "tool": "lms_resolve_model",
                "description": "Check if a model is available and find alternatives"
            }
        ],
        "browseModels": (
            "To browse available models:\n"
            "  - LM Studio app: Browse models tab\n"
            "  - Web: https://lmstudio.ai/models\n"
            "  - HuggingFace: https://huggingface.co/models"
        )
    }


def lms_download_model(model_key: str, wait: bool = False) -> Dict[str, Any]:
    """
    Download a model from the LM Studio model hub.

    Use this to:
    - Download a model that isn't available locally
    - Get a specific model version for a task
    - Prepare models in advance for workflows

    ⚠️ WARNING: Model downloads can be large (GB) and take significant time.
    Use wait=False for background downloads (recommended for large models).

    Args:
        model_key: Full model identifier (e.g., "qwen/qwen3-coder-30b")
        wait: If True, block until download completes (can take hours!)
              If False, start download in background (default, recommended)

    Returns:
        Dictionary with:
        - success (bool): Whether download started/completed
        - model (str): Model identifier
        - message (str): Status message
        - isBackground (bool): True if download is running in background
        - error (str): Error message (if failed)

    Example:
        # Start background download (recommended)
        result = lms_download_model("qwen/qwen3-coder-30b", wait=False)
        if result["success"]:
            print("Download started! Check LM Studio for progress.")

        # Blocking download (use for small models only)
        result = lms_download_model("mistralai/mistral-small-3.2", wait=True)
    """
    if not LMSHelper.is_installed():
        return {
            "success": False,
            "error": "LMS CLI not installed",
            "installInstructions": (
                "Install LMS CLI to download models:\n"
                "  brew install lmstudio-ai/lms/lms"
            )
        }

    # Check if already downloaded
    is_downloaded = LMSHelper.is_model_downloaded(model_key)
    if is_downloaded:
        return {
            "success": True,
            "model": model_key,
            "alreadyDownloaded": True,
            "message": f"Model '{model_key}' is already downloaded"
        }

    success, message = LMSHelper.download_model(model_key, wait=wait)

    if success:
        return {
            "success": True,
            "model": model_key,
            "alreadyDownloaded": False,
            "isBackground": not wait,
            "message": message
        }
    else:
        return {
            "success": False,
            "model": model_key,
            "error": message,
            "troubleshooting": (
                "1. Check model key is correct (use lms_search_models to find exact name)\n"
                "2. Check internet connection\n"
                "3. Check disk space (models can be 10-100GB)\n"
                "4. Try downloading manually in LM Studio app"
            )
        }


def lms_list_downloaded_models() -> Dict[str, Any]:
    """
    List all downloaded models (loaded or not).

    Unlike lms_list_loaded_models which shows only currently loaded models,
    this shows ALL models downloaded to LM Studio, including those not in memory.

    Use this to:
    - See complete inventory of available models
    - Check if a specific model is downloaded before use
    - Plan which models to load based on what's available
    - Review model metadata (size, capabilities, etc.)

    Returns:
        Dictionary with:
        - success (bool): Whether operation succeeded
        - models (list): All downloaded models with full metadata
        - count (int): Number of downloaded models
        - totalSizeBytes (int): Total disk space used
        - totalSizeGB (float): Total size in GB
        - error (str): Error message (if failed)

    Example:
        result = lms_list_downloaded_models()
        if result["success"]:
            for model in result["models"]:
                tool_use = "✅" if model.get("trainedForToolUse") else "❌"
                print(f"{model['modelKey']} - Tool use: {tool_use}")
    """
    if not LMSHelper.is_installed():
        return {
            "success": False,
            "error": "LMS CLI not installed",
            "installInstructions": (
                "Install LMS CLI to list downloaded models:\n"
                "  brew install lmstudio-ai/lms/lms"
            )
        }

    models = LMSHelper.list_downloaded_models()

    if models is None:
        return {
            "success": False,
            "error": "Failed to list downloaded models",
            "troubleshooting": "Check LM Studio is running and LMS CLI is working"
        }

    total_size = sum(m.get("sizeBytes", 0) for m in models)
    total_gb = round(total_size / (1024**3), 2)

    return {
        "success": True,
        "models": models,
        "count": len(models),
        "totalSizeBytes": total_size,
        "totalSizeGB": total_gb,
        "summary": f"Found {len(models)} downloaded models using {total_gb}GB disk space"
    }


def lms_resolve_model(
    model_key: str,
    auto_fallback: bool = False,
    task_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Resolve a model request with intelligent fallback to alternatives.

    This is the RECOMMENDED way to handle model requests when you're unsure
    if a model is available. It checks availability and suggests or auto-selects
    alternatives based on capability matching.

    Use this when:
    - Importing agent configs that specify models you may not have
    - User requests a specific model that might not be downloaded
    - You want graceful degradation instead of hard failures
    - Building workflows that should work across different setups

    Args:
        model_key: The requested model identifier (e.g., "deepseek/deepseek-coder-33b")
        auto_fallback: If True, automatically use best alternative if unavailable
                       If False, return alternatives list for user to choose
        task_type: Optional hint about the task for better matching
                   ("coding", "reasoning", "chat", "analysis")

    Returns:
        Dictionary with:
        - success (bool): Whether resolution succeeded
        - requested_model (str): Original model requested
        - resolved_model (str): Model to use (may be fallback)
        - status (str): "available", "fallback", or "unavailable"
        - alternatives (list): Alternative models if unavailable
        - message (str): Human-readable status message

    Example:
        # Auto-fallback mode (for automation)
        result = lms_resolve_model("deepseek/deepseek-coder-33b", auto_fallback=True, task_type="coding")
        if result["success"]:
            model_to_use = result["resolved_model"]
            # Use model_to_use in your workflow

        # Manual mode (for user interaction)
        result = lms_resolve_model("deepseek/deepseek-coder-33b", auto_fallback=False)
        if result["status"] == "unavailable":
            print(result["message"])  # Shows alternatives
            # Let user choose from result["alternatives"]
    """
    if not LMSHelper.is_installed():
        return {
            "success": False,
            "error": "LMS CLI not installed",
            "installInstructions": (
                "Install LMS CLI to use model resolution:\n"
                "  brew install lmstudio-ai/lms/lms"
            )
        }

    manager = get_fallback_manager()
    resolved_model, status, alternatives = manager.resolve_model(
        model_key,
        auto_fallback=auto_fallback,
        task_type=task_type
    )

    result = {
        "success": status != "unavailable" or auto_fallback,
        "requested_model": model_key,
        "resolved_model": resolved_model,
        "status": status,
    }

    if status == "available":
        result["message"] = f"Model '{model_key}' is available"
    elif status == "fallback":
        result["message"] = f"Using '{resolved_model}' as fallback for '{model_key}'"
        result["fallback_reasons"] = alternatives[0].reasons if alternatives else []
    else:  # unavailable
        if alternatives:
            result["alternatives"] = [
                {
                    "model_key": alt.model_key,
                    "display_name": alt.display_name,
                    "score": alt.score,
                    "reasons": alt.reasons,
                    "trained_for_tool_use": alt.trained_for_tool_use,
                    "size_gb": round(alt.size_bytes / (1024**3), 1) if alt.size_bytes else None
                }
                for alt in alternatives
            ]
            result["message"] = manager.format_alternatives_message(model_key, alternatives)
        else:
            result["alternatives"] = []
            result["message"] = f"Model '{model_key}' is not downloaded and no alternatives found"

    return result


def lms_server_status() -> Dict[str, Any]:
    """
    Get LM Studio server status and diagnostics.

    Use this to:
    - Check server health before operations
    - Diagnose issues when failures occur
    - Monitor server state
    - Verify LM Studio is running properly

    Returns:
        Dictionary with:
        - success (bool): Whether status retrieved successfully
        - serverRunning (bool): Whether LM Studio server is running
        - status (dict): Server status details (if available)
        - error (str): Error message (if failed)

    Example:
        # Check server health before running tasks
        result = lms_server_status()
        if result["success"] and result["serverRunning"]:
            print("LM Studio server is healthy!")
        else:
            print("Server issue detected")
    """
    if not LMSHelper.is_installed():
        return {
            "success": False,
            "error": "LMS CLI not installed",
            "installInstructions": (
                "Install LMS CLI to use this tool:\n"
                "  brew install lmstudio-ai/lms/lms"
            )
        }

    status = LMSHelper.get_server_status()

    if status:
        return {
            "success": True,
            "serverRunning": True,
            "status": status,
            "message": "LM Studio server is running"
        }
    else:
        return {
            "success": False,
            "serverRunning": False,
            "error": "Could not get server status",
            "troubleshooting": (
                "1. Check LM Studio is running\n"
                "2. Check LM Studio server is started (not just app open)\n"
                "3. Try: lms server status\n"
                "4. Check LM Studio logs for errors"
            )
        }


def register_lms_cli_tools(mcp_server):
    """
    Register all LMS CLI tools with the MCP server.

    Args:
        mcp_server: FastMCP server instance

    Registers 9 tools:
    - lms_list_loaded_models: List currently loaded models
    - lms_list_downloaded_models: List ALL downloaded models (loaded or not)
    - lms_load_model: Load specific model
    - lms_unload_model: Unload model to free memory
    - lms_ensure_model_loaded: Idempotent preload (RECOMMENDED)
    - lms_search_models: Search for models online
    - lms_download_model: Download a model from hub
    - lms_resolve_model: Resolve model with intelligent fallback (RECOMMENDED)
    - lms_server_status: Server health diagnostics
    """
    mcp_server.tool()(lms_list_loaded_models)
    mcp_server.tool()(lms_list_downloaded_models)
    mcp_server.tool()(lms_load_model)
    mcp_server.tool()(lms_unload_model)
    mcp_server.tool()(lms_ensure_model_loaded)
    mcp_server.tool()(lms_search_models)
    mcp_server.tool()(lms_download_model)
    mcp_server.tool()(lms_resolve_model)
    mcp_server.tool()(lms_server_status)


# Export all tools and registration function
__all__ = [
    'lms_list_loaded_models',
    'lms_list_downloaded_models',
    'lms_load_model',
    'lms_unload_model',
    'lms_ensure_model_loaded',
    'lms_search_models',
    'lms_download_model',
    'lms_resolve_model',
    'lms_server_status',
    'register_lms_cli_tools'
]


if __name__ == "__main__":
    """Test LMS CLI MCP tools."""
    print("Testing LMS CLI MCP Tools\n")
    print("=" * 80)

    # Test 1: Check server status
    print("\n1. Testing lms_server_status()...")
    result = lms_server_status()
    print(f"   Result: {result}")

    # Test 2: List loaded models
    print("\n2. Testing lms_list_loaded_models()...")
    result = lms_list_loaded_models()
    print(f"   Result: {result}")

    # Test 3: Ensure model loaded
    print("\n3. Testing lms_ensure_model_loaded()...")
    result = lms_ensure_model_loaded("qwen/qwen3-4b-thinking-2507")
    print(f"   Result: {result}")

    print("\n" + "=" * 80)
    print("Testing complete!")
