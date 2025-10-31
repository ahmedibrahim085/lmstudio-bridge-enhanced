#!/usr/bin/env python3
from mcp.server.fastmcp import FastMCP
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
import requests
import json
import sys
import os
import asyncio
from typing import List, Dict, Any, Optional, Union

# Import constants
from config.constants import (
    DEFAULT_LMSTUDIO_HOST,
    DEFAULT_LMSTUDIO_PORT,
)

# Initialize FastMCP server
mcp = FastMCP("lmstudio-bridge-enhanced")

# LM Studio settings - configurable via environment variables
LMSTUDIO_HOST = os.getenv("LMSTUDIO_HOST", DEFAULT_LMSTUDIO_HOST)
LMSTUDIO_PORT = os.getenv("LMSTUDIO_PORT", str(DEFAULT_LMSTUDIO_PORT))
LMSTUDIO_API_BASE = f"http://{LMSTUDIO_HOST}:{LMSTUDIO_PORT}/v1"
DEFAULT_MODEL = "default"  # Will be replaced with whatever model is currently loaded

def log_error(message: str):
    """Log error messages to stderr for debugging"""
    print(f"ERROR: {message}", file=sys.stderr)

def log_info(message: str):
    """Log informational messages to stderr for debugging"""
    print(f"INFO: {message}", file=sys.stderr)

@mcp.tool()
async def health_check() -> str:
    """Check if LM Studio API is accessible.
    
    Returns:
        A message indicating whether the LM Studio API is running.
    """
    try:
        response = requests.get(f"{LMSTUDIO_API_BASE}/models")
        if response.status_code == 200:
            return "LM Studio API is running and accessible."
        else:
            return f"LM Studio API returned status code {response.status_code}."
    except Exception as e:
        return f"Error connecting to LM Studio API: {str(e)}"

@mcp.tool()
async def list_models() -> str:
    """List all available models in LM Studio.
    
    Returns:
        A formatted list of available models.
    """
    try:
        response = requests.get(f"{LMSTUDIO_API_BASE}/models")
        if response.status_code != 200:
            return f"Failed to fetch models. Status code: {response.status_code}"
        
        models = response.json().get("data", [])
        if not models:
            return "No models found in LM Studio."
        
        result = "Available models in LM Studio:\n\n"
        for model in models:
            result += f"- {model['id']}\n"
        
        return result
    except Exception as e:
        log_error(f"Error in list_models: {str(e)}")
        return f"Error listing models: {str(e)}"

@mcp.tool()
async def get_current_model() -> str:
    """Get the currently loaded model in LM Studio.
    
    Returns:
        The name of the currently loaded model.
    """
    try:
        # LM Studio doesn't have a direct endpoint for currently loaded model
        # We'll check which model responds to a simple completion request
        response = requests.post(
            f"{LMSTUDIO_API_BASE}/chat/completions",
            json={
                "messages": [{"role": "system", "content": "What model are you?"}],
                "temperature": 0.7,
                "max_tokens": 10
            }
        )
        
        if response.status_code != 200:
            return f"Failed to identify current model. Status code: {response.status_code}"
        
        # Extract model info from response
        model_info = response.json().get("model", "Unknown")
        return f"Currently loaded model: {model_info}"
    except Exception as e:
        log_error(f"Error in get_current_model: {str(e)}")
        return f"Error identifying current model: {str(e)}"

