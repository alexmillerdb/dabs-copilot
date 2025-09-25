#!/usr/bin/env python3
"""
Test script for Claude Code SDK integration
Run this to debug streaming responses and MCP tool connectivity
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
project_root = Path(__file__).parent.parent.parent
dotenv_path = project_root / ".env"
load_dotenv(dotenv_path)

try:
    from claude_client import create_chat_client
    from models import ChatRequest
except ImportError as e:
    print(f"Import error: {e}")
    exit(1)

async def test_claude_connection():
    """Test basic Claude Code SDK connection"""
    print("🔧 Testing Claude Code SDK Connection...")
    print(f"📁 Working directory: {os.getcwd()}")
    print(f"🔐 Claude API Key set: {'Yes' if os.getenv('CLAUDE_API_KEY') else 'No'}")
    print(f"🏢 Databricks Host: {os.getenv('DATABRICKS_HOST', 'Not set')}")
    print(f"👤 Databricks Profile: {os.getenv('DATABRICKS_CONFIG_PROFILE', 'Not set')}")
    print()
    
    try:
        client = await create_chat_client()
        print("✅ Claude SDK client created successfully")
        return client
    except Exception as e:
        print(f"❌ Failed to create Claude SDK client: {e}")
        return None

async def test_simple_message(client, message: str = "Hello! Can you help me?"):
    """Test a simple message to Claude"""
    print(f"💬 Testing message: '{message}'")
    print("📡 Streaming response:")
    print("-" * 50)
    
    try:
        async with client:
            # Send the query
            await client.query(message)
            
            # Receive and process messages
            async for msg in client.receive_messages():
                print(f"Message type: {type(msg).__name__}")
                print(f"Raw message: {repr(msg)}")
                
                # Try to extract content
                if hasattr(msg, 'content'):
                    print(f"Content blocks: {len(msg.content) if msg.content else 0}")
                    if msg.content:
                        for i, block in enumerate(msg.content):
                            print(f"  Block {i}: {type(block).__name__}")
                            if hasattr(block, 'text'):
                                print(f"    Text: {block.text[:100]}...")
                            elif hasattr(block, 'name'):
                                print(f"    Tool: {block.name}")
                                if hasattr(block, 'input'):
                                    print(f"    Input: {block.input}")
                
                print("-" * 30)
                
                # Break after a reasonable number of messages for testing
                if hasattr(msg, '__class__') and 'Result' in msg.__class__.__name__:
                    print("✅ Conversation completed")
                    break
            
    except Exception as e:
        print(f"❌ Error during streaming: {e}")
        import traceback
        traceback.print_exc()

async def test_dab_generation_message(client):
    """Test a DAB-specific message"""
    message = "Generate a simple bundle for testing - no real job needed, just a basic structure"
    print(f"🏗️ Testing DAB generation: '{message}'")
    print("📡 Streaming response:")
    print("-" * 50)
    
    try:
        async with client:
            await client.query(message)
            async for msg in client.receive_messages():
                print(f"DAB Message: {type(msg).__name__}")
                if hasattr(msg, 'content') and msg.content:
                    for block in msg.content:
                        if hasattr(block, 'text'):
                            print(f"Text: {block.text[:200]}...")
                        elif hasattr(block, 'name'):
                            print(f"Tool used: {block.name}")
                print("-" * 20)
                if 'Result' in type(msg).__name__:
                    break
            
    except Exception as e:
        print(f"❌ Error during DAB test: {e}")
        import traceback
        traceback.print_exc()

async def test_mcp_tools(client):
    """Test MCP tool availability"""
    message = "What MCP tools do you have access to?"
    print(f"🛠️ Testing MCP tools: '{message}'")
    print("📡 Streaming response:")
    print("-" * 50)
    
    try:
        async with client:
            await client.query(message)
            async for msg in client.receive_messages():
                print(f"MCP Message: {type(msg).__name__}")
                if hasattr(msg, 'content') and msg.content:
                    for block in msg.content:
                        if hasattr(block, 'text'):
                            print(f"Text: {block.text[:200]}...")
                        elif hasattr(block, 'name'):
                            print(f"Tool used: {block.name}")
                print("-" * 20)
                if 'Result' in type(msg).__name__:
                    break
            
    except Exception as e:
        print(f"❌ Error during MCP test: {e}")
        import traceback
        traceback.print_exc()

async def main():
    print("🚀 Claude Code SDK Local Test")
    print("=" * 50)
    
    # Test 1: Connection
    client = await test_claude_connection()
    if not client:
        print("❌ Cannot proceed without client connection")
        return
    
    print("\n" + "=" * 50)
    
    # Test 2: Simple message
    await test_simple_message(client, "Hello! Please introduce yourself briefly.")
    
    print("\n" + "=" * 50)
    
    # Test 3: MCP Tools
    await test_mcp_tools(client)
    
    print("\n" + "=" * 50)
    
    # Test 4: DAB Generation
    await test_dab_generation_message(client)
    
    print("\n✅ Testing complete!")

if __name__ == "__main__":
    asyncio.run(main())