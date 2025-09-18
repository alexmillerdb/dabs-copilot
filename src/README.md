# Databricks Asset Bundle Agent System

A modular, intelligent agent system built with Claude Code SDK for generating, validating, and deploying Databricks Asset Bundles (DABs). Uses a hybrid architecture that leverages your existing MCP server while adding sophisticated conversation management.

## 🏗️ Architecture Overview

```
src/
├── agents/              # Intelligent agent implementations
│   ├── base.py         # Abstract base agent with Claude SDK integration
│   └── orchestrator.py # Main routing agent (Chief of Staff pattern)
├── tools/              # MCP bridge and agent tools
│   └── mcp_client.py   # Hybrid client (local stdio + remote HTTP)
├── config/             # Configuration management
│   └── settings.py     # Pydantic settings with .env support
├── services/           # Business logic services
├── utils/              # Utility functions
├── tests/              # Comprehensive test suite
│   ├── test_agents/    # Agent-specific tests
│   ├── test_tools/     # Tool and MCP bridge tests
│   └── test_config.py  # Configuration tests
├── main.py             # Interactive CLI entry point
└── IMPLEMENTATION_PLAN.md # Detailed implementation roadmap
```

## 🚀 Quick Start

### Prerequisites

1. **Python Environment**: Activate the virtual environment
2. **Environment Variables**: Ensure `.env` file is configured with Claude API key
3. **MCP Server**: Have your 18-tool MCP server accessible (local or remote)

### Installation

```bash
# From project root
cd src

# Install dependencies (if not already installed)
pip install pytest pytest-asyncio pydantic-settings claude-code-sdk

# Verify configuration
python -c "from config.settings import get_settings; print('✅ Config loaded:', get_settings().claude_api_key is not None)"
```

### Environment Configuration

Your `.env` file should contain:
```bash
# Claude API Key (required)
CLAUDE_API_KEY=sk-ant-api03-...

# MCP Configuration
MCP_MODE=local  # or "remote" for production
MCP_REMOTE_URL=https://your-databricks-mcp-server.aws.databricksapps.com

# Databricks Configuration  
DATABRICKS_CONFIG_PROFILE=aws-apps
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
```

## 🧪 Testing

### Run All Tests
```bash
# From src/ directory
python -m pytest tests/ -v

# Expected output: 15 passed tests
```

### Test Categories

**Configuration Tests** (`test_config.py`):
- Settings loading and validation
- Environment variable handling
- API key configuration

**Agent Tests** (`test_agents/`):
- Base agent functionality
- Orchestrator routing logic
- Claude SDK integration

**Tool Tests** (`test_tools/`):
- MCP client bridge functionality
- Local vs remote mode switching
- Tool call interfaces

### Manual Testing

**Interactive Agent System**:
```bash
python main.py

# Try these commands:
# - help
# - list jobs
# - get job 123
# - generate bundle from job 456
# - quit
```

**Configuration Verification**:
```bash
python -c "
from agents.orchestrator import OrchestratorAgent
import asyncio

async def test():
    agent = OrchestratorAgent()
    result = await agent.handle_request('help')
    print('Agent Response:', result)

asyncio.run(test())
"
```

## 🔧 Current Capabilities

### Phase 1 Implementation ✅

**Orchestrator Agent** (`agents/orchestrator.py`):
- Natural language command parsing
- Route requests to appropriate handlers
- Integration with MCP bridge
- Error handling and help messages

**Supported Commands**:
- `list jobs` - List all jobs in workspace
- `get job <id>` - Get details for specific job  
- `generate bundle from job <id>` - Create DAB from existing job
- `help` - Show available commands

**MCP Bridge** (`tools/mcp_client.py`):
- **Local Mode**: Connects to `mcp/server/main.py` via stdio
- **Remote Mode**: HTTP calls to Databricks Apps deployment
- **Tool Mapping**: Wraps all 18 existing MCP server tools
- **Error Handling**: Graceful fallbacks and retry logic

**Configuration System** (`config/settings.py`):
- Automatic `.env` file loading
- Support for both `CLAUDE_API_KEY` and `ANTHROPIC_API_KEY`
- Pydantic validation with type checking
- Extra fields ignored (clean separation)

## 🔍 Key Design Patterns

### 1. **Hybrid MCP Integration**
```python
# Automatically switches between local and remote MCP servers
client = DatabricksMCPClient(mode="local")  # Development
client = DatabricksMCPClient(mode="remote")  # Production
```

