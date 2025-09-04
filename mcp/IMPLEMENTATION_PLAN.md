# Databricks MCP Server Implementation Plan

## Overview
This plan outlines the enhancement of the existing FastMCP server to follow production-ready patterns from the reference Databricks MCP implementation. The goal is to create a robust, scalable MCP server that integrates with both Claude Code CLI and the Databricks App UI.

## Current State Analysis

### Existing Implementation ✅
- **FastMCP server** with basic tool definitions
- **5 core tools**: `list_jobs`, `get_job`, `run_job`, `list_notebooks`, `export_notebook`
- **JSON configuration** with tool metadata
- **Basic error handling** with try/catch blocks
- **Databricks SDK integration** using WorkspaceClient

### Missing Components (vs Reference Implementation)
- FastAPI integration for web endpoints
- Modular architecture (routers, services)
- YAML configuration system
- SQL warehouse operations
- DBFS file operations
- Health monitoring endpoints
- User authentication/authorization
- Service layer separation
- Comprehensive logging
- Static file serving for UI

## Enhanced Architecture Plan

### 1. Hybrid Server Architecture

**Target Structure:**
```
mcp/server/
├── app.py                 # FastAPI + FastMCP integration
├── tools.py              # MCP tool implementations  
├── prompts.py            # AI prompt templates
├── config.yaml           # YAML configuration
├── requirements.txt      # Dependencies
├── routers/              # FastAPI route handlers
│   ├── __init__.py
│   ├── mcp_info.py       # MCP server info endpoints
│   ├── chat.py           # Chat/Claude integration
│   └── health.py         # Health check endpoints
├── services/             # Business logic layer
│   ├── __init__.py
│   ├── databricks_service.py  # Databricks operations
│   ├── bundle_service.py      # DAB generation
│   └── analysis_service.py    # Code analysis
└── tests/               # Unit tests
    ├── test_tools.py
    ├── test_services.py
    └── test_integration.py
```

### 2. Implementation Phases

#### Phase 1: Core Architecture Enhancement (Week 2 Sprint)
**Priority: HIGH - Needed for Claude Code CLI testing**

1. **Create FastAPI + FastMCP hybrid application** (`app.py`)
   - Integrate existing FastMCP server as sub-mount
   - Add CORS middleware for development
   - Enable static file serving capability
   - Environment-based configuration loading

2. **Enhance tool implementations** (`tools.py`)
   - Add missing tools: `health`, `execute_dbsql`, `list_warehouses`, `list_dbfs_files`
   - Implement consistent error handling pattern
   - Add comprehensive logging
   - Standardize response format: `{'success': bool, 'data': Any, 'error': str}`

3. **YAML configuration system** (`config.yaml`)
   - Convert from JSON to YAML for better readability
   - Environment variable substitution
   - Development/production profiles
   - Tool configuration externalization

4. **Service layer abstraction** (`services/`)
   - Extract business logic from tools
   - Create reusable service methods
   - Enable proper unit testing
   - Separate concerns (Databricks API, data processing, etc.)

#### Phase 2: DAB Generation & Analysis (Week 2-3)
**Priority: MEDIUM - Core feature implementation**

5. **Bundle generation service** (`services/bundle_service.py`)
   - Analyze notebook/job configurations
   - Generate `bundle.yml` templates
   - Create target configurations (dev/staging/prod)
   - Validate generated bundles

6. **Code analysis tools**
   - Parse notebook dependencies
   - Identify data sources and sinks
   - Extract configuration patterns
   - Generate recommendations

7. **Enhanced MCP tools for DAB workflow**
   - `analyze_notebook`: Deep analysis of notebook structure
   - `generate_bundle`: Create DAB from analysis
   - `validate_bundle`: Check bundle configuration
   - `create_tests`: Generate unit test scaffolds

#### Phase 3: Production Features (Week 3-4)
**Priority: LOW - Polish and UI integration**

8. **FastAPI routing layer** (`routers/`)
   - Health check endpoints
   - MCP server information API
   - Chat integration endpoints
   - File upload/download handlers

9. **Authentication & Security**
   - OAuth integration for Databricks
   - API key validation
   - User session management
   - Permission-based access control

10. **UI Integration Features**
    - WebSocket support for real-time chat
    - File preview capabilities
    - Progress tracking for long operations
    - Error reporting and logging

## Detailed Implementation Specifications

### Enhanced Tool Definitions

#### Core Databricks Tools (Phase 1)
```python
# Existing tools (enhanced)
@mcp.tool()
async def list_jobs(limit: int = 100, name_filter: Optional[str] = None)

@mcp.tool() 
async def get_job(job_id: int)

@mcp.tool()
async def run_job(job_id: int, notebook_params: Optional[Dict] = None)

@mcp.tool()
async def list_notebooks(path: str = "/", recursive: bool = False)

@mcp.tool()
async def export_notebook(path: str, format: str = "SOURCE")

# New tools (Phase 1)
@mcp.tool()
async def health() -> Dict[str, Any]
    """Check server and Databricks connection health"""

@mcp.tool()
async def execute_dbsql(query: str, warehouse_id: Optional[str] = None) -> str
    """Execute SQL query on Databricks SQL warehouse"""

@mcp.tool()
async def list_warehouses() -> str
    """List available SQL warehouses"""

@mcp.tool()
async def list_dbfs_files(path: str = "/") -> str
    """List files in Databricks File System"""
```

