#!/bin/bash
# Enhanced deployment script for Databricks Apps MCP Server

set -e

# Load environment variables from .env file if it exists
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MCP_ROOT="$(dirname "$SCRIPT_DIR")"

# Check for .env file in MCP root directory
if [ -f "$MCP_ROOT/.env" ]; then
    echo "📄 Loading environment variables from .env file..."
    set -a  # automatically export all variables
    source "$MCP_ROOT/.env"
    set +a  # disable automatic export
fi

# Configuration with environment variable support
APP_NAME=${DATABRICKS_APP_NAME:-"databricks-mcp-server"}
PROFILE=${DATABRICKS_CONFIG_PROFILE:-"DEFAULT"}
DATABRICKS_HOST=${DATABRICKS_HOST:-""}

# Validate required environment variables
if [ -z "$DATABRICKS_HOST" ]; then
    echo "⚠️  Warning: DATABRICKS_HOST not set. Make sure your profile is configured correctly."
fi

# Function to find the best Databricks CLI
find_databricks_cli() {
    # Try different locations in order of preference
    local cli_paths=(
        "databricks"                    # Check PATH first
        "/usr/local/bin/databricks"     # Common Linux/macOS
        "/opt/homebrew/bin/databricks"  # macOS Homebrew
        "$HOME/.local/bin/databricks"   # User local install
    )
    
    for cli_path in "${cli_paths[@]}"; do
        if command -v "$cli_path" >/dev/null 2>&1; then
            # Test if it's the new CLI (v0.2+)
            if "$cli_path" --version 2>/dev/null | grep -q "v0\.[2-9]"; then
                echo "$cli_path"
                return 0
            fi
        fi
    done
    
    # Fallback to 'databricks' and hope for the best
    echo "databricks"
}

DATABRICKS_CMD=$(find_databricks_cli)

echo "🚀 Deploying MCP Server to Databricks Apps..."
echo "📱 App Name: $APP_NAME"
echo "👤 Profile: $PROFILE"
echo "🌐 Host: ${DATABRICKS_HOST:-"(using profile default)"}"
echo "📁 MCP Root: $MCP_ROOT"

# Ensure we're in the MCP directory
cd "$MCP_ROOT"

# Check if required files exist
if [ ! -f "app.yaml" ]; then
    echo "❌ app.yaml not found! Creating it..."
    cat > app.yaml << EOF
# Databricks Apps entry point configuration
command: ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]
EOF
    echo "✅ Created app.yaml"
fi

if [ ! -f "requirements.txt" ]; then
    echo "❌ requirements.txt not found in MCP directory!"
    echo "   This file is required for Databricks Apps to install dependencies."
    exit 1
fi

echo "📦 Using MCP app requirements.txt with $(grep -v '^#' requirements.txt | grep -v '^$' | wc -l | tr -d ' ') dependencies"

# Check if Python utils exist
if [ ! -f "scripts/databricks_apps_utils.py" ]; then
    echo "❌ databricks_apps_utils.py not found!"
    exit 1
fi

# Use Python utility for deployment
echo "🔧 Using Python utility for deployment..."
python scripts/databricks_apps_utils.py deploy --app-name "$APP_NAME" --profile "$PROFILE"

# Get URLs using the utility
echo ""
echo "📍 Getting app URLs..."
python scripts/databricks_apps_utils.py url --app-name "$APP_NAME" --profile "$PROFILE"

# Test the deployment
echo ""
echo "🧪 Testing MCP connection..."
python scripts/databricks_apps_utils.py test --app-name "$APP_NAME" --profile "$PROFILE"

echo ""
echo "✅ Deployment and testing complete!"
echo ""
echo "🎯 Next steps:"
echo "  1. Test individual tools: python scripts/databricks_apps_utils.py test-tool --tool health"
echo "  2. View app logs: databricks apps logs $APP_NAME --profile $PROFILE"
echo "  3. Open app in browser using the URL above"
