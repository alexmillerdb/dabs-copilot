# Claude Context for Databricks AI Copilot Project

## IMPORTANT: Documentation Context
**ALWAYS reference the `/docs` folder for detailed implementation guidance:**
- `/docs/databricks-asset-bundles.md` - Complete DAB structure, configuration, and examples
- `/docs/custom-mcp-server.md` - MCP server setup, deployment, and connection methods

**Before implementing any feature, search and read relevant documentation in the `/docs` folder first.**

## Project Overview
You are helping build a **Databricks AI Copilot** that uses Claude Code SDK and Model Context Protocol (MCP) to help Data Engineers and ML Engineers analyze notebooks/jobs and generate Databricks Asset Bundles (DABs) with unit tests.

## Current Sprint: 4-Week MVP Hackathon
**Goal**: Deploy a working Databricks App with custom UI that allows users to interact with Claude to analyze existing Databricks assets and generate DABs.

## Architecture Components

### 1. Claude Code SDK Agent
- Orchestrates prompts and tool calls
- Connects to MCP servers for Databricks operations
- Generates DABs and unit tests from analysis

### 2. MCP Integration
- **Managed MCP**: Unity Catalog functions, Genie, Vector Search
- **Custom MCP Server**: Databricks App exposing:
  - `list_jobs`, `run_job`
  - `list_notebooks`, `export_notebook`
  - Additional workspace operations

### 3. Custom Databricks App UI
- **Tech Stack**: React 18 + TypeScript
- **Layout**: 3-panel design (Resource Explorer, Chat, Output)
- **Authentication**: Databricks OAuth
- **Deployment**: Serverless via Databricks Apps

## Implementation Timeline

### Current Status
- [ ] Week 1: Setup foundations
- [ ] Week 2: Build MCP server core
- [ ] Week 3: Expand toolset and polish
- [ ] Week 4: Create custom UI

## Key Technical Requirements

### Environment Setup
- Unity Catalog enabled workspace
- Serverless compute (preferred) or cluster fallback
- Claude API key stored in Databricks secret scope
- GitHub repository for version control

### Security Requirements
- OAuth authentication for UI
- Secrets management via Databricks secrets
- User permissions respect via Unity Catalog

### Core Functionality (MVP)
1. **Analyze existing notebooks/jobs**
   - Export and parse notebook content
   - Identify dependencies and patterns
   - Generate recommendations

2. **Generate DABs**
   - Create `bundle.yml` from analysis
   - Include proper targets (dev only for MVP)
   - Generate unit test scaffolds

3. **Interactive UI**
   - Chat interface with Claude
   - Resource selection (notebooks/jobs)
   - Preview generated artifacts
   - Deploy to dev environment

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
├── frontend/
│   ├── src/
│   │   ├── components/ # React components
│   │   ├── hooks/     # Custom React hooks
│   │   └── utils/     # Helper functions
│   └── public/
├── databricks/
│   ├── apps/          # Databricks App configs
│   └── notebooks/     # Development notebooks
└── tests/
```

### API Endpoints
- `POST /chat` - Send message to Claude agent
- `GET /resources` - List workspace resources
- `POST /analyze` - Analyze selected resource
- `POST /generate-dab` - Generate DAB from analysis
- `POST /deploy` - Deploy bundle to dev

### MCP Tool Definitions
```python
# Essential tools for MVP
tools = {
    "list_jobs": "List all jobs in workspace",
    "get_job": "Get job configuration details",
    "run_job": "Execute a job",
    "list_notebooks": "List notebooks in path",
    "export_notebook": "Export notebook content",
    "create_bundle": "Generate bundle.yml",
    "validate_bundle": "Validate DAB configuration"
}
```

### UI Component Structure
```typescript
// Main components
<App>
  <Header />
  <MainLayout>
    <ResourceExplorer />
    <ChatInterface />
    <OutputPanel />
  </MainLayout>
</App>
```

## Testing Strategy

### Unit Tests
- MCP server handlers
- Claude agent logic
- React component tests
- API endpoint tests

### Integration Tests
- End-to-end workflow: select → analyze → generate
- MCP tool execution
- Authentication flow
- Bundle deployment

## Common Commands

### Development
```bash
# Backend
cd backend && pip install -r requirements.txt
python -m uvicorn api.main:app --reload

# Frontend  
cd frontend && npm install
npm run dev

# Databricks App deployment
databricks apps deploy --app-name dabs-copilot

# Run tests
pytest backend/tests/
npm run test
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

### UI Error States
- Loading spinners during operations
- Error boundaries for component crashes
- User-friendly error messages

## Performance Considerations

### Optimization Targets
- Chat response time < 3 seconds
- Resource listing < 1 second
- Bundle generation < 10 seconds
- UI rendering < 100ms

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
   - [ ] User can authenticate via OAuth
   - [ ] User can select notebooks/jobs from UI
   - [ ] Claude analyzes selected resources
   - [ ] System generates valid bundle.yml
   - [ ] User can preview generated artifacts
   - [ ] User can deploy to dev environment

2. **Non-Functional Requirements**
   - [ ] Response time < 5 seconds for analysis
   - [ ] UI responsive on desktop browsers
   - [ ] Handles 10 concurrent users
   - [ ] 95% uptime during demo

## Debug Tips

### Common Issues
1. **MCP connection fails**: Check app deployment status
2. **Claude timeout**: Reduce prompt complexity
3. **OAuth fails**: Verify redirect URIs
4. **Bundle invalid**: Check YAML formatting
5. **UI not updating**: Check WebSocket connection

### Logging
- Backend: Python `logging` module
- Frontend: Browser console + error tracking
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

## Implementation Workflow

When implementing ANY feature:
1. **FIRST**: Read relevant documentation in `/docs` folder
2. **SECOND**: Check the PROJECT_PLAN.md for scope and requirem
3. **THIRD**: Begin implementation following the patterns found

## Next Steps

When implementing:
1. Start with Week 1 setup tasks
2. Test each component in isolation
3. Integrate incrementally
4. Focus on MVP scope only
5. Document as you build

Remember: This is a hackathon MVP. Prioritize working functionality over perfect code. Get the core flow working first, then iterate.