#!/usr/bin/env bash
# Setup script to configure lmstudio-bridge-enhanced for your system
# This script creates the MCP configuration with the correct paths

set -e

# Get the absolute path to this script's directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$SCRIPT_DIR"

echo "========================================="
echo "LM Studio Bridge Enhanced - Setup"
echo "========================================="
echo ""
echo "Project root: $PROJECT_ROOT"
echo ""

# Detect the MCP client being used
echo "Which MCP client are you configuring?"
echo "1) Claude Code (project .mcp.json)"
echo "2) LM Studio (~/.lmstudio/mcp.json)"
echo "3) Both"
read -rp "Enter choice [1-3]: " choice

case $choice in
    1|3)
        # Claude Code configuration
        read -rp "Enter path to your Claude Code project directory: " project_dir
        if [ ! -d "$project_dir" ]; then
            echo "Error: Directory $project_dir does not exist"
            exit 1
        fi
        
        MCP_JSON="$project_dir/.mcp.json"
        
        # Create or update .mcp.json
        if [ -f "$MCP_JSON" ]; then
            echo "Warning: $MCP_JSON already exists"
            read -rp "Backup and overwrite? (y/n): " backup
            if [ "$backup" = "y" ]; then
                cp "$MCP_JSON" "$MCP_JSON.backup"
                echo "Backup created: $MCP_JSON.backup"
            fi
        fi
        
        cat > "$MCP_JSON" << EOFCONFIG
{
  "mcpServers": {
    "lmstudio-bridge-enhanced": {
      "command": "python3",
      "args": [
        "$PROJECT_ROOT/main.py"
      ],
      "env": {
        "PYTHONPATH": "$PROJECT_ROOT",
        "LMSTUDIO_HOST": "localhost",
        "LMSTUDIO_PORT": "1234"
      }
    }
  }
}
EOFCONFIG
        
        echo "✅ Created: $MCP_JSON"
        ;;
esac

case $choice in
    2|3)
        # LM Studio configuration
        LMSTUDIO_CONFIG="$HOME/.lmstudio/mcp.json"
        
        # Check if LM Studio directory exists
        if [ ! -d "$HOME/.lmstudio" ]; then
            echo "Warning: ~/.lmstudio directory does not exist"
            echo "This will be created when you first run LM Studio"
        fi
        
        # Create or update mcp.json
        if [ -f "$LMSTUDIO_CONFIG" ]; then
            echo "Warning: $LMSTUDIO_CONFIG already exists"
            read -rp "Backup and overwrite? (y/n): " backup
            if [ "$backup" = "y" ]; then
                cp "$LMSTUDIO_CONFIG" "$LMSTUDIO_CONFIG.backup"
                echo "Backup created: $LMSTUDIO_CONFIG.backup"
            fi
        fi
        
        mkdir -p "$HOME/.lmstudio"
        
        cat > "$LMSTUDIO_CONFIG" << EOFCONFIG
{
  "mcpServers": {
    "lmstudio-bridge-enhanced": {
      "command": "python3",
      "args": [
        "$PROJECT_ROOT/main.py"
      ],
      "env": {
        "PYTHONPATH": "$PROJECT_ROOT",
        "LMSTUDIO_HOST": "localhost",
        "LMSTUDIO_PORT": "1234"
      }
    }
  }
}
EOFCONFIG
        
        echo "✅ Created: $LMSTUDIO_CONFIG"
        ;;
esac

echo ""
echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
echo "Configuration created with:"
echo "  - Project root: $PROJECT_ROOT"
echo "  - PYTHONPATH: $PROJECT_ROOT"
echo ""
echo "Next steps:"
echo "  1. Ensure LM Studio is running (localhost:1234)"
echo "  2. Restart your MCP client (Claude Code or LM Studio)"
echo "  3. Test the connection"
echo ""
echo "Optional: Edit the configuration to add:"
echo "  - DEFAULT_MODEL: Pin a specific model"
echo "  - Custom LMSTUDIO_HOST/PORT if needed"
echo ""
