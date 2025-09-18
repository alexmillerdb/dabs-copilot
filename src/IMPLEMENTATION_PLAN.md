# Databricks Asset Bundles Agent System - Implementation Plan

## Overview

This implementation plan outlines the creation of an intelligent agent system using Claude Code SDK that works in harmony with the existing production-ready MCP server. The hybrid approach preserves the 18 operational tools while adding sophisticated conversation management and multi-step workflow capabilities.

## Current MCP Server Status ✅

**Production Deployment**: https://databricks-mcp-server-1444828305810485.aws.databricksapps.com
**Local Development**: `mcp/server/main.py` (FastMCP stdio mode for Claude Code CLI)

**Available Tools (18 total)**:
- **Phase 1 (9 tools)**: health, list_jobs, get_job, run_job, list_notebooks, export_notebook, execute_dbsql, list_warehouses, list_dbfs_files
- **Phase 2 (6 tools)**: analyze_notebook, generate_bundle, generate_bundle_from_job, validate_bundle, create_tests, get_cluster
- **Phase 3 (3 tools)**: upload_bundle, run_bundle_command, sync_workspace_to_local

**Capabilities**: Complete DAB lifecycle (analyze → generate → upload → deploy)
**Local Testing**: Works with Claude Code CLI via `python mcp/server/main.py`

## Hybrid Architecture

```
src/ (Agent System)              mcp/server/ (Existing)
├── agents/                      ├── main.py (FastMCP stdio)
│   ├── orchestrator.py          ├── app.py (FastAPI HTTP)
│   ├── bundle_specialist.py     ├── tools.py (9 core tools)
│   └── deployment_manager.py    ├── tools_dab.py (6 DAB tools)
└── tools/                       └── tools_workspace.py (3 upload tools)
    ├── agent_tools.py           
    └── mcp_client.py            
```

**Communication Flow**:
1. User → Claude Code SDK Agent (src/)
2. Agent → In-process MCP tools (orchestration)
3. Agent → HTTP calls to existing MCP server (Databricks operations)
4. Agent → Intelligent response synthesis

## Folder Structure

```
src/
├── __init__.py
├── main.py                    # Claude SDK entry point
├── IMPLEMENTATION_PLAN.md     # This document
├── config/
│   ├── __init__.py
│   ├── settings.py           # Agent configuration
│   └── prompts/              # Agent system prompts
│       ├── orchestrator.md
│       ├── bundle_specialist.md
│       └── deployment_manager.md
├── agents/
│   ├── __init__.py
│   ├── base_agent.py         # Base agent with SDK client
│   ├── orchestrator.py       # Main routing agent (Chief of Staff pattern)
│   ├── bundle_specialist.py  # DAB generation expert
│   └── deployment_manager.py # Validation & deployment expert
├── tools/
│   ├── __init__.py
│   ├── agent_tools.py        # SDK in-process tools for orchestration
│   └── mcp_client.py         # HTTP client bridge to existing MCP server
├── services/
│   ├── __init__.py
│   ├── conversation_service.py # Manage context & history
│   └── workflow_service.py     # Complex multi-step workflows
├── utils/
│   ├── __init__.py
│   ├── mcp_bridge.py         # Bridge between SDK and FastMCP
│   └── response_formatter.py # Consistent output formatting
└── tests/
    ├── __init__.py
    ├── test_agents/
    ├── test_tools/
    └── test_integration/
```

## Core Components

### 1. Main Entry Point (`main.py`)

```python
from claude_code_sdk import ClaudeSDKClient, create_sdk_mcp_server
from agents.orchestrator import OrchestratorAgent
from tools.agent_tools import create_agent_tools

# Create in-process MCP server for agent coordination
agent_server = create_sdk_mcp_server(
    name="dab-agent-coordinator",
    version="1.0.0",
    tools=create_agent_tools()
)

# Initialize main agent with hybrid MCP setup
def create_dab_agent():
    return ClaudeSDKClient(
        mcp_servers=[agent_server],
        system_prompt=load_orchestrator_prompt()
    )
```

### 2. Orchestrator Agent (`agents/orchestrator.py`)

