# Claude Context for Databricks AI Copilot Project

## IMPORTANT: Documentation Context
**ALWAYS reference the `/docs` folder for detailed implementation guidance:**
- `/docs/databricks-asset-bundles.md` - Complete DAB structure, configuration, and examples
- `/docs/custom-mcp-server.md` - MCP server setup, deployment, and connection methods

**Before implementing any feature, search and read relevant documentation in the `/docs` folder first.**

## Project Overview
You are helping build a **Databricks AI Copilot** that uses Claude Code SDK and Model Context Protocol (MCP) to help Data Engineers and ML Engineers analyze notebooks/jobs and generate Databricks Asset Bundles (DABs) with unit tests.

## Current Sprint: 4-Week MVP Hackathon
**Goal**: Deploy a working MCP server integrated with Claude Code CLI that allows users to analyze existing Databricks assets and generate DABs.

## Architecture Components

### 1. Claude Code SDK Agent
- Orchestrates prompts and tool calls
- Connects to MCP servers for Databricks operations
- Generates DABs and unit tests from analysis

### 2. MCP Integration ✅ Phase 1 COMPLETE
- **Managed MCP**: Unity Catalog functions, Genie, Vector Search
- **Custom MCP Server**: Working implementation with 9 operational tools:
  - `health` - Server and Databricks connection status
  - `list_jobs`, `get_job`, `run_job` - Job management
  - `list_notebooks`, `export_notebook` - Notebook operations
  - `execute_dbsql`, `list_warehouses` - SQL operations
  - `list_dbfs_files` - File system browsing

### 3. Claude Code CLI Integration
- **Connection Mode**: stdio-based MCP server
- **Authentication**: Uses existing Databricks CLI profiles
- **Deployment**: Local server or Databricks Apps (optional)
- **Interface**: Natural language chat through Claude

## Implementation Timeline

### Current Status
- [x] Week 1: Setup foundations ✅ COMPLETED
- [x] Week 2: Build MCP server core ✅ COMPLETED (Phase 1)
- [x] Week 3: Expand toolset (Phase 2: DAB generation) ⚡ 25% COMPLETE
- [ ] Week 4: Polish and production deployment

### Current Focus: Phase 2 - DAB Generation Tools
**Current Achievement**: `analyze_notebook` tool fully implemented ✅
**Next Priority**: Integrate with MCP server and implement `generate_bundle`

## Key Technical Requirements

### Environment Setup ✅ COMPLETED
- ✅ Unity Catalog enabled workspace
- ✅ Serverless compute configured
- ✅ Claude API key stored in Databricks secret scope
- ✅ GitHub repository for version control

### Security Requirements
- OAuth authentication for UI
- Secrets management via Databricks secrets
- User permissions respect via Unity Catalog

### Core Functionality (MVP)
1. **Analyze existing notebooks/jobs** ✅
   - [x] Export and parse notebook content ✅
   - [x] Identify dependencies and patterns ✅
   - [x] Generate DAB recommendations ✅

2. **Generate DABs** 📅
   - [ ] Create `bundle.yml` from analysis
   - [ ] Include proper targets (dev only for MVP)
   - [ ] Generate unit test scaffolds

3. **Interactive Claude Integration** ⏳
   - [x] Natural language interface via Claude Code CLI ✅
   - [x] Resource selection through conversation ✅
   - [ ] Preview generated artifacts in chat ⏳
   - [ ] Deploy to dev environment via MCP tools

## Development Guidelines

### CRITICAL: Documentation Usage
Before writing ANY code:
1. **Check `/docs/custom-mcp-server.md`** for MCP server implementation details
2. **Check `/docs/databricks-asset-bundles.md`** for DAB structure and validation

Use these documents as your primary reference - they contain tested patterns and official examples.

### Code Structure
```
dabs-copilot/
├── backend/
│   ├── mcp_server/      # Custom MCP implementation
│   ├── claude_agent/    # Claude SDK integration
│   └── api/            # FastAPI backend
├── mcp/                # MCP server implementation
│   ├── server/        # Server code with 9 working tools
│   ├── scripts/       # Deployment and testing scripts
│   └── tests/         # Test suite
├── databricks/
│   ├── apps/          # Databricks App configs
│   └── notebooks/     # Development notebooks
└── tests/
```

### MCP Server Endpoints
- **stdio mode** - Primary interface for Claude Code CLI
- **FastAPI mode** (optional) - HTTP endpoints for future integrations:
  - `GET /health` - Server health check
  - `GET /mcp-info` - List available tools
  - Future: REST API for tool execution

### MCP Tool Definitions

#### Phase 1 Tools (✅ COMPLETE - Working in /mcp)
```python
# Production-ready tools now available
tools = {
    "health": "Check server and Databricks connection",
    "list_jobs": "List all jobs in workspace",
    "get_job": "Get job configuration details",
    "run_job": "Execute a job with parameters",
    "list_notebooks": "List notebooks in path",
    "export_notebook": "Export notebook in multiple formats",
    "execute_dbsql": "Execute SQL queries",
    "list_warehouses": "List SQL warehouses",
    "list_dbfs_files": "Browse Databricks File System"
}
```

#### Phase 2 Tools (⚡ 25% COMPLETE)
```python
# DAB generation tools implementation status
tools_phase2 = {
    "analyze_notebook": "Deep notebook analysis", ✅ COMPLETE
    "generate_bundle": "Create bundle.yml",     📅 Next
    "validate_bundle": "Validate DAB configuration", 📅 Planned
    "create_tests": "Generate unit test scaffolds"   📅 Planned
}
```

