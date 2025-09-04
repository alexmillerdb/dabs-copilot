# Databricks Apps Deployment Plan

## 📋 Current Status & Implementation Roadmap

This document outlines the complete plan to extend your working MCP server to support both local development with Claude Code CLI and production deployment on Databricks Apps.

## ✅ Current Working Implementation

### **Local MCP Server (Complete)**
- **9 operational MCP tools** with live Databricks integration
- **Two running modes**:
  - `main.py` - stdio mode for Claude Code CLI ✅
  - `app.py` - FastAPI + MCP hybrid for web UI ✅
- **Configuration system** with YAML + environment variables ✅
- **Authentication** via Databricks CLI profiles ✅
- **Testing suite** with live workspace validation ✅
- **Service layer architecture** ✅

### **Claude Code CLI Integration (Working)**
- Successfully connects via: `claude mcp add --scope user databricks-mcp python mcp/server/main.py` ✅
- All 9 tools available through Claude conversations ✅

### **Current Tools Available**
1. `health` - Server and Databricks connection status
2. `list_jobs` - Workspace jobs with filtering
3. `get_job` - Detailed job configuration
4. `run_job` - Execute jobs with parameters
5. `list_notebooks` - Browse workspace notebooks
6. `export_notebook` - Export in multiple formats
7. `execute_dbsql` - SQL queries on warehouses
8. `list_warehouses` - List available SQL warehouses
9. `list_dbfs_files` - Browse Databricks File System

## ❌ Missing for Databricks Apps Deployment

### **Critical Missing Components**
1. **`app.yaml`** - Databricks Apps entry point specification
2. **Production FastAPI configuration** - Host binding and security
3. **Databricks Apps authentication** - OAuth token handling
4. **Deployment automation** - Scripts for sync and deploy
5. **Environment separation** - Dev vs production configs

## 🎯 Implementation Plan

### **Phase 1: Core Databricks Apps Support**

#### **1.1 Create `app.yaml` (Critical)**
**Location**: `/Users/alex.miller/Documents/GitHub/dabs-copilot/mcp/app.yaml`

```yaml
# Databricks Apps entry point configuration
command: ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### **1.2 Update `server/app.py` for Production**
**Changes needed**:

```python
# Production host configuration
host = os.getenv("SERVER_HOST", "0.0.0.0")  # Changed from localhost

# Enhanced CORS for Databricks Apps
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",        # Local React dev
        "http://localhost:5173",        # Local Vite dev
        "https://*.databricks.com",     # Databricks workspace
        "https://*.databricksapps.com", # Databricks Apps domain
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount MCP at root for Databricks Apps compatibility
app.mount('/', mcp_asgi_app)  # Change from '/mcp'

# Add production-ready settings
if os.getenv("ENVIRONMENT") == "production":
    # Disable reload, debug mode
    reload = False
    debug = False
```

#### **1.3 Create Deployment Scripts**
**Location**: `/Users/alex.miller/Documents/GitHub/dabs-copilot/mcp/scripts/`

**`deploy.sh`**:
```bash
#!/bin/bash
# Automated deployment to Databricks Apps

set -e

APP_NAME="databricks-mcp-server"
DATABRICKS_USERNAME=$(databricks current-user me | jq -r .userName)
SOURCE_PATH="/Users/$DATABRICKS_USERNAME/$APP_NAME"

echo "🚀 Deploying MCP Server to Databricks Apps..."

# Create app if it doesn't exist
if ! databricks apps get "$APP_NAME" >/dev/null 2>&1; then
    echo "📱 Creating new Databricks app..."
    databricks apps create "$APP_NAME"
fi

# Sync code to workspace
echo "📁 Syncing code to workspace..."
databricks sync . "$SOURCE_PATH"

# Deploy app
echo "🔧 Deploying app..."
databricks apps deploy "$APP_NAME" --source-code-path "/Workspace$SOURCE_PATH"

# Get app URL
APP_URL=$(databricks apps get "$APP_NAME" | jq -r .url)
echo "✅ Deployment complete!"
echo "🌐 App URL: $APP_URL"
echo "🔗 MCP Endpoint: $APP_URL/mcp/"
```

**`test-deployment.sh`**:
```bash
#!/bin/bash
# Test deployed MCP server

APP_NAME="databricks-mcp-server"
APP_URL=$(databricks apps get "$APP_NAME" | jq -r .url)

echo "🧪 Testing deployed MCP server..."
echo "📍 URL: $APP_URL"

# Test health endpoint
curl -s "$APP_URL/health" | jq .

# Test MCP info endpoint
curl -s "$APP_URL/mcp-info" | jq .

echo "✅ Basic connectivity test complete"
```

#### **1.4 Environment Configuration Updates**

**Update `server/config.yaml`**:
```yaml
# Add production overrides
server:
  title: "Databricks MCP Server"
  host: "${SERVER_HOST:-0.0.0.0}"     # Production-ready default
  port: "${SERVER_PORT:-8000}"
  debug: "${DEBUG:-false}"
  reload: "${RELOAD:-false}"           # Disable in production

