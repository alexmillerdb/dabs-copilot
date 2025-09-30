#!/usr/bin/env python3
"""
Test deployed MCP server connectivity
"""

import asyncio
import os
import subprocess
import json
from pathlib import Path
from dotenv import load_dotenv
from claude_code_sdk import ClaudeCodeOptions, ClaudeSDKClient

# Load environment
project_root = Path(__file__).parent
dotenv_path = project_root / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)

def get_oauth_token():
    """Get OAuth token for authentication"""
    try:
        result = subprocess.run(
            ["databricks", "auth", "token", "--profile", "aws-apps"],
            capture_output=True,
            text=True,
            check=True
        )
        token_data = json.loads(result.stdout)
        return token_data["access_token"]
    except Exception as e:
        print(f"Failed to get OAuth token: {e}")
        return None

async def test_deployed_mcp():
    """Test deployed MCP server"""

    print("🔍 Testing deployed MCP server...")

    oauth_token = get_oauth_token()
    if not oauth_token:
        print("❌ Could not get OAuth token")
        return

    # Configure to connect to deployed server
    options = ClaudeCodeOptions(
        model="claude-sonnet-4-20250514",
        cwd=str(project_root),
        mcp_servers={
            "databricks-mcp": {
                "type": "http",
                "url": "https://databricks-mcp-server-1444828305810485.aws.databricksapps.com/mcp",
                "headers": {
                    "Authorization": f"Bearer {oauth_token}"
                }
            }
        },
        allowed_tools=["mcp__databricks-mcp__*"],
        max_turns=3,
        system_prompt="Test MCP connectivity and list available tools."
    )

    print(f"🔌 Testing MCP server at: https://databricks-mcp-server-1444828305810485.aws.databricksapps.com/mcp")
    print(f"🔐 Using OAuth authentication")

    try:
        client = ClaudeSDKClient(options=options)

        async with client:
            await client.query("Test the MCP connection. Can you list the available databricks MCP tools?")

            message_count = 0
            found_tools = []

            async for msg in client.receive_messages():
                message_count += 1
                print(f"📨 Message {message_count}: {type(msg).__name__}")

                if hasattr(msg, 'content'):
                    for block in msg.content:
                        if hasattr(block, 'text'):
                            text = block.text[:200]
                            print(f"   Text: {text}...")
                        elif hasattr(block, 'name'):
                            if block.name.startswith('mcp__databricks-mcp__'):
                                found_tools.append(block.name)
                                print(f"   🔧 Tool found: {block.name}")

                if message_count > 10:
                    break

        if found_tools:
            print(f"\n✅ Connection successful! Found {len(found_tools)} MCP tools:")
            for tool in found_tools:
                print(f"   - {tool}")
        else:
            print("\n⚠️ Connection established but no MCP tools found")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_deployed_mcp())