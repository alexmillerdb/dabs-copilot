# DAB Generator MVP - Implementation Plan

## Overview

This implementation plan outlines the creation of a simple but effective web-based DAB (Databricks Asset Bundle) generator. The MVP leverages the existing production-ready MCP server and the proven Claude Code SDK pattern from `src/examples/databricks_job_dab_example.py` to create a user-friendly interface for generating bundles.

## Current MCP Server Status ✅

**Production Deployment**: https://databricks-mcp-server-1444828305810485.aws.databricksapps.com
**Local Development**: `mcp/server/main.py` (FastMCP stdio mode for Claude Code CLI)

**Available Tools (18 total)**:
- **Phase 1 (9 tools)**: health, list_jobs, get_job, run_job, list_notebooks, export_notebook, execute_dbsql, list_warehouses, list_dbfs_files
- **Phase 2 (6 tools)**: analyze_notebook, generate_bundle, generate_bundle_from_job, validate_bundle, create_tests, get_cluster
- **Phase 3 (3 tools)**: upload_bundle, run_bundle_command, sync_workspace_to_local

**Authentication**: Uses `DATABRICKS_CONFIG_PROFILE=aws-apps` (profile-based auth working ✅)

## MVP Architecture

```
dabs-copilot/
├── src/
│   ├── examples/                    # Reference implementations ✅
│   │   └── databricks_job_dab_example.py  # Working Claude SDK pattern
│   ├── api/                         # FastAPI backend
│   │   ├── main.py                  # FastAPI app
│   │   ├── models.py                # Request/response schemas
│   │   ├── claude_client.py         # Claude SDK wrapper (from example)
│   │   └── bundle_service.py        # DAB generation logic
│   └── frontend/                    # Simple web UI
│       ├── static/
│       │   ├── index.html           # Single page app
│       │   ├── app.js               # Vanilla JavaScript
│       │   └── style.css            # Basic styling
│       └── bundles/                 # Generated bundle storage
├── mcp/                             # Existing MCP server ✅
│   └── server/                      # 18 production tools
└── .env                             # Environment config ✅
```

## MVP Features

### Core Functionality
✅ **Job → DAB Generation** - User inputs job ID, gets downloadable bundle
✅ **Workspace → DAB Generation** - User inputs workspace path, gets bundle  
✅ **Real-time Progress** - Show what's happening during generation
✅ **Download Results** - ZIP file with generated bundle
✅ **Bundle Validation** - Validate generated bundles before download

### Out of Scope (for MVP)
❌ Authentication (use existing profile)
❌ Bundle deployment to workspace
❌ Multiple workspace support
❌ Advanced configuration options
❌ Bundle editing interface

## Chat-Based API Design

### Primary Chat Interface
```python
# Natural language DAB generation
POST /api/chat
# Request: {
#   "message": "Generate a DAB from job 662067900958232 with ML optimizations",
#   "conversation_id": "optional-uuid-for-context"
# }
# Response: Server-Sent Events (SSE) stream with:
# {
#   "type": "message", 
#   "content": "🚀 I'll generate an ML-optimized bundle from job 662067900958232..."
# }
# {
#   "type": "tool_use",
#   "tool": "get_job",
#   "status": "running"
# }
# {
#   "type": "file_generated",
#   "filename": "job-662067900958232-bundle.zip",
#   "download_url": "/api/files/bundle-uuid"
# }

# System health check
GET /api/health
# Response: {"status": "healthy", "databricks_connected": true, "mcp_tools": 18}

# Download generated files
GET /api/files/{file_id}
# Response: ZIP file download or individual file

# Optional: Chat history
GET /api/history/{conversation_id}
# Response: {"messages": [...], "files_generated": [...]}
```