#### DAB Generation Tools (Phase 2)
```python
@mcp.tool()
async def analyze_notebook(path: str) -> str
    """Analyze notebook structure and dependencies"""

@mcp.tool()
async def generate_bundle(
    name: str, 
    notebooks: List[str], 
    jobs: List[int] = None,
    target: str = "dev"
) -> str
    """Generate Databricks Asset Bundle configuration"""

@mcp.tool()
async def validate_bundle(bundle_path: str) -> str
    """Validate DAB configuration file"""

@mcp.tool()
async def create_tests(notebook_path: str, test_framework: str = "pytest") -> str
    """Generate unit test scaffolds for notebook"""
```

### Configuration System

**YAML Configuration Template:**
```yaml
# config.yaml
server:
  name: "databricks-mcp-server"
  version: "0.2.0" 
  host: "localhost"
  port: 8000
  debug: ${DEBUG:false}

databricks:
  host: ${DATABRICKS_HOST}
  token: ${DATABRICKS_TOKEN}
  warehouse_id: ${DATABRICKS_WAREHOUSE_ID}
  
mcp:
  tools_enabled:
    - list_jobs
    - get_job
    - run_job
    - list_notebooks
    - export_notebook
    - health
    - execute_dbsql
    - list_warehouses
    - list_dbfs_files
    - analyze_notebook
    - generate_bundle
    - validate_bundle

logging:
  level: ${LOG_LEVEL:INFO}
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

cors:
  enabled: ${CORS_ENABLED:true}
  origins:
    - "http://localhost:3000"
    - "http://localhost:5173"
```

### Error Handling Strategy

**Standardized Response Format:**
```python
class MCPResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    timestamp: datetime
    
def create_success_response(data: Any) -> str:
    return json.dumps(MCPResponse(
        success=True,
        data=data,
        timestamp=datetime.now()
    ).model_dump(), indent=2)
    
def create_error_response(error: str) -> str:
    return json.dumps(MCPResponse(
        success=False,
        error=error,
        timestamp=datetime.now()
    ).model_dump(), indent=2)
```

### Testing Strategy

#### Unit Tests
```python
# tests/test_tools.py
@pytest.mark.asyncio
async def test_list_jobs():
    response = await list_jobs(limit=5)
    data = json.loads(response)
    assert data["success"] == True
    assert len(data["data"]["jobs"]) <= 5

# tests/test_services.py  
def test_bundle_generation():
    service = BundleService()
    bundle = service.generate_bundle("test-bundle", ["/path/notebook.py"])
    assert "bundle.yml" in bundle
    assert "dev" in bundle["targets"]
```

#### Integration Tests  
```python
# tests/test_integration.py
@pytest.mark.integration
async def test_notebook_to_bundle_workflow():
    # 1. List notebooks
    notebooks = await list_notebooks(path="/test")
    
    # 2. Analyze notebook 
    analysis = await analyze_notebook("/test/example.py")
    
    # 3. Generate bundle
    bundle = await generate_bundle("example-bundle", ["/test/example.py"])
    
    # 4. Validate bundle
    validation = await validate_bundle(bundle)
    
    assert all(step["success"] for step in [notebooks, analysis, bundle, validation])
```

## Development Workflow

### Local Testing with Claude Code CLI
```bash
# Terminal 1: Start enhanced MCP server
cd mcp/server
python app.py

# Terminal 2: Test with Claude Code CLI
claude-code-cli connect localhost:8000/mcp
claude-code-cli chat "List all jobs in my workspace"
claude-code-cli chat "Export notebook at /Users/example.py and generate a DAB"
```

### Environment Setup
```bash
# Required environment variables
export DATABRICKS_HOST="https://your-workspace.databricks.com"
export DATABRICKS_TOKEN="your-token"
export DATABRICKS_WAREHOUSE_ID="your-warehouse-id"
export DEBUG="true"
export LOG_LEVEL="DEBUG"
export CORS_ENABLED="true"
```

## Success Criteria

### Phase 1 (Week 2)
- [ ] FastAPI + FastMCP server running locally
- [ ] All existing tools working with enhanced error handling
- [ ] New tools implemented: health, SQL operations, DBFS
- [ ] YAML configuration system operational
- [ ] Service layer created and functional
- [ ] Claude Code CLI can connect and execute all tools

### Phase 2 (Week 2-3)  
- [ ] Bundle generation from notebook analysis
- [ ] DAB validation and testing tools
- [ ] Complete notebook-to-DAB workflow functional
- [ ] Unit tests covering all tools and services
- [ ] Integration tests for full workflows

### Phase 3 (Week 3-4)
- [ ] FastAPI routes for UI integration
- [ ] Authentication and security measures
- [ ] WebSocket support for real-time features
- [ ] Production-ready deployment configuration
- [ ] Comprehensive logging and monitoring

## Deployment Considerations

### Local Development
- FastMCP server on port 5173 (for Claude Code CLI)
- FastAPI server on port 8000 (for web UI)
- Hot reload for development

### Databricks App Deployment
- Single entry point supporting both MCP and HTTP protocols
- Environment-specific configuration
- Secure credential management
- Health monitoring and logging

## Next Steps

1. **Start with Phase 1** - enhance existing architecture
2. **Test each component** with Claude Code CLI before moving to next phase
3. **Iterate quickly** - prioritize working functionality over perfect code
4. **Document as you build** - maintain implementation notes
5. **Focus on MVP scope** - avoid feature creep during hackathon

This plan provides a clear roadmap to transform the basic FastMCP server into a production-ready, feature-rich MCP implementation that supports both Claude Code CLI and Databricks App UI integration.