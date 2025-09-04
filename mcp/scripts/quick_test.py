#!/usr/bin/env python3
"""
Quick test script for Databricks Apps MCP server
"""

import asyncio
import json
from databricks_apps_utils import DatabricksAppsManager

async def quick_test():
    """Quick test of the deployed MCP server"""
    print("🧪 Quick MCP Server Test")
    print("=" * 40)
    
    manager = DatabricksAppsManager()
    
    # Get URLs
    app_url = manager.get_app_url()
    mcp_url = manager.get_mcp_endpoint_url()
    
    print(f"🌐 App URL: {app_url}")
    print(f"🔗 MCP Endpoint: {mcp_url}")
    
    if not mcp_url:
        print("❌ Could not get MCP endpoint URL")
        return
    
    # Test connection
    print("\n🔌 Testing MCP connection...")
    result = await manager.test_mcp_connection()
    
    if result["success"]:
        print(f"✅ Connection successful!")
        print(f"📊 Found {result['tools_count']} tools: {', '.join(result['tools'])}")
        
        # Test health tool
        print("\n💓 Testing health tool...")
        health_result = await manager.test_mcp_tool("health")
        if health_result["success"]:
            print("✅ Health check passed!")
            # Parse the JSON result to show key info
            try:
                health_data = json.loads(health_result["result"])
                if health_data.get("success"):
                    print(f"   Server: {health_data['data'].get('server_status', 'unknown')}")
                    print(f"   Databricks: {health_data['data'].get('databricks_connection', 'unknown')}")
            except:
                print("   Raw result:", health_result["result"][:100] + "...")
        else:
            print(f"❌ Health check failed: {health_result.get('error')}")
    else:
        print(f"❌ Connection failed: {result.get('error')}")
    
    print("\n🎯 Test complete!")

if __name__ == "__main__":
    asyncio.run(quick_test())