**Responsibilities**:
- Route user requests to specialist agents
- Maintain conversation context
- Coordinate multi-agent workflows
- Bridge between SDK and existing MCP server

**Pattern**: Chief of Staff from Claude Code cookbook

### 3. Specialist Agents

**Bundle Specialist** (`agents/bundle_specialist.py`):
- Complex DAB generation workflows
- Multi-resource bundle coordination
- Advanced parameter optimization
- Template customization

**Deployment Manager** (`agents/deployment_manager.py`):
- Bundle validation orchestration
- Deployment strategy planning
- Error recovery workflows
- Environment management

### 4. MCP Bridge (`tools/mcp_client.py`)

```python
class DatabricksMCPClient:
    """Bridge to existing FastMCP server (local or remote)"""
    
    def __init__(self, mode="local", remote_url=None):
        if mode == "local":
            # For development - connect to local stdio server
            self.server_command = ["python", "mcp/server/main.py"]
            self.use_stdio = True
        else:
            # For production - HTTP to Databricks Apps
            self.base_url = remote_url or os.getenv("MCP_REMOTE_URL", 
                "https://databricks-mcp-server-1444828305810485.aws.databricksapps.com")
            self.use_stdio = False
        
    async def call_tool(self, tool_name: str, params: dict) -> dict:
        """Call existing MCP server tools via stdio or HTTP"""
        if self.use_stdio:
            # Use subprocess to communicate with local stdio server
            return await self._call_stdio(tool_name, params)
        else:
            # Use HTTP client for remote server
            return await self._call_http(tool_name, params)
        
    async def list_jobs(self, **kwargs) -> dict:
        return await self.call_tool("list_jobs", kwargs)
        
    async def analyze_notebook(self, **kwargs) -> dict:
        return await self.call_tool("analyze_notebook", kwargs)
        
    # ... wrapper methods for all 18 tools
```

### 5. Agent Tools (`tools/agent_tools.py`)

```python
from claude_code_sdk import tool
from tools.mcp_client import DatabricksMCPClient

@tool()
async def orchestrate_bundle_creation(
    source_type: str,
    source_identifier: str,
    target_env: str = "dev"
) -> str:
    """
    Orchestrate complete bundle creation workflow
    
    Args:
        source_type: "job", "notebook", or "workspace_path"
        source_identifier: Job ID, notebook path, or workspace directory
        target_env: Target environment (dev/staging/prod)
    """
    client = DatabricksMCPClient()
    
    if source_type == "job":
        # Multi-step workflow using existing MCP tools
        job_data = await client.get_job(job_id=source_identifier)
        bundle_config = await client.generate_bundle_from_job(
            job_id=source_identifier,
            bundle_name=f"job-{source_identifier}-bundle"
        )
        validation = await client.validate_bundle(yaml_content=bundle_config)
        
        return format_workflow_result({
            "job_analysis": job_data,
            "bundle_config": bundle_config,
            "validation": validation
        })

@tool()
async def delegate_to_specialist(
    task_type: str,
    task_details: str
) -> str:
    """Delegate complex tasks to specialist agents"""
    if task_type == "bundle_generation":
        specialist = BundleSpecialist()
        return await specialist.handle_request(task_details)
    elif task_type == "deployment":
        manager = DeploymentManager()
        return await manager.handle_request(task_details)
```

## Implementation Timeline

### Phase 1: Foundation (Days 1-2) ✅ COMPLETED
```
✅ Create src/ folder structure
✅ Implement base agent class with ClaudeSDKClient
✅ Create MCP bridge to local server (mcp/server/main.py)
✅ Build simple orchestrator agent
✅ Test hybrid communication with local MCP server
✅ Configure Claude API key integration
✅ Set up comprehensive test suite (15 passing tests)
```

**Completed Components:**
- **Folder Structure**: Complete modular organization with agents/, tools/, services/, tests/
- **Base Agent Class**: Abstract base with lazy-loaded Claude SDK client
- **MCP Bridge**: Dual-mode client (local stdio + remote HTTP) 
- **Orchestrator Agent**: Main routing agent with command parsing
- **Configuration System**: Pydantic settings with .env file support
- **Claude SDK Integration**: Automatic API key loading and client creation
- **Test Coverage**: 15 passing tests using TDD approach

