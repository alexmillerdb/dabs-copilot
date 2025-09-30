#!/usr/bin/env python3
"""
Test OAuth authentication for Databricks Apps
Verifies the OAuth token flow from Streamlit context to MCP server
"""

import os
import sys
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch
from dotenv import load_dotenv

# Load environment
project_root = Path(__file__).parent.parent.parent
dotenv_path = project_root / ".env"
load_dotenv(dotenv_path)

# Import claude_client
from claude_client import create_chat_client, get_databricks_token, build_chat_options

async def test_oauth_authentication():
    """Test OAuth authentication flow"""

    print("🧪 Testing OAuth Authentication for Databricks Apps")
    print("=" * 50)

    # Test 1: Profile-based authentication (local development)
    print("\n1️⃣ Testing profile-based authentication:")
    try:
        token = get_databricks_token()
        print(f"   ✅ Token obtained: {token[:20]}..." if token else "   ❌ No token obtained")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 2: OAuth token pass-through
    print("\n2️⃣ Testing OAuth token pass-through:")
    mock_oauth_token = "mock-oauth-token-from-databricks-apps"
    try:
        token = get_databricks_token(token=mock_oauth_token)
        assert token == mock_oauth_token, "Token pass-through failed"
        print(f"   ✅ OAuth token correctly passed through")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 3: Build chat options with OAuth token
    print("\n3️⃣ Testing chat options with OAuth token:")
    try:
        options = build_chat_options(oauth_token=mock_oauth_token)
        mcp_config = options.mcp_servers.get("databricks-mcp")
        assert mcp_config is not None, "MCP config not found"
        assert mcp_config.get("auth", {}).get("token") == mock_oauth_token, "OAuth token not in config"
        print(f"   ✅ Chat options correctly configured with OAuth token")
        print(f"   📍 MCP URL: {mcp_config.get('url')}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 4: Create client with OAuth token
    print("\n4️⃣ Testing client creation with OAuth token:")
    try:
        client = await create_chat_client(oauth_token=mock_oauth_token)
        print(f"   ✅ Client created successfully")
        print(f"   📊 Model: {client.options.model}")
        print(f"   🛠️ Allowed tools: {len(client.options.allowed_tools)} tools")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 5: Simulate Databricks Apps context
    print("\n5️⃣ Simulating Databricks Apps context:")
    with patch('streamlit.context') as mock_context:
        mock_context.headers = {"x-forwarded-access-token": "databricks-apps-oauth-token"}

        # Import after patching to test Streamlit context detection
        from app import get_oauth_token

        try:
            token = get_oauth_token()
            if token:
                print(f"   ✅ OAuth token extracted from Streamlit context")
                print(f"   🔑 Token: {token[:30]}...")
            else:
                print(f"   ⚠️ No OAuth token found (expected in non-Apps environment)")
        except Exception as e:
            print(f"   ❌ Error: {e}")

    print("\n" + "=" * 50)
    print("✅ OAuth authentication tests completed")
    print("\nNext steps:")
    print("1. Deploy to Databricks Apps to test real OAuth flow")
    print("2. Verify MCP server accepts OAuth tokens")
    print("3. Test end-to-end workflow with authenticated requests")

if __name__ == "__main__":
    asyncio.run(test_oauth_authentication())