### 2. **Lazy-Loaded Claude SDK**
```python
# Base agent creates Claude SDK client only when needed
class BaseAgent:
    @property
    def client(self):
        if self._client is None:
            self._client = self._create_client()
        return self._client
```

### 3. **Command Routing Pattern**
```python
# Orchestrator parses natural language and routes to handlers
if "list jobs" in request_lower:
    return await self._handle_list_jobs()
elif job_match := re.search(r"get job (\d+)", request_lower):
    return await self._handle_get_job(int(job_match.group(1)))
```

## 🐛 Troubleshooting

### Common Issues

**1. Claude API Key Not Found**
```bash
# Check if environment variables are loaded
python -c "
from config.settings import get_settings
settings = get_settings()
print('API Key loaded:', settings.claude_api_key is not None)
"
```

**2. MCP Server Connection Issues**
```bash
# Test MCP bridge directly
python -c "
from tools.mcp_client import DatabricksMCPClient
import asyncio

async def test():
    client = DatabricksMCPClient(mode='local')
    result = await client.list_jobs()
    print('MCP Response:', result)

asyncio.run(test())
"
```

**3. Import Errors**
```bash
# Ensure you're running from src/ directory
pwd  # Should end with /src
python -c "import agents.orchestrator; print('✅ Imports working')"
```

**4. Test Failures**
```bash
# Run tests with verbose output for debugging
python -m pytest tests/ -v --tb=short

# Run specific test file
python -m pytest tests/test_config.py -v
```

## 🔮 Phase 2 Roadmap

### Planned Specialist Agents

**Bundle Specialist** (`agents/bundle_specialist.py`):
- Complex multi-resource DAB generation
- Parameter optimization and recommendations
- Template customization and versioning

**Deployment Manager** (`agents/deployment_manager.py`):
- Bundle validation orchestration
- Environment-specific deployment strategies
- Error recovery and rollback workflows

**Code Analyzer** (`agents/code_analyzer.py`):
- Workspace code scanning and analysis
- Dependency extraction and mapping
- Entry point identification for DAB generation

### Enhanced Features

- **Conversation Context**: Persistent state across interactions
- **Multi-step Workflows**: Complex task orchestration
- **Advanced Error Recovery**: Production-ready resilience
- **Real-time Streaming**: Progress updates for long-running operations

## 📚 Development Guidelines

### Adding New Agents

1. **Extend Base Agent**:
```python
from agents.base import BaseAgent

class NewAgent(BaseAgent):
    def __init__(self):
        super().__init__("new-agent")
    
    def _create_client(self):
        # Return Claude SDK client
        
    async def handle_request(self, request: str) -> str:
        # Implement agent logic
```

2. **Add Tests**:
```python
# tests/test_agents/test_new_agent.py
async def test_new_agent_functionality():
    agent = NewAgent()
    result = await agent.handle_request("test command")
    assert "expected" in result
```

3. **Update Orchestrator**:
```python
# In orchestrator.py
if "new agent pattern" in request_lower:
    specialist = NewAgent()
    return await specialist.handle_request(request)
```

### Code Quality Standards

- **TDD Approach**: Write tests first, then implementation
- **Type Hints**: Use comprehensive type annotations
- **Error Handling**: Graceful degradation, no silent failures
- **Documentation**: Clear docstrings and inline comments
- **Modularity**: Single responsibility principle
- **Testing**: Aim for >90% test coverage

## 🤝 Integration Points

### Existing MCP Server
- **18 Production Tools**: Full integration with existing DAB lifecycle
- **Seamless Bridge**: No changes required to existing MCP implementation
- **Local Development**: Fast iteration with `mcp/server/main.py`
- **Production Ready**: HTTP integration with Databricks Apps deployment

### Claude Code CLI
- **Compatible**: Designed to work with Claude Code CLI patterns
- **SDK Integration**: Proper use of Claude Code SDK patterns
- **Tool Definitions**: Ready for `@tool` decorator integration

### Future UI Integration
- **API Ready**: Clean interfaces for web UI integration
- **State Management**: Context preservation for UI sessions
- **Real-time Updates**: WebSocket-compatible architecture

---

## 📄 License & Contributing

This is part of the Databricks Asset Bundle Copilot project. See main project documentation for contributing guidelines and license information.

For questions or issues with this agent system, please refer to the `IMPLEMENTATION_PLAN.md` for detailed architecture decisions and next steps.