#!/bin/bash

# Deploy DAB Generator Streamlit App to Databricks Apps
# Usage: ./deploy_dab_generator.sh [profile]

set -e

# Configuration
APP_NAME="dab-generator"
PROFILE="${1:-aws-apps}"
APP_DIR="$(dirname "$0")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Deploying DAB Generator to Databricks Apps${NC}"
echo -e "Profile: ${YELLOW}$PROFILE${NC}"
echo -e "App Directory: ${YELLOW}$APP_DIR${NC}"
echo ""

# Function to check command status
check_status() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ $1${NC}"
    else
        echo -e "${RED}❌ $1${NC}"
        exit 1
    fi
}

# Step 1: Validate configuration
echo -e "${YELLOW}1️⃣ Validating configuration...${NC}"
if [ ! -f "$APP_DIR/app.yaml" ]; then
    echo -e "${RED}❌ app.yaml not found in $APP_DIR${NC}"
    exit 1
fi
check_status "app.yaml found"

if [ ! -f "$APP_DIR/app.py" ]; then
    echo -e "${RED}❌ app.py not found in $APP_DIR${NC}"
    exit 1
fi
check_status "app.py found"

if [ ! -f "$APP_DIR/requirements.txt" ]; then
    echo -e "${RED}❌ requirements.txt not found in $APP_DIR${NC}"
    exit 1
fi
check_status "requirements.txt found"

# Step 2: Check Databricks CLI authentication
echo -e "${YELLOW}2️⃣ Checking Databricks CLI authentication...${NC}"
databricks auth profiles --profile $PROFILE > /dev/null 2>&1
check_status "Databricks CLI authenticated with profile: $PROFILE"

# Step 3: Create secret for Claude API key if needed
echo -e "${YELLOW}3️⃣ Setting up secrets...${NC}"
echo -e "Checking if Claude API key secret exists..."

# First, ensure the secret scope exists
SCOPE_EXISTS=$(databricks secrets list-scopes --profile $PROFILE 2>/dev/null | grep -c "dabscribe" || true)

if [ "$SCOPE_EXISTS" -eq 0 ]; then
    echo -e "${YELLOW}Creating secret scope 'dabscribe'...${NC}"
    databricks secrets create-scope dabscribe --profile $PROFILE
    check_status "Secret scope 'dabscribe' created"
else
    echo -e "${GREEN}✅ Secret scope 'dabscribe' already exists${NC}"
fi

# Check if secret exists
SECRET_EXISTS=$(databricks secrets list-secrets dabscribe --profile $PROFILE 2>/dev/null | grep -c "dab_generator_claude_key" || true)

if [ "$SECRET_EXISTS" -eq 0 ]; then
    echo -e "${YELLOW}Creating Claude API key secret...${NC}"

    # Check if we have the key in .env file
    if [ -f "$APP_DIR/../../.env" ] && grep -q "CLAUDE_API_KEY=" "$APP_DIR/../../.env"; then
        echo -e "${GREEN}Found Claude API key in .env file${NC}"
        CLAUDE_KEY=$(grep "CLAUDE_API_KEY=" "$APP_DIR/../../.env" | cut -d '=' -f2)
    else
        # Prompt for API key
        echo -n "Enter your Claude API key: "
        read -s CLAUDE_KEY
        echo ""
    fi

    # Create secret using the correct syntax
    echo -n "$CLAUDE_KEY" | databricks secrets put-secret dabscribe dab_generator_claude_key --profile $PROFILE
    check_status "Claude API key secret created"
else
    echo -e "${GREEN}✅ Claude API key secret already exists${NC}"
fi

# Step 4: Sync code to workspace
echo -e "${YELLOW}4️⃣ Syncing code to Databricks Workspace...${NC}"
cd "$APP_DIR"

# Define workspace path
WORKSPACE_PATH="/Workspace/Users/alex.miller@databricks.com/$APP_NAME"
echo -e "Workspace path: ${YELLOW}$WORKSPACE_PATH${NC}"

# Sync files to workspace (without --watch for one-time sync)
databricks sync . "$WORKSPACE_PATH" --profile $PROFILE
check_status "Code synced to workspace"

# Step 5: Create or deploy the app
echo -e "${YELLOW}5️⃣ Creating/Deploying app to Databricks Apps...${NC}"

# Check if app exists
if databricks apps get $APP_NAME --profile $PROFILE > /dev/null 2>&1; then
    echo -e "${GREEN}App exists, deploying update...${NC}"
    # Deploy update to existing app with source code from workspace
    databricks apps deploy $APP_NAME --source-code-path "$WORKSPACE_PATH" --profile $PROFILE
else
    echo -e "${YELLOW}App does not exist, creating new app...${NC}"
    # Create new app
    databricks apps create $APP_NAME --profile $PROFILE
    check_status "App created successfully"

    # Now deploy the app with source code from workspace
    echo -e "${YELLOW}Deploying app code from workspace...${NC}"
    databricks apps deploy $APP_NAME --source-code-path "$WORKSPACE_PATH" --profile $PROFILE
fi

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ App deployed successfully!${NC}"

    # Get app URL
    echo -e "${YELLOW}6️⃣ Getting app URL...${NC}"
    APP_INFO=$(databricks apps get $APP_NAME --profile $PROFILE 2>/dev/null || true)

    if [ ! -z "$APP_INFO" ]; then
        echo -e "${GREEN}📱 App Information:${NC}"
        echo "$APP_INFO" | grep -E "(url|status)" || true
    fi

    echo ""
    echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
    echo -e "${YELLOW}Next steps:${NC}"
    echo -e "1. Access your app at the URL shown above"
    echo -e "2. The app will use OAuth authentication automatically"
    echo -e "3. Test DAB generation workflows through the UI"

else
    echo -e "${RED}❌ Deployment failed${NC}"
    echo -e "Check the error messages above and try again"
    exit 1
fi

# Step 6: Monitor deployment (optional)
echo ""
echo -e "${YELLOW}📋 Useful Commands:${NC}"
echo ""
echo -e "${GREEN}Monitor app logs:${NC}"
echo "  databricks apps logs $APP_NAME --profile $PROFILE --follow"
echo ""
echo -e "${GREEN}Check app status:${NC}"
echo "  databricks apps get $APP_NAME --profile $PROFILE"
echo ""
echo -e "${GREEN}Redeploy after changes:${NC}"
echo "  ./deploy_dab_generator.sh $PROFILE"
echo ""
echo -e "${GREEN}Development mode (continuous sync):${NC}"
echo "  databricks sync --watch . $WORKSPACE_PATH --profile $PROFILE"
echo ""
echo -e "${YELLOW}💡 Tip:${NC} Run sync --watch in a separate terminal during development for live updates"