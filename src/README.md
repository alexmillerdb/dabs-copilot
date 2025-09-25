# DAB Generator - Databricks Asset Bundle Co-pilot

A conversational AI-powered web application that generates Databricks Asset Bundles (DAB) from existing jobs, pipelines, or workspace code using Claude Code SDK and MCP integration. Features a beautiful, modern web interface with real-time streaming responses and professional Databricks branding.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Databricks CLI configured with your workspace
- Claude API key
- Virtual environment (recommended)

### 1. Environment Setup

```bash
# Clone and navigate to the project
cd dabs-copilot/src/api

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the project root or set these environment variables:

```bash
# Required: Claude API Key
export CLAUDE_API_KEY="sk-ant-api03-your-key-here"

# Required: Databricks Configuration
export DATABRICKS_CONFIG_PROFILE="your-profile"  # Or "DEFAULT"
export DATABRICKS_HOST="https://your-workspace.databricks.com"

# Optional: Databricks token (if not using CLI auth)
export DATABRICKS_TOKEN="your-databricks-token"
```

### 3. Start the Application

```bash
# From src/api directory
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Access the Web Interface

Open your browser and navigate to:
- **Main Application**: http://localhost:8000
- **API Health Check**: http://localhost:8000/api/health
- **API Documentation**: http://localhost:8000/docs

## 💬 How to Use

### Example Conversations

1. **Generate from Job ID**:
   ```
   "Generate a bundle from job 662067900958232"
   ```

2. **Convert Workspace Code**:
   ```
   "Create bundles for /Workspace/Users/alex/ml-project/"
   ```

3. **Optimize Configuration**:
   ```
   "Convert my streaming job with smaller clusters"
   ```

### What the AI Can Do

- 🔍 **Analyze** existing Databricks jobs and extract configurations
- 📊 **Examine** workspace notebooks for dependencies and patterns
- 🔧 **Generate** optimized bundle configurations with proper cluster sizing
- ✅ **Validate** bundle structures using Databricks CLI
- 📦 **Package** complete bundles ready for deployment
- 🎯 **Optimize** for different environments (dev/staging/prod)

## 🧪 Testing Instructions

### Claude Code SDK Testing

The project includes comprehensive test utilities to validate Claude Code SDK integration and MCP tool connectivity:

#### 1. Simple Connection Test
```bash
# From src/api directory
python simple_test.py
```
This performs a minimal connectivity test with Claude Code SDK.

#### 2. Comprehensive SDK Test
```bash
# From src/api directory  
python test_claude_sdk.py
```
This comprehensive test validates:
- ✅ Claude Code SDK client creation
- ✅ Message streaming functionality
- ✅ MCP tool availability (should show 18+ tools)
- ✅ DAB generation capabilities
- ✅ Real-time response handling

#### 3. Web API Testing
```bash
# Test the health endpoint
curl http://localhost:8000/api/health

# Test chat endpoint with streaming
curl -N -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello! Can you help me generate a DAB?"}'

# Test static file serving
curl http://localhost:8000/static/style.css
```

#### 4. Environment Validation
```bash
# Check your environment setup
python -c "
import os
print('Claude API Key:', '✅' if os.getenv('CLAUDE_API_KEY') else '❌ Missing')
print('Databricks Host:', os.getenv('DATABRICKS_HOST', '❌ Not set'))
print('Databricks Profile:', os.getenv('DATABRICKS_CONFIG_PROFILE', 'DEFAULT'))
"
```

### Expected Test Results

When tests are working correctly, you should see:

1. **Connection Success**: Client creates without errors
2. **Streaming Messages**: Real-time message display with proper content parsing  
3. **MCP Tools**: Discovery of 18+ Databricks-specific tools
4. **Health Check**: All services report healthy status
5. **Frontend Loading**: CSS/JS files serve correctly with proper styling

### Testing Troubleshooting

**Common Issues:**
- **Import Errors**: Ensure you're in the correct directory (`src/api`)
- **API Key Issues**: Verify `CLAUDE_API_KEY` is set and valid
- **MCP Tools Missing**: Check MCP server path in `claude_client.py`
- **Streaming Failures**: Verify network connectivity and API quotas

**Debug Mode:**
```bash
# Enable detailed logging
export LOG_LEVEL=DEBUG
python test_claude_sdk.py
```

## 🏗️ Architecture

