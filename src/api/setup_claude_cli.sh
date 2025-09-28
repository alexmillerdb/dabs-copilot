#!/bin/bash

# Setup script for Claude Code CLI in Databricks Apps environment
# This script installs the CLI and makes it available to the Python SDK

set -e

echo "🚀 Setting up Claude Code CLI for Databricks Apps..."

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CLI_DIR="$SCRIPT_DIR/claude_cli"

# Create directory for CLI
mkdir -p "$CLI_DIR"
cd "$CLI_DIR"

# Check if Node.js is available (it should be in Apps environment)
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not available. Installing Node.js..."
    # For Databricks Apps, we might need to use a different approach
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
    apt-get install -y nodejs
fi

# Check if npm is available
if ! command -v npm &> /dev/null; then
    echo "❌ npm is not available"
    exit 1
fi

echo "📦 Installing Claude Code CLI..."

# Go back to script directory where package.json is
cd "$SCRIPT_DIR"

# Install dependencies from package.json
npm install

# Find the CLI binary (it will be in the app's node_modules)
CLAUDE_CLI_PATH="$SCRIPT_DIR/node_modules/.bin/claude"

if [ -f "$CLAUDE_CLI_PATH" ]; then
    echo "✅ Claude Code CLI installed successfully at: $CLAUDE_CLI_PATH"

    # Make it executable
    chmod +x "$CLAUDE_CLI_PATH"

    # Export the path for use in Python
    export CLAUDE_CLI_PATH="$CLAUDE_CLI_PATH"

    # Create a marker file with the path for Python to read
    echo "$CLAUDE_CLI_PATH" > "$SCRIPT_DIR/claude_cli_path.txt"

    echo "✅ CLI path saved to claude_cli_path.txt"
else
    echo "❌ Failed to find Claude Code CLI binary"
    exit 1
fi

echo "🎉 Claude Code CLI setup completed!"