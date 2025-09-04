# Databricks MCP Server

A Model Context Protocol (MCP) server for Databricks workspace operations and Databricks Asset Bundle (DAB) generation. This server provides tools for analyzing notebooks, managing jobs, executing SQL queries, and generating production-ready DABs.

## 🏗️ Code Structure

```
mcp/
├── README.md                    # This file
├── server/                      # MCP server implementation
│   ├── main.py                 # MCP server entry point
│   ├── tools.py                # MCP tool definitions (9 tools)
│   ├── app.py                  # FastAPI + FastMCP hybrid app
│   ├── config.yaml             # Server configuration
│   ├── services/               # Business logic layer
│   │   ├── __init__.py
│   │   └── databricks_service.py
│   └── config/                 # Configuration management
│       ├── __init__.py
│       └── loader.py
├── tests/                       # Test suite
│   ├── __init__.py
│   └── test_tools.py           # Tool testing script
├── IMPLEMENTATION_PLAN.md       # 3-phase implementation roadmap
├── ARCHITECTURE_DESIGN.md       # Detailed system architecture
├── TOOLS_SPECIFICATION.md       # Complete tool specifications
├── CONFIG_ERROR_HANDLING.md     # Configuration and error handling
└── IMPLEMENTATION_SUMMARY.md    # Planning phase summary
```

## 🛠️ Available MCP Tools

The server provides 9 MCP tools for Databricks operations:

### Core Workspace Tools
- **`health`** - Check server and Databricks connection status
- **`list_jobs`** - List workspace jobs with filtering options
- **`get_job`** - Get detailed job configuration and task information
- **`run_job`** - Execute jobs with parameter support
- **`list_notebooks`** - Browse notebooks in workspace paths
- **`export_notebook`** - Export notebooks in various formats (SOURCE, HTML, JUPYTER, DBC)

### SQL & Data Tools
- **`execute_dbsql`** - Execute SQL queries on Databricks SQL warehouses
- **`list_warehouses`** - List available SQL warehouses
- **`list_dbfs_files`** - Browse Databricks File System (DBFS)

## 🚀 Quick Start

### Prerequisites

1. **Databricks Configuration**: Ensure you have Databricks CLI configured with a profile:
   ```bash
   databricks configure --profile aws-apps
   ```

2. **Environment Variables**: The server uses your existing `.env` file with:
   ```bash
   DATABRICKS_CONFIG_PROFILE=aws-apps
   DATABRICKS_HOST=https://your-workspace.cloud.databricks.com/
   ```

3. **Dependencies**: Install from the root requirements.txt:
   ```bash
   cd /Users/alex.miller/Documents/GitHub/dabs-copilot
   pip install -r requirements.txt
   ```

### Running the MCP Server

#### Option 1: Direct MCP Server (for Claude Code CLI)
```bash
cd mcp/server
python main.py
```

This starts the MCP server in stdio mode, perfect for connecting with Claude Code CLI.

#### Option 2: FastAPI + MCP Hybrid Server
```bash
cd mcp/server
python app.py
```

This starts both FastAPI (port 8000) and MCP server for web UI integration.

### Testing the Server

Run the test suite to verify all tools work:

```bash
cd mcp/tests
python test_tools.py
```

Expected output:
```
Testing Databricks MCP tools...
Testing health tool...
Health result: {"success": true, "data": {"server_status": "healthy", ...}}

Testing list_jobs tool...
List jobs result: {"success": true, "data": {"jobs": [...], "count": 5}}

Testing list_notebooks tool...
List notebooks result: {"success": true, "data": {"notebooks": [], "count": 0}}

✅ All tests completed!
```

## 🔧 Configuration

### Server Configuration (`config.yaml`)

The server uses a YAML configuration file with environment variable substitution:

```yaml
servername: "databricks-mcp-server"
server:
  host: "localhost"
  port: 8000
  debug: false

databricks:
  host: "${DATABRICKS_HOST}"
  token: "${DATABRICKS_TOKEN}"
  warehouse_id: "${DATABRICKS_WAREHOUSE_ID}"

tools:
  enabled:
    - health
    - list_jobs
    - get_job
    # ... all 9 tools
```

