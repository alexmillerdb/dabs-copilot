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
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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

# Create MCP server
mcp_server = FastMCP(name=servername)

# Load tools (imports from tools.py will register tools with mcp_server)
try:
    import tools
    logger.info("MCP tools loaded successfully")
except ImportError as e:
    logger.error(f"Failed to load MCP tools: {e}")

# Create MCP ASGI app
mcp_asgi_app = mcp_server.http_app(path='/')

# Create FastAPI app with MCP lifespan
app = FastAPI(
    title='Databricks MCP Server',
    version='0.2.0',
    description='MCP server for Databricks workspace operations and DAB generation',
    lifespan=mcp_asgi_app.lifespan,
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

# Mount MCP server
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
    return {
        "server_name": servername,
        "tools_count": len(mcp_server._tools) if hasattr(mcp_server, '_tools') else 0,
        "environment": os.getenv("ENVIRONMENT", "dev")
    }

# Serve static files if directory exists
static_path = Path("static")
if static_path.exists():
    app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("SERVER_HOST", "localhost")
    port = int(os.getenv("SERVER_PORT", "8000"))
    reload = os.getenv("RELOAD", "true").lower() == "true"
    
    logger.info(f"Starting server on {host}:{port}")
    
    uvicorn.run(
        "app:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )