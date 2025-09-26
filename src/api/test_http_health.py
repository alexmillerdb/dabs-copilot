#!/usr/bin/env python3
"""
Test HTTP MCP connection via Claude Code SDK client (Streamlit app config)
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from claude_client import create_chat_client

async def test_health_via_http():
    """Test health check through Claude Code SDK with HTTP MCP connection"""
    print("=" * 60)
    print("Testing MCP Health via HTTP Connection")
    print("=" * 60)

    try:
        client = await create_chat_client()
        print("[INFO] Claude Code SDK client created")
        print(f"[INFO] MCP Server URL: {client.options.mcp_servers['databricks-mcp']['url']}\n")

        print("Connecting to Claude Code SDK...")
        await client.connect()
        print("[INFO] Connected successfully\n")

        print("Sending message to trigger health check...")

        response = await client.query("Please run the health check tool to verify Databricks connection")

        print("\n" + "=" * 60)
        print("Response:")
        print("=" * 60)

        for block in response.content:
            if hasattr(block, 'text'):
                print(block.text)

        return True

    except Exception as e:
        print(f"[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_health_via_http())
    sys.exit(0 if success else 1)