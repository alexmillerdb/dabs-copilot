#!/usr/bin/env python3
"""
Databricks MCP Server - Following reference implementation pattern
Simple FastAPI + FastMCP integration
"""

import os
import yaml
import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastmcp import FastMCP
from dotenv import load_dotenv
# from mcp.server.fastmcp import FastMCP

# Load environment variables from project root
project_root = Path(__file__).parent.parent.parent
dotenv_path = project_root / ".env"
load_dotenv(dotenv_path)

def load_config():
    """Load configuration from config.yaml"""
    config_path = Path('config.yaml')
    if config_path.exists():
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    return {}

def load_env_config():
    """Load environment-specific configuration"""
    env_config = {}
    for key, value in os.environ.items():
        if key.startswith(('DATABRICKS_', 'SERVER_', 'MCP_', 'LOG_')):
            env_config[key.lower()] = value
    return env_config

# Load configuration
config = load_config()
env_config = load_env_config()

# Get server name from config or environment
servername = config.get('servername', os.getenv('MCP_SERVER_NAME', 'databricks-mcp-server'))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import the MCP server instance from tools.py (same as main.py uses)
try:
    # Import tools modules with proper path
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    # from fastmcp.server.http import create_streamable_http_app

    from tools import mcp as mcp_server
    # Also import DAB tools to register them
    import tools_dab
    # Import workspace tools to register them
    import tools_workspace
    logger.info("MCP tools loaded successfully from tools.py")
except ImportError as e:
    logger.error(f"Failed to load MCP tools: {e}")
    # Fallback: create new instance
    mcp_server = FastMCP(name=servername)

# Create MCP ASGI app for Streamable HTTP transport
# Using streamable-http transport for Claude Code SDK compatibility
mcp_asgi_app = mcp_server.http_app(transport='streamable-http')
# mcp_asgi_app = create_streamable_http_app(mcp_server, path="/")

# Create FastAPI app
app = FastAPI(
    title='Databricks MCP Server',
    version='0.2.0',
    description='MCP server for Databricks workspace operations and DAB generation',
)

# Setup CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "http://localhost:5173",  # Vite dev server
        "https://*.databricks.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount MCP server at /mcp
app.mount('/mcp', mcp_asgi_app)

# Health check endpoint
@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "server_name": servername,
        "version": "0.2.0"
    }

# MCP info endpoint  
@app.get("/mcp-info")
async def mcp_info():
    """MCP server information"""
    tools_count = 0
    tool_names = []
    
    if hasattr(mcp_server, '_tool_manager'):
        tools_count = len(mcp_server._tool_manager._tools)
        tool_names = [tool.name for tool in mcp_server._tool_manager._tools.values()]
    
    return {
        "server_name": servername,
        "tools_count": tools_count,
        "tool_names": tool_names,
        "environment": os.getenv("ENVIRONMENT", "dev"),
        "mcp_endpoint": "/mcp",
        "databricks_apps_mode": is_databricks_apps_environment()
    }

# App URL discovery endpoint for Databricks Apps
@app.get("/app-info")
async def app_info():
    """Databricks Apps information"""
    return {
        "app_name": servername,
        "version": "0.2.0",
        "mcp_endpoint": "/mcp",
        "health_endpoint": "/health",
        "environment": os.getenv("ENVIRONMENT", "dev"),
        "databricks_apps": is_databricks_apps_environment(),
        "host": os.getenv("SERVER_HOST", "localhost"),
        "port": int(os.getenv("SERVER_PORT", "8000"))
    }

def is_databricks_apps_environment():
    """Detect if running in Databricks Apps"""
    return os.getenv("DATABRICKS_RUNTIME_VERSION") is not None

# Serve static files if directory exists
static_path = Path("static")
if static_path.exists():
    app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    
    # Use 0.0.0.0 for Databricks Apps, localhost for local dev
    default_host = "0.0.0.0" if is_databricks_apps_environment() else "localhost"
    host = os.getenv("SERVER_HOST", default_host)
    port = int(os.getenv("SERVER_PORT", "8000"))
    
    # Disable reload in production/Databricks Apps
    default_reload = "false" if is_databricks_apps_environment() else "true"
    reload = os.getenv("RELOAD", default_reload).lower() == "true"
    
    logger.info(f"Starting server on {host}:{port}")
    logger.info(f"Databricks Apps mode: {is_databricks_apps_environment()}")
    logger.info(f"MCP streamable HTTP endpoint will be available at: /mcp")
    
    uvicorn.run(
        "app:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )