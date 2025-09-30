#!/usr/bin/env python3
"""
Databricks MCP Server - Direct Streamable HTTP version
Simple direct server without FastAPI wrapper
"""

import os
import logging
from pathlib import Path
import uvicorn
from dotenv import load_dotenv

# Load environment variables from project root
project_root = Path(__file__).parent.parent.parent
dotenv_path = project_root / ".env"
load_dotenv(dotenv_path)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import the MCP server instance and tools
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools import mcp as mcp_server
# Import DAB tools to register them
import tools_dab
# Import workspace tools to register them
import tools_workspace

logger.info("MCP tools loaded successfully")
logger.info(f"Total tools registered: {len(mcp_server._tool_manager._tools)}")

def is_databricks_apps_environment():
    """Detect if running in Databricks Apps"""
    return os.getenv("DATABRICKS_RUNTIME_VERSION") is not None

if __name__ == "__main__":
    # Create the streamable HTTP app
    app = mcp_server.http_app(transport='streamable-http')

    # Use 0.0.0.0 for Databricks Apps, localhost for local dev
    default_host = "0.0.0.0" if is_databricks_apps_environment() else "localhost"
    host = os.getenv("SERVER_HOST", default_host)
    port = int(os.getenv("SERVER_PORT", "8000"))

    # Disable reload in production/Databricks Apps
    default_reload = "false" if is_databricks_apps_environment() else "false"
    reload = os.getenv("RELOAD", default_reload).lower() == "true"

    logger.info(f"Starting MCP server on {host}:{port}")
    logger.info(f"Databricks Apps mode: {is_databricks_apps_environment()}")
    logger.info(f"MCP streamable HTTP endpoint available at: http://{host}:{port}/")
    logger.info(f"Tools available: {[tool.name for tool in mcp_server._tool_manager._tools.values()]}")

    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )