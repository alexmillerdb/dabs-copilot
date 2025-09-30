#!/usr/bin/env python3
"""
Test script for Phase 1.1: Validate HTTP MCP connection to remote server
Tests configuration loading and basic connectivity
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from claude_client import build_chat_options, create_chat_client

async def test_configuration_loading():
    """Test 1: Verify configuration loads without errors"""
    print("=" * 60)
    print("TEST 1: Configuration Loading")
    print("=" * 60)

    try:
        options = build_chat_options()
        print("[PASS] Configuration loaded successfully")
        print(f"\nMCP Server Config:")
        print(f"  - Server Name: databricks-mcp")
        print(f"  - Command Type: {options.mcp_servers['databricks-mcp']['command']}")
        print(f"  - URL: {options.mcp_servers['databricks-mcp']['url']}")
        print(f"  - Auth Type: {options.mcp_servers['databricks-mcp']['auth']['type']}")
        print(f"\nAllowed Tools: {len(options.allowed_tools)} tools")
        return True
    except Exception as e:
        print(f"[FAIL] Configuration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_client_initialization():
    """Test 2: Verify Claude Code SDK client initializes with HTTP config"""
    print("\n" + "=" * 60)
    print("TEST 2: Client Initialization")
    print("=" * 60)

    try:
        client = await create_chat_client()
        print("[PASS] Claude Code SDK client initialized successfully")
        print(f"\nClient Info:")
        print(f"  - Model: {client.options.model}")
        print(f"  - Max Turns: {client.options.max_turns}")
        print(f"  - Working Directory: {client.options.cwd}")
        return True
    except Exception as e:
        print(f"[FAIL] Client initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all Phase 1.1 tests"""
    print("\nPhase 1.1: HTTP MCP Connection Configuration Test\n")

    results = []

    results.append(await test_configuration_loading())

    if results[0]:
        results.append(await test_client_initialization())

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Configuration Loading: {'PASS' if results[0] else 'FAIL'}")
    if len(results) > 1:
        print(f"Client Initialization: {'PASS' if results[1] else 'FAIL'}")

    success = all(results)
    print(f"\n{'Phase 1.1 Complete - Ready for Phase 1.2' if success else 'Phase 1.1 Failed - Fix errors before proceeding'}")

    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)