### Phase 2: Core Agents (Days 3-4)
```
- Implement Bundle Specialist agent
- Create Deployment Manager agent
- Add conversation context management
- Build multi-step workflow coordination
- Test complex DAB workflows
```

### Phase 3: Advanced Features (Days 5-6)
```
- Enhanced error handling & recovery
- Performance optimization
- Advanced prompt engineering
- Integration testing with existing MCP server
- Documentation and examples
```

### Phase 4: Integration & Polish (Day 7)
```
- UI integration preparation
- End-to-end testing
- Performance tuning
- Production readiness
```

## Key Design Patterns

### 1. Chief of Staff Pattern
```python
# Orchestrator delegates to specialists
class OrchestratorAgent:
    def route_request(self, user_input: str) -> str:
        if "generate bundle" in user_input.lower():
            return self.delegate_to_bundle_specialist(user_input)
        elif "deploy" in user_input.lower():
            return self.delegate_to_deployment_manager(user_input)
```

### 2. Bridge Pattern
```python
# Seamless integration between SDK and FastMCP
class MCPBridge:
    async def execute_tool(self, tool_name: str, params: dict):
        # Route to appropriate backend (SDK vs HTTP)
        if tool_name in self.agent_tools:
            return await self.sdk_server.call_tool(tool_name, params)
        else:
            return await self.http_client.call_tool(tool_name, params)
```

### 3. Context Management
```python
# Persistent conversation context
class ConversationService:
    def __init__(self):
        self.context = {
            "selected_resources": [],
            "generated_bundles": [],
            "deployment_history": []
        }
        
    def add_context(self, key: str, value: any):
        self.context[key].append(value)
```

## Sample Workflows

### Workflow 1: Job to Bundle (Simple)
```
User: "Generate a bundle from job ID 123"
↓
Orchestrator → MCP Bridge → get_job(123)
↓
Orchestrator → MCP Bridge → generate_bundle_from_job(123)
↓
Orchestrator → Format and return bundle YAML
```

### Workflow 2: Complex Analysis (Multi-step)
```
User: "Analyze all notebooks in /Users/analytics/ and create optimized bundles"
↓
Orchestrator → Bundle Specialist
↓
Specialist → MCP Bridge → list_notebooks("/Users/analytics/")
↓
Specialist → MCP Bridge → analyze_notebook() for each
↓
Specialist → Advanced optimization logic
↓
Specialist → MCP Bridge → generate_bundle() with optimizations
↓
Specialist → Return comprehensive analysis + bundle
```

## Configuration Examples

### Agent Settings (`config/settings.py`)
```python
from pydantic import BaseSettings

class AgentSettings(BaseSettings):
    # MCP Server Configuration
    mcp_mode: str = "local"  # "local" or "remote"
    mcp_remote_url: str = "https://databricks-mcp-server-1444828305810485.aws.databricksapps.com"
    mcp_local_command: str = "python mcp/server/main.py"
    
    # Claude SDK
    claude_api_key: str
    max_conversation_length: int = 100
    
    # Agent Behavior
    auto_validate_bundles: bool = True
    default_target_env: str = "dev"
    enable_advanced_analysis: bool = True
    
    class Config:
        env_file = ".env"
```

### Orchestrator Prompt (`config/prompts/orchestrator.md`)
```markdown
You are the Databricks Asset Bundle Orchestrator, an expert system for managing DAB workflows.

Your responsibilities:
- Route user requests to appropriate specialist agents
- Coordinate multi-step bundle generation workflows
- Maintain conversation context and user preferences
- Provide clear, actionable responses

Available specialists:
- Bundle Specialist: Complex DAB generation, optimization, multi-resource bundles
- Deployment Manager: Validation, deployment strategies, environment management

Available tools via existing MCP server:
- 18 production-ready Databricks tools
- Complete DAB lifecycle capabilities
- Workspace analysis and manipulation

Always prioritize user workflow efficiency and provide step-by-step progress updates.
```

