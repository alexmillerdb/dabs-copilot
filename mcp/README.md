# Databricks MCP Server

A production-ready Model Context Protocol (MCP) server for Databricks workspace operations and DAB generation. Provides 15 tools for managing jobs, notebooks, SQL queries, and generating Databricks Asset Bundles.

## 🚀 Quick Start

### Prerequisites
1. **Databricks CLI configured**:
   ```bash
   databricks configure --profile aws-apps
   ```

2. **Environment variables** (.env file):
   ```bash
   DATABRICKS_CONFIG_PROFILE=aws-apps
   DATABRICKS_HOST=https://your-workspace.cloud.databricks.com/
   DATABRICKS_SERVERLESS_COMPUTE_ID=auto  # Optional for serverless
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Server

#### Option 1: Claude Code CLI Integration
```bash
# Start MCP server
cd mcp/server
python main.py

# Register with Claude (one-time)
claude mcp add --scope user databricks-mcp python /path/to/mcp/server/main.py
```

#### Option 2: Databricks Apps (Deployed) ✅
```bash
# Deploy to Databricks Apps
cd mcp && ./scripts/deploy.sh

# Access deployed server
URL: https://databricks-mcp-server-1444828305810485.aws.databricksapps.com
```

#### Option 3: Local FastAPI Server
```bash
cd mcp/server
python app.py  # Runs on http://localhost:8000
```

## 🛠️ Available Tools (15 Total)

### Core Workspace Tools (9)
| Tool | Description |
|------|-------------|
| `health` | Check server and Databricks connection |
| `list_jobs` | List workspace jobs with filtering |
| `get_job` | Get detailed job configuration |
| `run_job` | Execute jobs with parameters |
| `list_notebooks` | Browse workspace notebooks |
| `export_notebook` | Export notebooks (SOURCE, HTML, JUPYTER, DBC) |
| `execute_dbsql` | Execute SQL queries |
| `list_warehouses` | List SQL warehouses |
| `list_dbfs_files` | Browse DBFS |

### DAB Generation Tools (6)
| Tool | Description |
|------|-------------|
| `analyze_notebook` | Deep analysis for dependencies and patterns |
| `generate_bundle` | Create DAB configurations |
| `generate_bundle_from_job` | Generate DAB from existing jobs |
| `validate_bundle` | Validate bundle configurations |
| `create_tests` | Generate test scaffolds |
| `get_cluster` | Get cluster configurations |

## 📦 DAB Generation Examples

### Generate from Existing Job
```bash
# Via Claude
"List my Databricks jobs"
"Generate a bundle from job ID 123"

# Direct tool call
await mcp.call_tool("generate_bundle_from_job", {"job_id": 123})
```

### Generate from Notebook Analysis
```bash
# Via Claude
"Analyze notebook at /Users/example/etl_pipeline.py"
"Generate a DAB from the analysis"

# Direct tool call
await mcp.call_tool("analyze_notebook", {
    "notebook_path": "/Users/example/etl.py",
    "include_dependencies": true,
    "detect_patterns": true
})
```

### Example DAB Output
```yaml
bundle:
  name: etl-pipeline
  
resources:
  jobs:
    etl_job:
      tasks:
        - task_key: extract
        - task_key: transform
        - task_key: load
      
targets:
  dev:
    mode: development
  prod:
    mode: production
```

## 🔧 Configuration

### Project Structure
```
mcp/
├── server/
│   ├── main.py          # Claude Code CLI entry
│   ├── app.py           # FastAPI server
│   ├── tools.py         # Core tools
│   └── tools_dab.py     # DAB tools
├── scripts/
│   └── deploy.sh        # Deployment script
└── requirements.txt     # Dependencies
```

### Key Configuration Files
- **app.yaml** - Databricks Apps entry point
- **config.yaml** - Server configuration
- **.env** - Environment variables

## 🧪 Testing

### Test All Tools
```bash
cd mcp/tests
python test_tools.py
```

### Test Deployed Server
```bash
# Get auth token
TOKEN=$(databricks auth token --profile aws-apps | jq -r .access_token)

# Test endpoints
curl -H "Authorization: Bearer $TOKEN" \
     https://databricks-mcp-server-1444828305810485.aws.databricksapps.com/health

curl -H "Authorization: Bearer $TOKEN" \
     https://databricks-mcp-server-1444828305810485.aws.databricksapps.com/mcp-info
```

## 📊 Response Format

All tools return standardized JSON:
```json
{
  "success": true,
  "data": {
    // Tool-specific data
  },
  "timestamp": "2025-09-11T03:38:00Z"
}
```

## 🚢 Deployment to Databricks Apps

The server is deployed and accessible at:
- **URL**: https://databricks-mcp-server-1444828305810485.aws.databricksapps.com
- **Health**: `/health`
- **MCP Info**: `/mcp-info`
- **MCP Endpoint**: `/mcp-server/mcp`

### Authentication
All endpoints require OAuth authentication:
```bash
databricks auth token --profile aws-apps
```

### Logs
View logs at: https://databricks-mcp-server-1444828305810485.aws.databricksapps.com/logz

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| "Databricks client not initialized" | Check `~/.databrickscfg` and `DATABRICKS_CONFIG_PROFILE` |
| "No warehouse ID provided" | Set `DATABRICKS_WAREHOUSE_ID` or use `DATABRICKS_SERVERLESS_COMPUTE_ID=auto` |
| FastMCP import error | Ensure `pip install -r requirements.txt` completed |
| Authentication required | Use `databricks auth token` for Bearer token |

## 📈 Status

- ✅ **15 tools operational** across 2 phases
- ✅ **Deployed to Databricks Apps** with OAuth
- ✅ **Claude Code CLI integrated**
- ✅ **Sub-3 second response times**
- ✅ **Production-ready** with error handling

## 🤝 Contributing

Follow these patterns:
- Standardized JSON responses
- Profile-based authentication
- Environment-based configuration
- Comprehensive error handling

For detailed implementation guide, see [CLAUDE.md](./CLAUDE.md)