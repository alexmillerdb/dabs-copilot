#!/usr/bin/env python3
"""
Simple script to list workspace files using MCP Databricks tools
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent / "src/api"))

from claude_code_sdk import AssistantMessage, TextBlock, ToolUseBlock, ToolResultBlock, ResultMessage
from claude_client import create_chat_client

# Load environment variables
dotenv_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path)

async def list_workspace_files():
    """List files in the specified Databricks workspace path"""
    workspace_path = "/Users/alex.miller@databricks.com"

    print(f"🔍 Listing files in Databricks workspace: {workspace_path}")
    print("=" * 60)

    # Check environment
    claude_key = os.getenv("CLAUDE_API_KEY")
    databricks_host = os.getenv("DATABRICKS_HOST")

    print(f"✓ Claude API Key: {'Configured' if claude_key else '❌ Missing'}")
    print(f"✓ Databricks Host: {databricks_host if databricks_host else '❌ Missing'}")
    print()

    if not claude_key:
        print("❌ Error: CLAUDE_API_KEY not configured")
        return

    try:
        client = await create_chat_client()
        print("✅ Claude client created successfully")
        print()

        async with client:
            # Request to list workspace files
            query = f"Use the MCP Databricks tools to list all files and notebooks in the workspace path: {workspace_path}"
            print(f"📤 Sending query: {query}")
            print("-" * 40)

            await client.query(query)

            message_count = 0
            workspace_files = []

            async for msg in client.receive_messages():
                message_count += 1

                if isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            text = block.text
                            if text and not text.startswith('{') and not text.startswith('data:'):
                                print(f"📝 {text}")
                        elif isinstance(block, ToolUseBlock):
                            tool_name = block.name.replace('mcp__databricks-mcp__', '')
                            print(f"🔧 Using tool: {tool_name}")
                            if hasattr(block, 'input') and isinstance(block.input, dict):
                                for key, value in block.input.items():
                                    print(f"   - {key}: {value}")

                elif hasattr(msg, 'content'):
                    for block in msg.content:
                        if isinstance(block, ToolResultBlock):
                            content = ""
                            if hasattr(block.content, 'text'):
                                content = block.content.text
                            elif isinstance(block.content, str):
                                content = block.content
                            elif isinstance(block.content, list):
                                for item in block.content:
                                    if hasattr(item, 'text'):
                                        content += item.text

                            if content:
                                workspace_files.append(content)
                                print(f"✓ Workspace content:\n{content}")

                # Stop when we get a result or after reasonable number of messages
                if isinstance(msg, ResultMessage) or message_count > 15:
                    break

            print()
            print("=" * 60)
            print("✅ Workspace scan complete!")

            if workspace_files:
                print(f"📁 Found {len(workspace_files)} file/directory entries")
            else:
                print("📭 No files found or unable to access workspace")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Starting Workspace File Listing")
    print()
    asyncio.run(list_workspace_files())