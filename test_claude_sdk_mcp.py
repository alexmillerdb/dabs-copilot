#!/usr/bin/env python3
"""
Test Claude SDK connection to MCP server
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from claude_code_sdk import ClaudeCodeOptions, ClaudeSDKClient

# Load environment
project_root = Path(__file__).parent
dotenv_path = project_root / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)

async def test_mcp_connection():
    """Test MCP connection with Claude SDK"""

    # Test with direct MCP server on port 8001
    options = ClaudeCodeOptions(
        model="claude-sonnet-4-20250514",
        cwd=str(project_root),
        mcp_servers={
            "databricks-mcp": {
                "type": "http",
                "url": "http://localhost:8000/mcp",  # FastMCP streamable HTTP endpoint
                "headers": {}
            }
        },
        allowed_tools=["mcp__databricks-mcp__*"],
        max_turns=3,
        system_prompt="List all available MCP tools."
    )

    print("🔍 Testing Claude SDK with direct MCP server on port 8001...")

    try:
        client = ClaudeSDKClient(options=options)

        async with client:
            await client.query("What MCP tools are available? List all mcp__databricks-mcp__ tools.")

            message_count = 0
            async for msg in client.receive_messages():
                message_count += 1
                print(f"📨 Message {message_count}: {type(msg).__name__}")

                if hasattr(msg, 'content'):
                    for block in msg.content:
                        if hasattr(block, 'text'):
                            print(f"   Text: {block.text[:200]}...")
                        elif hasattr(block, 'name'):
                            print(f"   🔧 Tool found: {block.name}")

                if message_count > 5:
                    break

        print("\n✅ Connection successful!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mcp_connection())