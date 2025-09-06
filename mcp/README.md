# Databricks MCP Server

A Model Context Protocol (MCP) server for Databricks workspace operations and Databricks Asset Bundle (DAB) generation. This server provides tools for analyzing notebooks, managing jobs, executing SQL queries, and generating production-ready DABs.

## 🏗️ Code Structure

```
mcp/
├── README.md                    # This file
├── server/                      # MCP server implementation
│   ├── main.py                 # MCP server entry point
│   ├── tools.py                # Phase 1: Core MCP tools (9 tools)
│   ├── tools_dab.py            # Phase 2: DAB generation tools (4 tools)
│   ├── app.py                  # FastAPI + FastMCP hybrid app
│   ├── config.yaml             # Server configuration
│   ├── services/               # Business logic layer
│   │   ├── __init__.py
│   │   ├── databricks_service.py
│   │   └── analysis_service.py # Notebook analysis service
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

The server provides **14 MCP tools** for Databricks operations and DAB generation:

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

### DAB Generation Tools (Phase 2)
- **`generate_bundle_from_job`** ✅ - Generate DAB from existing jobs using native Databricks CLI
- **`analyze_notebook`** ✅ - Deep notebook analysis for dependencies, data sources, and patterns
- **`generate_bundle`** 📅 - Create complete DAB configurations from analysis results
- **`validate_bundle`** 📅 - Validate generated bundle configurations and best practices
- **`create_tests`** 📅 - Generate unit test scaffolds for bundle resources

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

### Testing the analyze_notebook Tool

Test the new DAB generation functionality:

```python
import asyncio
from tools import mcp

async def test_notebook_analysis():
    result = await mcp.call_tool("analyze_notebook", {
        "notebook_path": "/Users/example/etl_pipeline.py",
        "include_dependencies": True,
        "include_data_sources": True,
        "detect_patterns": True
    })
    print(result)

asyncio.run(test_notebook_analysis())
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

1. **Add the MCP server to Claude:**
   ```bash
   claude mcp add --scope user databricks-mcp python mcp/server/main.py
   ```

2. **Test tools via Claude:**
   ```
   "Check the health of my Databricks connection"
   "List the first 5 jobs in my workspace"
   "Export the notebook at /Users/alex.miller/example.py"
   ```

3. **Generate DABs from existing jobs:**
   ```
   "List my jobs"
   "Generate a bundle from job ID 456"
   "Create a DAB from the ETL pipeline job"
   ```

4. **Analyze notebooks for DAB generation:**
   ```
   "Analyze the notebook at /Users/alex.miller/etl_pipeline.py and extract dependencies"
   "What patterns does the notebook at /Users/example.py follow?"
   "Generate a DAB from the analyzed notebook"
   ```

The MCP server will automatically start when Claude needs to use the tools.

## 📦 DAB Generation Example

The MCP server can analyze exported notebooks and generate comprehensive Databricks Asset Bundles (DABs). Here's how:

### Quick Start for DAB Generation

#### Method 1: Generate from Existing Jobs (Recommended)

1. **List your existing jobs:**
   ```
   "List my Databricks jobs"
   ```

2. **Generate a DAB from an existing job:**
   ```
   "Generate a bundle from job ID 123"
   ```
   
   This uses the native Databricks CLI command `databricks bundle generate job --existing-job-id <job_id>` to create a production-ready bundle.

#### Method 2: Generate from Notebook Analysis

1. **Export a notebook using MCP tools:**
   ```python
   # Via Claude: "Export notebook at /path/to/your/notebook"
   # Or directly with the tool:
   await mcp.call_tool("export_notebook", {
     "path": "/Users/alex.miller@databricks.com/genai-business-agent/agents/driver",
     "format": "SOURCE"
   })
   ```

2. **Analyze the notebook:**
   ```
   "Analyze the notebook at /Users/alex.miller/etl_pipeline.py"
   ```

3. **Generate a DAB from the analysis:**
   Claude will create a complete bundle configuration including:
   - Job definitions with task dependencies
   - Cluster configurations
   - Unity Catalog resources (models, functions, schemas)
   - Environment-specific settings (dev, staging, prod)
   - Schedule configurations
   - Permission management

### Example Generated DAB Structure

```yaml
bundle:
  name: genai-business-agent
  description: Tool-calling agent for analyzing GenAI consumption patterns

resources:
  jobs:
    genai_agent_deployment:
      tasks:
        - task_key: setup_environment
        - task_key: create_uc_tools
        - task_key: train_agent
        - task_key: evaluate_agent
        - task_key: deploy_agent
      
  models:
    genai_consumption_agent:
      catalog_name: ${var.catalog}
      schema_name: ${var.schema}
      
  schemas:
    genai_functions:
      functions:
        - name: get_genai_consumption_growth
        - name: get_genai_consumption_data_daily

targets:
  dev:
    mode: development
    default: true
  staging:
    mode: development
  prod:
    mode: production
```

### Deploy the Generated DAB

```bash
# Validate the generated bundle
databricks bundle validate

# Deploy to development
databricks bundle deploy --target dev

# Run the job
databricks bundle run genai_agent_deployment --target dev
```

### What Gets Generated

The DAB generator creates:
- **Multi-task workflows** with proper dependencies
- **Job clusters** with appropriate Spark configurations
- **Unity Catalog resources** (models, functions, schemas)
- **Vector search indexes** for RAG applications
- **Environment configurations** for dev/staging/prod
- **Quality monitoring** and inference logging
- **Permission sets** for team collaboration
- **Scheduled jobs** for data pipelines

The generated DAB follows Databricks best practices and is production-ready.

## 🚧 Development Status

### ✅ Phase 1 Complete (Week 2)
- [x] Hybrid FastAPI + FastMCP architecture
- [x] 9 core tools implemented with error handling
- [x] YAML configuration system
- [x] Service layer abstraction
- [x] Databricks SDK integration with profile support
- [x] Comprehensive testing suite
- [x] Claude Code CLI integration working

### ⚡ Phase 2 (Week 3) - DAB Generation **30% Complete**
- [x] `analyze_notebook` ✅ - Deep notebook analysis tool **INTEGRATED**
  - [x] Python/SQL notebook parsing with AST analysis
  - [x] Databricks-specific features detection (widgets, spark, MLflow)
  - [x] Unity Catalog table and dependency extraction
  - [x] ETL/ML/Reporting workflow pattern identification
  - [x] DAB configuration recommendations generation
  - [x] MCP server integration with 13 total tools
  - [x] Claude Code CLI testing completed
- [ ] `generate_bundle` 📅 - Automated DAB creation tool **NEXT PRIORITY**
- [ ] `validate_bundle` 📅 - Bundle validation tool  
- [ ] `create_tests` 📅 - Test scaffold generation tool

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