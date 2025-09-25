#!/usr/bin/env python3
"""
Databricks MCP Server - Main entry point for Claude Code CLI
Combines Phase 1 (core tools) and Phase 2 (DAB generation) tools
"""

import asyncio
import logging
from tools import mcp
from dotenv import load_dotenv

# Import DAB tools to register them with the MCP server
# This adds analyze_notebook, generate_bundle, validate_bundle, create_tests
import tools_dab

# Import workspace tools to register them with the MCP server
# This adds upload_bundle, run_bundle_command, sync_workspace_to_local
import tools_workspace

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

async def main():
    """Run MCP server with all available tools"""
    tool_count = len(mcp._tool_manager._tools)
    logger.info(f"Starting Databricks MCP server with {tool_count} tools")
    
    # List available tools for debugging
    tool_names = [tool.name for tool in mcp._tool_manager._tools.values()]
    logger.info(f"Available tools: {', '.join(tool_names)}")
    
    print(f"Databricks MCP Server started with {tool_count} tools")
    print("Ready for Claude Code CLI connections...")
    
    await mcp.run_stdio_async()

if __name__ == "__main__":
    asyncio.run(main())