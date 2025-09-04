#!/bin/bash
# Setup script for Databricks CLI v2

set -e

echo "🔧 Setting up Databricks CLI for MCP server..."

# Check if new CLI is already installed
if command -v databricks >/dev/null 2>&1; then
    CLI_VERSION=$(databricks --version 2>/dev/null | head -n1 || echo "unknown")
    if echo "$CLI_VERSION" | grep -q "v0\.[2-9]"; then
        echo "✅ Databricks CLI v2 is already installed: $CLI_VERSION"
        exit 0
    else
        echo "⚠️  Found older CLI version: $CLI_VERSION"
        echo "   Installing newer version..."
    fi
fi

# Install the new CLI
echo "📥 Installing Databricks CLI v2..."

if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    if command -v brew >/dev/null 2>&1; then
        echo "   Using Homebrew..."
        brew install databricks/tap/databricks
    else
        echo "   Using curl installer..."
        curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh
    fi
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    echo "   Using curl installer..."
    curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh
else
    echo "❌ Unsupported OS: $OSTYPE"
    echo "   Please install manually: https://docs.databricks.com/dev-tools/cli/install.html"
    exit 1
fi

# Verify installation
echo "🧪 Verifying installation..."
if command -v databricks >/dev/null 2>&1; then
    CLI_VERSION=$(databricks --version 2>/dev/null | head -n1)
    echo "✅ Successfully installed: $CLI_VERSION"
    
    echo ""
    echo "🎯 Next steps:"
    echo "  1. Configure authentication:"
    echo "     databricks auth login --host https://your-workspace.cloud.databricks.com --profile your-profile"
    echo "  2. Test the setup:"
    echo "     cd mcp && ./scripts/deploy.sh"
else
    echo "❌ Installation failed. Please install manually."
    exit 1
fi