### Chat-Based Data Flow Pattern
```python
# Streaming natural language workflow:
1. User sends natural language message via POST /api/chat
2. FastAPI creates ClaudeSDKClient with CLAUDE.md context
3. Claude reads context and understands DAB domain expertise
4. Stream responses back to user in real-time (SSE)
5. Claude uses MCP tools dynamically based on user request
6. Files are generated and made available via download links
7. Conversation context maintained for follow-up questions

# Implementation:
@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """Stream DAB generation responses"""
    
    async def generate_response():
        async with ClaudeSDKClient(
            options=ClaudeCodeOptions(
                model="claude-sonnet-4-20250514",
                cwd="src/api",  # CLAUDE.md context
                mcp_servers=build_mcp_servers(),
                allowed_tools=ALL_MCP_TOOLS,
                max_turns=20  # Allow for complex conversations
            )
        ) as client:
            
            async for message in client.query(request.message):
                if isinstance(message, AssistantMessage):
                    yield f"data: {json.dumps({'type': 'message', 'content': message.content})}\n\n"
                elif isinstance(message, ToolUseBlock):
                    yield f"data: {json.dumps({'type': 'tool_use', 'tool': message.name})}\n\n"
    
    return StreamingResponse(generate_response(), media_type="text/plain")
```

## Chat-Based Frontend UI Design

### Chat Interface Layout
```html
┌─────────────────────────────────────────────────┐
│              DAB Generator Chat                 │
├─────────────────────────────────────────────────┤
│ Chat Messages:                                  │
│                                                 │
│ User: Generate a bundle from job 662067900958232│
│                                                 │
│ 🤖 Claude: 🚀 I'll generate a DAB from job     │
│ 662067900958232. Let me analyze it first...     │
│                                                 │
│ ⚡ Using tool: get_job                          │
│ ✅ Found MLflow batch inference job             │
│                                                 │
│ ⚡ Using tool: analyze_notebook                 │
│ 📊 Analyzing notebook for dependencies...       │
│                                                 │
│ ✅ Generated optimized ML bundle!               │
│ 📦 [Download: job-662067900958232-bundle.zip]  │
│                                                 │
├─────────────────────────────────────────────────┤
│ [                                           ] 💬│
│ Type your DAB generation request...             │
│                                                 │
│ 💡 Examples:                                    │
│ • Generate a bundle from job 123                │
│ • Create bundles for /Workspace/Users/alex/ml/  │
│ • Convert my streaming job with smaller clusters │
└─────────────────────────────────────────────────┘
```

### Interactive Features
```javascript
// Chat-based JavaScript features:
1. Real-time message streaming (Server-Sent Events)
2. Auto-scrolling chat messages
3. Typing indicators during tool usage
4. Inline download buttons for generated files
5. Message history and conversation context
6. Example prompts to guide users
7. File preview capabilities (YAML viewer)
8. Copy/paste bundle configurations
```

## Implementation Timeline

### Phase 1: Chat Backend (2-3 hours)
```python
✅ Create FastAPI app with SSE streaming support
✅ Implement POST /api/chat endpoint with Claude SDK integration
✅ Extract CLAUDE.md context pattern from examples/databricks_job_dab_example.py
✅ Add file generation and download endpoint
✅ Test with natural language: "Generate bundle from job 662067900958232"
```

### Phase 2: Chat Frontend (1-2 hours)
```html
✅ Create chat interface with message bubbles
✅ Implement Server-Sent Events for real-time streaming
✅ Add auto-scrolling and typing indicators
✅ Create inline download buttons for generated files
✅ Add example prompts to guide user interaction
```

### Phase 3: Enhanced Features (1-2 hours)
```
✅ Conversation history and context management
✅ File preview capabilities (YAML viewer)
✅ Error handling with helpful suggestions
✅ Mobile-responsive chat design
✅ Copy/paste functionality for configurations
```

## Key Implementation Details

