#!/usr/bin/env python3
"""
Databricks MCP Server - Entry point for Claude Code CLI (stdio mode)

Per MCP Builder best practices:
- All logging goes to stderr (not stdout)
- No print() statements (stdout reserved for MCP protocol)
- Clean initialization without internal API access
"""
import sys
import logging
from dotenv import load_dotenv

# Configure logging to stderr (REQUIRED for MCP stdio servers)
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("databricks_mcp")

# Load environment variables
load_dotenv()

# Import MCP server and tool modules to register all tools
from tools import mcp
import tools_dab
import tools_workspace

def main():
    """Run MCP server in stdio mode for Claude Code CLI integration."""
    logger.info("Starting Databricks MCP server (stdio mode)")
    logger.info("Tools registered from: tools.py, tools_dab.py, tools_workspace.py")

    # Run the MCP server (blocks until connection closes)
    mcp.run()

if __name__ == "__main__":
    main()
