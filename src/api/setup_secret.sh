#!/bin/bash

# Setup Claude API key as Databricks secret
# Usage: ./setup_secret.sh [profile]

set -e

PROFILE="${1:-aws-apps}"

echo "🔐 Setting up Claude API key secret for Databricks Apps"
echo "Profile: $PROFILE"

# Load API key from .env file
if [ -f "../../.env" ]; then
    CLAUDE_KEY=$(grep "CLAUDE_API_KEY=" ../../.env | cut -d '=' -f2)
    echo "✅ Found API key in .env file"
elif [ -n "$CLAUDE_API_KEY" ]; then
    CLAUDE_KEY="$CLAUDE_API_KEY"
    echo "✅ Using CLAUDE_API_KEY environment variable"
else
    echo -n "Enter your Claude API key: "
    read -s CLAUDE_KEY
    echo ""
fi

# Create the secret in Databricks (simpler path without scope)
echo "📝 Creating secret 'claude_api_key' in Databricks..."

# Use the simpler secret path that Apps can access
echo -n "$CLAUDE_KEY" | databricks secrets put-secret apps claude_api_key --profile $PROFILE 2>/dev/null || {
    # If apps scope doesn't exist, create it first
    echo "Creating apps scope..."
    databricks secrets create-scope apps --profile $PROFILE 2>/dev/null || true
    echo -n "$CLAUDE_KEY" | databricks secrets put-secret apps claude_api_key --profile $PROFILE
}

echo "✅ Secret 'claude_api_key' created successfully"
echo ""
echo "The secret can now be accessed by your Databricks App"
echo "Deploy your app with: ./deploy_dab_generator.sh $PROFILE"