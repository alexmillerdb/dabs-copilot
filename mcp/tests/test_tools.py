#!/usr/bin/env python3
"""
Test MCP tools directly
"""

import asyncio
import sys
from pathlib import Path

# Add server directory to path for imports
server_dir = Path(__file__).parent.parent / "server"
sys.path.insert(0, str(server_dir))

from tools import mcp

async def test_health():
    """Test health check tool"""
    print("Testing health tool...")
    result = await mcp.call_tool("health", {})
    print("Health result:", result)

async def test_list_jobs():
    """Test list jobs tool"""
    print("\nTesting list_jobs tool...")
    result = await mcp.call_tool("list_jobs", {"limit": 5})
    print("List jobs result:", result)

async def test_list_notebooks():
    """Test list notebooks tool"""
    print("\nTesting list_notebooks tool...")
    result = await mcp.call_tool("list_notebooks", {"path": "/Users"})
    print("List notebooks result:", result)

async def main():
    """Run tests"""
    print("Testing Databricks MCP tools...")
    
    try:
        await test_health()
        await test_list_jobs() 
        await test_list_notebooks()
        print("\n✅ All tests completed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())