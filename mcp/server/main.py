#!/usr/bin/env python3
"""
Simple MCP server runner for testing with Claude Code CLI
"""

import asyncio
from tools import mcp

async def main():
    """Run MCP server"""
    print("Starting Databricks MCP server...")
    print("Tools available:", len(mcp._tool_manager._tools))
    await mcp.run_stdio_async()

if __name__ == "__main__":
    asyncio.run(main())