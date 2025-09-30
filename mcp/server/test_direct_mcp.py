#!/usr/bin/env python3
"""
Test running MCP server directly without FastAPI wrapper
"""

import os
import sys
import uvicorn
from pathlib import Path

# Add server directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment
from dotenv import load_dotenv
project_root = Path(__file__).parent.parent.parent
dotenv_path = project_root / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)

# Import the MCP server and tools
from tools import mcp as mcp_server
import tools_dab
import tools_workspace

if __name__ == "__main__":
    # Create the HTTP app directly
    app = mcp_server.http_app(transport='streamable-http')

    print(f"Starting direct MCP server on port 8001")
    print(f"Tools registered: {len(mcp_server._tool_manager._tools)}")
    print(f"Streamable HTTP endpoint at: http://localhost:8001/")

    # Run the server
    uvicorn.run(app, host="localhost", port=8001, log_level="info")