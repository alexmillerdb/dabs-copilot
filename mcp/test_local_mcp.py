#!/usr/bin/env python3
"""
Simple script to test the local MCP server in different modes
"""

import asyncio
import sys
from pathlib import Path

# Add server directory to path for imports
server_dir = Path(__file__).parent / "server"
sys.path.insert(0, str(server_dir))

from tools import mcp

async def test_mcp_tools():
    """Test MCP tools directly (fastest method)"""
    print("🧪 Testing MCP Tools Directly")
    print("=" * 50)
    
    # Test health
    print("💓 Health Check:")
    result = await mcp.call_tool("health", {})
    print(f"   Status: {'✅ PASS' if result[1].get('result') else '❌ FAIL'}")
    
    # Test list jobs
    print("\n📋 List Jobs (limit 3):")
    result = await mcp.call_tool("list_jobs", {"limit": 3})
    print(f"   Status: {'✅ PASS' if result[1].get('result') else '❌ FAIL'}")
    
    # Test list warehouses
    print("\n🏭 List Warehouses:")
    result = await mcp.call_tool("list_warehouses", {})
    print(f"   Status: {'✅ PASS' if result[1].get('result') else '❌ FAIL'}")
    
    # Test list notebooks
    print("\n📓 List Notebooks:")
    result = await mcp.call_tool("list_notebooks", {"path": "/Users", "limit": 5})
    print(f"   Status: {'✅ PASS' if result[1].get('result') else '❌ FAIL'}")
    
    print("\n✅ Direct tool testing complete!")

async def run_mcp_stdio():
    """Run MCP server in STDIO mode (for Claude Desktop)"""
    print("\n🚀 Starting MCP Server in STDIO Mode")
    print("=" * 50)
    print("This mode is used by Claude Desktop to connect to MCP servers.")
    print("The server will wait for JSON-RPC messages on stdin...")
    print("Press Ctrl+C to stop.\n")
    
    try:
        await mcp.run_stdio_async()
    except KeyboardInterrupt:
        print("\n👋 MCP server stopped.")

def show_usage():
    """Show usage information"""
    print("🔧 Local MCP Server Testing")
    print("=" * 50)
    print("Usage: python test_local_mcp.py [mode]")
    print("")
    print("Modes:")
    print("  test    - Test MCP tools directly (default)")
    print("  stdio   - Run MCP server in STDIO mode")
    print("  help    - Show this help message")
    print("")
    print("Examples:")
    print("  python test_local_mcp.py test")
    print("  python test_local_mcp.py stdio")
    print("")
    print("For Claude Desktop integration, use 'stdio' mode.")

async def main():
    """Main function"""
    mode = sys.argv[1] if len(sys.argv) > 1 else "test"
    
    if mode == "help":
        show_usage()
        return
    elif mode == "test":
        await test_mcp_tools()
    elif mode == "stdio":
        await run_mcp_stdio()
    else:
        print(f"❌ Unknown mode: {mode}")
        show_usage()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
