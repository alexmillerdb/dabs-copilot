#!/usr/bin/env python3
"""
Phase 1 Complete Test: Verify HTTP MCP connection to remote Databricks Apps server
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src' / 'api'))

from claude_client import create_chat_client

async def test_phase1_http_connection():
    """Test that Claude Code SDK can connect to remote MCP server via HTTP"""
    print("\n" + "=" * 70)
    print("PHASE 1 COMPLETE TEST: HTTP MCP Connection to Databricks Apps")
    print("=" * 70 + "\n")

    try:
        print("[1/3] Creating Claude Code SDK client...")
        client = await create_chat_client()
        print(f"  ✓ Client created")
        print(f"  ✓ MCP Server: {client.options.mcp_servers['databricks-mcp']['url']}\n")

        print("[2/3] Connecting to remote MCP server...")
        await client.connect()
        print("  ✓ Connected successfully\n")

        print("[3/3] Testing health check via remote MCP...")
        response = await client.query("Run the health tool to check Databricks connection")

        if response and hasattr(response, 'content'):
            print("  ✓ Response received from remote MCP server\n")
            print("=" * 70)
            print("RESPONSE:")
            print("=" * 70)
            for block in response.content:
                if hasattr(block, 'text'):
                    print(block.text)
            print("\n" + "=" * 70)
            print("✅ PHASE 1 COMPLETE: HTTP MCP connection successful!")
            print("=" * 70)
            return True
        else:
            print("  ✗ No response from remote MCP server")
            return False

    except Exception as e:
        print(f"\n❌ PHASE 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if client:
            await client.disconnect()

if __name__ == "__main__":
    success = asyncio.run(test_phase1_http_connection())
    sys.exit(0 if success else 1)