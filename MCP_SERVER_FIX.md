# MCP Server Fix for Databricks Apps Integration

## Problem
The Databricks App client (`src/api/app.py`) was unable to find MCP tools when connecting to the MCP server. The error was:
```
<tool_use_error>Error: No such tool available: mcp__databricks-mcp__list_jobs</tool_use_error>
```

## Root Cause
Mounting a FastMCP Starlette app inside FastAPI causes routing issues. The streamable HTTP transport doesn't work correctly when the MCP app is mounted at a subpath (e.g., `/mcp`).

## Solution
Run the MCP server directly without the FastAPI wrapper, using only the FastMCP streamable HTTP transport.

## Implementation Steps

### 1. Backup Current Server File
```bash
cd mcp/server
cp app.py old_app.py
```

### 2. Replace app.py with Simplified Version
```bash
cp app_simple.py app.py
```

The new `app.py` should:
- Run the MCP server directly using `mcp_server.http_app(transport='streamable-http')`
- Serve at the root path without FastAPI wrapper
- Include all 18 tools from `tools.py`, `tools_dab.py`, and `tools_workspace.py`

### 3. Update Databricks Apps Deployment Configuration
File: `mcp/app.yaml`
```yaml
# Change from:
command: ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]

# To:
command: ["python", "server/app.py"]
```

### 4. Update Client Configuration
File: `src/api/claude_client.py`
```python
# Change from:
"url": f"{mcp_server_url}/mcp",

# To:
"url": mcp_server_url,  # Direct connection to root
```

## Key Changes Summary

### Server Side (mcp/server/)
- **Old**: FastAPI app with MCP mounted at `/mcp` using `app.mount()`
- **New**: Direct MCP server running at root using streamable HTTP

### Client Side (src/api/)
- **Old**: Connecting to `{server_url}/mcp`
- **New**: Connecting to `{server_url}` directly

## Technical Details

### Why This Works
1. **Direct Transport**: FastMCP's `http_app()` creates a Starlette app with streamable HTTP transport
2. **No Path Conflicts**: Running directly eliminates FastAPI's path routing issues
3. **Proper Tool Discovery**: Claude SDK can properly discover tools when connecting to the root path

### What Gets Fixed
- ✅ All 18 MCP tools are accessible
- ✅ Correct naming convention (`mcp__databricks-mcp__*`)
- ✅ OAuth authentication works in Databricks Apps
- ✅ Streamable HTTP transport functions correctly

## Deployment Instructions

### Step 1: Apply Server Fixes
```bash
# Navigate to MCP server directory
cd mcp/server

# Backup current app.py
cp app.py old_app.py

# Replace with simplified version
cp app_simple.py app.py
```

### Step 2: Update MCP App Configuration
```bash
# Navigate to MCP root
cd mcp

# Edit app.yaml to use the new server
# Change from: command: ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]
# To: command: ["python", "server/app.py"]
```

### Step 3: Deploy MCP Server to Databricks Apps
```bash
# From the mcp directory
./scripts/deploy.sh

# This will:
# 1. Load environment variables from .env
# 2. Deploy to Databricks Apps using profile (default: aws-apps)
# 3. Test the deployment
# 4. Show the app URL
```

### Step 4: Deploy DAB Generator Streamlit App
```bash
# Navigate to Streamlit app directory
cd src/api

# Deploy using the deployment script
./deploy_dab_generator.sh [profile]

# This will:
# 1. Validate configuration files
# 2. Set up Claude API key secret
# 3. Sync code to workspace
# 4. Deploy to Databricks Apps
```

### Step 5: Verify Deployments

#### Test MCP Server
```bash
# Get OAuth token
TOKEN=$(databricks auth token --profile aws-apps | jq -r .access_token)

# Test health endpoint
curl -H "Authorization: Bearer $TOKEN" \
  https://databricks-mcp-server-1444828305810485.aws.databricksapps.com/health

# Expected: {"status": "healthy", "tools_count": 18, ...}
```

#### Test DAB Generator App
```bash
# Check app status
databricks apps get dab-generator --profile aws-apps

# View logs
databricks apps logs dab-generator --profile aws-apps --follow
```

### Local Testing (Before Deployment)
```bash
# Test MCP server locally
cd mcp/server
python app.py

# In another terminal, test Streamlit app
cd src/api
streamlit run app.py

# Test connection
curl http://localhost:8000/health
```

## Verification

### Test MCP Tools Discovery
Create a test script to verify tools are accessible:
```python
from claude_code_sdk import ClaudeCodeOptions, ClaudeSDKClient

options = ClaudeCodeOptions(
    mcp_servers={
        "databricks-mcp": {
            "type": "http",
            "url": "http://localhost:8000",
            "headers": {}
        }
    },
    allowed_tools=["mcp__databricks-mcp__*"]
)

# Should successfully find all 18 tools
```

### Expected Tools (18 total)
- Core: `health`, `list_jobs`, `get_job`, `run_job`, `list_notebooks`, `export_notebook`, `execute_dbsql`, `list_warehouses`, `list_dbfs_files`, `generate_bundle_from_job`, `get_cluster`
- DAB: `analyze_notebook`, `generate_bundle`, `validate_bundle`, `create_tests`
- Workspace: `upload_bundle`, `run_bundle_command`, `sync_workspace_to_local`

## Troubleshooting

### Common Issues

#### 1. MCP Tools Not Found
```bash
# Symptom: "No such tool available: mcp__databricks-mcp__list_jobs"
# Cause: MCP server routing issues or incorrect URL

# Check MCP server is running
curl -H "Authorization: Bearer $TOKEN" https://databricks-mcp-server-1444828305810485.aws.databricksapps.com/health

# Should return: {"status": "healthy", "tools_count": 18, ...}
```

#### 2. Authentication Errors
```bash
# Symptom: 302 redirects or authentication errors
# Solution: Ensure OAuth token is properly forwarded

# Test token validity
databricks auth token --profile aws-apps

# Check app logs
databricks apps logs dab-generator --profile aws-apps --tail 50
```

#### 3. App Deployment Failures
```bash
# Check app status
databricks apps get [app-name] --profile aws-apps

# View deployment logs
databricks apps logs [app-name] --profile aws-apps

# Redeploy if needed
cd mcp && ./scripts/deploy.sh
cd src/api && ./deploy_dab_generator.sh
```

### Monitoring Commands

#### Check Both Apps Status
```bash
# MCP Server
databricks apps get databricks-mcp-server --profile aws-apps

# DAB Generator
databricks apps get dab-generator --profile aws-apps
```

#### View Live Logs
```bash
# MCP Server logs
databricks apps logs databricks-mcp-server --profile aws-apps --follow

# DAB Generator logs
databricks apps logs dab-generator --profile aws-apps --follow
```

## Notes
- The old `app.py` is preserved as `old_app.py` for reference
- The simplified server (`app_simple.py`) becomes the new `app.py`
- No changes needed to the MCP tools themselves
- OAuth headers are properly passed through when deployed
- Both deployment scripts handle environment variables and secrets automatically
- The MCP server runs at root path, Streamlit app connects directly