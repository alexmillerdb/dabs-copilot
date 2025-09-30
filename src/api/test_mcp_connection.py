#!/usr/bin/env python3
"""
Test MCP server connectivity for debugging Databricks Apps deployment
"""

import os
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
project_root = Path(__file__).parent.parent.parent
dotenv_path = project_root / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)
    print("📁 Loaded .env file for testing")

def test_mcp_server():
    """Test connectivity to the MCP server"""
    mcp_server_url = os.getenv(
        "MCP_REMOTE_URL",
        "https://databricks-mcp-server-1444828305810485.aws.databricksapps.com",
    )

    print(f"🧪 Testing MCP server connectivity")
    print(f"URL: {mcp_server_url}")
    print("=" * 50)

    # Test 1: Basic connectivity
    try:
        response = requests.get(mcp_server_url, timeout=10)
        print(f"✅ Server reachable - Status: {response.status_code}")
    except Exception as e:
        print(f"❌ Server unreachable: {e}")
        return False

    # Test 2: MCP endpoint
    mcp_endpoint = f"{mcp_server_url}/mcp"
    try:
        # Try to get OAuth token for auth
        from databricks.sdk import WorkspaceClient
        profile = os.getenv("DATABRICKS_CONFIG_PROFILE", "DEFAULT")

        try:
            workspace_client = WorkspaceClient(profile=profile)
            token = workspace_client.config.token
            headers = {"Authorization": f"Bearer {token}"}

            response = requests.get(mcp_endpoint, headers=headers, timeout=10)
            print(f"✅ MCP endpoint with auth - Status: {response.status_code}")

            if response.status_code == 200:
                print("🎉 MCP server is working correctly!")
            else:
                print(f"⚠️ Unexpected status code: {response.status_code}")
                print(f"Response: {response.text[:200]}")

        except Exception as auth_e:
            print(f"❌ Auth failed: {auth_e}")

            # Try without auth
            response = requests.get(mcp_endpoint, timeout=10)
            print(f"📡 MCP endpoint without auth - Status: {response.status_code}")

    except Exception as e:
        print(f"❌ MCP endpoint failed: {e}")

    return True

if __name__ == "__main__":
    test_mcp_server()