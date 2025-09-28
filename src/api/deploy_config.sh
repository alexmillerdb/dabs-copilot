#!/bin/bash

# Deployment configuration for DABscribe
# This script sets up environment variables before deployment

# Load the Claude API key from .env file
if [ -f "../../.env" ]; then
    export $(grep CLAUDE_API_KEY ../../.env | xargs)
    echo "✅ Loaded CLAUDE_API_KEY from .env"
else
    echo "⚠️ .env file not found. Please set CLAUDE_API_KEY environment variable"
    echo -n "Enter your Claude API key: "
    read -s CLAUDE_API_KEY
    export CLAUDE_API_KEY
    echo ""
fi

# Export for app.yaml substitution
echo "📝 Creating temporary app.yaml with API key..."

# Create a temporary app.yaml with the actual API key
envsubst < app.yaml > app_temp.yaml

echo "✅ Configuration ready for deployment"