### Claude Code CLI Usage
```bash
# Add MCP server to Claude
claude mcp add --scope user databricks-mcp python mcp/server/main.py

# Use natural language to interact
"List all jobs in my workspace"
"Export the notebook at /Users/alex/etl.py"
"Generate a DAB for this notebook"
```

## Testing Strategy

### Unit Tests
- MCP server handlers
- Claude agent logic
- API endpoint tests

### Integration Tests
- End-to-end workflow: select → analyze → generate
- MCP tool execution
- Authentication flow
- Bundle deployment

## Common Commands

### MCP Server Development ✅ WORKING
```bash
# Start MCP server for Claude Code CLI
cd mcp/server
python main.py

# Register with Claude (one-time setup)
claude mcp add --scope user databricks-mcp python /path/to/mcp/server/main.py

# Test MCP server locally
cd mcp
python test_local_mcp.py test  # Quick validation
python test_local_mcp.py stdio # Test STDIO mode

# Run comprehensive tests
cd mcp/tests
python test_tools.py
```

### Development
```bash
# Install dependencies
pip install -r requirements.txt

# Start FastAPI server (optional, for HTTP access)
cd mcp/server
python app.py

# Databricks App deployment (optional)
cd mcp
./scripts/deploy.sh

# Run tests
cd mcp/tests
python test_tools.py
```

### Databricks CLI
```bash
# Configure workspace
databricks configure --profile dev

# Create secret scope
databricks secrets create-scope --scope claude-keys

# Store API key
databricks secrets put --scope claude-keys --key claude-api-key

# Deploy bundle
databricks bundle deploy --target dev
```

## Error Handling Patterns

### MCP Server Errors
- Graceful degradation if tools unavailable
- Retry logic with exponential backoff
- Clear error messages to UI

### Claude Agent Errors
- Rate limiting handling
- Token limit management
- Fallback to simpler prompts

### Claude Integration Error States
- Clear error messages in chat responses
- Graceful degradation if tools unavailable
- User-friendly explanations of issues

## Performance Considerations

### Optimization Targets
- Chat response time < 3 seconds
- Resource listing < 1 second
- Bundle generation < 10 seconds
- Tool execution < 2 seconds

### Caching Strategy
- Cache workspace resources (5 min TTL)
- Cache notebook exports (until modified)
- Session-based chat history

## Security Checklist

- [ ] Never log or expose API keys
- [ ] Validate all user inputs
- [ ] Use parameterized queries
- [ ] Implement rate limiting
- [ ] Audit tool usage
- [ ] Respect UC permissions
- [ ] HTTPS only for production

## MVP Success Criteria

1. **Functional Requirements**
   - [x] User authenticated via Databricks CLI profile
   - [x] User can select notebooks/jobs via Claude chat
   - [ ] Claude analyzes selected resources
   - [ ] System generates valid bundle.yml
   - [ ] User can preview generated artifacts in chat
   - [ ] User can deploy to dev environment

2. **Non-Functional Requirements**
   - [ ] Response time < 5 seconds for analysis
   - [x] MCP server responds quickly to Claude requests
   - [ ] Handles 10 concurrent users
   - [ ] 95% uptime during demo

## Debug Tips

### Common Issues
1. **MCP connection fails**: Check app deployment status
2. **Claude timeout**: Reduce prompt complexity
3. **OAuth fails**: Verify redirect URIs
4. **Bundle invalid**: Check YAML formatting
5. **MCP tools not available**: Check server registration with Claude

### Logging
- Backend: Python `logging` module
- Claude: Tool response messages
- MCP: Structured logs to Unity Catalog

## References

### Local Documentation (READ THESE FIRST)
- `/docs/databricks-asset-bundles.md` - DAB configuration, structure, validation
- `/docs/custom-mcp-server.md` - MCP server implementation and deployment

### External Documentation
- [Databricks Apps Documentation](https://docs.databricks.com/apps)
- [Claude Code SDK](https://github.com/anthropics/claude-code)
- [Model Context Protocol](https://modelcontextprotocol.io)
- [Databricks Asset Bundles](https://docs.databricks.com/dev-tools/bundles)

## MCP Server Implementation ✅ COMPLETE

### Phase 1 Achievements
1. **9 Working MCP Tools**
   - Full Databricks workspace integration
   - Jobs, notebooks, SQL, and file system operations
   - Tested against live workspace

2. **Claude Code CLI Integration**
   ```bash
   # Working command for Claude integration
   claude mcp add --scope user databricks-mcp python /path/to/mcp/server/main.py
   
   # Natural language queries work immediately
   "List all jobs in my workspace"
   "Export notebook at /Users/alex/etl.py"
   "Run SQL query: SELECT * FROM main.default.sales"
   ```

3. **Production-Ready Architecture**
   - Profile-based authentication using existing CLI setup
   - Environment-aware configuration with YAML + env vars
   - Comprehensive error handling and logging
   - Service layer separation for clean testing

4. **Deployment Options**
   - Local server for development (stdio mode)
   - FastAPI hybrid for HTTP access
   - Databricks Apps deployment scripts ready

The MCP server is fully operational and ready for Phase 2 DAB generation tools.

## Implementation Workflow

When implementing ANY feature:
1. **FIRST**: Read relevant documentation in `/docs` folder
2. **SECOND**: Check the PROJECT_PLAN.md for scope and requirements
3. **THIRD**: Begin implementation following the patterns found
4. **FOURTH**: Test locally with Claude Code CLI before deployment

## Next Steps

When implementing:
1. Start with Week 1 setup tasks
2. Test each component in isolation
3. Integrate incrementally
4. Focus on MVP scope only
5. Document as you build

Remember: This is a hackathon MVP. Prioritize working functionality over perfect code. Get the core flow working first, then iterate.