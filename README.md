# Databricks Asset Bundles Co-pilot

> **AI-powered Databricks Asset Bundle (DAB) generation made simple**

Transform your existing Databricks jobs and workspace code into properly configured, production-ready Asset Bundles using Claude AI and a comprehensive MCP (Model Context Protocol) server.

## 🎯 What This Tool Does

The DABs Co-pilot automatically generates Databricks Asset Bundles from:
- **Existing Databricks Jobs** → Extract job configuration, analyze notebooks, create optimized bundles
- **Workspace Code** → Scan directories, detect patterns, generate multi-resource bundles

**Key Benefits:**
- ⚡ **Fast Generation** - Convert jobs to DABs in under 2 minutes
- 🎯 **Production Ready** - Generates validated, deployable configurations
- 🔧 **Smart Analysis** - Detects dependencies, cluster requirements, and best practices
- 🖥️ **Easy Interface** - Simple web UI with real-time progress tracking
- ✅ **Built-in Validation** - Automatically validates generated bundles

## 🏗️ Architecture

```
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│   Streamlit Web UI  │    │  Claude Code SDK    │    │   MCP Server        │
│   (Frontend)        │◄──►│  (AI Engine)       │◄──►│   (Databricks API)  │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
         │                           │                           │
         ▼                           ▼                           ▼
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│   User Interaction  │    │   DAB Generation    │    │   18 Databricks     │
│   - Job/Path Input  │    │   - Analysis        │    │   Operations        │
│   - Progress View   │    │   - YAML Creation   │    │   - Jobs/Notebooks  │
│   - YAML Download   │    │   - Validation      │    │   - Workspace/DBFS  │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
```

### Components

- **Frontend**: Streamlit web application with real-time chat interface
- **AI Engine**: Claude Code SDK with 50-turn conversations for complex workflows
- **MCP Server**: 18 specialized tools for Databricks operations (STDIO/HTTP modes)
- **Integration**: Databricks SDK for secure workspace access

## 📁 Project Structure

```
dabs-copilot/
├── src/api/                    # Streamlit Application
│   ├── app.py                  # Main web interface
│   ├── claude_client.py        # Claude Code SDK configuration
│   └── .env                    # Environment variables
├── mcp/                        # MCP Server
│   ├── server/
│   │   ├── main.py             # STDIO entry point
│   │   ├── app.py              # HTTP server (FastAPI)
│   │   ├── tools.py            # Core Databricks operations (9 tools)
│   │   ├── tools_dab.py        # DAB generation tools (6 tools)
│   │   └── tools_workspace.py  # Workspace operations (3 tools)
│   └── scripts/
│       └── deploy.sh           # Databricks Apps deployment
├── README.md                   # This file
└── .env                        # Global environment config
```

## 🔧 Prerequisites

Before getting started, ensure you have:

1. **Python 3.11+** installed
2. **Databricks CLI** configured with a valid profile
3. **Claude API Key** from Anthropic
4. **Claude Code CLI** installed (`npm install -g @anthropic-ai/claude-code`)
5. **Git** for cloning the repository

### Verify Prerequisites

```bash
# Check Python version
python --version

# Verify Databricks CLI
databricks auth show

# Test Claude CLI
claude --help

# Check Node.js (for Claude CLI)
node --version
```

## 🚀 Quick Start Guide

### Step 1: Clone and Setup

```bash
# Clone the repository
git clone https://github.com/your-org/dabs-copilot.git
cd dabs-copilot

# Install Python dependencies
pip install -r requirements.txt

# Install additional dependencies
pip install streamlit databricks-sdk claude-code-sdk python-dotenv
```

### Step 2: Configure Environment

Create and configure your `.env` file:

```bash
# Copy the example environment file
cp .env.example .env

# Edit the configuration
nano .env
```

**Required Environment Variables:**

```bash
# Databricks Configuration
DATABRICKS_CONFIG_PROFILE=your-profile-name
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com

# Claude AI
CLAUDE_API_KEY=sk-ant-api03-your-key-here

# Optional: MCP Server Mode
USE_MCP_HTTP_MODE=false  # Use STDIO mode (recommended)
```

### Step 3: Start the Application

```bash
# Navigate to the API directory
cd src/api

# Start the Streamlit application
streamlit run app.py --server.port 8501
```

### Step 4: Access the Web Interface

Open your browser and navigate to:
```
http://localhost:8501
```

## 💻 Usage Instructions

### Generate DAB from Existing Job

1. **Open the Web Interface** at `http://localhost:8501`
2. **Enter a Databricks Job ID** (e.g., `662067900958232`)
3. **Click "Generate DAB"** or press Enter
4. **Monitor Progress** in real-time as the system:
   - Fetches job configuration
   - Analyzes referenced notebooks
   - Extracts dependencies and parameters
   - Generates optimized bundle YAML
   - Validates the configuration
5. **Download Results** - Use the sidebar to download `databricks.yml`

### Generate DAB from Workspace Code

1. **Enter a Workspace Path** (e.g., `/Workspace/Users/your-name/project/`)
2. **Specify Bundle Name** when prompted
3. **Review Analysis** as the system scans files and detects patterns
4. **Download Bundle** with complete configuration and documentation

### Example Workflow

```
User Input: "Generate a DAB from job 662067900958232"

System Process:
🚀 Starting job analysis...
⚡ Fetching job configuration from Databricks
⚡ Analyzing notebook dependencies (3 found)
⚡ Extracting cluster requirements and libraries
⚡ Generating optimized bundle configuration
⚡ Validating bundle structure
✅ Bundle validation passed - ready for deployment

Output: databricks.yml + README.md ready for download
```

## 🔧 Configuration Options

### MCP Server Modes

The system supports two operation modes:

#### STDIO Mode (Default - Recommended)
```bash
USE_MCP_HTTP_MODE=false
```
- **Advantages**: More reliable, direct Python execution, better error handling
- **Use Case**: Local development and testing

#### HTTP Mode
```bash
USE_MCP_HTTP_MODE=true
MCP_REMOTE_URL=https://your-mcp-server.databricksapps.com
```
- **Advantages**: Remote deployment, shared server access
- **Use Case**: Production deployments with Databricks Apps

### Databricks Authentication

The system supports multiple authentication methods:

1. **CLI Profile** (Recommended for local development)
   ```bash
   DATABRICKS_CONFIG_PROFILE=your-profile
   ```

2. **Environment Variables**
   ```bash
   DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
   DATABRICKS_TOKEN=your-token
   ```

3. **OAuth** (For Databricks Apps deployment)
   - Automatically handled when deployed to Databricks Apps

## 🐛 Troubleshooting

### Common Issues and Solutions

#### Permission Errors
```
Error: Claude requested permissions to use mcp__databricks-mcp__get_job
```
**Solution**: The allowed_tools list has been updated to include all necessary permissions. Restart the application.

#### MCP Server Connection Issues
```
Error: Failed to connect to MCP server
```
**Solutions**:
1. Verify Databricks CLI authentication: `databricks auth show`
2. Check environment variables in `.env` file
3. Try switching to STDIO mode: `USE_MCP_HTTP_MODE=false`

#### Claude API Key Issues
```
Error: CLAUDE_API_KEY not found
```
**Solution**: Ensure your Claude API key is properly set in the `.env` file and starts with `sk-ant-`

#### Bundle Validation Failures
**Solution**: The system automatically detects and fixes common validation issues. Check the validation output in the sidebar for specific error details.

### Getting Help

1. **Check the Logs**: Streamlit logs appear in your terminal
2. **Validate Configuration**: Use `databricks auth show` to verify Databricks access
3. **Test MCP Server**: The system includes built-in health checks
4. **Review Environment**: Ensure all variables in `.env` are correctly set

## 🎯 Advanced Features

### Custom Bundle Templates
The system automatically detects workload patterns:
- **ETL Jobs** → Optimized for data processing workflows
- **ML Training** → MLflow integration and experiment tracking
- **Streaming** → Delta Live Tables and structured streaming
- **Notebooks** → Interactive development workflows

### Production Deployment
Deploy the MCP server to Databricks Apps for team access:
```bash
cd mcp
./scripts/deploy.sh
```

### API Integration
The MCP server exposes 18 specialized tools that can be used programmatically:
- Core operations (9 tools): Jobs, notebooks, SQL, DBFS
- DAB generation (6 tools): Analysis, generation, validation, testing
- Workspace operations (3 tools): Upload, sync, deployment

## 📊 System Requirements

- **Memory**: 4GB RAM minimum, 8GB recommended
- **Storage**: 2GB free space for dependencies and generated bundles
- **Network**: Internet access for Claude API and Databricks workspace
- **Permissions**: Databricks workspace access with job/notebook read permissions

## 🚀 Next Steps: Deploy to Databricks Apps

Take your DABs Co-pilot to production by deploying it as a Databricks App for team-wide access.

### Why Deploy to Databricks Apps?

- **🌐 Team Access** - Share the tool with your entire organization
- **🔐 Built-in Security** - OAuth authentication and workspace permissions
- **☁️ No Infrastructure** - Databricks handles scaling and availability
- **📊 Usage Analytics** - Track adoption and usage patterns
- **🔄 Easy Updates** - Deploy new versions with zero downtime

### Success Metrics

Once deployed, monitor these KPIs:
- **Adoption Rate**: Number of unique users per week
- **Generation Success**: Percentage of successful DAB creations
- **Time Savings**: Average time reduced from manual to automated
- **Error Rate**: Failed generations requiring manual intervention

## 🤝 Contributing

This project follows Databricks best practices for Asset Bundle generation. Contributions are welcome for:
- Additional workload pattern detection
- Enhanced bundle templates
- Improved error handling and validation
- Extended MCP tool capabilities

---

**Ready to get started?** Follow the [Quick Start Guide](#🚀-quick-start-guide) above and transform your Databricks workflows into production-ready Asset Bundles in minutes!

**Ready for production?** Deploy to [Databricks Apps](#🚀-next-steps-deploy-to-databricks-apps) and enable your entire team to generate DABs with AI assistance!