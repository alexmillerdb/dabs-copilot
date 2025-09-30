#!/bin/bash

# Startup script for DABscribe in Databricks Apps
# This script ensures Claude CLI is set up before starting Streamlit

echo "🚀 Starting DABscribe..."

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Run setup if CLI is not already installed
if [ ! -f "$SCRIPT_DIR/claude_cli_path.txt" ]; then
    echo "📦 Setting up Claude CLI..."
    bash "$SCRIPT_DIR/setup_claude_cli.sh"
fi

# Export the CLI path
if [ -f "$SCRIPT_DIR/claude_cli_path.txt" ]; then
    export CLAUDE_CLI_PATH=$(cat "$SCRIPT_DIR/claude_cli_path.txt")
    echo "✅ Claude CLI path: $CLAUDE_CLI_PATH"
fi

# Get port from environment variable or use 8000 as default (Databricks Apps requirement)
PORT=${PORT:-8000}

# Start Streamlit app
echo "🎯 Starting Streamlit app on port $PORT..."
exec streamlit run "$SCRIPT_DIR/app.py" --server.port=$PORT --server.address=0.0.0.0