### Chat-Based Implementation Pattern
```python
# Streaming chat with CLAUDE.md context:
def build_chat_options() -> ClaudeCodeOptions:
    """Build Claude options for chat-based DAB generation"""
    project_root = Path(__file__).parent.parent.parent
    mcp_server_path = project_root / "mcp" / "server" / "main.py"
    
    return ClaudeCodeOptions(
        model="claude-sonnet-4-20250514",
        cwd="src/api",  # Directory containing CLAUDE.md ✅
        mcp_servers={
            "databricks-mcp": {
                "command": "python",
                "args": [str(mcp_server_path)],
                "env": {
                    "DATABRICKS_CONFIG_PROFILE": os.getenv("DATABRICKS_CONFIG_PROFILE", "DEFAULT"),
                    "DATABRICKS_HOST": os.getenv("DATABRICKS_HOST", ""),
                }
            }
        },
        allowed_tools=ALL_MCP_TOOLS,  # Full tool access for natural language
        max_turns=20  # Extended for conversational workflows
    )

@app.post("/api/chat")
async def chat_dab_generation(request: ChatRequest):
    """Handle natural language DAB generation requests"""
    
    async def stream_responses():
        async with ClaudeSDKClient(options=build_chat_options()) as client:
            # Claude reads CLAUDE.md for DAB expertise automatically
            async for message in client.query(request.message):
                
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            yield {
                                "type": "message",
                                "content": block.text,
                                "timestamp": datetime.now().isoformat()
                            }
                        elif isinstance(block, ToolUseBlock):
                            yield {
                                "type": "tool_use",
                                "tool": block.name,
                                "status": "starting",
                                "inputs": block.input
                            }
                
                elif isinstance(message, ResultMessage):
                    # Handle file generation and download links
                    if hasattr(message, 'files_generated'):
                        for file_path in message.files_generated:
                            yield {
                                "type": "file_generated",
                                "filename": Path(file_path).name,
                                "download_url": f"/api/files/{generate_file_id(file_path)}"
                            }
    
    return StreamingResponse(
        (f"data: {json.dumps(data)}\n\n" async for data in stream_responses()),
        media_type="text/plain"
    )
```

### Conversation Management
```python
# Chat-based session management:
conversations: Dict[str, ConversationState] = {}

class ConversationState:
    conversation_id: str
    messages: List[ChatMessage]
    generated_files: List[GeneratedFile]
    context: Dict[str, Any]  # For maintaining context between messages
    created_at: datetime
    last_activity: datetime

class ChatMessage:
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime
    tool_uses: List[str] = []  # Track which tools were used
    files_generated: List[str] = []

# File management for downloads
generated_files: Dict[str, str] = {}  # file_id -> file_path

def generate_file_id(file_path: str) -> str:
    """Generate unique ID for file downloads"""
    file_id = str(uuid.uuid4())
    generated_files[file_id] = file_path
    return file_id

@app.get("/api/files/{file_id}")
async def download_file(file_id: str):
    """Download generated bundle files"""
    if file_id not in generated_files:
        raise HTTPException(status_code=404, detail="File not found")
    
    file_path = generated_files[file_id]
    if not Path(file_path).exists():
        raise HTTPException(status_code=404, detail="File no longer available")
    
    return FileResponse(
        file_path,
        media_type='application/octet-stream',
        filename=Path(file_path).name
    )
```

## File Structure
```
src/
├── __init__.py
├── IMPLEMENTATION_PLAN.md         # This document
├── examples/                      # Reference implementations ✅
│   ├── databricks_job_dab_example.py  # Working pattern to reuse
│   ├── quick_start.py
│   ├── streaming_mode.py
│   ├── mcp_calculator.py
│   └── custom_mcp_example.py
└── api/                           # Chat-based MVP backend
    ├── CLAUDE.md                  # Context file for DAB generation ✅
    ├── main.py                    # FastAPI chat app (~200 lines)
    ├── models.py                  # Chat & conversation schemas (~100 lines)
    ├── chat_handler.py            # Chat streaming logic (~150 lines)
    ├── file_manager.py            # File generation & downloads (~100 lines)
    └── static/                    # Chat frontend
        ├── index.html             # Chat UI (~150 lines)
        ├── chat.js                # SSE + chat logic (~250 lines)
        ├── style.css              # Chat styling (~120 lines)
        └── files/                 # Generated bundle storage
```

**Total: ~1,070 lines of code for complete chat-based MVP**

## Success Criteria

### Chat MVP Complete
- [ ] FastAPI backend with streaming chat endpoint
- [ ] Natural language DAB generation working end-to-end
- [ ] Real-time streaming responses (Server-Sent Events)
- [ ] File generation with download links in chat
- [ ] Conversation context and history management
- [ ] Professional chat UI with examples and guidance
- [ ] Error handling with conversational recovery
- [ ] CLAUDE.md context integration for domain expertise

