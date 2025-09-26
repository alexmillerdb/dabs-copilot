#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'mcp' / 'server'))

from workspace_factory import get_or_create_client
from dotenv import load_dotenv
import asyncio

load_dotenv()

async def test():
    print("Testing workspace client initialization...")
    client = get_or_create_client()
    print(f"Client: {client}")
    if client:
        print(f"Host: {client.config.host}")
        print(f"Profile: {client.config.profile}")
        me = client.current_user.me()
        print(f"User: {me.user_name}")

asyncio.run(test())