### System Overview
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Beautiful     │    │   FastAPI        │    │   Claude Code   │
│   Frontend      │◄──►│   Backend        │◄──►│   SDK + MCP     │
│                 │    │                  │    │                 │
│ • Modern UI     │    │ • SSE Streaming  │    │ • 18+ Tools     │
│ • Real-time     │    │ • Health Checks  │    │ • Databricks    │  
│ • Responsive    │    │ • File Downloads │    │ • Bundle Gen    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Project Structure
```
src/
├── api/                          # FastAPI Backend
│   ├── main.py                   # Main application server with static file serving
│   ├── models.py                 # Pydantic schemas for requests/responses  
│   ├── claude_client.py          # Claude Code SDK integration with MCP
│   ├── chat_handler.py           # Server-Sent Events streaming logic
│   ├── CLAUDE.md                 # AI context for DAB generation expertise
│   ├── requirements.txt          # Python dependencies
│   ├── test_claude_sdk.py        # Comprehensive SDK testing utility
│   ├── simple_test.py            # Minimal connection test
│   └── static/                   # Beautiful Frontend Assets
│       ├── index.html            # Modern chat interface with Databricks branding
│       ├── style.css             # Professional styling with gradients & animations
│       ├── chat.js               # Real-time SSE client with UI interactions
│       └── test.html             # Development testing interface
├── examples/                     # Reference implementations and demos
│   ├── databricks_job_dab_example.py
│   ├── streaming_mode.py
│   └── custom_mcp_example.py
└── README.md                     # This comprehensive documentation
```

## ✨ Beautiful Frontend Features

### Modern Design Elements
- **🎨 Professional Databricks Branding**: Official colors, fonts, and visual identity
- **🌈 Elegant Gradients**: Smooth color transitions and modern visual effects  
- **✨ Smooth Animations**: Subtle transitions and loading states for premium feel
- **📱 Responsive Design**: Perfect on desktop, tablet, and mobile devices
- **🎯 Intuitive UX**: Clean, distraction-free interface focused on conversation

### Advanced UI Components  
- **💬 Real-time Chat**: Server-Sent Events for instant streaming responses
- **📡 Connection Status**: Visual indicators for API and service connectivity
- **📁 File Downloads**: One-click bundle download with progress indicators
- **🔄 Loading States**: Beautiful spinners and progress animations
- **⚡ Fast Performance**: Optimized CSS/JS with minimal load times
- **🎪 Interactive Elements**: Hover effects, button states, and micro-interactions

### User Experience Highlights
```javascript
✅ Instant message streaming with typing indicators
✅ Professional chat bubbles with syntax highlighting  
✅ Auto-scroll with smart positioning
✅ File download notifications with success states
✅ Error handling with user-friendly messages
✅ Keyboard shortcuts and accessibility features
✅ Dark/light theme considerations built-in
```

### Technical Frontend Stack
- **Pure HTML5/CSS3/JavaScript**: No framework dependencies for fast loading
- **Server-Sent Events (SSE)**: Real-time streaming without WebSocket complexity
- **CSS Grid/Flexbox**: Modern responsive layout techniques
- **CSS Custom Properties**: Dynamic theming and maintainable styles
- **Progressive Enhancement**: Works without JavaScript, enhanced with it

## 🛠️ API Endpoints

### Main Endpoints
- `GET /` - Serve web interface
- `POST /api/chat` - Conversational DAB generation (SSE streaming)
- `GET /api/health` - System health and connectivity status
- `GET /api/files/{file_id}` - Download generated bundle files

### Chat API Request Format
```json
{
  "message": "Generate a bundle from job 662067900958232",
  "conversation_id": "optional-uuid-for-context"
}
```

### Response Format (Server-Sent Events)
```javascript
data: {"type": "message", "content": "🚀 Starting job analysis...", "timestamp": "..."}
data: {"type": "tool_use", "tool": "get_job", "status": "starting"}
data: {"type": "file_generated", "filename": "bundle.zip", "download_url": "/api/files/uuid"}
data: {"type": "complete", "conversation_id": "uuid", "files_generated": 1}
```

## 🔧 Configuration

### Databricks Authentication

The application supports multiple authentication methods:

1. **Profile-based** (recommended):
   ```bash
   databricks configure --profile my-profile
   export DATABRICKS_CONFIG_PROFILE=my-profile
   ```

2. **Environment variables**:
   ```bash
   export DATABRICKS_HOST="https://your-workspace.databricks.com"
   export DATABRICKS_TOKEN="your-token"
   ```

3. **CLI default**:
   ```bash
   databricks configure
   # Uses DEFAULT profile automatically
   ```

### MCP Server Integration

The application automatically connects to the Databricks MCP server located at:
- `../../mcp/server/main.py` (relative to api directory)
- Provides 18+ tools for job analysis, bundle generation, and validation

## 🧪 Development

### Project Structure
```bash
# Start development server
uvicorn main:app --reload

# Run health checks
curl http://localhost:8000/api/health

# Test chat endpoint
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, can you help me generate a DAB?"}'
```

### Adding New Features

1. **Backend**: Extend `chat_handler.py` for new conversation patterns
2. **Frontend**: Modify `static/chat.js` for UI enhancements  
3. **AI Context**: Update `CLAUDE.md` for improved DAB generation
4. **Models**: Add new schemas in `models.py`

## 📦 Generated Bundle Structure

The AI creates production-ready bundles with:

```yaml
bundle:
  name: your-bundle-name

variables:
  environment:
    description: Target environment
    default: dev
  catalog:
    description: Unity Catalog name  
    default: main

targets:
  dev:
    default: true
    workspace:
      host: ${DATABRICKS_HOST}
      root_path: /Workspace/Users/${user}/bundles/${bundle.name}

resources:
  jobs:
    your_job:
      name: ${bundle.name}-${var.environment}
      job_clusters: [...]
      tasks: [...]
      
  pipelines:
    your_pipeline:
      name: ${bundle.name}-pipeline
      clusters: [...]
      libraries: [...]
```

## 🚨 Troubleshooting

### Common Issues & Solutions

#### 1. Claude Code SDK Issues
**Problem**: `ImportError` or client creation failures
```bash
# Solutions:
pip install --upgrade claude-code-sdk
export CLAUDE_API_KEY="your-valid-key-here"
python test_claude_sdk.py  # Run diagnostic
```

**Problem**: MCP tools not found (less than 18 tools)
```bash
# Check MCP server path
ls -la ../../mcp/server/main.py
# Verify server permissions and Python path
```

#### 2. Authentication Problems  
**Problem**: Databricks connection refused
```bash
# Solution 1: Profile-based auth (recommended)
databricks configure --profile dev
export DATABRICKS_CONFIG_PROFILE=dev

# Solution 2: Token-based auth
export DATABRICKS_HOST="https://your-workspace.databricks.com"  
export DATABRICKS_TOKEN="dapi-your-token-here"

# Test connection
databricks workspace list
```

#### 3. Frontend Loading Issues
**Problem**: CSS/JS files not loading, styling broken
```bash
# Check static file serving
curl -I http://localhost:8000/static/style.css
curl -I http://localhost:8000/static/chat.js

# Verify server configuration
grep -n "StaticFiles" main.py
```

**Problem**: Chat interface not streaming
- Open browser DevTools → Network tab
- Look for SSE connection to `/api/chat`
- Check for CORS or connection errors
- Verify EventSource is supported

#### 4. Bundle Generation Failures
**Problem**: Job analysis fails  
```bash
# Debug specific job
databricks jobs get --job-id YOUR_JOB_ID
# Check job permissions and workspace access
```

**Problem**: Bundle validation errors
```bash
# Test bundle manually
cd generated_bundle/
databricks bundle validate
# Review error messages for missing configurations
```

### Advanced Debugging

#### Enable Maximum Logging
```bash
export LOG_LEVEL=DEBUG
export CLAUDE_SDK_DEBUG=true
uvicorn main:app --log-level debug --reload
```

#### Test Individual Components
```bash
# Test 1: SDK Connection Only
python simple_test.py

# Test 2: Full Integration
python test_claude_sdk.py

# Test 3: Health Endpoint
curl -s http://localhost:8000/api/health | jq

# Test 4: Static Files
for file in style.css chat.js index.html; do
  echo "Testing $file..."
  curl -sI "http://localhost:8000/static/$file" | head -n1
done
```

### Health Check Diagnostics

Visit `/api/health` for comprehensive system status:

```json
{
  "status": "healthy",
  "timestamp": "2024-09-25T10:30:00Z",
  "services": {
    "claude_sdk": "✅ Connected", 
    "databricks": "✅ Authenticated",
    "mcp_tools": "✅ 18 tools available",
    "static_files": "✅ Serving correctly"
  },
  "environment": {
    "python_version": "3.11.5",
    "claude_sdk_version": "0.0.23",
    "fastapi_version": "0.104.0"
  }
}
```

### Performance Optimization

#### Memory Usage
```bash  
# Monitor memory during streaming
ps aux | grep uvicorn
# If memory grows, restart server periodically
```

#### Connection Limits
```bash
# Check concurrent connections
netstat -an | grep :8000 | wc -l
# Adjust uvicorn worker settings if needed
```

### Emergency Recovery Steps

1. **Complete Reset**:
   ```bash
   # Kill all background processes
   pkill -f uvicorn
   # Clear Python cache
   find . -name "*.pyc" -delete
   find . -name "__pycache__" -delete
   # Restart fresh
   python -m uvicorn main:app --reload
   ```

2. **Environment Reset**:
   ```bash
   # Recreate virtual environment
   deactivate
   rm -rf .venv/
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configuration Reset**:
   ```bash
   # Re-authenticate Databricks
   databricks auth logout
   databricks auth login
   # Verify new auth
   databricks workspace list
   ```

## 📋 Dependencies

### Backend
- `fastapi>=0.104.0` - Web framework
- `uvicorn[standard]>=0.24.0` - ASGI server
- `claude-code-sdk>=0.0.23` - Claude integration
- `pydantic>=2.5.0` - Data validation
- `python-dotenv>=1.0.0` - Environment management

### MCP Integration
- Databricks MCP server (18 tools available)
- Automatic tool discovery and integration
- Real-time workspace interaction

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and test thoroughly
4. Update documentation as needed
5. Submit a pull request

## 📄 License

This project is part of the dabs-copilot application for Databricks Asset Bundle generation.

---

**🎉 Happy Bundle Generating!**

For more information, visit the main project repository or check the implementation plan in `IMPLEMENTATION_PLAN.md`.