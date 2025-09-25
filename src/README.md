# DAB Generator - Databricks Asset Bundle Co-pilot

A modern AI-powered application that generates Databricks Asset Bundles (DAB) from existing jobs or workspace code using Claude Code SDK and MCP integration. Features a clean Streamlit interface for reliable, real-time bundle generation.

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Databricks CLI configured with your workspace
- Claude API key

### Setup & Run
```bash
# Navigate to project
cd dabs-copilot/src/api

# Install dependencies
pip install -r requirements.txt
pip install streamlit

# Set environment variables
export CLAUDE_API_KEY="sk-ant-api03-your-key-here"
export DATABRICKS_CONFIG_PROFILE="your-profile"
export DATABRICKS_HOST="https://your-workspace.databricks.com"

# Start Streamlit UI (Recommended)
streamlit run streamlit_app.py --server.port 8501

# OR Legacy FastAPI UI
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Access
- **🎯 Streamlit UI**: http://localhost:8501 (Primary)
- **⚡ FastAPI UI**: http://localhost:8000 (Legacy)

## 💬 Usage Examples

1. **Generate from Job**: `"Generate a bundle from job 662067900958232"`
2. **Browse Workspace**: `"List workspace files in /Workspace/Users/alex.miller"`
3. **Health Check**: `"Check Databricks MCP server health"`

## ✨ Key Features

### Streamlit Interface
- **🎨 Clean Design**: Professional, distraction-free interface
- **⚡ Real-time Updates**: Live tool execution feedback (`🔧 Using: get_job`)
- **📁 File Management**: Built-in download handling for generated bundles
- **🏥 Health Monitoring**: Environment status and connectivity dashboard
- **🚀 Quick Actions**: One-click buttons for common operations

### AI Capabilities
- 🔍 **Analyze** existing Databricks jobs and extract configurations
- 📊 **Browse** workspace notebooks with MCP integration
- 🔧 **Generate** optimized bundles with proper cluster sizing
- ✅ **Validate** bundle structures using Databricks CLI tools
- 📦 **Create** production-ready bundles for deployment

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Streamlit     │    │   Claude Code    │    │   Databricks    │
│   Frontend      │◄──►│   SDK + MCP      │◄──►│   Workspace     │
│                 │    │                  │    │                 │
│ • Clean UI      │    │ • 18+ MCP Tools  │    │ • Jobs/Pipelines│
│ • Real-time     │    │ • Tool Filtering │    │ • Notebooks     │
│ • File Downloads│    │ • Loop Prevention│    │ • Clusters      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Project Structure
```
src/api/
├── streamlit_app.py          # 🆕 Primary Streamlit UI
├── main.py                   # Legacy FastAPI backend
├── claude_client.py          # Claude Code SDK + MCP integration
├── test_bundle_generation.py # Bundle generation testing
├── simple_test.py            # Basic connectivity test
└── CLAUDE.md                 # AI context for DAB expertise
```

## 🔧 MCP Tool Integration

**Security-First Design:**
- ✅ **18+ Databricks MCP tools** for workspace operations
- ❌ **No built-in tools** (Bash, Grep, Read, Write disabled)
- ✅ **Loop prevention** (Max 10 turns, 20 messages)
- ✅ **Real-time filtering** with clean tool names

```python
# Core MCP Tools Used:
"mcp__databricks-mcp__health"                 # Health checks
"mcp__databricks-mcp__list_jobs"              # Job operations
"mcp__databricks-mcp__get_job"                # Job analysis
"mcp__databricks-mcp__list_notebooks"         # Workspace browsing
"mcp__databricks-mcp__generate_bundle_from_job" # Bundle generation
# ... and 13+ more specialized tools
```

## 🧪 Testing

```bash
# Quick connectivity test
python simple_test.py

# Full bundle generation test
python test_bundle_generation.py

# Environment validation
python -c "
import os
print('Claude API Key:', '✅' if os.getenv('CLAUDE_API_KEY') else '❌ Missing')
print('Databricks Host:', os.getenv('DATABRICKS_HOST', '❌ Not set'))
"
```

**Expected Results:**
- ✅ Claude client connects successfully
- ✅ 18+ Databricks MCP tools discovered
- ✅ No bash/grep tools (security feature)
- ✅ Bundle generation from job IDs works

## 🚨 Troubleshooting

### Common Issues

**Streamlit UI Problems:**
```bash
pip install streamlit
streamlit run streamlit_app.py --server.port 8501 --logger.level debug
lsof -i :8501  # Check port conflicts
```

**MCP Connection Issues:**
```bash
# Check MCP server path (look for debug output: 🐞 Project root...)
ls -la ../../mcp/server/main.py
pwd  # Should be in src/api/
```

**Tool Filtering Problems:**
```bash
grep -A 20 "allowed_tools" claude_client.py
# Should show ONLY mcp__databricks-mcp__* tools
```

### Health Check
```bash
# Test endpoints
curl -s http://localhost:8501/healthz || echo 'Streamlit not running'
curl -s http://localhost:8000/api/health | jq '.status' || echo 'FastAPI not running'
```

## 📦 Generated Bundle Structure

```yaml
bundle:
  name: your-bundle-name
variables:
  environment: { default: dev }
  catalog: { default: main }
targets:
  dev:
    workspace:
      host: ${DATABRICKS_HOST}
      root_path: /Workspace/Users/${user}/bundles/${bundle.name}
resources:
  jobs:
    your_job:
      name: ${bundle.name}-${var.environment}
      job_clusters: [...]
      tasks: [...]
```

## 📋 Dependencies

```
# Core Requirements
streamlit>=1.50.0         # Primary UI framework
fastapi>=0.104.0          # Legacy web framework
claude-code-sdk>=0.0.23   # Claude integration
pydantic>=2.5.0          # Data validation
python-dotenv>=1.0.0     # Environment management
```

## 🎯 What's New

### ✅ Major Improvements
- **Streamlit UI** replaces complex FastAPI + JavaScript frontend
- **MCP-only tools** for security (no bash/grep access)
- **Infinite loop prevention** with conversation limits
- **Real-time progress** with tool call visualization
- **File generation tracking** with download management
- **Professional error handling** and structured results

### 🔄 In Progress
- Workspace code analysis
- Pipeline bundle support
- Advanced cluster optimization

---

**🚀 Quick Start:** `streamlit run streamlit_app.py --server.port 8501`

**🧪 Test:** `python test_bundle_generation.py`

**🏥 Health Check:** http://localhost:8501 → "🏥 Health Check"