### Ready for Extension
- [ ] Multi-conversation support with persistent history
- [ ] Advanced file preview and editing capabilities
- [ ] Mobile-responsive chat interface
- [ ] Integration with Databricks deployment workflows
- [ ] Docker deployment configuration
- [ ] API documentation for chat endpoints

## Environment Setup ✅

```bash
# Required environment variables (already configured):
DATABRICKS_CONFIG_PROFILE=aws-apps           # ✅ Working
DATABRICKS_HOST=https://e2-demo-field-eng... # ✅ Working
CLAUDE_API_KEY=sk-ant-api03-...              # ✅ Required for Claude SDK
```

## Development Workflow

### Local Development
```bash
# Terminal 1: Start chat backend
cd src/api
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Terminal 2: Open chat interface
# Open http://localhost:8000 in browser

# Terminal 3: Monitor MCP server (optional)
cd mcp/server  
python main.py
```

### Testing
```bash
# Test chat endpoint
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Generate a bundle from job 662067900958232"}'

# Test health check
curl http://localhost:8000/api/health

# Test file download
curl http://localhost:8000/api/files/{file-id}
```

## Next Steps

1. **Start with Phase 1** - Create FastAPI chat backend with streaming
2. **Build Chat UI** - Real-time chat interface with Server-Sent Events
3. **Add Advanced Features** - File preview, conversation history, mobile support
4. **Enhance Context** - Improve CLAUDE.md for better DAB generation
5. **Package for Deployment** - Docker container for easy deployment

## Sample User Interactions

### Example 1: Simple Job Conversion
```
User: Generate a bundle from job 662067900958232

Claude: 🚀 I'll generate a DAB from job 662067900958232. Let me analyze it first...

⚡ Using tool: get_job
✅ Found MLflow batch inference job with 1 notebook

⚡ Using tool: analyze_notebook  
📊 Analyzing notebook for dependencies and ML patterns...

⚡ Using tool: generate_bundle
🔧 Creating optimized ML bundle with 14.3.x-ml cluster configuration...

✅ Bundle generated successfully!
📦 [Download: job-662067900958232-bundle.zip]

The bundle includes:
• Optimized ML cluster configuration
• MLflow library dependencies  
• Parameterized variables for different environments
• Validation passed ✅
```

### Example 2: Conversational Refinement
```
User: Make the cluster smaller for dev

Claude: ✅ I'll update the cluster configuration for a development environment.

⚡ Using tool: generate_bundle
🔧 Updated cluster to i3.large with 1 worker for cost optimization...

✅ Updated bundle generated!
📦 [Download: job-662067900958232-bundle-dev.zip]

Changes made:
• Cluster: i3.xlarge → i3.large (cost savings)
• Workers: 2 → 1 (sufficient for dev)
• Same ML optimizations maintained
```

## CLAUDE.md Integration Benefits

### Context-Aware Generation
✅ **Domain Expertise** - Claude understands DAB best practices from CLAUDE.md
✅ **Workflow Guidance** - Follows structured generation patterns automatically
✅ **Quality Standards** - Ensures bundles meet Databricks requirements
✅ **Error Recovery** - Provides contextual fixes and alternatives
✅ **Template Selection** - Chooses appropriate patterns for detected workloads

### Implementation Pattern
```python
# The cwd parameter points Claude to the api/ directory:
ClaudeCodeOptions(
    model="claude-sonnet-4-20250514",
    cwd="src/api",  # Claude reads CLAUDE.md from this directory
    mcp_servers=...,
    max_turns=15
)

# Claude automatically incorporates CLAUDE.md context:
# - Objective and use cases
# - Workflow patterns and standards  
# - Template selection logic
# - Error handling approaches
# - Response guidelines and quality metrics
```

## Key Advantages

✅ **Fast to Build** - Reuses working MCP integration and Claude SDK pattern
✅ **Contextually Intelligent** - Claude understands DAB domain from CLAUDE.md
✅ **Simple to Use** - Single page, clear workflow, immediate results
✅ **Production Ready** - Built on proven MCP server with 18 operational tools
✅ **Quality Assured** - Follows Databricks best practices automatically
✅ **Easy to Extend** - Clean API and modular structure for future features
✅ **Self Contained** - No complex dependencies or external services

This MVP approach delivers immediate value with intelligent DAB generation while providing a solid foundation for future enhancements.