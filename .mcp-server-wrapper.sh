#!/usr/bin/env bash
set -e

# Resolve user's home directory
if [ -z "$HOME" ]; then
    echo "ERROR: HOME environment variable not set" >&2
    exit 1
fi

# Standard installation location
INSTALL_DIR="$HOME/.local/share/claude-context-local"

# Check if installation exists
if [ ! -d "$INSTALL_DIR" ]; then
    echo "ERROR: claude-context-local not found at $INSTALL_DIR" >&2
    echo "" >&2
    echo "Please install with:" >&2
    echo "  curl -fsSL https://raw.githubusercontent.com/FarhanAliRaza/claude-context-local/main/scripts/install.sh | bash" >&2
    exit 1
fi

# Find uv executable (check common locations)
UV_CMD=""
if command -v uv &> /dev/null; then
    UV_CMD="uv"
elif [ -f "$HOME/.langflow/uv/uv" ]; then
    UV_CMD="$HOME/.langflow/uv/uv"
elif [ -f "$HOME/.cargo/bin/uv" ]; then
    UV_CMD="$HOME/.cargo/bin/uv"
elif [ -f "$HOME/.local/bin/uv" ]; then
    UV_CMD="$HOME/.local/bin/uv"
else
    echo "ERROR: uv command not found" >&2
    echo "" >&2
    echo "Install uv with:" >&2
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
    exit 1
fi

# Set storage directory to project-local path
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export CODE_SEARCH_STORAGE="$PROJECT_ROOT/.code-search-index"

# Execute the MCP server using uv
exec "$UV_CMD" run --directory "$INSTALL_DIR" python mcp_server/server.py "$@"
