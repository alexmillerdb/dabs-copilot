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

# Check if secret exists (will fail silently if not)
if ! databricks secrets get --profile $PROFILE --scope apps --key dab_generator_claude_key > /dev/null 2>&1; then
    echo -e "${YELLOW}Creating secret scope and key...${NC}"

    # Create scope if it doesn't exist
    databricks secrets create-scope --profile $PROFILE --scope apps 2>/dev/null || true

    # Prompt for API key
    echo -n "Enter your Claude API key: "
    read -s CLAUDE_KEY
    echo ""

    # Create secret
    echo "$CLAUDE_KEY" | databricks secrets put --profile $PROFILE --scope apps --key dab_generator_claude_key --string-value
    check_status "Claude API key secret created"
else
    echo -e "${GREEN}✅ Claude API key secret already exists${NC}"
fi

# Step 4: Deploy the app
echo -e "${YELLOW}4️⃣ Deploying app to Databricks Apps...${NC}"
cd "$APP_DIR"

# Deploy command
databricks apps deploy $APP_NAME --profile $PROFILE

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ App deployed successfully!${NC}"

    # Get app URL
    echo -e "${YELLOW}5️⃣ Getting app URL...${NC}"
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

# Step 5: Monitor deployment (optional)
echo ""
echo -e "${YELLOW}To monitor your app:${NC}"
echo "databricks apps logs $APP_NAME --profile $PROFILE --follow"
echo ""
echo -e "${YELLOW}To check app status:${NC}"
echo "databricks apps get $APP_NAME --profile $PROFILE"
echo ""
echo -e "${YELLOW}To redeploy after changes:${NC}"
echo "./deploy_dab_generator.sh $PROFILE"