## Testing Strategy

### Unit Tests
```python
# tests/test_agents/test_orchestrator.py
async def test_job_bundle_workflow():
    orchestrator = OrchestratorAgent()
    result = await orchestrator.process("Generate bundle from job 123")
    assert "bundle.yml" in result
    assert "validation" in result

# tests/test_tools/test_mcp_bridge.py
async def test_mcp_client_communication():
    client = DatabricksMCPClient()
    jobs = await client.list_jobs(limit=5)
    assert jobs["success"] is True
```

### Integration Tests
```python
# tests/test_integration/test_end_to_end.py
async def test_complete_bundle_workflow():
    agent = create_dab_agent()
    response = await agent.query(
        "Analyze job 123 and create an optimized bundle for dev environment"
    )
    # Verify complete workflow execution
```

## Key Advantages

1. **Preserve Investment**: Keep excellent 18-tool MCP server
2. **Add Intelligence**: Layer sophisticated agents on top
3. **Flexible Deployment**: Can run locally or in Databricks Apps
4. **Modular Design**: Each component evolves independently
5. **Best of Both Worlds**: FastMCP operations + SDK conversations
6. **Scalable Architecture**: Easy to add new agents and capabilities

## Success Criteria

### Phase 1 Complete ✅
- [x] Basic agent structure implemented
- [x] MCP bridge communicating with existing server  
- [x] Simple orchestrator routing requests
- [x] End-to-end test working locally
- [x] Claude API key configured and working
- [x] Comprehensive test suite (15 passing tests)
- [x] TDD approach with clean code practices

### Phase 2 Complete
- [ ] Bundle Specialist handling complex workflows
- [ ] Deployment Manager coordinating validation/deployment
- [ ] Multi-step workflows executing successfully
- [ ] Conversation context maintained

### Phase 3 Complete
- [ ] Advanced error handling and recovery
- [ ] Performance optimized for production use
- [ ] Comprehensive test coverage
- [ ] Ready for UI integration

## Development Workflow

### Local Testing with Existing MCP Server
```bash
# Terminal 1: Start local MCP server
cd mcp/server
python main.py

# Terminal 2: Test with Claude Code CLI (if configured)
claude-code-cli connect stdio python mcp/server/main.py
claude-code-cli chat "List all jobs in my workspace"

# Terminal 3: Run agent system (once built)
cd src
python main.py
```

### Environment Setup ✅ CONFIGURED
```bash
# Required environment variables (configured in .env)
CLAUDE_API_KEY=sk-ant-api03-...  # ✅ Configured and working
MCP_MODE=local                   # ✅ Set to local for development
MCP_REMOTE_URL=https://databricks-mcp-server-1444828305810485.aws.databricksapps.com
DATABRICKS_CONFIG_PROFILE=aws-apps
DATABRICKS_HOST=https://e2-demo-field-eng.cloud.databricks.com
```

**Configuration Features:**
- **Automatic .env Loading**: Supports both `../env` and `.env` paths
- **API Key Fallback**: Uses `ANTHROPIC_API_KEY` if `CLAUDE_API_KEY` not set
- **Extra Fields Ignored**: Pydantic ignores unrelated environment variables
- **Validation**: Comprehensive error checking and type validation

## Next Steps (Phase 2)

1. **Implement Bundle Specialist Agent** - Complex DAB generation workflows
2. **Create Deployment Manager Agent** - Validation and deployment coordination
3. **Add Conversation Context Management** - Persistent state across interactions
4. **Build Multi-step Workflow Coordination** - Complex task orchestration
5. **Enhanced Error Handling & Recovery** - Production-ready resilience

## Phase 1 Achievement Summary ✅

**Architecture Delivered:**
- Complete modular agent system with 15 passing tests
- Hybrid MCP bridge supporting local development and production deployment
- Claude Code SDK integration with automatic API key management
- TDD-driven development with clean, maintainable code

**Ready For:** Phase 2 specialist agent development and advanced workflow coordination

This hybrid approach leverages your existing production infrastructure while adding the sophisticated agent capabilities needed for an intelligent DAB copilot system.