### Environment Variables

The server automatically detects and uses these environment variables:

```bash
# Databricks connection (from your existing .env)
DATABRICKS_CONFIG_PROFILE=aws-apps
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com/
DATABRICKS_SERVERLESS_COMPUTE_ID=auto

# Optional overrides
DATABRICKS_TOKEN=your-token          # If not using profile
DATABRICKS_WAREHOUSE_ID=your-warehouse-id
ENVIRONMENT=development              # dev, staging, prod
```

## 🧪 Testing Individual Tools

You can test specific tools directly:

```python
import asyncio
from tools import mcp

async def test_health():
    result = await mcp.call_tool("health", {})
    print(result)

async def test_list_jobs():
    result = await mcp.call_tool("list_jobs", {"limit": 3})
    print(result)

# Run tests
asyncio.run(test_health())
asyncio.run(test_list_jobs())
```

## 📊 Tool Response Format

All tools return standardized JSON responses:

```json
{
  "success": true,
  "data": {
    // Tool-specific data
  },
  "timestamp": "2025-09-03T21:23:15.495658"
}
```

Error responses:
```json
{
  "success": false,
  "error": "Error description",
  "timestamp": "2025-09-03T21:23:15.495658"
}
```

## 🔄 Integration with Claude Code CLI

To connect the MCP server with Claude Code CLI:

1. **Start the MCP server:**
   ```bash
   cd mcp/server
   python main.py
   ```

2. **Connect Claude Code CLI** (in another terminal):
   ```bash
   claude-code-cli connect stdio://path/to/mcp/server/main.py
   ```

3. **Test tools via Claude:**
   ```
   "Check the health of my Databricks connection"
   "List the first 5 jobs in my workspace"
   "Export the notebook at /Users/alex.miller/example.py"
   ```

## 🚧 Development Status

### ✅ Phase 1 Complete (Week 2)
- [x] Hybrid FastAPI + FastMCP architecture
- [x] 9 core tools implemented with error handling
- [x] YAML configuration system
- [x] Service layer abstraction
- [x] Databricks SDK integration with profile support
- [x] Comprehensive testing suite

### 🔜 Phase 2 (Week 2-3) - DAB Generation
- [ ] `analyze_notebook` - Deep notebook analysis
- [ ] `generate_bundle` - Create DAB configurations
- [ ] `validate_bundle` - Bundle validation
- [ ] `create_tests` - Test scaffold generation

### 🔮 Phase 3 (Week 3-4) - Production Features
- [ ] FastAPI routes for web UI
- [ ] Authentication and security
- [ ] Real-time features (WebSocket)
- [ ] Production deployment configuration

## 📚 Documentation

- **[IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md)** - Complete 3-phase roadmap
- **[ARCHITECTURE_DESIGN.md](./ARCHITECTURE_DESIGN.md)** - System architecture details
- **[TOOLS_SPECIFICATION.md](./TOOLS_SPECIFICATION.md)** - All 20+ planned tools
- **[CONFIG_ERROR_HANDLING.md](./CONFIG_ERROR_HANDLING.md)** - Configuration patterns

## 🐛 Troubleshooting

### Common Issues

1. **"Databricks client not initialized"**
   - Check your `~/.databrickscfg` profile configuration
   - Verify `DATABRICKS_CONFIG_PROFILE` environment variable

2. **"No warehouse ID provided"**
   - Set `DATABRICKS_WAREHOUSE_ID` environment variable
   - Or use `DATABRICKS_SERVERLESS_COMPUTE_ID=auto` for serverless

3. **Import errors**
   - Run `pip install -r requirements.txt` from project root
   - Ensure you're in the correct virtual environment

### Debug Mode

Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
cd mcp/server
python main.py
```

## 🤝 Contributing

The MCP server follows these development patterns:
- **Simple, clean code** following the reference implementation
- **Standardized error handling** with success/error response format
- **Environment-based configuration** for flexible deployment
- **Comprehensive testing** before adding new features

Next steps: Ready for Phase 2 DAB generation tools or integration with Claude Code CLI!