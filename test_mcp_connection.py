#!/usr/bin/env python3
"""
Test MCP connection directly without Claude SDK
"""

import requests
import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
project_root = Path(__file__).parent
dotenv_path = project_root / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)
    print("✅ Loaded .env file")

def test_local_mcp():
    """Test local MCP server"""
    print("\n🔍 Testing LOCAL MCP server...")

    # Test health endpoint
    try:
        response = requests.get("http://localhost:8000/health")
        if response.status_code == 200:
            print(f"✅ Health check passed: {response.json()}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Cannot connect to local server: {e}")
        return

    # Test MCP info endpoint
    try:
        response = requests.get("http://localhost:8000/mcp-info")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ MCP Info:")
            print(f"   Server: {data.get('server_name')}")
            print(f"   Tools: {data.get('tools_count')}")
            print(f"   Tool names: {', '.join(data.get('tool_names', []))}")
        else:
            print(f"❌ MCP info failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error getting MCP info: {e}")

    # Test MCP endpoint with JSON-RPC
    try:
        # Initialize request
        init_request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "clientInfo": {"name": "test", "version": "1.0.0"},
                "capabilities": {}
            },
            "id": 1
        }

        response = requests.post(
            "http://localhost:8000/mcp",
            json=init_request,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            print(f"✅ MCP initialize response: {response.text[:200]}")
        else:
            print(f"❌ MCP initialize failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ Error with MCP endpoint: {e}")

def test_remote_mcp():
    """Test remote MCP server (Databricks Apps)"""
    print("\n🔍 Testing REMOTE MCP server...")

    remote_url = os.getenv("MCP_REMOTE_URL", "https://databricks-mcp-server-1444828305810485.aws.databricksapps.com")
    print(f"   URL: {remote_url}")

    # Note: This will require OAuth authentication when deployed
    try:
        response = requests.get(f"{remote_url}/health", timeout=5)
        print(f"   Status: {response.status_code}")
        if response.status_code == 302:
            print("   ⚠️ Requires OAuth authentication (expected for Databricks Apps)")
        elif response.status_code == 200:
            print(f"   ✅ Health: {response.json()}")
    except Exception as e:
        print(f"   ❌ Cannot connect: {e}")

if __name__ == "__main__":
    print("=" * 50)
    print("MCP Server Connection Test")
    print("=" * 50)

    test_local_mcp()
    test_remote_mcp()

    print("\n" + "=" * 50)
    print("Test completed")
    print("=" * 50)