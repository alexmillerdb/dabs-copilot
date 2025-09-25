#!/usr/bin/env python3
"""
Test script for bundle generation with proper MCP integration
Tests the full flow from job ID to bundle generation
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from claude_code_sdk import (
    AssistantMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
    ResultMessage,
)

# Load environment variables
project_root = Path(__file__).parent.parent.parent
dotenv_path = project_root / ".env"
load_dotenv(dotenv_path)

from claude_client import create_chat_client

async def test_bundle_generation():
    """Test bundle generation from a job ID"""
    print("🧪 Testing Bundle Generation Flow")
    print("=" * 50)

    # Check environment
    claude_key = os.getenv("CLAUDE_API_KEY")
    databricks_host = os.getenv("DATABRICKS_HOST")
    databricks_profile = os.getenv("DATABRICKS_CONFIG_PROFILE")

    print(f"✓ Claude API Key: {'Configured' if claude_key else '❌ Missing'}")
    print(f"✓ Databricks Host: {databricks_host if databricks_host else '❌ Missing'}")
    print(f"✓ Databricks Profile: {databricks_profile if databricks_profile else 'DEFAULT'}")
    print()

    if not claude_key:
        print("❌ Error: CLAUDE_API_KEY not configured")
        return

    try:
        client = await create_chat_client()
        print("✅ Claude client created successfully")
        print()

        async with client:
            # Test message for bundle generation
            test_message = "Generate a bundle from job 662067900958232"
            print(f"📤 Sending: {test_message}")
            print("-" * 40)

            await client.query(test_message)

            # Track responses
            message_count = 0
            tool_calls = []
            text_responses = []
            tool_results = []

            async for msg in client.receive_messages():
                message_count += 1

                if isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            # Filter out raw JSON/SSE strings
                            text = block.text
                            if text and not text.startswith('{') and not text.startswith('data:'):
                                text_responses.append(text)
                                print(f"📝 Assistant: {text[:200]}{'...' if len(text) > 200 else ''}")
                        elif isinstance(block, ToolUseBlock):
                            tool_name = block.name.replace('mcp__databricks-mcp__', '')
                            tool_calls.append(tool_name)
                            print(f"🔧 Tool Call: {tool_name}")
                            if isinstance(block.input, dict):
                                for key, value in block.input.items():
                                    print(f"   - {key}: {value}")

                # Track tool results
                elif hasattr(msg, 'content'):
                    for block in msg.content:
                        if isinstance(block, ToolResultBlock):
                            # Extract tool result content
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
                                tool_results.append(content[:100])
                                print(f"✓ Tool Result: {content[:100]}...")

                # Check for completion
                if isinstance(msg, ResultMessage):
                    print()
                    print("=" * 50)
                    print("✅ Conversation Complete!")
                    break

                # Prevent infinite loops
                if message_count > 30:
                    print("⚠️ Stopping after 30 messages")
                    break

            # Summary
            print()
            print("📊 Summary:")
            print(f"  - Total messages: {message_count}")
            print(f"  - Tool calls: {len(tool_calls)}")
            print(f"  - Tools used: {', '.join(set(tool_calls)) if tool_calls else 'None'}")
            print(f"  - Text responses: {len(text_responses)}")

            # Check for common issues
            print()
            print("🔍 Diagnostics:")
            if not tool_calls:
                print("  ⚠️ No MCP tools were called - check MCP server is running")
            if 'generate_bundle_from_job' not in tool_calls and 'get_job' not in tool_calls:
                print("  ⚠️ Expected job-related tools were not called")
            if any('error' in r.lower() for r in tool_results):
                print("  ❌ Errors detected in tool results")
            else:
                print("  ✅ No obvious errors detected")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

async def test_simple_health_check():
    """Test a simple health check with MCP"""
    print("\n🧪 Testing MCP Health Check")
    print("=" * 50)

    try:
        client = await create_chat_client()

        async with client:
            await client.query("Check the Databricks MCP server health")

            message_count = 0
            async for msg in client.receive_messages():
                message_count += 1

                if isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, ToolUseBlock) and 'health' in block.name:
                            print("✅ Health check tool called successfully")
                            return True

                if message_count > 10 or isinstance(msg, ResultMessage):
                    break

            print("⚠️ Health check tool was not called")
            return False

    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Databricks Bundle Generation Tests")
    print()

    # Run tests
    asyncio.run(test_simple_health_check())
    print()
    asyncio.run(test_bundle_generation())