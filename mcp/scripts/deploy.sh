#!/bin/bash
# Enhanced deployment script for Databricks Apps MCP Server

set -e

# Load environment variables from .env file if it exists
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MCP_ROOT="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$MCP_ROOT")"

# Function to load and validate .env file
load_env_file() {
    local env_file="$PROJECT_ROOT/.env"
    
    if [ -f "$env_file" ]; then
        echo "📄 Found .env file at: $env_file"
        echo "📄 Loading environment variables from .env file..."
        
        # Show file size and modification time for debugging
        if [ "${DEBUG_ENV:-}" = "true" ]; then
            echo "🐛 Debug: .env file details:"
            ls -la "$env_file" | sed 's/^/   /'
            echo "🐛 Debug: .env file contents (with values hidden):"
            sed 's/=.*/=***/' "$env_file" | sed 's/^/   /'
        fi
        
        # Validate .env file format before sourcing
        if ! grep -q "^[A-Z_][A-Z0-9_]*=" "$env_file" 2>/dev/null; then
            echo "⚠️  Warning: .env file exists but appears to be empty or malformed"
            echo "   Expected format: VARIABLE_NAME=value"
            if [ "${DEBUG_ENV:-}" = "true" ]; then
                echo "🐛 Debug: Raw file contents:"
                cat "$env_file" | sed 's/^/   /'
            fi
        fi
        
        # Show what we're about to load (without values for security)
        echo "🔍 Environment variables found in .env:"
        grep -E "^[A-Z_][A-Z0-9_]*=" "$env_file" | cut -d'=' -f1 | sed 's/^/   - /' || echo "   (none found)"
        
        # Store current values for comparison
        if [ "${DEBUG_ENV:-}" = "true" ]; then
            OLD_APP_NAME="${DATABRICKS_APP_NAME:-}"
            OLD_PROFILE="${DATABRICKS_CONFIG_PROFILE:-}"
            OLD_HOST="${DATABRICKS_HOST:-}"
        fi
        
        set -a  # automatically export all variables
        source "$env_file"
        set +a  # disable automatic export
        
        # Show what changed if debug is enabled
        if [ "${DEBUG_ENV:-}" = "true" ]; then
            echo "🐛 Debug: Environment variable changes:"
            [ "$OLD_APP_NAME" != "${DATABRICKS_APP_NAME:-}" ] && echo "   DATABRICKS_APP_NAME: '$OLD_APP_NAME' -> '${DATABRICKS_APP_NAME:-}'"
            [ "$OLD_PROFILE" != "${DATABRICKS_CONFIG_PROFILE:-}" ] && echo "   DATABRICKS_CONFIG_PROFILE: '$OLD_PROFILE' -> '${DATABRICKS_CONFIG_PROFILE:-}'"
            [ "$OLD_HOST" != "${DATABRICKS_HOST:-}" ] && echo "   DATABRICKS_HOST: '$OLD_HOST' -> '${DATABRICKS_HOST:-}'"
        fi
        
        echo "✅ Environment variables loaded successfully"
    else
        echo "📄 No .env file found at: $env_file"
        echo "   (.env should be in the project root directory, not the MCP subdirectory)"
        echo "   You can create one to set custom environment variables"
        echo "   Expected variables: DATABRICKS_APP_NAME, DATABRICKS_CONFIG_PROFILE, DATABRICKS_HOST"
    fi
}

# Function to create .env file from template if it doesn't exist
create_env_if_missing() {
    local env_file="$PROJECT_ROOT/.env"
    local env_example="$PROJECT_ROOT/env.example"
    local mcp_env_example="$MCP_ROOT/env.example"
    
    # Check for template in project root first, then MCP directory
    local template_file=""
    if [ -f "$env_example" ]; then
        template_file="$env_example"
    elif [ -f "$mcp_env_example" ]; then
        template_file="$mcp_env_example"
        echo "📋 Found template in MCP directory, will copy to project root"
    fi
    
    if [ ! -f "$env_file" ] && [ -n "$template_file" ]; then
        echo "🤔 Would you like to create a .env file from the template? (y/N)"
        echo "   Template: $template_file"
        echo "   Target: $env_file"
        if [ "${AUTO_CREATE_ENV:-}" = "true" ]; then
            echo "   AUTO_CREATE_ENV=true, creating .env file automatically..."
            cp "$template_file" "$env_file"
            echo "✅ Created .env file from template. Please edit it with your values."
            echo "   Edit: $env_file"
        else
            echo "   Run with AUTO_CREATE_ENV=true to create automatically, or:"
            echo "   cp $template_file $env_file"
        fi
    elif [ ! -f "$env_file" ]; then
        echo "📄 No .env file or template found"
        echo "   Expected .env location: $env_file"
        echo "   You can create one manually with these variables:"
        echo "   DATABRICKS_APP_NAME, DATABRICKS_CONFIG_PROFILE, DATABRICKS_HOST"
    fi
}

# Create .env if missing and load environment variables
create_env_if_missing
load_env_file

# Configuration with environment variable support
APP_NAME=${DATABRICKS_APP_NAME:-"databricks-mcp-server"}
PROFILE=${DATABRICKS_CONFIG_PROFILE:-"DEFAULT"}
DATABRICKS_HOST=${DATABRICKS_HOST:-""}

# Debug: Show final configuration values
echo ""
echo "🔧 Final Configuration:"
echo "   APP_NAME: $APP_NAME ${DATABRICKS_APP_NAME:+(from env)}"
echo "   PROFILE: $PROFILE ${DATABRICKS_CONFIG_PROFILE:+(from env)}"
echo "   DATABRICKS_HOST: ${DATABRICKS_HOST:-"(not set)"} ${DATABRICKS_HOST:+(from env)}"

# Validate required environment variables
if [ -z "$DATABRICKS_HOST" ]; then
    echo "⚠️  Warning: DATABRICKS_HOST not set. Make sure your profile is configured correctly."
    echo "   To fix this, either:"
    echo "   1. Add DATABRICKS_HOST=your-workspace-url to your .env file"
    echo "   2. Configure your Databricks CLI profile with: databricks configure --profile $PROFILE"
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
echo "📁 Project Root: $PROJECT_ROOT"
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