# Databricks Apps specific settings
databricks_apps:
  enabled: "${DATABRICKS_APPS_MODE:-false}"
  oauth_required: "${OAUTH_REQUIRED:-true}"

cors:
  enabled: true
  origins:
    - "https://*.databricks.com"
    - "https://*.databricksapps.com"   # Add Databricks Apps domain
    - "${CORS_ORIGINS}"                # Environment override
```

### **Phase 2: Authentication & Security**

#### **2.1 Databricks Apps OAuth Support**
**Add to `server/app.py`**:

```python
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_databricks_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify Databricks OAuth token for Apps deployment"""
    if os.getenv("DATABRICKS_APPS_MODE") == "true":
        # In Databricks Apps, verify the bearer token
        token = credentials.credentials
        # Add token validation logic here
        return token
    return None  # Skip auth for local development

# Add auth dependency to sensitive endpoints
@app.get("/mcp-info")
async def mcp_info(token: str = Depends(verify_databricks_token)):
    # ... existing implementation
```

#### **2.2 Environment Detection**
```python
def is_databricks_apps_environment():
    """Detect if running in Databricks Apps"""
    return os.getenv("DATABRICKS_RUNTIME_VERSION") is not None

def configure_for_environment():
    """Configure server based on deployment environment"""
    if is_databricks_apps_environment():
        os.environ["ENVIRONMENT"] = "production"
        os.environ["SERVER_HOST"] = "0.0.0.0"
        os.environ["RELOAD"] = "false"
```

### **Phase 3: Testing & Validation**

#### **3.1 Local Testing (Current)**
```bash
# Test locally with Claude Code CLI
cd mcp/tests && python test_tools.py
claude mcp add --scope user databricks-mcp python mcp/server/main.py
```

#### **3.2 Databricks Apps Testing**
```bash
# Deploy and test
cd mcp && chmod +x scripts/deploy.sh
./scripts/deploy.sh
./scripts/test-deployment.sh
```

#### **3.3 Integration Testing**
```python
# Test MCP server via HTTP (Databricks Apps mode)
import httpx
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def test_databricks_apps_mcp():
    app_url = "https://your-app-url.databricksapps.com/"
    
    async with streamablehttp_client(app_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            tools = await session.list_tools()
            print(f"Available tools: {[tool.name for tool in tools.tools]}")
```

## 📂 File Structure After Implementation

```
mcp/
├── README.md                           # User documentation ✅
├── CLAUDE.md                          # Implementation guide ✅
├── DATABRICKS_APPS_DEPLOYMENT.md      # This file - deployment plan
├── app.yaml                           # ✅ Databricks Apps entry point
├── requirements.txt                   # ✅ MCP app dependencies (runtime only)
├── .env.example                       # ✅ Environment variables template
├── test_local_mcp.py                  # ✅ Local testing script with multiple modes
├── server/                            # MCP server implementation ✅
│   ├── main.py                        # Claude CLI stdio mode ✅
│   ├── app.py                         # ✅ FastAPI hybrid (production-ready)
│   ├── tools.py                       # 9 MCP tools ✅
│   ├── config.yaml                    # Configuration ✅
│   ├── services/                      # Business logic ✅
│   └── config/                        # Config management ✅
├── scripts/                           # ✅ Deployment automation
│   ├── deploy.sh                      # ✅ Deploy to Databricks Apps (enhanced with .env)
│   ├── databricks_apps_utils.py       # Portable CLI utilities
│   ├── setup_cli.sh                   # CLI installation script
│   ├── quick_test.py                  # Quick deployment test
│   └── test_databricks_apps.py        # Comprehensive testing
└── tests/                             # Test suite ✅
    └── test_tools.py                  # Local testing ✅
```

## 🚀 Implementation Checklist

### **✅ Completed Tasks**
- [x] Create `app.yaml` with uvicorn command
- [x] Create `mcp/requirements.txt` with runtime dependencies only
- [x] Update `app.py` host configuration (`0.0.0.0`)
- [x] Add Databricks Apps CORS origins
- [x] Create deployment scripts directory
- [x] Write `deploy.sh` automation script
- [x] Write comprehensive testing scripts
- [x] **Make CLI usage portable** - No hardcoded paths!
- [x] Add portable CLI detection function
- [x] Update project requirements.txt with proper dependencies
- [x] **Enhanced deploy.sh with .env file support** - Loads environment variables
- [x] **Remove conflicting databricks-cli from venv** - Clean CLI setup
- [x] **Create local testing infrastructure** - `test_local_mcp.py`
- [x] **Validate local MCP tools functionality** - All 9 tools tested and working
- [x] **STDIO mode testing** - Claude Desktop compatible mode verified
- [x] **Virtual environment setup** - Proper activation and dependency management

### **Configuration Updates**
- [ ] Update `config.yaml` with production defaults
- [ ] Add environment detection logic
- [ ] Configure MCP endpoint routing for Apps
- [ ] Add OAuth token handling (optional)

### **Testing & Validation**
- [x] **Test local development** - All MCP tools working with Databricks connection
- [x] **Validate MCP tools work locally** - Health, jobs, notebooks, warehouses tested
- [x] **Local STDIO mode testing** - Ready for Claude Desktop integration
- [ ] Test Databricks Apps deployment
- [ ] Validate MCP tools work in cloud environment
- [x] **Document local testing procedures** - Created comprehensive testing guide

## 🎯 Success Criteria

### **Local Development**
- ✅ Claude Code CLI integration continues to work
- ✅ All 9 tools operational via `python main.py`
- ✅ FastAPI dev server works via `python app.py`

### **Databricks Apps Deployment**
- [ ] Successful deployment via `databricks apps deploy`
- [ ] MCP server accessible at `https://app-url.databricksapps.com/`
- [ ] All 9 tools operational in cloud environment
- [ ] Health check and MCP info endpoints working

### **Dual Environment Support**
- [ ] Single codebase supports both local and cloud deployment
- [ ] Environment-specific configuration handling
- [ ] Automated deployment and testing scripts
- [ ] Clear documentation for both use cases

## 📚 Implementation Steps

### **Step 1: Setup Databricks CLI (Required)**
```bash
# Option 1: Run the setup script (recommended)
cd mcp && ./scripts/setup_cli.sh

# Option 2: Manual installation
# macOS with Homebrew:
brew install databricks/tap/databricks

# Or use curl installer:
curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh
```

### **Step 2: Configure Authentication**
```bash
# Configure your profile
databricks auth login --host https://your-workspace.cloud.databricks.com --profile aws-apps

# Verify authentication
databricks current-user me --profile aws-apps
```

### **Step 3: Deploy to Databricks Apps**
```bash
# Deploy with the portable script
cd mcp && ./scripts/deploy.sh

# Test the deployment
python scripts/quick_test.py
```

### **Step 4: Verify Both Environments Work**
```bash
# Test local Claude Code CLI (should still work)
claude mcp list

# Test Databricks Apps deployment
python scripts/test_databricks_apps.py --test-type comprehensive
```

## 🔍 Key Considerations

### **Backward Compatibility**
- Local development with Claude Code CLI must continue working
- Existing tool functionality should remain unchanged
- Configuration should gracefully handle both environments

### **Security & Authentication**
- Databricks Apps will provide OAuth tokens automatically
- Local development continues using CLI profiles
- Environment detection determines authentication method

### **Deployment Automation**
- Single command deployment to Databricks Apps
- Automated testing and validation scripts
- Clear rollback procedures if deployment fails

### **Monitoring & Debugging**
- Health check endpoints for both environments
- Comprehensive logging for troubleshooting
- Clear error messages for configuration issues

## 📞 Support & Troubleshooting

### **Common Issues**
1. **Host binding errors**: Ensure `SERVER_HOST=0.0.0.0` for Databricks Apps
2. **CORS issues**: Add `*.databricksapps.com` to allowed origins
3. **Authentication failures**: Verify OAuth token handling in Apps environment
4. **Tool failures**: Check Databricks client initialization in cloud environment

### **Debug Commands**
```bash
# Test local server
cd mcp/server && python app.py

# Test deployed server
curl -s https://your-app-url.databricksapps.com/health

# Check app logs
databricks apps logs databricks-mcp-server
```

This plan maintains your current working local setup while adding full Databricks Apps deployment capability with minimal changes to your existing architecture.

## 🎯 Recent Accomplishments (Latest Session)

### **✅ Environment & CLI Setup**
- **Resolved databricks-cli conflicts** - Removed v0.18.0 from venv, using local v0.245.0
- **Enhanced deploy.sh script** - Now supports .env file loading for flexible configuration
- **Created .env.example template** - Shows required environment variables format

### **✅ Local Testing Infrastructure** 
- **Created `test_local_mcp.py`** - Comprehensive local testing script with multiple modes:
  - `python test_local_mcp.py test` - Quick tool validation
  - `python test_local_mcp.py stdio` - STDIO mode for Claude Desktop
  - `python test_local_mcp.py help` - Usage documentation
- **Validated all 9 MCP tools** - Health, jobs, notebooks, warehouses all working
- **Confirmed Databricks connectivity** - Successfully connected to workspace
- **Virtual environment setup** - Proper activation and dependency management

### **✅ Configuration Improvements**
- **Profile flexibility** - deploy.sh now uses `DATABRICKS_CONFIG_PROFILE` from .env
- **Host detection** - Shows which Databricks host is being used
- **Environment variable support** - Full .env integration for deployment settings

### **🎯 Ready for Next Phase**
The local development environment is now fully validated and ready. Next steps:
1. **Test Databricks Apps deployment** - Use the enhanced `./scripts/deploy.sh`
2. **Validate cloud environment** - Ensure all tools work in Databricks Apps
3. **Complete dual-environment testing** - Verify both local and cloud work seamlessly