@mcp.tool()
async def chat_completion(prompt: str, system_prompt: str = "", temperature: float = 0.7, max_tokens: int = 1024) -> str:
    """Generate a completion from the current LM Studio model.

    Args:
        prompt: The user's prompt to send to the model
        system_prompt: Optional system instructions for the model
        temperature: Controls randomness (0.0 to 1.0)
        max_tokens: Maximum number of tokens to generate

    Returns:
        The model's response to the prompt
    """
    try:
        messages = []

        # Add system message if provided
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # Add user message
        messages.append({"role": "user", "content": prompt})

        log_info(f"Sending request to LM Studio with {len(messages)} messages")

        response = requests.post(
            f"{LMSTUDIO_API_BASE}/chat/completions",
            json={
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
        )

        if response.status_code != 200:
            log_error(f"LM Studio API error: {response.status_code}")
            return f"Error: LM Studio returned status code {response.status_code}"

        response_json = response.json()
        log_info(f"Received response from LM Studio")

        # Extract the assistant's message
        choices = response_json.get("choices", [])
        if not choices:
            return "Error: No response generated"

        message = choices[0].get("message", {})
        content = message.get("content", "")

        if not content:
            return "Error: Empty response from model"

        return content
    except Exception as e:
        log_error(f"Error in chat_completion: {str(e)}")
        return f"Error generating completion: {str(e)}"

@mcp.tool()
async def text_completion(prompt: str, temperature: float = 0.7, max_tokens: int = 1024, stop_sequences: Optional[List[str]] = None) -> str:
    """Generate a raw text completion (non-chat format) from LM Studio.

    This endpoint is simpler and faster than chat completions for single-turn tasks
    like code completion, text continuation, or simple Q&A.

    Args:
        prompt: The text prompt to complete
        temperature: Controls randomness (0.0 to 2.0, default 0.7)
        max_tokens: Maximum number of tokens to generate (default 1024)
        stop_sequences: Optional list of sequences where generation will stop

    Returns:
        The completed text from the model
    """
    try:
        payload = {
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        # Add stop sequences if provided
        if stop_sequences:
            payload["stop"] = stop_sequences

        log_info(f"Sending text completion request to LM Studio")

        response = requests.post(
            f"{LMSTUDIO_API_BASE}/completions",
            json=payload,
            timeout=30
        )

        if response.status_code != 200:
            log_error(f"LM Studio API error: {response.status_code}")
            return f"Error: LM Studio returned status code {response.status_code}"

        response_json = response.json()
        log_info(f"Received text completion from LM Studio")

        # Extract the completion text
        choices = response_json.get("choices", [])
        if not choices:
            return "Error: No completion generated"

        text = choices[0].get("text", "")

        if not text:
            return "Error: Empty completion from model"

        return text
    except Exception as e:
        log_error(f"Error in text_completion: {str(e)}")
        return f"Error generating text completion: {str(e)}"

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
    try:
        payload = {"input": text}

        # Only include model if it's not the default
        if model != "default":
            payload["model"] = model

        log_info(f"Sending embeddings request to LM Studio")

        response = requests.post(
            f"{LMSTUDIO_API_BASE}/embeddings",
            json=payload,
            timeout=30
        )

        if response.status_code != 200:
            log_error(f"LM Studio API error: {response.status_code}")
            error_response = {
                "error": f"LM Studio returned status code {response.status_code}"
            }
            return json.dumps(error_response)

        log_info(f"Received embeddings from LM Studio")

        # Return the JSON response as a string
        return response.text

    except requests.exceptions.RequestException as e:
        log_error(f"Error in generate_embeddings: {str(e)}")
        error_response = {
            "error": f"Failed to generate embeddings: {str(e)}"
        }
        return json.dumps(error_response)
    except Exception as e:
        log_error(f"Unexpected error in generate_embeddings: {str(e)}")
        error_response = {
            "error": f"Unexpected error during embedding generation: {str(e)}"
        }
        return json.dumps(error_response)

@mcp.tool()
async def create_response(input_text: str, previous_response_id: Optional[str] = None, stream: bool = False, model: Optional[str] = None) -> str:
    """Create a response using LM Studio's stateful /v1/responses endpoint.

    This endpoint provides stateful conversations where you can reference previous
    responses without managing message history manually.

    Args:
        input_text: The user's input text
        previous_response_id: Optional ID from a previous response to continue conversation
        stream: Whether to stream the response (default False)
        model: Model to use (default: uses currently loaded model)

    Returns:
        JSON string with response including ID for future reference
    """
    try:
        # Get current model if not specified
        if model is None:
            try:
                current_model_response = await get_current_model()
                model = current_model_response.replace("Currently loaded model: ", "").strip()
            except:
                from config.constants import DEFAULT_FALLBACK_MODEL
                model = DEFAULT_FALLBACK_MODEL

        payload = {
            "input": input_text,
            "model": model,
            "stream": stream
        }

        # Add previous response ID if provided (for conversation continuity)
        if previous_response_id:
            payload["previous_response_id"] = previous_response_id

        log_info(f"Sending stateful response request to LM Studio")

        response = requests.post(
            f"{LMSTUDIO_API_BASE}/responses",
            json=payload,
            timeout=60  # Longer timeout for reasoning
        )

        if response.status_code != 200:
            log_error(f"LM Studio API error: {response.status_code}")
            error_response = {
                "error": f"LM Studio returned status code {response.status_code}"
            }
            return json.dumps(error_response)

        log_info(f"Received stateful response from LM Studio")

        # Return the JSON response as a string (includes response ID)
        return response.text

    except requests.exceptions.RequestException as e:
        log_error(f"Error in create_response: {str(e)}")
        error_response = {
            "error": f"Failed to create response: {str(e)}"
        }
        return json.dumps(error_response)
    except Exception as e:
        log_error(f"Unexpected error in create_response: {str(e)}")
        error_response = {
            "error": f"Unexpected error during response creation: {str(e)}"
        }
        return json.dumps(error_response)

@mcp.tool()
async def test_autonomous_poc(task: str, file_path: str = None) -> str:
    """
    PoC: Test autonomous loop with REAL filesystem MCP (read_file only).

    This validates:
    - Can we connect to battle-tested filesystem MCP as a client?
    - Can we get its tools?
    - Can Qwen use them autonomously?
    - Does the whole flow work end-to-end?

    Args:
        task: The task for Qwen (e.g., "Read README.md and summarize")
        file_path: Optional specific file path to read

    Returns:
        Qwen's final answer after autonomous tool usage

    Example:
        test_autonomous_poc("Read README.md and tell me the first sentence")
    """
    log_info("=== Starting PoC: Autonomous Loop with Filesystem MCP ===")

    try:
        # 1. Connect to REAL filesystem MCP
        log_info("Step 1: Connecting to filesystem MCP...")

        from config.constants import (
            DEFAULT_MCP_NPX_COMMAND,
            DEFAULT_MCP_NPX_ARGS,
            MCP_PACKAGES,
            DEFAULT_FILESYSTEM_ROOT
        )

        server_params = StdioServerParameters(
            command=DEFAULT_MCP_NPX_COMMAND,
            args=DEFAULT_MCP_NPX_ARGS + [
                MCP_PACKAGES["filesystem"],
                DEFAULT_FILESYSTEM_ROOT
            ]
        )

        # Spawn and connect
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize MCP session
                log_info("Step 2: Initializing MCP session...")
                init_result = await session.initialize()
                log_info(f"MCP initialized: {init_result.serverInfo.name}")

                # 2. Get tools from filesystem MCP
                log_info("Step 3: Getting tools from filesystem MCP...")
                tools_result = await session.list_tools()
                log_info(f"Found {len(tools_result.tools)} tools")

                # Find read_file tool
                read_file_tool = None
                for tool in tools_result.tools:
                    log_info(f"  - {tool.name}: {tool.description}")
                    if tool.name == "read_file":
                        read_file_tool = tool

                if not read_file_tool:
                    return "Error: read_file tool not found in filesystem MCP"

                # 3. Convert to OpenAI format
                log_info("Step 4: Converting tool to OpenAI format...")
                openai_tools = [{
                    "type": "function",
                    "function": {
                        "name": read_file_tool.name,
                        "description": read_file_tool.description,
                        "parameters": read_file_tool.inputSchema
                    }
                }]

                # 4. Autonomous loop with Qwen
                log_info("Step 5: Starting autonomous loop with Qwen...")
                messages = [{"role": "user", "content": task}]

                for round_num in range(5):  # Max 5 rounds
                    log_info(f"\n--- Round {round_num + 1} ---")

                    # Ask Qwen
                    log_info("Calling Qwen with tools...")
                    from config.constants import DEFAULT_AUTONOMOUS_MODEL

                    response = requests.post(
                        f"{LMSTUDIO_API_BASE}/chat/completions",
                        json={
                            "model": DEFAULT_AUTONOMOUS_MODEL,
                            "messages": messages,
                            "tools": openai_tools,
                            "tool_choice": "auto"
                        },
                        timeout=30
                    )

                    if response.status_code != 200:
                        return f"Error: Qwen API returned {response.status_code}: {response.text}"

                    response_data = response.json()
                    message = response_data["choices"][0]["message"]

                    log_info(f"Qwen response: {message.get('content', 'No content')[:100]}...")

                    # Check for tool calls
                    if message.get("tool_calls"):
                        log_info(f"Qwen requested {len(message['tool_calls'])} tool call(s)")

                        # Add assistant message
                        messages.append(message)

                        # Execute each tool via REAL MCP
                        for tool_call in message["tool_calls"]:
                            tool_name = tool_call["function"]["name"]
                            tool_args = json.loads(tool_call["function"]["arguments"])

                            log_info(f"Executing {tool_name} via filesystem MCP with args: {tool_args}")

                            # Call REAL MCP tool
                            result = await session.call_tool(tool_name, tool_args)

                            log_info(f"MCP result: {str(result.content)[:200]}...")

                            # Add tool result to messages
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call["id"],
                                "content": str(result.content[0].text) if result.content else "No result"
                            })
                    else:
                        # Qwen has final answer
                        log_info("Qwen provided final answer")
                        final_answer = message.get("content", "No content in response")
                        log_info("=== PoC Complete: SUCCESS ===")
                        return final_answer

                return "Max rounds reached without final answer"

    except Exception as e:
        log_error(f"PoC failed: {str(e)}")
        import traceback
        log_error(traceback.format_exc())
        return f"Error during PoC: {str(e)}"

def main():
    """Entry point for the package when installed via pip"""
    log_info("Starting LM Studio Bridge MCP Server")
    mcp.run(transport='stdio')

if __name__ == "__main__":
    # Initialize and run the server
    main()