#!/usr/bin/env python3
"""
Simple Claude Code SDK test - minimal version
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
project_root = Path(__file__).parent.parent.parent
dotenv_path = project_root / ".env"
load_dotenv(dotenv_path)

from claude_client import create_chat_client

async def simple_test():
    print("🧪 Simple Claude Code SDK Test")
    print(f"Claude API Key configured: {'Yes' if os.getenv('CLAUDE_API_KEY') else 'No'}")
    
    try:
        client = await create_chat_client()
        print("✅ Client created")
        
        async with client:
            print("📤 Sending simple message...")
            await client.query("Hello! Just say 'Hi' back.")
            
            message_count = 0
            async for msg in client.receive_messages():
                message_count += 1
                print(f"📥 Message {message_count}: {type(msg).__name__}")
                
                if hasattr(msg, 'content') and msg.content:
                    for block in msg.content:
                        if hasattr(block, 'text'):
                            print(f"   Text: {block.text}")
                        elif hasattr(block, 'name'):
                            print(f"   Tool: {block.name}")
                
                # Limit to prevent infinite loop
                if message_count >= 5 or 'Result' in type(msg).__name__:
                    break
            
            print("✅ Test complete!")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(simple_test())